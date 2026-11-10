"""The shared shell of the app: page set-up, navigation, the global year filter and footer.

``Home.py`` only calls :func:`run`. To add a page, create ``pages/<name>.py`` and add one
:class:`PageSpec` to :data:`PAGES`. Pages read the global year filter with
:func:`selected_years` and call functions in ``ihub.mart``; they never contain SQL.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import streamlit as st

from ihub.app.idle import pause_when_idle
from ihub.mart import research
from ihub.mart.research import YearRange
from ihub.mart.status import last_pipeline_run
from ihub.settings import get_settings

APP_TITLE = "iHub Data Analytics Platform"
REPO_URL = "https://github.com/DataLab-UNZA/ihub-data-analytics-platform"
ROADMAP_URL = f"{REPO_URL}/blob/main/docs/ROADMAP.md"
YEAR_KEY = "year_range"


@dataclass(frozen=True)
class PageSpec:
    """One page in the sidebar. ``path`` is relative to ``Home.py``."""

    path: str
    title: str
    icon: str
    default: bool = False


#: The pages in the sidebar, in order. Add new pages here.
PAGES: tuple[PageSpec, ...] = (
    PageSpec("pages/overview.py", "Overview", ":material/dashboard:", default=True),
)


def database_path() -> Path:
    """Return the path of the DuckDB file the app reads."""
    return get_settings().ihub_duckdb_path


def selected_years() -> YearRange:
    """Return the years chosen in the global year filter (the full range before it is shown)."""
    chosen = st.session_state.get(YEAR_KEY)
    if chosen:
        return YearRange(int(chosen[0]), int(chosen[1]))
    return research.year_bounds(database_path())


def _render_year_filter(bounds: YearRange) -> None:
    """Show the one global year-range filter that every page uses."""
    st.sidebar.markdown("**Publication years**")
    if bounds.start == bounds.end:
        st.session_state[YEAR_KEY] = (bounds.start, bounds.end)
        st.sidebar.caption(f"All data is from {bounds.start}.")
        return
    current = st.session_state.get(YEAR_KEY)
    if current and not (bounds.start <= current[0] <= current[1] <= bounds.end):
        st.session_state[YEAR_KEY] = (bounds.start, bounds.end)  # data changed under the filter
    st.sidebar.slider(
        "Years",
        min_value=bounds.start,
        max_value=bounds.end,
        value=(bounds.start, bounds.end),
        key=YEAR_KEY,
        label_visibility="collapsed",
        help="Applies to every number, chart and table in the app.",
    )


def _render_data_status() -> None:
    last_run = last_pipeline_run(database_path())
    if last_run is not None:
        st.sidebar.caption(f"Data last built: {last_run:%B %-d, %Y at %H:%M} UTC")


def render_footer() -> None:
    """Show the footer: where the project lives and where the data comes from."""
    st.divider()
    st.caption(
        f"[GitHub repository]({REPO_URL}) · [Roadmap]({ROADMAP_URL})  \n"
        "Research metadata from OpenAlex, ORCID, the UNZA Institutional Repository "
        "and UNZA journals (being added)."
    )


def _render_empty_state() -> None:
    st.title(APP_TITLE)
    st.caption("Research analytics for the University of Zambia: prototype, iteration 1")
    last_run = last_pipeline_run(database_path())
    if last_run is None:
        st.warning("No data has been published yet. The weekly pipeline will add it.")
    else:
        st.warning(
            f"The pipeline last ran on {last_run:%B %-d, %Y}, but the research data is "
            "not available yet. It will appear after the next successful data build."
        )


def run() -> None:
    """Set up the page, the sidebar and navigation, then run the selected page."""
    st.set_page_config(page_title=APP_TITLE, page_icon=":material/school:", layout="wide")
    pause_when_idle()

    if not research.is_available(database_path()):
        _render_empty_state()
        render_footer()
        return

    _render_year_filter(research.year_bounds(database_path()))
    _render_data_status()
    navigation = st.navigation(
        [
            st.Page(spec.path, title=spec.title, icon=spec.icon, default=spec.default)
            for spec in PAGES
        ]
    )
    navigation.run()
    render_footer()
