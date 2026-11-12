"""Organisation, author and department-attribution tests, built with dbt from fixtures.

The external institutions and their affiliation texts are the recorded OpenAlex sample
(tests/fixtures/openalex_works_sample.json); the UNZA institution has the same shape. The
ORCID employment is the recorded one (tests/fixtures/orcid_employments_sample.json).
"""

import copy
from pathlib import Path
from typing import Any

import pytest

from tests.dbt_helpers import build_warehouse, make_work, query, sample_works
from tests.test_orcid_connector import EMPLOYMENTS

MARY = "0000-0001-0000-0001"
NAMELESS = "0000-0002-0000-0002"

SAMPLE_AUTHORSHIP: dict[str, Any] = sample_works()[0]["authorships"][0]
SAMPLE_INSTITUTIONS: list[dict[str, Any]] = SAMPLE_AUTHORSHIP["institutions"]
SAMPLE_AFFILIATIONS: list[dict[str, Any]] = SAMPLE_AUTHORSHIP["affiliations"]

UNZA = {
    "id": "https://openalex.org/I33278361",
    "display_name": "University of Zambia",
    "ror": "https://ror.org/03gh19d69",
    "country_code": "ZM",
    "type": "education",
}


def affiliated(
    work: dict[str, Any], position: int, institutions: list[dict[str, Any]], texts: list[str]
) -> dict[str, Any]:
    """Give the author at ``position`` these institutions, each named by every text."""
    ids = [institution["id"] for institution in institutions]
    work["authorships"][position]["institutions"] = institutions
    work["authorships"][position]["affiliations"] = [
        {"raw_affiliation_string": text, "institution_ids": ids} for text in texts
    ]
    return work


def unza_work(
    work_id: str, title: str, year: int, author: tuple[str, str, str | None], text: str
) -> dict[str, Any]:
    work = make_work(work_id, title=title, year=year, authors=[author])
    return affiliated(work, 0, [UNZA], [text])


W1 = unza_work(
    "W1",
    "Cholera in Lusaka",
    2019,
    ("A1", "Mary Phiri", MARY),
    "Department of Biological Sciences, School of Natural and Applied Sciences, "
    "University of Zambia, Lusaka, Zambia",
)
# A second author, from the recorded sample, who is not at UNZA.
W1["authorships"].append(copy.deepcopy(SAMPLE_AUTHORSHIP))
W1["authorships"][1]["author"] = {
    "id": "https://openalex.org/A2",
    "display_name": "Ophira Ginsburg",
}
W2 = unza_work(
    "W2",
    "Calf health",
    2020,
    ("A3", "Joseph Banda", None),
    "Department of Biomedical Sciences, School of Veterinary Medicine, University of Zambia",
)
# "Biomedical Sciences" is a department of two schools and no school is named.
W3 = unza_work(
    "W3",
    "Cell study",
    2020,
    ("A4", "Ruth Tembo", None),
    "Department of Biomedical Sciences, University of Zambia",
)
# No affiliation at all: only the author's ORCID employment can place these.
W4 = make_work("W4", title="Water quality", year=2020, authors=[("A1", "Mary Phiri", MARY)])
W5 = make_work("W5", title="Old study", year=2015, authors=[("A1", "Mary Phiri", MARY)])
# Departments whose official name contains commas, in the middle of the affiliation text.
W6 = unza_work(
    "W6",
    "Spatial study",
    2021,
    ("A6", "Chanda Mwape", None),
    "Department of Mathematics, Statistics and Actuarial Science, "
    "School of Natural and Applied Sciences, University of Zambia, Lusaka",
)
W7 = unza_work(
    "W7",
    "Demography study",
    2021,
    ("A7", "Lubuto Sakala", None),
    "Department of Demography, Population Sciences, Monitoring and Evaluation, "
    "University of Zambia",
)
WORKS = [W1, W2, W3, W4, W5, W6, W7]

ORCID = [
    (MARY, {"orcid": MARY, "works": {"group": []}, "employments": EMPLOYMENTS}),
    (NAMELESS, {"orcid": NAMELESS, "works": {"group": []}, "employments": {}}),
]


