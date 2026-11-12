"""Tests for the Source coverage queries, against the tiny hand-built mart in conftest.py.

In that mart: p1 (2019), p3 (2020) and p4 (2022) are in OpenAlex only; p2 (2020) is in
OpenAlex, the repository and ORCID; p5 (2022) is in OJS and the repository.
"""

from pathlib import Path

import duckdb
import pytest

from ihub.mart import coverage as c
from ihub.mart.research import MartUnavailableError, YearRange, publications_to_csv

ALL = YearRange(2019, 2022)


def titles(db: Path, in_source: str, missing_from: str, years: YearRange = ALL) -> list[str]:
    return [r.title for r in c.missing_publications(db, in_source, missing_from, years)]


def test_source_systems_are_listed_by_name(mart_db: Path) -> None:
    assert [s.code for s in c.source_systems(mart_db)] == [
        "orcid",
        "openalex",
        "dspace_oai",
        "ojs",
    ]


def test_source_totals_count_publications_with_a_record_in_each_source(mart_db: Path) -> None:
    totals = {t.source.code: t.publications for t in c.source_totals(mart_db, ALL)}
    assert totals == {"openalex": 4, "orcid": 1, "dspace_oai": 2, "ojs": 1}


def test_source_totals_follow_the_years_and_keep_empty_sources(mart_db: Path) -> None:
    totals = {
        t.source.code: t.publications for t in c.source_totals(mart_db, YearRange(2019, 2019))
    }
    assert totals == {"openalex": 1, "orcid": 0, "dspace_oai": 0, "ojs": 0}


@pytest.mark.parametrize(
    ("gap", "expected"),
    [
        # In OpenAlex, not in the repository: newest, then most cited first.
        (c.COVERAGE_GAPS[0], ["100% sure_thing", '=HYPERLINK("x")', "Malaria in Zambia"]),
        (c.COVERAGE_GAPS[1], ["Zambian soils"]),  # OJS articles not in OpenAlex
        (c.COVERAGE_GAPS[2], ["Zambian soils"]),  # in the repository, not in OpenAlex
    ],
)
def test_the_three_gaps_the_library_asked_for(
    mart_db: Path, gap: c.CoverageGap, expected: list[str]
) -> None:
    assert titles(mart_db, gap.in_source, gap.missing_from) == expected
    assert c.count_missing(mart_db, gap.in_source, gap.missing_from, ALL) == len(expected)


def test_the_presets_are_the_comparisons_in_issue_22() -> None:
    assert [(g.in_source, g.missing_from) for g in c.COVERAGE_GAPS] == [
        ("openalex", "dspace_oai"),
        ("ojs", "openalex"),
        ("dspace_oai", "openalex"),
    ]


def test_gaps_follow_the_global_year_filter(mart_db: Path) -> None:
    only_2020 = YearRange(2020, 2020)
    assert titles(mart_db, "openalex", "dspace_oai", only_2020) == ['=HYPERLINK("x")']
    assert c.count_missing(mart_db, "openalex", "dspace_oai", only_2020) == 1
    assert c.count_missing(mart_db, "ojs", "openalex", YearRange(2019, 2021)) == 0


def test_any_pair_of_sources_can_be_compared(mart_db: Path) -> None:
    assert titles(mart_db, "orcid", "dspace_oai") == []  # p2 is in both
    assert titles(mart_db, "dspace_oai", "orcid") == ["Zambian soils"]


def test_the_record_link_is_the_record_in_the_source_it_is_in(mart_db: Path) -> None:
    from_ojs = c.missing_publications(mart_db, "ojs", "openalex", ALL)[0]
    from_repository = c.missing_publications(mart_db, "dspace_oai", "openalex", ALL)[0]
    assert from_ojs.record_url == "https://journals.unza.zm/index.php/x/article/view/5"
    assert from_repository.record_url == "https://rims.unza.ac.zm/handle/1/5"
    assert from_ojs.sources == "UNZA Institutional Repository (IRIMS), UNZA journals (OJS)"
    assert from_ojs.doi_url is None and from_ojs.doi == "10.1/e"


def test_paging_and_full_export(mart_db: Path) -> None:
    page = c.missing_publications(mart_db, "openalex", "dspace_oai", ALL, limit=1, offset=1)
    assert [r.title for r in page] == ['=HYPERLINK("x")']
    every = c.missing_publications(mart_db, "openalex", "dspace_oai", ALL, limit=None)
    header, *lines = publications_to_csv(every).strip().splitlines()
    assert header.startswith("Title,Year,Type,Venue")
    assert len(lines) == 3
    assert any(line.startswith("\"'=HYPERLINK") for line in lines)  # formula neutralised


@pytest.mark.parametrize(
    ("in_source", "missing_from", "message"),
    [
        ("openalex", "openalex", "two different sources"),
        ("openalex", "scopus", "Unknown source"),
        ("nope", "ojs", "Unknown source"),
    ],
)
def test_bad_comparisons_are_refused(
    mart_db: Path, in_source: str, missing_from: str, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        c.count_missing(mart_db, in_source, missing_from, ALL)
    with pytest.raises(ValueError, match=message):
        c.missing_publications(mart_db, in_source, missing_from, ALL)


def test_negative_paging_is_refused(mart_db: Path) -> None:
    with pytest.raises(ValueError):
        c.missing_publications(mart_db, "openalex", "ojs", ALL, limit=-1)
    with pytest.raises(ValueError):
        c.missing_publications(mart_db, "openalex", "ojs", ALL, offset=-1)


def test_a_missing_mart_is_reported(tmp_path: Path) -> None:
    empty = tmp_path / "empty.duckdb"
    duckdb.connect(str(empty)).close()
    with pytest.raises(MartUnavailableError):
        c.source_systems(empty)
    with pytest.raises(MartUnavailableError):
        c.source_totals(tmp_path / "missing.duckdb", ALL)
