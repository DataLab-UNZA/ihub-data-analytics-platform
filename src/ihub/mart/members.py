"""Read-only queries behind the Members directory: ORCID iDs and publication facts per author.

Same rules as :mod:`ihub.mart.research`: only SQL here, every value a query parameter. The
matching of authors to staff is in :mod:`ihub.staff`.
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from ihub.mart._duckdb import fetch
from ihub.mart.research import YearRange


def author_orcids(db_path: Path, author_keys: Sequence[str]) -> dict[str, str]:
    """Return the ORCID iD of each author in ``author_keys`` that has one."""
    if not author_keys:
        return {}
    rows = fetch(
        db_path,
        """
        SELECT author_key, orcid_id FROM marts.dim_author
        WHERE orcid_id IS NOT NULL AND list_contains(?, author_key)
        """,
        [list(author_keys)],
    )
    return {str(key): str(orcid) for key, orcid in rows}


def author_publication_facts(
    db_path: Path, author_keys: Sequence[str], years: YearRange
) -> list[tuple[str, str, bool, int]]:
    """Return distinct ``(author_key, publication_key, is_oa, cited_by_count)`` in ``years``."""
    if not author_keys:
        return []
    rows = fetch(
        db_path,
        """
        SELECT DISTINCT a.author_key, a.publication_key, coalesce(f.is_oa, false),
                        coalesce(f.cited_by_count, 0)
        FROM marts.fact_authorship AS a
        JOIN marts.fact_publication AS f USING (publication_key)
        WHERE f.year_key BETWEEN ? AND ? AND list_contains(?, a.author_key)
        """,
        [years.start, years.end, list(author_keys)],
    )
    return [(str(a), str(p), bool(oa), int(c)) for a, p, oa, c in rows]
