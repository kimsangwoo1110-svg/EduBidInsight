"""Transactional import workflow used by the smart import wizard."""

import json
import os
import threading
from contextlib import closing
from datetime import datetime
from time import perf_counter

from services import database
from services.base_import import BaseImport, ImportCancelled
from services.connectors.base import RESULT_KEYS
from services.connectors.contract_import import ContractImportConnector
from services.contract_service import ContractService


DEFAULT_MAPPING_PATH = os.path.join("config", "import_mappings.json")


class MappingStore:
    """Persist reusable mappings in a small, human-readable JSON file."""

    def __init__(self, path=DEFAULT_MAPPING_PATH):
        self.path = os.path.abspath(path)

    def load(self, name="contract"):
        try:
            with open(self.path, encoding="utf-8") as mapping_file:
                mappings = json.load(mapping_file)
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            return {}
        selected = mappings.get(name, {})
        return dict(selected) if isinstance(selected, dict) else {}

    def save(self, mapping, name="contract"):
        mappings = {}
        try:
            with open(self.path, encoding="utf-8") as mapping_file:
                loaded = json.load(mapping_file)
                if isinstance(loaded, dict):
                    mappings = loaded
        except (FileNotFoundError, json.JSONDecodeError, OSError):
            pass
        mappings[name] = dict(mapping)
        directory = os.path.dirname(self.path)
        if directory:
            os.makedirs(directory, exist_ok=True)
        temporary_path = f"{self.path}.tmp"
        with open(temporary_path, "w", encoding="utf-8") as mapping_file:
            json.dump(mappings, mapping_file, ensure_ascii=False, indent=2)
        os.replace(temporary_path, self.path)


class SmartContractImport(BaseImport):
    """Preview and atomically import a mapped contract file."""

    def __init__(
        self,
        filename,
        sheet_name=None,
        mapping=None,
        history_service=None,
        cancel_event=None,
    ):
        super().__init__(ContractImportConnector.source, filename, history_service)
        self.connector = ContractImportConnector(filename, sheet_name, mapping)
        self.cancel_event = cancel_event or threading.Event()
        self._loaded = None

    def load(self):
        if self._loaded is None:
            self._loaded = list(self.connector.fetch())
        return self._loaded

    def validate(self):
        validated = []
        for row_number, source_row in enumerate(self.load(), start=2):
            try:
                validated.append(
                    {
                        "row_number": row_number,
                        "contract": self.connector.transform(source_row),
                        "error": "",
                    }
                )
            except (TypeError, ValueError) as error:
                validated.append(
                    {"row_number": row_number, "contract": None, "error": str(error)}
                )
        return validated

    def preview(self, limit=100):
        return self.connector.preview(limit=min(100, max(0, int(limit))))

    def cancel(self):
        self.cancel_event.set()

    def save(self, progress_callback=None):
        """Save all valid rows in one transaction, rolling back on cancellation."""
        rows = self.validate()
        total = len(rows)
        result = {key: 0 for key in RESULT_KEYS}
        warnings = []
        with closing(database.get_connection()) as connection:
            try:
                connection.execute("BEGIN")
                for processed, row in enumerate(rows, start=1):
                    if self.cancel_event.is_set():
                        raise ImportCancelled()
                    if row["error"]:
                        result["errors"] += 1
                        warnings.append(f"Row {row['row_number']}: {row['error']}")
                    else:
                        contract_id = ContractService.save(
                            connection=connection,
                            commit=False,
                            **row["contract"],
                        )
                        result["inserted" if contract_id is not None else "skipped"] += 1
                    if progress_callback:
                        progress_callback(
                            stage="Importing...",
                            processed=processed,
                            total=total,
                            percentage=round(processed * 100 / total) if total else 100,
                        )
                if self.cancel_event.is_set():
                    raise ImportCancelled()
                if progress_callback:
                    progress_callback(
                        stage="Saving...", processed=total, total=total, percentage=100
                    )
                connection.commit()
            except BaseException:
                connection.rollback()
                raise
        result["warnings"] = warnings
        return result

    def run(self, progress_callback=None):
        """Execute the complete audited workflow and return a summary."""
        started = datetime.now().astimezone()
        timer = perf_counter()
        result = {key: 0 for key in RESULT_KEYS}
        warnings = []
        status = "FAILED"
        exception_text = ""
        try:
            self._notify(progress_callback, "Reading file...", 0, 0, 0)
            self.load()
            total = len(self._loaded)
            self._notify(progress_callback, "Validating...", 0, total, 0)
            result = self.save(progress_callback)
            warnings = result.pop("warnings", [])
            status = "PARTIAL" if result["errors"] else "SUCCESS"
        except ImportCancelled:
            status = "Cancelled"
            result = {key: 0 for key in RESULT_KEYS}
            warnings = ["Import cancelled by user; all changes were rolled back."]
        except Exception as error:
            exception_text = f"{type(error).__name__}: {error}"
            warnings = [exception_text]
            self.logger.exception("Smart import failed")
        elapsed = perf_counter() - timer
        finished = datetime.now().astimezone()
        self.log(status, result["inserted"])
        summary = {
            "status": status,
            "started_at": started.isoformat(timespec="seconds"),
            "finished_at": finished.isoformat(timespec="seconds"),
            "elapsed": elapsed,
            "imported": result["inserted"],
            "skipped": result["skipped"],
            "failed": result["errors"],
            "warnings": warnings,
            "cancelled": status == "Cancelled",
            "exception": exception_text,
        }
        self.logger.info(
            "Smart import finished | start=%s | finish=%s | elapsed=%.3f | "
            "warnings=%d | cancelled=%s | exception=%s",
            summary["started_at"], summary["finished_at"], elapsed,
            len(warnings), summary["cancelled"], exception_text or "none",
        )
        return summary

    @staticmethod
    def _notify(callback, stage, processed, total, percentage):
        if callback:
            callback(
                stage=stage,
                processed=processed,
                total=total,
                percentage=percentage,
            )


def format_import_summary(summary):
    """Create clipboard-ready text from a completed import summary."""
    warnings = summary.get("warnings") or []
    warning_text = "\n".join(f"- {warning}" for warning in warnings) or "None"
    schoolmarket_details = ""
    if "duplicates" in summary:
        categories = summary.get("category_summary") or {}
        category_text = ", ".join(
            f"{category}: {count:,}" for category, count in categories.items()
        ) or "None"
        schoolmarket_details = (
            f"Duplicates: {int(summary.get('duplicates', 0) or 0):,}\n"
            f"School match rate: {float(summary.get('school_match_rate', 0) or 0):.1f}%\n"
            f"Category summary: {category_text}\n"
        )
    return (
        f"Status: {summary.get('status', '')}\n"
        f"Imported rows: {int(summary.get('imported', 0) or 0):,}\n"
        f"Skipped rows: {int(summary.get('skipped', 0) or 0):,}\n"
        f"Failed rows: {int(summary.get('failed', 0) or 0):,}\n"
        f"{schoolmarket_details}"
        f"Elapsed time: {float(summary.get('elapsed', 0) or 0):.2f}s\n"
        f"Warnings:\n{warning_text}"
    )
