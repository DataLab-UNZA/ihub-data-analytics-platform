"""The shared interface every ingestion connector implements.

A connector only *fetches*: it returns records exactly as the source gave them,
wrapped with run metadata. Cleaning, standardising and de-duplication happen
later, in the dbt staging and intermediate layers.

To add a new source (e.g. a student information system):
1. Subclass ``Connector`` in ``src/ihub/connectors/<source>.py``.
2. Set ``source_name`` and implement ``fetch_records``.
3. Register it in ``config/sources.yml``.
4. Add ``transform/models/staging/<source>/`` models.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class RawRecord:
    """One record exactly as fetched from a source, plus provenance."""

    source: str
    record_id: str
    payload: dict[str, Any]
    fetched_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class Connector(ABC):
    """Base class for all source connectors."""

    #: Short, unique, snake_case name, e.g. "openalex", "dspace_oai".
    source_name: str = ""

    def __init__(self, config: dict[str, Any] | None = None) -> None:
        if not self.source_name:
            raise ValueError(f"{type(self).__name__} must set source_name")
        self.config = config or {}

    @abstractmethod
    def fetch_records(self) -> Iterator[tuple[str, dict[str, Any]]]:
        """Yield ``(record_id, payload)`` pairs from the source."""

    def fetch(self) -> Iterator[RawRecord]:
        """Yield raw records wrapped with source name and fetch time."""
        for record_id, payload in self.fetch_records():
            yield RawRecord(source=self.source_name, record_id=str(record_id), payload=payload)
