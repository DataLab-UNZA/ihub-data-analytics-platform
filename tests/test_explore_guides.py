"""The ready-made Explore charts: every guide runs, the new options work, and the school
datasets agree with the Organisation counts (invented names only)."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ihub.api.app import create_app
from ihub.api.explore_routes import QueryIn
from ihub.api.units import UnitScope
from ihub.mart import explore, explore_guides
from ihub.mart.explore import Filter, QuerySpec, run_query
from ihub.workspace.service import VIZ_TYPES

HEADER = "Staff ID,Surname,First Name,Second Name,Title,Occupation,School\n"


@pytest.fixture
def roster(tmp_path: Path) -> Path:
    path = tmp_path / "roster.csv"
    path.write_text(HEADER + "1001,MWANSA,ALICE,,Dr,LECTURER,Medicine\n", encoding="utf-8")
    return path


@pytest.fixture
def scope(insights_db: Path, roster: Path) -> UnitScope:
    return UnitScope(lambda: insights_db, lambda: roster)


@pytest.fixture
def department_scope(insights_db: Path) -> UnitScope:
    """No roster file: the school datasets fall back to department evidence."""
    return UnitScope(lambda: insights_db, lambda: None)


def spec_of(guide_id: str) -> QuerySpec:
    return QueryIn.model_validate(explore_guides.GUIDES_BY_ID[guide_id].spec).spec()


# --- the catalogue -----------------------------------------------------------------------------


def test_every_guide_runs_with_and_without_a_roster(
    insights_db: Path, scope: UnitScope, department_scope: UnitScope
) -> None:
    for provider in (scope.chart_tables, department_scope.chart_tables):
        for guide in explore_guides.GUIDES:
            result = run_query(insights_db, spec_of(guide.id), provider)
            assert result.columns, guide.id


def test_the_catalogue_is_well_formed() -> None:
    ids = [guide.id for guide in explore_guides.GUIDES]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 30
    themes = {guide.theme for guide in explore_guides.GUIDES}
    assert themes == {theme.key for theme in explore_guides.THEMES}
    for guide in explore_guides.GUIDES:
        assert guide.viz in VIZ_TYPES, guide.id  # so it can be saved to a dashboard
        assert guide.question.endswith("?") and guide.how_to_read, guide.id
        assert "SELECT" not in str(guide.spec).upper(), "guides hold no SQL"


def test_a_guide_offers_only_filters_its_data_can_apply() -> None:
    by_id = explore_guides.GUIDES_BY_ID
    assert explore_guides.simple_filters(by_id["output-per-year"]) == ["years", "type"]
    assert explore_guides.simple_filters(by_id["type-mix"]) == ["years"]  # already split by type
    assert explore_guides.simple_filters(by_id["productivity"]) == []  # no year, no type
    assert "school" not in explore_guides.simple_filters(by_id["output-by-school"])


def test_the_guides_api_returns_themes(insights_db: Path) -> None:
    client = TestClient(create_app(lambda: insights_db, require_sign_in=False))
    themes = client.get("/api/explore/guides").json()
    assert [t["key"] for t in themes][:2] == ["growth", "impact"]
    assert themes[-1]["admin_only"] is True
    first = themes[0]["guides"][0]
    wanted = {"id", "title", "question", "how_to_read", "viz", "spec", "options", "filters"}
    assert wanted <= set(first)


def test_a_guide_runs_through_the_api_and_csv(insights_db: Path, roster: Path) -> None:
    client = TestClient(
        create_app(lambda: insights_db, require_sign_in=False, staff_roster_path=lambda: roster)
    )
    for guide in explore_guides.GUIDES:
        response = client.post("/api/explore/query", json=guide.spec)
        assert response.status_code == 200, (guide.id, response.text)
    csv = client.post(
        "/api/explore/query.csv", json=explore_guides.GUIDES_BY_ID["oa-by-school"].spec
    )
    assert csv.status_code == 200 and "School" in csv.text


# --- transforms and bands ------------------------------------------------------------------------


def with_transform(base: QuerySpec, transform: str) -> QuerySpec:
    return QuerySpec(**{**base.__dict__, "transform": transform})


def test_rolling_average_and_year_on_year_change(insights_db: Path) -> None:
    base = QuerySpec("publications", ["count"], ["year"], order_by="c0", order_desc=False)
    assert run_query(insights_db, base).rows == [[2019, 1], [2020, 2], [2022, 2]]
    yoy = run_query(insights_db, with_transform(base, "yoy"))
    assert [c.label for c in yoy.columns] == ["Year", "Change on previous year"]
    assert yoy.columns[1].format == "percent"
    assert yoy.rows == [[2019, None], [2020, 1.0], [2022, None]]  # 2021 is missing: no change
    rolling = run_query(insights_db, with_transform(base, "rolling3"))
    assert [c.label for c in rolling.columns][-1] == "3-year average"
    assert all(row[2] is None for row in rolling.rows)  # no three consecutive years


def test_a_cumulative_share_covers_every_group_before_the_limit(insights_db: Path) -> None:
    base = QuerySpec("publications", ["count"], ["publication_type"])
    result = run_query(insights_db, with_transform(base, "cumulative_share"))
    assert result.rows == [["Article", 4, 0.8], ["Review", 1, 1.0]]
    one = QuerySpec(**{**with_transform(base, "cumulative_share").__dict__, "row_limit": 1})
    limited = run_query(insights_db, one)
    assert limited.rows == [["Article", 4, 0.8]] and limited.truncated is True


def test_a_transform_needs_exactly_one_group_by(insights_db: Path) -> None:
    two = QuerySpec("publications", ["count"], ["year", "publication_type"])
    with pytest.raises(ValueError, match="one group-by"):
        run_query(insights_db, with_transform(two, "yoy"))
    one = QuerySpec("publications", ["count"], ["year"])
    with pytest.raises(ValueError, match="Unknown transform"):
        run_query(insights_db, with_transform(one, "nope"))


def test_bands_are_ordered_by_size_not_alphabetically(insights_db: Path) -> None:
    result = run_query(
        insights_db,
        QuerySpec("publications", ["count"], ["citation_band"], order_by="c0", order_desc=False),
    )
    assert [row[0] for row in result.rows] == ["0", "1", "5–9", "10–19", "20–49"]


def test_a_dataset_without_a_year_refuses_a_year_range(insights_db: Path) -> None:
    ok = QuerySpec("researcher_output", ["researchers"], ["publications_band"])
    assert run_query(insights_db, ok).rows  # runs without years
    with pytest.raises(ValueError, match="no year"):
        run_query(insights_db, QuerySpec(**{**ok.__dict__, "year_from": 2020}))


def test_metadata_completeness_without_a_group_by(insights_db: Path) -> None:
    result = run_query(insights_db, spec_of("metadata-completeness"))
    assert len(result.rows) == 1 and len(result.rows[0]) == 4
    assert result.rows[0][0] == pytest.approx(3 / 5)  # DOIs on p1, p2, p5


# --- the school datasets -------------------------------------------------------------------------


def test_school_charts_use_the_same_credit_as_the_organisation_screen(
    insights_db: Path, scope: UnitScope, roster: Path
) -> None:
    result = run_query(
        insights_db,
        QuerySpec("unit_publications", ["publications"], ["school"]),
        scope.chart_tables,
    )
    assert result.rows == [["School of Medicine", 4]]
    client = TestClient(
        create_app(lambda: insights_db, require_sign_in=False, staff_roster_path=lambda: roster)
    )
    credit = client.get("/api/organisation").json()["school_credit"]["schools"][0]
    assert credit["roster_publications"] == 4


def test_school_charts_respect_the_year_and_the_school_filter(
    insights_db: Path, scope: UnitScope
) -> None:
    only_2020 = QuerySpec(
        "unit_publications", ["publications"], ["school"], year_from=2020, year_to=2020
    )
    assert run_query(insights_db, only_2020, scope.chart_tables).rows == [["School of Medicine", 2]]
    other = QuerySpec(
        "unit_publications",
        ["publications"],
        ["year"],
        filters=[Filter("school", "==", "School of Law")],
    )
    assert run_query(insights_db, other, scope.chart_tables).rows == []


def test_without_a_roster_school_charts_use_department_evidence(
    insights_db: Path, department_scope: UnitScope
) -> None:
    result = run_query(
        insights_db,
        QuerySpec("unit_publications", ["publications"], ["school"]),
        department_scope.chart_tables,
    )
    found = {row[0]: row[1] for row in result.rows}
    assert found == {"School of Medicine": 2, "School of Natural and Applied Sciences": 1}


def test_author_charts_count_roles_and_orcid_without_naming_anyone(
    insights_db: Path, scope: UnitScope
) -> None:
    roles = run_query(
        insights_db,
        QuerySpec("unit_authorships", ["authorships"], ["school", "author_role"]),
        scope.chart_tables,
    )
    assert {row[1] for row in roles.rows} <= {
        "First author",
        "Corresponding author",
        "Other author",
    }
    assert all(len(row) == 3 for row in roles.rows)
    orcid = run_query(
        insights_db,
        QuerySpec("unit_researchers", ["researchers", "orcid_share"], ["school"]),
        scope.chart_tables,
    )
    assert orcid.rows == [["School of Medicine", 1, 1.0]]  # Alice has an ORCID iD in the fixture


def test_a_school_dataset_is_refused_without_its_tables(insights_db: Path) -> None:
    with pytest.raises(ValueError, match="not available"):
        run_query(insights_db, QuerySpec("unit_publications", ["publications"], ["school"]))


def test_filter_values_for_a_school_come_from_the_tables(
    insights_db: Path, scope: UnitScope
) -> None:
    values = explore.column_values(
        insights_db, "unit_publications", "school", tables=scope.chart_tables
    )
    assert values == ["School of Medicine"]


# --- saving a guide -------------------------------------------------------------------------


def test_every_guide_can_be_saved_as_a_chart(tmp_path: Path) -> None:
    """A guide's chart type, options and query are all accepted by the saved-chart rules."""
    from ihub.workspace.service import WorkspaceService
    from ihub.workspace.sqlite_store import SqliteWorkspaceStore
    from tests.auth_helpers import ADMIN, make_harness

    h = make_harness(tmp_path)
    admin = h.service.principal(h.sign_in_by_email(ADMIN).access_token)
    ws = WorkspaceService(SqliteWorkspaceStore(tmp_path / "workspace.sqlite"))
    for guide in explore_guides.GUIDES:
        chart = ws.create_chart(
            admin, name=guide.title, viz_type=guide.viz, params=guide.spec, options=guide.options
        )
        assert chart.viz_type == guide.viz and chart.dataset == guide.spec["dataset"]
