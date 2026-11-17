"""Read-only queries on the research mart for the Next.js front end.

Same rules as :mod:`ihub.mart.research`: no SQL outside ``ihub.mart``, every function takes the
DuckDB path first, opens its own read-only connection and returns plain, typed values, and
every user-supplied value is a query parameter.

Organisations follow ADR-004: UNZA authorships sit at department level (or centre, institute,
directorate, library, or "Unassigned department"), so a school's total is every distinct
publication with an authorship in one of its units. A publication with authors in two schools
counts once in each, so school totals add up to more than the number of publications.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from ihub.mart._duckdb import MartUnavailableError, fetch
from ihub.mart.research import YearRange

#: The taxonomy levels :func:`top_themes` can group by, mapped to their ``dim_topic`` column.
THEME_LEVELS: dict[str, str] = {
    "domain": "domain_name",
    "field": "field_name",
    "subfield": "subfield_name",
    "topic": "topic_name",
}

UNASSIGNED_UNIT = "Unassigned department"


@dataclass(frozen=True)
class VenueSummary:
    """Publications, citations and open access for one venue (journal, repository set...)."""

    venue: str
    publications: int
    open_access_publications: int
    citations: int

    @property
    def open_access_share(self) -> float:
        """Share of the venue's publications that are open access, from 0 to 1."""
        return self.open_access_publications / self.publications if self.publications else 0.0


@dataclass(frozen=True)
class ThemeCount:
    """Publications tagged with one topic-taxonomy value."""

    name: str
    publications: int


