"""Source coverage page: which publications one source has and another lacks.

For the UNZA Library (issue #22): every comparison follows the global year filter, shows
its count and its newest publications, and can be downloaded in full as CSV.
"""

import streamlit as st

from ihub.app import formatting, layout
from ihub.mart import coverage, research

PREVIEW_ROWS = 100

db = layout.database_path()
years = layout.selected_years()
sources = coverage.source_systems(db)
names = {source.code: source.name for source in sources}

st.title("Source coverage")
st.caption(
    f"Publications found in one source but not in another, {years.start} to {years.end}. "
    "A publication counts as in a source when at least one of its records came from it."
)

totals = coverage.source_totals(db, years)
for column, total in zip(st.columns(len(totals)), totals, strict=True):
    column.metric(total.source.name, formatting.format_count(total.publications), border=True)


def show_gap(in_source: str, missing_from: str, purpose: str, key: str) -> None:
    """Show one comparison: its count, a CSV of every row and the newest publications."""
    total = coverage.count_missing(db, in_source, missing_from, years)
    st.caption(purpose)
    count_column, export_column = st.columns([1, 2], vertical_alignment="bottom")
    count_column.metric("Publications", formatting.format_count(total))
    if total == 0:
        st.info("None in the selected years.")
        return
    export_column.download_button(
        f"Download all {total:,} as CSV",
        data=lambda: research.publications_to_csv(
            coverage.missing_publications(db, in_source, missing_from, years, limit=None)
        ),
        file_name=f"unza-in-{in_source}-not-in-{missing_from}-{years.start}-{years.end}.csv",
        mime="text/csv",
        icon=":material/download:",
        key=f"download-{key}",
    )
    rows = coverage.missing_publications(db, in_source, missing_from, years, limit=PREVIEW_ROWS)
    if total > len(rows):
        st.caption(f"Showing the newest {len(rows):,} of {total:,}. Download the CSV for all.")
    st.dataframe(
        [
            {
                "Title": row.title,
                "Year": row.year,
                "Type": row.type,
                "Venue": row.venue,
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


tabs = st.tabs([gap.title for gap in coverage.COVERAGE_GAPS] + ["Compare any two sources"])
for tab, gap in zip(tabs, coverage.COVERAGE_GAPS, strict=False):
    with tab:
        show_gap(gap.in_source, gap.missing_from, gap.purpose, key=gap.in_source + gap.missing_from)


def default_index(codes: list[str], preferred: str, fallback: int) -> int:
    """The position of ``preferred`` in ``codes``, or ``fallback`` if it is not there."""
    return codes.index(preferred) if preferred in codes else min(fallback, len(codes) - 1)


with tabs[-1]:
    codes = list(names)
    in_column, missing_column = st.columns(2)
    in_source = in_column.selectbox(
        "In",
        codes,
        format_func=names.get,
        index=default_index(codes, "orcid", 0),
        key="compare-in",
    )
    missing_from = missing_column.selectbox(
        "Not in",
        codes,
        format_func=names.get,
        index=default_index(codes, "openalex", 1),
        key="compare-not-in",
    )
    if in_source == missing_from:
        st.info("Choose two different sources.")
    else:
        purpose = (
            f"Publications with a record in {names[in_source]} and none in {names[missing_from]}."
        )
        if "orcid" in (in_source, missing_from):
            purpose += (
                " ORCID holds only what researchers add to their own records, so its gaps "
                "say more about ORCID than about UNZA's output."
            )
        show_gap(in_source, missing_from, purpose, key="compare")
