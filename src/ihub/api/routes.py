"""HTTP routes. Each one parses its query, calls ``ihub.mart`` and returns plain JSON."""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from ihub.mart import coverage, insights, research
from ihub.mart.research import PublicationFilter, YearRange
from ihub.mart.status import last_pipeline_run
from ihub.staff import attribution

MAX_PAGE_SIZE = 100
PREVIEW_ROWS = 10

Start = Annotated[int | None, Query(description="First publication year (default: earliest)")]
End = Annotated[int | None, Query(description="Last publication year (default: latest)")]
Types = Annotated[list[str] | None, Query(alias="type")]
Statuses = Annotated[list[str] | None, Query(alias="oa_status")]
Venues = Annotated[list[str] | None, Query(alias="venue")]
Sources = Annotated[list[str] | None, Query(alias="source")]


def _share(part: int, whole: int) -> float:
    return part / whole if whole else 0.0


def _headline(counts: research.HeadlineCounts) -> dict[str, Any]:
    return {**asdict(counts), "open_access_share": counts.open_access_share}


def build_router(
    database_path: Callable[[], Path],
    *,
    read: Sequence[Any] = (),
    export: Sequence[Any] = (),
    staff_roster_path: Callable[[], Path | None] | None = None,
) -> APIRouter:
    """Create the router; ``database_path`` is called per request so tests can swap the file.

    ``/api/health`` is always public (Cloud Run's probes call it). ``read`` dependencies
    guard every data route and ``export`` the CSV export as well (ADR-010): the app passes
    ``require(research:read)`` and ``require(research:export)`` when sign-in is required.
    """
    router = APIRouter(prefix="/api")

    def school_credit(db: Path, years: YearRange, total_publications: int) -> dict[str, Any] | None:
        """Schools credited through the private staff roster (ADR-012), or None without one.

        The payload holds school-level numbers and match statistics only: never a name, a staff
        ID or a per-person result.
        """
        roster = staff_roster_path() if staff_roster_path else None
        if roster is None:
            return None
        report = attribution.school_credit(db, roster, years, total_publications)
        if report is None:
            return None
        return {
            "source": "staff_roster",
            "total_publications": report.total_publications,
            "credited_by_roster": report.credited_by_roster,
            "credited_any": report.credited_any,
            "schools": [asdict(school) for school in report.schools],
            "stats": asdict(report.stats),
        }

    data = APIRouter(dependencies=list(read))

    def years_from(start: int | None, end: int | None) -> YearRange:
        """Fill the open ends from the mart's year bounds."""
        bounds = research.year_bounds(database_path())
        return YearRange(
            bounds.start if start is None else start, bounds.end if end is None else end
        )

    @router.get("/health")
    def health() -> dict[str, Any]:
        """Report whether the mart is readable and when the pipeline last ran."""
        db = database_path()
        last_run = last_pipeline_run(db)
        return {
            "status": "ok",
            "mart_available": research.is_available(db),
            "last_pipeline_run": last_run.isoformat() if last_run else None,
        }

    @data.get("/filters")
    def filters() -> dict[str, Any]:
        """Return the values the global filters can offer."""
        db = database_path()
        options = research.filter_options(db)
        bounds = research.year_bounds(db)
        schools = [s.school for s in insights.school_outputs(db, bounds)]
        return {
            "years": asdict(bounds),
            "types": options.types,
            "oa_statuses": options.oa_statuses,
            "sources": options.sources,
            "schools": schools,
        }

    @data.get("/overview")
    def overview(start: Start = None, end: End = None) -> dict[str, Any]:
        """Headline numbers, trends, top venues, schools and collaboration for a period."""
        db = database_path()
        years = years_from(start, end)
        bounds = research.year_bounds(db)
        current = research.headline_counts(db, years)
        previous_years = years.previous_period()
        has_previous = previous_years.start >= bounds.start
        previous = research.headline_counts(db, previous_years) if has_previous else None
        return {
            "years": asdict(years),
            "previous_years": asdict(previous_years) if has_previous else None,
            "headline": _headline(current),
            "previous_headline": _headline(previous) if previous else None,
            "per_year": [asdict(y) for y in research.publications_per_year(db, years)],
            "oa_per_year": [
                {**asdict(y), "open_access_share": y.open_access_share}
                for y in research.oa_share_per_year(db, years)
            ],
            "top_venues": [asdict(v) for v in research.top_venues(db, years, limit=5)],
            "schools": [asdict(s) for s in insights.school_outputs(db, years)],
            "school_credit": school_credit(db, years, current.publications),
            "collaboration": {
                "summary": asdict(insights.collaboration_summary(db, years)),
                "countries": [asdict(c) for c in insights.top_countries(db, years, limit=8)],
            },
            "missing_from_repository": coverage.count_missing(db, "openalex", "dspace_oai", years),
        }

    def publication_filter(
        years: YearRange,
        type_: list[str] | None,
        oa_status: list[str] | None,
        venue: list[str] | None,
        source: list[str] | None,
        q: str,
    ) -> PublicationFilter:
        return PublicationFilter(
            years=years,
            types=tuple(type_ or ()),
            oa_statuses=tuple(oa_status or ()),
            venues=tuple(venue or ()),
            sources=tuple(source or ()),
            search=q,
        )

    @data.get("/publications")
    def publication_list(
        start: Start = None,
        end: End = None,
        type_: Types = None,
        oa_status: Statuses = None,
        venue: Venues = None,
        source: Sources = None,
        q: str = "",
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 10,
    ) -> dict[str, Any]:
        """One page of de-duplicated publications matching the filters."""
        db = database_path()
        selected = publication_filter(years_from(start, end), type_, oa_status, venue, source, q)
        total = research.count_publications(db, selected)
        rows = research.publications(db, selected, limit=page_size, offset=(page - 1) * page_size)
        return {
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(1, math.ceil(total / page_size)),
            "rows": [asdict(row) for row in rows],
        }

    @data.get("/publications/export", dependencies=list(export))
    def publication_export(
        start: Start = None,
        end: End = None,
        type_: Types = None,
        oa_status: Statuses = None,
        venue: Venues = None,
        source: Sources = None,
        q: str = "",
    ) -> Response:
        """Every publication matching the filters, as a CSV download."""
        db = database_path()
        selected = publication_filter(years_from(start, end), type_, oa_status, venue, source, q)
        rows = research.publications(db, selected, limit=None)
        return Response(
            research.publications_to_csv(rows),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="ihub-publications.csv"'},
        )

    @data.get("/publications/{publication_key}")
    def publication(publication_key: str) -> dict[str, Any]:
        """One publication with its authors, source records and UNZA units."""
        detail = insights.publication_detail(database_path(), publication_key)
        if detail is None:
            raise HTTPException(status_code=404, detail="Publication not found")
        return asdict(detail)

    @data.get("/journals")
    def journals(start: Start = None, end: End = None, limit: int = 50) -> dict[str, Any]:
        """The busiest venues, with open-access share, for a period."""
        db = database_path()
        years = years_from(start, end)
        venues = insights.venue_directory(db, years, limit=limit)
        counts = research.headline_counts(db, years)
        return {
            "years": asdict(years),
            "venues_in_period": counts.venues,
            "venues": [{**asdict(v), "open_access_share": v.open_access_share} for v in venues],
        }

    @data.get("/topics")
    def topics(start: Start = None, end: End = None) -> dict[str, Any]:
        """Research fields with their busiest topics (OpenAlex classifications)."""
        db = database_path()
        years = years_from(start, end)
        return {
            "years": asdict(years),
            "fields": [asdict(f) for f in insights.fields_with_topics(db, years)],
        }

    @data.get("/organisation")
    def organisation(start: Start = None, end: End = None) -> dict[str, Any]:
        """Output per school and per UNZA unit for a period."""
        db = database_path()
        years = years_from(start, end)
        total = research.headline_counts(db, years).publications
        return {
            "years": asdict(years),
            "total_publications": total,
            "schools": [asdict(s) for s in insights.school_outputs(db, years)],
            "school_credit": school_credit(db, years, total),
            "units": [asdict(u) for u in insights.unit_outputs(db, years)],
        }

    @data.get("/collaboration")
    def collaboration(start: Start = None, end: End = None) -> dict[str, Any]:
        """Collaboration summary, countries and partner institutions for a period."""
        db = database_path()
        years = years_from(start, end)
        return {
            "years": asdict(years),
            "summary": asdict(insights.collaboration_summary(db, years)),
            "countries": [asdict(c) for c in insights.top_countries(db, years, limit=15)],
            "partners": [asdict(p) for p in insights.top_partners(db, years, limit=10)],
        }

    @data.get("/coverage")
    def source_coverage(start: Start = None, end: End = None) -> dict[str, Any]:
        """Per-source totals and the librarians' coverage gaps, with a short preview of each."""
        db = database_path()
        years = years_from(start, end)
        totals = coverage.source_totals(db, years)
        corpus = research.headline_counts(db, years).publications
        gaps = []
        for gap in coverage.COVERAGE_GAPS:
            gaps.append(
                {
                    **asdict(gap),
                    "count": coverage.count_missing(db, gap.in_source, gap.missing_from, years),
                    "rows": [
                        asdict(r)
                        for r in coverage.missing_publications(
                            db, gap.in_source, gap.missing_from, years, limit=PREVIEW_ROWS
                        )
                    ],
                }
            )
        return {
            "years": asdict(years),
            "publications": corpus,
            "sources": [
                {
                    "code": t.source.code,
                    "name": t.source.name,
                    "kind": t.source.kind,
                    "publications": t.publications,
                    "share": _share(t.publications, corpus),
                }
                for t in totals
            ],
            "gaps": gaps,
        }

    @data.get("/sources")
    def sources() -> dict[str, Any]:
        """The connected sources, how many publications each holds, and the last pipeline run."""
        db = database_path()
        years = research.year_bounds(db)
        last_run = last_pipeline_run(db)
        return {
            "last_pipeline_run": last_run.isoformat() if last_run else None,
            "publications": research.headline_counts(db, years).publications,
            "sources": [
                {
                    "code": t.source.code,
                    "name": t.source.name,
                    "kind": t.source.kind,
                    "publications": t.publications,
                }
                for t in coverage.source_totals(db, years)
            ],
        }

    router.include_router(data)
    return router
