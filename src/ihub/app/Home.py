"""Streamlit entry point.

Run locally with:  uv run streamlit run src/ihub/app/Home.py

Pages go in src/ihub/app/pages/. Pages must not contain SQL: they call
query functions in ihub.mart, so the UI can be replaced later without
touching the data layer.
"""

from pathlib import Path

import streamlit as st

from ihub.mart.data_source import ensure_duckdb
from ihub.mart.status import last_pipeline_run
from ihub.settings import get_settings

st.set_page_config(page_title="iHub Data Analytics Platform", layout="wide")

st.title("iHub Data Analytics Platform")
st.caption("Research analytics for the University of Zambia: prototype, iteration 1")

st.info(
    "The research data mart has not been built yet. "
    "Pages (Overview, Explorer, Departments, Authors, Journals, Coverage) "
    "will appear here as the team builds them."
)


@st.cache_data(ttl=3600, show_spinner="Fetching the latest data…")
def _duckdb_path() -> str | None:
    """Local path to the DuckDB file, fetching the newest published data if needed.

    Re-checked hourly, so a new weekly data release is picked up without a
    redeploy. See ihub.mart.data_source.
    """
    path = ensure_duckdb(get_settings().ihub_duckdb_path)
    return str(path) if path is not None else None


_path = _duckdb_path()
last_run = last_pipeline_run(Path(_path)) if _path is not None else None
if last_run is None:
    st.caption("Data: no pipeline run is published yet.")
else:
    st.caption(f"Data: last pipeline run {last_run:%B %-d, %Y at %H:%M} UTC.")
