"""Suggested author links for staff the name matching missed, and how they are confirmed."""

import importlib.util
import shutil
from pathlib import Path

import duckdb
import pytest
from fastapi.testclient import TestClient

from ihub.api.app import create_app
from ihub.staff import attribution as at
from ihub.staff import suggestions as sg
from ihub.staff.overrides import load_confirmed, merge
from ihub.staff.roster import load_roster

HEADER = "Staff ID,Surname,First Name,Second Name,Title,Occupation,School\n"
ORCID = "0000-0002-3868-4319"


def roster_of(tmp_path: Path, *rows: str):
    path = tmp_path / "staff_roster.csv"
    path.write_text(HEADER + "".join(rows), encoding="utf-8")
    loaded = load_roster(path)
    assert loaded is not None
    return path, loaded


def empty_result(roster) -> at.LinkResult:
    return at.link_authors([], roster, {})


# --- the suggestions ---------------------------------------------------------------------------


def test_close_spellings_are_suggested_but_short_words_must_match_exactly() -> None:
    assert sg._close("mukelebai", "mukelabai") >= sg.THRESHOLD
    assert sg._close("mwansa", "mwanza") == 0.0  # six letters: a different name, not a typo
    assert sg._close("mwansa", "mwansa") == 1.0


def test_an_author_with_a_variant_spelling_is_suggested(tmp_path: Path) -> None:
    _, roster = roster_of(tmp_path, "9938,MUKELEBAI,MUKELEBAI,,Mr,LECTURER III,Natural Sciences\n")
    found = sg.suggest(
        roster,
        empty_result(roster),
        [("k1", "Mukelabai Mukelabai"), ("k2", "Zulu Zulu")],
        {"k1": "A5000315992", "k2": "A2"},
    )
    assert [(s.staff_id, s.author_name, s.author_id) for s in found] == [
        ("9938", "Mukelabai Mukelabai", "A5000315992")
    ]
    assert 0.84 <= found[0].score < 1.0
    assert found[0].school == "School of Natural and Applied Sciences"


def test_a_different_short_surname_is_not_suggested(tmp_path: Path) -> None:
    _, roster = roster_of(tmp_path, "1,MWANSA,PETER,,Mr,LECTURER,Law\n")
    found = sg.suggest(roster, empty_result(roster), [("k", "Peter Mwanza")], {"k": "A1"})
    assert found == []


def test_an_unlinked_author_is_suggested_to_every_staff_member_it_could_be(tmp_path: Path) -> None:
    _, roster = roster_of(
        tmp_path, "1,KAUNDA,MARTIN,,Mr,LECTURER,Law\n", "2,KAUNDA,MARTIN,,Dr,LECTURER,Education\n"
    )
    result = at.link_authors([("k1", "Martin Kaunda")], roster, {})
    assert result.links == {}  # two people fit and nothing tells them apart: not linked
    found = sg.suggest(roster, result, [("k1", "Martin Kaunda")], {"k1": "A1"})
    assert {s.staff_id for s in found} == {"1", "2"}  # a person decides


def test_linked_staff_and_taken_authors_are_left_alone(tmp_path: Path) -> None:
    _, roster = roster_of(tmp_path, "1,CHANDA,GRACE,,Dr,LECTURER,Law\n")
    result = at.link_authors([("k1", "Grace Chanda")], roster, {})
    assert result.links["k1"].staff_id == "1"
    assert (
        sg.suggest(
            roster,
            result,
            [("k1", "Grace Chanda"), ("k2", "Chanda Grace")],
            {"k1": "A1", "k2": "A2"},
        )
        == []
    )


def test_authors_without_an_id_or_with_one_word_are_not_suggested(tmp_path: Path) -> None:
    _, roster = roster_of(tmp_path, "1,KANYANTA,CHILESHE,,Mr,LECTURER,Law\n")
    authors = [("a", "Kanyantaa Chileshe"), ("b", "Chileshe")]
    assert sg.suggest(roster, empty_result(roster), authors, {"b": "A2"}) == []  # a has no ID
    found = sg.suggest(roster, empty_result(roster), authors, {"a": "A1", "b": "A2"})
    assert [s.author_key for s in found] == ["a"]


def test_at_most_three_suggestions_per_staff_member(tmp_path: Path) -> None:
    _, roster = roster_of(tmp_path, "1,KANYANTA,KANYANTA,,Mr,LECTURER,Law\n")
    authors = [(f"k{i}", f"Kanyantaa{'a' * i} Kanyanta") for i in range(6)]
    ids = {key: f"A{i}" for i, (key, _) in enumerate(authors)}
    assert len(sg.suggest(roster, empty_result(roster), authors, ids)) <= sg.PER_STAFF


# --- confirming ----------------------------------------------------------------------------------


