"""Tests for the ingest command line, with fake connectors (no network)."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import duckdb
import pytest

from ihub.connectors.base import Connector
from ihub.ingest import __main__ as ingest


class FakeA(Connector):
    source_name = "fake_a"

    def fetch_records(self) -> Iterator[tuple[str, dict[str, Any]]]:
        yield "a1", {"n": 1}


class FakeB(Connector):
    source_name = "fake_b"

    def fetch_records(self) -> Iterator[tuple[str, dict[str, Any]]]:
        yield from [("b1", {"n": 1}), ("b2", {"n": 2})]


@pytest.fixture
def db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "ihub.duckdb"
    monkeypatch.setenv("IHUB_DUCKDB_PATH", str(path))
    monkeypatch.setattr(ingest, "CONNECTORS", [FakeA, FakeB])
    monkeypatch.setattr(
        ingest,
        "load_source_config",
        lambda: {"fake_a": {"enabled": True}, "fake_b": {"enabled": False}},
    )
    return path


def tables(path: Path) -> set[str]:
    with duckdb.connect(str(path)) as con:
        return {
            row[0] for row in con.execute("SELECT schema_name FROM duckdb_schemas()").fetchall()
        }


def test_a_full_run_skips_disabled_sources_and_is_recorded(db: Path) -> None:
    ingest.main([])
    assert {"raw_fake_a", "meta"} <= tables(db)
    assert "raw_fake_b" not in tables(db)


def test_a_named_source_runs_even_if_disabled_and_is_not_recorded(db: Path) -> None:
    ingest.main(["--source", "fake_b"])
    with duckdb.connect(str(db)) as con:
        assert con.execute("SELECT count(*) FROM raw_fake_b.records").fetchone() == (2,)
    assert "raw_fake_a" not in tables(db)
    assert "meta" not in tables(db)


def test_an_unknown_source_is_refused(db: Path) -> None:
    with pytest.raises(SystemExit):
        ingest.main(["--source", "nope"])
