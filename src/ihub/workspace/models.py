"""Saved charts and dashboards. ``params`` and ``layout`` are JSON-compatible data."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class Chart:
    """A saved Explore chart: its query (``params``) and its look (``viz_type``, ``options``)."""

    chart_id: str
    name: str
    viz_type: str
    dataset: str
    params: dict[str, Any]
    options: dict[str, Any]
    owner_id: str
    created_at: datetime
    updated_at: datetime
    description: str = ""


@dataclass(frozen=True)
class DashboardItem:
    """One chart on a dashboard: its width in grid columns (of 12) and height in rows (of 50px)."""

    chart_id: str
    width: int = 6
    height: int = 8


@dataclass(frozen=True)
class NativeFilter:
    """A dashboard filter, applied to every chart whose dataset has the column."""

    filter_id: str
    label: str
    column: str
    kind: str = "values"  # "values" (pick values) or "year_range"


@dataclass(frozen=True)
class Dashboard:
    dashboard_id: str
    title: str
    owner_id: str
    created_at: datetime
    updated_at: datetime
    published: bool = False
    description: str = ""
    items: tuple[DashboardItem, ...] = ()
    filters: tuple[NativeFilter, ...] = ()
    favourited_by: frozenset[str] = field(default_factory=frozenset)
