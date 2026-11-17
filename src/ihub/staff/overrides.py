"""Hand-confirmed links between a staff member and a publication author (ADR-014).

Name matching cannot link a person whose name is written differently in the roster and in the
publication sources (for example the roster has "Kakanda, Mukelabai Alfred" while OpenAlex
has "Mukelabai Mukelabai"). A person who has checked such a case can pin it in a private CSV
next to the roster, ``staff_author_overrides.csv``, with the columns ``Staff ID`` and
``Author ID``. The author ID is an OpenAlex author ID (``A5000315992``) or an ORCID iD
(``0000-0002-3868-4319``); full URLs are accepted. The file is private HR data, like the
roster, and is read from a git-ignored location.
"""

from __future__ import annotations

import csv
import re
from collections import defaultdict
from collections.abc import Iterable, Mapping
from pathlib import Path

OVERRIDES_FILENAME = "staff_author_overrides.csv"

_ORCID = re.compile(r"\d{4}-\d{4}-\d{4}-\d{3}[\dX]")
_OPENALEX = re.compile(r"A\d+")


def overrides_path(roster_path: Path) -> Path:
    """Return where the overrides file sits: next to the roster."""
    return Path(roster_path).with_name(OVERRIDES_FILENAME)


def normalise_author_id(text: str | None) -> str | None:
    """Return an OpenAlex author ID or ORCID iD in canonical form, or None if it is neither."""
    last = (text or "").strip().rstrip("/").rsplit("/", 1)[-1].upper()
    return last if _ORCID.fullmatch(last) or _OPENALEX.fullmatch(last) else None


def load_overrides(path: Path) -> dict[str, frozenset[str]]:
    """Read the overrides file: staff ID -> author IDs. A missing file or bad row gives nothing."""
    if not Path(path).is_file():
        return {}
    pinned: dict[str, set[str]] = defaultdict(set)
    with open(path, encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            staff_id = str(row.get("Staff ID") or "").strip()
            author_id = normalise_author_id(row.get("Author ID"))
            if staff_id and author_id:
                pinned[staff_id].add(author_id)
    return {staff_id: frozenset(ids) for staff_id, ids in pinned.items()}


def pin_authors(
    overrides: Mapping[str, frozenset[str]],
    identifiers: Iterable[tuple[str, str | None, str | None]],
) -> dict[str, str]:
    """Return author_key -> staff ID for every author whose OpenAlex ID or ORCID is pinned.

    ``identifiers`` holds ``(author_key, openalex_author_id, orcid_id)``. An author pinned to
    two different staff members is left out (the file contradicts itself).
    """
    owner: dict[str, set[str]] = defaultdict(set)
    for staff_id, ids in overrides.items():
        for author_id in ids:
            owner[author_id].add(staff_id)
    pinned: dict[str, set[str]] = defaultdict(set)
    for author_key, openalex_id, orcid in identifiers:
        for raw in (openalex_id, orcid):
            author_id = normalise_author_id(raw)
            if author_id and author_id in owner:
                pinned[author_key] |= owner[author_id]
    return {key: next(iter(ids)) for key, ids in pinned.items() if len(ids) == 1}
