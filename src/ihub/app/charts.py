"""Plotly figures for the app. Pure functions of mart results, so they are easy to test."""

from __future__ import annotations

from collections.abc import Sequence

# Imported explicitly on purpose: Plotly looks pandas up in sys.modules without waiting for
# the import lock, so when several sessions load a cold server at once one of them can see
# pandas half-imported and crash with a circular-import error. An explicit import waits.
import pandas  # noqa: F401
import plotly.graph_objects as go

from ihub.mart.research import YearCount, YearOpenAccess

#: One accent colour for every chart so the pages look like one product.
ACCENT = "#1f6f8b"
OPEN_ACCESS = "#e08a1e"


def _base_layout(fig: go.Figure) -> go.Figure:
    fig.update_layout(
        margin={"l": 8, "r": 8, "t": 8, "b": 8},
        height=320,
        showlegend=False,
        xaxis={"type": "category", "title": None},
        hovermode="x unified",
    )
    return fig


def publications_per_year_chart(rows: Sequence[YearCount]) -> go.Figure:
    """Bar chart of publications per year."""
    fig = go.Figure(
        go.Bar(
            x=[str(r.year) for r in rows],
            y=[r.publications for r in rows],
            marker_color=ACCENT,
            name="Publications",
            hovertemplate="%{y:,} publications<extra></extra>",
        )
    )
    fig.update_yaxes(title="Publications", rangemode="tozero")
    return _base_layout(fig)


def oa_share_chart(rows: Sequence[YearOpenAccess]) -> go.Figure:
    """Line chart of the open-access share of publications per year (0 to 100%)."""
    fig = go.Figure(
        go.Scatter(
            x=[str(r.year) for r in rows],
            y=[r.open_access_share * 100 for r in rows],
            mode="lines+markers",
            line={"color": OPEN_ACCESS, "width": 3},
            name="Open access",
            customdata=[[r.open_access_publications, r.publications] for r in rows],
            hovertemplate="%{y:.1f}% (%{customdata[0]:,} of %{customdata[1]:,})<extra></extra>",
        )
    )
    fig.update_yaxes(title="Open access (%)", range=[0, 100], ticksuffix="%")
    return _base_layout(fig)