def dspace_set(spec: str, name: str) -> tuple[str, dict[str, Any]]:
    return f"set:{spec}", {"record_type": "set", "set_spec": spec, "set_name": name}


def dspace_item(number: int, title: str, set_specs: list[str]) -> tuple[str, dict[str, Any]]:
    return (
        f"oai:rims.unza.ac.zm:123456789/{number}",
        {
            "record_type": "item",
            "datestamp": "2026-01-01T00:00:00Z",
            "set_specs": set_specs,
            "deleted": False,
            "metadata": {
                "title": [title],
                "creator": ["Zulu, Anna"],
                "date": ["2021"],
                "type": ["Article"],
                "identifier": [f"https://rims.unza.ac.zm/handle/123456789/{number}"],
            },
        },
    )


DSPACE = [
    dspace_set("com_1_1", "School of Health Sciences"),
    dspace_set("col_1_2", "Biomedical Sciences"),
    dspace_set("col_1_3", "Library and Information Science"),
    dspace_set("col_1_4", "Theses"),
    dspace_item(1, "Drug study", ["com_1_1", "col_1_2"]),
    dspace_item(2, "Library study", ["col_1_3"]),
    dspace_item(3, "Other study", ["col_1_4"]),
    dspace_item(4, "Ward study", ["col_1_2"]),
]

BIOSCIENCES = "unza/natural-and-applied-sciences/biosciences-and-biotechnology"
LIBRARY_SCIENCE = "unza/education/library-and-information-science"
VET_BIOMEDICAL = "unza/veterinary-medicine/biomedical-sciences"
HEALTH_BIOMEDICAL = "unza/health-sciences/biomedical-sciences"
MATH_STATS = "unza/natural-and-applied-sciences/mathematics-statistics-and-actuarial-science"
DEMOGRAPHY = (
    "unza/humanities-and-social-sciences/demography-population-sciences-monitoring-and-evaluation"
)


@pytest.fixture(scope="module")
def db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    return build_warehouse(
        tmp_path_factory.mktemp("orgs") / "test.duckdb",
        WORKS,
        select="+path:models/marts/research +int_publications__departments",
        extra_raw={"orcid": ORCID, "dspace_oai": DSPACE},
    )


def test_each_institution_has_one_row_for_every_text_that_names_it(db: Path) -> None:
    toronto = SAMPLE_INSTITUTIONS[0]["id"]
    expected = sum(toronto in a["institution_ids"] for a in SAMPLE_AFFILIATIONS)
    rows = query(
        db,
        "select count(*) as n from staging.stg_openalex__work_author_affiliations "
        f"where institution_id = '{toronto.rsplit('/', 1)[-1]}'",
    )
    assert rows == [{"n": expected}]


def test_only_the_university_of_zambia_is_flagged_as_unza(db: Path) -> None:
    rows = query(
        db,
        "select distinct institution_name from staging.stg_openalex__work_author_affiliations "
        "where is_unza_institution",
    )
    assert rows == [{"institution_name": "University of Zambia"}]


def test_dim_org_holds_the_unza_hierarchy_and_an_unassigned_row(db: Path) -> None:
    rows = query(
        db,
        """
        select
            (select count(*) from marts.dim_org where org_kind = 'unza_unit') as in_dim_org,
            (select count(*) from seeds.unza_org_units) as in_seed,
            (select parent.org_name from marts.dim_org as unassigned
                join marts.dim_org as parent on parent.org_key = unassigned.parent_org_key
                where unassigned.org_name = 'Unassigned department') as parent_name
        """,
    )
    assert rows == [
        {
            "in_dim_org": rows[0]["in_seed"] + 1,
            "in_seed": rows[0]["in_seed"],
            "parent_name": "University of Zambia",
        }
    ]


def test_dim_org_gives_a_department_its_school(db: Path) -> None:
    rows = query(db, f"select school_name from marts.dim_org where org_id = '{LIBRARY_SCIENCE}'")
    assert rows == [{"school_name": "School of Education"}]


