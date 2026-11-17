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
from collections.abc import Callable, Iterator, Mapping, Sequence
from contextlib import contextmanager
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

import duckdb

from ihub.mart._duckdb import connect

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
    #: Orders the groups of this column in charts (bands such as "2-4" before "10-19").
    sort_expr: str = ""


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
    time_column: str = "year"  # "" when the rows have no year (the year range is then refused)
    #: Names of the temporary tables (:data:`TEMP_TABLES`) the dataset joins; the API fills them.
    tables: tuple[str, ...] = ()

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


#: Temporary tables that carry what only Python knows (school credit from the staff roster,
#: ADR-012), loaded per query: name -> column names. Values are bound parameters.
TEMP_TABLES: dict[str, tuple[str, str]] = {
    "unit_pub": ("unit", "publication_key"),
    "author_unit": ("author_key", "unit"),
}
#: Called with the names a query needs; returns name -> rows of the temporary table.
TablesProvider = Callable[[frozenset[str]], Mapping[str, Sequence[tuple[str, str]]]]


def _band(expr: str, edges: Sequence[tuple[int, str]], last: str) -> tuple[str, str]:
    """A CASE expression for the label of a numeric band, and one for its sort position.

    ``edges`` are (inclusive upper bound, label) in ascending order; ``last`` labels the rest.
    """
    labels = " ".join(f"WHEN {expr} <= {upper} THEN '{label}'" for upper, label in edges)
    order = " ".join(f"WHEN {expr} <= {upper} THEN {i}" for i, (upper, _) in enumerate(edges))
    return f"CASE {labels} ELSE '{last}' END", f"CASE {order} ELSE {len(edges)} END"


