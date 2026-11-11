"""Tests for the unza_org_units and department_aliases seeds (issue #18).

``dbt build`` loads both seeds and runs every test on them, including the hierarchy and
unambiguous-alias data tests in transform/tests/.
"""

from pathlib import Path

import pytest

from tests.dbt_helpers import query, run_dbt

SELECT = "unza_org_units department_aliases"


@pytest.fixture(scope="module")
def db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    path = tmp_path_factory.mktemp("seeds") / "test.duckdb"
    run_dbt(path, "build", SELECT)
    return path


def unit(db: Path, org_unit_id: str) -> dict:
    rows = query(db, f"select * from seeds.unza_org_units where org_unit_id = '{org_unit_id}'")
    assert len(rows) == 1, org_unit_id
    return rows[0]


def test_library_and_information_science_is_in_the_school_of_education(db: Path) -> None:
    department = unit(db, "unza/education/library-and-information-science")
    assert department["org_unit_name"] == "Library and Information Science"
    assert department["org_unit_type"] == "department"
    assert department["parent_org_unit_id"] == "unza/education"
    assert unit(db, "unza/education")["org_unit_name"] == "School of Education"


def test_the_library_is_a_separate_unit_outside_every_school(db: Path) -> None:
    library = unit(db, "unza/library")
    assert library["org_unit_type"] == "library"
    assert library["parent_org_unit_id"] == "unza"


def test_units_outside_the_schools_sit_directly_under_the_university(db: Path) -> None:
    rows = query(
        db,
        "select org_unit_id, org_unit_type from seeds.unza_org_units "
        "where org_unit_type in ('library', 'institute', 'directorate') "
        "and parent_org_unit_id = 'unza' order by org_unit_id",
    )
    assert [r["org_unit_id"] for r in rows] == [
        "unza/crhma",
        "unza/distance-education",
        "unza/dittc",
        "unza/library",
        "unza/research-and-development",
    ]


def test_the_hierarchy_has_one_institution_thirteen_schools_and_their_departments(
    db: Path,
) -> None:
    rows = query(
        db,
        "select org_unit_type, count(*) as n from seeds.unza_org_units group by 1 order by 1",
    )
    counts = {r["org_unit_type"]: r["n"] for r in rows}
    assert counts["institution"] == 1
    assert counts["school"] == 13
    assert counts["library"] == 1
    assert counts["department"] >= 60
    empty_schools = query(
        db,
        """
        select school.org_unit_id
        from seeds.unza_org_units as school
        where school.org_unit_type = 'school'
          and not exists (
              select 1 from seeds.unza_org_units as child
              where child.parent_org_unit_id = school.org_unit_id
                and child.org_unit_type = 'department'
          )
        """,
    )
    assert empty_schools == []


def test_every_unit_can_be_found_under_its_own_name(db: Path) -> None:
    """Each unit's official name is also an alias, so one lookup finds any unit."""
    missing = query(
        db,
        """
        select org_unit_id, org_unit_name
        from seeds.unza_org_units as u
        where org_unit_type <> 'institution'
          and not exists (
              select 1 from seeds.department_aliases as a
              where a.org_unit_id = u.org_unit_id
                and lower(a.alias) in (lower(u.org_unit_name), lower(u.org_unit_name) || 's')
          )
        """,
    )
    assert missing == []


@pytest.mark.parametrize(
    ("alias", "school_context_id", "expected"),
    [
        (
            "Biological Sciences",
            None,
            "unza/natural-and-applied-sciences/biosciences-and-biotechnology",
        ),
        ("Computer Science", None, "unza/natural-and-applied-sciences/computing-and-informatics"),
        ("Library and Information Studies", None, "unza/education/library-and-information-science"),
        (
            "Biomedical Sciences",
            "unza/veterinary-medicine",
            "unza/veterinary-medicine/biomedical-sciences",
        ),
        ("Biomedical Sciences", "unza/health-sciences", "unza/health-sciences/biomedical-sciences"),
    ],
)
def test_names_seen_in_the_sources_map_to_the_right_unit(
    db: Path, alias: str, school_context_id: str | None, expected: str
) -> None:
    context = "is null" if school_context_id is None else f"= '{school_context_id}'"
    rows = query(
        db,
        f"select org_unit_id from seeds.department_aliases where alias = '{alias}' "
        f"and applies_to = 'any' and school_context_id {context}",
    )
    assert rows == [{"org_unit_id": expected}]


def test_a_name_shared_by_two_schools_never_maps_without_a_school(db: Path) -> None:
    rows = query(
        db,
        "select org_unit_id from seeds.department_aliases "
        "where alias in ('Biomedical Sciences', 'Population Studies') "
        "and school_context_id is null",
    )
    assert rows == []
