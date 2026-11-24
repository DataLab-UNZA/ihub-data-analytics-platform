"""Reading the staff roster (ADR-012, ADR-017).

A roster row has the columns ``Surname, First Name, Second Name, Title, Occupation, School``
(a local file may also have ``Staff ID``, which is ignored). Rows come from a local CSV or from
``marts.dim_staff`` (see :mod:`ihub.staff.sources`); both are read by :func:`roster_from_rows`,
so a person gets the same :attr:`StaffMember.staff_key` whichever source they come from.
Nothing here writes the roster anywhere.
"""

from __future__ import annotations

import csv
import hashlib
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

from ihub.staff.names import name_words

#: Roster school label -> name of the unit in the research mart (``marts.dim_org``).
SCHOOL_BY_LABEL: dict[str, str] = {
    "agricultural sciences": "School of Agricultural Sciences",
    "education": "School of Education",
    "engineering": "School of Engineering",
    "graduate school of business": "Graduate School of Business",
    "health sciences": "School of Health Sciences",
    "humanities and social sciences": "School of Humanities and Social Sciences",
    "law": "School of Law",
    "medicine": "School of Medicine",
    "mines": "School of Mines",
    "natural sciences": "School of Natural and Applied Sciences",
    "nursing sciences": "School of Nursing Sciences",
    "public health": "School of Public Health",
    "veterinary medicine": "School of Veterinary Medicine",
    "library": "University of Zambia Library",
    "ide": "Institute of Distance Education",
    "inesor": "Institute of Economic and Social Research (INESOR)",
    "drgs": "Directorate of Research and Graduate Studies (DRGS)",
}

#: Roster labels that are not a school or unit: the person has no school in the roster.
NO_SCHOOL_LABELS = frozenset({"sdf", ""})  # SDF = staff development fellows


def school_for_label(label: str | None) -> str | None:
    """Return the unit name for a roster school label, or None for "no school" (SDF, blank).

    A label that is not in :data:`SCHOOL_BY_LABEL` is kept as it was written, so a new unit in
    the roster is counted rather than dropped.
    """
    clean = " ".join((label or "").split())
    key = clean.lower()
    if key in NO_SCHOOL_LABELS:
        return None
    return SCHOOL_BY_LABEL.get(key, clean)


@dataclass(frozen=True)
class StaffMember:
    """One person on the roster, reduced to what matching needs."""

    #: Stable, opaque identity built from the name and school label (never a staff ID).
    staff_key: str
    school: str | None
    surname: frozenset[str]
    words: frozenset[str]  # every whole word of the name, surname included
    initials: frozenset[str]  # initials written as such, and the first letters of given names
    title: str = ""  # "Dr", "Prof", ... as written in the roster (empty when blank)
    display_name: str = ""  # "Chanda Banda": given names then surname, in capitals and lower case

    @property
    def has_name(self) -> bool:
        return bool(self.words)


@dataclass(frozen=True)
class Roster:
    """The roster, with the counts reported to the screen."""

    members: tuple[StaffMember, ...]
    skipped_rows: int = 0
    by_label: dict[str, int] = field(default_factory=dict)

    @property
    def headcount(self) -> int:
        return len(self.members)


def display_name(row: Mapping[str, str | None]) -> str:
    """Return the person's name for display: given names, then the surname, in title case."""
    parts = [row.get("First Name"), row.get("Second Name"), row.get("Surname")]
    words = [word for part in parts if part for word in part.split() if not word.isdigit()]
    return " ".join(word.title() for word in words)


def staff_key(row: Mapping[str, str | None]) -> str:
    """Return the person's key: a hash of their name parts and school label, case-insensitive."""
    parts = [row.get(column) for column in ("Surname", "First Name", "Second Name", "School")]
    text = "|".join(" ".join((part or "").split()).casefold() for part in parts)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:20]


def _member(row: Mapping[str, str | None], key: str) -> StaffMember | None:
    surname = name_words(row.get("Surname"))
    given = name_words(row.get("First Name")) + name_words(row.get("Second Name"))
    words = frozenset(word for word in surname + given if len(word) > 1)
    if not words or not surname:
        return None
    initials = frozenset(
        {word for word in surname + given if len(word) == 1} | {word[0] for word in given}
    )
    return StaffMember(
        staff_key=key,
        school=school_for_label(row.get("School")),
        surname=frozenset(word for word in surname if len(word) > 1),
        words=words,
        initials=initials,
        title=" ".join((row.get("Title") or "").split()),
        display_name=display_name(row),
    )


def roster_from_rows(rows: Iterable[Mapping[str, str | None]]) -> Roster:
    """Build the roster from rows with the roster's column names.

    Two rows with the same name and school get different keys (``<key>-2``, ...), so they stay
    two people and the matching never merges them (ADR-014).
    """
    members: list[StaffMember] = []
    skipped = 0
    labels: Counter[str] = Counter()
    seen: Counter[str] = Counter()
    for row in rows:
        key = staff_key(row)
        seen[key] += 1
        member = _member(row, key if seen[key] == 1 else f"{key}-{seen[key]}")
        if member is None:
            skipped += 1
            continue
        members.append(member)
        labels[(row.get("School") or "").strip()] += 1
    return Roster(tuple(members), skipped_rows=skipped, by_label=dict(labels))


def load_roster(path: Path) -> Roster | None:
    """Read the roster CSV, or return None when there is no file (the screen then falls back)."""
    if not Path(path).is_file():
        return None
    with open(path, encoding="utf-8-sig", newline="") as handle:
        return roster_from_rows(csv.DictReader(handle))
