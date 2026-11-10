"""Tests for the research mart query functions, against a tiny hand-built DuckDB file."""

from pathlib import Path

import duckdb
import pytest

from ihub.mart import research as r
from ihub.mart.research import PublicationFilter, YearRange

ALL = YearRange(2019, 2022)


def test_year_range_validation_and_previous_period() -> None:
    assert YearRange(2020, 2022).previous_period() == YearRange(2017, 2019)
    with pytest.raises(ValueError):
        YearRange(2022, 2020)


def test_availability(mart_db: Path, tmp_path: Path) -> None:
    assert r.is_available(mart_db)
    assert not r.is_available(tmp_path / "missing.duckdb")
    empty = tmp_path / "empty.duckdb"
    duckdb.connect(str(empty)).close()
    assert not r.is_available(empty)
    with pytest.raises(r.MartUnavailableError):
        r.headline_counts(empty, ALL)


def test_year_bounds(mart_db: Path) -> None:
    assert r.year_bounds(mart_db) == ALL


def test_headline_counts(mart_db: Path) -> None:
    counts = r.headline_counts(mart_db, ALL)
    assert counts == r.HeadlineCounts(5, 3, 36, 2)  # unknown venue is not counted
    assert counts.open_access_share == pytest.approx(0.6)


def test_headline_counts_respect_the_year_range_and_empty_periods(mart_db: Path) -> None:
    assert r.headline_counts(mart_db, YearRange(2020, 2020)).publications == 2
    empty = r.headline_counts(mart_db, YearRange(1990, 1991))
    assert empty == r.HeadlineCounts(0, 0, 0, 0)
    assert empty.open_access_share == 0.0


def test_publications_per_year_includes_years_with_none(mart_db: Path) -> None:
    result = r.publications_per_year(mart_db, ALL)
    assert [(y.year, y.publications) for y in result] == [
        (2019, 1),
        (2020, 2),
        (2021, 0),
        (2022, 2),
    ]


def test_oa_share_per_year(mart_db: Path) -> None:
    by_year = {y.year: y for y in r.oa_share_per_year(mart_db, ALL)}
    assert by_year[2020].open_access_share == pytest.approx(0.5)
    assert by_year[2021].open_access_share == 0.0  # no publications, no division by zero


def test_top_venues_orders_by_publications_and_skips_unknown(mart_db: Path) -> None:
    venues = r.top_venues(mart_db, ALL, limit=10)
    assert [(v.venue, v.publications, v.citations) for v in venues] == [
        ("The Lancet", 2, 30),
        ("Medical Journal of Zambia", 2, 1),
    ]
    assert len(r.top_venues(mart_db, ALL, limit=1)) == 1
    with pytest.raises(ValueError):
        r.top_venues(mart_db, ALL, limit=0)


def test_filter_options(mart_db: Path) -> None:
    options = r.filter_options(mart_db)
    assert options.types == ("Article", "Review")
    assert options.oa_statuses == ("closed", "diamond", "gold", "green")
    assert options.venues == ("Medical Journal of Zambia", "The Lancet")  # ties by name
    assert options.sources == ("OpenAlex", "Repository", "OJS")


def titles(db: Path, **kwargs: object) -> list[str]:
    return [p.title for p in r.publications(db, PublicationFilter(**kwargs), limit=None)]


def test_publications_are_sorted_newest_then_most_cited(mart_db: Path) -> None:
    assert titles(mart_db) == [
        "100% sure_thing",
        "Zambian soils",
        "Maternal health",
        '=HYPERLINK("x")',
        "Malaria in Zambia",
    ]


@pytest.mark.parametrize(
    ("kwargs", "expected"),
    [
        ({"years": YearRange(2020, 2020)}, {"Maternal health", '=HYPERLINK("x")'}),
        ({"types": ["Review"]}, {"Maternal health"}),
        ({"oa_statuses": ["gold", "diamond"]}, {"Malaria in Zambia", "Zambian soils"}),
        ({"venues": ["The Lancet"]}, {"Malaria in Zambia", "Maternal health"}),
        ({"sources": ["OJS"]}, {"Zambian soils"}),
        (
            {"sources": ["OJS", "OpenAlex"]},
            {
                "Malaria in Zambia",
                "Maternal health",
                '=HYPERLINK("x")',
                "100% sure_thing",
                "Zambian soils",
            },
        ),
        ({"search": "MALARIA"}, {"Malaria in Zambia"}),
        ({"search": "10.1/b"}, {"Maternal health"}),
        ({"types": ["Article"], "oa_statuses": ["gold"]}, {"Malaria in Zambia"}),
    ],
)
def test_publication_filters(mart_db: Path, kwargs: dict, expected: set[str]) -> None:
    assert set(titles(mart_db, **kwargs)) == expected
    assert r.count_publications(mart_db, PublicationFilter(**kwargs)) == len(expected)


def test_search_treats_wildcards_as_text(mart_db: Path) -> None:
    assert titles(mart_db, search="100%") == ["100% sure_thing"]
    assert titles(mart_db, search="%") == ["100% sure_thing"]
    assert titles(mart_db, search="e_t") == ["100% sure_thing"]
    assert titles(mart_db, search="' OR 1=1 --") == []


def test_unknown_source_is_rejected(mart_db: Path) -> None:
    with pytest.raises(ValueError):
        r.publications(mart_db, PublicationFilter(sources=["Nope"]))


def test_paging_and_validation(mart_db: Path) -> None:
    page = r.publications(mart_db, PublicationFilter(), limit=2, offset=1)
    assert [p.title for p in page] == ["Zambian soils", "Maternal health"]
    with pytest.raises(ValueError):
        r.publications(mart_db, PublicationFilter(), limit=-1)
    with pytest.raises(ValueError):
        r.publications(mart_db, PublicationFilter(), offset=-1)


def test_row_contents(mart_db: Path) -> None:
    row = r.publications(mart_db, PublicationFilter(search="Malaria"))[0]
    assert row == r.PublicationRow(
        title="Malaria in Zambia",
        year=2019,
        type="Article",
        venue="The Lancet",
        oa_status="gold",
        cited_by_count=10,
        n_authors=3,
        sources="OpenAlex",
        doi="10.1/a",
        doi_url="https://doi.org/10.1/a",
        record_url="https://openalex.org/W1",
    )


def test_csv_export_has_header_and_neutralises_formulas(mart_db: Path) -> None:
    text = r.publications_to_csv(r.publications(mart_db, PublicationFilter(search="HYPERLINK")))
    header, line = text.strip().splitlines()
    assert header.startswith("Title,Year,Type,Venue")
    assert line.startswith('"\'=HYPERLINK(""x"")"')
