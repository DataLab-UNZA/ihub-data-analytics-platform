"""Tests for name handling, the roster loader and the matching rules (ADR-012).

All names here are invented: the real staff roster is private and never used in tests.
"""

from pathlib import Path

import pytest

from ihub.staff import matching
from ihub.staff.names import name_words, parse_person
from ihub.staff.roster import load_roster, school_for_label

HEADER = "Staff ID,Surname,First Name,Second Name,Title,Occupation,School\n"


def write_roster(tmp_path: Path, rows: list[str]) -> Path:
    path = tmp_path / "roster.csv"
    path.write_text("﻿" + HEADER + "\n".join(rows) + "\n", encoding="utf-8")
    return path


def index_of(tmp_path: Path, rows: list[str]) -> matching.RosterIndex:
    roster = load_roster(write_roster(tmp_path, rows))
    assert roster is not None
    return matching.RosterIndex(roster.members)


def rules(name: str, index: matching.RosterIndex) -> list[str]:
    return [c.rule for c in matching.match_name(parse_person(name), index).candidates]


# --- names ------------------------------------------------------------------------------------


def test_name_words_normalises_case_accents_apostrophes_hyphens_and_titles() -> None:
    assert name_words("Dr. Ng'andu-Phiri") == ["ngandu", "phiri"]
    assert name_words("NGÚNI, Alice") == ["nguni", "alice"]
    assert name_words("Mwaba, 0 C Sydney") == ["mwaba", "c", "sydney"]  # digits are dropped
    assert name_words(None) == []


def test_parse_person_separates_words_from_initials_and_notes_the_surname_before_a_comma() -> None:
    person = parse_person("Banda, C. John")
    assert person.words == {"banda", "john"}
    assert person.initials == {"c"}
    assert person.surname_hint == {"banda"}
    assert parse_person("John Banda").surname_hint == frozenset()
    assert parse_person("  ").is_empty


# --- roster -----------------------------------------------------------------------------------


def test_school_labels_map_to_mart_names_and_sdf_has_no_school() -> None:
    assert school_for_label("Natural Sciences") == "School of Natural and Applied Sciences"
    assert school_for_label("  medicine ") == "School of Medicine"
    assert school_for_label("SDF") is None
    assert school_for_label("") is None
    assert school_for_label("Brand New Centre") == "Brand New Centre"  # kept, not dropped


def test_load_roster_reads_a_bom_file_skips_nameless_rows_and_counts_schools(
    tmp_path: Path,
) -> None:
    path = write_roster(
        tmp_path,
        [
            "1,BANDA,CHANDA,JOHN,Mr,LECTURER,Medicine",
            "2,,,,,,Medicine",
            "3,NG'ANDU,SOPHIE,,Dr,LECTURER,SDF",
        ],
    )
    roster = load_roster(path)
    assert roster is not None
    assert roster.headcount == 2
    assert roster.skipped_rows == 1
    assert roster.by_label == {"Medicine": 1, "SDF": 1}
    assert [m.school for m in roster.members] == ["School of Medicine", None]


def test_load_roster_without_a_file_is_none(tmp_path: Path) -> None:
    assert load_roster(tmp_path / "missing.csv") is None


# --- matching ---------------------------------------------------------------------------------


def test_exact_and_surname_first_spellings_match(tmp_path: Path) -> None:
    index = index_of(tmp_path, ["1,BANDA,CHANDA,,Mr,LECTURER,Medicine"])
    assert rules("Chanda Banda", index) == [matching.EXACT]
    assert rules("Banda, Chanda", index) == [matching.EXACT]
    assert rules("BANDA CHANDA", index) == [matching.EXACT]
    assert rules("Dr. Chanda Banda", index) == [matching.EXACT]


def test_an_author_who_leaves_out_a_middle_name_matches_as_a_subset(tmp_path: Path) -> None:
    index = index_of(tmp_path, ["1,BANDA,CHANDA,JOHN,Mr,LECTURER,Medicine"])
    assert rules("Chanda Banda", index) == [matching.AUTHOR_SUBSET]
    assert rules("John Banda", index) == [matching.AUTHOR_SUBSET]


