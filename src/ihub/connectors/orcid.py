"""ORCID connector: pulls works and employment records for UNZA-affiliated ORCID iDs.

The iDs come from an ORCID search (by default on UNZA's ROR ID). For each iD the connector
fetches the ``works`` and ``employments`` summaries exactly as the public API returns them.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ihub.connectors.base import Connector
from ihub.settings import get_settings

#: Number of iDs requested per search page (the ORCID search returns at most 1000).
PAGE_SIZE = 200
DEFAULT_TOKEN_URL = "https://orcid.org/oauth/token"
DEFAULT_BASE_URL = "https://pub.orcid.org/v3.0"
TOKEN_SCOPE = "/read-public"


class OrcidError(Exception):
    """A non-retryable ORCID failure.

    Messages never include request URLs, request bodies or credentials.
    """


class OrcidTransientError(Exception):
    """A retryable failure: a network error, a rate limit (429) or a server error (5xx)."""


class OrcidConnector(Connector):
    """Fetch works and employments for UNZA ORCID iDs, exactly as returned."""

    source_name = "orcid"

    def __init__(
        self, config: dict[str, Any] | None = None, client: httpx.Client | None = None
    ) -> None:
        super().__init__(config)
        self._client = client

    def _search_query(self) -> str:
        query = str(self.config.get("search_query") or "").strip()
        if not query:
            raise ValueError("orcid.search_query is not set in config/sources.yml")
        return query

    @retry(
        retry=retry_if_exception_type(OrcidTransientError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(min=1, max=30),
        reraise=True,
    )
    def _request(self, client: httpx.Client, method: str, url: str, **kwargs: Any) -> Any:
        try:
            response = client.request(method, url, **kwargs)
        except httpx.TransportError as exc:
            raise OrcidTransientError(f"Network error: {type(exc).__name__}") from None
        status = response.status_code
        if status == 429 or status >= 500:
            raise OrcidTransientError(f"ORCID returned HTTP {status}")
        if status >= 400:
            raise OrcidError(f"ORCID returned HTTP {status}")
        return response.json()

    def _get_token(self, client: httpx.Client) -> str:
        settings = get_settings()
        if not settings.orcid_client_id or not settings.orcid_client_secret:
            raise ValueError("ORCID_CLIENT_ID and ORCID_CLIENT_SECRET must be set")
        token_url = str(self.config.get("token_url", DEFAULT_TOKEN_URL))
        body = self._request(
            client,
            "POST",
            token_url,
            data={
                "client_id": settings.orcid_client_id,
                "client_secret": settings.orcid_client_secret,
                "grant_type": "client_credentials",
                "scope": TOKEN_SCOPE,
            },
            headers={"Accept": "application/json"},
        )
        return str(body["access_token"])

    def _search_ids(
        self, client: httpx.Client, base_url: str, headers: dict[str, str]
    ) -> Iterator[str]:
        """Yield every ORCID iD matching the search query, paging with ``start`` and ``rows``."""
        query = self._search_query()
        rows = int(self.config.get("page_size", PAGE_SIZE))
        start = 0
        while True:
            body = self._request(
                client,
                "GET",
                f"{base_url}/search/",
                params={"q": query, "start": start, "rows": rows},
                headers=headers,
            )
            results = body.get("result") or []
            for item in results:
                yield str(item["orcid-identifier"]["path"])
            start += len(results)
            if not results or start >= int(body.get("num-found", 0)):
                break

    def fetch_records(self) -> Iterator[tuple[str, dict[str, Any]]]:
        """Yield ``(ORCID iD, {"orcid", "works", "employments"})`` pairs."""
        base_url = str(self.config.get("base_url", DEFAULT_BASE_URL)).rstrip("/")
        self._search_query()  # fail early, before any network call
        client = self._client or httpx.Client(timeout=60)
        try:
            token = self._get_token(client)
            headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
            for orcid_id in self._search_ids(client, base_url, headers):
                works = self._request(
                    client, "GET", f"{base_url}/{orcid_id}/works", headers=headers
                )
                employments = self._request(
                    client, "GET", f"{base_url}/{orcid_id}/employments", headers=headers
                )
                yield orcid_id, {"orcid": orcid_id, "works": works, "employments": employments}
        finally:
            if self._client is None:
                client.close()
