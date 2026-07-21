import os
import sqlite3
import tempfile
import unittest
from contextlib import closing

from gui.data_source_manager import import_history_values
from services import database
from services.base_import import BaseImport
from services.import_history_service import ImportHistoryService


class SampleImport(BaseImport):
    def load(self):
        return [{"value": 1}]

    def validate(self):
        return True

    def preview(self, limit=20):
        return self.load()[:limit]

    def save(self):
        return len(self.load())


class DataSourceManagerTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.original_db_name = database.DB_NAME
        database.DB_NAME = os.path.join(self.temp_directory.name, "imports.db")
        database.create_database()

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        self.temp_directory.cleanup()

    def test_import_history_service_records_and_lists_newest_first(self):
        first_id = ImportHistoryService.record(
            "계약 파일", "C:/imports/first.csv", "SUCCESS", 12,
            imported_at="2026-07-21T10:00:00+09:00",
        )
        second_id = ImportHistoryService.record(
            "학교 파일", "second.xlsx", "PARTIAL", 3,
            imported_at="2026-07-21T11:00:00+09:00",
        )

        history = ImportHistoryService.history()

        self.assertEqual([item["id"] for item in history], [second_id, first_id])
        self.assertEqual(history[1]["filename"], "first.csv")
        self.assertEqual(history[1]["imported_rows"], 12)
        self.assertEqual(
            import_history_values(history[0])[-2:], ("PARTIAL", 3)
        )

    def test_base_import_defines_lifecycle_and_logs_through_service(self):
        importer = SampleImport("테스트", "sample.csv")

        self.assertEqual(importer.preview(), [{"value": 1}])
        history_id = importer.log("SUCCESS", importer.save())

        self.assertEqual(ImportHistoryService.history()[0]["id"], history_id)
        self.assertEqual(ImportHistoryService.history()[0]["imported_rows"], 1)

    def test_import_history_validation(self):
        with self.assertRaises(ValueError):
            ImportHistoryService.record("", "file.csv", "SUCCESS", 1)
        with self.assertRaises(ValueError):
            ImportHistoryService.record("source", "file.csv", "SUCCESS", -1)

    def test_import_history_migration_preserves_existing_data(self):
        legacy_path = os.path.join(self.temp_directory.name, "legacy.db")
        database.DB_NAME = legacy_path
        with closing(sqlite3.connect(legacy_path)) as connection, connection:
            connection.execute(
                "CREATE TABLE schools(id INTEGER PRIMARY KEY, school_name TEXT)"
            )
            connection.execute("INSERT INTO schools VALUES (1, '기존학교')")

        database.create_database()

        with closing(database.get_connection()) as connection:
            columns = [
                row[1]
                for row in connection.execute("PRAGMA table_info(import_history)")
            ]
            school = connection.execute("SELECT school_name FROM schools").fetchone()
        self.assertEqual(
            columns,
            ["id", "imported_at", "source_type", "filename", "result", "imported_rows"],
        )
        self.assertEqual(school, ("기존학교",))


if __name__ == "__main__":
    unittest.main()
