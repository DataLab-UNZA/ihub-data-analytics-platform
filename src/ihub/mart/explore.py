"""A small semantic layer over the research mart for the Explore chart builder.

Users choose a dataset, metrics, group-by columns, filters and a year range, as in Apache
Superset's Explore view. They never write SQL: every expression comes from the dataset
definitions below (trusted code), aliases are positional, and every value is a bound
parameter, so a query spec cannot inject SQL. Invalid specs raise ValueError (a 400).

Individual authors are deliberately not a group-by column: CLAUDE.md rules out individual
staff rankings.
"""

from __future__ import annotations

import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ihub.mart._duckdb import fetch

ColumnType = Literal["string", "number", "boolean", "year"]
MAX_ROWS = 10_000
SAMPLE_ROWS = 100
VALUES_LIMIT = 100


@dataclass(frozen=True)
class Column:
    name: str
    label: str
    type: ColumnType
    expr: str
    groupable: bool = True
    description: str = ""


@dataclass(frozen=True)
class Metric:
    name: str
    label: str
    expr: str
    format: Literal["number", "percent", "decimal"] = "number"
    description: str = ""


@dataclass(frozen=True)
class Dataset:
    name: str
    label: str
    description: str
    from_sql: str
    columns: tuple[Column, ...]
    metrics: tuple[Metric, ...]
    time_column: str = "year"

    def column(self, name: str) -> Column:
        for column in self.columns:
            if column.name == name:
                return column
        raise ValueError(f"Unknown column '{name}' in dataset '{self.name}'.")

    def metric(self, name: str) -> Metric:
        for metric in self.metrics:
            if metric.name == name:
                return metric
        raise ValueError(f"Unknown metric '{name}' in dataset '{self.name}'.")


_YEAR = Column("year", "Year", "year", "y.year")

