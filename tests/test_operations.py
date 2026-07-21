import json
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.app_settings import AppSettings
from core.logger import configure_logging, get_logger
from services import database
from services.backup_service import BackupService
from services.diagnostics_service import DiagnosticsService
from services.migration_service import MigrationError, MigrationService
from services.release_validator import ReleaseValidator


class SettingsTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)
        self.settings_path = self.root / "config" / "settings.json"

    def tearDown(self):
        self.temp_directory.cleanup()

    def test_settings_persist_and_recent_files_are_bounded(self):
        settings = AppSettings(
            settings_path=self.settings_path, app_root=self.root, portable=True
        )
        settings.update({
            "theme": "Dark", "window_size": "1280x720",
            "auto_refresh_interval": 600,
        })
        for index in range(12):
            settings.add_recent_file(self.root / f"file-{index}.csv")
        saved = settings.save()

        loaded = AppSettings(
            settings_path=self.settings_path, app_root=self.root, portable=True
        )
        self.assertEqual(saved, self.settings_path)
        self.assertEqual(loaded.get("theme"), "Dark")
        self.assertEqual(loaded.get("window_size"), "1280x720")
        self.assertEqual(loaded.get("auto_refresh_interval"), 600)
        self.assertEqual(len(loaded.get("recent_files")), 10)
        self.assertTrue(loaded.database_path.endswith(os.path.join("data", "edubid.db")))

    def test_portable_detection_and_settings_validation(self):
        (self.root / "portable.flag").touch()
        self.assertTrue(AppSettings.detect_portable_mode(self.root))
        with patch.dict(os.environ, {"EDUBID_PORTABLE": "0"}):
            self.assertFalse(AppSettings.detect_portable_mode(self.root))
        settings = AppSettings(
            settings_path=self.settings_path, app_root=self.root, portable=True
        )
        with self.assertRaises(ValueError):
            settings.set("auto_refresh_interval", 10)
        with self.assertRaises(ValueError):
            settings.set("window_size", "small")

    def test_categorized_logs_are_created_and_rotating(self):
        log_directory = self.root / "logs"
        logger = configure_logging(str(log_directory), force=True)
        get_logger("import.test").info("import event")
        get_logger("service").error("error event")
        get_logger("crash").critical("crash event")
        for handler in logger.handlers:
            handler.flush()
            self.assertGreater(handler.backupCount, 0)

        self.assertIn("import event", (log_directory / "import.log").read_text(encoding="utf-8"))
        self.assertIn("error event", (log_directory / "error.log").read_text(encoding="utf-8"))
        self.assertIn("crash event", (log_directory / "crash.log").read_text(encoding="utf-8"))
        self.assertTrue((log_directory / "application.log").is_file())
        configure_logging("logs", force=True)


class OperationsServiceTest(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_directory.name)
        self.original_db_name = database.DB_NAME
        self.settings = AppSettings(
            settings_path=self.root / "config" / "settings.json",
            app_root=self.root,
            portable=True,
        )
        self.settings.ensure_directories()
        self.settings.save()
        database.configure_database(self.settings.database_path)
        MigrationService(self.settings.database_path).migrate()

    def tearDown(self):
        database.DB_NAME = self.original_db_name
        self.temp_directory.cleanup()

    def _insert_marker(self, value):
        connection = sqlite3.connect(self.settings.database_path)
        try:
            connection.execute("CREATE TABLE IF NOT EXISTS backup_marker(value TEXT)")
            connection.execute("DELETE FROM backup_marker")
            connection.execute("INSERT INTO backup_marker(value) VALUES (?)", (value,))
            connection.commit()
        finally:
            connection.close()

    def _marker(self):
        connection = sqlite3.connect(self.settings.database_path)
        try:
            row = connection.execute("SELECT value FROM backup_marker").fetchone()
            return row[0]
        finally:
            connection.close()

    def test_manual_backup_restore_integrity_and_retention(self):
        self._insert_marker("before")
        service = BackupService(
            self.settings.database_path, self.settings.backup_directory,
            retention_count=7,
        )
        first = service.create_backup()
        self.assertTrue(service.verify_backup(first))
        self._insert_marker("after")
        service.restore_backup(first)
        self.assertEqual(self._marker(), "before")

        for _index in range(9):
            service.create_backup(reason="retention")
        self.assertEqual(len(service.list_backups()), 7)
        corrupt = self.root / "corrupt.db"
        corrupt.write_text("not sqlite", encoding="utf-8")
        self.assertFalse(service.verify_backup(corrupt))
        with self.assertRaises(ValueError):
            service.restore_backup(corrupt)

    def test_migration_records_version_and_rolls_back_failure(self):
        service = MigrationService(self.settings.database_path)
        self.assertEqual(service.current_version(), MigrationService.CURRENT_VERSION)
        self._insert_marker("safe")

        def failing_migration(connection):
            connection.execute("CREATE TABLE rollback_probe(id INTEGER)")
            raise RuntimeError("intentional failure")

        failing = MigrationService(
            self.settings.database_path, migrations={2: failing_migration}
        )
        with self.assertRaises(MigrationError):
            failing.migrate()

        self.assertEqual(self._marker(), "safe")
        connection = sqlite3.connect(self.settings.database_path)
        try:
            exists = connection.execute(
                "SELECT 1 FROM sqlite_master WHERE name='rollback_probe'"
            ).fetchone()
        finally:
            connection.close()
        self.assertIsNone(exists)
        self.assertEqual(service.current_version(), 1)

    def test_diagnostics_generates_healthy_report(self):
        # Diagnostics checks release files from the real application root.
        application_root = Path(__file__).resolve().parents[1]
        report = DiagnosticsService(self.settings, app_root=application_root).run()

        self.assertEqual(report.status, "Healthy")
        checks = {check.name: check for check in report.checks}
        self.assertEqual(checks["Database"].status, "PASS")
        self.assertEqual(checks["Dependencies"].status, "PASS")
        self.assertIn("schema version 1", checks["Database"].detail)
        self.assertIn("EduBid Insight Health", report.to_text())

    def test_release_validation_checks_all_release_boundaries(self):
        application_root = Path(__file__).resolve().parents[1]
        report = ReleaseValidator(self.settings, app_root=application_root).validate()

        self.assertTrue(report.ready)
        self.assertEqual(
            {check.name for check in report.checks},
            {"Database", "Configuration", "Permissions", "Dependencies", "Version consistency"},
        )
        self.assertTrue(all(check.passed for check in report.checks))


if __name__ == "__main__":
    unittest.main()
