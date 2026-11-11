"""Run the ingestion step of the pipeline: ``python -m ihub.ingest``.

Creates (or opens) the DuckDB file at ``IHUB_DUCKDB_PATH``, runs every enabled
connector listed in ``config/sources.yml``, writes each source's records unchanged
to its ``raw_<source>`` schema and records the run in ``meta.pipeline_runs``.
Run it from the repository root.
"""

from __future__ import annotations

import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import yaml

from ihub.connectors.base import Connector
from ihub.connectors.dspace_oai import DSpaceOaiConnector
from ihub.connectors.ojs import OjsConnector
from ihub.connectors.openalex import OpenAlexConnector
from ihub.connectors.orcid import OrcidConnector
from ihub.ingest.raw import write_raw
from ihub.settings import get_settings

CONFIG_PATH = Path("config/sources.yml")

# Every connector, in the order they run. Each one reads its own block of config/sources.yml
# (keyed by its source_name) and is skipped there unless enabled.
CONNECTORS: list[type[Connector]] = [
    OpenAlexConnector,
    DSpaceOaiConnector,
    OjsConnector,
    OrcidConnector,
]


def load_source_config(path: Path = CONFIG_PATH) -> dict[str, dict[str, Any]]:
    """Return the ``sources`` section of ``config/sources.yml``."""
    with path.open(encoding="utf-8") as handle:
        return yaml.safe_load(handle)["sources"]


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


def configure_logging() -> None:
    """Show connector progress, but keep request URLs out of the log (they can hold API keys)."""
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    for noisy in ("httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)


def main() -> None:
    """Run all enabled connectors and record the pipeline run."""
    configure_logging()
    settings = get_settings()
    sources = load_source_config()
    connectors_run = 0
    for connector_cls in CONNECTORS:
        name = connector_cls.source_name
        source_config = sources.get(name, {})
        if not source_config.get("enabled", False):
            print(f"Skipping {name}: not enabled in {CONFIG_PATH}")
            continue
        connector = connector_cls(source_config)
        written = write_raw(settings.ihub_duckdb_path, f"raw_{name}", connector.fetch())
        print(f"Wrote {written} records to raw_{name}.records")
        connectors_run += 1
    record_run(settings.ihub_duckdb_path, os.environ.get("GITHUB_SHA"), connectors_run)
    print(f"Recorded pipeline run in {settings.ihub_duckdb_path}")


if __name__ == "__main__":
    main()
