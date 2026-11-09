from pathlib import Path

from ihub.ingest.__main__ import record_run
from ihub.mart.status import last_pipeline_run


def test_no_database_means_no_run(tmp_path: Path) -> None:
    assert last_pipeline_run(tmp_path / "missing.duckdb") is None


def test_recorded_run_is_reported(tmp_path: Path) -> None:
    db = tmp_path / "ihub.duckdb"
    record_run(db, "abc1234", 0)
    record_run(db, "def5678", 0)
    assert last_pipeline_run(db) is not None
