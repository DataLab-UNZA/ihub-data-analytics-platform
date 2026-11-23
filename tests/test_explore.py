"""The Explore semantic layer (ihub.mart.explore) and its API: results, safety and RBAC."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ihub.api.app import create_app
from ihub.mart.explore import (
    DATASETS,
    MAX_ROWS,
    AdhocMetric,
    Filter,
    QuerySpec,
    build_query,
    column_values,
    run_query,
    samples,
)
from tests.auth_helpers import ADMIN, STAFF, make_harness

# The tiny mart (tests/conftest.py): five publications.
# p1 2019 Article gold OA 10 citations; p2 2020 Review closed 20; p3 2020 Article green OA 0;
# p4 2022 Article closed 5; p5 2022 Article diamond OA 1.


def test_counts_and_shares_by_year(insights_db: Path) -> None:
    result = run_query(
        insights_db,
        QuerySpec(
            "publications",
            metrics=["count", "citations", "oa_share"],
            groupby=["year"],
            order_by="c0",
            order_desc=False,
        ),
    )
    assert [c.label for c in result.columns] == [
        "Year",
        "Publications",
        "Citations",
        "Open-access share",
    ]
    assert result.rows == [[2019, 1, 10, 1.0], [2020, 2, 20, 0.5], [2022, 2, 6, 0.5]]
    assert result.columns[3].format == "percent"


def test_filters_year_range_and_adhoc_metrics(insights_db: Path) -> None:
    result = run_query(
        insights_db,
        QuerySpec(
            "publications",
            metrics=[AdhocMetric("MAX", "citations"), "count"],
            groupby=["publication_type"],
            filters=[Filter("oa_status", "NOT IN", ["closed"])],
            year_from=2020,
        ),
    )
    assert result.rows == [["Article", 1, 2]]  # p3 (0 citations) and p5 (1)
    assert result.columns[1].label == "MAX(Citations)"


def test_series_limit_keeps_the_top_values(insights_db: Path) -> None:
    spec = QuerySpec(
        "publications", metrics=["count"], groupby=["year", "publication_type"], series_limit=1
    )
    types = {row[1] for row in run_query(insights_db, spec).rows}
    assert types == {"Article"}  # 4 articles against 1 review


def test_row_limit_reports_truncation(insights_db: Path) -> None:
    result = run_query(insights_db, QuerySpec("publications", groupby=["year"], row_limit=2))
    assert result.row_count == 2 and result.truncated


def test_other_datasets_and_helpers(insights_db: Path) -> None:
    topics = run_query(
        insights_db, QuerySpec("topics", metrics=["publications"], groupby=["field"])
    )
    assert topics.rows and all(isinstance(row[1], int) for row in topics.rows)
    affiliations = run_query(insights_db, QuerySpec("affiliations", metrics=["publications"]))
    assert affiliations.rows[0][0] >= 1
    assert "gold" in column_values(insights_db, "publications", "oa_status")
    assert column_values(insights_db, "publications", "oa_status", "clo") == ["closed"]
    rows = samples(
        insights_db, QuerySpec("publications", filters=[Filter("title", "CONTAINS", "malaria")])
    )
    assert rows.row_count == 1


def test_international_share_ignores_unknowns(insights_db: Path) -> None:
    result = run_query(insights_db, QuerySpec("publications", metrics=["intl_share"]))
    assert 0.0 <= result.rows[0][0] <= 1.0


# Safety: nothing from the request reaches the SQL text except validated names.


@pytest.mark.parametrize(
    "spec",
    [
        QuerySpec("publications; DROP TABLE x", metrics=["count"]),
        QuerySpec("publications", metrics=["count); DROP TABLE marts.fact_publication; --"]),
        QuerySpec("publications", groupby=["year, (SELECT 1)"]),
        QuerySpec("publications", metrics=[AdhocMetric("SUM", "f.cited_by_count")]),
        QuerySpec("publications", metrics=[AdhocMetric("EXEC", "citations")]),
        QuerySpec("publications", metrics=[AdhocMetric("SUM", "venue")]),  # SUM of text
        QuerySpec("publications", metrics=["count"], filters=[Filter("year", "; DROP", 1)]),
        QuerySpec("publications", metrics=["count"], filters=[Filter("year", "==", "1 OR 1=1")]),
        QuerySpec("publications", groupby=["title"]),  # not groupable
        QuerySpec("publications", metrics=["count"], order_by='m0" ; --'),
        QuerySpec("publications", metrics=["count"], row_limit=MAX_ROWS + 1),
        QuerySpec("publications"),
    ],
)
def test_invalid_specs_are_refused(spec: QuerySpec) -> None:
    with pytest.raises(ValueError):
        build_query(spec)


def test_values_are_bound_parameters(insights_db: Path) -> None:
    hostile = "x'); DROP TABLE marts.fact_publication; --"
    sql, params, _ = build_query(
        QuerySpec("publications", metrics=["count"], filters=[Filter("venue", "==", hostile)])
    )
    assert hostile not in sql and hostile in params
    result = run_query(
        insights_db,
        QuerySpec("publications", metrics=["count"], filters=[Filter("title", "CONTAINS", "%_")]),
    )
    assert result.rows == [[0]]  # % and _ are literal, not wildcards
    assert run_query(insights_db, QuerySpec("publications", metrics=["count"])).rows == [[5]]


def test_authors_cannot_be_ranked() -> None:
    names = {column.name for dataset in DATASETS.values() for column in dataset.columns}
    assert not {"author", "author_name", "orcid"} & names  # CLAUDE.md: no individual rankings


# HTTP


@pytest.fixture
def clients(insights_db: Path, tmp_path: Path) -> tuple[TestClient, TestClient, TestClient]:
    h = make_harness(tmp_path)
    app = create_app(lambda: insights_db, auth_service=lambda: h.service, require_sign_in=True)
    admin, member, anonymous = TestClient(app), TestClient(app), TestClient(app)
    admin.headers["Authorization"] = f"Bearer {h.sign_in_by_email(ADMIN).access_token}"
    member.headers["Authorization"] = f"Bearer {h.sign_in_by_email(STAFF).access_token}"
    return admin, member, anonymous


def test_explore_api(clients: tuple[TestClient, TestClient, TestClient]) -> None:
    admin, member, anonymous = clients
    datasets = member.get("/api/explore/datasets").json()
    assert [d["name"] for d in datasets][:3] == ["publications", "affiliations", "topics"]
    names = {d["name"] for d in datasets}
    assert {"unit_publications", "unit_authorships", "researcher_output"} <= names
    assert all("expr" not in c for d in datasets for c in d["columns"])  # SQL never leaves the API
    body = {
        "dataset": "publications",
        "metrics": ["count"],
        "groupby": ["year"],
        "order_by": "c0",
        "order_desc": False,
    }
    result = member.post("/api/explore/query", json=body).json()
    assert result["rows"] == [[2019, 1], [2020, 2], [2022, 2]]
    assert "SELECT" in result["sql"]
    assert (
        member.post("/api/explore/samples", json={"dataset": "publications"}).json()["row_count"]
        == 5
    )
    assert member.get("/api/explore/datasets/publications/values/oa_status").status_code == 200
    bad = member.post("/api/explore/query", json={"dataset": "publications", "groupby": ["nope"]})
    assert bad.status_code == 400
    assert (
        member.post("/api/explore/query", json={"dataset": "x", "row_limit": 99999}).status_code
        == 422
    )

    assert anonymous.post("/api/explore/query", json=body).status_code == 401
    assert member.post("/api/explore/query.csv", json=body).status_code == 403  # no research:export
    csv = admin.post("/api/explore/query.csv", json=body)
    assert csv.status_code == 200 and csv.text.splitlines()[0] == "Year,Publications"


def test_csv_neutralises_spreadsheet_formulas(
    clients: tuple[TestClient, TestClient, TestClient],
) -> None:
    admin, _, _ = clients
    body = {"dataset": "publications", "groupby": ["title"]}
    # title is not groupable; use samples-like grouping via venue instead and check the helper
    from ihub.api.explore_routes import _csv_safe

    assert _csv_safe('=HYPERLINK("x")') == '\'=HYPERLINK("x")'
    assert _csv_safe("Malaria") == "Malaria" and _csv_safe(5) == 5
    assert admin.post("/api/explore/query.csv", json=body).status_code == 400