DATASETS: dict[str, Dataset] = {
    dataset.name: dataset
    for dataset in (
        Dataset(
            name="publications",
            label="Publications",
            description="One row per de-duplicated publication (fact_publication).",
            from_sql=(
                "marts.fact_publication f "
                "JOIN marts.dim_publication p ON p.publication_key = f.publication_key "
                "LEFT JOIN marts.dim_year y ON y.year_key = f.year_key "
                "LEFT JOIN marts.dim_venue v ON v.venue_key = f.venue_key "
                "LEFT JOIN marts.dim_publication_type t ON t.type_key = f.type_key"
            ),
            columns=(
                _YEAR,
                Column("publication_type", "Publication type", "string", "t.type_label"),
                Column("venue", "Venue", "string", "v.venue_name"),
                Column("oa_status", "Open-access status", "string", "f.oa_status"),
                Column("is_oa", "Open access", "boolean", "f.is_oa"),
                Column(
                    "international_collab",
                    "International collaboration",
                    "boolean",
                    "f.is_international_collab",
                    description="Unknown (empty) when OpenAlex gives no affiliations.",
                ),
                Column("in_openalex", "In OpenAlex", "boolean", "f.in_openalex"),
                Column("in_repository", "In the repository", "boolean", "f.in_repository"),
                Column("in_ojs", "In UNZA journals (OJS)", "boolean", "f.in_ojs"),
                Column("primary_source", "Primary source", "string", "p.primary_source_system"),
                Column("citations", "Citations", "number", "f.cited_by_count"),
                Column("authors", "Number of authors", "number", "CAST(f.n_authors AS BIGINT)"),
                Column("title", "Title", "string", "p.title", groupable=False),
                Column("doi", "DOI", "string", "p.doi", groupable=False),
            ),
            metrics=(
                Metric("count", "Publications", "COUNT(*)"),
                Metric("citations", "Citations", "SUM(f.cited_by_count)"),
                Metric(
                    "avg_citations", "Citations per publication", "AVG(f.cited_by_count)", "decimal"
                ),
                Metric(
                    "oa_share",
                    "Open-access share",
                    "AVG(CASE WHEN f.is_oa THEN 1.0 ELSE 0.0 END)",
                    "percent",
                ),
                Metric(
                    "intl_share",
                    "International share",
                    "AVG(CASE WHEN f.is_international_collab THEN 1.0 "
                    "WHEN NOT f.is_international_collab THEN 0.0 END)",
                    "percent",
                    "Among publications whose affiliations are known.",
                ),
            ),
        ),
        Dataset(
            name="affiliations",
            label="Affiliations",
            description="One row per publication × author × organisation (fact_authorship).",
            from_sql=(
                "marts.fact_authorship a "
                "LEFT JOIN marts.dim_author au ON au.author_key = a.author_key "
                "LEFT JOIN marts.dim_org o ON o.org_key = a.org_key "
                "LEFT JOIN marts.dim_year y ON y.year_key = a.year_key"
            ),
            columns=(
                _YEAR,
                Column("organisation", "Organisation", "string", "o.org_name"),
                Column("organisation_kind", "Organisation kind", "string", "o.org_kind"),
                Column("school", "School", "string", "o.school_name"),
                Column("country", "Country", "string", "o.country_code"),
                Column("is_unza_author", "UNZA author", "boolean", "au.is_unza_author"),
                Column("is_corresponding", "Corresponding author", "boolean", "a.is_corresponding"),
                Column("org_basis", "Attribution basis", "string", "a.org_basis"),
            ),
            metrics=(
                Metric("publications", "Publications", "COUNT(DISTINCT a.publication_key)"),
                Metric("authors", "Authors", "COUNT(DISTINCT a.author_key)"),
                Metric("organisations", "Organisations", "COUNT(DISTINCT a.org_key)"),
                Metric("rows", "Affiliation rows", "COUNT(*)"),
            ),
        ),
        Dataset(
            name="topics",
            label="Topics",
            description="Publications by OpenAlex topic (bridge_publication_topic).",
            from_sql=(
                "marts.bridge_publication_topic bt "
                "JOIN marts.dim_topic tp ON tp.topic_key = bt.topic_key "
                "JOIN marts.fact_publication f ON f.publication_key = bt.publication_key "
                "LEFT JOIN marts.dim_year y ON y.year_key = f.year_key"
            ),
            columns=(
                _YEAR,
                Column("topic", "Topic", "string", "tp.topic_name"),
                Column("subfield", "Subfield", "string", "tp.subfield_name"),
                Column("field", "Field", "string", "tp.field_name"),
                Column("domain", "Domain", "string", "tp.domain_name"),
                Column("is_primary_topic", "Primary topic", "boolean", "bt.is_primary_topic"),
                Column("is_oa", "Open access", "boolean", "f.is_oa"),
            ),
            metrics=(
                Metric("publications", "Publications", "COUNT(DISTINCT bt.publication_key)"),
                Metric("citations", "Citations", "SUM(f.cited_by_count)"),
                Metric("avg_score", "Average topic score", "AVG(bt.score)", "decimal"),
            ),
        ),
    )
}

AGGREGATES = {
    "COUNT": "COUNT({})",
    "COUNT_DISTINCT": "COUNT(DISTINCT {})",
    "SUM": "SUM({})",
    "AVG": "AVG({})",
    "MIN": "MIN({})",
    "MAX": "MAX({})",
}
NUMERIC_AGGREGATES = {"SUM", "AVG"}
OPERATORS = {"==", "!=", ">", "<", ">=", "<=", "IN", "NOT IN", "IS NULL", "IS NOT NULL", "CONTAINS"}


@dataclass(frozen=True)
class AdhocMetric:
    """An aggregate over one column, like Superset's simple ad-hoc metric."""

    aggregate: str
    column: str


MetricSpec = str | AdhocMetric


@dataclass(frozen=True)
class Filter:
    column: str
    op: str
    value: Any = None


@dataclass(frozen=True)
class QuerySpec:
    """What to compute. Validated against the dataset by :func:`build_query`."""

    dataset: str
    metrics: Sequence[MetricSpec] = ()
    groupby: Sequence[str] = ()
    filters: Sequence[Filter] = ()
    year_from: int | None = None
    year_to: int | None = None
    order_by: str | None = None  # a metric key ("m0"...) or group column; default first metric
    order_desc: bool = True
    row_limit: int = 1_000
    series_limit: int | None = None  # keep the top N values of the last group-by column


@dataclass(frozen=True)
class ResultColumn:
    key: str
    label: str
    type: str
    is_metric: bool
    format: str = "number"


