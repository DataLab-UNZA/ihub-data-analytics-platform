"""Tests for the OpenAlex connector, using a recorded response (never the live API)."""

import json
from pathlib import Path

import httpx
import pytest

from ihub.connectors.openalex import OpenAlexConnector, OpenAlexError

FIXTURE = Path(__file__).parent / "fixtures" / "openalex_works_sample.json"
CONFIG = {
    "base_url": "https://api.openalex.org",
    "institution_id": "I-TEST",
    "year_from": 2015,
}


@pytest.fixture(autouse=True)
def no_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_MAILTO", "")
    monkeypatch.setenv("OPENALEX_API_KEY", "")


def make_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def recorded_handler(request: httpx.Request) -> httpx.Response:
    if request.url.params["cursor"] == "*":
        return httpx.Response(200, json=json.loads(FIXTURE.read_text(encoding="utf-8")))
    return httpx.Response(200, json={"results": [], "meta": {"next_cursor": None}})


def test_records_are_returned_unchanged() -> None:
    recorded = json.loads(FIXTURE.read_text(encoding="utf-8"))["results"]
    connector = OpenAlexConnector(CONFIG, client=make_client(recorded_handler))
    records = list(connector.fetch_records())
    assert records
    assert [payload for _, payload in records] == recorded
    assert [record_id for record_id, _ in records] == [work["id"] for work in recorded]


def test_fetch_adds_source_and_fetch_time() -> None:
    connector = OpenAlexConnector(CONFIG, client=make_client(recorded_handler))
    records = list(connector.fetch())
    assert records
    assert all(record.source == "openalex" for record in records)
    assert all(record.fetched_at is not None for record in records)


def test_request_filters_by_institution_and_year() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return recorded_handler(request)

    list(OpenAlexConnector(CONFIG, client=make_client(handler)).fetch_records())
    assert seen[0].url.params["filter"] == (
        "authorships.institutions.id:I-TEST,from_publication_date:2015-01-01"
    )
    assert seen[0].url.params["per_page"] == "100"


def test_follows_cursor_until_exhausted() -> None:
    pages = {
        "*": {"results": [{"id": "W1"}], "meta": {"next_cursor": "next"}},
        "next": {"results": [{"id": "W2"}], "meta": {"next_cursor": None}},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=pages[request.url.params["cursor"]])

    connector = OpenAlexConnector(CONFIG, client=make_client(handler))
    assert [record_id for record_id, _ in connector.fetch_records()] == ["W1", "W2"]


def test_sends_mailto_and_api_key_only_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"results": [], "meta": {"next_cursor": None}})

    list(OpenAlexConnector(CONFIG, client=make_client(handler)).fetch_records())
    assert "mailto" not in seen[0].url.params
    assert "api_key" not in seen[0].url.params

    monkeypatch.setenv("OPENALEX_MAILTO", "student@example.org")
    monkeypatch.setenv("OPENALEX_API_KEY", "test-key")
    list(OpenAlexConnector(CONFIG, client=make_client(handler)).fetch_records())
    assert seen[1].url.params["mailto"] == "student@example.org"
    assert seen[1].url.params["api_key"] == "test-key"


def test_client_error_does_not_leak_the_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "secret-test-key")
    connector = OpenAlexConnector(CONFIG, client=make_client(lambda request: httpx.Response(403)))
    with pytest.raises(OpenAlexError) as excinfo:
        list(connector.fetch_records())
    assert "403" in str(excinfo.value)
    assert "secret-test-key" not in str(excinfo.value)


def test_missing_institution_id_is_an_error() -> None:
    connector = OpenAlexConnector({"institution_id": None})
    with pytest.raises(ValueError, match="institution_id"):
        list(connector.fetch_records())
