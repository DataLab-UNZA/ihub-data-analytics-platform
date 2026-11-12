"""Cross-source matching tests: publications and authors from all four sources."""

from pathlib import Path
from typing import Any

import pytest

from tests.dbt_helpers import build_warehouse, make_work, query, run_dbt

MARY = "0000-0001-0000-0001"
PETER = "0000-0002-0000-0002"

OPENALEX = [
    # Shares a DOI with a repository item and an ORCID work.
    make_work(
        "W101",
        doi="10.5555/x1",
        title="Cholera in Lusaka",
        year=2020,
        authors=[("A1", "Mary Phiri", MARY)],
    ),
    # No DOI: matches a repository item on title + year + first-author surname.
    make_work(
        "W102",
        title="Cholera trends in Zambia",
        year=2021,
        authors=[("A2", "Joseph Banda", None)],
    ),
    # Shares a DOI with a journal article. Peter Mwila has an ORCID iD here, not on W104.
    make_work(
        "W103",
        doi="10.5555/x3",
        title="Soil study",
        year=2018,
        authors=[("A3", "Peter Mwila", PETER)],
    ),
    make_work(
        "W104",
        doi="10.5555/x6",
        title="Water quality",
        year=2019,
        authors=[("A3", "Peter Mwila", None)],
    ),
]


def dspace_item(
    number: int,
    title: str,
    creators: list[str],
    date: str,
    doi: str | None = None,
    deleted: bool = False,
) -> tuple[str, dict[str, Any]]:
    identifiers = [f"https://rims.unza.ac.zm/handle/123456789/{number}"]
    if doi:
        identifiers.append(f"https://doi.org/{doi}")
    return (
        f"oai:rims.unza.ac.zm:123456789/{number}",
        {
            "record_type": "item",
            "datestamp": "2026-01-01T00:00:00Z",
            "set_specs": [],
            "deleted": deleted,
            "metadata": {
                "title": [title],
                "creator": creators,
                "date": [date],
                "type": ["Article"],
                "identifier": identifiers,
            },
        },
    )


D1 = dspace_item(1, "Cholera in Lusaka.", ["Phiri, Mary"], "2020-05-01", doi="10.5555/X1")
D2 = dspace_item(2, "Cholera trends in Zambia.", ["Banda, Joseph"], "2021")
D3 = dspace_item(3, "Cholera trends in Zambia", ["Tembo, Ruth"], "2021")
D4 = dspace_item(4, "Withdrawn item", ["Zulu, Anna"], "2020", deleted=True)

OJS_7 = (
    "oai:journals.unza.zm:article/7",
    {
        "journal": "mjz",
        "harvest_method": "oai_pmh",
        "datestamp": "2026-01-01T00:00:00Z",
        "deleted": False,
        "metadata": {
            "title": ["Soil study"],
            "creator": ["Mwila, Peter"],
            "date": ["2018-03-01"],
            "type": ["Article"],
            "identifier": [
                "https://doi.org/10.5555/x3",
                "https://journals.unza.zm/index.php/mjz/article/view/7",
            ],
            "source": [],
        },
    },
)

ORCID_MARY = (
    MARY,
    {
        "orcid": MARY,
        "works": {
            "group": [
                {
                    "work-summary": [
                        {
                            "put-code": 1,
                            "display-index": "0",
                            "title": {"title": {"value": "Cholera in Lusaka"}},
                            "publication-date": {"year": {"value": "2020"}},
                            "type": "JOURNAL_ARTICLE",
                        }
                    ],
                    "external-ids": {
                        "external-id": [
                            {
                                "external-id-type": "doi",
                                "external-id-value": "10.5555/x1",
                                "external-id-relationship": "self",
                            }
                        ]
                    },
                }
            ]
        },
        "employments": {"affiliation-group": []},
    },
)

OPENALEX_IDS = ("W101", "W102", "W103", "W104")
DS = "oai:rims.unza.ac.zm:123456789/"
OJS_ID = OJS_7[0]
ORCID_WORK = f"{MARY}:1"


@pytest.fixture(scope="module")
def db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("sources") / "test.duckdb"
    build_warehouse(
        path,
        OPENALEX,
        extra_raw={
            "dspace_oai": [D1, D2, D3, D4],
            "ojs": [OJS_7],
            "orcid": [ORCID_MARY],
        },
    )
    run_dbt(path, "build", "+int_authors__deduplicated")
    return path


def keys_of(db: Path, *record_ids: str) -> set[str]:
    ids = ", ".join(f"'{r}'" for r in record_ids)
    rows = query(
        db,
        "select distinct publication_key from intermediate.int_publications__source_records "
        f"where source_record_id in ({ids})",
    )
    return {r["publication_key"] for r in rows}


def test_same_doi_in_three_sources_is_one_publication(db: Path) -> None:
    assert len(keys_of(db, "W101", f"{DS}1", ORCID_WORK)) == 1


def test_same_doi_in_openalex_and_ojs_is_one_publication(db: Path) -> None:
    assert len(keys_of(db, "W103", OJS_ID)) == 1


def test_no_doi_matches_on_title_year_and_first_author_surname(db: Path) -> None:
    assert len(keys_of(db, "W102", f"{DS}2")) == 1
    rule = query(
        db,
        "select match_rule from intermediate.int_publications__source_records "
        f"where source_record_id = '{DS}2'",
    )
    assert rule == [{"match_rule": "title_year"}]


def test_same_title_and_year_with_another_surname_is_not_a_match(db: Path) -> None:
    assert keys_of(db, f"{DS}3").isdisjoint(keys_of(db, "W102", f"{DS}2"))


def test_deleted_records_are_left_out(db: Path) -> None:
    rows = query(
        db,
        "select count(*) as n from intermediate.int_publications__source_records "
        f"where source_record_id = '{DS}4'",
    )
    assert rows == [{"n": 0}]


def test_bridge_links_every_record_and_duplicates_are_counted(db: Path) -> None:
    rows = query(
        db,
        """
        select
            (select count(*) from marts.bridge_publication_source) as records,
            (select count(*) from marts.fact_publication) as publications
        """,
    )
    # 4 OpenAlex + 3 repository + 1 journal + 1 ORCID = 9 records; 5 publications
    # (x1, Banda, Tembo, x3, x6), so 4 duplicates are removed.
    assert rows == [{"records": 9, "publications": 5}]


def test_author_with_an_orcid_id_is_one_author_across_sources(db: Path) -> None:
    rows = query(
        db,
        "select n_source_records as n from intermediate.int_authors__deduplicated "
        f"where orcid_id = '{MARY}'",
    )
    assert rows == [{"n": 2}]  # the OpenAlex authorship and the ORCID researcher


def test_openalex_id_without_orcid_joins_the_orcid_author(db: Path) -> None:
    rows = query(
        db,
        "select n_source_records as n from intermediate.int_authors__deduplicated "
        f"where orcid_id = '{PETER}'",
    )
    assert rows == [{"n": 2}]  # W103 (with the iD) and W104 (same OpenAlex ID, no iD)


def test_name_only_authors_stay_unmatched(db: Path) -> None:
    rows = query(
        db,
        "select count(*) as n from intermediate.int_authors__source_records "
        "where match_rule = 'single_record'",
    )
    assert rows == [{"n": 4}]  # Phiri, Banda and Tembo in IRIMS, Mwila in OJS
    total = query(db, "select count(*) as n from intermediate.int_authors__deduplicated")
    assert total == [{"n": 7}]
