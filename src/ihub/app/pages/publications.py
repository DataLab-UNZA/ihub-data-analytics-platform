"""Publications explorer: search, filter and export the publications behind the numbers."""

import streamlit as st

from ihub.app import layout
from ihub.mart import research

PAGE_SIZES = (25, 50, 100)
PAGE_KEY = "publications_page"
SIGNATURE_KEY = "publications_filter_signature"

db = layout.database_path()
years = layout.selected_years()
options = research.filter_options(db)

st.title("Publications")
st.caption(f"University of Zambia publications, {years.start} to {years.end}")

type_column, oa_column, source_column, venue_column = st.columns(4)
types = type_column.multiselect("Type", options.types)
oa_statuses = oa_column.multiselect("Open access status", options.oa_statuses)
sources = source_column.multiselect("Source", options.sources)
venues = venue_column.multiselect("Venue", options.venues)
search = st.text_input("Search title or DOI", placeholder="For example: malaria")

filters = research.PublicationFilter(
    years=years,
    types=tuple(types),
    oa_statuses=tuple(oa_statuses),
    venues=tuple(venues),
    sources=tuple(sources),
    search=search,
)
total = research.count_publications(db, filters)

if total == 0:
    st.info("No publications match these filters. Try removing one.")
    st.stop()

# Go back to the first page whenever a filter changes.
if st.session_state.get(SIGNATURE_KEY) != repr(filters):
    st.session_state[SIGNATURE_KEY] = repr(filters)
    st.session_state[PAGE_KEY] = 1

size_column, page_column, export_column = st.columns([1, 1, 2], vertical_alignment="bottom")
page_size = size_column.selectbox("Rows per page", PAGE_SIZES, index=1)
last_page = max(1, -(-total // page_size))
st.session_state[PAGE_KEY] = min(st.session_state.get(PAGE_KEY, 1), last_page)
page = page_column.number_input(
    f"Page (of {last_page:,})", min_value=1, max_value=last_page, step=1, key=PAGE_KEY
)
export_column.download_button(
    f"Download all {total:,} rows as CSV",
    data=lambda: research.publications_to_csv(research.publications(db, filters, limit=None)),
    file_name=f"unza-publications-{years.start}-{years.end}.csv",
    mime="text/csv",
    icon=":material/download:",
)

rows = research.publications(db, filters, limit=page_size, offset=(page - 1) * page_size)
first = (page - 1) * page_size + 1
st.caption(f"Showing {first:,} to {first + len(rows) - 1:,} of {total:,} publications")
st.dataframe(
    [
        {
            "Title": row.title,
            "Year": row.year,
            "Type": row.type,
            "Venue": row.venue,
            "OA status": row.oa_status,
            "Citations": row.cited_by_count,
            "Authors": row.n_authors,
            "Sources": row.sources,
            "DOI": row.doi_url,
            "Record": row.record_url,
        }
        for row in rows
    ],
    hide_index=True,
    column_config={
        "Title": st.column_config.TextColumn(width="large"),
        "Year": st.column_config.NumberColumn(format="%d"),
        "DOI": st.column_config.LinkColumn(display_text=r"https://doi\.org/(.*)"),
        "Record": st.column_config.LinkColumn(display_text="Open record"),
    },
)
