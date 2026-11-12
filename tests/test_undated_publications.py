"""Publications that no source dates are left out of the mart, with all their records.

Found on the first full build on real data (November 12, 2026): 218 ORCID works entered
without a date and 2 empty IRIMS items made the not-null test on the year fail, and so
every mart was skipped. The rule lives in int_publications__source_records.
"""

import copy
from pathlib import Path
from typing import Any

import pytest

from tests.dbt_helpers import build_warehouse, make_work, query
from tests.test_orcid_connector import WORKS

RESEARCHER = "0000-0001-0000-0009"
DATED = make_work("W1", doi="10.1000/dated", title="Cholera in Lusaka", year=2020)


def orcid_work(put_code: int, doi: str, title: str) -> dict[str, Any]:
    """One ORCID work group, from the recorded sample, with no publication date."""
    group = copy.deepcopy(WORKS["group"][0])
    group["external-ids"]["external-id"][0]["external-id-value"] = doi
    summary = group["work-summary"][0]
    summary["put-code"] = put_code
    summary["title"]["title"]["value"] = title
    summary["publication-date"] = None
    return group


ORCID = [
    (
        RESEARCHER,
        {
            "orcid": RESEARCHER,
            "works": {
                "group": [
                    # No date, but W1's DOI: it joins W1's dated publication and is kept.
                    orcid_work(1, "10.1000/dated", "Cholera in Lusaka"),
                    # No date and nothing to match: no source dates this publication.
                    orcid_work(2, "10.1000/undated", "A study with no date"),
                ]
            },
            "employments": {"affiliation-group": []},
        },
    )
]


@pytest.fixture(scope="module")
def db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("undated") / "test.duckdb"
    return build_warehouse(path, [DATED], extra_raw={"orcid": ORCID})


def test_a_publication_no_source_dates_is_left_out(db: Path) -> None:
    rows = query(db, "select doi from marts.dim_publication order by doi")
    assert rows == [{"doi": "10.1000/dated"}]


def test_an_undated_record_of_a_dated_publication_is_kept(db: Path) -> None:
    rows = query(
        db,
        "select source_system, source_record_id from intermediate.int_publications__source_records "
        "order by source_system",
    )
    assert rows == [
        {"source_system": "openalex", "source_record_id": "W1"},
        {"source_system": "orcid", "source_record_id": f"{RESEARCHER}:1"},
    ]


def test_no_mart_table_refers_to_the_undated_publication(db: Path) -> None:
    for table in ("fact_publication", "fact_authorship", "bridge_publication_source"):
        joined = query(
            db,
            f"select count(*) as n from marts.{table} as t "
            "join marts.dim_publication as p using (publication_key)",
        )
        assert joined == query(db, f"select count(*) as n from marts.{table}"), table
