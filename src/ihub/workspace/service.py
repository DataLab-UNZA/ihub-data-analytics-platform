"""Rules for saved charts and dashboards: visibility, ownership and validation."""

from __future__ import annotations

import json
import uuid
from collections.abc import Callable
from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

from ihub.auth.errors import InvalidRequestError, NotFoundError, PermissionDeniedError
from ihub.auth.models import Principal
from ihub.auth.rbac import Permission
from ihub.mart import explore
from ihub.workspace.models import Chart, Dashboard, DashboardItem, NativeFilter
from ihub.workspace.store import WorkspaceStore

VIZ_TYPES = frozenset(
    {"table", "big_number", "bar", "line", "area", "pie", "treemap", "heatmap", "world_map"}
)
MAX_OPTIONS_BYTES = 20_000
MAX_ITEMS = 40
MAX_FILTERS = 10


def _now() -> datetime:
    return datetime.now(UTC)


def _text(value: str, label: str, limit: int, *, required: bool = True) -> str:
    text = " ".join(str(value or "").split())
    if required and not text:
        raise InvalidRequestError(f"Give the {label}.", reason="missing")
    if len(text) > limit:
        raise InvalidRequestError(
            f"The {label} can have at most {limit} characters.", reason="long"
        )
    return text


class WorkspaceService:
    """The only entry point the chart and dashboard routes use."""

    def __init__(self, store: WorkspaceStore, clock: Callable[[], datetime] = _now) -> None:
        self._store = store
        self._clock = clock

    # Rules -----------------------------------------------------------------------------

    @staticmethod
    def _can_build(principal: Principal) -> None:
        if not principal.has(Permission.REPORTS_MANAGE):
            raise PermissionDeniedError("Your role cannot save charts or dashboards.")

    @staticmethod
    def _can_change(principal: Principal, owner_id: str) -> None:
        if principal.user_id != owner_id and not principal.has(Permission.USERS_MANAGE):
            raise PermissionDeniedError("Only the owner or an administrator can change this.")

    @staticmethod
    def _visible(principal: Principal, dashboard: Dashboard) -> bool:
        return (
            dashboard.published
            or dashboard.owner_id == principal.user_id
            or principal.has(Permission.USERS_MANAGE)
        )

    @staticmethod
    def _check_chart(viz_type: str, params: dict[str, Any], options: dict[str, Any]) -> str:
        if viz_type not in VIZ_TYPES:
            raise InvalidRequestError(f"Unknown chart type '{viz_type}'.", reason="viz_type")
        if len(json.dumps(options)) > MAX_OPTIONS_BYTES:
            raise InvalidRequestError("The chart options are too large.", reason="options")
        from ihub.api.explore_routes import QueryIn  # one definition of a valid query

        try:
            spec = QueryIn.model_validate(params).spec()
            explore.build_query(spec)
        except ValueError as exc:  # pydantic errors are ValueErrors too
            raise InvalidRequestError(
                f"The chart's query is not valid: {exc}", reason="query"
            ) from exc
        return spec.dataset

    # Charts ----------------------------------------------------------------------------

    def list_charts(self) -> list[Chart]:
        return sorted(self._store.charts.list_all(), key=lambda c: c.updated_at, reverse=True)

    def get_chart(self, chart_id: str) -> Chart:
        chart = self._store.charts.get(chart_id)
        if chart is None:
            raise NotFoundError("No such chart.")
        return chart

    def create_chart(
        self,
        principal: Principal,
        *,
        name: str,
        viz_type: str,
        params: dict[str, Any],
        options: dict[str, Any],
        description: str = "",
    ) -> Chart:
        self._can_build(principal)
        dataset = self._check_chart(viz_type, params, options)
        now = self._clock()
        chart = Chart(
            chart_id=uuid.uuid4().hex,
            name=_text(name, "chart name", 120),
            viz_type=viz_type,
            dataset=dataset,
            params=params,
            options=options,
            owner_id=principal.user_id,
            created_at=now,
            updated_at=now,
            description=_text(description, "description", 500, required=False),
        )
        self._store.charts.save(chart)
        return chart

    def update_chart(self, principal: Principal, chart_id: str, **changes: Any) -> Chart:
        chart = self.get_chart(chart_id)
        self._can_change(principal, chart.owner_id)
        viz_type = changes.get("viz_type") or chart.viz_type
        params = changes.get("params") if changes.get("params") is not None else chart.params
        options = changes.get("options") if changes.get("options") is not None else chart.options
        dataset = self._check_chart(viz_type, params, options)
        updated = replace(
            chart,
            name=_text(changes.get("name") or chart.name, "chart name", 120),
            description=_text(
                changes["description"]
                if changes.get("description") is not None
                else chart.description,
                "description",
                500,
                required=False,
            ),
            viz_type=viz_type,
            dataset=dataset,
            params=params,
            options=options,
            updated_at=self._clock(),
        )
        self._store.charts.save(updated)
        return updated

    def delete_chart(self, principal: Principal, chart_id: str) -> None:
        chart = self.get_chart(chart_id)
        self._can_change(principal, chart.owner_id)
        self._store.charts.delete(chart_id)
        for dashboard in self._store.dashboards.list_all():  # remove it from every dashboard
            kept = tuple(item for item in dashboard.items if item.chart_id != chart_id)
            if kept != dashboard.items:
                self._store.dashboards.save(replace(dashboard, items=kept))

    # Dashboards ------------------------------------------------------------------------

    def list_dashboards(self, principal: Principal) -> list[Dashboard]:
        visible = [d for d in self._store.dashboards.list_all() if self._visible(principal, d)]
        return sorted(visible, key=lambda d: d.updated_at, reverse=True)

    def get_dashboard(self, principal: Principal, dashboard_id: str) -> Dashboard:
        dashboard = self._store.dashboards.get(dashboard_id)
        if dashboard is None or not self._visible(principal, dashboard):
            raise NotFoundError("No such dashboard.")
        return dashboard

    def create_dashboard(
        self, principal: Principal, *, title: str, description: str = ""
    ) -> Dashboard:
        self._can_build(principal)
        now = self._clock()
        dashboard = Dashboard(
            dashboard_id=uuid.uuid4().hex,
            title=_text(title, "dashboard title", 120),
            description=_text(description, "description", 500, required=False),
            owner_id=principal.user_id,
            created_at=now,
            updated_at=now,
        )
        self._store.dashboards.save(dashboard)
        return dashboard

    def update_dashboard(
        self,
        principal: Principal,
        dashboard_id: str,
        *,
        title: str | None = None,
        description: str | None = None,
        published: bool | None = None,
        items: list[dict[str, Any]] | None = None,
        filters: list[dict[str, Any]] | None = None,
    ) -> Dashboard:
        dashboard = self.get_dashboard(principal, dashboard_id)
        self._can_change(principal, dashboard.owner_id)
        new_items = dashboard.items
        if items is not None:
            if len(items) > MAX_ITEMS:
                raise InvalidRequestError(f"A dashboard can hold at most {MAX_ITEMS} charts.")
            new_items = tuple(
                DashboardItem(
                    chart_id=self.get_chart(str(item["chart_id"])).chart_id,
                    width=min(12, max(3, int(item.get("width", 6)))),
                    height=min(20, max(4, int(item.get("height", 8)))),
                )
                for item in items
            )
        new_filters = dashboard.filters
        if filters is not None:
            if len(filters) > MAX_FILTERS:
                raise InvalidRequestError(f"A dashboard can have at most {MAX_FILTERS} filters.")
            new_filters = tuple(self._filter(flt) for flt in filters)
        updated = replace(
            dashboard,
            title=_text(title, "dashboard title", 120) if title is not None else dashboard.title,
            description=_text(description, "description", 500, required=False)
            if description is not None
            else dashboard.description,
            published=dashboard.published if published is None else bool(published),
            items=new_items,
            filters=new_filters,
            updated_at=self._clock(),
        )
        self._store.dashboards.save(updated)
        return updated

    @staticmethod
    def _filter(data: dict[str, Any]) -> NativeFilter:
        column = str(data.get("column", ""))
        known = {c.name for ds in explore.DATASETS.values() for c in ds.columns}
        if column not in known:
            raise InvalidRequestError(f"Unknown filter column '{column}'.", reason="filter")
        kind = data.get("kind", "values")
        if kind not in ("values", "year_range"):
            raise InvalidRequestError("A filter is either 'values' or 'year_range'.")
        return NativeFilter(
            filter_id=str(data.get("filter_id") or uuid.uuid4().hex[:8]),
            label=_text(data.get("label") or column, "filter label", 60),
            column=column,
            kind=kind,
        )

    def delete_dashboard(self, principal: Principal, dashboard_id: str) -> None:
        dashboard = self.get_dashboard(principal, dashboard_id)
        self._can_change(principal, dashboard.owner_id)
        self._store.dashboards.delete(dashboard_id)

    def set_favourite(self, principal: Principal, dashboard_id: str, favourite: bool) -> Dashboard:
        dashboard = self.get_dashboard(principal, dashboard_id)
        fans = set(dashboard.favourited_by)
        (fans.add if favourite else fans.discard)(principal.user_id)
        updated = replace(dashboard, favourited_by=frozenset(fans))
        self._store.dashboards.save(updated)
        return updated
