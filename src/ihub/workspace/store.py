"""Repository interfaces for saved charts and dashboards (SQLite)."""

from __future__ import annotations

from typing import Protocol

from ihub.workspace.models import Chart, Dashboard


class ChartRepository(Protocol):
    def get(self, chart_id: str) -> Chart | None: ...

    def list_all(self) -> list[Chart]: ...

    def save(self, chart: Chart) -> None: ...

    def delete(self, chart_id: str) -> None: ...


class DashboardRepository(Protocol):
    def get(self, dashboard_id: str) -> Dashboard | None: ...

    def list_all(self) -> list[Dashboard]: ...

    def save(self, dashboard: Dashboard) -> None: ...

    def delete(self, dashboard_id: str) -> None: ...


class WorkspaceStore(Protocol):
    @property
    def charts(self) -> ChartRepository: ...

    @property
    def dashboards(self) -> DashboardRepository: ...