@dataclass(frozen=True)
class FieldTopics:
    """A research field, its publication count and its busiest topics."""

    field: str
    publications: int
    topics: tuple[ThemeCount, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class SchoolOutput:
    """Distinct publications with at least one authorship in a school's units."""

    school: str
    publications: int


@dataclass(frozen=True)
class UnitOutput:
    """Distinct publications with at least one authorship in one UNZA unit."""

    name: str
    unit_type: str
    school: str | None
    publications: int


@dataclass(frozen=True)
class CollaborationSummary:
    """Headline numbers for collaboration in a period."""

    international_publications: int
    partner_organisations: int
    countries: int
    publications_with_unknown_country: int


@dataclass(frozen=True)
class CountryCount:
    """Publications with at least one author at an institution in one country."""

    country_code: str
    publications: int


@dataclass(frozen=True)
class PartnerCount:
    """Publications with at least one author at one external institution."""

    name: str
    country_code: str | None
    publications: int


@dataclass(frozen=True)
class AuthorCredit:
    """One author of a publication, in author order."""

    name: str
    orcid_url: str | None
    is_unza_author: bool


@dataclass(frozen=True)
class SourceRecord:
    """One source record that was merged into a publication."""

    source: str
    url: str | None
    match_rule: str | None


@dataclass(frozen=True)
class PublicationDetail:
    """Everything the mart knows about one de-duplicated publication."""

    key: str
    title: str
    year: int
    type: str
    venue: str
    oa_status: str
    cited_by_count: int
    n_authors: int
    doi: str | None
    doi_url: str | None
    authors: tuple[AuthorCredit, ...]
    sources: tuple[SourceRecord, ...]
    units: tuple[str, ...]


def venue_directory(db_path: Path, years: YearRange, limit: int = 50) -> list[VenueSummary]:
    """Return the busiest venues in ``years`` (unknown venues excluded), with open access."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    rows = fetch(
        db_path,
        """
        SELECT v.venue_name, count(*), count(*) FILTER (WHERE f.is_oa),
               coalesce(sum(f.cited_by_count), 0)
        FROM marts.fact_publication AS f
        JOIN marts.dim_venue AS v USING (venue_key)
        WHERE f.year_key BETWEEN ? AND ? AND v.venue_id IS NOT NULL
        GROUP BY v.venue_key, v.venue_name
        ORDER BY count(*) DESC, v.venue_name
        LIMIT ?
        """,
        [years.start, years.end, limit],
    )
    return [VenueSummary(str(n), int(p), int(oa), int(c)) for n, p, oa, c in rows]


def top_themes(
    db_path: Path, years: YearRange, level: str = "field", limit: int = 10
) -> list[ThemeCount]:
    """Return the most common topic-taxonomy values at ``level`` in ``years``.

    Topics come from OpenAlex only. One publication can carry several topics, so the counts
    overlap and must not be added together.
    """
    if level not in THEME_LEVELS:
        raise ValueError(f"Unknown theme level: {level}")
    if limit < 1:
        raise ValueError("limit must be at least 1")
    column = THEME_LEVELS[level]  # from the fixed mapping above, never from the caller
    rows = fetch(
        db_path,
        f"""
        SELECT t.{column}, count(DISTINCT b.publication_key) AS publications
        FROM marts.bridge_publication_topic AS b
        JOIN marts.dim_topic AS t USING (topic_key)
        JOIN marts.fact_publication AS f USING (publication_key)
        WHERE f.year_key BETWEEN ? AND ? AND t.{column} IS NOT NULL
        GROUP BY t.{column}
        ORDER BY publications DESC, t.{column}
        LIMIT ?
        """,  # noqa: S608
        [years.start, years.end, limit],
    )
    return [ThemeCount(str(name), int(count)) for name, count in rows]


def fields_with_topics(
    db_path: Path, years: YearRange, fields: int = 6, topics_per_field: int = 4
) -> list[FieldTopics]:
    """Return the busiest research fields, each with its busiest topics."""
    result: list[FieldTopics] = []
    for theme in top_themes(db_path, years, level="field", limit=fields):
        rows = fetch(
            db_path,
            """
            SELECT t.topic_name, count(DISTINCT b.publication_key) AS publications
            FROM marts.bridge_publication_topic AS b
            JOIN marts.dim_topic AS t USING (topic_key)
            JOIN marts.fact_publication AS f USING (publication_key)
            WHERE f.year_key BETWEEN ? AND ? AND t.field_name = ?
            GROUP BY t.topic_name
            ORDER BY publications DESC, t.topic_name
            LIMIT ?
            """,
            [years.start, years.end, theme.name, topics_per_field],
        )
        result.append(
            FieldTopics(
                theme.name,
                theme.publications,
                tuple(ThemeCount(str(n), int(c)) for n, c in rows),
            )
        )
    return result


UNIT_LABEL_SQL = f"""
    CASE
        WHEN o.org_type = 'unassigned' THEN '{UNASSIGNED_UNIT}'
        ELSE coalesce(o.school_name, o.org_name)
    END
"""


def school_outputs(db_path: Path, years: YearRange) -> list[SchoolOutput]:
    """Return, per school, the distinct publications with an authorship in its units.

    Units with no school (the library, "Unassigned department") appear under their own name.
    """
    rows = fetch(
        db_path,
        f"""
        SELECT {UNIT_LABEL_SQL} AS school, count(DISTINCT a.publication_key) AS publications
        FROM marts.fact_authorship AS a
        JOIN marts.dim_org AS o USING (org_key)
        WHERE o.org_kind = 'unza_unit' AND a.year_key BETWEEN ? AND ?
        GROUP BY school
        ORDER BY publications DESC, school
        """,  # noqa: S608
        [years.start, years.end],
    )
    return [SchoolOutput(str(school), int(count)) for school, count in rows]


def unit_outputs(db_path: Path, years: YearRange) -> list[UnitOutput]:
    """Return, per UNZA unit with at least one publication in ``years``, its distinct count."""
    rows = fetch(
        db_path,
        """
        SELECT o.org_name, o.org_type, o.school_name, count(DISTINCT a.publication_key)
        FROM marts.fact_authorship AS a
        JOIN marts.dim_org AS o USING (org_key)
        WHERE o.org_kind = 'unza_unit' AND a.year_key BETWEEN ? AND ?
        GROUP BY o.org_key, o.org_name, o.org_type, o.school_name
        ORDER BY count(DISTINCT a.publication_key) DESC, o.org_name
        """,
        [years.start, years.end],
    )
    return [UnitOutput(str(n), str(t), s, int(c)) for n, t, s, c in rows]


def collaboration_summary(db_path: Path, years: YearRange) -> CollaborationSummary:
    """Return the headline collaboration numbers for ``years``.

    ``international_publications`` counts only publications where OpenAlex gave affiliations
    (an unknown value is not counted as international).
    """
    international = fetch(
        db_path,
        "SELECT count(*) FROM marts.fact_publication "
        "WHERE is_international_collab AND year_key BETWEEN ? AND ?",
        [years.start, years.end],
    )[0][0]
    row = fetch(
        db_path,
        """
        SELECT count(DISTINCT o.org_key),
               count(DISTINCT o.country_code),
               count(DISTINCT a.publication_key) FILTER (WHERE o.country_code IS NULL)
        FROM marts.fact_authorship AS a
        JOIN marts.dim_org AS o USING (org_key)
        WHERE o.org_kind = 'external' AND a.year_key BETWEEN ? AND ?
        """,
        [years.start, years.end],
    )[0]
    return CollaborationSummary(int(international), int(row[0]), int(row[1]), int(row[2]))


def top_countries(db_path: Path, years: YearRange, limit: int = 12) -> list[CountryCount]:
    """Return the countries of external institutions that co-author with UNZA the most."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    rows = fetch(
        db_path,
        """
        SELECT o.country_code, count(DISTINCT a.publication_key) AS publications
        FROM marts.fact_authorship AS a
        JOIN marts.dim_org AS o USING (org_key)
        WHERE o.org_kind = 'external' AND o.country_code IS NOT NULL
          AND a.year_key BETWEEN ? AND ?
        GROUP BY o.country_code
        ORDER BY publications DESC, o.country_code
        LIMIT ?
        """,
        [years.start, years.end, limit],
    )
    return [CountryCount(str(code), int(count)) for code, count in rows]


