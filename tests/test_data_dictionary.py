"""docs/DATA_DICTIONARY.md must describe the research mart exactly as dbt builds it (issue #23).

The mart is built from fixtures and compared with the dictionary's tables: every table and
column (names, order and types) must be documented, and every documented column must exist
unless it is marked "planned". The dictionary therefore has to change in the same pull
request as a mart model.
"""

import re
from pathlib import Path

import pytest

from tests.dbt_helpers import build_warehouse, make_work, query

ROOT = Path(__file__).resolve().parent.parent
DICTIONARY = ROOT / "docs" / "DATA_DICTIONARY.md"
TABLE_HEADING = re.compile(r"^### `(\w+)`\s*$")
COLUMN_ROW = re.compile(r"^\| `(\w+)` \| (\w+) \| ([^|]*) \|")


def documented() -> dict[str, list[tuple[str, str, bool]]]:
    """``{table: [(column, type, planned), ...]}`` in the order the dictionary lists them."""
    tables: dict[str, list[tuple[str, str, bool]]] = {}
    current: str | None = None
    for line in DICTIONARY.read_text(encoding="utf-8").splitlines():
        if heading := TABLE_HEADING.match(line):
            current = heading.group(1)
            tables[current] = []
        elif current and (row := COLUMN_ROW.match(line)):
            column, data_type, role = row.groups()
            tables[current].append((column, data_type, "planned" in role.lower()))
    return tables


@pytest.fixture(scope="module")
def built(tmp_path_factory: pytest.TempPathFactory) -> dict[str, list[tuple[str, str]]]:
    """``{table: [(column, type), ...]}`` of the mart built from two small works."""
    db = build_warehouse(
        tmp_path_factory.mktemp("dictionary") / "test.duckdb",
        [
            make_work("W1", doi="10.1000/a", title="Cholera in Lusaka", year=2020),
            make_work("W2", title="Soil study", year=2021),
        ],
    )
    rows = query(
        db,
        "select table_name, column_name, data_type from information_schema.columns "
        "where table_schema = 'marts' order by table_name, ordinal_position",
    )
    tables: dict[str, list[tuple[str, str]]] = {}
    for row in rows:
        tables.setdefault(row["table_name"], []).append((row["column_name"], row["data_type"]))
    return tables


def test_every_mart_table_is_documented_and_every_documented_table_exists(
    built: dict[str, list[tuple[str, str]]],
) -> None:
    docs = documented()
    assert sorted(built) == sorted(
        table for table, columns in docs.items() if not all(p for _, _, p in columns)
    )


def test_columns_match_the_mart_by_name_order_and_type(
    built: dict[str, list[tuple[str, str]]],
) -> None:
    docs = documented()
    for table, columns in built.items():
        existing = [(name, data_type) for name, data_type, planned in docs[table] if not planned]
        assert existing == columns, f"docs/DATA_DICTIONARY.md is out of date for {table}"


def test_planned_columns_are_not_built_yet(built: dict[str, list[tuple[str, str]]]) -> None:
    for table, columns in documented().items():
        built_names = {name for name, _ in built.get(table, [])}
        for name, _, planned in columns:
            assert not (planned and name in built_names), f"{table}.{name} exists: drop 'planned'"


def test_every_table_of_the_star_schema_in_claude_md_is_documented() -> None:
    claude = (ROOT / "CLAUDE.md").read_text(encoding="utf-8")
    star = claude.split("### Research mart (star schema)", 1)[1].split("\n## ", 1)[0]
    named = set(re.findall(r"`((?:fact|dim|bridge)_\w+)`", star))
    assert named, "no tables found in the star-schema section of CLAUDE.md"
    assert named <= set(documented())


def test_the_readme_links_to_the_dictionary() -> None:
    assert "docs/DATA_DICTIONARY.md" in (ROOT / "README.md").read_text(encoding="utf-8")
