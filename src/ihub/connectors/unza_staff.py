"""Connector for UNZA's public staff list: a published Google Sheet CSV (ADR-017).

The list holds only what UNZA already publishes about its academic staff: names, title,
occupation and school. Everything a connector fetches ends up in the public data release (the
``raw_*`` schemas are part of ``ihub.duckdb``), so this connector keeps **only** the public
columns below and drops any other column the sheet may gain, such as a staff ID. Dropping a
column is the one exception to "connectors never clean data": it is a privacy guard, not a
clean-up, and it is logged by column name only.

The sheet's address is the ``UNZA_STAFF_LIST_URL`` setting. Without it the connector fetches
nothing, so the pipeline still runs and the Members directory stays empty.
"""

from __future__ import annotations

import csv
import hashlib
import io
import logging
from collections.abc import Iterator
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ihub.connectors.base import Connector
from ihub.settings import get_settings

logger = logging.getLogger(__name__)

#: The only columns that may leave this connector. All are published by UNZA itself.
PUBLIC_COLUMNS: tuple[str, ...] = (
    "Surname",
    "First Name",
    "Second Name",
    "Title",
    "Occupation",
    "School",
)


class UnzaStaffError(Exception):
    """The staff list could not be read (wrong address, or not a CSV with a Surname column)."""


class UnzaStaffConnector(Connector):
    """Fetches the public staff list, one record per staff row."""

    source_name = "unza_staff"

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        client: httpx.Client | None = None,
        url: str | None = None,
    ) -> None:
        super().__init__(config)
        self._client = client
        self._url = url if url is not None else get_settings().unza_staff_list_url

    @retry(
        retry=retry_if_exception_type(httpx.TransportError),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, max=10),
        reraise=True,
    )
    def _download(self, client: httpx.Client, url: str) -> str:
        response = client.get(url, follow_redirects=True, timeout=60)
        response.raise_for_status()
        response.encoding = "utf-8"
        return response.text

    def fetch_records(self) -> Iterator[tuple[str, dict[str, Any]]]:
        """Yield ``(record_id, row)`` with the public columns only, in the sheet's order.

        The record ID is a hash of the row, because the public list has no identifier. Two
        identical rows (two people with the same name, title and school) get different IDs,
        so they are never merged into one person.
        """
        url = (self._url or "").strip()
        if not url:
            logger.warning("unza_staff: UNZA_STAFF_LIST_URL is not set; nothing fetched.")
            return
        client = self._client or httpx.Client()
        try:
            text = self._download(client, url)
        finally:
            if self._client is None:
                client.close()
        reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
        header = [name.strip() for name in reader.fieldnames or []]
        if "Surname" not in header:
            raise UnzaStaffError("The staff list is not a CSV with a Surname column.")
        dropped = [name for name in header if name and name not in PUBLIC_COLUMNS]
        if dropped:
            logger.warning("unza_staff: dropped non-public columns: %s", ", ".join(dropped))
        seen: dict[str, int] = {}
        for row in reader:
            clean = {key.strip(): value for key, value in row.items() if key}
            public = {column: (clean.get(column) or "").strip() for column in PUBLIC_COLUMNS}
            if not any(public.values()):
                continue
            digest = hashlib.sha256(
                "\x1f".join(public[column] for column in PUBLIC_COLUMNS).encode("utf-8")
            ).hexdigest()[:16]
            seen[digest] = seen.get(digest, 0) + 1
            suffix = f"-{seen[digest]}" if seen[digest] > 1 else ""
            yield f"staff:{digest}{suffix}", public
