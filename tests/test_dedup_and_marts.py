"""De-duplication and research-mart tests, built with dbt from synthetic OpenAlex works."""

from pathlib import Path

import pytest

from tests.dbt_helpers import build_warehouse, make_work, query

WORKS = [
    # Same DOI written three ways: one publication, three source records.
    make_work(
        "W1",
        doi="https://doi.org/10.1000/ABC",
        title="Malaria in Zambia",
        year=2019,
        cited_by_count=5,
        is_oa=False,
        oa_status="closed",
    ),
    make_work(
        "W2",
        doi="https://dx.doi.org/10.1000/abc",
        title="Malaria in Zambia.",
        year=2019,
        cited_by_count=9,
        is_oa=True,
        oa_status="gold",
    ),
    make_work("W3", doi="10.1000/abc", title="Malaria in Zambia", year=2019),
    # No DOI, same title + year as a single-DOI publication: joins it.
    make_work("W4", doi=None, title="MALARIA IN ZAMBIA!", year=2019),
    # No DOI, same title but another year: a different publication.
    make_work("W5", doi=None, title="Malaria in Zambia", year=2021),
    # Two DOI publications sharing a title + year: a DOI-less twin must not guess between them.
    make_work("W6", doi="10.2000/one", title="Editorial", year=2020),
    make_work("W7", doi="10.2000/two", title="Editorial", year=2020),
    make_work("W8", doi=None, title="Editorial", year=2020),
    # No DOI and no title: stays on its own.
    make_work(
        "W9",
        doi=None,
        title=None,
        year=2022,
        venue_id=None,
        venue_name=None,
        work_type="book-chapter",
    ),
]


@pytest.fixture(scope="module")
def db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_warehouse(tmp_path_factory.mktemp("marts") / "test.duckdb", WORKS)


def keys_of(db: Path, *record_ids: str) -> set[str]:
    ids = ", ".join(f"'{r}'" for r in record_ids)
    rows = query(
        db,
        "select distinct publication_key from intermediate.int_publications__source_records "
        f"where source_record_id in ({ids})",
    )
    return {r["publication_key"] for r in rows}


def test_same_doi_in_any_spelling_is_one_publication(db: Path) -> None:
    assert len(keys_of(db, "W1", "W2", "W3")) == 1


def test_record_without_doi_joins_the_single_doi_with_the_same_title_and_year(db: Path) -> None:
    assert keys_of(db, "W4") == keys_of(db, "W1")
    rule = query(
        db,
        "select match_rule from intermediate.int_publications__source_records "
        "where source_record_id = 'W4'",
    )
    assert rule == [{"match_rule": "title_year_to_doi"}]


def test_a_different_year_is_a_different_publication(db: Path) -> None:
    assert keys_of(db, "W5").isdisjoint(keys_of(db, "W1"))


def test_a_record_is_not_attached_when_the_title_points_to_two_dois(db: Path) -> None:
    w8 = keys_of(db, "W8")
    assert w8.isdisjoint(keys_of(db, "W6")) and w8.isdisjoint(keys_of(db, "W7"))
    assert keys_of(db, "W6").isdisjoint(keys_of(db, "W7"))


def test_every_source_record_is_kept_and_linked(db: Path) -> None:
    total = query(db, "select count(*) as n from intermediate.int_publications__source_records")
    assert total == [{"n": len(WORKS)}]


def test_one_row_per_publication_with_merged_measures(db: Path) -> None:
    rows = query(
        db,
        "select * from intermediate.int_publications__deduplicated where doi = '10.1000/abc'",
    )
    assert len(rows) == 1
    row = rows[0]
    assert row["n_source_records"] == 4  # W1, W2, W3 and W4
    assert row["is_oa"] is True  # any source says open access
    assert row["oa_status"] == "gold"  # consistent with is_oa
    assert row["cited_by_count"] == 9
    assert row["in_openalex"] is True
    assert row["in_repository"] is False and row["in_ojs"] is False


def test_publication_count_after_deduplication(db: Path) -> None:
    # abc, malaria-2021, one, two, editorial-no-doi, untitled
    assert query(db, "select count(*) as n from marts.fact_publication") == [{"n": 6}]


def test_fact_rows_join_to_every_dimension(db: Path) -> None:
    rows = query(
        db,
        """
        select count(*) as n
        from marts.fact_publication f
        join marts.dim_publication p using (publication_key)
        join marts.dim_venue v using (venue_key)
        join marts.dim_year y on y.year_key = f.year_key
        join marts.dim_publication_type t using (type_key)
        """,
    )
    assert rows == [{"n": 6}]


def test_unknown_venue_and_type_labels(db: Path) -> None:
    rows = query(
        db,
        """
        select v.venue_name, t.type_label
        from marts.fact_publication f
        join marts.dim_venue v using (venue_key)
        join marts.dim_publication_type t using (type_key)
        join marts.dim_publication p using (publication_key)
        where p.title = 'Untitled'
        """,
    )
    assert rows == [{"venue_name": "Unknown venue", "type_label": "Book chapter"}]


def test_dim_year_has_no_gaps(db: Path) -> None:
    years = [r["year"] for r in query(db, "select year from marts.dim_year order by year")]
    assert years == [2019, 2020, 2021, 2022]
