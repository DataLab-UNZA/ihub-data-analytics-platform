"""Helpers for tests that build dbt models from raw records in a temporary DuckDB file."""

from __future__ import annotations

import copy
import json
import os
from collections.abc import Iterable
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


def load_raw(db: Path, source: str, records: Iterable[tuple[str, dict[str, Any]]]) -> Path:
    """Write ``(record_id, payload)`` pairs to ``raw_<source>.records``, as a connector would.

    Records are loaded in order, each fetched one second after the one before, so when the
    same record appears twice the later one is the more recent delivery.
    """
    start = datetime(2026, 1, 1, tzinfo=UTC)
    raw = [
        RawRecord(
            source=source,
            record_id=record_id,
            payload=payload,
            fetched_at=start + timedelta(seconds=i),
        )
        for i, (record_id, payload) in enumerate(records)
    ]
    write_raw(db, f"raw_{source}", raw)
    return db


def run_dbt(db: Path, command: str, select: str | None = None) -> None:
    """Run a dbt command (``build``, ``seed``, ...) on ``db`` and fail the test if it fails."""
    args = [command]
    if select:
        args += ["--select", select]
    args += [
        "--project-dir",
        str(TRANSFORM),
        "--profiles-dir",
        str(TRANSFORM),
        "--target-path",
        str(db.parent / "target"),
        "--log-path",
        str(db.parent / "logs"),
    ]
    previous = os.environ.get("IHUB_DUCKDB_PATH")
    os.environ["IHUB_DUCKDB_PATH"] = str(db)
    try:
        result = dbtRunner().invoke(args)
    finally:
        if previous is None:
            os.environ.pop("IHUB_DUCKDB_PATH", None)
        else:
            os.environ["IHUB_DUCKDB_PATH"] = previous
    assert result.success, result.exception or _failures(result)


def _failures(result: Any) -> str:
    """The names and messages of the nodes that failed, for a readable assertion."""
    nodes = getattr(result, "result", None) or []
    return "; ".join(
        f"{r.node.name}: {r.message}" for r in nodes if str(r.status) in ("error", "fail")
    )


def build_warehouse(
    db: Path, works: list[dict[str, Any]], select: str = "+path:models/marts/research"
) -> Path:
    """Load OpenAlex ``works`` into raw_openalex and run ``dbt build`` for ``select``."""
    load_raw(db, "openalex", [(w["id"], w) for w in works])
    run_dbt(db, "build", select)
    return db


def query(db: Path, sql: str) -> list[dict[str, Any]]:
    """Run a query and return rows as dictionaries."""
    with duckdb.connect(str(db)) as con:
        cursor = con.execute(sql)
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]
