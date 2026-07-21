"""Versioned SQLite schema migrations with file-level rollback."""

import os
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from core.logger import get_logger
from services import database


class MigrationError(RuntimeError):
    pass


class MigrationService:
    CURRENT_VERSION = 1

    def __init__(self, database_path=None, migrations=None):
        self.database_path = Path(database_path or database.DB_NAME).resolve()
        self.migrations = migrations or {1: self._baseline}
        self.logger = get_logger("migration")

    def current_version(self):
        if not self.database_path.exists():
            return 0
        try:
            connection = sqlite3.connect(str(self.database_path))
            try:
                exists = connection.execute(
                    "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_version'"
                ).fetchone()
                if not exists:
                    return 0
                row = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()
                return int(row[0] or 0)
            finally:
                connection.close()
        except sqlite3.Error:
            return 0

    def migrate(self, target_version=None):
        target = int(target_version or max(self.migrations, default=self.CURRENT_VERSION))
        original_exists = self.database_path.exists()
        safety_path = None
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        if original_exists:
            handle = tempfile.NamedTemporaryFile(
                prefix="edubid_migration_", suffix=".db", dir=self.database_path.parent,
                delete=False,
            )
            safety_path = Path(handle.name)
            handle.close()
            shutil.copy2(self.database_path, safety_path)
        try:
            database.configure_database(self.database_path)
            database.create_database()
            connection = sqlite3.connect(str(self.database_path))
            try:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS schema_version(
                        version INTEGER PRIMARY KEY,
                        applied_at TEXT NOT NULL
                    )
                    """
                )
                connection.commit()
                current = self._connection_version(connection)
                if current > target:
                    raise MigrationError(
                        f"Database version {current} is newer than supported version {target}"
                    )
                for version in range(current + 1, target + 1):
                    migration = self.migrations.get(version)
                    if migration is None:
                        raise MigrationError(f"Missing migration {version}")
                    connection.execute("BEGIN")
                    try:
                        migration(connection)
                        connection.execute(
                            "INSERT INTO schema_version(version, applied_at) VALUES (?, ?)",
                            (version, datetime.now().astimezone().isoformat(timespec="seconds")),
                        )
                        connection.commit()
                    except Exception:
                        connection.rollback()
                        raise
            finally:
                connection.close()
        except Exception as error:
            if safety_path and safety_path.exists():
                os.replace(safety_path, self.database_path)
            elif not original_exists:
                self.database_path.unlink(missing_ok=True)
            self.logger.exception("migration failed | target=%s", target)
            raise MigrationError(f"Migration failed: {error}") from error
        finally:
            if safety_path and safety_path.exists():
                safety_path.unlink(missing_ok=True)
        version = self.current_version()
        self.logger.info("migration complete | version=%s | database=%s", version, self.database_path)
        return version

    @staticmethod
    def _connection_version(connection):
        row = connection.execute("SELECT MAX(version) FROM schema_version").fetchone()
        return int(row[0] or 0)

    @staticmethod
    def _baseline(_connection):
        """Version 1 adopts the idempotent v1.0 compatibility schema."""
