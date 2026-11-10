"""Tests for the app's pure helpers: number formatting and charts."""

import pytest

from ihub.app import charts, formatting
from ihub.mart.research import YearCount, YearOpenAccess


def test_format_count_and_share() -> None:
    assert formatting.format_count(1234567) == "1,234,567"
    assert formatting.format_share(0.6249) == "62.5%"
    assert formatting.format_share(0) == "0.0%"


@pytest.mark.parametrize(
    ("current", "previous", "expected"),
    [(120, 100, "+20.0%"), (80, 100, "-20.0%"), (100, 100, "+0.0%"), (5, 0, None)],
)
def test_percent_change(current: int, previous: int, expected: str | None) -> None:
    assert formatting.percent_change(current, previous) == expected


def test_points_change() -> None:
    assert formatting.points_change(0.5, 0.25) == "+25.0 pp"
    assert formatting.points_change(0.25, 0.5) == "-25.0 pp"


def test_publications_chart_has_one_bar_per_year() -> None:
    fig = charts.publications_per_year_chart([YearCount(2020, 3), YearCount(2021, 0)])
    assert list(fig.data[0].x) == ["2020", "2021"]
    assert list(fig.data[0].y) == [3, 0]


def test_oa_chart_is_in_percent_and_bounded() -> None:
    fig = charts.oa_share_chart([YearOpenAccess(2020, 4, 1), YearOpenAccess(2021, 0, 0)])
    assert list(fig.data[0].y) == [25.0, 0.0]
    assert tuple(fig.layout.yaxis.range) == (0, 100)
