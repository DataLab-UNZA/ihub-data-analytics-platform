"""Tests for the stg_openalex__works dbt model, built from the recorded OpenAlex sample."""

import json
import os
from pathlib import Path

import duckdb
import pytest
from dbt.cli.main import dbtRunner

from ihub.connectors.base import RawRecord
from ihub.ingest.raw import write_raw

ROOT = Path(__file__).resolve().parent.parent
TRANSFORM = ROOT / "transform"
SAMPLE = ROOT / "tests" / "fixtures" / "openalex_works_sample.json"


@pytest.fixture(scope="module")
def built_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Load the sample into raw_openalex and run dbt build for the staging model once."""
    tmp_path = tmp_path_factory.mktemp("dbt")
    db = tmp_path / "test.duckdb"
    works = json.loads(SAMPLE.read_text(encoding="utf-8"))["results"]
    records = [RawRecord(source="openalex", record_id=w["id"], payload=w) for w in works]
    write_raw(db, "raw_openalex", records)

    previous = os.environ.get("IHUB_DUCKDB_PATH")
    os.environ["IHUB_DUCKDB_PATH"] = str(db)
    try:
        result = dbtRunner().invoke(
            [
                "build",
                "--select",
                "stg_openalex__works",
                "--project-dir",
                str(TRANSFORM),
                "--profiles-dir",
                str(TRANSFORM),
                "--target-path",
                str(tmp_path / "target"),
                "--log-path",
                str(tmp_path / "logs"),
            ]
        )
    finally:
        if previous is None:
            os.environ.pop("IHUB_DUCKDB_PATH", None)
        else:
            os.environ["IHUB_DUCKDB_PATH"] = previous
    assert result.success, result.exception
    return db


def read_works(db: Path) -> list[dict]:
    with duckdb.connect(str(db)) as con:
        schema = con.execute(
            "SELECT table_schema FROM information_schema.tables "
            "WHERE table_name = 'stg_openalex__works'"
        ).fetchone()[0]
        cursor = con.execute(f"SELECT * FROM {schema}.stg_openalex__works ORDER BY openalex_id")
        columns = [c[0] for c in cursor.description]
        return [dict(zip(columns, row, strict=True)) for row in cursor.fetchall()]


def test_one_row_per_work_and_dbt_tests_pass(built_db: Path) -> None:
    assert [w["openalex_id"] for w in read_works(built_db)] == ["W1617145133", "W2548000951"]


def test_columns_are_cleaned_and_typed(built_db: Path) -> None:
    work = read_works(built_db)[1]
    assert work["doi"] == "10.1016/s0140-6736(16)31392-7"
    assert work["year"] == 2016
    assert work["type"] == "review"
    assert work["venue_id"] == "S49861241"
    assert work["venue_name"] == "The Lancet"
    assert work["is_oa"] is True
    assert work["oa_status"] == "green"
    assert work["cited_by_count"] == 13519
    assert work["n_authors"] == 21
