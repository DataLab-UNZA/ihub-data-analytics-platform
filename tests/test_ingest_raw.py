"""Tests for writing raw records into DuckDB."""

import json
from pathlib import Path

import duckdb
import pytest

from ihub.connectors.base import RawRecord
from ihub.ingest.raw import write_raw


def make_records(*ids: str) -> list[RawRecord]:
    return [RawRecord(source="openalex", record_id=i, payload={"id": i}) for i in ids]


def read_rows(db: Path) -> list[tuple]:
    with duckdb.connect(str(db)) as con:
        return con.execute(
            "SELECT record_id, source, payload FROM raw_openalex.records ORDER BY record_id"
        ).fetchall()


def test_records_are_stored_unchanged(tmp_path: Path) -> None:
    db = tmp_path / "test.duckdb"
    assert write_raw(db, "raw_openalex", make_records("W1", "W2")) == 2
    rows = read_rows(db)
    assert [row[:2] for row in rows] == [("W1", "openalex"), ("W2", "openalex")]
    assert json.loads(rows[0][2]) == {"id": "W1"}


def test_a_new_load_replaces_the_previous_one(tmp_path: Path) -> None:
    db = tmp_path / "test.duckdb"
    write_raw(db, "raw_openalex", make_records("W1", "W2"))
    write_raw(db, "raw_openalex", make_records("W3"))
    assert [row[0] for row in read_rows(db)] == ["W3"]


def test_a_failed_load_keeps_the_previous_data(tmp_path: Path) -> None:
    db = tmp_path / "test.duckdb"
    write_raw(db, "raw_openalex", make_records("W1"))

    def failing():
        yield from make_records("W2")
        raise RuntimeError("network down")

    with pytest.raises(RuntimeError):
        write_raw(db, "raw_openalex", failing())
    assert [row[0] for row in read_rows(db)] == ["W1"]


def test_invalid_schema_name_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Invalid raw schema name"):
        write_raw(tmp_path / "test.duckdb", "raw_openalex; DROP TABLE x", [])
