"""Read-only queries for the Source coverage page: what one source has and another lacks.

A publication is "in" a source when at least one of its records came from that source
(``marts.bridge_publication_source``). Comparisons work for any pair of the sources in
``marts.dim_source_system``, so a source added later appears here without a code change.
:data:`COVERAGE_GAPS` holds the three comparisons the UNZA Library asked for (issue #22).

Rows come back as :class:`ihub.mart.research.PublicationRow`, so the explorer's CSV export
(:func:`ihub.mart.research.publications_to_csv`) works for them unchanged. A row's
``record_url`` is the record in the source the publication *is* in, because that is the
record a librarian follows up. All values are passed as query parameters.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ihub.mart._duckdb import fetch
from ihub.mart.research import PublicationRow, YearRange


@dataclass(frozen=True)
class SourceSystem:
    """One source the platform reads publications from."""

    code: str
    name: str
    kind: str


@dataclass(frozen=True)
class SourceTotal:
    """How many publications in a period have a record in one source."""

    source: SourceSystem
    publications: int


@dataclass(frozen=True)
class CoverageGap:
    """A named comparison: publications in ``in_source`` with no record in ``missing_from``."""

    in_source: str
    missing_from: str
    title: str
    purpose: str


#: The comparisons the Source coverage page always shows (issue #22).
COVERAGE_GAPS: tuple[CoverageGap, ...] = (
    CoverageGap(
        in_source="openalex",
        missing_from="dspace_oai",
        title="In OpenAlex, not in the repository",
        purpose="UNZA publications that could be deposited in the institutional repository.",
    ),
    CoverageGap(
        in_source="ojs",
        missing_from="openalex",
        title="OJS articles not in OpenAlex",
        purpose="Articles in UNZA's own journals that OpenAlex does not index.",
    ),
    CoverageGap(
        in_source="dspace_oai",
        missing_from="openalex",
        title="In the repository, not in OpenAlex",
        purpose="Repository items that OpenAlex does not know about.",
    ),
)

# Publications with a record in the source given by the parameter.
_IN_SOURCE = """
    SELECT b.publication_key
    FROM marts.bridge_publication_source AS b
    JOIN marts.dim_source_system AS s USING (source_system_key)
    WHERE s.source_system = ?
"""

_GAP_FROM = f"""
    FROM marts.fact_publication AS f
    JOIN marts.dim_publication AS p USING (publication_key)
    JOIN marts.dim_venue AS v USING (venue_key)
    JOIN marts.dim_publication_type AS t USING (type_key)
    WHERE f.year_key BETWEEN ? AND ?
      AND f.publication_key IN ({_IN_SOURCE})
      AND f.publication_key NOT IN ({_IN_SOURCE})
"""


def source_systems(db_path: Path) -> tuple[SourceSystem, ...]:
    """Return every source system, in name order."""
    rows = fetch(
        db_path,
        "SELECT source_system, source_name, source_kind FROM marts.dim_source_system "
        "ORDER BY source_name",
    )
    return tuple(SourceSystem(code, name, kind) for code, name, kind in rows)


def source_totals(db_path: Path, years: YearRange) -> list[SourceTotal]:
    """Return, for every source, how many publications in ``years`` have a record in it."""
    rows = fetch(
        db_path,
        """
        SELECT s.source_system, s.source_name, s.source_kind, count(DISTINCT f.publication_key)
        FROM marts.dim_source_system AS s
        LEFT JOIN marts.bridge_publication_source AS b USING (source_system_key)
        LEFT JOIN marts.fact_publication AS f
            ON f.publication_key = b.publication_key
            AND f.year_key BETWEEN ? AND ?
        GROUP BY s.source_system, s.source_name, s.source_kind
        ORDER BY s.source_name
        """,
        [years.start, years.end],
    )
    return [
        SourceTotal(SourceSystem(code, name, kind), int(count)) for code, name, kind, count in rows
    ]


def _check_pair(db_path: Path, in_source: str, missing_from: str) -> None:
    """Refuse a comparison of a source with itself or with a source that does not exist."""
    if in_source == missing_from:
        raise ValueError("Compare two different sources")
    known = {source.code for source in source_systems(db_path)}
    unknown = [code for code in (in_source, missing_from) if code not in known]
    if unknown:
        raise ValueError(f"Unknown source(s): {', '.join(unknown)}")


def count_missing(db_path: Path, in_source: str, missing_from: str, years: YearRange) -> int:
    """Return how many publications in ``years`` are in ``in_source`` but not ``missing_from``."""
    _check_pair(db_path, in_source, missing_from)
    return int(
        fetch(
            db_path,
            f"SELECT count(*) {_GAP_FROM}",
            [years.start, years.end, in_source, missing_from],
        )[0][0]
    )


def missing_publications(
    db_path: Path,
    in_source: str,
    missing_from: str,
    years: YearRange,
    limit: int | None = 100,
    offset: int = 0,
) -> list[PublicationRow]:
    """Return the publications in ``years`` that are in ``in_source`` but not ``missing_from``.

    Newest and most cited first, as in the explorer. Pass ``limit=None`` for every row
    (used for CSV export).
    """
    if limit is not None and limit < 0:
        raise ValueError("limit must not be negative")
    if offset < 0:
        raise ValueError("offset must not be negative")
    _check_pair(db_path, in_source, missing_from)
    params: list[object] = [in_source, years.start, years.end, in_source, missing_from]
    paging = ""
    if limit is not None:
        paging = "LIMIT ? OFFSET ?"
        params += [limit, offset]
    rows = fetch(
        db_path,
        f"""
        SELECT
            p.title, f.year_key, t.type_label, v.venue_name, f.oa_status,
            f.cited_by_count, f.n_authors,
            (
                SELECT string_agg(DISTINCT s.source_name, ', ' ORDER BY s.source_name)
                FROM marts.bridge_publication_source AS b
                JOIN marts.dim_source_system AS s USING (source_system_key)
                WHERE b.publication_key = f.publication_key
            ) AS sources,
            p.doi, p.doi_url,
            (
                SELECT min(b.source_url)
                FROM marts.bridge_publication_source AS b
                JOIN marts.dim_source_system AS s USING (source_system_key)
                WHERE b.publication_key = f.publication_key AND s.source_system = ?
            ) AS record_url
        {_GAP_FROM}
        ORDER BY f.year_key DESC, f.cited_by_count DESC, p.title, p.publication_key
        {paging}
        """,
        params,
    )
    return [
        PublicationRow(
            title=r[0],
            year=int(r[1]),
            type=r[2],
            venue=r[3],
            oa_status=r[4],
            cited_by_count=int(r[5]),
            n_authors=int(r[6]),
            sources=r[7] or "",
            doi=r[8],
            doi_url=r[9],
            record_url=r[10],
        )
        for r in rows
    ]
