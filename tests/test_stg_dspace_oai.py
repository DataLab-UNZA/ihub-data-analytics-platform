"""Tests for the IRIMS (DSpace) staging models, built from the recorded OAI-PMH replies.

The recorded replies go through the real connector into raw_dspace_oai, so the models are
tested on payloads exactly as the connector writes them. Never calls the live repository.
"""

from pathlib import Path
from typing import Any

import pytest
import responses

from ihub.connectors.dspace_oai import DSpaceOaiConnector
from tests.dbt_helpers import load_raw, query, run_dbt
from tests.oai_helpers import oai_replies, read_fixture

ENDPOINT = "https://rims.unza.ac.zm/server/oai/request"
SELECT = "path:models/staging/dspace_oai"


def recorded_records() -> list[tuple[str, dict[str, Any]]]:
    """Every record the connector yields for the recorded replies (3 sets, 5 items)."""
    with responses.RequestsMock() as rsps:
        oai_replies(
            rsps,
            ENDPOINT,
            {
                ("ListSets", ""): read_fixture("dspace_oai", "list_sets.xml"),
                ("ListRecords", ""): read_fixture("dspace_oai", "list_records_page1.xml"),
                ("ListRecords", "oai_dc////100"): read_fixture(
                    "dspace_oai", "list_records_page2.xml"
                ),
            },
        )
        config = {"oai_endpoint": ENDPOINT, "retry_wait": 0}
        return list(DSpaceOaiConnector(config).fetch_records())


def synthetic_item(oai_id: str, **metadata: list[str]) -> tuple[str, dict[str, Any]]:
    """An item record in the connector's shape, with the given Dublin Core elements."""
    return oai_id, {
        "record_type": "item",
        "metadata_prefix": "oai_dc",
        "identifier": oai_id,
        "datestamp": "2024-01-02T03:04:05Z",
        "set_specs": ["com_1_1"],
        "deleted": False,
        "metadata": metadata,
    }


@pytest.fixture(scope="module")
def db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    records = recorded_records()
    first_item = next(r for r in records if r[1]["record_type"] == "item")
    edge_cases = [
        # the same item delivered again (it sits in a second harvested set)
        first_item,
        synthetic_item(
            "oai:test:1/1",
            title=["  A   study\nof soils "],
            creator=["Jane Banda", "Mwila, Chipo K."],
            identifier=["https://hdl.example/1/1", "doi:10.1234/ABC.5."],
            date=["2020-05-06T07:08:09Z", "2019"],
            type=["Article"],
        ),
    ]
    path = tmp_path_factory.mktemp("dspace") / "test.duckdb"
    load_raw(path, "dspace_oai", records + edge_cases)
    run_dbt(path, "build", SELECT)  # also runs every not-null, unique and relationship test
    return path


def item(db: Path, item_id: str) -> dict[str, Any]:
    rows = query(
        db, f"select * from staging.stg_dspace_oai__items where dspace_item_id = '{item_id}'"
    )
    assert len(rows) == 1
    return rows[0]


def test_one_row_per_item_even_when_delivered_twice(db: Path) -> None:
    rows = query(db, "select count(*) as n from staging.stg_dspace_oai__items")
    assert rows == [{"n": 6}]  # 5 recorded items + 1 synthetic


def test_a_recorded_item_is_renamed_and_typed(db: Path) -> None:
    row = item(db, "oai:rims.unza.ac.zm:123456789/4153")
    assert row["handle"] == "123456789/4153"
    assert row["item_url"] == "http://dspace.unza.zm/handle/123456789/4153"
    assert row["title"].startswith("Morphological characterisation of low and high oil")
    assert row["year"] == 2015
    assert (row["type"], row["source_type"]) == ("other", "Other")
    assert row["author_names"] == ["Chinyundo, Anthony"]
    assert row["first_author_family_name"] == "Chinyundo"
    assert row["set_specs"] == ["com_123456789_289", "col_123456789_290"]
    assert row["is_deleted"] is False


def test_the_issue_date_wins_over_accession_timestamps(db: Path) -> None:
    # dc:date is 2022-06-01T10:39:14Z (accessioned, twice) and 2021 (issued)
    assert item(db, "oai:rims.unza.ac.zm:123456789/7371")["year"] == 2021


def test_theses_are_dissertations(db: Path) -> None:
    assert item(db, "oai:rims.unza.ac.zm:123456789/3777")["type"] == "dissertation"


def test_deleted_items_are_kept_and_flagged(db: Path) -> None:
    row = item(db, "oai:rims.unza.ac.zm:123456789/106")
    assert row["is_deleted"] is True
    assert row["title"] is None and row["n_authors"] == 0


def test_dois_names_titles_and_years_are_standardised(db: Path) -> None:
    row = item(db, "oai:test:1/1")
    assert row["title"] == "A study of soils"
    assert row["doi"] == "10.1234/abc.5"  # prefix removed, lower case, trailing dot dropped
    assert row["year"] == 2019
    assert row["type"] == "article"
    assert row["first_author_family_name"] == "Banda"  # "Given Family" order


def test_authors_are_split_into_family_and_given_names(db: Path) -> None:
    rows = query(
        db,
        "select author_position, family_name, given_names, family_name_normalised "
        "from staging.stg_dspace_oai__item_authors where dspace_item_id = 'oai:test:1/1' "
        "order by author_position",
    )
    assert rows == [
        {
            "author_position": 1,
            "family_name": "Banda",
            "given_names": "Jane",
            "family_name_normalised": "banda",
        },
        {
            "author_position": 2,
            "family_name": "Mwila",
            "given_names": "Chipo K.",
            "family_name_normalised": "mwila",
        },
    ]


def test_sets_are_communities_or_collections_with_names(db: Path) -> None:
    rows = query(db, "select set_spec, set_kind, set_name_key from staging.stg_dspace_oai__sets")
    assert {r["set_spec"]: (r["set_kind"], r["set_name_key"]) for r in rows} == {
        "com_123456789_5087": (
            "community",
            "african digital health library adhl zambia",
        ),
        "com_123456789_7": ("community", "agricultural sciences"),
        "com_123456789_7940": ("community", "agriculture science"),
    }


def test_every_item_is_linked_to_each_of_its_sets(db: Path) -> None:
    rows = query(
        db,
        "select set_spec, set_kind from staging.stg_dspace_oai__item_sets "
        "where dspace_item_id = 'oai:rims.unza.ac.zm:123456789/4153' order by set_spec",
    )
    assert rows == [
        {"set_spec": "col_123456789_290", "set_kind": "collection"},
        {"set_spec": "com_123456789_289", "set_kind": "community"},
    ]
