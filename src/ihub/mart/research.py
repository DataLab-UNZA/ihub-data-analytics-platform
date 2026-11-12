"""Read-only queries on the research mart, used by the Streamlit pages.

Pages never contain SQL: they call the functions here, so the user interface can change
without touching the data layer. Every function takes the path of the DuckDB file first,
opens its own read-only connection and returns plain, typed values (no DataFrames).

All user-supplied values are passed as query parameters, never formatted into the SQL.
"""

from __future__ import annotations

import csv
import io
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ihub.mart._duckdb import MartUnavailableError
from ihub.mart._duckdb import fetch as _fetch

__all__ = ["MartUnavailableError"]  # re-exported: pages and tests import it from here

#: Sources a publication can be found in, mapped to the ``fact_publication`` flag.
SOURCE_FLAGS: dict[str, str] = {
    "OpenAlex": "in_openalex",
    "Repository": "in_repository",
    "OJS": "in_ojs",
}

#: Columns of the publications table, in export order: (field name, CSV header).
PUBLICATION_COLUMNS: tuple[tuple[str, str], ...] = (
    ("title", "Title"),
    ("year", "Year"),
    ("type", "Type"),
    ("venue", "Venue"),
    ("oa_status", "OA status"),
    ("cited_by_count", "Citations"),
    ("n_authors", "Authors"),
    ("sources", "Sources"),
    ("doi", "DOI"),
    ("doi_url", "DOI link"),
    ("record_url", "Record link"),
)


@dataclass(frozen=True)
class YearRange:
    """An inclusive range of publication years."""

    start: int
    end: int

    def __post_init__(self) -> None:
        if self.start > self.end:
            raise ValueError(f"Year range starts after it ends: {self.start} > {self.end}")

    def previous_period(self) -> YearRange:
        """Return the period of the same length that ends the year before this one starts."""
        length = self.end - self.start + 1
        return YearRange(self.start - length, self.start - 1)


@dataclass(frozen=True)
class HeadlineCounts:
    """The headline numbers for a period."""

    publications: int
    open_access_publications: int
    citations: int
    venues: int

    @property
    def open_access_share(self) -> float:
        """Share of publications that are open access, from 0 to 1 (0 when there are none)."""
        return self.open_access_publications / self.publications if self.publications else 0.0


@dataclass(frozen=True)
class YearCount:
    """Publications in one year."""

    year: int
    publications: int


@dataclass(frozen=True)
class YearOpenAccess:
    """Publications and open-access publications in one year."""

    year: int
    publications: int
    open_access_publications: int

    @property
    def open_access_share(self) -> float:
        """Share of publications that are open access, from 0 to 1."""
        return self.open_access_publications / self.publications if self.publications else 0.0


@dataclass(frozen=True)
class VenueCount:
    """Publications and citations for one venue."""

    venue: str
    publications: int
    citations: int


@dataclass(frozen=True)
class PublicationFilter:
    """Filters for the publications list. An empty selection means "no restriction"."""

    years: YearRange | None = None
    types: Sequence[str] = field(default_factory=tuple)
    oa_statuses: Sequence[str] = field(default_factory=tuple)
    venues: Sequence[str] = field(default_factory=tuple)
    sources: Sequence[str] = field(default_factory=tuple)
    search: str = ""


@dataclass(frozen=True)
class PublicationRow:
    """One publication as shown in the explorer."""

    title: str
    year: int
    type: str
    venue: str
    oa_status: str
    cited_by_count: int
    n_authors: int
    sources: str
    doi: str | None
    doi_url: str | None
    record_url: str | None


@dataclass(frozen=True)
class FilterOptions:
    """The values offered by the explorer's filters."""

    types: tuple[str, ...]
    oa_statuses: tuple[str, ...]
    venues: tuple[str, ...]
    sources: tuple[str, ...]


def is_available(db_path: Path) -> bool:
    """Return True when the research mart exists and has at least one publication."""
    try:
        return _fetch(db_path, "SELECT count(*) FROM marts.fact_publication")[0][0] > 0
    except MartUnavailableError:
        return False