@dataclass(frozen=True)
class QueryResult:
    columns: list[ResultColumn]
    rows: list[list[Any]]
    sql: str
    params: list[Any]
    row_count: int
    duration_ms: float
    truncated: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


def dataset(name: str) -> Dataset:
    try:
        return DATASETS[name]
    except KeyError:
        raise ValueError(f"Unknown dataset '{name}'.") from None


def _coerce(column: Column, value: Any) -> Any:
    try:
        if column.type in ("number", "year"):
            number = float(value)
            return int(number) if number.is_integer() else number
        if column.type == "boolean":
            if isinstance(value, bool):
                return value
            if str(value).lower() in ("true", "1", "yes"):
                return True
            if str(value).lower() in ("false", "0", "no"):
                return False
            raise ValueError
        return str(value)
    except (TypeError, ValueError):
        raise ValueError(f"'{value}' is not a valid value for {column.label}.") from None


def _metric_sql(ds: Dataset, spec: MetricSpec) -> tuple[str, str, str]:
    """(SQL expression, label, format) for a named or ad-hoc metric."""
    if isinstance(spec, AdhocMetric):
        aggregate = spec.aggregate.upper()
        if aggregate not in AGGREGATES:
            raise ValueError(f"Unknown aggregate '{spec.aggregate}'.")
        column = ds.column(spec.column)
        if aggregate in NUMERIC_AGGREGATES and column.type != "number":
            raise ValueError(f"{aggregate} needs a number column; {column.label} is not one.")
        fmt = "decimal" if aggregate == "AVG" else "number"
        return AGGREGATES[aggregate].format(column.expr), f"{aggregate}({column.label})", fmt
    metric = ds.metric(spec)
    return metric.expr, metric.label, metric.format


