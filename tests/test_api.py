"""Tests for the JSON API, using FastAPI's test client over the tiny hand-built mart."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ihub.api.app import create_app


@pytest.fixture
def client(insights_db: Path) -> TestClient:
    return TestClient(create_app(lambda: insights_db))


def test_health(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["mart_available"] is True


def test_overview_defaults_to_every_year(client: TestClient) -> None:
    body = client.get("/api/overview").json()
    assert body["years"] == {"start": 2019, "end": 2022}
    assert body["headline"]["publications"] == 5
    assert body["headline"]["open_access_share"] == pytest.approx(0.6)
    assert body["previous_years"] is None  # the data does not cover the earlier period
    assert [y["publications"] for y in body["per_year"]] == [1, 2, 0, 2]
    assert body["collaboration"]["summary"]["international_publications"] == 2


def test_overview_compares_with_the_previous_period(client: TestClient) -> None:
    body = client.get("/api/overview", params={"start": 2021, "end": 2022}).json()
    assert body["previous_years"] == {"start": 2019, "end": 2020}
    assert body["previous_headline"]["publications"] == 3
    assert body["headline"]["publications"] == 2


def test_publications_are_paged_and_filtered(client: TestClient) -> None:
    body = client.get("/api/publications", params={"page_size": 2}).json()
    assert body["total"] == 5
    assert body["pages"] == 3
    assert len(body["rows"]) == 2
    only_oa = client.get("/api/publications", params={"oa_status": ["gold", "green"]}).json()
    assert only_oa["total"] == 2
    found = client.get("/api/publications", params={"q": "maternal"}).json()
    assert [r["publication_key"] for r in found["rows"]] == ["p2"]


def test_bad_input_is_rejected(client: TestClient) -> None:
    assert client.get("/api/publications", params={"page": 0}).status_code == 422
    assert client.get("/api/publications", params={"page_size": 1000}).status_code == 422
    assert client.get("/api/publications", params={"source": "Nowhere"}).status_code == 400
    assert client.get("/api/overview", params={"start": 2022, "end": 2019}).status_code == 400


def test_publication_export_is_csv(client: TestClient) -> None:
    response = client.get("/api/publications/export", params={"q": "malaria"})
    assert response.headers["content-type"].startswith("text/csv")
    assert "attachment" in response.headers["content-disposition"]
    assert response.text.splitlines()[0].startswith("Title,Year")
    assert "Malaria in Zambia" in response.text


def test_publication_detail_and_not_found(client: TestClient) -> None:
    assert client.get("/api/publications/p2").json()["title"] == "Maternal health"
    assert client.get("/api/publications/nope").status_code == 404


def test_the_other_endpoints_answer(client: TestClient) -> None:
    for path in ("filters", "journals", "topics", "organisation", "collaboration", "sources"):
        assert client.get(f"/api/{path}").status_code == 200, path
    coverage = client.get("/api/coverage").json()
    assert coverage["publications"] == 5
    assert len(coverage["gaps"]) == 3
    assert {s["code"] for s in coverage["sources"]} == {"openalex", "orcid", "dspace_oai", "ojs"}


def test_a_missing_mart_is_a_503(tmp_path: Path) -> None:
    client = TestClient(create_app(lambda: tmp_path / "missing.duckdb"))
    assert client.get("/api/overview").status_code == 503
    assert client.get("/api/health").json()["mart_available"] is False
