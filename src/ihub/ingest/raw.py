"""Write raw records, unchanged, into a per-source ``raw_<source>`` schema in DuckDB."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from pathlib import Path

import duckdb

from ihub.connectors.base import RawRecord

BATCH_SIZE = 500
_SCHEMA_NAME = re.compile(r"raw_[a-z][a-z0-9_]*")


def write_raw(db_path: Path, schema: str, records: Iterable[RawRecord]) -> int:
    """Replace ``<schema>.records`` with ``records`` and return how many rows were written.

    The load is one transaction, so a failed fetch leaves the previous load untouched.
    """
    if not _SCHEMA_NAME.fullmatch(schema):
        raise ValueError(f"Invalid raw schema name: {schema!r}")
    db_path.parent.mkdir(parents=True, exist_ok=True)
    insert_sql = f"INSERT INTO {schema}.records VALUES (?, ?, ?, ?)"
    count = 0
    with duckdb.connect(str(db_path)) as con:
        con.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
        con.execute("BEGIN")
        try:
            con.execute(
                f"""
                CREATE OR REPLACE TABLE {schema}.records (
                    record_id VARCHAR,
                    source VARCHAR,
                    fetched_at TIMESTAMP,
                    payload JSON
                )
                """
            )
            batch: list[list[object]] = []
            for record in records:
                batch.append(
                    [
                        record.record_id,
                        record.source,
                        record.fetched_at.replace(tzinfo=None),
                        json.dumps(record.payload),
                    ]
                )
                if len(batch) >= BATCH_SIZE:
                    con.executemany(insert_sql, batch)
                    count += len(batch)
                    batch = []
            if batch:
                con.executemany(insert_sql, batch)
                count += len(batch)
            con.execute("COMMIT")
        except BaseException:
            con.execute("ROLLBACK")
            raise
    return count
