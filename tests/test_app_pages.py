"""Smoke tests that run the real Streamlit app against a tiny mart and check it renders."""

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

HOME = str(Path(__file__).resolve().parent.parent / "src" / "ihub" / "app" / "Home.py")
FOOTER_SENTENCE = (
    "Research metadata from OpenAlex, ORCID, the UNZA Institutional Repository "
    "and UNZA journals (being added)."
)


def run_app(monkeypatch: pytest.MonkeyPatch, db: Path) -> AppTest:
    monkeypatch.setenv("IHUB_DUCKDB_PATH", str(db))
    app = AppTest.from_file(HOME, default_timeout=30)
    app.run()
    return app


def text_of(elements) -> str:
    return " ".join(e.value for e in elements)


def test_empty_state_when_there_is_no_database(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    app = run_app(monkeypatch, tmp_path / "missing.duckdb")
    assert not app.exception
    assert "No data has been published yet" in text_of(app.warning)
    assert FOOTER_SENTENCE in text_of(app.caption)


def test_overview_shows_headline_cards_for_the_whole_range(
    monkeypatch: pytest.MonkeyPatch, mart_db: Path
) -> None:
    app = run_app(monkeypatch, mart_db)
    assert not app.exception
    metrics = {m.label: m.value for m in app.metric}
    assert metrics == {
        "Publications": "5",
        "Open access share": "60.0%",
        "Citations": "36",
        "Venues": "2",
    }
    assert FOOTER_SENTENCE in text_of(app.caption)


def test_the_global_year_filter_changes_every_number(
    monkeypatch: pytest.MonkeyPatch, mart_db: Path
) -> None:
    app = run_app(monkeypatch, mart_db)
    app.sidebar.slider(key="year_range").set_value((2020, 2020)).run()
    assert not app.exception
    metrics = {m.label: m.value for m in app.metric}
    assert metrics["Publications"] == "2"
    assert metrics["Citations"] == "20"


def test_a_year_range_with_no_publications_shows_a_message(
    monkeypatch: pytest.MonkeyPatch, mart_db: Path
) -> None:
    app = run_app(monkeypatch, mart_db)
    app.sidebar.slider(key="year_range").set_value((2021, 2021)).run()
    assert not app.exception
    assert "no publications in the selected years" in text_of(app.info)


def test_change_against_the_previous_period_only_when_the_data_covers_it(
    monkeypatch: pytest.MonkeyPatch, mart_db: Path
) -> None:
    app = run_app(monkeypatch, mart_db)
    assert all(m.delta in (None, "") for m in app.metric)  # 2019 to 2022 has no earlier period

    app.sidebar.slider(key="year_range").set_value((2021, 2022)).run()
    publications = next(m for m in app.metric if m.label == "Publications")
    assert publications.value == "2"
    assert publications.delta == "-33.3%"  # 2 now against 3 in 2019 to 2020
