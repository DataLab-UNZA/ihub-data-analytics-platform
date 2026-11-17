"""Crediting schools with publications through the staff roster (ADR-012).

An author is linked to a school in one of four ways, recorded as the link's ``basis``:

* ``roster``: the author's name fits one roster entry (or several in the same school);
* ``roster_tiebreak``: the name fits entries in different schools, and the author's department
  evidence names exactly one of them;
* ``department_for_fellow``: the name fits a staff development fellow (no school in the roster),
  so the school comes from the author's department evidence;
* ``department_only``: the name is not on the roster but the pipeline found the author's
  department. This is the older, supplementary evidence, reported separately.

A publication counts once in every school with a linked author. Only school-level numbers are
returned; no name, staff ID or per-person result leaves this module.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from ihub.mart import staff_links
from ihub.mart.research import YearRange
from ihub.staff.matching import INITIAL, RosterIndex, match_name
from ihub.staff.names import parse_person
from ihub.staff.roster import Roster, load_roster

ROSTER = "roster"
TIEBREAK = "roster_tiebreak"
FELLOW = "department_for_fellow"
DEPARTMENT_ONLY = "department_only"

#: Link bases that come from the roster (the rest is supplementary department evidence).
ROSTER_BASES = frozenset({ROSTER, TIEBREAK, FELLOW})


@dataclass(frozen=True)
class AuthorLink:
    """The schools one author is credited to, and why."""

    schools: frozenset[str]
    basis: str
    rule: str | None = None


@dataclass(frozen=True)
class LinkStats:
    """How the matching went, in numbers only."""

    authors_considered: int
    by_rule: dict[str, int]
    roster_linked: int  # authors credited through the roster (any roster basis)
    tiebroken: int
    ambiguous: int  # fit several people or schools and department evidence could not choose
    initials_uncorroborated: int  # an initial fitted one person but no department evidence agreed
    fellows_without_evidence: int  # fit only staff development fellows, no department known
    department_only: int
    unmatched: int
    roster_headcount: int
    roster_staff_matched: int
    roster_rows_skipped: int


@dataclass(frozen=True)
class LinkResult:
    """Per-author links (internal) and the matching statistics (safe to report)."""

    links: dict[str, AuthorLink]
    stats: LinkStats
    staff_by_school: dict[str, int] = field(default_factory=dict)
    matched_staff_by_school: dict[str, int] = field(default_factory=dict)


def link_authors(
    authors: Iterable[tuple[str, str]],
    roster: Roster,
    evidence: Mapping[str, frozenset[str]],
) -> LinkResult:
    """Link ``(author_key, author_name)`` pairs to schools through ``roster``.

    ``evidence`` maps an author to the schools of the departments found for that author.
    """
    index = RosterIndex(roster.members)
    links: dict[str, AuthorLink] = {}
    by_rule: Counter[str] = Counter()
    matched_staff: dict[str, set[str]] = defaultdict(set)
    considered = tiebroken = ambiguous = uncorroborated = 0
    fellows_blank = department_only = unmatched = 0

    for key, name in authors:
        considered += 1
        known = evidence.get(key, frozenset())
        outcome = match_name(parse_person(name), index)
        candidates = list(outcome.candidates)
        if outcome.ambiguous:
            ambiguous += 1
        if candidates and candidates[0].rule == INITIAL:
            # The weakest rule only counts when the author's department evidence agrees.
            agreeing = [c for c in candidates if c.member.school in known]
            if not agreeing:
                uncorroborated += 1
            candidates = agreeing
        if not candidates:
            if known:
                links[key] = AuthorLink(known, DEPARTMENT_ONLY)
                department_only += 1
            else:
                unmatched += 1
            continue

        rule = candidates[0].rule
        schools = {c.member.school for c in candidates if c.member.school is not None}
        if len(schools) == 1:
            links[key] = AuthorLink(frozenset(schools), ROSTER, rule)
        elif len(schools) > 1:
            chosen = schools & known
            if len(chosen) != 1:
                ambiguous += 1
                if known:
                    links[key] = AuthorLink(known, DEPARTMENT_ONLY)
                    department_only += 1
                continue
            links[key] = AuthorLink(frozenset(chosen), TIEBREAK, rule)
            tiebroken += 1
        elif known:  # only staff development fellows fit: take the school from the department
            links[key] = AuthorLink(known, FELLOW, rule)
        else:
            fellows_blank += 1
            continue
        by_rule[rule] += 1
        for candidate in candidates:
            if candidate.member.school in links[key].schools:
                matched_staff[candidate.member.school].add(candidate.member.staff_id)

    staff_by_school = Counter(m.school for m in roster.members if m.school is not None)
    matched_ids = {sid for ids in matched_staff.values() for sid in ids}
    stats = LinkStats(
        authors_considered=considered,
        by_rule=dict(by_rule),
        roster_linked=sum(1 for link in links.values() if link.basis in ROSTER_BASES),
        tiebroken=tiebroken,
        ambiguous=ambiguous,
        initials_uncorroborated=uncorroborated,
        fellows_without_evidence=fellows_blank,
        department_only=department_only,
        unmatched=unmatched,
        roster_headcount=roster.headcount,
        roster_staff_matched=len(matched_ids),
        roster_rows_skipped=roster.skipped_rows,
    )
    return LinkResult(
        links,
        stats,
        staff_by_school=dict(staff_by_school),
        matched_staff_by_school={school: len(ids) for school, ids in matched_staff.items()},
    )


@dataclass(frozen=True)
class SchoolCredit:
    """What one school is credited with in a period."""

    school: str
    roster_publications: int  # distinct publications with an author linked through the roster
    publications: int  # the same, plus authors known only from department evidence
    roster_authors: int  # distinct author records linked through the roster
    staff_in_roster: int
    staff_matched: int


@dataclass(frozen=True)
class SchoolCreditReport:
    """School credit for a period, with how much of the corpus it covers."""

    years: YearRange
    schools: tuple[SchoolCredit, ...]
    total_publications: int
    credited_by_roster: int  # publications with at least one roster-linked school
    credited_any: int  # ... or any department-evidence school
    stats: LinkStats


def aggregate(
    result: LinkResult,
    pairs: Iterable[tuple[str, str]],
    years: YearRange,
    total_publications: int,
) -> SchoolCreditReport:
    """Count distinct publications per school from ``(author_key, publication_key)`` pairs."""
    roster_pubs: dict[str, set[str]] = defaultdict(set)
    any_pubs: dict[str, set[str]] = defaultdict(set)
    roster_authors: dict[str, set[str]] = defaultdict(set)
    for author, publication in pairs:
        link = result.links.get(author)
        if link is None:
            continue
        for school in link.schools:
            any_pubs[school].add(publication)
            if link.basis in ROSTER_BASES:
                roster_pubs[school].add(publication)
                roster_authors[school].add(author)

    schools = [
        SchoolCredit(
            school=school,
            roster_publications=len(roster_pubs.get(school, ())),
            publications=len(pubs),
            roster_authors=len(roster_authors.get(school, ())),
            staff_in_roster=result.staff_by_school.get(school, 0),
            staff_matched=result.matched_staff_by_school.get(school, 0),
        )
        for school, pubs in any_pubs.items()
    ]
    # Schools on the roster with no publication in the period still appear, with zeros.
    listed = {s.school for s in schools}
    schools += [
        SchoolCredit(school, 0, 0, 0, count, result.matched_staff_by_school.get(school, 0))
        for school, count in result.staff_by_school.items()
        if school not in listed
    ]
    schools.sort(key=lambda s: (-s.roster_publications, -s.publications, s.school))
    return SchoolCreditReport(
        years=years,
        schools=tuple(schools),
        total_publications=total_publications,
        credited_by_roster=len(set().union(*roster_pubs.values())) if roster_pubs else 0,
        credited_any=len(set().union(*any_pubs.values())) if any_pubs else 0,
        stats=result.stats,
    )


_cache: dict[tuple[str, int, str, int], tuple[Roster, LinkResult]] = {}


def _mtime(path: Path) -> int:
    return Path(path).stat().st_mtime_ns


def linked_authors(db_path: Path, roster_path: Path) -> tuple[Roster, LinkResult] | None:
    """Return the roster and the author links, or None when there is no roster file.

    The result is kept until the database or the roster file changes.
    """
    if not Path(roster_path).is_file() or not Path(db_path).is_file():
        return None
    key = (str(db_path), _mtime(db_path), str(roster_path), _mtime(roster_path))
    if key not in _cache:
        roster = load_roster(roster_path)
        if roster is None:
            return None
        authors = staff_links.unza_authors(db_path)
        evidence = staff_links.author_department_schools(db_path)
        _cache.clear()  # keep one entry: a rebuilt database or roster replaces the old one
        _cache[key] = (roster, link_authors(authors, roster, evidence))
    return _cache[key]


def school_credit(
    db_path: Path, roster_path: Path, years: YearRange, total_publications: int
) -> SchoolCreditReport | None:
    """Credit schools with the publications of their roster-linked authors in ``years``.

    Returns None when there is no roster, so callers can fall back to department-based counts.
    """
    linked = linked_authors(db_path, roster_path)
    if linked is None:
        return None
    _, result = linked
    pairs = staff_links.author_publications(db_path, list(result.links), years)
    return aggregate(result, pairs, years, total_publications)
