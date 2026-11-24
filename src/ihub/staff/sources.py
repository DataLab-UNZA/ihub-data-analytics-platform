"""Where the staff roster comes from (ADR-017).

The matching code (:mod:`ihub.staff.attribution`) depends on :class:`RosterSource`, not on a
file, so a new place to keep the roster (an HR system API, for example) is one more class here
and nothing else changes. Two sources exist:

* :class:`CsvRosterSource`: a local CSV (``IHUB_STAFF_ROSTER_PATH``), with the hand-confirmed
  overrides file next to it. Used in development.
* :class:`MartRosterSource`: the public staff list in ``marts.dim_staff``, built by the pipeline
  from the ``unza_staff`` connector. Used in production, where there is no local file.

:func:`choose_roster` picks the CSV when it exists, otherwise the mart when it has staff.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Hashable
from pathlib import Path

from ihub.mart import staff_links
from ihub.staff.overrides import overrides_path
from ihub.staff.roster import Roster, load_roster, roster_from_rows


def _stamp(path: Path | None) -> int:
    """The modification time of a file, or 0 when there is none."""
    return Path(path).stat().st_mtime_ns if path and Path(path).is_file() else 0


class RosterSource(ABC):
    """A place the roster can be read from."""

    @abstractmethod
    def load(self) -> Roster | None:
        """Return the roster, or None when this source has no staff."""

    @abstractmethod
    def version(self) -> Hashable:
        """A value that changes whenever the roster (or its overrides) changes, for caches."""

    def overrides_file(self) -> Path | None:
        """The hand-confirmed links file for this roster, if it has one."""
        return None


class CsvRosterSource(RosterSource):
    """The roster in a local CSV file, with the overrides file next to it."""

    def __init__(self, path: Path) -> None:
        self.path = Path(path)

    def load(self) -> Roster | None:
        return load_roster(self.path)

    def overrides_file(self) -> Path | None:
        return overrides_path(self.path)

    def version(self) -> Hashable:
        return ("csv", str(self.path), _stamp(self.path), _stamp(self.overrides_file()))


class MartRosterSource(RosterSource):
    """The public staff list in ``marts.dim_staff`` of the research database."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = Path(db_path)

    def load(self) -> Roster | None:
        rows = staff_links.public_staff(self.db_path)
        return roster_from_rows(rows) if rows else None

    def version(self) -> Hashable:
        return ("mart", str(self.db_path), _stamp(self.db_path))


#: What the API is given: called per request, returns a source, a CSV path, or None.
RosterProvider = Callable[[], "RosterSource | Path | None"]


def as_source(roster: RosterSource | Path | None) -> RosterSource | None:
    """Accept a source or a path to a roster CSV (a missing file gives None)."""
    if roster is None or isinstance(roster, RosterSource):
        return roster
    return CsvRosterSource(roster) if Path(roster).is_file() else None


def choose_roster(csv_path: Path | None, db_path: Path) -> RosterSource | None:
    """Return the local CSV when it exists, else the mart's staff list when it has rows."""
    if csv_path is not None and Path(csv_path).is_file():
        return CsvRosterSource(csv_path)
    if staff_links.has_public_staff(db_path):
        return MartRosterSource(db_path)
    return None
