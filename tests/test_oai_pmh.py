"""Tests for the shared OAI-PMH harvester, replaying recorded replies (never the live endpoint)."""

import pytest
import requests
import responses

from ihub.connectors.oai_pmh import (
    OaiPmhError,
    OaiPmhHarvester,
    OaiPmhIncompleteError,
    OaiPmhUnavailableError,
)
from tests.oai_helpers import oai_replies, read_fixture

ENDPOINT = "https://rims.unza.ac.zm/server/oai/request"
PAGE1 = read_fixture("dspace_oai", "list_records_page1.xml")
PAGE2 = read_fixture("dspace_oai", "list_records_page2.xml")
TOKEN = "oai_dc////100"


def harvester(**kwargs) -> OaiPmhHarvester:
    return OaiPmhHarvester(ENDPOINT, retry_wait=0, **kwargs)


@responses.activate
def test_follows_the_resumption_token_and_keeps_every_record() -> None:
    oai_replies(
        responses.mock, ENDPOINT, {("ListRecords", ""): PAGE1, ("ListRecords", TOKEN): PAGE2}
    )
    records = list(harvester().list_records("oai_dc"))

    assert [r["identifier"] for r in records] == [
        "oai:rims.unza.ac.zm:123456789/4153",
        "oai:rims.unza.ac.zm:123456789/3777",
        "oai:rims.unza.ac.zm:123456789/7371",
        "oai:rims.unza.ac.zm:123456789/8935",
        "oai:rims.unza.ac.zm:123456789/106",
    ]
    assert len(responses.calls) == 2
    assert "resumptionToken=" in responses.calls[1].request.url
    assert "metadataPrefix" not in responses.calls[1].request.url


@responses.activate
def test_records_keep_header_metadata_and_xml_unchanged() -> None:
    oai_replies(
        responses.mock, ENDPOINT, {("ListRecords", ""): PAGE1, ("ListRecords", TOKEN): PAGE2}
    )
    first, *_, deleted = harvester().list_records("oai_dc")

    assert first["datestamp"] == "2019-08-19T12:30:47Z"
    assert first["set_specs"] == ["com_123456789_289", "col_123456789_290"]
    assert first["deleted"] is False
    assert first["metadata"]["creator"] == ["Chinyundo, Anthony"]
    assert first["metadata"]["identifier"] == ["http://dspace.unza.zm/handle/123456789/4153"]
    assert "<dc:title>Morphological characterisation" in first["xml"]

    assert deleted["deleted"] is True
    assert deleted["metadata"] == {}


@responses.activate
def test_sends_the_set_when_one_is_given() -> None:
    oai_replies(
        responses.mock,
        ENDPOINT,
        {("ListRecords", "col_123456789_999"): read_fixture("dspace_oai", "no_records_match.xml")},
    )
    assert list(harvester().list_records("oai_dc", set_spec="col_123456789_999")) == []
    assert "set=col_123456789_999" in responses.calls[0].request.url


@responses.activate
def test_too_few_records_raise_instead_of_replacing_a_good_load() -> None:
    short_page2 = PAGE2.replace('completeListSize="5"', 'completeListSize="50"')
    oai_replies(
        responses.mock, ENDPOINT, {("ListRecords", ""): PAGE1, ("ListRecords", TOKEN): short_page2}
    )
    with pytest.raises(OaiPmhIncompleteError, match="50 items but only 5"):
        list(harvester().list_records("oai_dc"))


@responses.activate
def test_a_small_shortfall_is_accepted() -> None:
    oai_replies(
        responses.mock, ENDPOINT, {("ListRecords", ""): PAGE1, ("ListRecords", TOKEN): PAGE2}
    )
    long_page2 = PAGE2.replace('completeListSize="5"', 'completeListSize="6"')
    oai_replies(
        responses.mock, ENDPOINT, {("ListRecords", ""): PAGE1, ("ListRecords", TOKEN): long_page2}
    )
    assert len(list(harvester(max_shortfall=0.5).list_records("oai_dc"))) == 5


@responses.activate
def test_an_oai_protocol_error_is_reported() -> None:
    oai_replies(
        responses.mock,
        ENDPOINT,
        {("ListRecords", ""): read_fixture("dspace_oai", "cannot_disseminate_format.xml")},
    )
    with pytest.raises(OaiPmhError, match="CannotDisseminateFormat"):
        list(harvester().list_records("mods"))


@responses.activate
def test_a_server_error_part_way_through_is_reported() -> None:
    oai_replies(responses.mock, ENDPOINT, {("ListRecords", ""): PAGE1, ("ListRecords", TOKEN): 500})
    with pytest.raises(OaiPmhError, match="HTTP 500"):
        list(harvester(attempts=2).list_records("oai_dc"))
    # one first page, then the second page tried twice
    assert len(responses.calls) == 3


@responses.activate
def test_network_errors_are_retried() -> None:
    responses.add(responses.GET, ENDPOINT, body=requests.ConnectionError("down"))
    responses.add(responses.GET, ENDPOINT, body=read_fixture("dspace_oai", "identify.xml"))
    identify = harvester(attempts=3).identify()
    assert identify["repositoryName"] == [
        "(IRIMS) Integrated Research Information Management System"
    ]
    assert len(responses.calls) == 2


@responses.activate
def test_identify_404_means_the_endpoint_is_unavailable() -> None:
    oai_replies(responses.mock, ENDPOINT, {("Identify", ""): 404})
    with pytest.raises(OaiPmhUnavailableError, match="HTTP 404"):
        harvester().identify()


@responses.activate
def test_identify_answered_with_html_means_the_endpoint_is_unavailable() -> None:
    oai_replies(responses.mock, ENDPOINT, {("Identify", ""): "<html><body>Not OAI</body></html"})
    with pytest.raises(OaiPmhUnavailableError, match="not answer Identify with OAI-PMH"):
        harvester().identify()


def test_an_endpoint_is_required() -> None:
    with pytest.raises(ValueError, match="endpoint"):
        OaiPmhHarvester("")


def test_from_config_reads_the_harvest_settings() -> None:
    built = OaiPmhHarvester.from_config(ENDPOINT, {"max_shortfall": 0.1, "retry_wait": 0})
    assert built.endpoint == ENDPOINT
    assert built.max_shortfall == 0.1


@responses.activate
def test_an_html_page_part_way_through_is_an_error_not_the_end_of_the_list() -> None:
    oai_replies(
        responses.mock,
        ENDPOINT,
        {
            ("ListRecords", ""): PAGE1,
            ("ListRecords", TOKEN): "<html><body>Maintenance</body></html>",
        },
    )
    with pytest.raises(OaiPmhError, match="not OAI-PMH"):
        list(harvester().list_records("oai_dc"))


@responses.activate
def test_sets_are_listed_with_their_names() -> None:
    oai_replies(
        responses.mock, ENDPOINT, {("ListSets", ""): read_fixture("dspace_oai", "list_sets.xml")}
    )
    sets = list(harvester().list_sets())
    assert [(s["set_spec"], s["set_name"]) for s in sets] == [
        ("com_123456789_5087", "African Digital Health Library (ADHL) - Zambia"),
        ("com_123456789_7", "Agricultural Sciences"),
        ("com_123456789_7940", "Agriculture Science"),
    ]


@responses.activate
def test_a_repository_without_sets_lists_none() -> None:
    no_sets = read_fixture("dspace_oai", "no_records_match.xml").replace(
        'code="noRecordsMatch"', 'code="noSetHierarchy"'
    )
    oai_replies(responses.mock, ENDPOINT, {("ListSets", ""): no_sets})
    assert list(harvester().list_sets()) == []
