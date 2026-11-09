"""Streamlit entry point.

Run locally with:  uv run streamlit run src/ihub/app/Home.py

Pages go in src/ihub/app/pages/. Pages must not contain SQL: they call
query functions in ihub.mart, so the UI can be replaced later without
touching the data layer.
"""

import streamlit as st

st.set_page_config(page_title="iHub Data Analytics Platform", layout="wide")

st.title("iHub Data Analytics Platform")
st.caption("Research analytics for the University of Zambia: prototype, iteration 1")

st.info(
    "The research data mart has not been built yet. "
    "Pages (Overview, Explorer, Departments, Authors, Journals, Coverage) "
    "will appear here as the team builds them."
)
