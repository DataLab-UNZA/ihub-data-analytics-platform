"""A tiny mart with organisations, authors and topics, for ``ihub.mart.insights`` and the API."""

from pathlib import Path

import duckdb

from tests.conftest import build_mart_db


def build_insights_db(db: Path) -> Path:
    """Extend the tiny mart from ``conftest`` with the tables the insight queries read."""
    build_mart_db(db)
    with duckdb.connect(str(db)) as con:
        con.execute("ALTER TABLE marts.fact_publication ADD COLUMN is_international_collab BOOLEAN")
        con.execute(
            "UPDATE marts.fact_publication SET is_international_collab = publication_key IN "
            "('p1','p2')"
        )
        con.execute(
            "CREATE TABLE marts.dim_org (org_key VARCHAR, org_id VARCHAR, org_name VARCHAR, "
            "org_kind VARCHAR, org_type VARCHAR, parent_org_key VARCHAR, school_name VARCHAR, "
            "country_code VARCHAR, ror VARCHAR)"
        )
        con.execute(
            """
            INSERT INTO marts.dim_org VALUES
            ('ou1','u1','Department of Public Health','unza_unit','department',NULL,
             'School of Medicine','ZM',NULL),
            ('ou2','u2','Department of Physics','unza_unit','department',NULL,
             'School of Natural and Applied Sciences','ZM',NULL),
            ('ou3','u3','Unassigned department','unza_unit','unassigned',NULL,NULL,'ZM',NULL),
            ('ox1','x1','University of Oxford','external','education',NULL,NULL,'GB',NULL),
            ('ox2','x2','Wits','external','education',NULL,NULL,'ZA',NULL),
            ('ox3','x3','Mystery Institute','external','other',NULL,NULL,NULL,NULL)
            """
        )
        con.execute(
            "CREATE TABLE marts.dim_author (author_key VARCHAR, author_name VARCHAR, "
            "orcid_id VARCHAR, orcid_url VARCHAR, openalex_author_id VARCHAR, "
            "openalex_url VARCHAR, is_unza_author BOOLEAN, n_source_records BIGINT, "
            "n_sources BIGINT)"
        )
        con.execute(
            """
            INSERT INTO marts.dim_author VALUES
            ('a1','Alice Mwansa','0000-0001','https://orcid.org/0000-0001',NULL,NULL,true,2,1),
            ('a2','Bob Smith',NULL,NULL,NULL,NULL,false,1,1)
            """
        )
        con.execute(
            "CREATE TABLE marts.fact_authorship (publication_key VARCHAR, author_key VARCHAR, "
            "org_key VARCHAR, year_key INT, author_position BIGINT, is_corresponding BOOLEAN, "
            "org_basis VARCHAR)"
        )
        con.execute(
            """
            INSERT INTO marts.fact_authorship VALUES
            ('p1','a1','ou1',2019,1,true,'openalex_institution'),
            ('p1','a2','ox1',2019,2,false,'openalex_institution'),
            ('p2','a1','ou1',2020,1,true,'openalex_institution'),
            ('p2','a1','ou2',2020,1,true,'openalex_institution'),
            ('p2','a2','ox2',2020,2,false,'openalex_institution'),
            ('p3','a1','ou3',2020,1,true,'unassigned'),
            ('p5','a1','ou3',2022,1,true,'unassigned'),
            ('p5','a2','ox3',2022,2,false,'openalex_institution')
            """
        )
        con.execute(
            "CREATE TABLE marts.dim_topic (topic_key VARCHAR, topic_id VARCHAR, "
            "topic_name VARCHAR, subfield_id VARCHAR, subfield_name VARCHAR, field_id VARCHAR, "
            "field_name VARCHAR, domain_id VARCHAR, domain_name VARCHAR)"
        )
        con.execute(
            """
            INSERT INTO marts.dim_topic VALUES
            ('tp1','T1','Malaria','S1','Infectious Diseases','F1','Medicine','D1','Health'),
            ('tp2','T2','Soil','S2','Soil Science','F2','Agricultural and Biological Sciences',
             'D2','Life'),
            ('tp3','T3','HIV','S1','Infectious Diseases','F1','Medicine','D1','Health')
            """
        )
        con.execute(
            "CREATE TABLE marts.bridge_publication_topic (publication_key VARCHAR, "
            "topic_key VARCHAR, score DOUBLE, is_primary_topic BOOLEAN)"
        )
        con.execute(
            """
            INSERT INTO marts.bridge_publication_topic VALUES
            ('p1','tp1',0.9,true),('p2','tp1',0.8,true),('p2','tp3',0.5,false),('p5','tp2',0.7,true)
            """
        )
    return db
