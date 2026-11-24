"""The public staff list: connector, dbt models and the roster source (ADR-017).

The sample has the shape of the published sheet (a blank first column where the staff IDs were
removed, a byte-order mark, Windows line endings) with made-up names. No live call is made.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import duckdb
import httpx
import pytest

from ihub.connectors.unza_staff import PUBLIC_COLUMNS, UnzaStaffConnector, UnzaStaffError
from ihub.staff.roster import load_roster, roster_from_rows, staff_key
from ihub.staff.sources import CsvRosterSource, MartRosterSource, choose_roster
from tests.dbt_helpers import build_warehouse, make_work, query

SAMPLE = Path(__file__).parent / "fixtures" / "unza_staff" / "staff_list_sample.csv"
URL = "https://docs.example/pub?output=csv"


def connector_for(body: bytes, url: str = URL) -> UnzaStaffConnector:
    transport = httpx.MockTransport(lambda request: httpx.Response(200, content=body))
    return UnzaStaffConnector({}, client=httpx.Client(transport=transport), url=url)


def test_rows_keep_only_public_columns_and_skip_blank_rows() -> None:
    records = list(connector_for(SAMPLE.read_bytes()).fetch_records())
    assert len(records) == 4  # the empty row is skipped
    for _, row in records:
        assert tuple(row) == PUBLIC_COLUMNS
    assert records[2][1]["First Name"] == "GRACE"


def test_a_staff_id_column_is_never_fetched() -> None:
    body = (
        b"Staff ID,Surname,First Name,Second Name,Title,Occupation,School\n12345,BANDA,C,,,,Law\n"
    )
    [(record_id, row)] = list(connector_for(body).fetch_records())
    assert "Staff ID" not in row and "12345" not in str(row) and "12345" not in record_id


def test_identical_rows_get_different_record_ids() -> None:
    ids = [record_id for record_id, _ in connector_for(SAMPLE.read_bytes()).fetch_records()]
    assert len(ids) == len(set(ids))


def test_without_an_address_nothing_is_fetched() -> None:
    assert list(connector_for(b"", url="").fetch_records()) == []


def test_a_page_that_is_not_the_list_is_an_error() -> None:
    with pytest.raises(UnzaStaffError):
        list(connector_for(b"<html>Sign in</html>").fetch_records())


def test_the_key_ignores_case_and_spacing_and_duplicates_stay_two_people() -> None:
    row = {"Surname": "BANDA", "First Name": "CHANDA", "Second Name": "", "School": "Law"}
    assert staff_key(row) == staff_key({**row, "Surname": " banda ", "Second Name": None})
    roster = roster_from_rows([row, dict(row)])
    keys = [member.staff_key for member in roster.members]
    assert keys == [staff_key(row), staff_key(row) + "-2"]


@pytest.fixture(scope="module")
def staff_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    records = list(connector_for(SAMPLE.read_bytes()).fetch_records())
    return build_warehouse(
        tmp_path_factory.mktemp("staff") / "test.duckdb",
        [make_work("W1", authors=[("A1", "Chanda Banda", None)])],
        extra_raw={"unza_staff": records},
    )


@pytest.fixture
def staff_mart(staff_db: Path, insights_db: Path, tmp_path: Path) -> Path:
    """The tiny insights mart plus the ``dim_staff`` dbt built (dbt keeps its file open)."""
    rows = query(staff_db, "SELECT * FROM marts.dim_staff")
    copy = tmp_path / "staff_mart.duckdb"
    shutil.copy(insights_db, copy)
    with duckdb.connect(str(copy)) as con:
        con.execute(
            "CREATE TABLE marts.dim_staff (staff_key VARCHAR, surname VARCHAR, first_name VARCHAR,"
            " second_name VARCHAR, title VARCHAR, occupation VARCHAR, school_label VARCHAR)"
        )
        con.executemany(
            "INSERT INTO marts.dim_staff VALUES (?, ?, ?, ?, ?, ?, ?)",
            [list(row.values()) for row in rows],
        )
    return copy


def test_dim_staff_holds_one_row_per_person_and_no_staff_id(staff_db: Path) -> None:
    rows = query(staff_db, "SELECT * FROM marts.dim_staff ORDER BY surname, first_name")
    assert [(r["surname"], r["first_name"], r["school_label"]) for r in rows] == [
        ("BANDA", "CHANDA", "Law"),
        ("MWANSA", "ALICE", "Natural Sciences"),
        ("MWANSA", "ALICE", "Natural Sciences"),
        ("PHIRI", "GRACE", "SDF"),
    ]
    assert rows[3]["second_name"] is None
    assert not any("staff_id" in column for column in rows[0])


def test_the_mart_and_the_csv_give_the_same_people(staff_mart: Path, tmp_path: Path) -> None:
    from_mart = MartRosterSource(staff_mart).load()
    local = tmp_path / "staff_roster.csv"
    local.write_bytes(SAMPLE.read_bytes())
    from_csv = load_roster(local)
    assert from_mart is not None and from_csv is not None
    assert sorted(m.staff_key for m in from_mart.members) == sorted(
        m.staff_key for m in from_csv.members
    )
    assert {m.school for m in from_mart.members} == {
        "School of Law",
        "School of Natural and Applied Sciences",
        None,
    }


def test_choose_roster_prefers_the_local_file_then_the_mart(
    staff_mart: Path, insights_db: Path, tmp_path: Path
) -> None:
    local = tmp_path / "staff_roster.csv"
    assert isinstance(choose_roster(local, staff_mart), MartRosterSource)
    local.write_bytes(SAMPLE.read_bytes())
    assert isinstance(choose_roster(local, staff_mart), CsvRosterSource)
    assert choose_roster(tmp_path / "missing.csv", insights_db) is None  # no dim_staff