def test_external_institutions_carry_their_country_and_unza_is_not_one_of_them(db: Path) -> None:
    toronto = SAMPLE_INSTITUTIONS[0]
    rows = query(
        db,
        "select org_name, country_code from marts.dim_org where org_kind = 'external' "
        "order by org_name",
    )
    assert {"org_name": toronto["display_name"], "country_code": toronto["country_code"]} in rows
    assert all(r["org_name"] != "University of Zambia" for r in rows)
    assert len(rows) == len(SAMPLE_INSTITUTIONS)


def test_dim_author_marks_unza_authors_and_names_the_nameless(db: Path) -> None:
    rows = query(
        db,
        "select author_name, is_unza_author, orcid_url from marts.dim_author "
        "where author_name in ('Mary Phiri', 'Ophira Ginsburg', 'Unknown author') "
        "order by author_name",
    )
    assert rows == [
        {
            "author_name": "Mary Phiri",
            "is_unza_author": True,
            "orcid_url": f"https://orcid.org/{MARY}",
        },
        {"author_name": "Ophira Ginsburg", "is_unza_author": False, "orcid_url": None},
        {
            "author_name": "Unknown author",
            "is_unza_author": False,
            "orcid_url": f"https://orcid.org/{NAMELESS}",
        },
    ]


def test_departments_are_attributed_from_each_kind_of_evidence(db: Path) -> None:
    rows = query(
        db,
        """
        select publication.title, department.org_unit_id, department.evidence
        from intermediate.int_publications__departments as department
        join marts.dim_publication as publication using (publication_key)
        """,
    )
    attributed: dict[str, set[tuple[str, str]]] = {}
    for row in rows:
        attributed.setdefault(row["title"], set()).add((row["org_unit_id"], row["evidence"]))
    assert attributed == {
        # an affiliation, and the author's UNZA employment current in 2019
        "Cholera in Lusaka": {
            (BIOSCIENCES, "openalex_affiliation"),
            (LIBRARY_SCIENCE, "orcid_employment"),
        },
        # the school named in the affiliation settles the two "Biomedical Sciences"
        "Calf health": {(VET_BIOMEDICAL, "openalex_affiliation")},
        # employment only (no affiliation text)
        "Water quality": {(LIBRARY_SCIENCE, "orcid_employment")},
        # the IRIMS community names the school; the collection names the department
        "Drug study": {(HEALTH_BIOMEDICAL, "dspace_set")},
        "Library study": {(LIBRARY_SCIENCE, "dspace_set")},
        # official names that contain commas
        "Spatial study": {(MATH_STATS, "openalex_affiliation")},
        "Demography study": {(DEMOGRAPHY, "openalex_affiliation")},
    }


@pytest.mark.parametrize(
    "title",
    [
        "Cell study",  # "Biomedical Sciences" with no school: ambiguous, never guessed
        "Old study",  # published in 2015, before the ORCID employment started in 2017
        "Other study",  # an IRIMS set that names no unit
        "Ward study",  # "Biomedical Sciences" again, with no school among its sets
    ],
)
def test_names_that_cannot_be_placed_get_no_department(db: Path, title: str) -> None:
    rows = query(
        db,
        "select count(*) as n from intermediate.int_publications__departments "
        f"join marts.dim_publication using (publication_key) where title = '{title}'",
    )
    assert rows == [{"n": 0}]
    assert query(
        db, f"select count(*) as n from marts.dim_publication where title = '{title}'"
    ) == [{"n": 1}]


def authorship_rows(db: Path) -> dict[str, set[tuple[str, str]]]:
    """Every fact_authorship row as publication title -> {(author name, org id)}."""
    rows = query(
        db,
        """
        select publication.title, author.author_name, org.org_id
        from marts.fact_authorship as authorship
        join marts.dim_publication as publication using (publication_key)
        join marts.dim_author as author using (author_key)
        join marts.dim_org as org using (org_key)
        """,
    )
    found: dict[str, set[tuple[str, str]]] = {}
    for row in rows:
        found.setdefault(row["title"], set()).add((row["author_name"], row["org_id"]))
    return found


