"""SQLite store for saved charts and dashboards (tests and development).

Each record is stored as one JSON document, so the shape can grow without migrations.
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ihub.workspace.models import Chart, Dashboard, DashboardItem, NativeFilter

_SCHEMA = """
CREATE TABLE IF NOT EXISTS charts (chart_id TEXT PRIMARY KEY, doc TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS dashboards (dashboard_id TEXT PRIMARY KEY, doc TEXT NOT NULL);
"""


def _encode(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.astimezone(UTC).isoformat(timespec="microseconds")
    if isinstance(value, frozenset | set | tuple):
        return sorted(value) if isinstance(value, frozenset | set) else list(value)
    raise TypeError(f"Cannot store {type(value).__name__}")


class _Database:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as con:
            con.executescript(_SCHEMA)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        con = sqlite3.connect(self.path, timeout=10)
        try:
            with con:
                yield con
        finally:
            con.close()


class SqliteChartRepository:
    def __init__(self, db: _Database) -> None:
        self._db = db

    @staticmethod
    def _chart(doc: str) -> Chart:
        data = json.loads(doc)
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        return Chart(**data)

    def get(self, chart_id: str) -> Chart | None:
        with self._db.connect() as con:
            row = con.execute("SELECT doc FROM charts WHERE chart_id = ?", (chart_id,)).fetchone()
        return self._chart(row[0]) if row else None

    def list_all(self) -> list[Chart]:
        with self._db.connect() as con:
            rows = con.execute("SELECT doc FROM charts").fetchall()
        return [self._chart(row[0]) for row in rows]

    def save(self, chart: Chart) -> None:
        doc = json.dumps(asdict(chart), default=_encode)
        with self._db.connect() as con:
            con.execute(
                "INSERT INTO charts VALUES (?, ?) "
                "ON CONFLICT (chart_id) DO UPDATE SET doc = excluded.doc",
                (chart.chart_id, doc),
            )

    def delete(self, chart_id: str) -> None:
        with self._db.connect() as con:
            con.execute("DELETE FROM charts WHERE chart_id = ?", (chart_id,))


class SqliteDashboardRepository:
    def __init__(self, db: _Database) -> None:
        self._db = db

    @staticmethod
    def _dashboard(doc: str) -> Dashboard:
        data = json.loads(doc)
        data["created_at"] = datetime.fromisoformat(data["created_at"])
        data["updated_at"] = datetime.fromisoformat(data["updated_at"])
        data["items"] = tuple(DashboardItem(**item) for item in data.get("items", []))
        data["filters"] = tuple(NativeFilter(**flt) for flt in data.get("filters", []))
        data["favourited_by"] = frozenset(data.get("favourited_by", []))
        return Dashboard(**data)

    def get(self, dashboard_id: str) -> Dashboard | None:
        with self._db.connect() as con:
            row = con.execute(
                "SELECT doc FROM dashboards WHERE dashboard_id = ?", (dashboard_id,)
            ).fetchone()
        return self._dashboard(row[0]) if row else None

    def list_all(self) -> list[Dashboard]:
        with self._db.connect() as con:
            rows = con.execute("SELECT doc FROM dashboards").fetchall()
        return [self._dashboard(row[0]) for row in rows]

    def save(self, dashboard: Dashboard) -> None:
        doc = json.dumps(asdict(dashboard), default=_encode)
        with self._db.connect() as con:
            con.execute(
                "INSERT INTO dashboards VALUES (?, ?) "
                "ON CONFLICT (dashboard_id) DO UPDATE SET doc = excluded.doc",
                (dashboard.dashboard_id, doc),
            )

    def delete(self, dashboard_id: str) -> None:
        with self._db.connect() as con:
            con.execute("DELETE FROM dashboards WHERE dashboard_id = ?", (dashboard_id,))


class SqliteWorkspaceStore:
    def __init__(self, path: Path) -> None:
        db = _Database(path)
        self._charts = SqliteChartRepository(db)
        self._dashboards = SqliteDashboardRepository(db)

    @property
    def charts(self) -> SqliteChartRepository:
        return self._charts

    @property
    def dashboards(self) -> SqliteDashboardRepository:
        return self._dashboards
