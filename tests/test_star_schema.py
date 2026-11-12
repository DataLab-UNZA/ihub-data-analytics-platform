"""Research-mart tests: sources, topics and venues, built with dbt from recorded fixtures.

The OpenAlex works are the recorded sample (tests/fixtures/openalex_works_sample.json),
so the expected topics are read from the fixture, not typed out here.
"""

from pathlib import Path
from typing import Any

import pytest

from tests.dbt_helpers import build_warehouse, make_work, query, sample_works

SAMPLE_TOPICS: list[dict[str, Any]] = sample_works()[0]["topics"]
SAMPLE_PRIMARY: dict[str, Any] = sample_works()[0]["primary_topic"]

# W1 and W2 share a DOI (one publication) and carry the sample's recorded topics.
# W3 is another publication whose topics have been emptied.
W1 = make_work("W1", doi="10.1000/a", title="Cancer screening", year=2020)
W2 = make_work("W2", doi="https://doi.org/10.1000/A", title="Cancer screening", year=2020)
W3 = make_work("W3", doi="10.1000/b", title="Water quality", year=2021)
W3["topics"] = []
W3["primary_topic"] = None


def ojs_article(
    number: int, journal: str, title: str, citation: str | None
) -> tuple[str, dict[str, Any]]:
    """One OJS article over OAI-PMH; ``citation`` is the dc:source text that names the journal."""
    return (
        f"oai:journals.unza.zm:article/{number}",
        {
            "journal": journal,
            "harvest_method": "oai_pmh",
            "datestamp": "2026-01-01T00:00:00Z",
            "deleted": False,
            "metadata": {
                "title": [title],
                "creator": ["Mwila, Peter"],
                "date": ["2018-03-01"],
                "type": ["Article"],
                "identifier": [
                    f"https://journals.unza.zm/index.php/{journal}/article/view/{number}"
                ],
                "source": [citation] if citation else [],
            },
        },
    )


OJS = [
    ojs_article(1, "mjz", "Soil study", "Test Journal of Zambia; Vol 5 No 2 (2018)"),
    ojs_article(2, "mjz", "Maize study", "Test Journal of Zambia; Vol 5 No 3 (2018)"),
    ojs_article(3, "zjh", "A history", None),
]


@pytest.fixture(scope="module")
def db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_warehouse(
        tmp_path_factory.mktemp("star") / "test.duckdb", [W1, W2, W3], extra_raw={"ojs": OJS}
    )


def test_dim_source_system_has_the_four_sources(db: Path) -> None:
    rows = query(db, "select source_system from marts.dim_source_system order by 1")
    assert [r["source_system"] for r in rows] == ["dspace_oai", "ojs", "openalex", "orcid"]


def test_every_bridge_row_has_a_source_system(db: Path) -> None:
    rows = query(
        db,
        """
        select s.source_system, count(*) as n
        from marts.bridge_publication_source as b
        join marts.dim_source_system as s using (source_system_key)
        group by 1
        order by 1
        """,
    )
    assert rows == [{"source_system": "ojs", "n": 3}, {"source_system": "openalex", "n": 3}]
    assert query(db, "select count(*) as n from marts.bridge_publication_source") == [{"n": 6}]


def test_topics_of_duplicate_records_are_merged(db: Path) -> None:
    rows = query(
        db,
        """
        select count(*) as n_topics, count(distinct publication_key) as n_publications
        from marts.bridge_publication_topic
        """,
    )
    # W1 and W2 are one publication, so its topics appear once; W3 has none.
    assert rows == [{"n_topics": len({t["id"] for t in SAMPLE_TOPICS}), "n_publications": 1}]


def test_exactly_one_topic_is_primary(db: Path) -> None:
    rows = query(
        db,
        """
        select t.topic_name
        from marts.bridge_publication_topic as b
        join marts.dim_topic as t using (topic_key)
        where b.is_primary_topic
        """,
    )
    assert rows == [{"topic_name": SAMPLE_PRIMARY["display_name"]}]


def test_dim_topic_carries_the_topic_hierarchy(db: Path) -> None:
    primary_id = SAMPLE_PRIMARY["id"].rsplit("/", 1)[-1]
    rows = query(
        db,
        f"select field_name, domain_name from marts.dim_topic where topic_id = '{primary_id}'",
    )
    assert rows == [
        {
            "field_name": SAMPLE_PRIMARY["field"]["display_name"],
            "domain_name": SAMPLE_PRIMARY["domain"]["display_name"],
        }
    ]


def test_ojs_journals_are_venues(db: Path) -> None:
    rows = query(
        db,
        """
        select v.venue_name, count(*) as n
        from marts.fact_publication as f
        join marts.dim_venue as v using (venue_key)
        join marts.bridge_publication_source as b using (publication_key)
        join marts.dim_source_system as s using (source_system_key)
        where s.source_system = 'ojs'
        group by 1
        order by 1
        """,
    )
    # A journal named in the citation takes that name; one without falls back to its path.
    assert rows == [
        {"venue_name": "OJS journal zjh", "n": 1},
        {"venue_name": "Test Journal of Zambia", "n": 2},
    ]
