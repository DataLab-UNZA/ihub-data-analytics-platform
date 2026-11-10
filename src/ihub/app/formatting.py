"""Number formatting for the app. Pure functions, no Streamlit, so they are easy to test."""

from __future__ import annotations


def format_count(value: int) -> str:
    """Format a whole number with thousands separators, e.g. 12,345."""
    return f"{value:,}"


def format_share(share: float) -> str:
    """Format a share between 0 and 1 as a percentage with one decimal, e.g. 62.5%."""
    return f"{share * 100:.1f}%"


def percent_change(current: int, previous: int) -> str | None:
    """Return the change from ``previous`` to ``current`` as e.g. "+12.5%".

    Returns None when ``previous`` is zero, because a percentage change is undefined.
    """
    if previous == 0:
        return None
    return f"{(current - previous) / previous * 100:+.1f}%"


def points_change(current_share: float, previous_share: float) -> str:
    """Return the change between two shares in percentage points, e.g. "+2.1 pp"."""
    return f"{(current_share - previous_share) * 100:+.1f} pp"
