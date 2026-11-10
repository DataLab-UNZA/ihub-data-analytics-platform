"""Streamlit entry point.

Run locally with:  uv run streamlit run src/ihub/app/Home.py

Pages go in src/ihub/app/pages/. Pages must not contain SQL: they call
query functions in ihub.mart, so the UI can be replaced later without
touching the data layer.
"""

import streamlit as st

from ihub.app.idle import pause_when_idle
from ihub.mart.status import last_pipeline_run
from ihub.settings import get_settings

st.set_page_config(page_title="iHub Data Analytics Platform", layout="wide")
pause_when_idle()

st.title("iHub Data Analytics Platform")
st.caption("Research analytics for the University of Zambia: prototype, iteration 1")

last_run = last_pipeline_run(get_settings().ihub_duckdb_path)
if last_run is None:
    st.warning("No data has been published yet. The weekly pipeline will add it.")
else:
    st.caption(f"Data last built: {last_run:%B %-d, %Y at %H:%M} UTC")

st.info(
    "The research data mart has not been built yet. "
    "Pages (Overview, Explorer, Departments, Authors, Journals, Coverage) "
    "will appear here as the team builds them."
)

st.divider()
st.caption(
    "[GitHub repository](https://github.com/DataLab-UNZA/ihub-data-analytics-platform) · "
    "[Roadmap](https://github.com/DataLab-UNZA/ihub-data-analytics-platform/blob/main/docs/ROADMAP.md)"
    "  \n"
    "Research metadata from OpenAlex, ORCID, the UNZA Institutional Repository "
    "and UNZA journals (being added)."
)
