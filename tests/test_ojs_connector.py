"""Tests for the OJS connector, replaying recorded replies (never the live site)."""

import json
from pathlib import Path

import duckdb
import httpx
import pytest
import responses

from ihub.connectors.ojs import OjsConnector, OjsError, OjsRestApi
from ihub.ingest.raw import write_raw
from tests.oai_helpers import FIXTURES, oai_replies, read_fixture

BASE_URL = "https://journals.unza.zm"
TOKEN = "secret-test-token"
# JABS (two pages) and zjh are recorded replies; "example" stands for a journal without
# OAI-PMH, served by hand-made REST API replies.
CONFIG = {"base_url": BASE_URL, "journals": ["JABS", "zjh", "example"], "retry_wait": 0}
ISSUES = json.loads((FIXTURES / "ojs" / "rest_issues.json").read_text(encoding="utf-8"))
ISSUE_41 = json.loads((FIXTURES / "ojs" / "rest_issue_41.json").read_text(encoding="utf-8"))


def oai(journal: str) -> str:
    return f"{BASE_URL}/index.php/{journal}/oai"


def register_oai_journals(rsps: responses.RequestsMock) -> None:
    """JABS (two pages) and zjh answer OAI-PMH; the example journal's endpoint answers 404."""
    oai_replies(
        rsps,
        oai("JABS"),
        {
            ("Identify", ""): read_fixture("ojs", "JABS_identify.xml"),
            ("ListRecords", ""): read_fixture("ojs", "JABS_list_records_page1.xml"),
            ("ListRecords", "5b308a1597eb45199c804a8333065bcd"): read_fixture(
                "ojs", "JABS_list_records_page2.xml"
            ),
        },
    )
    oai_replies(
        rsps,
        oai("zjh"),
        {
            ("Identify", ""): read_fixture("ojs", "zjh_identify.xml"),
            ("ListRecords", ""): read_fixture("ojs", "zjh_list_records.xml"),
        },
    )
    oai_replies(rsps, oai("example"), {("Identify", ""): 404})


class RestRecorder:
    """An httpx handler serving the example journal's REST replies and keeping every request."""

    def __init__(self, issues: dict | None = None, status: int = 200) -> None:
        self.issues = issues or ISSUES
        self.status = status
        self.requests: list[httpx.Request] = []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if self.status != 200:
            return httpx.Response(self.status, json={"error": "api.403.unauthorized"})
        path = request.url.path
        if path == "/index.php/example/api/v1/issues":
            return httpx.Response(200, json=self.issues)
        if path == "/index.php/example/api/v1/issues/41":
            return httpx.Response(200, json=ISSUE_41)
        return httpx.Response(404, json={"error": "api.404.resourceNotFound"})


def rest_api(recorder: RestRecorder, page_size: int = 100) -> OjsRestApi:
    client = httpx.Client(transport=httpx.MockTransport(recorder))
    return OjsRestApi(BASE_URL, TOKEN, client, page_size=page_size)


@responses.activate
def test_every_journal_is_harvested_and_keeps_its_journal_path() -> None:
    register_oai_journals(responses.mock)
    records = list(OjsConnector(CONFIG, rest_api=rest_api(RestRecorder())).fetch_records())

    assert [(payload["journal"], record_id) for record_id, payload in records] == [
        ("JABS", "oai:ojs2.journals.unza.zm:article/321"),
        ("JABS", "oai:ojs2.journals.unza.zm:article/324"),
        ("JABS", "oai:ojs2.journals.unza.zm:article/329"),
        ("JABS", "oai:ojs2.journals.unza.zm:article/1279"),
        ("JABS", "oai:ojs2.journals.unza.zm:article/1289"),
        ("zjh", "oai:ojs2.journals.unza.zm:article/1067"),
        ("zjh", "oai:ojs2.journals.unza.zm:article/1069"),
        ("example", "ojs:example:article/702"),
        ("example", "ojs:example:article/703"),
    ]


@responses.activate
def test_oai_pmh_records_are_unchanged_and_say_how_they_were_harvested() -> None:
    register_oai_journals(responses.mock)
    records = dict(OjsConnector(CONFIG, rest_api=rest_api(RestRecorder())).fetch_records())
    article = records["oai:ojs2.journals.unza.zm:article/1067"]

    assert article["harvest_method"] == "oai_pmh"
    assert article["metadata_prefix"] == "oai_dc"
    assert article["set_specs"] == ["zjh:ART"]
    assert article["metadata"]["creator"] == ["Chama, Meldad L.", "Kanyembo, Terry"]
    assert article["metadata"]["source"][0].startswith("Zambia Journal of History; Vol 10 No 1")
    assert "<dc:title" in article["xml"]


