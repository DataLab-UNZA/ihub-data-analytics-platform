"""Ingestion connectors: one module per source system."""

from ihub.connectors.base import Connector, RawRecord

__all__ = ["Connector", "RawRecord"]
