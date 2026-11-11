"""Tests for the DSpace (IRIMS) connector, replaying recorded replies (never the live endpoint)."""

from pathlib import Path

import duckdb
import pytest
import responses

from ihub.connectors.dspace_oai import DSpaceOaiConnector
from ihub.ingest.raw import write_raw
from tests.oai_helpers import oai_replies, read_fixture

ENDPOINT = "https://rims.unza.ac.zm/server/oai/request"
CONFIG = {"oai_endpoint": ENDPOINT, "metadata_prefix": "oai_dc", "retry_wait": 0}
ITEM_IDS = [
    "oai:rims.unza.ac.zm:123456789/4153",
    "oai:rims.unza.ac.zm:123456789/3777",
    "oai:rims.unza.ac.zm:123456789/7371",
    "oai:rims.unza.ac.zm:123456789/8935",
    "oai:rims.unza.ac.zm:123456789/106",
]
SET_IDS = ["set:com_123456789_5087", "set:com_123456789_7", "set:com_123456789_7940"]
REPLIES = {
    ("ListSets", ""): read_fixture("dspace_oai", "list_sets.xml"),
    ("ListRecords", ""): read_fixture("dspace_oai", "list_records_page1.xml"),
    ("ListRecords", "oai_dc////100"): read_fixture("dspace_oai", "list_records_page2.xml"),
}


@responses.activate
def test_sets_come_first_then_every_item_keyed_by_oai_identifier() -> None:
    oai_replies(responses.mock, ENDPOINT, REPLIES)
    records = list(DSpaceOaiConnector(CONFIG).fetch_records())

    assert [record_id for record_id, _ in records] == SET_IDS + ITEM_IDS
    assert [payload["record_type"] for _, payload in records] == ["set"] * 3 + ["item"] * 5


@responses.activate
def test_items_keep_their_metadata_prefix_and_metadata_unchanged() -> None:
    oai_replies(responses.mock, ENDPOINT, REPLIES)
    records = dict(DSpaceOaiConnector(CONFIG).fetch_records())

    item = records["oai:rims.unza.ac.zm:123456789/4153"]
    assert item["metadata_prefix"] == "oai_dc"
    assert item["metadata"]["creator"] == ["Chinyundo, Anthony"]
    assert item["set_specs"] == ["com_123456789_289", "col_123456789_290"]
    assert records["oai:rims.unza.ac.zm:123456789/106"]["deleted"] is True
    assert records["set:com_123456789_7"]["set_name"] == "Agricultural Sciences"


@responses.activate
def test_sets_can_be_left_out() -> None:
    oai_replies(responses.mock, ENDPOINT, REPLIES)
    records = list(DSpaceOaiConnector({**CONFIG, "harvest_sets": False}).fetch_records())
    assert [record_id for record_id, _ in records] == ITEM_IDS
    assert not any("ListSets" in call.request.url for call in responses.calls)


@responses.activate
def test_fetch_adds_source_and_fetch_time() -> None:
    oai_replies(responses.mock, ENDPOINT, REPLIES)
    records = list(DSpaceOaiConnector(CONFIG).fetch())
    assert len(records) == 8
    assert all(record.source == "dspace_oai" for record in records)
    assert all(record.fetched_at is not None for record in records)


@responses.activate
def test_each_configured_set_is_harvested() -> None:
    oai_replies(
        responses.mock,
        ENDPOINT,
        {
            ("ListRecords", "col_123456789_290"): read_fixture(
                "dspace_oai", "list_records_page1.xml"
            ),
            ("ListRecords", "oai_dc////100"): read_fixture("dspace_oai", "list_records_page2.xml"),
            ("ListRecords", "col_123456789_999"): read_fixture(
                "dspace_oai", "no_records_match.xml"
            ),
        },
    )
    config = {**CONFIG, "harvest_sets": False, "sets": ["col_123456789_290", "col_123456789_999"]}
    assert len(list(DSpaceOaiConnector(config).fetch_records())) == 5


@responses.activate
def test_records_reach_the_raw_schema_unchanged(tmp_path: Path) -> None:
    oai_replies(responses.mock, ENDPOINT, REPLIES)
    db = tmp_path / "ihub.duckdb"
    assert write_raw(db, "raw_dspace_oai", DSpaceOaiConnector(CONFIG).fetch()) == 8
    with duckdb.connect(str(db)) as con:
        rows = con.execute(
            "SELECT payload->>'$.record_type' AS kind, count(*), "
            "count(*) FILTER (WHERE payload->>'$.deleted' = 'true') "
            "FROM raw_dspace_oai.records WHERE source = 'dspace_oai' GROUP BY kind ORDER BY kind"
        ).fetchall()
    assert rows == [("item", 5, 1), ("set", 3, 0)]


def test_a_missing_endpoint_fails_before_any_request() -> None:
    with pytest.raises(ValueError, match="oai_endpoint is not set"):
        list(DSpaceOaiConnector({"oai_endpoint": None}).fetch_records())
