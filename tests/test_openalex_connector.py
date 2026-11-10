"""Tests for the OpenAlex connector, using a recorded response (never the live API)."""

import json
from pathlib import Path

import duckdb
import httpx
import pytest

from ihub.connectors.openalex import OpenAlexConnector, OpenAlexError, OpenAlexIncompleteError
from ihub.ingest.__main__ import configure_logging, load_source_config
from ihub.ingest.raw import write_raw

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
        body = json.loads(FIXTURE.read_text(encoding="utf-8"))
        # The fixture is a short extract of a longer result set: say that all of it is here.
        body["meta"]["count"] = len(body["results"])
        return httpx.Response(200, json=body)
    return httpx.Response(200, json={"results": [], "meta": {"next_cursor": None}})


def pages_handler(*pages: dict, count: int | None):
    """Serve ``pages`` in order (each with a next cursor except the last), reporting ``count``."""

    def handler(request: httpx.Request) -> httpx.Response:
        cursor = request.url.params["cursor"]
        index = 0 if cursor == "*" else int(cursor)
        meta = {"next_cursor": str(index + 1) if index + 1 < len(pages) else None}
        if count is not None:
            meta["count"] = count
        return httpx.Response(200, json={"results": pages[index]["results"], "meta": meta})

    return handler


def works(*ids: str) -> dict:
    return {"results": [{"id": i} for i in ids]}


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


def test_no_year_filter_is_sent_unless_one_is_configured() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return recorded_handler(request)

    config = {"base_url": "https://api.openalex.org", "institution_id": "I-TEST"}
    list(OpenAlexConnector(config, client=make_client(handler)).fetch_records())
    assert seen[0].url.params["filter"] == "authorships.institutions.id:I-TEST"


def test_institution_url_form_is_reduced_to_its_id() -> None:
    config = {"institution_id": "https://openalex.org/I33278361"}
    assert OpenAlexConnector(config)._works_filter() == "authorships.institutions.id:I33278361"


def first_request_params(config: dict) -> httpx.QueryParams:
    """Run a fetch with ``config`` and return the parameters of its first request."""
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json={"results": [], "meta": {"next_cursor": None}})

    list(OpenAlexConnector(config, client=make_client(handler)).fetch_records())
    return seen[0].url.params


def test_xpac_works_are_requested_by_default_and_can_be_switched_off() -> None:
    assert first_request_params(CONFIG)["include_xpac"] == "true"
    assert "include_xpac" not in first_request_params({**CONFIG, "include_xpac": False})


def test_duplicate_deliveries_are_passed_through_and_counted_once() -> None:
    handler = pages_handler(works("W1", "W2"), works("W2", "W3"), count=3)
    ids = [i for i, _ in OpenAlexConnector(CONFIG, client=make_client(handler)).fetch_records()]
    assert ids == ["W1", "W2", "W2", "W3"]  # raw keeps what was delivered; staging de-duplicates


def test_a_truncated_fetch_is_an_error() -> None:
    handler = pages_handler(works("W1", "W2"), count=100)
    connector = OpenAlexConnector(CONFIG, client=make_client(handler))
    with pytest.raises(OpenAlexIncompleteError, match="100 matching works but only 2"):
        list(connector.fetch_records())


def test_repeated_works_do_not_hide_a_shortfall() -> None:
    handler = pages_handler(works("W1", "W2"), works("W1", "W2"), count=4)
    connector = OpenAlexConnector(CONFIG, client=make_client(handler))
    with pytest.raises(OpenAlexIncompleteError):
        list(connector.fetch_records())


def test_a_small_drift_in_the_count_is_tolerated() -> None:
    ids = [f"W{n}" for n in range(996)]
    handler = pages_handler(works(*ids), count=1000)  # 0.4% short: works added while pulling
    assert len(list(OpenAlexConnector(CONFIG, client=make_client(handler)).fetch_records())) == 996


def test_a_larger_shortfall_than_the_default_tolerance_is_an_error() -> None:
    ids = [f"W{n}" for n in range(990)]
    handler = pages_handler(works(*ids), count=1000)  # 1% short
    with pytest.raises(OpenAlexIncompleteError):
        list(OpenAlexConnector(CONFIG, client=make_client(handler)).fetch_records())


def test_the_tolerance_is_configurable() -> None:
    handler = pages_handler(works("W1", "W2"), count=3)
    strict = {**CONFIG, "max_shortfall": 0}
    with pytest.raises(OpenAlexIncompleteError):
        list(OpenAlexConnector(strict, client=make_client(handler)).fetch_records())


def test_a_response_without_a_count_is_not_checked() -> None:
    handler = pages_handler(works("W1"), count=None)
    assert len(list(OpenAlexConnector(CONFIG, client=make_client(handler)).fetch_records())) == 1


def test_the_api_key_never_reaches_the_log(
    monkeypatch: pytest.MonkeyPatch, caplog: pytest.LogCaptureFixture
) -> None:
    monkeypatch.setenv("OPENALEX_API_KEY", "secret-test-key")
    configure_logging()
    caplog.set_level("INFO")
    handler = pages_handler(works("W1"), count=1)
    list(OpenAlexConnector(CONFIG, client=make_client(handler)).fetch_records())
    assert "secret-test-key" not in caplog.text
    assert "1 distinct works" in caplog.text  # the totals are still logged


def test_shipped_configuration_pulls_every_work_not_just_recent_ones() -> None:
    """The real config/sources.yml must not cut off old works or hide OpenAlex's xpac works."""
    config = load_source_config(Path(__file__).parent.parent / "config" / "sources.yml")["openalex"]
    assert config.get("year_from") is None
    assert config.get("include_xpac") is True
    assert OpenAlexConnector(config)._works_filter() == (
        f"authorships.institutions.id:{config['institution_id']}"
    )


def test_an_incomplete_fetch_leaves_the_previous_raw_load_in_place(tmp_path: Path) -> None:
    """Loading through write_raw: the guard fires mid-load and the old table survives."""
    db = tmp_path / "raw.duckdb"
    good = OpenAlexConnector(CONFIG, client=make_client(pages_handler(works("W1", "W2"), count=2)))
    assert write_raw(db, "raw_openalex", good.fetch()) == 2

    truncated = OpenAlexConnector(CONFIG, client=make_client(pages_handler(works("W1"), count=100)))
    with pytest.raises(OpenAlexIncompleteError):
        write_raw(db, "raw_openalex", truncated.fetch())

    with duckdb.connect(str(db)) as con:
        ids = con.execute("SELECT record_id FROM raw_openalex.records ORDER BY 1").fetchall()
    assert ids == [("W1",), ("W2",)]
