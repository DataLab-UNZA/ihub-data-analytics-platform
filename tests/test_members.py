"""Tests for the Members directory built from the staff roster (ADR-014), with invented names."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ihub.api.app import create_app
from ihub.auth.rbac import ROLE_PERMISSIONS, Permission, Role
from ihub.staff.roster import load_roster
from tests.auth_helpers import ADMIN, STAFF, make_harness

HEADER = "Staff ID,Surname,First Name,Second Name,Title,Occupation,School\n"
ALICE = "1001,MWANSA,ALICE,,Dr,LECTURER,Medicine\n"


def roster_with(tmp_path: Path, *rows: str) -> Path:
    path = tmp_path / "roster.csv"
    path.write_text(HEADER + "".join(rows), encoding="utf-8")
    return path


def client_for(insights_db: Path, roster: Path) -> TestClient:
    return TestClient(
        create_app(lambda: insights_db, require_sign_in=False, staff_roster_path=lambda: roster)
    )


@pytest.fixture
def client(insights_db: Path, tmp_path: Path) -> TestClient:
    return client_for(
        insights_db, roster_with(tmp_path, ALICE, "2002,PHIRI,JOHN,,Mr,LECTURER,Law\n")
    )


def test_the_roster_keeps_the_title_and_a_display_name(tmp_path: Path) -> None:
    roster = load_roster(roster_with(tmp_path, "7,BANDA,CHANDA,JOHN,Prof,LECTURER,Law\n"))
    assert roster is not None
    member = roster.members[0]
    assert (member.title, member.display_name) == ("Prof", "Chanda John Banda")


def test_the_directory_lists_matched_staff_with_title_orcid_and_counts(client: TestClient) -> None:
    body = client.get("/api/members").json()
    assert body["available"] is True and body["total"] == 1  # John Phiri has no author record
    row = body["rows"][0]
    assert (row["title"], row["name"], row["school"]) == (
        "Dr",
        "Alice Mwansa",
        "School of Medicine",
    )
    assert row["orcid"] == "0000-0001" and row["orcid_url"] == "https://orcid.org/0000-0001"
    assert row["publications"] == 4
    assert body["units"] == ["School of Medicine"]


def test_nothing_in_the_response_exposes_a_staff_id(client: TestClient) -> None:
    row = client.get("/api/members").json()["rows"][0]
    assert "1001" not in str(row) and row["member_id"].startswith("m")
    profile = client.get(f"/api/members/{row['member_id']}").json()
    assert "1001" not in str(profile)


def test_the_period_changes_the_counts(client: TestClient) -> None:
    row = client.get("/api/members", params={"start": 2020, "end": 2020}).json()["rows"][0]
    assert row["publications"] == 2  # p2, p3


def test_the_directory_can_be_searched_and_filtered(client: TestClient) -> None:
    def total(**params: str) -> int:
        return client.get("/api/members", params=params).json()["total"]

    assert total(q="dr mwansa") == 1 and total(q="ALICE") == 1
    assert total(q="phiri") == 0
    assert total(unit="School of Medicine") == 1 and total(unit="School of Law") == 0
    assert total(orcid="linked") == 1 and total(orcid="unknown") == 0


def test_a_profile_has_totals_and_newest_first_publications(client: TestClient) -> None:
    member_id = client.get("/api/members").json()["rows"][0]["member_id"]
    body = client.get(f"/api/members/{member_id}").json()
    assert body["member"]["publications"] == 4
    assert body["member"]["open_access"] == 3 and body["member"]["citations"] == 31
    assert body["total"] == 4
    assert [r["year"] for r in body["rows"]] == [2022, 2020, 2020, 2019]
    assert {r["publication_key"] for r in body["rows"]} == {"p1", "p2", "p3", "p5"}
    only_2019 = client.get(f"/api/members/{member_id}", params={"start": 2019, "end": 2019}).json()
    assert [r["publication_key"] for r in only_2019["rows"]] == ["p1"]


def test_an_unknown_member_is_a_404(client: TestClient) -> None:
    assert client.get("/api/members/mdoesnotexist").status_code == 404


def test_two_staff_with_the_same_name_are_not_merged_into_one_profile(
    insights_db: Path, tmp_path: Path
) -> None:
    roster = roster_with(tmp_path, ALICE, "1002,MWANSA,ALICE,,Mr,LECTURER,Medicine\n")
    client = client_for(insights_db, roster)
    assert client.get("/api/members").json()["rows"] == []
    # ... but the school is still credited, because both are in the same school.
    credit = client.get("/api/organisation").json()["school_credit"]
    assert credit["schools"][0]["roster_publications"] == 4


def test_without_a_roster_the_directory_is_not_available(insights_db: Path, tmp_path: Path) -> None:
    client = client_for(insights_db, tmp_path / "missing.csv")
    body = client.get("/api/members").json()
    assert body["available"] is False and body["rows"] == []
    assert client.get("/api/members/manything").status_code == 404


def test_only_leadership_roles_may_read_members() -> None:
    allowed = {r for r, p in ROLE_PERMISSIONS.items() if Permission.MEMBERS_READ in p}
    assert allowed == {Role.UNIT_HEAD, Role.EXECUTIVE, Role.ADMIN}


def test_the_members_routes_need_the_members_permission(insights_db: Path, tmp_path: Path) -> None:
    roster = roster_with(tmp_path, ALICE)
    h = make_harness(tmp_path)
    app = create_app(
        lambda: insights_db,
        auth_service=lambda: h.service,
        require_sign_in=True,
        staff_roster_path=lambda: roster,
    )
    anonymous = TestClient(app)
    assert anonymous.get("/api/members").status_code == 401
    member = TestClient(app)
    member.headers["Authorization"] = f"Bearer {h.sign_in_by_email(STAFF).access_token}"
    assert member.get("/api/publications").status_code == 200  # research:read is not enough
    assert member.get("/api/members").status_code == 403
    admin = TestClient(app)
    admin.headers["Authorization"] = f"Bearer {h.sign_in_by_email(ADMIN).access_token}"
    assert admin.get("/api/members").status_code == 200


# --- the global filters (period, unit, source, type) ---------------------------------------------


def listed(client: TestClient, **params: str) -> list[tuple[str, int]]:
    rows = client.get("/api/members", params=params).json()["rows"]
    return [(r["name"], r["publications"]) for r in rows]


def test_every_global_filter_changes_the_directory(client: TestClient) -> None:
    assert listed(client) == [("Alice Mwansa", 4)]
    assert listed(client, start=2020, end=2020) == [("Alice Mwansa", 2)]
    assert listed(client, type="Review") == [("Alice Mwansa", 1)]  # p2 only
    assert listed(client, source="OJS") == [("Alice Mwansa", 1)]  # p5 only
    assert listed(client, unit="School of Medicine") == [("Alice Mwansa", 4)]


def test_members_without_publications_under_the_filters_are_not_listed(client: TestClient) -> None:
    assert listed(client, start=2021, end=2021) == []  # nothing in 2021
    assert listed(client, unit="School of Law") == []
    assert listed(client, type="Dataset") == []
    assert client.get("/api/members", params={"start": 2021, "end": 2021}).json()["total"] == 0


def test_the_profile_follows_the_same_filters(client: TestClient) -> None:
    member_id = client.get("/api/members").json()["rows"][0]["member_id"]
    body = client.get(f"/api/members/{member_id}", params={"type": "Review"}).json()
    assert [r["publication_key"] for r in body["rows"]] == ["p2"]
    assert body["member"]["publications"] == 1 and body["member"]["citations"] == 20
    none = client.get(f"/api/members/{member_id}", params={"type": "Dataset"}).json()
    assert none["rows"] == [] and none["member"]["publications"] == 0


# --- hand-confirmed links (the overrides file) ---------------------------------------------------


def test_author_ids_are_normalised() -> None:
    from ihub.staff.overrides import normalise_author_id as norm

    assert norm("https://openalex.org/a5000315992") == "A5000315992"
    assert norm("https://orcid.org/0000-0002-3868-4319") == "0000-0002-3868-4319"
    assert norm("0000-0002-3868-431x") == "0000-0002-3868-431X"
    assert norm("not an id") is None and norm("") is None and norm(None) is None


def test_the_overrides_file_is_read_leniently(tmp_path: Path) -> None:
    from ihub.staff.overrides import load_overrides, overrides_path

    assert load_overrides(tmp_path / "missing.csv") == {}
    path = tmp_path / "o.csv"
    path.write_text("Staff ID,Author ID\n7,A5000315992\n7,0000-0002-3868-4319\n,A1\n8,junk\n")
    assert load_overrides(path) == {"7": frozenset({"A5000315992", "0000-0002-3868-4319"})}
    assert overrides_path(tmp_path / "staff_roster.csv").name == "staff_author_overrides.csv"


def test_a_pin_matches_an_openalex_id_or_an_orcid_and_contradictions_are_dropped() -> None:
    from ihub.staff.overrides import pin_authors

    ids = [
        ("k1", "https://openalex.org/A5000315992", None),
        ("k2", None, "0000-0002-3868-4319"),
        ("k3", "A9", None),
        ("k4", "A7", None),
    ]
    overrides = {
        "9936": frozenset({"A5000315992", "0000-0002-3868-4319"}),
        "1": frozenset({"A7"}),
        "2": frozenset({"A7"}),  # A7 is claimed by two people: nobody gets it
    }
    assert pin_authors(overrides, ids) == {"k1": "9936", "k2": "9936"}


ORCID = "0000-0002-3868-4319"


@pytest.fixture
def pinnable_db(insights_db: Path, tmp_path: Path) -> Path:
    """A copy of the tiny mart whose author Alice has an OpenAlex ID and a full ORCID iD."""
    import shutil

    import duckdb

    copy = tmp_path / "pinnable.duckdb"
    shutil.copy(insights_db, copy)
    with duckdb.connect(str(copy)) as con:
        con.execute(
            "UPDATE marts.dim_author SET orcid_id = ?, openalex_author_id = 'A5000315992' "
            "WHERE author_key = 'a1'",
            [ORCID],
        )
    return copy


def pin_file(roster: Path, *rows: str) -> None:
    (roster.parent / "staff_author_overrides.csv").write_text(
        "Staff ID,Author ID\n" + "".join(rows), encoding="utf-8"
    )


def test_a_pinned_author_appears_under_the_staff_member_with_a_different_name(
    pinnable_db: Path, tmp_path: Path
) -> None:
    roster = roster_with(tmp_path, "5,KAKANDA,BOB,,Dr,LECTURER,Law\n")
    pin_file(roster, f"5,{ORCID}\n")  # Alice Mwansa's ORCID: the names do not match at all
    client = client_for(pinnable_db, roster)
    row = client.get("/api/members").json()["rows"][0]
    assert (row["title"], row["name"], row["school"]) == ("Dr", "Bob Kakanda", "School of Law")
    assert row["publications"] == 4 and row["orcid"] == ORCID
    credit = client.get("/api/organisation").json()["school_credit"]
    assert credit["schools"][0]["school"] == "School of Law"  # the pin also credits the school
    assert "5," not in str(row) and "Alice" not in str(row)


def test_a_pin_wins_over_the_name_match(pinnable_db: Path, tmp_path: Path) -> None:
    roster = roster_with(tmp_path, ALICE, "5,KAKANDA,BOB,,Dr,LECTURER,Law\n")
    pin_file(roster, f"5,{ORCID}\n")
    names = [r["name"] for r in client_for(pinnable_db, roster).get("/api/members").json()["rows"]]
    assert names == ["Bob Kakanda"]  # Alice Mwansa is pinned away from her namesake


def test_an_unknown_staff_id_or_author_in_the_file_changes_nothing(
    pinnable_db: Path, tmp_path: Path
) -> None:
    roster = roster_with(tmp_path, ALICE)
    pin_file(roster, f"999,{ORCID}\n", "1001,A123\n")
    names = [r["name"] for r in client_for(pinnable_db, roster).get("/api/members").json()["rows"]]
    assert names == ["Alice Mwansa"]


def test_editing_the_overrides_file_is_picked_up(pinnable_db: Path, tmp_path: Path) -> None:
    roster = roster_with(tmp_path, ALICE, "5,KAKANDA,BOB,,Dr,LECTURER,Law\n")
    client = client_for(pinnable_db, roster)
    assert [r["name"] for r in client.get("/api/members").json()["rows"]] == ["Alice Mwansa"]
    pin_file(roster, f"5,{ORCID}\n")
    assert [r["name"] for r in client.get("/api/members").json()["rows"]] == ["Bob Kakanda"]


def test_the_near_miss_script_suggests_a_repeated_given_name(tmp_path: Path) -> None:
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "staff_near_misses", Path(__file__).parent.parent / "scripts" / "staff_near_misses.py"
    )
    assert spec and spec.loader
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)

    roster = load_roster(
        roster_with(tmp_path, "9,KAKANDA,MUKELABAI ALFRED,,Dr,LECTURER,Education\n")
    )
    assert roster is not None
    member = roster.members[0]
    authors = [
        ("k1", "Mukelabai Mukelabai", frozenset({"mukelabai"}), ["mukelabai", "mukelabai"]),
        ("k2", "Mukelabai", frozenset({"mukelabai"}), ["mukelabai"]),  # one word: too vague
        ("k3", "Alfred Kakanda", frozenset({"alfred", "kakanda"}), ["alfred", "kakanda"]),
        ("k4", "Bob Smith", frozenset({"bob", "smith"}), ["bob", "smith"]),
    ]
    assert [key for key, _ in script.candidates(member, authors)] == ["k1", "k3"]
