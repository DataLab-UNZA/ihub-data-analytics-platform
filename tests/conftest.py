"""Shared test fixtures."""

from pathlib import Path

import duckdb
import pytest


def build_mart_db(db: Path) -> Path:
    """Create a tiny research mart (five publications, 2019 to 2022) at ``db``."""
    with duckdb.connect(str(db)) as con:
        con.execute("CREATE SCHEMA marts")
        con.execute("CREATE TABLE marts.dim_year (year_key INT, year INT)")
        con.execute(
            "INSERT INTO marts.dim_year VALUES (2019,2019),(2020,2020),(2021,2021),(2022,2022)"
        )
        con.execute(
            "CREATE TABLE marts.dim_publication_type (type_key VARCHAR, type_label VARCHAR)"
        )
        con.execute(
            "INSERT INTO marts.dim_publication_type VALUES ('t1','Article'),('t2','Review')"
        )
        con.execute(
            "CREATE TABLE marts.dim_venue (venue_key VARCHAR, venue_id VARCHAR, venue_name VARCHAR)"
        )
        con.execute(
            "INSERT INTO marts.dim_venue VALUES "
            "('v1','S1','The Lancet'),('v2','S2','Medical Journal of Zambia'),(NULL,NULL,'x'),"
            "('v0',NULL,'Unknown venue')"
        )
        con.execute(
            "CREATE TABLE marts.dim_publication (publication_key VARCHAR, title VARCHAR, "
            "doi VARCHAR, "
            "doi_url VARCHAR, primary_source_system VARCHAR, primary_record_url VARCHAR)"
        )
        con.execute(
            """
            INSERT INTO marts.dim_publication VALUES
            ('p1','Malaria in Zambia','10.1/a','https://doi.org/10.1/a','openalex','https://openalex.org/W1'),
            ('p2','Maternal health','10.1/b','https://doi.org/10.1/b','openalex','https://openalex.org/W2'),
            ('p3','=HYPERLINK("x")',NULL,NULL,'openalex','https://openalex.org/W3'),
            ('p4','100% sure_thing',NULL,NULL,'openalex','https://openalex.org/W4'),
            ('p5','Zambian soils','10.1/e',NULL,'ojs',NULL)
            """
        )
        con.execute(
            """
            CREATE TABLE marts.fact_publication (
                publication_key VARCHAR, venue_key VARCHAR, year_key INT, type_key VARCHAR,
                cited_by_count INT, n_authors INT, is_oa BOOLEAN, oa_status VARCHAR,
                in_openalex BOOLEAN, in_repository BOOLEAN, in_ojs BOOLEAN)
            """
        )
        con.execute(
            """
            INSERT INTO marts.fact_publication VALUES
            ('p1','v1',2019,'t1',10,3,true,'gold',true,false,false),
            ('p2','v1',2020,'t2',20,5,false,'closed',true,false,false),
            ('p3','v2',2020,'t1',0,1,true,'green',true,false,false),
            ('p4','v0',2022,'t1',5,2,false,'closed',true,false,false),
            ('p5','v2',2022,'t1',1,1,true,'diamond',false,false,true)
            """
        )
    return db


@pytest.fixture(scope="session")
def mart_db(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """A tiny research mart, built once per test run."""
    return build_mart_db(tmp_path_factory.mktemp("mart") / "mart.duckdb")
