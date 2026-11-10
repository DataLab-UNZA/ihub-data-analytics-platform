"""Overview page: headline numbers and trends for the selected years."""

import streamlit as st

from ihub.app import charts, formatting, layout
from ihub.mart import research

db = layout.database_path()
years = layout.selected_years()
bounds = research.year_bounds(db)

st.title("Overview")
st.caption(f"University of Zambia research output, {years.start} to {years.end}")

current = research.headline_counts(db, years)
if current.publications == 0:
    st.info("There are no publications in the selected years.")
    st.stop()

# Compare with the period of the same length just before, but only when the data covers it.
previous_years = years.previous_period()
previous = (
    research.headline_counts(db, previous_years) if previous_years.start >= bounds.start else None
)
versus = f"vs {previous_years.start} to {previous_years.end}"


def card(column, label: str, value: str, delta: str | None) -> None:
    """Show one headline card; the comparison label appears only when there is a change."""
    column.metric(
        label,
        value,
        delta=delta,
        delta_description=versus if delta else None,
        border=True,
    )


publications_card, oa_card, citations_card, venues_card = st.columns(4)
card(
    publications_card,
    "Publications",
    formatting.format_count(current.publications),
    formatting.percent_change(current.publications, previous.publications) if previous else None,
)
card(
    oa_card,
    "Open access share",
    formatting.format_share(current.open_access_share),
    formatting.points_change(current.open_access_share, previous.open_access_share)
    if previous and previous.publications
    else None,
)
card(
    citations_card,
    "Citations",
    formatting.format_count(current.citations),
    formatting.percent_change(current.citations, previous.citations) if previous else None,
)
card(
    venues_card,
    "Venues",
    formatting.format_count(current.venues),
    formatting.percent_change(current.venues, previous.venues) if previous else None,
)
if previous is None:
    st.caption(
        "Changes are shown when the data covers the previous period of the same length "
        f"({previous_years.start} to {previous_years.end})."
    )

per_year_column, oa_column = st.columns(2)
with per_year_column:
    st.subheader("Publications per year")
    st.plotly_chart(charts.publications_per_year_chart(research.publications_per_year(db, years)))
with oa_column:
    st.subheader("Open access share")
    st.plotly_chart(charts.oa_share_chart(research.oa_share_per_year(db, years)))

st.subheader("Top 10 venues")
venues = research.top_venues(db, years, limit=10)
st.dataframe(
    [{"Venue": v.venue, "Publications": v.publications, "Citations": v.citations} for v in venues],
    hide_index=True,
    column_config={
        "Publications": st.column_config.NumberColumn(format="%d"),
        "Citations": st.column_config.NumberColumn(format="%d"),
    },
)
