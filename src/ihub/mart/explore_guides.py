"""Ready-made charts for Explore: plain-language questions answered by a chart.

Each guide is a question, a chart type and a query for the Explore semantic layer
(:mod:`ihub.mart.explore`), so a guide can be run, exported, saved to a dashboard and opened in
the chart builder like any other chart. The text is written for people who do not work with
data: it says what the chart answers and how to read it. There is no SQL here.

The ``filters`` of a guide are the simple filters that make sense for it (years, publication
type, school); they are worked out from the dataset, so a guide never offers a filter its data
cannot apply.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ihub.mart import explore


@dataclass(frozen=True)
class Theme:
    key: str
    title: str
    blurb: str
    admin_only: bool = False


@dataclass(frozen=True)
class Guide:
    id: str
    theme: str
    title: str
    question: str
    how_to_read: str
    viz: str
    spec: dict[str, Any]
    options: dict[str, Any] = field(default_factory=dict)
    note: str = ""  # a caveat shown under the chart, such as what is left out


THEMES: tuple[Theme, ...] = (
    Theme("growth", "Output and growth", "How much UNZA publishes, and how that is changing."),
    Theme("impact", "Impact", "How often publications are cited, and which ones stand out."),
    Theme("open-access", "Open access", "How much of the research anyone can read for free."),
    Theme("collaboration", "Collaboration", "Who UNZA researchers work with, at home and abroad."),
    Theme("researchers", "Researchers", "Roles, activity and ORCID use. Counts only, no rankings."),
    Theme("topics", "Research topics", "What UNZA researches, and where each school is strong."),
    Theme("venues", "Journals and venues", "Where UNZA research is published."),
    Theme(
        "quality",
        "Data quality and coverage",
        "How complete the data is, and which sources hold it. For data stewards.",
        admin_only=True,
    ),
)


def _spec(dataset: str, metrics: list[str], groupby: list[str] | None = None, **rest: Any) -> dict:
    return {"dataset": dataset, "metrics": metrics, "groupby": groupby or [], **rest}


_ASCENDING = {"order_by": "c0", "order_desc": False}
_EXTERNAL = [{"column": "organisation_kind", "op": "==", "value": "external"}]
_NO_SCHOOL_NOTE = "Publications with no credited school are left out."

GUIDES: tuple[Guide, ...] = (
    # --- Output and growth -------------------------------------------------------------------
    Guide(
        "output-per-year",
        "growth",
        "Publications per year",
        "Is UNZA publishing more over time?",
        "Each bar is one year. The line is the average of that year and the two before it, "
        "which smooths out ups and downs so the direction is easier to see.",
        "combo",
        _spec("publications", ["count"], ["year"], transform="rolling3", **_ASCENDING),
    ),
    Guide(
        "output-growth",
        "growth",
        "Year-on-year change",
        "By how much did output rise or fall each year?",
        "Each point is the change from the year before: above zero means more publications "
        "than the year before, below zero means fewer.",
        "line",
        _spec("publications", ["count"], ["year"], transform="yoy", **_ASCENDING),
    ),
    Guide(
        "output-by-school",
        "growth",
        "Output by school over time",
        "How much does each school contribute, and has that changed?",
        "Each coloured band is a school. The taller the band, the more publications that "
        "school is credited with that year. A publication shared by two schools counts for both.",
        "area",
        _spec(
            "unit_publications", ["publications"], ["year", "school"], series_limit=8, **_ASCENDING
        ),
        {"stacked": True},
        _NO_SCHOOL_NOTE + " Shows the eight busiest schools.",
    ),
    Guide(
        "type-mix",
        "growth",
        "Types of publication",
        "What kinds of publication make up the output?",
        "Each bar adds up to 100% of that year's publications, split by type (articles, "
        "reviews, preprints and so on). Watch how the colours change over the years.",
        "bar",
        _spec(
            "publications", ["count"], ["year", "publication_type"], series_limit=6, **_ASCENDING
        ),
        {"stacked": True, "stack_percent": True},
        "Shows the six most common types.",
    ),
    Guide(
        "output-by-decade",
        "growth",
        "Output by decade",
        "How does each decade compare?",
        "Each bar adds up all the publications of one decade, so you can compare the long-term "
        "picture without the year-to-year noise.",
        "bar",
        _spec("publications", ["count"], ["decade"], order_by="c0", order_desc=False),
    ),
    # --- Impact ------------------------------------------------------------------------------
    Guide(
        "citations-per-year",
        "impact",
        "Citations per year",
        "How many citations do publications from each year attract?",
        "Bars show total citations to that year's publications (left scale). The line shows the "
        "average number of citations per publication (right scale). Recent years have had less "
        "time to be cited, so they look lower.",
        "combo",
        _spec("publications", ["citations", "avg_citations"], ["year"], **_ASCENDING),
    ),
    Guide(
        "citation-spread",
        "impact",
        "How citations are spread",
        "Do most publications get cited, or only a few?",
        "Each bar counts publications with that many citations. The scale is logarithmic, so "
        "each gridline is ten times the one below. Most research has few citations and a "
        "small number have very many; that is normal.",
        "bar",
        _spec("publications", ["count"], ["citation_band"], **_ASCENDING),
        {"log_scale": True, "show_values": True},
    ),
    Guide(
        "most-cited",
        "impact",
        "Most-cited publications",
        "Which publications have been cited the most?",
        "The longest bars are the publications that other researchers cite most. The chart "
        "ranks publications, not people.",
        "bar",
        _spec("publications", ["citations"], ["publication"], row_limit=15),
        {"horizontal": True, "show_legend": False},
    ),
    Guide(
        "citations-by-school",
        "impact",
        "Citations per paper by school",
        "Which schools' papers are cited the most, on average?",
        "The dark bar is the average number of citations per paper; the light bar is the "
        "typical (median) paper. When the average is far above the median, a few papers with "
        "many citations are lifting it.",
        "bar",
        _spec("unit_publications", ["avg_citations", "median_citations"], ["school"]),
        {"horizontal": True},
        _NO_SCHOOL_NOTE,
    ),
    Guide(
        "impact-vs-output",
        "impact",
        "Output against impact by school",
        "Do the schools that publish most also get cited most?",
        "Each bubble is a school. Further right means more publications; higher up means more "
        "citations per paper; a bigger bubble means larger author teams.",
        "scatter",
        _spec("unit_publications", ["publications", "avg_citations", "avg_authors"], ["school"]),
        {"show_legend": False},
        _NO_SCHOOL_NOTE,
    ),
    # --- Open access ---------------------------------------------------------------------------
    Guide(
        "oa-mix",
        "open-access",
        "Open-access status over the years",
        "How much of the research is free to read?",
        "Each bar adds up to 100% of that year's publications. Gold, green, hybrid, bronze and "
        "diamond are different kinds of open access; closed means a subscription is needed.",
        "bar",
        _spec("publications", ["count"], ["year", "oa_status"], **_ASCENDING),
        {"stacked": True, "stack_percent": True},
    ),
    Guide(
        "oa-by-school",
        "open-access",
        "Open-access share by school",
        "Which schools make the most of their research freely available?",
        "Each bar is the share of that school's publications that are open access.",
        "bar",
        _spec("unit_publications", ["oa_share"], ["school"]),
        {"horizontal": True, "show_legend": False},
        _NO_SCHOOL_NOTE,
    ),
    # --- Collaboration -------------------------------------------------------------------------
    Guide(
        "intl-share",
        "collaboration",
        "International collaboration over time",
        "Is UNZA working with more researchers abroad?",
        "The line is the share of publications with at least one co-author at an institution "
        "outside Zambia. Publications whose affiliations are unknown are left out.",
        "line",
        _spec("publications", ["intl_share"], ["year"], **_ASCENDING),
    ),
    Guide(
        "partner-countries",
        "collaboration",
        "Partner countries",
        "Which countries do UNZA researchers publish with?",
        "Darker countries have more co-authored publications. Drag to move the map, scroll to "
        "zoom. Hover over a country to see its number.",
        "world_map",
        _spec(
            "affiliations",
            ["publications"],
            ["country"],
            filters=[*_EXTERNAL, {"column": "country", "op": "!=", "value": "ZM"}],
            row_limit=300,
        ),
        {},
        "Counts co-authors at institutions outside Zambia; Zambia itself is left out.",
    ),
    Guide(
        "partner-types",
        "collaboration",
        "Types of partner institution",
        "What kinds of institution does UNZA work with?",
        "Each bar counts publications co-authored with that kind of institution, such as "
        "universities, hospitals, companies or government bodies.",
        "bar",
        _spec("affiliations", ["publications"], ["organisation_type"], filters=_EXTERNAL),
        {"horizontal": True, "show_legend": False},
    ),
    Guide(
        "top-partners",
        "collaboration",
        "Top partner institutions",
        "Which institutions does UNZA co-author with most?",
        "Each bar counts the publications UNZA shares with that institution.",
        "bar",
        _spec("affiliations", ["publications"], ["organisation"], filters=_EXTERNAL, row_limit=15),
        {"horizontal": True, "show_legend": False},
    ),
    Guide(
        "team-size",
        "collaboration",
        "Team size over time",
        "Are research teams getting bigger?",
        "The middle line is the typical number of authors on a publication. The other two lines "
        "show where the smaller and larger quarter of teams fall.",
        "line",
        _spec(
            "publications",
            ["median_authors", "p25_authors", "p75_authors"],
            ["year"],
            **_ASCENDING,
        ),
    ),
    Guide(
        "domestic-vs-international",
        "collaboration",
        "Home-grown against international papers",
        "Do papers with international partners get cited more?",
        "Compares papers with and without international co-authors: the dark bar is the average "
        "citations, the light bar the typical (median) paper.",
        "bar",
        _spec(
            "publications",
            ["avg_citations", "median_citations"],
            ["international_collab"],
            filters=[{"column": "international_collab", "op": "IS NOT NULL"}],
        ),
        {"x_label": "International co-authors?"},
    ),
    Guide(
        "school-links",
        "collaboration",
        "Which schools work together",
        "Which schools co-author with each other?",
        "Each square is a pair of schools. The darker the square, the more publications they "
        "share. The chart reads the same from either side.",
        "heatmap",
        _spec(
            "school_collaboration", ["publications"], ["school", "partner_school"], row_limit=2000
        ),
        {"show_values": True},
        _NO_SCHOOL_NOTE,
    ),
    # --- Researchers ---------------------------------------------------------------------------
    Guide(
        "author-roles",
        "researchers",
        "Roles of authors by school",
        "Do researchers lead their papers or contribute to others'?",
        "Each bar adds up to 100% of a school's authorships: first author, corresponding author "
        "or another position. Only authors linked to a school are counted.",
        "bar",
        _spec("unit_authorships", ["authorships"], ["school", "author_role"], row_limit=2000),
        {"stacked": True, "stack_percent": True, "horizontal": True},
        "Counts positions, never individuals.",
    ),
    Guide(
        "active-researchers",
        "researchers",
        "Active researchers per year",
        "How many UNZA researchers publish each year?",
        "Each point is the number of different UNZA authors with at least one publication that "
        "year.",
        "line",
        _spec(
            "affiliations",
            ["authors"],
            ["year"],
            filters=[{"column": "is_unza_author", "op": "==", "value": True}],
            **_ASCENDING,
        ),
    ),
    Guide(
        "productivity",
        "researchers",
        "Publications per researcher",
        "Do a few researchers produce most of the output?",
        "Each bar counts researchers who have that many publications in total. Most researchers "
        "have a few; a small number have many. No one is named or ranked.",
        "bar",
        _spec("researcher_output", ["researchers"], ["publications_band"], **_ASCENDING),
        {"show_values": True, "show_legend": False},
    ),
    Guide(
        "orcid-by-school",
        "researchers",
        "ORCID use by school",
        "Which schools have researchers registered with ORCID?",
        "An ORCID iD is a researcher's permanent ID. Each bar is the share of a school's "
        "researchers who have one; the more, the better their work is linked up.",
        "bar",
        _spec("unit_researchers", ["orcid_share"], ["school"]),
        {"horizontal": True, "show_legend": False},
        _NO_SCHOOL_NOTE,
    ),
    Guide(
        "orcid-overall",
        "researchers",
        "ORCID use overall",
        "How many UNZA researchers have an ORCID iD?",
        "The ring splits UNZA researchers into those with and without an ORCID iD.",
        "pie",
        _spec("unit_researchers", ["researchers"], ["has_orcid"]),
        {"donut": True, "show_values": True},
        _NO_SCHOOL_NOTE,
    ),
    # --- Research topics -----------------------------------------------------------------------
    Guide(
        "topic-hierarchy",
        "topics",
        "What UNZA researches",
        "Which research areas does UNZA publish in?",
        "The inner ring is the broad domain, the next the field, the outer ring the subfield. "
        "A bigger slice means more publications. Click a slice to zoom in.",
        "sunburst",
        _spec("topics", ["publications"], ["domain", "field", "subfield"], row_limit=1000),
        {"show_legend": False},
        "Topics come from OpenAlex.",
    ),
    Guide(
        "topic-trends",
        "topics",
        "Topic trends",
        "Which topics are growing or fading?",
        "Each row is a topic and each column a year. The darker the square, the more "
        "publications. Shows the twelve most common topics.",
        "heatmap",
        _spec(
            "topics",
            ["publications"],
            ["year", "topic"],
            filters=[{"column": "is_primary_topic", "op": "==", "value": True}],
            series_limit=12,
            row_limit=1000,
            **_ASCENDING,
        ),
    ),
    Guide(
        "topic-by-school",
        "topics",
        "Strengths of each school",
        "Which research fields is each school strongest in?",
        "Each square is a school and a research field. The darker the square, the more "
        "publications that school has in that field.",
        "heatmap",
        _spec("unit_topics", ["publications"], ["field", "school"], row_limit=2000),
        {},
        _NO_SCHOOL_NOTE,
    ),
    # --- Journals and venues -------------------------------------------------------------------
    Guide(
        "venue-concentration",
        "venues",
        "Where UNZA publishes",
        "Is UNZA's research concentrated in a few journals?",
        "Bars are the 20 venues with the most publications. The line adds them up as a share "
        "of everything UNZA published: where it climbs steeply, a few venues carry most of the "
        "output.",
        "combo",
        _spec(
            "publications",
            ["count"],
            ["venue"],
            filters=[{"column": "venue", "op": "!=", "value": "Unknown venue"}],
            row_limit=20,
            transform="cumulative_share",
        ),
        {"show_legend": False},
        "Publications with no known venue are left out of the bars.",
    ),
    Guide(
        "ojs-vs-external",
        "venues",
        "UNZA journals and other journals",
        "How much is published in UNZA's own journals?",
        "The bottom band is publications in UNZA's own journals (the OJS platform); the top "
        "band is everything published elsewhere.",
        "area",
        _spec("publications", ["count"], ["year", "venue_kind"], **_ASCENDING),
        {"stacked": True},
    ),
    # --- Data quality and coverage ------------------------------------------------------------
    Guide(
        "source-overlap",
        "quality",
        "Which sources hold each publication",
        "How much do the sources overlap?",
        "Each bar counts publications by the sources that hold a record of them. A publication "
        "found only in the repository, say, is one OpenAlex does not have.",
        "bar",
        _spec("publications", ["count"], ["sources_found_in"]),
        {"horizontal": True, "show_legend": False},
    ),
    Guide(
        "attribution-quality",
        "quality",
        "How units were assigned",
        "How reliable is the school and department assignment?",
        "Each bar adds up to 100% of a year's author records at UNZA units, split by how the "
        "unit was found: from the author's department, from OpenAlex, or not at all.",
        "bar",
        _spec(
            "affiliations",
            ["publications"],
            ["year", "org_basis"],
            filters=[{"column": "organisation_kind", "op": "==", "value": "unza_unit"}],
            **_ASCENDING,
        ),
        {"stacked": True, "stack_percent": True},
    ),
    Guide(
        "metadata-completeness",
        "quality",
        "How complete the records are",
        "How many publications have a DOI, a known venue, a type and a year?",
        "Each bar is the share of publications that have that piece of information. Short bars "
        "show where the sources need to be improved.",
        "bar",
        _spec("publications", ["doi_share", "venue_share", "type_share", "year_share"]),
        {"show_legend": False},
    ),
)

GUIDES_BY_ID = {guide.id: guide for guide in GUIDES}
THEMES_BY_KEY = {theme.key: theme for theme in THEMES}

#: The simple filters a guide can offer: filter name -> the dataset column it applies to.
SIMPLE_FILTERS = {"type": "publication_type", "school": "school"}


def simple_filters(guide: Guide) -> list[str]:
    """Return the simple filters that fit ``guide``: ``years``, ``type`` and/or ``school``.

    A filter is offered only when the dataset has the column and the chart is not already split
    by it (a school filter on a chart with one bar per school would leave a single bar).
    """
    dataset = explore.dataset(guide.spec["dataset"])
    columns = {column.name for column in dataset.columns}
    grouped = set(guide.spec.get("groupby", []))
    found = ["years"] if dataset.time_column else []
    for name, column in SIMPLE_FILTERS.items():
        if column in columns and column not in grouped:
            found.append(name)
    return found


def catalogue() -> list[dict[str, Any]]:
    """The themes with their guides, as the API returns them."""
    return [
        {
            "key": theme.key,
            "title": theme.title,
            "blurb": theme.blurb,
            "admin_only": theme.admin_only,
            "guides": [
                {
                    "id": guide.id,
                    "title": guide.title,
                    "question": guide.question,
                    "how_to_read": guide.how_to_read,
                    "note": guide.note,
                    "viz": guide.viz,
                    "spec": guide.spec,
                    "options": guide.options,
                    "filters": simple_filters(guide),
                }
                for guide in GUIDES
                if guide.theme == theme.key
            ],
        }
        for theme in THEMES
    ]
