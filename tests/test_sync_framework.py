import logging
import os
import sqlite3
import tempfile
import unittest
from contextlib import closing

from core.logger import LOG_FILE_NAME, configure_logging, get_logger
from gui.sync_manager import sync_history_values
from services import database
from services.connectors.base import BaseConnector
from services.sync_service import SyncService


class SampleConnector(BaseConnector):
    source = "TEST SAMPLE"

    def __init__(self, records=None, fail_fetch=False):
        self.records = records or []
        self.fail_fetch = fail_fetch
        self.closed_with = None
        super().__init__()

    def fetch(self):
        if self.fail_fetch:
            raise RuntimeError("source unavailable")
        yield from self.records

    def transform(self, record):
        if record == "empty":
            return None
        return record

    def load(self, record):
        if record == "error":
            raise ValueError("bad record")
        return record

    def close(self, success):
        self.closed_with = success


class BaseConnectorTest(unittest.TestCase):
    def test_connector_counts_results_errors_and_progress(self):
        connector = SampleConnector(["inserted", "updated", "skipped", "empty", "error"])
        progress = []

        result = connector.synchronize(progress.append)

        self.assertEqual(
            result,
            {"inserted": 1, "updated": 1, "skipped": 2, "errors": 1},
        )
        self.assertTrue(connector.closed_with)
        self.assertEqual(progress[-1]["processed"], 5)
        self.assertEqual(progress[-1]["source"], SampleConnector.source)

    def test_connector_closes_unsuccessfully_when_fetch_fails(self):
        connector = SampleConnector(fail_fetch=True)

        with self.assertRaises(RuntimeError):
            connector.synchronize()

        self.assertFalse(connector.closed_with)


class SyncDatabaseTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_db_name = database.DB_NAME
        database.DB_NAME = os.path.join(self.temp_directory.name, "sync.db")
        database.create_database()

    def tearDown(self):
        SyncService.unregister(SampleConnector.source)
        database.DB_NAME = self.original_db_name
        self.temp_directory.cleanup()

    def test_sync_service_records_success_and_history_values(self):
        SyncService.register(
            lambda: SampleConnector(["inserted", "updated", "skipped"]),
            replace=True,
        )

        result = SyncService.synchronize(SampleConnector.source)
        history = SyncService.history()[0]

        self.assertEqual(result["status"], "SUCCESS")
        self.assertEqual(history["inserted"], 1)
        self.assertEqual(history["updated"], 1)
        self.assertEqual(history["skipped"], 1)
        self.assertEqual(history["errors"], 0)
        self.assertEqual(history["status"], "SUCCESS")
        self.assertIsNotNone(history["finished_at"])
        self.assertEqual(sync_history_values(history)[-1], "SUCCESS")

    def test_sync_service_records_failed_source(self):
        SyncService.register(
            lambda: SampleConnector(fail_fetch=True),
            replace=True,
        )

        with self.assertRaises(RuntimeError):
            SyncService.synchronize(SampleConnector.source)

        history = SyncService.history()[0]
        self.assertEqual(history["status"], "FAILED")
        self.assertEqual(history["errors"], 1)
        self.assertIsNotNone(history["finished_at"])

    def test_sync_history_database_api(self):
        history_id = database.start_sync_history("MANUAL", "2026-07-21T10:00:00+09:00")
        self.assertTrue(
            database.finish_sync_history(
                history_id,
                "2026-07-21T10:00:02+09:00",
                2,
                3,
                4,
                1,
                2.25,
                "PARTIAL",
            )
        )

        row = database.find_sync_history(limit=1)[0]
        self.assertEqual(row[0], history_id)
        self.assertEqual(row[4:8], (2, 3, 4, 1))
        self.assertEqual(row[8], 2.25)
        self.assertEqual(row[9], "PARTIAL")


class DatabaseMigrationTest(unittest.TestCase):
    def test_existing_database_is_migrated_without_data_loss(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            original_db_name = database.DB_NAME
            database.DB_NAME = os.path.join(temp_directory, "legacy.db")
            try:
                with closing(sqlite3.connect(database.DB_NAME)) as connection, connection:
                    connection.execute(
                        """
                        CREATE TABLE schools(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            school_code TEXT UNIQUE,
                            school_name TEXT NOT NULL
                        )
                        """
                    )
                    connection.execute(
                        "INSERT INTO schools(school_code, school_name) VALUES ('S1', '기존학교')"
                    )

                database.create_database()
                with closing(database.get_connection()) as connection:
                    columns = [
                        row[1]
                        for row in connection.execute("PRAGMA table_info(sync_history)")
                    ]
                    school = connection.execute(
                        "SELECT school_name FROM schools WHERE school_code = 'S1'"
                    ).fetchone()

                self.assertEqual(
                    columns,
                    [
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
                    ],
                )
                self.assertEqual(school, ("기존학교",))
            finally:
                database.DB_NAME = original_db_name


class ApplicationLoggingTest(unittest.TestCase):
    def test_application_log_is_written_in_utf8(self):
        with tempfile.TemporaryDirectory() as temp_directory:
            logger = configure_logging(temp_directory, logging.INFO, force=True)
            get_logger("test").info("동기화 로그 테스트")
            for handler in logger.handlers:
                handler.flush()

            log_path = os.path.join(temp_directory, LOG_FILE_NAME)
            self.assertTrue(os.path.exists(log_path))
            with open(log_path, encoding="utf-8") as log_file:
                self.assertIn("동기화 로그 테스트", log_file.read())

            configure_logging("logs", logging.INFO, force=True)


if __name__ == "__main__":
    unittest.main()