def top_partners(db_path: Path, years: YearRange, limit: int = 10) -> list[PartnerCount]:
    """Return the external institutions that co-author with UNZA the most."""
    if limit < 1:
        raise ValueError("limit must be at least 1")
    rows = fetch(
        db_path,
        """
        SELECT o.org_name, o.country_code, count(DISTINCT a.publication_key) AS publications
        FROM marts.fact_authorship AS a
        JOIN marts.dim_org AS o USING (org_key)
        WHERE o.org_kind = 'external' AND a.year_key BETWEEN ? AND ?
        GROUP BY o.org_key, o.org_name, o.country_code
        ORDER BY publications DESC, o.org_name
        LIMIT ?
        """,
        [years.start, years.end, limit],
    )
    return [PartnerCount(str(n), c, int(p)) for n, c, p in rows]


def publication_detail(db_path: Path, publication_key: str) -> PublicationDetail | None:
    """Return one publication with its authors, source records and UNZA units, or None."""
    head = fetch(
        db_path,
        """
        SELECT p.publication_key, p.title, f.year_key, t.type_label, v.venue_name, f.oa_status,
               f.cited_by_count, f.n_authors, p.doi, p.doi_url
        FROM marts.fact_publication AS f
        JOIN marts.dim_publication AS p USING (publication_key)
        JOIN marts.dim_venue AS v USING (venue_key)
        JOIN marts.dim_publication_type AS t USING (type_key)
        WHERE p.publication_key = ?
        """,
        [publication_key],
    )
    if not head:
        return None
    key, title, year, type_label, venue, oa, cites, n_authors, doi, doi_url = head[0]
    authors = fetch(
        db_path,
        """
        SELECT d.author_name, d.orcid_url, d.is_unza_author
        FROM marts.fact_authorship AS a
        JOIN marts.dim_author AS d USING (author_key)
        WHERE a.publication_key = ?
        GROUP BY d.author_key, d.author_name, d.orcid_url, d.is_unza_author
        ORDER BY min(a.author_position), d.author_name
        LIMIT 100
        """,
        [publication_key],
    )
    sources = fetch(
        db_path,
        """
        SELECT s.source_name, b.source_url, b.match_rule
        FROM marts.bridge_publication_source AS b
        JOIN marts.dim_source_system AS s USING (source_system_key)
        WHERE b.publication_key = ?
        ORDER BY s.source_name, b.source_record_id
        """,
        [publication_key],
    )
    units = fetch(
        db_path,
        f"""
        SELECT DISTINCT {UNIT_LABEL_SQL} AS unit
        FROM marts.fact_authorship AS a
        JOIN marts.dim_org AS o USING (org_key)
        WHERE a.publication_key = ? AND o.org_kind = 'unza_unit'
        ORDER BY unit
        """,  # noqa: S608
        [publication_key],
    )
    return PublicationDetail(
        key=str(key),
        title=str(title),
        year=int(year),
        type=str(type_label),
        venue=str(venue),
        oa_status=str(oa),
        cited_by_count=int(cites),
        n_authors=int(n_authors),
        doi=doi,
        doi_url=doi_url,
        authors=tuple(AuthorCredit(str(n), u, bool(z)) for n, u, z in authors),
        sources=tuple(SourceRecord(str(s), u, m) for s, u, m in sources),
        units=tuple(str(u[0]) for u in units),
    )


__all__ = [
    "THEME_LEVELS",
    "UNASSIGNED_UNIT",
    "UNIT_LABEL_SQL",
    "AuthorCredit",
    "CollaborationSummary",
    "CountryCount",
    "FieldTopics",
    "MartUnavailableError",
    "PartnerCount",
    "PublicationDetail",
    "SchoolOutput",
    "SourceRecord",
    "ThemeCount",
    "UnitOutput",
    "VenueSummary",
    "collaboration_summary",
    "fields_with_topics",
    "publication_detail",
    "school_outputs",
    "top_countries",
    "top_partners",
    "top_themes",
    "unit_outputs",
    "venue_directory",
]
