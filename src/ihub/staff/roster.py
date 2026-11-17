"""Reading the staff roster (private HR data, ADR-012).

The file has the columns ``Staff ID, Surname, First Name, Second Name, Title, Occupation, School``.
Only the name words, the staff ID and the school are kept in memory; titles and occupations are
not used. Nothing here writes the roster anywhere.
"""

from __future__ import annotations

import csv
from collections import Counter
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

    staff_id: str
    school: str | None
    surname: frozenset[str]
    words: frozenset[str]  # every whole word of the name, surname included
    initials: frozenset[str]  # initials written as such, and the first letters of given names

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


def _member(row: dict[str, str]) -> StaffMember | None:
    surname = name_words(row.get("Surname"))
    given = name_words(row.get("First Name")) + name_words(row.get("Second Name"))
    words = frozenset(word for word in surname + given if len(word) > 1)
    if not words or not surname:
        return None
    initials = frozenset(
        {word for word in surname + given if len(word) == 1} | {word[0] for word in given}
    )
    return StaffMember(
        staff_id=str(row.get("Staff ID", "")).strip(),
        school=school_for_label(row.get("School")),
        surname=frozenset(word for word in surname if len(word) > 1),
        words=words,
        initials=initials,
    )


def load_roster(path: Path) -> Roster | None:
    """Read the roster CSV, or return None when there is no file (the screen then falls back)."""
    if not Path(path).is_file():
        return None
    members: list[StaffMember] = []
    skipped = 0
    labels: Counter[str] = Counter()
    with open(path, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            member = _member(row)
            if member is None:
                skipped += 1
                continue
            members.append(member)
            labels[(row.get("School") or "").strip()] += 1
    return Roster(tuple(members), skipped_rows=skipped, by_label=dict(labels))
