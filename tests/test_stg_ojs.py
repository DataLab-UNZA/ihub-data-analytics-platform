"""Tests for the OJS staging models, built from the recorded OAI-PMH replies and the
hand-made REST API replies. Never calls the live journals site."""

import copy
from pathlib import Path
from typing import Any

import pytest
import responses

from ihub.connectors.ojs import OjsConnector
from tests.dbt_helpers import load_raw, query, run_dbt
from tests.test_ojs_connector import CONFIG, RestRecorder, register_oai_journals, rest_api

SELECT = "path:models/staging/ojs"


def recorded_records() -> list[tuple[str, dict[str, Any]]]:
    """Every article the connector yields: JABS and zjh over OAI-PMH, one journal by REST."""
    with responses.RequestsMock() as rsps:
        register_oai_journals(rsps)
        return list(OjsConnector(CONFIG, rest_api=rest_api(RestRecorder())).fetch_records())


#: Journal names as the live journals give them in dc:source (November 11, 2026), and
#: the venue name each should become.
VENUE_NAMES = {
    "Zambia Law Journal (ZLJ) ISSN Print: 1027-7862": "Zambia Law Journal",
    "Zambia Interdisciplinary Journal of Education ( ZIJE) Online-ISSN 2710-0715": (
        "Zambia Interdisciplinary Journal of Education"
    ),
    "Journal of Adult Education (online ISSN 2664-5688)": "Journal of Adult Education",
    "ZANGO: Zambian Journal of Contemporary Issues": (
        "ZANGO: Zambian Journal of Contemporary Issues"
    ),
}


def articles_with_venues(template: dict[str, Any]) -> list[tuple[str, dict[str, Any]]]:
    """Copies of an OAI-PMH article, one for each journal name in VENUE_NAMES."""
    copies = []
    for number, raw_name in enumerate(VENUE_NAMES, start=9001):
        payload = copy.deepcopy(template)
        payload["identifier"] = f"oai:ojs2.journals.unza.zm:article/{number}"
        payload["metadata"]["source"] = [f"{raw_name}; Vol 1 No 2 (2020); 3-9"]
        copies.append((payload["identifier"], payload))
    return copies


@pytest.fixture(scope="module")
def db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    records = recorded_records()
    path = tmp_path_factory.mktemp("ojs") / "test.duckdb"
    extra = [records[0], *articles_with_venues(records[0][1])]  # records[0] delivered twice
    load_raw(path, "ojs", records + extra)
    run_dbt(path, "build", SELECT)
    return path


def test_journal_names_lose_their_issns_and_acronyms(db: Path) -> None:
    rows = query(
        db,
        "select article_number, venue_name from staging.stg_ojs__articles "
        "where article_number >= 9001 order by article_number",
    )
    assert [r["venue_name"] for r in rows] == list(VENUE_NAMES.values())


def article(db: Path, article_id: str) -> dict[str, Any]:
    rows = query(
        db, f"select * from staging.stg_ojs__articles where ojs_article_id = '{article_id}'"
    )
    assert len(rows) == 1
    return rows[0]


def test_one_row_per_article_from_both_harvest_methods(db: Path) -> None:
    rows = query(
        db,
        "select harvest_method, count(*) as n from staging.stg_ojs__articles group by 1 order by 1",
    )
    assert rows == [{"harvest_method": "oai_pmh", "n": 11}, {"harvest_method": "rest_api", "n": 2}]


def test_an_oai_pmh_article_is_read_from_its_dublin_core(db: Path) -> None:
    row = article(db, "oai:ojs2.journals.unza.zm:article/321")
    assert row["journal_path"] == "JABS"
    assert row["article_number"] == 321
    assert row["title"] == "Publish or Perish: Ushering in UNZA-JABS"
    assert str(row["published_date"]) == "2012-03-31"
    assert row["year"] == 2012
    assert (row["type"], row["source_type"]) == ("article", "info:eu-repo/semantics/article")
    # the article's DOI, not the galley DOI (dc:relation) or the issue DOI (dc:source)
    assert row["doi"] == "10.53974/unza.jabs.1.1.321"
    assert row["article_url"] == "https://journals.unza.zm/index.php/JABS/article/view/321"
    assert row["venue_name"] == "Journal of Agricultural and Biomedical Sciences"
    assert row["issns"] == ["2710-138X", "2226-6410"]
    assert (row["volume"], row["issue"], row["pages"]) == ("1", "1", "1-4")
    assert row["author_names"] == ["Chipeta, J", "Nyambe, I"]
    assert row["first_author_family_name"] == "Chipeta"
    assert row["is_deleted"] is False


def test_a_citation_without_pages_leaves_pages_empty(db: Path) -> None:
    row = article(db, "oai:ojs2.journals.unza.zm:article/1279")
    assert (row["volume"], row["issue"], row["pages"]) == ("8", "1", None)
    assert row["n_authors"] == 12


def test_a_rest_api_article_has_the_same_shape(db: Path) -> None:
    row = article(db, "ojs:example:article/702")
    assert row["harvest_method"] == "rest_api"
    assert row["title"] == "Records management practices in Zambian public universities"
    assert row["doi"] == "10.99999/example.702"
    assert row["year"] == 2024
    assert str(row["published_date"]) == "2024-11-30"
    assert (row["volume"], row["issue"], row["pages"]) == ("3", "2", "1-18")
    assert row["author_names"] == ["Banda, Chipo", "Mwila, Ireen"]
    assert row["type"] == "article"
    assert article(db, "ojs:example:article/703")["doi"] is None


def test_authors_keep_their_order(db: Path) -> None:
    rows = query(
        db,
        "select author_position, family_name, given_names from staging.stg_ojs__article_authors "
        "where ojs_article_id = 'oai:ojs2.journals.unza.zm:article/1067' order by 1",
    )
    assert rows == [
        {"author_position": 1, "family_name": "Chama", "given_names": "Meldad L."},
        {"author_position": 2, "family_name": "Kanyembo", "given_names": "Terry"},
    ]
