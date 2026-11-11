"""OJS connector: harvests the articles of every configured UNZA journal.

Each journal is harvested by OAI-PMH (``<base_url>/index.php/<journal>/oai``) through the
shared :class:`~ihub.connectors.oai_pmh.OaiPmhHarvester`. Only when a journal's OAI-PMH
endpoint is unavailable (HTTP 404, or a reply that is not OAI-PMH) is the OJS REST API used
instead, which needs ``OJS_API_TOKEN``. Every record keeps its journal path and how it was
harvested (``harvest_method``), and is otherwise exactly as OJS returned it.

Settings come from the ``ojs`` block of ``config/sources.yml``: ``base_url``, ``journals``
(the journal paths), ``metadata_prefix`` (``oai_dc`` by default), ``page_size`` for the
REST API, ``ca_certificates`` (public intermediate certificates the server leaves out of its
chain; see :mod:`ihub.connectors.tls`) and the harvest settings of
:class:`~ihub.connectors.oai_pmh.OaiPmhHarvester`.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Iterator
from typing import Any

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from ihub.connectors.base import Connector
from ihub.connectors.oai_pmh import OaiPmhHarvester, OaiPmhUnavailableError
from ihub.connectors.tls import ssl_context
from ihub.settings import get_settings

logger = logging.getLogger(__name__)

DEFAULT_METADATA_PREFIX = "oai_dc"
#: 100 is the largest page the OJS REST API returns.
REST_PAGE_SIZE = 100
HARVEST_OAI_PMH = "oai_pmh"
HARVEST_REST_API = "rest_api"

#: Builds the OAI-PMH harvester for one journal's endpoint URL.
HarvesterFactory = Callable[[str], OaiPmhHarvester]


class OjsError(Exception):
    """A non-retryable OJS failure. Messages never include the API token."""


class OjsTransientError(Exception):
    """A retryable REST API failure: a network error, a rate limit (429) or a server error."""


class OjsRestApi:
    """Read the published issues and articles of one OJS installation through its REST API.

    Args:
        base_url: The OJS site, e.g. ``https://journals.unza.zm``.
        token: An OJS API token; it is sent as a ``Bearer`` header, never in the URL.
        client: The HTTP client to use (tests pass one with recorded responses).
        page_size: Issues requested per page (at most 100).
    """

    def __init__(
        self,
        base_url: str,
        token: str,
        client: httpx.Client,
        page_size: int = REST_PAGE_SIZE,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {"Accept": "application/json", "Authorization": f"Bearer {token}"}
        self._client = client
        self._page_size = min(int(page_size), REST_PAGE_SIZE)

    @retry(
        retry=retry_if_exception_type(OjsTransientError),
        stop=stop_after_attempt(5),
        wait=wait_exponential(min=1, max=30),
        reraise=True,
    )
    def _get(self, journal: str, path: str, params: dict[str, Any] | None = None) -> Any:
        url = f"{self._base_url}/index.php/{journal}/api/v1/{path}"
        try:
            response = self._client.get(url, params=params, headers=self._headers)
        except httpx.TransportError as exc:
            raise OjsTransientError(f"Network error: {type(exc).__name__}") from None
        status = response.status_code
        if status == 429 or status >= 500:
            raise OjsTransientError(f"OJS REST API returned HTTP {status} for {journal}")
        if status in (401, 403):
            raise OjsError(
                f"OJS REST API refused {journal} (HTTP {status}); "
                "check that OJS_API_TOKEN belongs to a user of that journal"
            )
        if status >= 400:
            raise OjsError(f"OJS REST API returned HTTP {status} for {journal}/{path}")
        return response.json()

    def published_issues(self, journal: str) -> Iterator[dict[str, Any]]:
        """Yield every published issue summary of ``journal``, paging with count and offset."""
        offset = 0
        expected: int | None = None
        while True:
            body = self._get(
                journal,
                "issues",
                {"isPublished": "true", "count": self._page_size, "offset": offset},
            )
            items = body.get("items") or []
            if expected is None and isinstance(body.get("itemsMax"), int):
                expected = body["itemsMax"]
            yield from items
            offset += len(items)
            if not items or (expected is not None and offset >= expected):
                break
        if expected is not None and offset < expected:
            raise OjsError(
                f"OJS REST API listed {expected} issues for {journal} but returned {offset}; "
                "the previous data has been left in place"
            )

    def published_articles(self, journal: str) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
        """Yield ``(issue, article)`` pairs for every article in every published issue.

        ``issue`` is the full issue without its ``articles`` list; ``article`` is unchanged.
        """
        for summary in self.published_issues(journal):
            issue = self._get(journal, f"issues/{summary['id']}")
            articles = issue.get("articles") or []
            issue_fields = {key: value for key, value in issue.items() if key != "articles"}
            for article in articles:
                yield issue_fields, article


class OjsConnector(Connector):
    """Fetch the articles of every configured OJS journal, exactly as returned."""

    source_name = "ojs"

    def __init__(
        self,
        config: dict[str, Any] | None = None,
        harvester_factory: HarvesterFactory | None = None,
        rest_api: OjsRestApi | None = None,
    ) -> None:
        super().__init__(config)
        self._harvester_factory = harvester_factory or (
            lambda endpoint: OaiPmhHarvester.from_config(endpoint, self.config)
        )
        self._rest_api = rest_api

    def _base_url(self) -> str:
        base_url = str(self.config.get("base_url") or "").strip().rstrip("/")
        if not base_url:
            raise ValueError("ojs.base_url is not set in config/sources.yml")
        return base_url

    def _journals(self) -> list[str]:
        journals = [str(journal).strip() for journal in self.config.get("journals") or []]
        if not journals or not all(journals):
            raise ValueError("ojs.journals in config/sources.yml must list the journal paths")
        # OJS matches journal paths without regard to case, so "zjh" and "ZJH" are one journal.
        if len({journal.lower() for journal in journals}) != len(journals):
            raise ValueError("ojs.journals in config/sources.yml lists a journal twice")
        return journals

    def oai_endpoint(self, journal: str) -> str:
        """Return the OAI-PMH endpoint of ``journal``."""
        return f"{self._base_url()}/index.php/{journal}/oai"

    def fetch_records(self) -> Iterator[tuple[str, dict[str, Any]]]:
        """Yield ``(record id, record)`` pairs for every article of every configured journal."""
        base_url = self._base_url()
        journals = self._journals()
        # The REST API is only set up if a journal needs it, and only for this run.
        rest_api = self._rest_api
        owned_client: httpx.Client | None = None
        try:
            for journal in journals:
                harvester = self._harvester_factory(self.oai_endpoint(journal))
                try:
                    harvester.identify()
                except OaiPmhUnavailableError as exc:
                    logger.info("OJS %s: %s; using the REST API instead", journal, exc)
                    if rest_api is None:
                        owned_client = httpx.Client(
                            timeout=60, verify=ssl_context(self.config.get("ca_certificates"))
                        )
                        rest_api = self._default_rest_api(base_url, journal, owned_client)
                    yield from self._rest_records(rest_api, journal)
                else:
                    yield from self._oai_records(harvester, journal)
        finally:
            if owned_client is not None:
                owned_client.close()

    def _default_rest_api(self, base_url: str, journal: str, client: httpx.Client) -> OjsRestApi:
        token = get_settings().ojs_api_token
        if not token:
            raise OjsError(
                f"{journal} has no OAI-PMH endpoint, so it needs the OJS REST API, "
                "but OJS_API_TOKEN is not set"
            )
        page_size = int(self.config.get("page_size", REST_PAGE_SIZE))
        return OjsRestApi(base_url, token, client, page_size=page_size)

    def _oai_records(
        self, harvester: OaiPmhHarvester, journal: str
    ) -> Iterator[tuple[str, dict[str, Any]]]:
        prefix = str(self.config.get("metadata_prefix") or DEFAULT_METADATA_PREFIX)
        for payload in harvester.list_records(prefix):
            record = {
                "journal": journal,
                "harvest_method": HARVEST_OAI_PMH,
                "metadata_prefix": prefix,
                **payload,
            }
            yield str(payload["identifier"]), record

    @staticmethod
    def _rest_records(api: OjsRestApi, journal: str) -> Iterator[tuple[str, dict[str, Any]]]:
        for issue, article in api.published_articles(journal):
            record = {
                "journal": journal,
                "harvest_method": HARVEST_REST_API,
                "issue": issue,
                "article": article,
            }
            yield f"ojs:{journal}:article/{article['id']}", record