def test_only_confirmed_rows_are_read(tmp_path: Path) -> None:
    path = tmp_path / "staff_name_suggestions.csv"
    path.write_text(
        "Confirm,Staff ID,Author ID\n"
        f"yes,1,{ORCID}\n"
        "Y,2,A5000315992\n"
        "no,3,A1\n"
        ",4,A2\n"
        "yes,5,not-an-id\n"
        "yes,,A3\n",
        encoding="utf-8",
    )
    assert load_confirmed(path) == {"1": frozenset({ORCID}), "2": frozenset({"A5000315992"})}
    assert load_confirmed(tmp_path / "missing.csv") == {}
    assert merge({"1": frozenset({"A1"})}, {"1": frozenset({"A2"}), "2": frozenset({"A3"})}) == {
        "1": frozenset({"A1", "A2"}),
        "2": frozenset({"A3"}),
    }


@pytest.fixture
def pinnable_db(insights_db: Path, tmp_path: Path) -> Path:
    copy = tmp_path / "pinnable.duckdb"
    shutil.copy(insights_db, copy)
    with duckdb.connect(str(copy)) as con:
        con.execute(
            "UPDATE marts.dim_author SET orcid_id = ?, openalex_author_id = 'A5000315992', "
            "author_name = 'Mukelabai Mukelabai' WHERE author_key = 'a1'",
            [ORCID],
        )
    return copy


def members(db: Path, roster: Path) -> list[str]:
    app = create_app(lambda: db, require_sign_in=False, staff_roster_path=lambda: roster)
    return [row["name"] for row in TestClient(app).get("/api/members").json()["rows"]]


def test_a_confirmed_suggestion_lists_the_member_and_an_unconfirmed_one_does_not(
    pinnable_db: Path, tmp_path: Path
) -> None:
    # The roster spells the name differently from the author "Mukelabai Mukelabai".
    path, _ = roster_of(tmp_path, "5,MUKELEBAI,MUKELEBAI,,Mr,LECTURER,Law\n")
    assert members(pinnable_db, path) == []
    file = tmp_path / "staff_name_suggestions.csv"
    file.write_text(f"Confirm,Staff ID,Author ID\n,5,{ORCID}\n", encoding="utf-8")
    assert members(pinnable_db, path) == []  # not confirmed yet
    file.write_text(f"Confirm,Staff ID,Author ID\nyes,5,{ORCID}\n", encoding="utf-8")
    assert members(pinnable_db, path) == ["Mukelebai Mukelebai"]  # the file is read again


# --- the script ----------------------------------------------------------------------------------


def load_script():
    spec = importlib.util.spec_from_file_location(
        "staff_name_suggestions",
        Path(__file__).parent.parent / "scripts" / "staff_name_suggestions.py",
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_the_script_writes_the_spreadsheet_and_keeps_earlier_answers(
    pinnable_db: Path, tmp_path: Path
) -> None:
    script = load_script()
    path, _ = roster_of(tmp_path, "5,MUKELEBAI,MUKELEBAI,,Mr,LECTURER,Law\n")
    assert script.main(["--db", str(pinnable_db), "--roster", str(path)]) == 0
    target = tmp_path / "staff_name_suggestions.csv"
    lines = target.read_text(encoding="utf-8-sig").splitlines()
    assert lines[0].startswith("Confirm,Staff ID,Author ID")
    assert len(lines) == 2 and ",5,A5000315992," in lines[1] and "Mukelabai Mukelabai" in lines[1]
    # A reviewer types yes; a re-run must not lose it.
    lines[1] = "yes" + lines[1]
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert script.main(["--db", str(pinnable_db), "--roster", str(path)]) == 0
    assert target.read_text(encoding="utf-8-sig").splitlines()[1].startswith("yes,5,A5000315992,")


def test_the_script_needs_a_roster(insights_db: Path, tmp_path: Path) -> None:
    script = load_script()
    assert script.main(["--db", str(insights_db), "--roster", str(tmp_path / "none.csv")]) == 1


def test_an_answered_no_is_kept_and_not_suggested_again(pinnable_db: Path, tmp_path: Path) -> None:
    script = load_script()
    path, _ = roster_of(tmp_path, "5,MUKELEBAI,MUKELEBAI,,Mr,LECTURER,Law\n")
    assert script.main(["--db", str(pinnable_db), "--roster", str(path)]) == 0
    target = tmp_path / "staff_name_suggestions.csv"
    lines = target.read_text(encoding="utf-8-sig").splitlines()
    target.write_text(lines[0] + "\nno" + lines[1] + "\n", encoding="utf-8")
    assert script.main(["--db", str(pinnable_db), "--roster", str(path)]) == 0
    kept = target.read_text(encoding="utf-8-sig").splitlines()
    assert len(kept) == 2 and kept[1].startswith("no,5,A5000315992,")
    assert members(pinnable_db, path) == []  # a "no" never links anyone
