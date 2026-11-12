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


def open_publications(monkeypatch: pytest.MonkeyPatch, db: Path) -> AppTest:
    app = run_app(monkeypatch, db)
    app.switch_page("pages/publications.py").run()
    return app


def test_publications_page_lists_every_publication(
    monkeypatch: pytest.MonkeyPatch, mart_db: Path
) -> None:
    app = open_publications(monkeypatch, mart_db)
    assert not app.exception
    assert "Showing 1 to 5 of 5 publications" in text_of(app.caption)
    assert len(app.dataframe[0].value) == 5


def test_publications_filters_and_global_year_filter_combine(
    monkeypatch: pytest.MonkeyPatch, mart_db: Path
) -> None:
    app = open_publications(monkeypatch, mart_db)
    app.multiselect[0].set_value(["Article"]).run()  # type
    assert "of 4 publications" in text_of(app.caption)
    app.session_state["year_range"] = (2020, 2022)  # what the global year filter stores
    app.run()
    assert "of 3 publications" in text_of(app.caption)  # global year filter still applies


def test_publications_search_and_empty_result(
    monkeypatch: pytest.MonkeyPatch, mart_db: Path
) -> None:
    app = open_publications(monkeypatch, mart_db)
    app.text_input[0].set_value("malaria").run()
    assert "of 1 publications" in text_of(app.caption)
    app.text_input[0].set_value("no such title").run()
    assert not app.exception
    assert "No publications match" in text_of(app.info)


def open_coverage(monkeypatch: pytest.MonkeyPatch, db: Path) -> AppTest:
    app = run_app(monkeypatch, db)
    app.switch_page("pages/coverage.py").run()
    return app


def test_coverage_page_shows_every_source_and_the_three_gaps(
    monkeypatch: pytest.MonkeyPatch, mart_db: Path
) -> None:
    app = open_coverage(monkeypatch, mart_db)
    assert not app.exception
    metrics = [(m.label, m.value) for m in app.metric]
    # one card per source, then one count per comparison tab
    assert metrics[:4] == [
        ("ORCID", "1"),
        ("OpenAlex", "4"),
        ("UNZA Institutional Repository (IRIMS)", "2"),
        ("UNZA journals (OJS)", "1"),
    ]
    assert [value for label, value in metrics[4:]] == ["3", "1", "1", "0"]
    assert [t.label for t in app.tabs] == [
        "In OpenAlex, not in the repository",
        "OJS articles not in OpenAlex",
        "In the repository, not in OpenAlex",
        "Compare any two sources",
    ]
    assert len(app.dataframe[0].value) == 3  # In OpenAlex, not in the repository


def test_coverage_page_follows_the_global_year_filter(
    monkeypatch: pytest.MonkeyPatch, mart_db: Path
) -> None:
    app = open_coverage(monkeypatch, mart_db)
    app.session_state["year_range"] = (2020, 2020)
    app.run()
    assert not app.exception
    assert [m.value for m in app.metric][4:] == ["1", "0", "0", "0"]
    assert "None in the selected years." in text_of(app.info)


def test_any_two_sources_can_be_compared(monkeypatch: pytest.MonkeyPatch, mart_db: Path) -> None:
    app = open_coverage(monkeypatch, mart_db)
    app.selectbox(key="compare-in").set_value("dspace_oai")
    app.selectbox(key="compare-not-in").set_value("orcid").run()
    assert not app.exception
    assert [m.value for m in app.metric][-1] == "1"
    assert "ORCID holds only what researchers add" in text_of(app.caption)
    app.selectbox(key="compare-not-in").set_value("dspace_oai").run()
    assert "Choose two different sources." in text_of(app.info)
