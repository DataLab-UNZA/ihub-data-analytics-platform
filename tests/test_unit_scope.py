"""Tests for scoping publications to a unit (Organisation screens), with invented names.

One shared filter drives the list, the count, the CSV export and the breakdowns, so a unit's
count on the Organisation screen and the "Explore N publications" figure cannot drift apart.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ihub.api.app import create_app
from ihub.api.units import NOT_CREDITED
from ihub.mart import research
from ihub.mart.research import PublicationFilter

HEADER = "Staff ID,Surname,First Name,Second Name,Title,Occupation,School\n"
MEDICINE = "School of Medicine"
LAW = "School of Law"


@pytest.fixture
def roster(tmp_path: Path) -> Path:
    path = tmp_path / "roster.csv"
    path.write_text(
        HEADER + "1001,MWANSA,ALICE,,Dr,LECTURER,Medicine\n2002,PHIRI,JOHN,,Mr,LECTURER,Law\n",
        encoding="utf-8",
    )
    return path


@pytest.fixture
def with_roster(insights_db: Path, roster: Path) -> TestClient:
    return TestClient(
        create_app(lambda: insights_db, require_sign_in=False, staff_roster_path=lambda: roster)
    )


@pytest.fixture
def without_roster(insights_db: Path, tmp_path: Path) -> TestClient:
    missing = tmp_path / "missing.csv"
    return TestClient(
        create_app(lambda: insights_db, require_sign_in=False, staff_roster_path=lambda: missing)
    )


def keys(client: TestClient, **params: object) -> set[str]:
    body = client.get("/api/publications", params={**params, "page_size": 100}).json()
    return {row["publication_key"] for row in body["rows"]}


# --- the shared filter -------------------------------------------------------------------------


def test_publication_keys_restrict_the_list_the_count_and_the_breakdown(mart_db: Path) -> None:
    only = PublicationFilter(publication_keys={"p1", "p2"})
    assert research.count_publications(mart_db, only) == 2
    assert {r.publication_key for r in research.publications(mart_db, only, limit=None)} == {
        "p1",
        "p2",
    }
    breakdown = research.publication_breakdown(mart_db, only)
    assert dict(breakdown.types) == {"Article": 1, "Review": 1}


def test_an_empty_unit_matches_nothing_but_no_unit_matches_everything(mart_db: Path) -> None:
    assert research.count_publications(mart_db, PublicationFilter(publication_keys=set())) == 0
    assert research.count_publications(mart_db, PublicationFilter(publication_keys=None)) == 5
    empty = research.publication_breakdown(mart_db, PublicationFilter(publication_keys=set()))
    assert empty.types == ()
    assert [n for _, _, n in empty.sources] == [0, 0, 0, 0]  # every source listed, with zero


def test_the_source_breakdown_uses_the_source_dimension(mart_db: Path) -> None:
    result = research.publication_breakdown(mart_db, PublicationFilter())
    assert {code: n for code, _, n in result.sources} == {
        "dspace_oai": 2,
        "openalex": 4,
        "ojs": 1,
        "orcid": 1,
    }


# --- the unit parameter ------------------------------------------------------------------------


def test_unit_filter_matches_the_organisation_count_with_a_roster(with_roster: TestClient) -> None:
    organisation = with_roster.get("/api/organisation").json()
    medicine = next(s for s in organisation["school_credit"]["schools"] if s["school"] == MEDICINE)
    scoped = with_roster.get("/api/publications", params={"unit": MEDICINE}).json()
    assert scoped["total"] == medicine["roster_publications"] == 4
    assert keys(with_roster, unit=MEDICINE) == {"p1", "p2", "p3", "p5"}


def test_unit_filter_respects_the_year(with_roster: TestClient) -> None:
    organisation = with_roster.get("/api/organisation", params={"start": 2020, "end": 2020}).json()
    count = organisation["school_credit"]["schools"][0]["roster_publications"]
    scoped = with_roster.get(
        "/api/publications", params={"unit": MEDICINE, "start": 2020, "end": 2020}
    ).json()
    assert scoped["total"] == count == 2


def test_a_school_with_no_publications_gives_an_empty_list_not_everything(
    with_roster: TestClient,
) -> None:
    scoped = with_roster.get("/api/publications", params={"unit": LAW}).json()
    assert scoped["total"] == 0 and scoped["rows"] == []
    breakdown = with_roster.get("/api/publications-breakdown", params={"unit": LAW}).json()
    assert breakdown["total"] == 0 and breakdown["types"] == []


def test_not_credited_is_the_rest_of_the_corpus(with_roster: TestClient) -> None:
    assert keys(with_roster, unit=NOT_CREDITED) == {"p4"}


def test_unit_filter_without_a_roster_uses_the_department_counts(
    without_roster: TestClient,
) -> None:
    organisation = without_roster.get("/api/organisation").json()
    for school in organisation["schools"]:
        scoped = without_roster.get("/api/publications", params={"unit": school["school"]}).json()
        assert scoped["total"] == school["publications"], school
    assert keys(without_roster, unit=MEDICINE) == {"p1", "p2"}


def test_an_unknown_unit_is_a_bad_request(with_roster: TestClient) -> None:
    assert (
        with_roster.get("/api/publications", params={"unit": "School of Nothing"}).status_code
        == 400
    )


def test_unit_also_scopes_the_export_and_the_breakdown(with_roster: TestClient) -> None:
    export = with_roster.get("/api/publications/export", params={"unit": MEDICINE}).text
    assert export.count("\n") == 1 + 4  # header and four rows
    breakdown = with_roster.get("/api/publications-breakdown", params={"unit": MEDICINE}).json()
    assert breakdown["total"] == 4
    assert sum(t["publications"] for t in breakdown["types"]) == 4
    by_source = {s["code"]: s["publications"] for s in breakdown["sources"]}
    assert by_source == {"openalex": 3, "dspace_oai": 2, "ojs": 1, "orcid": 1}


def test_the_filter_options_list_the_same_units(with_roster: TestClient) -> None:
    schools = with_roster.get("/api/filters").json()["schools"]
    assert schools[0] == MEDICINE and LAW in schools and schools[-1] == NOT_CREDITED


# --- per-unit source counts for the Organisation screen ----------------------------------------


def test_organisation_reports_source_counts_per_unit_and_year(with_roster: TestClient) -> None:
    body = with_roster.get("/api/organisation").json()["unit_sources"]
    assert {s["code"] for s in body["sources"]} == {"openalex", "orcid", "dspace_oai", "ojs"}
    assert body["by_unit"][MEDICINE] == {"openalex": 3, "orcid": 1, "dspace_oai": 2, "ojs": 1}
    assert body["by_unit"][LAW] == {"openalex": 0, "orcid": 0, "dspace_oai": 0, "ojs": 0}
    assert body["all"] == {"openalex": 4, "orcid": 1, "dspace_oai": 2, "ojs": 1}
    in_2020 = with_roster.get("/api/organisation", params={"start": 2020, "end": 2020}).json()
    assert in_2020["unit_sources"]["by_unit"][MEDICINE]["openalex"] == 2  # p2, p3


def test_source_counts_exist_without_a_roster_too(without_roster: TestClient) -> None:
    by_unit = without_roster.get("/api/organisation").json()["unit_sources"]["by_unit"]
    assert by_unit[MEDICINE]["openalex"] == 2  # p1, p2