def year_bounds(db_path: Path) -> YearRange:
    """Return the earliest and latest publication year in the mart."""
    row = _fetch(db_path, "SELECT min(year), max(year) FROM marts.dim_year")[0]
    if row[0] is None:
        raise MartUnavailableError("The research mart has no publications")
    return YearRange(int(row[0]), int(row[1]))


def headline_counts(db_path: Path, years: YearRange) -> HeadlineCounts:
    """Return publication, open-access, citation and venue counts for ``years``."""
    row = _fetch(
        db_path,
        """
        SELECT
            count(*),
            count(*) FILTER (WHERE f.is_oa),
            coalesce(sum(f.cited_by_count), 0),
            count(DISTINCT v.venue_id)
        FROM marts.fact_publication AS f
        JOIN marts.dim_venue AS v USING (venue_key)
        WHERE f.year_key BETWEEN ? AND ?
        """,
        [years.start, years.end],
    )[0]
    return HeadlineCounts(
        publications=int(row[0]),
        open_access_publications=int(row[1]),
        citations=int(row[2]),
        venues=int(row[3]),
    )


def publications_per_year(db_path: Path, years: YearRange) -> list[YearCount]:
    """Return publications per year for ``years``, including years with none."""
    rows = _fetch(
        db_path,
        """
        SELECT y.year, count(f.publication_key)
        FROM marts.dim_year AS y
        LEFT JOIN marts.fact_publication AS f ON f.year_key = y.year_key
        WHERE y.year BETWEEN ? AND ?
        GROUP BY y.year
        ORDER BY y.year
        """,
        [years.start, years.end],
    )
    return [YearCount(int(year), int(count)) for year, count in rows]


def oa_share_per_year(db_path: Path, years: YearRange) -> list[YearOpenAccess]:
    """Return open-access publication counts per year for ``years``."""
    rows = _fetch(
        db_path,
        """
        SELECT
            y.year,
            count(f.publication_key),
            count(f.publication_key) FILTER (WHERE f.is_oa)
        FROM marts.dim_year AS y
        LEFT JOIN marts.fact_publication AS f ON f.year_key = y.year_key
        WHERE y.year BETWEEN ? AND ?
        GROUP BY y.year
        ORDER BY y.year
        """,
        [years.start, years.end],
    )
    return [YearOpenAccess(int(year), int(total), int(oa)) for year, total, oa in rows]


def top_venues(db_path: Path, years: YearRange, limit: int = 10) -> list[VenueCount]:
    """Return the venues with most publications in ``years`` (unknown venues excluded)."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    rows = _fetch(
        db_path,
        """
        SELECT v.venue_name, count(*) AS publications, coalesce(sum(f.cited_by_count), 0)
        FROM marts.fact_publication AS f
        JOIN marts.dim_venue AS v USING (venue_key)
        WHERE f.year_key BETWEEN ? AND ?
          AND v.venue_id IS NOT NULL
        GROUP BY v.venue_key, v.venue_name
        ORDER BY publications DESC, sum(f.cited_by_count) DESC, v.venue_name
        LIMIT ?
        """,
        [years.start, years.end, limit],
    )
    return [VenueCount(str(name), int(count), int(cites)) for name, count, cites in rows]


def filter_options(db_path: Path, max_venues: int = 500) -> FilterOptions:
    """Return the values the explorer's filters offer (venues: the busiest ``max_venues``)."""
    types = _fetch(
        db_path,
        """
        SELECT DISTINCT t.type_label
        FROM marts.fact_publication AS f
        JOIN marts.dim_publication_type AS t USING (type_key)
        ORDER BY t.type_label
        """,
    )
    statuses = _fetch(
        db_path, "SELECT DISTINCT oa_status FROM marts.fact_publication ORDER BY oa_status"
    )
    venues = _fetch(
        db_path,
        """
        SELECT v.venue_name
        FROM marts.fact_publication AS f
        JOIN marts.dim_venue AS v USING (venue_key)
        WHERE v.venue_id IS NOT NULL
        GROUP BY v.venue_key, v.venue_name
        ORDER BY count(*) DESC, v.venue_name
        LIMIT ?
        """,
        [max_venues],
    )
    return FilterOptions(
        types=tuple(r[0] for r in types),
        oa_statuses=tuple(r[0] for r in statuses),
        venues=tuple(r[0] for r in venues),
        sources=tuple(SOURCE_FLAGS),
    )


