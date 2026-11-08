from collections.abc import Iterator
from typing import Any

import pytest

from ihub.connectors import Connector, RawRecord


class FakeConnector(Connector):
    source_name = "fake"

    def fetch_records(self) -> Iterator[tuple[str, dict[str, Any]]]:
        yield "w1", {"title": "A study of maize yields"}
        yield 2, {"title": "Data mining in Zambian universities"}


def test_fetch_wraps_records_with_provenance() -> None:
    records = list(FakeConnector().fetch())

    assert len(records) == 2
    assert all(isinstance(r, RawRecord) for r in records)
    assert records[0].source == "fake"
    assert records[1].record_id == "2"
    assert records[0].payload["title"] == "A study of maize yields"


def test_connector_without_source_name_is_rejected() -> None:
    class Nameless(Connector):
        def fetch_records(self) -> Iterator[tuple[str, dict[str, Any]]]:
            yield from ()

    with pytest.raises(ValueError):
        Nameless()
