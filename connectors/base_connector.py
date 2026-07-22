"""Transport-level connector contract for external EduBid data sources."""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass
from time import perf_counter


@dataclass(frozen=True)
class ConnectorMetadata:
    key: str
    name: str
    profile_key: str
    description: str
    is_mock: bool = True


class BaseConnector(ABC):
    """Define the lifecycle shared by file and future API connectors.

    Connectors obtain and normalize source records only. Business services are
    injected through ``import_data`` implementations, keeping this package free
    of database and domain-service dependencies.
    """

    metadata: ConnectorMetadata

    def __init__(self):
        if not isinstance(getattr(self, "metadata", None), ConnectorMetadata):
            raise TypeError("connector metadata is required")
        self.connected = False

    @abstractmethod
    def connect(self):
        """Open the external file, session, or API transport."""

    @abstractmethod
    def disconnect(self):
        """Release connector resources. This method must be idempotent."""

    @abstractmethod
    def validate(self):
        """Validate configuration and source availability before fetching."""

    @abstractmethod
    def fetch(self) -> Iterable[dict]:
        """Return normalized transport records without persisting them."""

    @abstractmethod
    def import_data(self, records):
        """Pass fetched records to an injected importer and return counters."""

    def sync(self):
        """Execute connect → validate → fetch → import and always disconnect."""
        started = perf_counter()
        records = []
        try:
            self.connect()
            if self.validate() is not True:
                raise ValueError(f"connector validation failed: {self.metadata.key}")
            records = list(self.fetch())
            result = dict(self.import_data(records) or {})
            return {
                "connector": self.metadata.key,
                "source": self.metadata.name,
                "status": result.pop("status", "SUCCESS"),
                "fetched": len(records),
                "duration": perf_counter() - started,
                **result,
            }
        finally:
            self.disconnect()


class MockConnector(BaseConnector):
    """Deterministic no-write connector used until a remote adapter is enabled."""

    def __init__(self, records=None):
        super().__init__()
        self._records = [dict(record) for record in (records or [])]

    def connect(self):
        self.connected = True
        return self

    def disconnect(self):
        self.connected = False

    def validate(self):
        return self.connected

    def fetch(self):
        if not self.connected:
            raise RuntimeError("connector is not connected")
        return [dict(record) for record in self._records]

    def import_data(self, records):
        # Mock connectors deliberately make no business-service or database call.
        return {"status": "MOCK", "imported": 0, "skipped": len(records), "failed": 0}