@responses.activate
def test_the_rest_api_is_used_only_where_oai_pmh_is_unavailable() -> None:
    register_oai_journals(responses.mock)
    recorder = RestRecorder()
    records = dict(OjsConnector(CONFIG, rest_api=rest_api(recorder)).fetch_records())

    assert {request.url.path.split("/")[2] for request in recorder.requests} == {"example"}
    assert not any(
        "example" in call.request.url and "ListRecords" in call.request.url
        for call in responses.calls
    )
    article = records["ojs:example:article/702"]
    assert article["harvest_method"] == "rest_api"
    assert article["article"] == ISSUE_41["articles"][0]
    assert article["issue"]["identification"] == "Vol. 3 No. 2 (2024)"
    assert "articles" not in article["issue"]


@responses.activate
def test_the_api_token_is_sent_as_a_header_and_never_in_the_url() -> None:
    register_oai_journals(responses.mock)
    recorder = RestRecorder()
    list(OjsConnector(CONFIG, rest_api=rest_api(recorder)).fetch_records())

    assert recorder.requests
    for request in recorder.requests:
        assert request.headers["Authorization"] == f"Bearer {TOKEN}"
        assert TOKEN not in str(request.url)
    assert recorder.requests[0].url.params["isPublished"] == "true"


def test_rest_issues_are_paged_until_items_max() -> None:
    two_issues = {"itemsMax": 2, "items": [ISSUES["items"][0]]}
    recorder = RestRecorder(issues=two_issues)
    issues = list(rest_api(recorder, page_size=1).published_issues("example"))

    assert len(issues) == 2
    assert [request.url.params["offset"] for request in recorder.requests] == ["0", "1"]
    assert recorder.requests[0].url.params["count"] == "1"


def test_fewer_rest_issues_than_listed_raise() -> None:
    recorder = RestRecorder(issues={"itemsMax": 5, "items": []})
    with pytest.raises(OjsError, match="listed 5 issues for example but returned 0"):
        list(rest_api(recorder).published_issues("example"))


def test_a_refused_token_is_reported_without_revealing_it() -> None:
    with pytest.raises(OjsError, match="HTTP 403") as error:
        list(rest_api(RestRecorder(status=403)).published_articles("example"))
    assert TOKEN not in str(error.value)


@responses.activate
def test_a_journal_without_oai_pmh_needs_a_token(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OJS_API_TOKEN", "")
    oai_replies(responses.mock, oai("example"), {("Identify", ""): 404})
    connector = OjsConnector({**CONFIG, "journals": ["example"]})
    with pytest.raises(OjsError, match="OJS_API_TOKEN is not set"):
        list(connector.fetch_records())


@responses.activate
def test_records_reach_the_raw_schema_with_their_journal(tmp_path: Path) -> None:
    register_oai_journals(responses.mock)
    db = tmp_path / "ihub.duckdb"
    records = OjsConnector(CONFIG, rest_api=rest_api(RestRecorder())).fetch()
    assert write_raw(db, "raw_ojs", records) == 9
    with duckdb.connect(str(db)) as con:
        rows = con.execute(
            "SELECT payload->>'$.journal' AS journal, count(*) FROM raw_ojs.records "
            "WHERE source = 'ojs' GROUP BY journal ORDER BY journal"
        ).fetchall()
    assert rows == [("JABS", 5), ("example", 2), ("zjh", 2)]


def test_the_oai_endpoint_is_built_from_the_base_url_and_journal_path() -> None:
    connector = OjsConnector({**CONFIG, "base_url": f"{BASE_URL}/"})
    assert connector.oai_endpoint("zjh") == "https://journals.unza.zm/index.php/zjh/oai"


@pytest.mark.parametrize(
    ("config", "message"),
    [
        ({"base_url": None, "journals": ["ZJH"]}, "base_url is not set"),
        ({"base_url": BASE_URL, "journals": []}, "must list the journal paths"),
        ({"base_url": BASE_URL, "journals": ["ZJH", "zjh"]}, "lists a journal twice"),
    ],
)
def test_bad_settings_fail_before_any_request(config: dict, message: str) -> None:
    with pytest.raises(ValueError, match=message):
        list(OjsConnector(config).fetch_records())