def _publication_where(filters: PublicationFilter) -> tuple[str, list[Any]]:
    """Build the WHERE clause and its parameters from ``filters`` (values never in the SQL)."""
    clauses: list[str] = []
    params: list[Any] = []
    if filters.years is not None:
        clauses.append("f.year_key BETWEEN ? AND ?")
        params += [filters.years.start, filters.years.end]
    for column, values in (
        ("t.type_label", filters.types),
        ("f.oa_status", filters.oa_statuses),
        ("v.venue_name", filters.venues),
    ):
        if values:
            clauses.append(f"{column} IN ({', '.join('?' for _ in values)})")
            params += list(values)
    if filters.sources:
        unknown = [s for s in filters.sources if s not in SOURCE_FLAGS]
        if unknown:
            raise ValueError(f"Unknown source(s): {', '.join(unknown)}")
        flags = " OR ".join(f"f.{SOURCE_FLAGS[s]}" for s in filters.sources)
        clauses.append(f"({flags})")
    search = filters.search.strip()
    if search:
        clauses.append("(p.title ILIKE ? ESCAPE '\\' OR p.doi ILIKE ? ESCAPE '\\')")
        pattern = "%" + search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_") + "%"
        params += [pattern, pattern]
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


_PUBLICATIONS_FROM = """
    FROM marts.fact_publication AS f
    JOIN marts.dim_publication AS p USING (publication_key)
    JOIN marts.dim_venue AS v USING (venue_key)
    JOIN marts.dim_publication_type AS t USING (type_key)
"""


def count_publications(db_path: Path, filters: PublicationFilter) -> int:
    """Return how many publications match ``filters``."""
    where, params = _publication_where(filters)
    return int(_fetch(db_path, f"SELECT count(*) {_PUBLICATIONS_FROM} {where}", params)[0][0])


def publications(
    db_path: Path,
    filters: PublicationFilter,
    limit: int | None = 100,
    offset: int = 0,
) -> list[PublicationRow]:
    """Return publications matching ``filters``, newest and most cited first.

    Pass ``limit=None`` to return every matching row (used for CSV export).
    """
    if limit is not None and limit < 0:
        raise ValueError("limit must not be negative")
    if offset < 0:
        raise ValueError("offset must not be negative")
    where, params = _publication_where(filters)
    paging = ""
    if limit is not None:
        paging = " LIMIT ? OFFSET ?"
        params += [limit, offset]
    rows = _fetch(
        db_path,
        f"""
        SELECT
            p.title, f.year_key, t.type_label, v.venue_name, f.oa_status,
            f.cited_by_count, f.n_authors,
            concat_ws(', ',
                CASE WHEN f.in_openalex THEN 'OpenAlex' END,
                CASE WHEN f.in_repository THEN 'Repository' END,
                CASE WHEN f.in_ojs THEN 'OJS' END),
            p.doi, p.doi_url, p.primary_record_url
        {_PUBLICATIONS_FROM}
        {where}
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
            sources=r[7],
            doi=r[8],
            doi_url=r[9],
            record_url=r[10],
        )
        for r in rows
    ]


def publications_to_csv(rows: Sequence[PublicationRow]) -> str:
    """Return ``rows`` as CSV text with a header row, ready for download."""
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(header for _, header in PUBLICATION_COLUMNS)
    for row in rows:
        writer.writerow(_csv_safe(getattr(row, name)) for name, _ in PUBLICATION_COLUMNS)
    return buffer.getvalue()


def _csv_safe(value: object) -> object:
    """Prefix text that a spreadsheet could run as a formula, and show None as empty."""
    if value is None:
        return ""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value
