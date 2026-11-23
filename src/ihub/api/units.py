"""Which publications belong to a unit, and how they split by source (Organisation screens).

One place decides this, so the Organisation counts, the unit filter on the publication list,
its CSV export and its breakdowns all agree. With the private staff roster (ADR-012) a unit is
a roster school and its publications are the ones with a roster-linked author; without it the
units are the department-based schools (ADR-004). This module holds no SQL: it combines
:mod:`ihub.mart` queries and :mod:`ihub.staff` results.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from ihub.mart import coverage, staff_links, units
from ihub.mart.insights import UNASSIGNED_UNIT
from ihub.mart.research import YearRange, year_bounds
from ihub.staff import attribution
from ihub.staff.overrides import overrides_path

#: Publications with no roster-linked school, shown as a unit of their own.
NOT_CREDITED = "Not credited to a school"

#: Labels that are not a school; the school charts of Explore leave them out.
NOT_A_SCHOOL = frozenset({NOT_CREDITED, UNASSIGNED_UNIT})

_chart_cache: dict[tuple[object, ...], dict[str, list[tuple[str, str]]]] = {}


def _stamp(path: Path | None) -> int:
    """The modification time of a file, or 0 when there is none."""
    return Path(path).stat().st_mtime_ns if path and Path(path).is_file() else 0


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

    def chart_tables(self, names: frozenset[str]) -> Mapping[str, Sequence[tuple[str, str]]]:
        """The temporary tables the school datasets of Explore join (see ``explore.TEMP_TABLES``).

        ``unit_pub`` holds ``(school, publication_key)`` and ``author_unit`` holds
        ``(author_key, school)``, for every year (the query filters years). Only publication
        and author keys and school names leave here: no author name or staff ID. The result is
        kept until the database, the roster or the overrides file changes.
        """
        db = self.database_path()
        roster = self.staff_roster_path()
        key = (
            str(db),
            _stamp(db),
            str(roster or ""),
            _stamp(roster),
            _stamp(overrides_path(roster) if roster else None),
        )
        cached = _chart_cache.get(key)
        if cached is None:
            _chart_cache.clear()  # one entry: a rebuilt database or roster replaces it
            cached = _chart_cache[key] = {}
        if "unit_pub" in names and "unit_pub" not in cached:
            sets = self.publication_sets(year_bounds(db))
            cached["unit_pub"] = [
                (unit, publication)
                for unit, keys in sets.items()
                if unit not in NOT_A_SCHOOL
                for publication in sorted(keys)
            ]
        if "author_unit" in names and "author_unit" not in cached:
            cached["author_unit"] = self._author_units(db, roster)
        return {name: cached[name] for name in names if name in cached}

    @staticmethod
    def _author_units(db: Path, roster: Path | None) -> list[tuple[str, str]]:
        """``(author_key, school)`` for authors linked to a school (roster, else departments)."""
        linked = attribution.linked_authors(db, roster) if roster else None
        if linked is not None:
            _, result = linked
            pairs = [
                (author, school)
                for author, link in result.links.items()
                if link.basis in attribution.ROSTER_BASES
                for school in link.schools
            ]
        else:
            evidence = staff_links.author_department_schools(db)
            pairs = [(author, school) for author, schools in evidence.items() for school in schools]
        return sorted((a, s) for a, s in pairs if s not in NOT_A_SCHOOL)
