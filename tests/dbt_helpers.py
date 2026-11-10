"""Helpers for tests that build dbt models from raw records in a temporary DuckDB file."""

from __future__ import annotations

import copy
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
from dbt.cli.main import dbtRunner

from ihub.connectors.base import RawRecord
from ihub.ingest.raw import write_raw

ROOT = Path(__file__).resolve().parent.parent
TRANSFORM = ROOT / "transform"
SAMPLE = ROOT / "tests" / "fixtures" / "openalex_works_sample.json"


def sample_works() -> list[dict[str, Any]]:
    """Return the recorded OpenAlex sample (two real works)."""
    return json.loads(SAMPLE.read_text(encoding="utf-8"))["results"]


def make_work(
    work_id: str,
    *,
    title: str | None = "A study of things",
    doi: str | None = None,
    year: int = 2020,
    work_type: str = "article",
    venue_id: str | None = "S1",
    venue_name: str | None = "Journal One",
    is_oa: bool = False,
    oa_status: str = "closed",
    cited_by_count: int = 0,
    n_authors: int = 1,
) -> dict[str, Any]:
    """Build a minimal OpenAlex work from the recorded sample's shape, overriding fields."""
    work = copy.deepcopy(sample_works()[0])
    work["id"] = f"https://openalex.org/{work_id}"
    work["title"] = title
    work["doi"] = doi
    work["publication_year"] = year
    work["type"] = work_type
    work["open_access"] = {"is_oa": is_oa, "oa_status": oa_status}
    work["cited_by_count"] = cited_by_count
    work["authorships"] = [
        {"author": {"id": f"https://openalex.org/A{i}"}} for i in range(n_authors)
    ]
    work["primary_location"] = (
        {"source": {"id": f"https://openalex.org/{venue_id}", "display_name": venue_name}}
        if venue_id
        else None
    )
    return work


def build_warehouse(
    db: Path, works: list[dict[str, Any]], select: str = "+path:models/marts/research"
) -> Path:
    """Load ``works`` into raw_openalex and run ``dbt build`` for ``select``. Return ``db``.

    Works are loaded in order, each fetched one second after the one before, so when the same
    work appears twice the later one is the more recent delivery.
    """
    start = datetime(2026, 1, 1, tzinfo=UTC)
    records = [
        RawRecord(
            source="openalex",
            record_id=w["id"],
            payload=w,
            fetched_at=start + timedelta(seconds=i),
        )
        for i, w in enumerate(works)
    ]
    write_raw(db, "raw_openalex", records)

    previous = os.environ.get("IHUB_DUCKDB_PATH")
    os.environ["IHUB_DUCKDB_PATH"] = str(db)
    try:
        result = dbtRunner().invoke(
            [
                "build",
                "--select",
                select,
                "--project-dir",
                str(TRANSFORM),
                "--profiles-dir",
                str(TRANSFORM),
                "--target-path",
                str(db.parent / "target"),
                "--log-path",
                str(db.parent / "logs"),
            ]
        )
    finally:
        if previous is None:
            os.environ.pop("IHUB_DUCKDB_PATH", None)
        else:
            os.environ["IHUB_DUCKDB_PATH"] = previous
    assert result.success, result.exception
    return db


def query(db: Path, sql: str) -> list[dict[str, Any]]:
    """Run a query and return rows as dictionaries."""
    with duckdb.connect(str(db)) as con:
        cursor = con.execute(sql)
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
