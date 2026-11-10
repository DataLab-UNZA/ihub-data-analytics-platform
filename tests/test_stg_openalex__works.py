"""Tests for the stg_openalex__works dbt model, built from the recorded OpenAlex sample."""

from pathlib import Path

import pytest

from tests.dbt_helpers import build_warehouse, query, sample_works


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
