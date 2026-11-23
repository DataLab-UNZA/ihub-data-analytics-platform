"""Members routes: roster staff matched to their publications (ADR-014).

Every route needs ``members:read`` when sign-in is on, because these are named individuals.
The list is always A to Z by name: individuals are never ranked. Without a roster file the
routes answer "not available" and list nobody.
"""

from __future__ import annotations

import math
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query

from ihub.mart import members as member_queries
from ihub.mart import research
from ihub.mart.research import PublicationFilter, YearRange
from ihub.staff import members as staff_members

Types = Annotated[list[str] | None, Query(alias="type")]
Sources = Annotated[list[str] | None, Query(alias="source")]
Start = Annotated[int | None, Query(description="First publication year (default: earliest)")]
End = Annotated[int | None, Query(description="Last publication year (default: latest)")]
MAX_PAGE_SIZE = 100


@dataclass(frozen=True)
class Summary:
    """A member with their ORCID iD and publication totals for a period."""

    record: staff_members.MemberRecord
    orcid: str | None
    publication_keys: frozenset[str]
    open_access: int
    citations: int

    def as_row(self) -> dict[str, Any]:
        """The fields shared by the directory row and the profile header."""
        return {
            "member_id": self.record.member_id,
            "title": self.record.title,
            "name": self.record.name,
            "school": self.record.school,
            "orcid": self.orcid,
            "orcid_url": f"https://orcid.org/{self.orcid}" if self.orcid else None,
            "publications": len(self.publication_keys),
        }


def _summaries(db: Path, roster: Path, selected: PublicationFilter) -> list[Summary] | None:
    """Totals per member over the publications matching ``selected`` (period, source, type)."""
    years = selected.years or research.year_bounds(db)
    records = staff_members.directory(db, roster)
    if records is None:
        return None
    every_author = [key for record in records for key in record.author_keys]
    orcids = member_queries.author_orcids(db, every_author)
    allowed = research.matching_keys(db, selected)
    facts: dict[str, dict[str, tuple[bool, int]]] = {}
    for author, publication, is_oa, cited in member_queries.author_publication_facts(
        db, every_author, years
    ):
        if publication in allowed:
            facts.setdefault(author, {})[publication] = (is_oa, cited)
    summaries = []
    for record in records:
        merged: dict[str, tuple[bool, int]] = {}
        for author in record.author_keys:
            merged.update(facts.get(author, {}))
        summaries.append(
            Summary(
                record=record,
                orcid=next((orcids[a] for a in record.author_keys if a in orcids), None),
                publication_keys=frozenset(merged),
                open_access=sum(1 for is_oa, _ in merged.values() if is_oa),
                citations=sum(cited for _, cited in merged.values()),
            )
        )
    return summaries


def build_members_router(
    database_path: Callable[[], Path],
    staff_roster_path: Callable[[], Path | None],
    *,
    read: Sequence[Any] = (),
) -> APIRouter:
    """Create the router; ``read`` holds the ``members:read`` dependency when sign-in is on."""
    router = APIRouter(prefix="/api", dependencies=list(read))

    def years_from(start: int | None, end: int | None) -> YearRange:
        bounds = research.year_bounds(database_path())
        return YearRange(
            bounds.start if start is None else start, bounds.end if end is None else end
        )

    def selection(
        start: int | None, end: int | None, type_: list[str] | None, source: list[str] | None
    ) -> PublicationFilter:
        """The global filters as one publication filter, shared with the publication list."""
        return PublicationFilter(
            years=years_from(start, end), types=tuple(type_ or ()), sources=tuple(source or ())
        )

    def summaries(selected: PublicationFilter) -> list[Summary] | None:
        roster = staff_roster_path()
        return _summaries(database_path(), roster, selected) if roster else None

    @router.get("/members")
    def members(
        start: Start = None,
        end: End = None,
        type_: Types = None,
        source: Sources = None,
        q: str = "",
        unit: str = "",
        orcid: Annotated[str, Query(pattern="^(|linked|unknown)$")] = "",
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
    ) -> dict[str, Any]:
        """Matched staff, A to Z, with ORCID and counts for the period, source and type.

        Only members with at least one publication under those filters are listed, so the
        filters visibly change who is shown.
        """
        found = summaries(selection(start, end, type_, source))
        if found is None:
            return {"available": False, "total": 0, "page": 1, "pages": 1, "units": [], "rows": []}
        units = sorted({s.record.school for s in found if s.record.school})
        words = q.casefold().split()  # every word must appear in the title or the name
        chosen = [
            s
            for s in found
            if s.publication_keys
            and all(word in f"{s.record.title} {s.record.name}".casefold() for word in words)
            and (not unit or s.record.school == unit)
            and (orcid != "linked" or s.orcid)
            and (orcid != "unknown" or not s.orcid)
        ]
        first = (page - 1) * page_size
        return {
            "available": True,
            "total": len(chosen),
            "page": page,
            "page_size": page_size,
            "pages": max(1, math.ceil(len(chosen) / page_size)),
            "units": units,
            "rows": [s.as_row() for s in chosen[first : first + page_size]],
        }

    @router.get("/members/{member_id}")
    def member(
        member_id: str,
        start: Start = None,
        end: End = None,
        type_: Types = None,
        source: Sources = None,
        page: Annotated[int, Query(ge=1)] = 1,
        page_size: Annotated[int, Query(ge=1, le=MAX_PAGE_SIZE)] = 20,
    ) -> dict[str, Any]:
        """One staff member with their linked publications (newest first) for the filters."""
        chosen = selection(start, end, type_, source)
        found = summaries(chosen)
        summary = next((s for s in found or () if s.record.member_id == member_id), None)
        if summary is None:
            raise HTTPException(status_code=404, detail="Member not found")
        selected = replace(chosen, publication_keys=summary.publication_keys)
        db = database_path()
        total = research.count_publications(db, selected)
        rows = research.publications(db, selected, limit=page_size, offset=(page - 1) * page_size)
        return {
            "member": {
                **summary.as_row(),
                "open_access": summary.open_access,
                "citations": summary.citations,
            },
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": max(1, math.ceil(total / page_size)),
            "rows": [asdict(row) for row in rows],
        }

    return router
