"""Who is who in the Members directory: roster staff linked to publication authors (ADR-014).

This is the one place where a person (name, title, school) leaves the matching code. A staff
member appears only when their name fits exactly one roster entry in the credited school, so
two people with the same name are never merged into one profile. Access is controlled by the
``members:read`` permission in the API; this module only builds the records.
"""

from __future__ import annotations

import hashlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from ihub.staff.attribution import MEMBER_BASES, linked_authors
from ihub.staff.sources import RosterSource


@dataclass(frozen=True)
class MemberRecord:
    """One roster staff member, and the author records that were matched to them."""

    member_id: str  # opaque, stable for a staff key; the staff key itself is never exposed
    title: str
    name: str
    school: str | None  # a fellow's school comes from department evidence, when there is one
    author_keys: tuple[str, ...]
    fellow: bool = False  # a staff development fellow: the roster gives them no school


def member_id(staff_key: str) -> str:
    """Return the opaque id used in URLs for ``staff_key``."""
    return "m" + hashlib.sha256(staff_key.encode("utf-8")).hexdigest()[:12]


def directory(db_path: Path, roster_path: RosterSource | Path | None) -> list[MemberRecord] | None:
    """Return the matched staff, A to Z by name, or None when there is no roster."""
    linked = linked_authors(db_path, roster_path)
    if linked is None:
        return None
    roster, result = linked
    by_staff: dict[str, list[str]] = defaultdict(list)
    for author_key, link in result.links.items():
        if link.basis in MEMBER_BASES and link.staff_key:
            by_staff[link.staff_key].append(author_key)
    people = {member.staff_key: member for member in roster.members}
    records = []
    for staff_key, keys in by_staff.items():
        person = people.get(staff_key)
        if person is None:
            continue
        school = person.school
        if school is None:  # a fellow: use the department evidence only if it names one school
            found = {s for key in keys for s in result.links[key].schools}
            school = next(iter(found)) if len(found) == 1 else None
        records.append(
            MemberRecord(
                member_id=member_id(staff_key),
                title=person.title,
                name=person.display_name,
                school=school,
                author_keys=tuple(sorted(keys)),
                fellow=person.school is None,
            )
        )
    records.sort(key=lambda record: (record.name.casefold(), record.member_id))
    return records
