"""Synchronization orchestration, history, and connector registry."""

from datetime import datetime
from time import perf_counter

from core.logger import get_logger
from services.connectors.neis_school import NeisSchoolConnector
from services.database import (
    find_sync_history,
    finish_sync_history,
    start_sync_history,
)


SYNC_HISTORY_FIELDS = (
    "id",
    "source",
    "started_at",
    "finished_at",
    "inserted",
    "updated",
    "skipped",
    "errors",
    "duration",
    "status",
)
DEFAULT_SCHOOL_SOURCE = NeisSchoolConnector.source


class SyncService:
    """Run registered connectors and persist a complete audit trail."""

    _connector_factories = {NeisSchoolConnector.source: NeisSchoolConnector}
    DEFAULT_SCHOOL_SOURCE = DEFAULT_SCHOOL_SOURCE
    logger = get_logger("sync")

    @classmethod
    def register(cls, connector_factory, replace=False):
        connector = connector_factory()
        if connector.source in cls._connector_factories and not replace:
            raise ValueError(f"connector already registered: {connector.source}")
        cls._connector_factories[connector.source] = connector_factory

    @classmethod
    def unregister(cls, source):
        return cls._connector_factories.pop(source, None) is not None

    @classmethod
    def available_sources(cls):
        return sorted(cls._connector_factories)

    @classmethod
    def synchronize(cls, source, progress_callback=None):
        factory = cls._connector_factories.get(source)
        if factory is None:
            raise ValueError(f"unknown synchronization source: {source}")
        return cls.synchronize_connector(factory(), progress_callback)

    @classmethod
    def synchronize_connector(cls, connector, progress_callback=None):
        """Run a configured connector instance through history and logging."""
        if not getattr(connector, "source", ""):
            raise ValueError("connector source is required")
        started_at = cls._timestamp()
        history_id = start_sync_history(connector.source, started_at)
        timer_started = perf_counter()
        cls.logger.info("Synchronization started | source=%s", connector.source)

        try:
            raw_result = connector.synchronize(progress_callback)
            result = {
                key: max(0, int((raw_result or {}).get(key, 0) or 0))
                for key in ("inserted", "updated", "skipped", "errors")
            }
        except Exception:
            duration = perf_counter() - timer_started
            finished_at = cls._timestamp()
            finish_sync_history(
                history_id,
                finished_at,
                0,
                0,
                0,
                1,
                duration,
                "FAILED",
            )
            cls.logger.exception(
                "Synchronization failed | source=%s | duration=%.3f",
                connector.source,
                duration,
            )
            raise

        duration = perf_counter() - timer_started
        status = "PARTIAL" if result.get("errors", 0) else "SUCCESS"
        finished_at = cls._timestamp()
        finish_sync_history(
            history_id,
            finished_at,
            result.get("inserted", 0),
            result.get("updated", 0),
            result.get("skipped", 0),
            result.get("errors", 0),
            duration,
            status,
        )
        completed_result = {
            "history_id": history_id,
            "source": connector.source,
            "duration": duration,
            "status": status,
            **result,
        }
        cls.logger.info(
            "Synchronization finished | source=%s | status=%s | "
            "inserted=%d | updated=%d | skipped=%d | errors=%d | duration=%.3f",
            connector.source,
            status,
            completed_result["inserted"],
            completed_result["updated"],
            completed_result["skipped"],
            completed_result["errors"],
            duration,
        )
        return completed_result

    @staticmethod
    def history(limit=100):
        return [
            dict(zip(SYNC_HISTORY_FIELDS, row))
            for row in find_sync_history(limit=limit)
        ]

    @staticmethod
    def _timestamp():
        return datetime.now().astimezone().isoformat(timespec="seconds")
