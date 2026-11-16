"""Tests for ``ihub.mart.insights``, against the tiny hand-built mart in ``conftest``."""

from pathlib import Path

import pytest

from ihub.mart import insights as i
from ihub.mart.research import YearRange

ALL = YearRange(2019, 2022)


def test_venue_directory_excludes_unknown_venues_and_counts_open_access(insights_db: Path) -> None:
    venues = i.venue_directory(insights_db, ALL)
    assert [(v.venue, v.publications, v.open_access_publications) for v in venues] == [
        ("Medical Journal of Zambia", 2, 2),
        ("The Lancet", 2, 1),
    ]
    assert venues[1].open_access_share == pytest.approx(0.5)
    assert venues[1].citations == 30


def test_venue_directory_rejects_a_bad_limit(insights_db: Path) -> None:
    with pytest.raises(ValueError):
        i.venue_directory(insights_db, ALL, limit=0)


def test_top_themes_counts_each_publication_once_per_theme(insights_db: Path) -> None:
    fields = i.top_themes(insights_db, ALL, level="field")
    assert [(t.name, t.publications) for t in fields] == [
        ("Medicine", 2),
        ("Agricultural and Biological Sciences", 1),
    ]
    topics = i.top_themes(insights_db, ALL, level="topic")
    assert [(t.name, t.publications) for t in topics] == [("Malaria", 2), ("HIV", 1), ("Soil", 1)]


def test_top_themes_respects_the_year_range_and_rejects_unknown_levels(insights_db: Path) -> None:
    assert [t.name for t in i.top_themes(insights_db, YearRange(2022, 2022))] == [
        "Agricultural and Biological Sciences"
    ]
    with pytest.raises(ValueError):
        i.top_themes(insights_db, ALL, level="name; DROP TABLE marts.dim_topic")


def test_fields_with_topics(insights_db: Path) -> None:
    medicine = i.fields_with_topics(insights_db, ALL)[0]
    assert medicine.field == "Medicine"
    assert [(t.name, t.publications) for t in medicine.topics] == [("Malaria", 2), ("HIV", 1)]


def test_school_outputs_count_distinct_publications_and_label_unassigned(
    insights_db: Path,
) -> None:
    schools = i.school_outputs(insights_db, ALL)
    assert [(s.school, s.publications) for s in schools] == [
        ("School of Medicine", 2),
        (i.UNASSIGNED_UNIT, 2),
        ("School of Natural and Applied Sciences", 1),
    ]


def test_unit_outputs(insights_db: Path) -> None:
    units = {u.name: u for u in i.unit_outputs(insights_db, ALL)}
    assert units["Department of Public Health"].publications == 2
    assert units["Department of Public Health"].school == "School of Medicine"
    assert units["Unassigned department"].unit_type == "unassigned"


def test_collaboration_summary_does_not_count_unknown_as_international(insights_db: Path) -> None:
    summary = i.collaboration_summary(insights_db, ALL)
    assert summary == i.CollaborationSummary(
        international_publications=2,
        partner_organisations=3,
        countries=2,
        publications_with_unknown_country=1,
    )


def test_top_countries_and_partners(insights_db: Path) -> None:
    assert [(c.country_code, c.publications) for c in i.top_countries(insights_db, ALL)] == [
        ("GB", 1),
        ("ZA", 1),
    ]
    partners = i.top_partners(insights_db, ALL)
    assert [p.name for p in partners] == ["Mystery Institute", "University of Oxford", "Wits"]
    assert partners[0].country_code is None
    with pytest.raises(ValueError):
        i.top_partners(insights_db, ALL, limit=0)


def test_publication_detail(insights_db: Path) -> None:
    detail = i.publication_detail(insights_db, "p2")
    assert detail is not None
    assert detail.title == "Maternal health"
    assert [a.name for a in detail.authors] == ["Alice Mwansa", "Bob Smith"]
    assert detail.authors[0].is_unza_author
    assert {s.source for s in detail.sources} == {
        "OpenAlex",
        "ORCID",
        "UNZA Institutional Repository (IRIMS)",
    }
    assert detail.units == ("School of Medicine", "School of Natural and Applied Sciences")


def test_publication_detail_of_an_unknown_key_is_none(insights_db: Path) -> None:
    assert i.publication_detail(insights_db, "nope") is None
