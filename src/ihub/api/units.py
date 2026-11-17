"""Which publications belong to a unit, and how they split by source (Organisation screens).

One place decides this, so the Organisation counts, the unit filter on the publication list,
its CSV export and its breakdowns all agree. With the private staff roster (ADR-012) a unit is
a roster school and its publications are the ones with a roster-linked author; without it the
units are the department-based schools (ADR-004). This module holds no SQL: it combines
:mod:`ihub.mart` queries and :mod:`ihub.staff` results.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from ihub.mart import coverage, units
from ihub.mart.research import YearRange
from ihub.staff import attribution

#: Publications with no roster-linked school, shown as a unit of their own.
NOT_CREDITED = "Not credited to a school"


@dataclass(frozen=True)
class UnitScope:
    """Resolves unit names to publication sets for a period."""

    database_path: Callable[[], Path]
    staff_roster_path: Callable[[], Path | None]

    def publication_sets(self, years: YearRange) -> dict[str, frozenset[str]]:
        """Return unit name -> publication keys, for every unit the screens can offer."""
        db = self.database_path()
        roster = self.staff_roster_path()
        sets = attribution.school_publications(db, roster, years) if roster else None
        if sets is None:
            return units.department_publications(db, years)
        credited = frozenset().union(*sets.values())
        sets[NOT_CREDITED] = units.all_publication_keys(db, years) - credited
        return sets

    def names(self, years: YearRange) -> list[str]:
        """Return the unit names for the Unit filter: busiest first, units with none last."""
        sets = self.publication_sets(years)
        schools = [name for name in sets if name != NOT_CREDITED]
        schools.sort(key=lambda name: (-len(sets[name]), name))
        return schools + ([NOT_CREDITED] if NOT_CREDITED in sets else [])

    def keys(self, unit: str, years: YearRange) -> frozenset[str]:
        """Return the publications of ``unit`` in ``years``; ValueError for an unknown unit."""
        sets = self.publication_sets(years)
        if unit not in sets:
            raise ValueError(f"Unknown unit: {unit}")
        return sets[unit]

    def source_breakdown(self, years: YearRange) -> dict[str, object]:
        """Return how many publications of every unit (and of the whole corpus) each source holds.

        ``sources`` lists the sources in the mart (so one that is not loaded is simply absent).
        ``by_unit`` maps a unit to ``{source code: publications}`` for ``years``.
        """
        db = self.database_path()
        held = units.publication_sources(db, years)
        sources = coverage.source_systems(db)
        codes = [source.code for source in sources]

        def count(keys: frozenset[str] | set[str]) -> dict[str, int]:
            return {code: sum(1 for key in keys if code in held.get(key, ())) for code in codes}

        return {
            "sources": [{"code": s.code, "name": s.name, "kind": s.kind} for s in sources],
            "all": {t.source.code: t.publications for t in coverage.source_totals(db, years)},
            "by_unit": {name: count(keys) for name, keys in self.publication_sets(years).items()},
        }
