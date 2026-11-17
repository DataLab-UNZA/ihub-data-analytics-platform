"""Read-only queries that tie publications to UNZA units and sources (Organisation screens).

The unit scope of a publication list is a set of publication keys. This module supplies the
building blocks; :mod:`ihub.api.units` decides which set applies (roster credit or department
evidence). Same rules as :mod:`ihub.mart.research`: only SQL here, every value a parameter.
"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from ihub.mart._duckdb import fetch
from ihub.mart.insights import UNIT_LABEL_SQL
from ihub.mart.research import YearRange


def all_publication_keys(db_path: Path, years: YearRange) -> frozenset[str]:
    """Return the key of every publication in ``years``."""
    rows = fetch(
        db_path,
        "SELECT publication_key FROM marts.fact_publication WHERE year_key BETWEEN ? AND ?",
        [years.start, years.end],
    )
    return frozenset(str(key) for (key,) in rows)


def department_publications(db_path: Path, years: YearRange) -> dict[str, frozenset[str]]:
    """Return, per unit label, the publications with an authorship in it (department evidence).

    The labels and counts are those of :func:`ihub.mart.insights.school_outputs`.
    """
    rows = fetch(
        db_path,
        f"""
        SELECT DISTINCT {UNIT_LABEL_SQL} AS unit, a.publication_key
        FROM marts.fact_authorship AS a
        JOIN marts.dim_org AS o USING (org_key)
        WHERE o.org_kind = 'unza_unit' AND a.year_key BETWEEN ? AND ?
        """,  # noqa: S608
        [years.start, years.end],
    )
    units: dict[str, set[str]] = defaultdict(set)
    for unit, key in rows:
        units[str(unit)].add(str(key))
    return {unit: frozenset(keys) for unit, keys in units.items()}


def publication_sources(db_path: Path, years: YearRange) -> dict[str, frozenset[str]]:
    """Return, per publication in ``years``, the codes of the sources that hold a record of it."""
    rows = fetch(
        db_path,
        """
        SELECT DISTINCT b.publication_key, s.source_system
        FROM marts.bridge_publication_source AS b
        JOIN marts.dim_source_system AS s USING (source_system_key)
        JOIN marts.fact_publication AS f ON f.publication_key = b.publication_key
        WHERE f.year_key BETWEEN ? AND ?
        """,
        [years.start, years.end],
    )
    found: dict[str, set[str]] = defaultdict(set)
    for key, code in rows:
        found[str(key)].add(str(code))
    return {key: frozenset(codes) for key, codes in found.items()}
