"""Tests for crediting schools through the staff roster (ADR-012), with invented names."""

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ihub.api.app import create_app
from ihub.mart.research import YearRange
from ihub.staff import attribution as at
from ihub.staff.roster import load_roster

HEADER = "Staff ID,Surname,First Name,Second Name,Title,Occupation,School\n"
MEDICINE = "School of Medicine"
LAW = "School of Law"
EDUCATION = "School of Education"
ALL = YearRange(2019, 2022)


def roster_from(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "roster.csv"
    path.write_text(HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def link(tmp_path: Path, rows: list[str], authors, evidence=None) -> at.LinkResult:
    roster = load_roster(roster_from(tmp_path, rows))
    assert roster is not None
    return at.link_authors(authors, roster, evidence or {})


def test_a_matching_author_is_credited_to_the_roster_school(tmp_path: Path) -> None:
    result = link(tmp_path, ["1,MWANSA,ALICE,,Dr,LECTURER,Medicine"], [("a1", "Alice Mwansa")])
    assert result.links["a1"] == at.AuthorLink(frozenset({MEDICINE}), at.ROSTER, "exact")
    assert result.stats.roster_linked == 1
    assert result.stats.roster_staff_matched == 1


def test_a_name_in_two_schools_is_resolved_by_department_evidence_or_left_out(
    tmp_path: Path,
) -> None:
    rows = ["1,PHIRI,JOHN,,Mr,LECTURER,Medicine", "2,PHIRI,JOHN,,Mr,LECTURER,Law"]
    authors = [("a1", "John Phiri")]

    undecided = link(tmp_path, rows, authors)
    assert "a1" not in undecided.links
    assert undecided.stats.ambiguous == 1  # two schools fit, nothing to choose between them

    decided = link(tmp_path, rows, authors, {"a1": frozenset({LAW})})
    assert decided.links["a1"].schools == {LAW}
    assert decided.links["a1"].basis == at.TIEBREAK
    assert decided.stats.tiebroken == 1


def test_a_fellow_takes_the_school_of_their_department_or_none(tmp_path: Path) -> None:
    rows = ["1,MUBITA,KAIKO,,Mr,LECTURER,SDF"]
    authors = [("a1", "Kaiko Mubita")]
    assert link(tmp_path, rows, authors).stats.fellows_without_evidence == 1
    assert "a1" not in link(tmp_path, rows, authors).links
    result = link(tmp_path, rows, authors, {"a1": frozenset({EDUCATION})})
    assert result.links["a1"] == at.AuthorLink(frozenset({EDUCATION}), at.FELLOW, "exact")


def test_an_initial_counts_only_when_department_evidence_agrees(tmp_path: Path) -> None:
    rows = ["1,TEMBO,LANGA,,Dr,LECTURER,Education"]
    authors = [("a1", "L. Tembo")]
    alone = link(tmp_path, rows, authors)
    assert "a1" not in alone.links
    assert alone.stats.initials_uncorroborated == 1
    backed = link(tmp_path, rows, authors, {"a1": frozenset({EDUCATION})})
    assert backed.links["a1"].basis == at.ROSTER
    assert backed.links["a1"].rule == "initial"
    wrong = link(tmp_path, rows, authors, {"a1": frozenset({LAW})})
    assert wrong.links["a1"].basis == at.DEPARTMENT_ONLY  # roster ignored, evidence kept


def test_an_ambiguous_initial_is_counted(tmp_path: Path) -> None:
    rows = ["1,BANDA,CHANDA,,Mr,LECTURER,Medicine", "2,BANDA,CHARLES,,Mr,LECTURER,Law"]
    result = link(tmp_path, rows, [("a1", "C. Banda")])
    assert result.stats.ambiguous == 1


def test_authors_not_on_the_roster_keep_their_department_evidence_separately(
    tmp_path: Path,
) -> None:
    result = link(
        tmp_path,
        ["1,MWANSA,ALICE,,Dr,LECTURER,Medicine"],
        [("a1", "Alice Mwansa"), ("a2", "Zed Nobody"), ("a3", "Yan Nobody")],
        {"a2": frozenset({LAW})},
    )
    assert result.links["a2"] == at.AuthorLink(frozenset({LAW}), at.DEPARTMENT_ONLY)
    assert "a3" not in result.links
    assert (result.stats.department_only, result.stats.unmatched) == (1, 1)


def test_publications_count_once_per_school_and_each_school_gets_credit(tmp_path: Path) -> None:
    result = link(
        tmp_path,
        ["1,MWANSA,ALICE,,Dr,LECTURER,Medicine", "2,SMITH,BOB,,Dr,LECTURER,Law"],
        [("a1", "Alice Mwansa"), ("a2", "Bob Smith"), ("a3", "Zed Nobody")],
        {"a3": frozenset({LAW})},
    )
    pairs = [("a1", "p1"), ("a1", "p2"), ("a2", "p2"), ("a3", "p3"), ("a3", "p1")]
    report = at.aggregate(result, pairs, ALL, total_publications=10)
    by_school = {s.school: s for s in report.schools}
    assert by_school[MEDICINE].roster_publications == 2  # p1, p2
    assert by_school[LAW].roster_publications == 1  # p2, through Bob
    assert by_school[LAW].publications == 3  # p1, p2, p3 once Zed's evidence is added
    assert report.credited_by_roster == 2
    assert report.credited_any == 3
    assert report.total_publications == 10
    assert (by_school[MEDICINE].staff_in_roster, by_school[MEDICINE].staff_matched) == (1, 1)


def test_roster_schools_with_no_publications_still_appear(tmp_path: Path) -> None:
    result = link(tmp_path, ["1,MWANSA,ALICE,,Dr,LECTURER,Medicine"], [])
    report = at.aggregate(result, [], ALL, 0)
    assert [(s.school, s.publications, s.staff_in_roster) for s in report.schools] == [
        (MEDICINE, 0, 1)
    ]


# --- against the tiny mart ---------------------------------------------------------------------


def test_school_credit_reads_authors_and_authorships_from_the_mart(
    insights_db: Path, tmp_path: Path
) -> None:
    roster = roster_from(tmp_path, ["1,MWANSA,ALICE,,Dr,LECTURER,Medicine"])
    report = at.school_credit(insights_db, roster, ALL, 5)
    assert report is not None
    assert [(s.school, s.roster_publications) for s in report.schools] == [(MEDICINE, 4)]
    only_2020 = at.school_credit(insights_db, roster, YearRange(2020, 2020), 2)
    assert only_2020 is not None
    assert only_2020.schools[0].roster_publications == 2  # p2, p3


def test_school_credit_without_a_roster_is_none(insights_db: Path, tmp_path: Path) -> None:
    assert at.school_credit(insights_db, tmp_path / "none.csv", ALL, 5) is None


def test_a_changed_roster_file_is_read_again(insights_db: Path, tmp_path: Path) -> None:
    roster = roster_from(tmp_path, ["1,MWANSA,ALICE,,Dr,LECTURER,Medicine"])
    first = at.school_credit(insights_db, roster, ALL, 5)
    assert first is not None and first.schools[0].school == MEDICINE
    roster.write_text(HEADER + "1,MWANSA,ALICE,,Dr,LECTURER,Law\n", encoding="utf-8")
    second = at.school_credit(insights_db, roster, ALL, 5)
    assert second is not None and second.schools[0].school == LAW


# --- the API -----------------------------------------------------------------------------------


@pytest.fixture
def client(insights_db: Path, tmp_path: Path) -> TestClient:
    roster = roster_from(tmp_path, ["1001,MWANSA,ALICE,,Dr,LECTURER,Medicine"])
    return TestClient(
        create_app(lambda: insights_db, require_sign_in=False, staff_roster=lambda: roster)
    )


def test_the_api_reports_school_credit_without_any_names_or_staff_ids(client: TestClient) -> None:
    response = client.get("/api/organisation")
    body = response.json()
    credit = body["school_credit"]
    assert credit["source"] == "staff_roster"
    assert credit["schools"][0]["school"] == MEDICINE
    assert credit["schools"][0]["roster_publications"] == 4
    assert credit["credited_by_roster"] == 4
    assert credit["stats"]["roster_linked"] == 1
    text = json.dumps(credit)
    for private in ("Alice", "Mwansa", "1001"):
        assert private not in text
    assert client.get("/api/overview").json()["school_credit"]["schools"][0]["school"] == MEDICINE


def test_the_api_falls_back_when_there_is_no_roster(insights_db: Path, tmp_path: Path) -> None:
    client = TestClient(
        create_app(
            lambda: insights_db,
            require_sign_in=False,
            staff_roster=lambda: tmp_path / "missing.csv",
        )
    )
    body = client.get("/api/organisation").json()
    assert body["school_credit"] is None
    assert body["schools"]  # the department-based counts are still there
