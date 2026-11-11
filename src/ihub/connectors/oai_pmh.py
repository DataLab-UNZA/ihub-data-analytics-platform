"""Shared OAI-PMH harvesting for every source that speaks OAI-PMH (DSpace, OJS).

:class:`OaiPmhHarvester` wraps Sickle, which follows resumption tokens. It only fetches:
each record comes back as a plain dictionary holding the OAI header, the metadata exactly
as the repository sent it (as Sickle parses it) and the record's XML. Connectors add their
own context (for example the journal path) and never clean the data.

Errors are reported as three kinds, so connectors can decide what to do:

- :class:`OaiPmhUnavailableError`: the endpoint does not speak OAI-PMH (HTTP 404, or a reply
  that is not XML). The OJS connector then falls back to the REST API.
- :class:`OaiPmhIncompleteError`: clearly fewer records arrived than the repository reported.
- :class:`OaiPmhError`: anything else that retrying will not fix.

Network errors are retried with exponential back-off, and HTTP 429 and 5xx replies are
retried by Sickle, honouring the server's ``Retry-After`` header.
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from typing import Any

import requests
from lxml import etree
from sickle import Sickle, oaiexceptions
from sickle.iterator import OAIItemIterator
from sickle.models import Identify, Record
from sickle.models import Set as OaiSet
from tenacity import (
    Retrying,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
    wait_none,
)

from ihub.connectors.tls import ca_bundle

logger = logging.getLogger(__name__)

#: How far below the repository's ``completeListSize`` the number of records may fall before
#: the harvest is treated as incomplete (the list can change a little during a harvest).
DEFAULT_MAX_SHORTFALL = 0.005
DEFAULT_TIMEOUT = 60
DEFAULT_ATTEMPTS = 5
#: Smallest wait in seconds between two tries of a request that failed on the network.
DEFAULT_RETRY_WAIT = 1.0
#: Seconds Sickle waits before retrying a 429 or 5xx reply that has no ``Retry-After`` header.
DEFAULT_RETRY_AFTER = 30
RETRY_STATUS_CODES = (429, 500, 502, 503, 504)
#: The root element of every OAI-PMH 2.0 reply.
OAI_PMH_ROOT = "{http://www.openarchives.org/OAI/2.0/}OAI-PMH"

#: Every error an OAI-PMH server can report inside a 200 reply, as Sickle raises them.
_OAI_PROTOCOL_ERRORS: tuple[type[Exception], ...] = (
    oaiexceptions.BadArgument,
    oaiexceptions.BadResumptionToken,
    oaiexceptions.BadVerb,
    oaiexceptions.CannotDisseminateFormat,
    oaiexceptions.IdDoesNotExist,
    oaiexceptions.NoMetadataFormat,
    oaiexceptions.NoSetHierarchy,
    oaiexceptions.OAIError,
)


class OaiPmhError(Exception):
    """A non-retryable OAI-PMH failure."""


class OaiPmhUnavailableError(OaiPmhError):
    """The endpoint does not answer OAI-PMH requests."""


class OaiPmhIncompleteError(OaiPmhError):
    """The harvest ended with clearly fewer records than the repository reported."""


class _NotOaiPmhReplyError(Exception):
    """A page that parsed but is not an OAI-PMH reply (for example an HTML error page)."""


#: Everything a harvest can raise that is translated into an :class:`OaiPmhError`.
_HARVEST_ERRORS = (
    requests.RequestException,
    etree.XMLSyntaxError,
    _NotOaiPmhReplyError,
    *_OAI_PROTOCOL_ERRORS,
)


class _CheckedItemIterator(OAIItemIterator):
    """Sickle's record iterator, refusing any page that is not an OAI-PMH reply.

    Without this check an HTML page would end the harvest quietly with no more records.
    """

    def _next_response(self) -> None:
        super()._next_response()
        if self.oai_response.xml.tag != OAI_PMH_ROOT:
            raise _NotOaiPmhReplyError


class _RetryingSickle(Sickle):
    """Sickle that also retries network errors (Sickle itself retries only HTTP codes)."""

    def __init__(self, endpoint: str, *, attempts: int, retry_wait: float, **kwargs: Any) -> None:
        super().__init__(endpoint, iterator=_CheckedItemIterator, **kwargs)
        self._retrying = Retrying(
            retry=retry_if_exception_type((requests.ConnectionError, requests.Timeout)),
            stop=stop_after_attempt(attempts),
            wait=wait_exponential(min=retry_wait, max=max(retry_wait, 30))
            if retry_wait > 0
            else wait_none(),
            reraise=True,
        )

    def harvest(self, **kwargs: Any) -> Any:
        return self._retrying(super().harvest, **kwargs)


def record_payload(record: Record) -> dict[str, Any]:
    """Return one OAI-PMH record as a JSON-ready dictionary, without changing its content."""
    header = record.header
    return {
        "identifier": header.identifier,
        "datestamp": header.datestamp,
        "set_specs": list(header.setSpecs),
        "deleted": bool(record.deleted),
        "metadata": {} if record.deleted else record.metadata,
        "xml": record.raw,
    }


def set_payload(oai_set: OaiSet) -> dict[str, Any]:
    """Return one OAI-PMH set as a JSON-ready dictionary, without changing its content."""
    return {"set_spec": oai_set.setSpec, "set_name": oai_set.setName, "xml": oai_set.raw}


class OaiPmhHarvester:
    """Harvest one OAI-PMH endpoint.

    Args:
        endpoint: The OAI-PMH base URL, e.g. ``https://repo.example/server/oai/request``.
        timeout: Seconds to wait for each HTTP response.
        attempts: How many times one request is tried before the harvest fails.
        retry_wait: Smallest wait in seconds between retries; ``0`` turns waiting off (tests).
        max_shortfall: See :data:`DEFAULT_MAX_SHORTFALL`.
        verify: ``True`` for the standard CA bundle, or the path of a bundle to use instead
            (see :func:`ihub.connectors.tls.ca_bundle`). Checking is never turned off.
    """

    def __init__(
        self,
        endpoint: str,
        *,
        timeout: float = DEFAULT_TIMEOUT,
        attempts: int = DEFAULT_ATTEMPTS,
        retry_wait: float = DEFAULT_RETRY_WAIT,
        max_shortfall: float = DEFAULT_MAX_SHORTFALL,
        verify: bool | str = True,
    ) -> None:
        if not endpoint:
            raise ValueError("An OAI-PMH endpoint URL is required")
        if verify is False:
            raise ValueError("Certificate checking cannot be turned off; add the CA instead")
        self.endpoint = endpoint
        self.max_shortfall = max_shortfall
        self._sickle = _RetryingSickle(
            endpoint,
            attempts=attempts,
            retry_wait=retry_wait,
            max_retries=attempts - 1,
            retry_status_codes=list(RETRY_STATUS_CODES),
            default_retry_after=DEFAULT_RETRY_AFTER if retry_wait > 0 else 0,
            timeout=timeout,
            verify=verify,
        )

    @classmethod
    def from_config(cls, endpoint: str, config: dict[str, Any]) -> OaiPmhHarvester:
        """Build a harvester for ``endpoint`` from a source's settings in ``sources.yml``.

        Reads ``timeout``, ``attempts``, ``retry_wait``, ``max_shortfall`` and
        ``ca_certificates`` (extra public CA files, for servers with an incomplete chain).
        """
        return cls(
            endpoint,
            timeout=float(config.get("timeout", DEFAULT_TIMEOUT)),
            attempts=int(config.get("attempts", DEFAULT_ATTEMPTS)),
            retry_wait=float(config.get("retry_wait", DEFAULT_RETRY_WAIT)),
            max_shortfall=float(config.get("max_shortfall", DEFAULT_MAX_SHORTFALL)),
            verify=ca_bundle(config.get("ca_certificates")),
        )

    def identify(self) -> dict[str, Any]:
        """Return the repository's ``Identify`` answer, or raise if it does not speak OAI-PMH."""
        try:
            response = self._sickle.harvest(verb="Identify")
            root_tag = response.xml.tag
        except requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else None
            if status == 404:
                raise OaiPmhUnavailableError(
                    f"{self.endpoint} returned HTTP 404 to Identify"
                ) from None
            raise OaiPmhError(f"{self.endpoint} returned HTTP {status} to Identify") from None
        except etree.XMLSyntaxError:
            root_tag = None
        except requests.RequestException as exc:
            raise OaiPmhError(f"{self.endpoint}: {type(exc).__name__}") from None
        # Sickle's parser recovers from broken markup, so an HTML page can parse as "XML".
        if root_tag != OAI_PMH_ROOT:
            raise OaiPmhUnavailableError(f"{self.endpoint} did not answer Identify with OAI-PMH")
        identify = Identify(response)
        return dict(identify)

    def list_records(
        self, metadata_prefix: str, set_spec: str | None = None
    ) -> Iterator[dict[str, Any]]:
        """Yield every record (deleted ones included, flagged) as :func:`record_payload` gives it.

        When the repository reports ``completeListSize``, the number of records received is
        checked against it at the end, so a silently truncated harvest raises instead of
        replacing a good load.
        """
        params: dict[str, Any] = {"metadataPrefix": metadata_prefix}
        if set_spec:
            params["set"] = set_spec
        label = f"{self.endpoint} ({metadata_prefix}{', set ' + set_spec if set_spec else ''})"
        for record in self._iterate("ListRecords", params, label):
            yield record_payload(record)

    def list_sets(self) -> Iterator[dict[str, Any]]:
        """Yield every set (in DSpace: a community or collection) as ``set_spec``, ``set_name``
        and its XML. A repository without sets yields nothing.
        """
        for item in self._iterate("ListSets", {}, f"{self.endpoint} (sets)"):
            yield set_payload(item)

    def _iterate(self, verb: str, params: dict[str, Any], label: str) -> Iterator[Any]:
        """Yield every item Sickle returns for ``verb``, translating errors and checking the
        number of items against ``completeListSize`` at the end."""
        try:
            items = getattr(self._sickle, verb)(**params)
        except (oaiexceptions.NoRecordsMatch, oaiexceptions.NoSetHierarchy):
            # The two OAI-PMH ways of saying "the list is empty".
            logger.info("OAI-PMH %s: nothing to harvest", label)
            return
        except _HARVEST_ERRORS as exc:
            raise self._translate(exc, label) from None

        received = 0
        expected: int | None = None
        while True:
            expected = self._complete_list_size(items) or expected
            try:
                item = next(items)
            except StopIteration:
                break
            except _HARVEST_ERRORS as exc:
                raise self._translate(exc, label) from None
            received += 1
            yield item
        self._check_complete(label, expected, received)

    @staticmethod
    def _complete_list_size(records: Any) -> int | None:
        token = getattr(records, "resumption_token", None)
        size = getattr(token, "complete_list_size", None)
        try:
            return int(size) if size not in (None, "") else None
        except ValueError:
            return None

    def _check_complete(self, label: str, expected: int | None, received: int) -> None:
        logger.info(
            "OAI-PMH %s: %s items received, %s expected",
            label,
            received,
            "unknown" if expected is None else expected,
        )
        if expected is not None and received < expected * (1 - self.max_shortfall):
            raise OaiPmhIncompleteError(
                f"{label} reported {expected} items but only {received} were received; "
                "the previous data has been left in place"
            )

    @staticmethod
    def _translate(exc: Exception, label: str) -> OaiPmhError:
        """Turn a Sickle, requests or lxml exception into an :class:`OaiPmhError`."""
        if isinstance(exc, requests.HTTPError):
            status = exc.response.status_code if exc.response is not None else None
            return OaiPmhError(f"{label} returned HTTP {status}")
        if isinstance(exc, etree.XMLSyntaxError | _NotOaiPmhReplyError):
            return OaiPmhError(f"{label} returned a reply that is not OAI-PMH")
        if isinstance(exc, requests.RequestException):
            return OaiPmhError(f"{label}: {type(exc).__name__}")
        return OaiPmhError(f"{label}: OAI-PMH error {type(exc).__name__}: {exc}")
