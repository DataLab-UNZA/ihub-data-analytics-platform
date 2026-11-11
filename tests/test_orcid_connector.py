"""Tests for the ORCID connector, using recorded responses (never the live API)."""

import json
from pathlib import Path

import httpx
import pytest

from ihub.connectors.orcid import OrcidConnector, OrcidError

FIXTURES = Path(__file__).parent / "fixtures"
SEARCH = json.loads((FIXTURES / "orcid_search_sample.json").read_text(encoding="utf-8"))
WORKS = json.loads((FIXTURES / "orcid_works_sample.json").read_text(encoding="utf-8"))
EMPLOYMENTS = json.loads((FIXTURES / "orcid_employments_sample.json").read_text(encoding="utf-8"))
IDS = [item["orcid-identifier"]["path"] for item in SEARCH["result"]]

CONFIG = {
    "base_url": "https://pub.orcid.org/v3.0",
    "token_url": "https://orcid.org/oauth/token",
    "search_query": 'ror-org-id:"https://ror.org/03gh19d69"',
}


@pytest.fixture(autouse=True)
def fake_credentials(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCID_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("ORCID_CLIENT_SECRET", "secret-test-value")


def make_client(handler) -> httpx.Client:
    return httpx.Client(transport=httpx.MockTransport(handler))


def recorded_handler(request: httpx.Request) -> httpx.Response:
    path = request.url.path
    if path == "/oauth/token":
        return httpx.Response(200, json={"access_token": "test-token", "token_type": "bearer"})
    if path == "/v3.0/search/":
        return httpx.Response(200, json=SEARCH)
    if path.endswith("/works"):
        return httpx.Response(200, json=WORKS)
    if path.endswith("/employments"):
        return httpx.Response(200, json=EMPLOYMENTS)
    return httpx.Response(404)


def test_records_hold_works_and_employments_unchanged() -> None:
    connector = OrcidConnector(CONFIG, client=make_client(recorded_handler))
    records = list(connector.fetch_records())
    assert [record_id for record_id, _ in records] == IDS
    for record_id, payload in records:
        assert payload == {"orcid": record_id, "works": WORKS, "employments": EMPLOYMENTS}


def test_fetch_adds_source_and_fetch_time() -> None:
    records = list(OrcidConnector(CONFIG, client=make_client(recorded_handler)).fetch())
    assert len(records) == len(IDS)
    assert all(record.source == "orcid" for record in records)
    assert all(record.fetched_at is not None for record in records)


def test_token_request_uses_the_client_credentials() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return recorded_handler(request)

    list(OrcidConnector(CONFIG, client=make_client(handler)).fetch_records())
    form = seen[0].content.decode()
    assert seen[0].url.path == "/oauth/token"
    assert "client_id=test-client-id" in form
    assert "client_secret=secret-test-value" in form
    assert "grant_type=client_credentials" in form
    assert "scope=%2Fread-public" in form
    assert seen[1].headers["authorization"] == "Bearer test-token"


def test_search_uses_the_configured_query() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return recorded_handler(request)

    list(OrcidConnector(CONFIG, client=make_client(handler)).fetch_records())
    search = next(request for request in seen if request.url.path == "/v3.0/search/")
    assert search.url.params["q"] == CONFIG["search_query"]
    assert search.url.params["start"] == "0"


def test_search_pages_until_all_ids_are_found() -> None:
    pages = {
        "0": {"result": [SEARCH["result"][0], SEARCH["result"][1]], "num-found": 3},
        "2": {"result": [SEARCH["result"][2]], "num-found": 3},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/v3.0/search/":
            assert request.url.params["rows"] == "2"
            return httpx.Response(200, json=pages[request.url.params["start"]])
        return recorded_handler(request)

    connector = OrcidConnector({**CONFIG, "page_size": 2}, client=make_client(handler))
    assert [record_id for record_id, _ in connector.fetch_records()] == IDS


def test_client_error_does_not_leak_credentials() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/oauth/token":
            return httpx.Response(401)
        return recorded_handler(request)

    connector = OrcidConnector(CONFIG, client=make_client(handler))
    with pytest.raises(OrcidError) as excinfo:
        list(connector.fetch_records())
    assert "401" in str(excinfo.value)
    assert "secret-test-value" not in str(excinfo.value)
    assert "test-client-id" not in str(excinfo.value)


def test_missing_credentials_is_an_error(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCID_CLIENT_ID", "")
    monkeypatch.setenv("ORCID_CLIENT_SECRET", "")
    connector = OrcidConnector(CONFIG, client=make_client(recorded_handler))
    with pytest.raises(ValueError, match="ORCID_CLIENT_ID"):
        list(connector.fetch_records())


def test_missing_search_query_is_an_error() -> None:
    connector = OrcidConnector({"search_query": None}, client=make_client(recorded_handler))
    with pytest.raises(ValueError, match="search_query"):
        list(connector.fetch_records())
