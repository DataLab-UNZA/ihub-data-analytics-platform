"""OpenAlex connector: pulls works with an author affiliated to the configured institution."""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ihub.connectors.base import Connector
from ihub.settings import get_settings

logger = logging.getLogger(__name__)

#: 100 is the supported maximum page size in the OpenAlex API.
PAGE_SIZE = 100

#: How far below OpenAlex's own count the number of distinct works may fall before the
#: fetch is treated as incomplete (the count can drift a little while a fetch is running).
DEFAULT_MAX_SHORTFALL = 0.005


class OpenAlexError(Exception):
    """A non-retryable OpenAlex failure.

    Messages never include the request URL (it may hold a key).
    """


class OpenAlexIncompleteError(OpenAlexError):
    """The fetch ended with clearly fewer distinct works than OpenAlex said match the filter."""


class OpenAlexTransientError(Exception):
    """A retryable failure: a network error, a rate limit (429) or a server error (5xx)."""


class OpenAlexConnector(Connector):
    """Fetch works from the OpenAlex API exactly as returned."""

    source_name = "openalex"

    def __init__(
        self, config: dict[str, Any] | None = None, client: httpx.Client | None = None
    ) -> None:
        super().__init__(config)
        self._client = client

    def _works_filter(self) -> str:
        """Return the ``filter`` parameter: the institution, and a start year only if configured."""
        institution = str(self.config.get("institution_id") or "").strip()
        if not institution:
            raise ValueError(
                "openalex.institution_id is not set in config/sources.yml; "
                "look it up in the OpenAlex API and verify it first"
            )
        institution = institution.rsplit("/", 1)[-1]
        filters = [f"authorships.institutions.id:{institution}"]
        year_from = self.config.get("year_from")
        if year_from is not None:
            filters.append(f"from_publication_date:{int(year_from)}-01-01")
        return ",".join(filters)

    @retry(
        retry=retry_if_exception_type(OpenAlexTransientError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(min=1, max=30),
        reraise=True,
    )
    def _get_page(self, client: httpx.Client, params: dict[str, Any]) -> dict[str, Any]:
        base_url = str(self.config.get("base_url", "https://api.openalex.org")).rstrip("/")
        try:
            response = client.get(f"{base_url}/works", params=params)
        except httpx.TransportError as exc:
            raise OpenAlexTransientError(f"Network error: {type(exc).__name__}") from None
        status = response.status_code
        if status == 429:
            raise OpenAlexTransientError(
                "OpenAlex returned HTTP 429 (rate limit or daily budget; "
                "a free API key raises the limit)"
            )
        if status >= 500:
            raise OpenAlexTransientError(f"OpenAlex returned HTTP {status}")
        if status >= 400:
            raise OpenAlexError(f"OpenAlex returned HTTP {status}")
        return response.json()

    def fetch_records(self) -> Iterator[tuple[str, dict[str, Any]]]:
        """Yield ``(OpenAlex work ID, work)`` pairs, following the API's cursor paging.

        Works are yielded exactly as received. OpenAlex can deliver the same work on two
        pages when its index changes mid-fetch, so duplicates are possible; the staging
        model keeps one row per work. When the fetch ends, the number of distinct works is
        checked against the count OpenAlex reported, so a silently truncated pull cannot
        replace a good one.
        """
        settings = get_settings()
        params: dict[str, Any] = {
            "filter": self._works_filter(),
            "per_page": PAGE_SIZE,
            "cursor": "*",
        }
        # OpenAlex leaves out "xpac" works (records it derives from repository and DataCite
        # metadata) unless asked; they are part of an institution's published works count.
        if self.config.get("include_xpac", True):
            params["include_xpac"] = "true"
        if settings.openalex_mailto:
            params["mailto"] = settings.openalex_mailto
        if settings.openalex_api_key:
            params["api_key"] = settings.openalex_api_key

        expected: int | None = None
        rows = 0
        seen: set[str] = set()
        client = self._client or httpx.Client(timeout=60)
        try:
            while True:
                body = self._get_page(client, params)
                meta = body.get("meta", {})
                if expected is None and isinstance(meta.get("count"), int):
                    expected = meta["count"]
                works = body.get("results", [])
                for work in works:
                    rows += 1
                    seen.add(str(work["id"]))
                    yield str(work["id"]), work
                cursor = meta.get("next_cursor")
                if not works or not cursor:
                    break
                params["cursor"] = cursor
        finally:
            if self._client is None:
                client.close()
        self._check_complete(expected, rows, len(seen))

    def _check_complete(self, expected: int | None, rows: int, distinct: int) -> None:
        """Log the fetch totals and raise if clearly fewer works arrived than expected."""
        logger.info(
            "OpenAlex: %s rows fetched, %s distinct works, %s expected",
            rows,
            distinct,
            "unknown" if expected is None else expected,
        )
        if expected is None:
            return
        max_shortfall = float(self.config.get("max_shortfall", DEFAULT_MAX_SHORTFALL))
        if distinct < expected * (1 - max_shortfall):
            raise OpenAlexIncompleteError(
                f"OpenAlex reported {expected} matching works but only {distinct} distinct "
                f"works were received; the previous data has been left in place"
            )
