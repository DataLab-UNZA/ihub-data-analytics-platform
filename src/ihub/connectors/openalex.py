"""OpenAlex connector: pulls works with an author affiliated to the configured institution."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ihub.connectors.base import Connector
from ihub.settings import get_settings

#: 100 is the supported maximum page size in the OpenAlex API.
PAGE_SIZE = 100


class OpenAlexError(Exception):
    """A non-retryable OpenAlex failure.

    Messages never include the request URL (it may hold a key).
    """


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
        institution = str(self.config.get("institution_id") or "").strip()
        if not institution:
            raise ValueError(
                "openalex.institution_id is not set in config/sources.yml; "
                "look it up in the OpenAlex API and verify it first"
            )
        institution = institution.rsplit("/", 1)[-1]
        year_from = int(self.config.get("year_from", 2015))
        institution_filter = f"authorships.institutions.id:{institution}"
        date_filter = f"from_publication_date:{year_from}-01-01"
        return f"{institution_filter},{date_filter}"

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
        """Yield ``(OpenAlex work ID, work)`` pairs, following the API's cursor paging."""
        settings = get_settings()
        params: dict[str, Any] = {
            "filter": self._works_filter(),
            "per_page": PAGE_SIZE,
            "cursor": "*",
        }
        if settings.openalex_mailto:
            params["mailto"] = settings.openalex_mailto
        if settings.openalex_api_key:
            params["api_key"] = settings.openalex_api_key

        client = self._client or httpx.Client(timeout=60)
        try:
            while True:
                body = self._get_page(client, params)
                works = body.get("results", [])
                for work in works:
                    yield str(work["id"]), work
                cursor = body.get("meta", {}).get("next_cursor")
                if not works or not cursor:
                    break
                params["cursor"] = cursor
        finally:
            if self._client is None:
                client.close()