def _where(ds: Dataset, spec: QuerySpec) -> tuple[list[str], list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    year = ds.column(ds.time_column).expr
    if spec.year_from is not None:
        clauses.append(f"{year} >= ?")
        params.append(int(spec.year_from))
    if spec.year_to is not None:
        clauses.append(f"{year} <= ?")
        params.append(int(spec.year_to))
    for flt in spec.filters:
        column = ds.column(flt.column)
        op = flt.op.upper()
        if op not in OPERATORS:
            raise ValueError(f"Unknown filter operator '{flt.op}'.")
        if op in ("IS NULL", "IS NOT NULL"):
            clauses.append(f"{column.expr} {op}")
        elif op in ("IN", "NOT IN"):
            values = flt.value if isinstance(flt.value, list | tuple) else [flt.value]
            if not values:
                raise ValueError(f"Choose at least one value for {column.label}.")
            if len(values) > 1000:
                raise ValueError("A filter can list at most 1,000 values.")
            clauses.append(f"{column.expr} {op} ({', '.join('?' for _ in values)})")
            params.extend(_coerce(column, value) for value in values)
        elif op == "CONTAINS":
            text = str(flt.value or "")
            escaped = text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            clauses.append(f"CAST({column.expr} AS VARCHAR) ILIKE ? ESCAPE '\\'")
            params.append(f"%{escaped}%")
        else:
            sql_op = "=" if op == "==" else op
            clauses.append(f"{column.expr} {sql_op} ?")
            params.append(_coerce(column, flt.value))
    return clauses, params


def build_query(spec: QuerySpec) -> tuple[str, list[Any], list[ResultColumn]]:
    """The SQL, its parameters and the result columns for a spec (no database access)."""
    ds = dataset(spec.dataset)
    if not spec.metrics and not spec.groupby:
        raise ValueError("Choose at least one metric or group-by column.")
    if not 1 <= spec.row_limit <= MAX_ROWS:
        raise ValueError(f"The row limit must be between 1 and {MAX_ROWS:,}.")

    select: list[str] = []
    result_columns: list[ResultColumn] = []
    group_exprs: list[str] = []
    for index, name in enumerate(spec.groupby):
        column = ds.column(name)
        if not column.groupable:
            raise ValueError(f"{column.label} cannot be used to group.")
        select.append(f'{column.expr} AS "c{index}"')
        group_exprs.append(column.expr)
        result_columns.append(ResultColumn(f"c{index}", column.label, column.type, False))
    metric_exprs: list[str] = []
    for index, metric_spec in enumerate(spec.metrics):
        expr, label, fmt = _metric_sql(ds, metric_spec)
        select.append(f'{expr} AS "m{index}"')
        metric_exprs.append(expr)
        result_columns.append(ResultColumn(f"m{index}", label, "number", True, fmt))

    clauses, params = _where(ds, spec)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""

    series = ""
    series_params: list[Any] = []
    if spec.series_limit and len(group_exprs) >= 2 and metric_exprs:
        if spec.series_limit < 1:
            raise ValueError("The series limit must be at least 1.")
        last = group_exprs[-1]
        series = (
            f"{' AND' if where else ' WHERE'} {last} IN (SELECT {last} FROM {ds.from_sql}{where} "
            f"GROUP BY {last} ORDER BY {metric_exprs[0]} DESC NULLS LAST LIMIT ?)"
        )
        series_params = [*params, int(spec.series_limit)]

    keys = [column.key for column in result_columns]
    order_key = spec.order_by or ("m0" if metric_exprs else "c0")
    if order_key not in keys:
        raise ValueError(f"Cannot order by '{order_key}'.")
    direction = "DESC" if spec.order_desc else "ASC"

    sql = f"SELECT {', '.join(select)} FROM {ds.from_sql}{where}{series}"
    if group_exprs:  # without metrics this lists the distinct combinations
        sql += f" GROUP BY {', '.join(str(i + 1) for i in range(len(group_exprs)))}"
    sql += f' ORDER BY "{order_key}" {direction} NULLS LAST LIMIT ?'
    return sql, [*params, *series_params, spec.row_limit + 1], result_columns


def _plain(value: Any) -> Any:
    """JSON-friendly values (DuckDB returns Decimal for some aggregates)."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


def run_query(db_path: Path, spec: QuerySpec) -> QueryResult:
    sql, params, columns = build_query(spec)
    started = time.perf_counter()
    rows = fetch(db_path, sql, params)
    duration = (time.perf_counter() - started) * 1000
    truncated = len(rows) > spec.row_limit
    rows = rows[: spec.row_limit]
    return QueryResult(
        columns=columns,
        rows=[[_plain(value) for value in row] for row in rows],
        sql=sql,
        params=params,
        row_count=len(rows),
        duration_ms=round(duration, 1),
        truncated=truncated,
    )


def samples(db_path: Path, spec: QuerySpec) -> QueryResult:
    """Raw rows of the dataset (every column) under the spec's filters, like Superset's samples."""
    ds = dataset(spec.dataset)
    clauses, params = _where(ds, spec)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    select = ", ".join(f'{column.expr} AS "c{i}"' for i, column in enumerate(ds.columns))
    sql = f"SELECT {select} FROM {ds.from_sql}{where} LIMIT ?"
    started = time.perf_counter()
    rows = fetch(db_path, sql, [*params, SAMPLE_ROWS])
    return QueryResult(
        columns=[
            ResultColumn(f"c{i}", column.label, column.type, False)
            for i, column in enumerate(ds.columns)
        ],
        rows=[[_plain(value) for value in row] for row in rows],
        sql=sql,
        params=[*params, SAMPLE_ROWS],
        row_count=len(rows),
        duration_ms=round((time.perf_counter() - started) * 1000, 1),
    )


def column_values(
    db_path: Path, dataset_name: str, column_name: str, search: str = ""
) -> list[Any]:
    """The most common values of a column (for filter pickers), optionally matching a search."""
    ds = dataset(dataset_name)
    column = ds.column(column_name)
    params: list[Any] = []
    where = f" WHERE {column.expr} IS NOT NULL"
    if search:
        escaped = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        where += f" AND CAST({column.expr} AS VARCHAR) ILIKE ? ESCAPE '\\'"
        params.append(f"%{escaped}%")
    sql = (
        f"SELECT {column.expr} AS value FROM {ds.from_sql}{where} "
        f"GROUP BY 1 ORDER BY COUNT(*) DESC, 1 LIMIT ?"
    )
    return [_plain(row[0]) for row in fetch(db_path, sql, [*params, VALUES_LIMIT])]