def test_an_author_who_adds_a_middle_name_matches_when_two_roster_words_remain(
    tmp_path: Path,
) -> None:
    index = index_of(tmp_path, ["1,BANDA,CHANDA,,Mr,LECTURER,Medicine"])
    assert rules("Chanda Peter Banda", index) == [matching.ROSTER_SUBSET]


def test_apostrophes_and_hyphens_do_not_block_a_match(tmp_path: Path) -> None:
    index = index_of(
        tmp_path,
        [
            "1,NG'ANDU,SOPHIE,,Dr,LECTURER,Education",
            "2,NAMUSAMBA - KAMANGA,MWICHIE,,Ms,LECTURER,SDF",
        ],
    )
    assert rules("Sophie Ngandu", index) == [matching.EXACT]
    assert rules("Mwichie Namusamba-Kamanga", index) == [matching.EXACT]
    assert rules("Mwichie Kamanga", index) == [matching.AUTHOR_SUBSET]


def test_columns_swapped_in_the_roster_still_match(tmp_path: Path) -> None:
    index = index_of(tmp_path, ["1,ELIZABETH,MWEWA,,Ms,LECTURER,Humanities and Social Sciences"])
    assert rules("Mwewa Elizabeth", index) == [matching.EXACT]
    assert rules("Elizabeth Mwewa", index) == [matching.EXACT]


def test_a_name_without_a_roster_surname_never_matches(tmp_path: Path) -> None:
    index = index_of(tmp_path, ["1,BANDA,CHANDA,JOHN,Mr,LECTURER,Medicine"])
    assert rules("Chanda John", index) == []  # two given names, no surname
    assert rules("Chanda Phiri", index) == []  # same given name, different person
    assert rules("Chanda", index) == []  # a single word is not enough


def test_an_initial_matches_only_when_the_roster_can_account_for_it(tmp_path: Path) -> None:
    index = index_of(tmp_path, ["1,BANDA,CHANDA,JOHN,Mr,LECTURER,Medicine"])
    assert rules("C. Banda", index) == [matching.INITIAL]
    assert rules("J Banda", index) == [matching.INITIAL]  # a second name's initial counts
    assert rules("P. Banda", index) == []  # no such initial on the roster entry
    assert rules("Chanda P. Banda", index) == []  # an unexplained initial rejects a subset match


def test_an_initial_that_fits_several_people_is_ambiguous_and_not_chosen(tmp_path: Path) -> None:
    index = index_of(
        tmp_path,
        [
            "1,BANDA,CHANDA,,Mr,LECTURER,Medicine",
            "2,BANDA,CHARLES,,Mr,LECTURER,Law",
        ],
    )
    outcome = matching.match_name(parse_person("C. Banda"), index)
    assert outcome.ambiguous
    assert outcome.candidates == ()
    # a whole first name still separates them
    assert rules("Chanda Banda", index) == [matching.EXACT]


def test_the_strongest_rule_wins_over_a_weaker_one(tmp_path: Path) -> None:
    index = index_of(
        tmp_path,
        [
            "1,BANDA,CHANDA,,Mr,LECTURER,Medicine",
            "2,BANDA,CHANDA,JOHN,Mr,LECTURER,Law",
        ],
    )
    outcome = matching.match_name(parse_person("Chanda Banda"), index)
    assert [c.rule for c in outcome.candidates] == [matching.EXACT]
    assert [c.member.school for c in outcome.candidates] == ["School of Medicine"]


@pytest.mark.parametrize("name", ["", "   ", "Dr.", "123"])
def test_nothing_matches_an_empty_name(tmp_path: Path, name: str) -> None:
    index = index_of(tmp_path, ["1,BANDA,CHANDA,,Mr,LECTURER,Medicine"])
    assert rules(name, index) == []
