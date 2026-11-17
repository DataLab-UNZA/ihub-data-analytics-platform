"""Routes for saved charts (/api/charts) and dashboards (/api/dashboards).

Every route needs a signed-in user with ``research:read``; the service applies the rest
(creating needs ``reports:manage``; changing needs ownership or ``users:manage``).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import asdict
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Request, status
from pydantic import BaseModel, Field

from ihub.auth.api import require
from ihub.auth.models import Principal
from ihub.auth.rbac import Permission
from ihub.workspace.models import Chart, Dashboard
from ihub.workspace.service import WorkspaceService

WorkspaceProvider = Callable[[], WorkspaceService]
Reader = Annotated[Principal, Depends(require(Permission.RESEARCH_READ))]


def get_workspace(request: Request) -> WorkspaceService:
    provider: WorkspaceProvider = request.app.state.workspace_service
    return provider()


Workspace = Annotated[WorkspaceService, Depends(get_workspace)]


class ChartIn(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    viz_type: str = Field(max_length=32)
    params: dict[str, Any]
    options: dict[str, Any] = Field(default_factory=dict)
    description: str = Field(default="", max_length=1000)


class ChartPatch(BaseModel):
    name: str | None = Field(default=None, max_length=200)
    viz_type: str | None = Field(default=None, max_length=32)
    params: dict[str, Any] | None = None
    options: dict[str, Any] | None = None
    description: str | None = Field(default=None, max_length=1000)


class DashboardIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)


class DashboardPatch(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    published: bool | None = None
    items: list[dict[str, Any]] | None = Field(default=None, max_length=40)
    filters: list[dict[str, Any]] | None = Field(default=None, max_length=10)


class FavouriteIn(BaseModel):
    favourite: bool


def chart_out(chart: Chart, principal: Principal) -> dict[str, Any]:
    data = asdict(chart)
    data["can_edit"] = chart.owner_id == principal.user_id or principal.has(Permission.USERS_MANAGE)
    return data


def dashboard_out(dashboard: Dashboard, principal: Principal) -> dict[str, Any]:
    data = asdict(dashboard)
    data["favourite"] = principal.user_id in dashboard.favourited_by
    data["favourite_count"] = len(dashboard.favourited_by)
    del data["favourited_by"]  # who favourited is nobody else's business
    data["can_edit"] = dashboard.owner_id == principal.user_id or principal.has(
        Permission.USERS_MANAGE
    )
    return data


def build_workspace_router() -> APIRouter:
    router = APIRouter(prefix="/api", tags=["workspace"])

    @router.get("/charts")
    def list_charts(principal: Reader, ws: Workspace) -> list[dict[str, Any]]:
        return [chart_out(chart, principal) for chart in ws.list_charts()]

    @router.post("/charts", status_code=status.HTTP_201_CREATED)
    def create_chart(body: ChartIn, principal: Reader, ws: Workspace) -> dict[str, Any]:
        return chart_out(ws.create_chart(principal, **body.model_dump()), principal)

    @router.get("/charts/{chart_id}")
    def get_chart(chart_id: str, principal: Reader, ws: Workspace) -> dict[str, Any]:
        return chart_out(ws.get_chart(chart_id), principal)

    @router.patch("/charts/{chart_id}")
    def update_chart(
        chart_id: str, body: ChartPatch, principal: Reader, ws: Workspace
    ) -> dict[str, Any]:
        changes = body.model_dump(exclude_none=True)
        return chart_out(ws.update_chart(principal, chart_id, **changes), principal)

    @router.delete("/charts/{chart_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_chart(chart_id: str, principal: Reader, ws: Workspace) -> None:
        ws.delete_chart(principal, chart_id)

    @router.get("/dashboards")
    def list_dashboards(principal: Reader, ws: Workspace) -> list[dict[str, Any]]:
        return [dashboard_out(d, principal) for d in ws.list_dashboards(principal)]

    @router.post("/dashboards", status_code=status.HTTP_201_CREATED)
    def create_dashboard(body: DashboardIn, principal: Reader, ws: Workspace) -> dict[str, Any]:
        return dashboard_out(ws.create_dashboard(principal, **body.model_dump()), principal)

    @router.get("/dashboards/{dashboard_id}")
    def get_dashboard(dashboard_id: str, principal: Reader, ws: Workspace) -> dict[str, Any]:
        return dashboard_out(ws.get_dashboard(principal, dashboard_id), principal)

    @router.patch("/dashboards/{dashboard_id}")
    def update_dashboard(
        dashboard_id: str, body: DashboardPatch, principal: Reader, ws: Workspace
    ) -> dict[str, Any]:
        updated = ws.update_dashboard(principal, dashboard_id, **body.model_dump(exclude_none=True))
        return dashboard_out(updated, principal)

    @router.delete("/dashboards/{dashboard_id}", status_code=status.HTTP_204_NO_CONTENT)
    def delete_dashboard(dashboard_id: str, principal: Reader, ws: Workspace) -> None:
        ws.delete_dashboard(principal, dashboard_id)

    @router.put("/dashboards/{dashboard_id}/favourite")
    def favourite(
        dashboard_id: str, body: FavouriteIn, principal: Reader, ws: Workspace
    ) -> dict[str, Any]:
        return dashboard_out(ws.set_favourite(principal, dashboard_id, body.favourite), principal)

    return router
