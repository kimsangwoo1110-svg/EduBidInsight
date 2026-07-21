"""Service boundary for the data-import audit trail."""

import os
from datetime import datetime

from services.database import add_import_history, find_import_history


IMPORT_HISTORY_FIELDS = (
    "id",
    "imported_at",
    "source_type",
    "filename",
    "result",
    "imported_rows",
)


class ImportHistoryService:
    """Validate, store, and query data-source import results."""

    @classmethod
    def record(
        cls,
        source_type,
        filename,
        result,
        imported_rows=0,
        imported_at=None,
    ):
        source = str(source_type or "").strip()
        selected_filename = os.path.basename(str(filename or "").strip())
        selected_result = str(result or "").strip()
        try:
            row_count = int(imported_rows or 0)
        except (TypeError, ValueError) as error:
            raise ValueError("imported_rows must be a non-negative integer") from error

        if not source:
            raise ValueError("source_type is required")
        if not selected_filename:
            raise ValueError("filename is required")
        if not selected_result:
            raise ValueError("result is required")
        if row_count < 0:
            raise ValueError("imported_rows must be a non-negative integer")

        timestamp = cls._timestamp(imported_at)
        return add_import_history(
            timestamp,
            source,
            selected_filename,
            selected_result,
            row_count,
        )

    @staticmethod
    def history(limit=100):
        return [
            dict(zip(IMPORT_HISTORY_FIELDS, row))
            for row in find_import_history(limit=limit)
        ]

    @staticmethod
    def _timestamp(value):
        if value is None:
            return datetime.now().astimezone().isoformat(timespec="seconds")
        if isinstance(value, datetime):
            return value.astimezone().isoformat(timespec="seconds")
        timestamp = str(value).strip()
        if not timestamp:
            raise ValueError("imported_at is required")
        return timestamp
