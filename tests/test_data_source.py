"""Tests for the runtime data source.

Only the local-file path is exercised, so the tests make no network calls:
when the DuckDB file already exists, ensure_duckdb must return it as-is without
reaching out to GitHub Releases.
"""

from pathlib import Path

from ihub.ingest.__main__ import record_run
from ihub.mart.data_source import ensure_duckdb


def test_existing_local_file_is_used(tmp_path: Path) -> None:
    db = tmp_path / "ihub.duckdb"
    record_run(str(db), [])
    assert ensure_duckdb(db) == db


def test_missing_file_without_data_returns_none(tmp_path: Path, monkeypatch) -> None:
    # No published release -> None, and still no network (latest_data_asset stubbed).
    monkeypatch.setattr("ihub.mart.data_source.latest_data_asset", lambda: None)
    assert ensure_duckdb(tmp_path / "absent.duckdb") is None
