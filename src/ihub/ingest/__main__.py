"""Pipeline entry point: run the enabled connectors and record the run in DuckDB.

Run with:  uv run python -m ihub.ingest

No connectors exist yet, so this currently creates the DuckDB file (if it does
not exist) and records the run in ``meta.pipeline_runs``. The scheduled
pipeline workflow runs this before ``dbt build``. As connectors are added,
they are called from ``run_connectors``.
"""

import os
from datetime import UTC, datetime

import duckdb

from ihub.settings import get_settings


def run_connectors() -> list[str]:
    """Run each enabled connector and return the names of those that ran.

    Connectors are not built yet (see config/sources.yml), so none run.
    """
    return []


def record_run(db_path: str, connectors_run: list[str]) -> None:
    """Create the DuckDB file if needed and append one row to meta.pipeline_runs."""
    with duckdb.connect(db_path) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS meta")
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS meta.pipeline_runs (
                run_at TIMESTAMP,
                git_sha VARCHAR,
                connectors_run VARCHAR[]
            )
            """
        )
        con.execute(
            # Store naive UTC in a plain TIMESTAMP. A TIMESTAMPTZ makes DuckDB
            # import pytz when the column is read back, and pytz is not an app
            # dependency (it is absent on Streamlit Community Cloud and in CI),
            # so reading it would fail. The app always treats this time as UTC.
            "INSERT INTO meta.pipeline_runs VALUES (?, ?, ?)",
            [
                datetime.now(UTC).replace(tzinfo=None),
                os.environ.get("GITHUB_SHA", "local"),
                connectors_run,
            ],
        )
        # Flush the write-ahead log into the database file itself, so the
        # published ihub.duckdb is self-contained: the app opens it read-only
        # (which cannot replay a .wal) and the .wal is never published.
        con.execute("CHECKPOINT")


def main() -> None:
    settings = get_settings()
    settings.ihub_duckdb_path.parent.mkdir(parents=True, exist_ok=True)
    connectors_run = run_connectors()
    record_run(str(settings.ihub_duckdb_path), connectors_run)
    print(f"Pipeline run recorded in {settings.ihub_duckdb_path}; connectors run: {connectors_run}")


if __name__ == "__main__":
    main()
