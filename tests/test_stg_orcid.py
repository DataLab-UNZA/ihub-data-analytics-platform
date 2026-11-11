"""Tests for the ORCID staging models, built from the recorded ORCID API responses.
Never calls the live API."""

import copy
from pathlib import Path
from typing import Any

import pytest

from ihub.connectors.orcid import OrcidConnector
from tests.dbt_helpers import load_raw, query, run_dbt
from tests.test_orcid_connector import CONFIG, EMPLOYMENTS, IDS, WORKS, make_client
from tests.test_orcid_connector import recorded_handler as orcid_handler

SELECT = "path:models/staging/orcid"
OTHER_ID = "0000-0000-0000-0001"


def recorded_records(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, dict[str, Any]]]:
    """Every record the connector yields for the recorded responses (three iDs)."""
    monkeypatch.setenv("ORCID_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("ORCID_CLIENT_SECRET", "test-secret")
    connector = OrcidConnector(CONFIG, client=make_client(orcid_handler))
    return list(connector.fetch_records())


def other_researcher() -> tuple[str, dict[str, Any]]:
    """A record whose only DOI is a "part-of" DOI and whose employer is not UNZA."""
    works = copy.deepcopy(WORKS)
    for external_id in works["group"][0]["external-ids"]["external-id"]:
        external_id["external-id-relationship"] = "part-of"
    employments = copy.deepcopy(EMPLOYMENTS)
    summary = employments["affiliation-group"][0]["summaries"][0]["employment-summary"]
    summary["organization"] = {
        "name": "University of Cape Town",
        "address": {"city": "Cape Town", "country": "ZA"},
        "disambiguated-organization": None,
    }
    summary["end-date"] = {"year": {"value": "2019"}, "month": None, "day": None}
    return OTHER_ID, {"orcid": OTHER_ID, "works": works, "employments": employments}


#: Department names as researchers really write them in ORCID (seen on November 11, 2026),
#: and the key each one is matched on.
DEPARTMENT_KEYS = {
    "School of Engineering, Department of Geomatic Engineering": "geomatic engineering",
    "Pharmacy Department": "pharmacy",
    "Paraclinical Studies, School of Veterinary Medicine": "paraclinical studies",
    "Dept. of Food Science & Nutrition": "food science and nutrition",
    "School of Medicine": "school of medicine",
    "The Library": "library",
}


def researcher_with_two_versions_of_a_work() -> tuple[str, dict[str, Any]]:
    """A work added by two sources, where the preferred one (highest display-index) is second."""
    works = copy.deepcopy(WORKS)
    group = works["group"][0]
    listed_first = group["work-summary"][0]
    listed_first["display-index"] = "0"
    preferred = copy.deepcopy(listed_first)
    preferred["put-code"] = 999
    preferred["display-index"] = "1"
    preferred["title"]["title"]["value"] = "The researcher's preferred title"
    group["work-summary"].append(preferred)
    orcid_id = "0000-0000-0000-0003"
    return orcid_id, {"orcid": orcid_id, "works": works, "employments": {}}


def researcher_with_departments() -> tuple[str, dict[str, Any]]:
    """A UNZA researcher with one employment for each name in DEPARTMENT_KEYS."""
    employments = copy.deepcopy(EMPLOYMENTS)
    template = employments["affiliation-group"][0]
    employments["affiliation-group"] = []
    for put_code, name in enumerate(DEPARTMENT_KEYS, start=1):
        group = copy.deepcopy(template)
        summary = group["summaries"][0]["employment-summary"]
        summary["put-code"] = put_code
        summary["department-name"] = name
        employments["affiliation-group"].append(group)
    orcid_id = "0000-0000-0000-0002"
    return orcid_id, {"orcid": orcid_id, "works": {"group": []}, "employments": employments}


@pytest.fixture(scope="module")
def db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    with pytest.MonkeyPatch.context() as monkeypatch:
        records = recorded_records(monkeypatch)
    path = tmp_path_factory.mktemp("orcid") / "test.duckdb"
    extra = [
        records[0],
        other_researcher(),
        researcher_with_departments(),
        researcher_with_two_versions_of_a_work(),
    ]
    load_raw(path, "orcid", [*records, *extra])
    run_dbt(path, "build", SELECT)
    return path


def test_compound_department_names_reduce_to_the_department(db: Path) -> None:
    rows = query(
        db,
        "select department_name, department_name_key from staging.stg_orcid__employments "
        "where orcid_id = '0000-0000-0000-0002'",
    )
    assert {r["department_name"]: r["department_name_key"] for r in rows} == DEPARTMENT_KEYS


def test_one_row_per_researcher(db: Path) -> None:
    rows = query(db, "select orcid_id, n_works from staging.stg_orcid__researchers order by 1")
    extra_ids = ["0000-0000-0000-0002", "0000-0000-0000-0003"]
    assert [r["orcid_id"] for r in rows] == sorted([*IDS, OTHER_ID, *extra_ids])
    assert [r["n_works"] for r in rows if r["orcid_id"] in IDS] == [1, 1, 1]


def test_works_are_read_from_the_preferred_summary(db: Path) -> None:
    rows = query(db, f"select * from staging.stg_orcid__works where orcid_id = '{IDS[0]}'")
    assert len(rows) == 1
    work = rows[0]
    assert work["orcid_work_id"] == f"{IDS[0]}:217903668"
    assert work["title"].startswith("Global South Health Practitioners")
    assert work["year"] == 2026
    assert (work["type"], work["source_type"]) == ("book-chapter", "book-chapter")
    assert work["doi"] == "10.1007/978-3-032-13654-1_18"
    assert work["added_by"] == "Crossref"


def test_a_doi_the_work_is_only_part_of_is_not_its_doi(db: Path) -> None:
    rows = query(db, f"select doi from staging.stg_orcid__works where orcid_id = '{OTHER_ID}'")
    assert rows == [{"doi": None}]


def test_employments_name_the_department_and_recognise_unza(db: Path) -> None:
    rows = query(db, f"select * from staging.stg_orcid__employments where orcid_id = '{IDS[0]}'")
    assert len(rows) == 1
    job = rows[0]
    assert job["organisation_name"] == "University of Zambia"
    assert job["department_name"] == "Department of Library and Information Science"
    assert job["department_name_key"] == "library and information science"
    assert job["role_title"] == "Lecturer and Researcher"
    assert (job["start_year"], job["start_month"], job["end_year"]) == (2017, 12, None)
    assert job["is_current"] is True
    assert (job["organisation_identifier"], job["organisation_identifier_source"]) == (
        "108234",
        "RINGGOLD",
    )
    assert job["country_code"] == "ZM"
    assert job["is_unza"] is True


def test_another_employer_is_not_unza(db: Path) -> None:
    rows = query(
        db,
        "select is_unza, is_current from staging.stg_orcid__employments "
        f"where orcid_id = '{OTHER_ID}'",
    )
    assert rows == [{"is_unza": False, "is_current": False}]


def test_the_summary_with_the_highest_display_index_describes_the_work(db: Path) -> None:
    rows = query(
        db,
        "select orcid_work_id, title from staging.stg_orcid__works "
        "where orcid_id = '0000-0000-0000-0003'",
    )
    assert rows == [
        {
            "orcid_work_id": "0000-0000-0000-0003:999",
            "title": "The researcher's preferred title",
        }
    ]
