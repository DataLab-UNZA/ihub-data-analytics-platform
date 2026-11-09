"""Tests for recording a pipeline run and reading it back for the app."""

from pathlib import Path

from ihub.ingest.__main__ import record_run
from ihub.mart.status import last_pipeline_run


def test_no_database_means_no_run(tmp_path: Path) -> None:
    assert last_pipeline_run(tmp_path / "missing.duckdb") is None


def test_recorded_run_is_read_back(tmp_path: Path) -> None:
    db = tmp_path / "ihub.duckdb"
    record_run(str(db), [])
    assert last_pipeline_run(db) is not None
