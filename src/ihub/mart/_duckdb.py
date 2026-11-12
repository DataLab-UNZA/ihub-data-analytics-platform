"""The read-only DuckDB access shared by the query modules of ``ihub.mart``.

Every query function opens its own read-only connection through :func:`fetch`, so pages can
call them freely, and a missing database or mart table becomes :class:`MartUnavailableError`
instead of a DuckDB error the page would have to know about.
"""

from __future__ import annotations

from collections.abc import Iterator, Sequence
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import duckdb


class MartUnavailableError(Exception):
    """The research mart has not been built yet (no database file, or no mart tables)."""


@contextmanager
def connect(db_path: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    """Open the database read-only, or raise ``MartUnavailableError`` if it is not there."""
    if not Path(db_path).exists():
        raise MartUnavailableError(f"No database at {db_path}")
    try:
        con = duckdb.connect(str(db_path), read_only=True)
    except duckdb.Error as exc:
        raise MartUnavailableError(f"Cannot open the database at {db_path}") from exc
    try:
        yield con
    except duckdb.CatalogException as exc:
        raise MartUnavailableError("The research mart has not been built yet") from exc
    finally:
        con.close()


def fetch(db_path: Path, sql: str, params: Sequence[Any] = ()) -> list[tuple[Any, ...]]:
    """Run one parameterised query and return every row."""
    with connect(db_path) as con:
        return con.execute(sql, list(params)).fetchall()