_CITATION_BAND = _band(
    "f.cited_by_count",
    [(0, "0"), (1, "1"), (4, "2\u20134"), (9, "5\u20139"), (19, "10\u201319"), (49, "20\u201349")]
    + [(99, "50\u201399")],
    "100+",
)
_TEAM_BAND = _band(
    "f.n_authors",
    [(1, "1 author"), (3, "2\u20133 authors"), (6, "4\u20136 authors"), (10, "7\u201310 authors")],
    "More than 10 authors",
)
_PRODUCTIVITY_BAND = _band(
    "pr.n",
    [(1, "1"), (2, "2"), (4, "3\u20134"), (9, "5\u20139"), (19, "10\u201319"), (49, "20\u201349")],
    "50+",
)
_SOURCES = (
    "COALESCE(NULLIF(concat_ws(' + ', CASE WHEN f.in_openalex THEN 'OpenAlex' END, "
    "CASE WHEN f.in_repository THEN 'Repository' END, "
    "CASE WHEN f.in_ojs THEN 'UNZA journals' END), ''), 'None of these three')"
)
_YEAR = Column("year", "Year", "year", "y.year")
_SCHOOL_PUBLICATION_FROM = (
    "temp.unit_pub up "
    "JOIN marts.fact_publication f ON f.publication_key = up.publication_key "
    "JOIN marts.dim_publication p ON p.publication_key = f.publication_key "
    "LEFT JOIN marts.dim_year y ON y.year_key = f.year_key "
    "LEFT JOIN marts.dim_publication_type t ON t.type_key = f.type_key"
)
_SHARE = "AVG(CASE WHEN {} THEN 1.0 ELSE 0.0 END)"

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
                Column("decade", "Decade", "string", "y.decade_label", sort_expr="y.decade_start"),
                Column("publication_type", "Publication type", "string", "t.type_label"),
                Column("venue", "Venue", "string", "v.venue_name"),
                Column(
                    "venue_kind",
                    "Venue kind",
                    "string",
                    "CASE WHEN f.in_ojs THEN 'UNZA journals (OJS)' ELSE 'Other venues' END",
                ),
                Column(
                    "citation_band",
                    "Citation band",
                    "string",
                    _CITATION_BAND[0],
                    sort_expr=_CITATION_BAND[1],
                ),
                Column(
                    "team_size",
                    "Team size",
                    "string",
                    _TEAM_BAND[0],
                    sort_expr=_TEAM_BAND[1],
                ),
                Column(
                    "sources_found_in",
                    "Sources the publication is in",
                    "string",
                    _SOURCES,
                    description="OpenAlex, the repository and UNZA journals (OJS).",
                ),
                Column("publication", "Publication (title)", "string", "p.title"),
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
                Metric(
                    "median_citations",
                    "Median citations per publication",
                    "MEDIAN(f.cited_by_count)",
                    "decimal",
                    "The typical paper: half have more citations, half fewer.",
                ),
                Metric(
                    "median_authors",
                    "Median team size",
                    "MEDIAN(CAST(f.n_authors AS DOUBLE))",
                    "decimal",
                    "Authors per publication.",
                ),
                Metric(
                    "p25_authors",
                    "Small teams (25th percentile)",
                    "QUANTILE_CONT(CAST(f.n_authors AS DOUBLE), 0.25)",
                    "decimal",
                ),
                Metric(
                    "p75_authors",
                    "Large teams (75th percentile)",
                    "QUANTILE_CONT(CAST(f.n_authors AS DOUBLE), 0.75)",
                    "decimal",
                ),
                Metric(
                    "doi_share",
                    "With a DOI",
                    _SHARE.format("p.doi IS NOT NULL AND p.doi <> ''"),
                    "percent",
                ),
                Metric(
                    "venue_share",
                    "With a known venue",
                    _SHARE.format("v.venue_name IS NOT NULL AND v.venue_name <> 'Unknown venue'"),
                    "percent",
                ),
                Metric(
                    "type_share",
                    "With a known type",
                    _SHARE.format("t.type_label IS NOT NULL AND t.type_label <> 'Unknown'"),
                    "percent",
                ),
                Metric(
                    "year_share",
                    "With a publication year",
                    _SHARE.format("f.year_key IS NOT NULL"),
                    "percent",
                ),
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
                Column("organisation_type", "Organisation type", "string", "o.org_type"),
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
        Dataset(
            name="unit_publications",
            label="Publications by school",
            description=(
                "One row per publication and school credited with it (staff roster when "
                "available, otherwise department evidence). A publication with authors in "
                "several schools appears once for each."
            ),
            from_sql=_SCHOOL_PUBLICATION_FROM,
            tables=("unit_pub",),
            columns=(
                _YEAR,
                Column("school", "School", "string", "up.unit"),
                Column("publication_type", "Publication type", "string", "t.type_label"),
                Column("oa_status", "Open-access status", "string", "f.oa_status"),
                Column("is_oa", "Open access", "boolean", "f.is_oa"),
                Column(
                    "international_collab",
                    "International collaboration",
                    "boolean",
                    "f.is_international_collab",
                ),
                Column(
                    "citation_band",
                    "Citation band",
                    "string",
                    _CITATION_BAND[0],
                    sort_expr=_CITATION_BAND[1],
                ),
            ),
            metrics=(
                Metric("publications", "Publications", "COUNT(*)"),
                Metric("citations", "Citations", "SUM(f.cited_by_count)"),
                Metric(
                    "avg_citations", "Citations per publication", "AVG(f.cited_by_count)", "decimal"
                ),
                Metric(
                    "median_citations",
                    "Median citations per publication",
                    "MEDIAN(f.cited_by_count)",
                    "decimal",
                ),
                Metric("oa_share", "Open-access share", _SHARE.format("f.is_oa"), "percent"),
                Metric(
                    "intl_share",
                    "International share",
                    "AVG(CASE WHEN f.is_international_collab THEN 1.0 "
                    "WHEN NOT f.is_international_collab THEN 0.0 END)",
                    "percent",
                ),
                Metric(
                    "avg_authors",
                    "Authors per publication",
                    "AVG(CAST(f.n_authors AS DOUBLE))",
                    "decimal",
                ),
            ),
        ),
        Dataset(
            name="unit_authorships",
            label="Authorships by school",
            description=(
                "One row per publication, author and organisation, for authors linked to a "
                "school. Counts roles only; individuals are never listed."
            ),
            from_sql=(
                "marts.fact_authorship a "
                "JOIN temp.author_unit au ON au.author_key = a.author_key "
                "LEFT JOIN marts.dim_year y ON y.year_key = a.year_key"
            ),
            tables=("author_unit",),
            columns=(
                _YEAR,
                Column("school", "School", "string", "au.unit"),
                Column(
                    "author_role",
                    "Author role",
                    "string",
                    "CASE WHEN a.is_corresponding THEN 'Corresponding author' "
                    "WHEN a.author_position = 1 THEN 'First author' ELSE 'Other author' END",
                    description="Corresponding wins over first; everyone else is 'Other'.",
                ),
            ),
            metrics=(
                Metric(
                    "authorships",
                    "Authorships",
                    "COUNT(DISTINCT a.publication_key || '|' || a.author_key)",
                ),
                Metric("researchers", "Researchers", "COUNT(DISTINCT a.author_key)"),
            ),
        ),
        Dataset(
            name="unit_researchers",
            label="Researchers by school",
            description="One row per UNZA author linked to a school (counts only, no names).",
            from_sql=(
                "temp.author_unit au JOIN marts.dim_author d ON d.author_key = au.author_key"
            ),
            tables=("author_unit",),
            time_column="",
            columns=(
                Column("school", "School", "string", "au.unit"),
                Column("has_orcid", "Has an ORCID iD", "boolean", "d.orcid_id IS NOT NULL"),
            ),
            metrics=(
                Metric("researchers", "Researchers", "COUNT(DISTINCT d.author_key)"),
                Metric(
                    "orcid_share",
                    "ORCID adoption",
                    _SHARE.format("d.orcid_id IS NOT NULL"),
                    "percent",
                ),
            ),
        ),
        Dataset(
            name="researcher_output",
            label="Output per researcher",
            description=(
                "UNZA authors grouped by how many publications they have (counts only, "
                "no names, so no one is ranked)."
            ),
            from_sql=(
                "(SELECT a.author_key, COUNT(DISTINCT a.publication_key) AS n "
                "FROM marts.fact_authorship a "
                "JOIN marts.dim_author d ON d.author_key = a.author_key WHERE d.is_unza_author "
                "GROUP BY a.author_key) pr"
            ),
            time_column="",
            columns=(
                Column(
                    "publications_band",
                    "Publications per researcher",
                    "string",
                    _PRODUCTIVITY_BAND[0],
                    sort_expr=_PRODUCTIVITY_BAND[1],
                ),
            ),
            metrics=(
                Metric("researchers", "Researchers", "COUNT(*)"),
                Metric("avg_publications", "Average publications", "AVG(pr.n)", "decimal"),
            ),
        ),
        Dataset(
            name="unit_topics",
            label="Topics by school",
            description="Publications by OpenAlex topic and the school credited with them.",
            from_sql=(
                "marts.bridge_publication_topic bt "
                "JOIN marts.dim_topic tp ON tp.topic_key = bt.topic_key "
                "JOIN marts.fact_publication f ON f.publication_key = bt.publication_key "
                "JOIN temp.unit_pub up ON up.publication_key = bt.publication_key "
                "LEFT JOIN marts.dim_year y ON y.year_key = f.year_key"
            ),
            tables=("unit_pub",),
            columns=(
                _YEAR,
                Column("school", "School", "string", "up.unit"),
                Column("topic", "Topic", "string", "tp.topic_name"),
                Column("subfield", "Subfield", "string", "tp.subfield_name"),
                Column("field", "Field", "string", "tp.field_name"),
                Column("domain", "Domain", "string", "tp.domain_name"),
            ),
            metrics=(Metric("publications", "Publications", "COUNT(DISTINCT bt.publication_key)"),),
        ),
        Dataset(
            name="school_collaboration",
            label="School-to-school co-authorship",
            description="Pairs of schools credited with the same publication.",
            from_sql=(
                "temp.unit_pub a "
                "JOIN temp.unit_pub b "
                "ON b.publication_key = a.publication_key AND b.unit <> a.unit "
                "JOIN marts.fact_publication f ON f.publication_key = a.publication_key "
                "LEFT JOIN marts.dim_year y ON y.year_key = f.year_key"
            ),
            tables=("unit_pub",),
            columns=(
                _YEAR,
                Column("school", "School", "string", "a.unit"),
                Column("partner_school", "Partner school", "string", "b.unit"),
            ),
            metrics=(
                Metric("publications", "Shared publications", "COUNT(DISTINCT a.publication_key)"),
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
    #: Post-processing of a one-group-by result: ``rolling3`` adds a 3-year average,
    #: ``yoy`` replaces the metric by its change on the previous year, ``cumulative_share``
    #: adds the running share of the total (a Pareto chart).
    transform: str | None = None


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
    if not ds.time_column and (spec.year_from is not None or spec.year_to is not None):
        raise ValueError(f"The {ds.label} dataset has no year, so it cannot be limited by years.")
    year = ds.column(ds.time_column).expr if ds.time_column else ""
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
    order_expr = f'"{order_key}"'
    if order_key.startswith("c") and group_exprs:
        sorter = ds.column(spec.groupby[int(order_key[1:])]).sort_expr
        if sorter:  # bands: "2-4" before "10-19"
            order_expr = f"MIN({sorter})"

    sql = f"SELECT {', '.join(select)} FROM {ds.from_sql}{where}{series}"
    if group_exprs:  # without metrics this lists the distinct combinations
        sql += f" GROUP BY {', '.join(str(i + 1) for i in range(len(group_exprs)))}"
    sql += f" ORDER BY {order_expr} {direction} NULLS LAST LIMIT ?"
    return sql, [*params, *series_params, spec.row_limit + 1], result_columns


def _plain(value: Any) -> Any:
    """JSON-friendly values (DuckDB returns Decimal for some aggregates)."""
    if value is None or isinstance(value, bool | int | float | str):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return str(value)


TRANSFORMS = {
    "rolling3": "a 3-year average next to the metric",
    "yoy": "the change on the previous year, as a percentage",
    "cumulative_share": "the running share of the total (a Pareto chart)",
}


@contextmanager
def _session(
    db_path: Path, ds: Dataset, tables: TablesProvider | None
) -> Iterator[duckdb.DuckDBPyConnection]:
    """A read-only connection with the temporary tables the dataset joins."""
    with connect(db_path) as con:
        if ds.tables:
            if tables is None:
                raise ValueError(f"The {ds.label} dataset is not available here.")
            loaded = tables(frozenset(ds.tables))
            for name in ds.tables:
                first, second = TEMP_TABLES[name]  # trusted names, never user input
                con.execute(f"CREATE TEMP TABLE {name} ({first} VARCHAR, {second} VARCHAR)")
                rows = list(loaded.get(name, ()))
                if rows:  # two list parameters, unnested: one statement however many rows
                    con.execute(
                        f"INSERT INTO {name} SELECT unnest(?), unnest(?)",  # noqa: S608
                        [[row[0] for row in rows], [row[1] for row in rows]],
                    )
        yield con


def _check_transform(spec: QuerySpec) -> str | None:
    if spec.transform is None:
        return None
    if spec.transform not in TRANSFORMS:
        raise ValueError(f"Unknown transform '{spec.transform}'.")
    if len(spec.groupby) != 1 or not spec.metrics:
        raise ValueError("This option needs one group-by column and a metric.")
    return spec.transform


def _apply_transform(result: QueryResult, spec: QuerySpec, transform: str | None) -> QueryResult:
    """Add the running share, the 3-year average or the yearly change to a one-group-by result."""
    if transform is None:
        return result
    column = result.columns[0]
    value_index = 1
    if transform == "cumulative_share":
        rows = [list(row) for row in result.rows]
        total = sum(row[value_index] or 0 for row in rows)
        running = 0.0
        for row in rows:
            running += row[value_index] or 0
            row.append(running / total if total else None)
        truncated = len(rows) > spec.row_limit
        rows = rows[: spec.row_limit]
        columns = [
            *result.columns,
            ResultColumn("t0", "Cumulative share", "number", True, "percent"),
        ]
        return replace(result, columns=columns, rows=rows, row_count=len(rows), truncated=truncated)

    if column.type not in ("year", "number"):
        raise ValueError("This option needs a number or year to group by.")
    rows = sorted((list(row) for row in result.rows if row[0] is not None), key=lambda row: row[0])
    values = {row[0]: row[value_index] for row in rows}
    if transform == "rolling3":
        for position, row in enumerate(rows):
            window = [values.get(row[0] - back) for back in range(3)]
            ready = position >= 2 and all(v is not None for v in window)
            row.append(sum(window) / 3 if ready else None)
        columns = [*result.columns, ResultColumn("t0", "3-year average", "number", True, "decimal")]
        return replace(result, columns=columns, rows=rows, row_count=len(rows))
    # yoy: replace the metrics by their change on the previous year
    changed = []
    for row in rows:
        previous = values.get(row[0] - 1)
        now = row[value_index]
        change = (now - previous) / previous if previous and now is not None else None
        changed.append([row[0], change])
    columns = [column, ResultColumn("t0", "Change on previous year", "number", True, "percent")]
    return replace(result, columns=columns, rows=changed, row_count=len(changed))


def run_query(db_path: Path, spec: QuerySpec, tables: TablesProvider | None = None) -> QueryResult:
    ds = dataset(spec.dataset)
    transform = _check_transform(spec)
    # A Pareto share needs every group, so the limit is applied after it is computed.
    run_spec = replace(spec, row_limit=MAX_ROWS) if transform == "cumulative_share" else spec
    sql, params, columns = build_query(run_spec)
    started = time.perf_counter()
    with _session(db_path, ds, tables) as con:
        rows = con.execute(sql, params).fetchall()
    duration = (time.perf_counter() - started) * 1000
    truncated = len(rows) > run_spec.row_limit
    rows = rows[: run_spec.row_limit]
    result = QueryResult(
        columns=columns,
        rows=[[_plain(value) for value in row] for row in rows],
        sql=sql,
        params=params,
        row_count=len(rows),
        duration_ms=round(duration, 1),
        truncated=truncated,
    )
    return _apply_transform(result, spec, transform)


def samples(db_path: Path, spec: QuerySpec, tables: TablesProvider | None = None) -> QueryResult:
    """Raw rows of the dataset (every column) under the spec's filters, like Superset's samples."""
    ds = dataset(spec.dataset)
    clauses, params = _where(ds, spec)
    where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
    select = ", ".join(f'{column.expr} AS "c{i}"' for i, column in enumerate(ds.columns))
    sql = f"SELECT {select} FROM {ds.from_sql}{where} LIMIT ?"
    started = time.perf_counter()
    with _session(db_path, ds, tables) as con:
        rows = con.execute(sql, [*params, SAMPLE_ROWS]).fetchall()
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
    db_path: Path,
    dataset_name: str,
    column_name: str,
    search: str = "",
    tables: TablesProvider | None = None,
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
    with _session(db_path, ds, tables) as con:
        rows = con.execute(sql, [*params, VALUES_LIMIT]).fetchall()
    return [_plain(row[0]) for row in rows]
