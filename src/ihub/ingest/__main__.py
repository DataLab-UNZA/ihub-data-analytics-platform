"""Run the ingestion step of the pipeline: ``python -m ihub.ingest``.

Creates (or opens) the DuckDB file at ``IHUB_DUCKDB_PATH``, runs every
registered connector and records the run in ``meta.pipeline_runs``. No
connectors exist yet, so for now this only records the run; the pipeline
still produces a valid DuckDB file that the app can open.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path

import duckdb

from ihub.settings import get_settings

# Connector classes are added here as they are built (OpenAlex, DSpace, OJS, ORCID).
CONNECTORS: list[type] = []


def record_run(db_path: Path, commit_sha: str | None, connectors_run: int) -> None:
    """Create the ``meta`` schema if needed and append one row for this run."""
    db_path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(str(db_path)) as con:
        con.execute("CREATE SCHEMA IF NOT EXISTS meta")
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS meta.pipeline_runs (
                run_at TIMESTAMP,
                commit_sha VARCHAR,
                connectors_run INTEGER
            )
            """
        )
        con.execute(
            "INSERT INTO meta.pipeline_runs VALUES (?, ?, ?)",
            [datetime.now(UTC).replace(tzinfo=None), commit_sha, connectors_run],
        )


def main() -> None:
    """Run all connectors and record the pipeline run."""
    settings = get_settings()
    for connector_cls in CONNECTORS:
        connector_cls().run()
    record_run(settings.ihub_duckdb_path, os.environ.get("GITHUB_SHA"), len(CONNECTORS))
    print(f"Recorded pipeline run in {settings.ihub_duckdb_path}")


if __name__ == "__main__":
    main()
