"""Data status: when the DuckDB file shipped with the app was last built."""

from datetime import datetime
from pathlib import Path

import duckdb


def last_pipeline_run(db_path: Path) -> datetime | None:
    """Return the time of the latest pipeline run, or None if there is no data yet."""
    if not db_path.exists():
        return None
    try:
        with duckdb.connect(str(db_path), read_only=True) as con:
            row = con.execute("SELECT max(run_at) FROM meta.pipeline_runs").fetchone()
    except duckdb.Error:
        return None
    return row[0] if row else None
