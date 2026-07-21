"""Reusable lifecycle and result accounting for external data connectors."""

from abc import ABC, abstractmethod

from core.logger import get_logger


RESULT_KEYS = ("inserted", "updated", "skipped", "errors")


class BaseConnector(ABC):
    """Process external records through fetch, transform, and load stages."""

    source = ""

    def __init__(self):
        if not str(self.source or "").strip():
            raise ValueError("connector source is required")
        self.logger = get_logger(f"connector.{self.source}")
        self._progress_callback = None

    def open(self):
        """Allocate optional connector resources before fetching."""

    def close(self, success):
        """Release optional connector resources after processing."""

    @abstractmethod
    def fetch(self):
        """Yield source records."""

    def transform(self, record):
        """Normalize one source record before persistence."""
        return record

    @abstractmethod
    def load(self, record):
        """Persist one record and return inserted, updated, or skipped."""

    def synchronize(self, progress_callback=None):
        """Execute the standard connector lifecycle and return result counters."""
        result = {key: 0 for key in RESULT_KEYS}
        processed = 0
        self._progress_callback = progress_callback
        self.open()
        completed = False
        try:
            for source_record in self.fetch():
                try:
                    record = self.transform(source_record)
                    outcome = "skipped" if record is None else self.load(record)
                    self._merge_outcome(result, outcome)
                except Exception:
                    result["errors"] += 1
                    self.logger.exception("Record synchronization failed")
                processed += 1
                self.notify(stage="processing", processed=processed, **result)
            completed = True
            return result
        finally:
            self.close(completed)
            self._progress_callback = None

    def notify(self, **progress):
        if self._progress_callback is not None:
            self._progress_callback({"source": self.source, **progress})

    @staticmethod
    def _merge_outcome(result, outcome):
        if isinstance(outcome, str):
            if outcome not in {"inserted", "updated", "skipped"}:
                raise ValueError(f"unsupported connector outcome: {outcome}")
            result[outcome] += 1
            return
        if isinstance(outcome, dict):
            for key in RESULT_KEYS:
                result[key] += max(0, int(outcome.get(key, 0) or 0))
            return
        raise ValueError("connector load must return an outcome string or result mapping")