def test_openalex_authorships_have_one_row_per_author_and_organisation(db: Path) -> None:
    external = {f"openalex:{i['id'].rsplit('/', 1)[-1]}" for i in SAMPLE_INSTITUTIONS}
    found = authorship_rows(db)
    assert found["Cholera in Lusaka"] == {
        # Mary's two departments (affiliation text and ORCID employment) are two rows
        ("Mary Phiri", BIOSCIENCES),
        ("Mary Phiri", LIBRARY_SCIENCE),
        *{("Ophira Ginsburg", org_id) for org_id in external},
    }
    assert found["Calf health"] == {("Joseph Banda", VET_BIOMEDICAL)}
    assert found["Spatial study"] == {("Chanda Mwape", MATH_STATS)}
    assert found["Demography study"] == {("Lubuto Sakala", DEMOGRAPHY)}
    # at UNZA by affiliation, but no department found: never guessed
    assert found["Cell study"] == {("Ruth Tembo", "unassigned-department")}
    # no affiliation, but a UNZA employment current in 2020
    assert found["Water quality"] == {("Mary Phiri", LIBRARY_SCIENCE)}
    # no affiliation and no employment yet in 2015: an unknown organisation, and the
    # publication still gets a row at UNZA, for the "No author listed" author
    assert found["Old study"] == {
        ("Mary Phiri", "unknown-organisation"),
        ("No author listed", "unassigned-department"),
    }


def test_repository_authors_take_the_department_found_for_the_item(db: Path) -> None:
    found = {
        title: {org_id for _, org_id in rows}
        for title, rows in authorship_rows(db).items()
        if title in {"Drug study", "Library study", "Other study", "Ward study"}
    }
    assert found == {
        "Drug study": {HEALTH_BIOMEDICAL},
        "Library study": {LIBRARY_SCIENCE},
        "Other study": {"unassigned-department"},
        "Ward study": {"unassigned-department"},
    }


def test_every_publication_has_an_authorship_row(db: Path) -> None:
    rows = query(
        db,
        """
        select count(*) as n
        from marts.fact_publication
        where publication_key not in (select publication_key from marts.fact_authorship)
        """,
    )
    assert rows == [{"n": 0}]


def test_unza_author_count_and_international_collaboration_are_null_when_unknown(db: Path) -> None:
    rows = query(
        db,
        """
        select publication.title, fact.n_unza_authors, fact.is_international_collab
        from marts.fact_publication as fact
        join marts.dim_publication as publication using (publication_key)
        order by publication.title
        """,
    )
    measures = {r["title"]: (r["n_unza_authors"], r["is_international_collab"]) for r in rows}
    assert measures == {
        "Calf health": (1, False),
        "Cell study": (1, False),
        "Cholera in Lusaka": (1, True),  # a co-author in Canada
        "Demography study": (1, False),
        "Spatial study": (1, False),
        # OpenAlex gives no affiliation for these, so the answer is unknown, not 0 or false
        "Old study": (None, None),
        "Water quality": (None, None),
        # repository items have no OpenAlex record at all
        "Drug study": (None, None),
        "Library study": (None, None),
        "Other study": (None, None),
        "Ward study": (None, None),
    }


def test_overlapping_matches_in_one_affiliation_keep_only_the_longest(db: Path) -> None:
    """The name with commas is found as two overlapping runs of parts; the longer one stays.

    Both runs point to the same unit here, so only the recorded matched name shows which
    one was kept: the run that goes on to include the school, not the shorter one.
    """
    rows = query(
        db,
        "select matched_name from intermediate.int_publications__departments "
        f"where org_unit_id = '{MATH_STATS}'",
    )
    assert rows == [
        {
            "matched_name": "Department of Mathematics, Statistics and Actuarial Science, "
            "School of Natural and Applied Sciences"
        }
    ]
