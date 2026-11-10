"""Tests for the stg_openalex__works dbt model, built from the recorded OpenAlex sample."""

from pathlib import Path

import pytest

from tests.dbt_helpers import build_warehouse, make_work, query, sample_works


@pytest.fixture(scope="module")
def built_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """Load the sample into raw_openalex and run dbt build for the staging model once."""
    db = tmp_path_factory.mktemp("dbt") / "test.duckdb"
    return build_warehouse(db, sample_works(), select="stg_openalex__works")


def read_works(db: Path) -> list[dict]:
    return query(db, "SELECT * FROM staging.stg_openalex__works ORDER BY openalex_id")


def test_one_row_per_work_and_dbt_tests_pass(built_db: Path) -> None:
    assert [w["openalex_id"] for w in read_works(built_db)] == ["W1617145133", "W2548000951"]


def test_columns_are_cleaned_and_typed(built_db: Path) -> None:
    work = read_works(built_db)[1]
    assert work["doi"] == "10.1016/s0140-6736(16)31392-7"
    assert work["year"] == 2016
    assert work["type"] == "review"
    assert work["venue_id"] == "S49861241"
    assert work["venue_name"] == "The Lancet"
    assert work["is_oa"] is True
    assert work["oa_status"] == "green"
    assert work["cited_by_count"] == 13519
    assert work["n_authors"] == 21


def test_a_work_delivered_twice_becomes_one_row_and_the_latest_delivery_wins(
    tmp_path: Path,
) -> None:
    older = make_work("W1", title="Old title", cited_by_count=1)
    newer = make_work("W1", title="New title", cited_by_count=9)
    other = make_work("W2", title="Another work")
    db = build_warehouse(
        tmp_path / "dup.duckdb", [older, other, newer], select="stg_openalex__works"
    )

    rows = query(db, "SELECT openalex_id, title, cited_by_count FROM staging.stg_openalex__works")
    assert sorted((r["openalex_id"], r["title"], r["cited_by_count"]) for r in rows) == [
        ("W1", "New title", 9),
        ("W2", "Another work", 0),
    ]


def test_identical_deliveries_collapse_to_one_row(tmp_path: Path) -> None:
    work = make_work("W1")
    db = build_warehouse(tmp_path / "same.duckdb", [work, work, work], select="stg_openalex__works")
    assert query(db, "SELECT count(*) AS n FROM staging.stg_openalex__works") == [{"n": 1}]


def test_is_xpac_flag_is_read_and_defaults_to_false(tmp_path: Path) -> None:
    xpac = make_work("W1")
    xpac["is_xpac"] = True
    plain = make_work("W2")
    plain.pop("is_xpac", None)
    db = build_warehouse(tmp_path / "xpac.duckdb", [xpac, plain], select="stg_openalex__works")
    rows = query(db, "SELECT openalex_id, is_xpac FROM staging.stg_openalex__works")
    assert {r["openalex_id"]: r["is_xpac"] for r in rows} == {"W1": True, "W2": False}
