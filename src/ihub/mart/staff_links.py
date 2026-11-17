"""Read-only queries that feed the school credit built from the staff roster (ADR-012).

Only the SQL lives here. The name matching is in :mod:`ihub.staff`, which never reads the
database itself. Same rules as :mod:`ihub.mart.research`: every value is a query parameter.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Sequence
from pathlib import Path

from ihub.mart._duckdb import fetch
from ihub.mart.research import YearRange


def unza_authors(db_path: Path) -> list[tuple[str, str]]:
    """Return ``(author_key, author_name)`` for every UNZA author with at least one authorship."""
    rows = fetch(
        db_path,
        """
        SELECT d.author_key, d.author_name
        FROM marts.dim_author AS d
        WHERE d.is_unza_author
          AND EXISTS (SELECT 1 FROM marts.fact_authorship AS a WHERE a.author_key = d.author_key)
        ORDER BY d.author_key
        """,
    )
    return [(str(key), str(name)) for key, name in rows]


def author_identifiers(db_path: Path) -> list[tuple[str, str | None, str | None]]:
    """Return ``(author_key, openalex_author_id, orcid_id)`` for every UNZA author."""
    rows = fetch(
        db_path,
        "SELECT author_key, openalex_author_id, orcid_id FROM marts.dim_author "
        "WHERE is_unza_author ORDER BY author_key",
    )
    return [(str(key), openalex, orcid) for key, openalex, orcid in rows]


def author_department_schools(db_path: Path) -> dict[str, frozenset[str]]:
    """Return, per author, the schools of the departments the pipeline found for that author.

    Only ``author_department`` evidence counts (the department was found for the person, not
    just for the publication), and only departments that belong to a school.
    """
    rows = fetch(
        db_path,
        """
        SELECT a.author_key, o.school_name
        FROM marts.fact_authorship AS a
        JOIN marts.dim_org AS o USING (org_key)
        WHERE o.org_kind = 'unza_unit'
          AND a.org_basis = 'author_department'
          AND o.school_name IS NOT NULL
        GROUP BY a.author_key, o.school_name
        """,
    )
    evidence: dict[str, set[str]] = defaultdict(set)
    for key, school in rows:
        evidence[str(key)].add(str(school))
    return {key: frozenset(schools) for key, schools in evidence.items()}


def author_publications(
    db_path: Path, author_keys: Sequence[str], years: YearRange
) -> list[tuple[str, str]]:
    """Return distinct ``(author_key, publication_key)`` pairs for ``author_keys`` in ``years``."""
    if not author_keys:
        return []
    rows = fetch(
        db_path,
        """
        SELECT DISTINCT a.author_key, a.publication_key
        FROM marts.fact_authorship AS a
        WHERE a.year_key BETWEEN ? AND ?
          AND list_contains(?, a.author_key)
        """,
        [years.start, years.end, list(author_keys)],
    )
    return [(str(author), str(publication)) for author, publication in rows]
