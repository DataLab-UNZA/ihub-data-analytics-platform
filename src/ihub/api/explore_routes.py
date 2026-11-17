"""Explore API: datasets, column values, queries, samples and CSV (ihub.mart.explore).

Thin controllers: each route validates its body with pydantic and calls ``ihub.mart``.
Reading needs ``research:read``; downloading CSV needs ``research:export`` (ADR-010).
"""

from __future__ import annotations

import csv
import io
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field

from ihub.mart import explore

Aggregate = Literal["COUNT", "COUNT_DISTINCT", "SUM", "AVG", "MIN", "MAX"]
Operator = Literal[
    "==", "!=", ">", "<", ">=", "<=", "IN", "NOT IN", "IS NULL", "IS NOT NULL", "CONTAINS"
]


class AdhocMetricIn(BaseModel):
    aggregate: Aggregate
    column: str = Field(max_length=64)


class FilterIn(BaseModel):
    column: str = Field(max_length=64)
    op: Operator
    value: Any = None


class QueryIn(BaseModel):
    dataset: str = Field(max_length=64)
    metrics: list[str | AdhocMetricIn] = Field(default_factory=list, max_length=10)
    groupby: list[str] = Field(default_factory=list, max_length=5)
    filters: list[FilterIn] = Field(default_factory=list, max_length=20)
    year_from: int | None = Field(default=None, ge=1800, le=2200)
    year_to: int | None = Field(default=None, ge=1800, le=2200)
    order_by: str | None = Field(default=None, max_length=8)
    order_desc: bool = True
    row_limit: int = Field(default=1000, ge=1, le=explore.MAX_ROWS)
    series_limit: int | None = Field(default=None, ge=1, le=100)

    def spec(self) -> explore.QuerySpec:
        return explore.QuerySpec(
            dataset=self.dataset,
            metrics=[
                explore.AdhocMetric(m.aggregate, m.column) if isinstance(m, AdhocMetricIn) else m
                for m in self.metrics
            ],
            groupby=self.groupby,
            filters=[explore.Filter(f.column, f.op, f.value) for f in self.filters],
            year_from=self.year_from,
            year_to=self.year_to,
            order_by=self.order_by,
            order_desc=self.order_desc,
            row_limit=self.row_limit,
            series_limit=self.series_limit,
        )


def _result(result: explore.QueryResult) -> dict[str, Any]:
    return {
        "columns": [asdict(column) for column in result.columns],
        "rows": result.rows,
        "row_count": result.row_count,
        "truncated": result.truncated,
        "duration_ms": result.duration_ms,
        "sql": result.sql,
        "params": [str(p) if not isinstance(p, int | float | bool) else p for p in result.params],
    }


def build_explore_router(
    database_path: Callable[[], Path],
    *,
    read: Sequence[Any] = (),
    export: Sequence[Any] = (),
) -> APIRouter:
    router = APIRouter(prefix="/api/explore", tags=["explore"], dependencies=list(read))

    @router.get("/datasets")
    def datasets() -> list[dict[str, Any]]:
        """Every dataset with its columns and metrics (the left panel of Explore)."""
        return [
            {
                "name": ds.name,
                "label": ds.label,
                "description": ds.description,
                "time_column": ds.time_column,
                "columns": [
                    {k: v for k, v in asdict(column).items() if k != "expr"}
                    for column in ds.columns
                ],
                "metrics": [
                    {k: v for k, v in asdict(metric).items() if k != "expr"}
                    for metric in ds.metrics
                ],
            }
            for ds in explore.DATASETS.values()
        ]

    @router.get("/datasets/{name}/values/{column}")
    def values(
        name: str,
        column: str,
        q: Annotated[str, Query(max_length=100)] = "",
    ) -> list[Any]:
        """The most common values of a column, for filter pickers."""
        return explore.column_values(database_path(), name, column, q)

    @router.post("/query")
    def query(body: QueryIn) -> dict[str, Any]:
        """Run a chart query: metrics by group-by columns under filters."""
        return _result(explore.run_query(database_path(), body.spec()))

    @router.post("/samples")
    def samples(body: QueryIn) -> dict[str, Any]:
        """Up to 100 raw rows of the dataset under the same filters."""
        return _result(explore.samples(database_path(), body.spec()))

    @router.post("/query.csv", dependencies=list(export))
    def query_csv(body: QueryIn) -> Response:
        """The query result as CSV (needs research:export)."""
        result = explore.run_query(database_path(), body.spec())
        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow([column.label for column in result.columns])
        for row in result.rows:
            writer.writerow([_csv_safe(value) for value in row])
        return Response(
            out.getvalue(),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": 'attachment; filename="ihub-chart-data.csv"'},
        )

    return router


def _csv_safe(value: Any) -> Any:
    """Stop spreadsheet formula injection: text starting with = + - @ is prefixed with '."""
    if isinstance(value, str) and value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value
