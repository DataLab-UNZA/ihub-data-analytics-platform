"""DSpace connector: harvests the UNZA Institutional Repository (IRIM) over OAI-PMH.

Two kinds of raw record are written, told apart by ``record_type``:

- ``item``: every item, deleted ones included (flagged ``deleted``), exactly as sent;
- ``set``: every community and collection (``setSpec`` and name), so staging can attribute an
  item to a school or department through the ``set_specs`` in its header.

The staging layer decides what to use. Settings come from the ``dspace_oai`` block of
``config/sources.yml``:

- ``oai_endpoint`` (required): the OAI-PMH base URL, confirmed in issue #12;
- ``harvest_sets``: also harvest the community and collection names (``true`` by default);
- ``metadata_prefix``: ``oai_dc`` by default (``dim`` or ``qdc`` hold richer department data);
- ``sets``: optional list of setSpecs (communities or collections) to harvest; everything by
  default;
- ``timeout``, ``attempts``, ``retry_wait``, ``max_shortfall``: see
  :class:`ihub.connectors.oai_pmh.OaiPmhHarvester`.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Any

from ihub.connectors.base import Connector
from ihub.connectors.oai_pmh import OaiPmhHarvester

DEFAULT_METADATA_PREFIX = "oai_dc"
RECORD_TYPE_ITEM = "item"
RECORD_TYPE_SET = "set"


class DSpaceOaiConnector(Connector):
    """Fetch every record of a DSpace repository over OAI-PMH, exactly as returned."""

    source_name = "dspace_oai"

    def __init__(
        self, config: dict[str, Any] | None = None, harvester: OaiPmhHarvester | None = None
    ) -> None:
        super().__init__(config)
        self._harvester = harvester

    def _endpoint(self) -> str:
        endpoint = str(self.config.get("oai_endpoint") or "").strip()
        if not endpoint:
            raise ValueError(
                "dspace_oai.oai_endpoint is not set in config/sources.yml; "
                "confirm the repository's OAI-PMH endpoint first (issue #12)"
            )
        return endpoint

    def _harvester_for_run(self) -> OaiPmhHarvester:
        if self._harvester is not None:
            return self._harvester
        return OaiPmhHarvester.from_config(self._endpoint(), self.config)

    def fetch_records(self) -> Iterator[tuple[str, dict[str, Any]]]:
        """Yield ``(record id, record)`` pairs: the sets first, then the items of every set.

        Items are keyed by OAI identifier and sets by ``set:<setSpec>``. An item that sits in
        two harvested sets is yielded twice; the staging model keeps one row per identifier.
        """
        harvester = self._harvester_for_run()
        if self.config.get("harvest_sets", True):
            for oai_set in harvester.list_sets():
                yield f"set:{oai_set['set_spec']}", {"record_type": RECORD_TYPE_SET, **oai_set}
        prefix = str(self.config.get("metadata_prefix") or DEFAULT_METADATA_PREFIX)
        set_specs: list[str | None] = list(self.config.get("sets") or []) or [None]
        for set_spec in set_specs:
            for payload in harvester.list_records(prefix, set_spec=set_spec):
                record = {"record_type": RECORD_TYPE_ITEM, "metadata_prefix": prefix, **payload}
                yield str(payload["identifier"]), record
