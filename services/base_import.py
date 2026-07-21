"""Reusable interface for file-based data imports."""

import os
from abc import ABC, abstractmethod

from core.logger import get_logger
from services.import_history_service import ImportHistoryService


class BaseImport(ABC):
    """Define the common load, validation, preview, save, and audit lifecycle."""

    def __init__(self, source_type, filename, history_service=None):
        self.source_type = str(source_type or "").strip()
        self.filename = os.path.abspath(str(filename or "").strip())
        if not self.source_type:
            raise ValueError("source_type is required")
        if not str(filename or "").strip():
            raise ValueError("filename is required")
        self.history_service = history_service or ImportHistoryService
        self.logger = get_logger(f"import.{self.source_type}")

    @abstractmethod
    def load(self):
        """Load source data into memory or a streaming representation."""

    @abstractmethod
    def validate(self):
        """Validate loaded source data and return the validated representation."""

    @abstractmethod
    def preview(self, limit=20):
        """Return a bounded preview without persisting source rows."""

    @abstractmethod
    def save(self):
        """Persist validated rows and return the imported-row count or result."""

    def log(self, result, imported_rows=0):
        """Write one import result through the service and database layers."""
        history_id = self.history_service.record(
            source_type=self.source_type,
            filename=os.path.basename(self.filename),
            result=result,
            imported_rows=imported_rows,
        )
        self.logger.info(
            "Import recorded | source=%s | file=%s | result=%s | rows=%d",
            self.source_type,
            os.path.basename(self.filename),
            result,
            int(imported_rows or 0),
        )
        return history_id
