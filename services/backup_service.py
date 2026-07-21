"""SQLite-safe manual, automatic, and restore backup operations."""

import os
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from core.logger import get_logger


class BackupService:
    RETENTION_COUNT = 7

    def __init__(self, database_path, backup_directory, retention_count=RETENTION_COUNT):
        self.database_path = Path(database_path).resolve()
        self.backup_directory = Path(backup_directory).resolve()
        self.retention_count = max(1, int(retention_count))
        self.logger = get_logger("backup")

    def create_backup(self, reason="manual"):
        if not self.database_path.exists():
            raise FileNotFoundError(f"Database not found: {self.database_path}")
        if not self.verify_backup(self.database_path):
            raise ValueError("Source database failed integrity verification")
        self.backup_directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
        safe_reason = "".join(character for character in str(reason) if character.isalnum() or character in "-_") or "backup"
        destination = self.backup_directory / f"edubid_{timestamp}_{safe_reason}.db"
        source_connection = sqlite3.connect(str(self.database_path))
        destination_connection = sqlite3.connect(str(destination))
        try:
            source_connection.backup(destination_connection)
        finally:
            destination_connection.close()
            source_connection.close()
        if not self.verify_backup(destination):
            destination.unlink(missing_ok=True)
            raise ValueError("Created backup failed integrity verification")
        self._prune()
        self.logger.info("backup created | reason=%s | path=%s", reason, destination)
        return str(destination)

    def automatic_backup(self):
        return self.create_backup(reason="exit")

    def restore_backup(self, backup_path):
        source = Path(backup_path).resolve()
        if not source.exists():
            raise FileNotFoundError(f"Backup not found: {source}")
        if not self.verify_backup(source):
            raise ValueError("Backup failed integrity verification")
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_handle = tempfile.NamedTemporaryFile(
            prefix="edubid_restore_", suffix=".db", dir=self.database_path.parent,
            delete=False,
        )
        temporary_path = Path(temporary_handle.name)
        temporary_handle.close()
        try:
            source_connection = sqlite3.connect(str(source))
            target_connection = sqlite3.connect(str(temporary_path))
            try:
                source_connection.backup(target_connection)
            finally:
                target_connection.close()
                source_connection.close()
            if not self.verify_backup(temporary_path):
                raise ValueError("Restored database failed integrity verification")
            os.replace(temporary_path, self.database_path)
        except Exception:
            temporary_path.unlink(missing_ok=True)
            raise
        self.logger.warning("backup restored | source=%s | database=%s", source, self.database_path)
        return str(self.database_path)

    @staticmethod
    def verify_backup(file_path):
        path = Path(file_path)
        if not path.is_file() or path.stat().st_size == 0:
            return False
        try:
            connection = sqlite3.connect(f"file:{path.resolve()}?mode=ro", uri=True)
            try:
                result = connection.execute("PRAGMA integrity_check").fetchone()
                return bool(result and result[0] == "ok")
            finally:
                connection.close()
        except sqlite3.Error:
            return False

    def list_backups(self):
        if not self.backup_directory.exists():
            return []
        return sorted(
            (str(path) for path in self.backup_directory.glob("edubid_*.db") if path.is_file()),
            key=lambda value: Path(value).stat().st_mtime,
            reverse=True,
        )

    def _prune(self):
        backups = self.list_backups()
        for file_path in backups[self.retention_count:]:
            candidate = Path(file_path).resolve()
            if candidate.parent != self.backup_directory:
                raise ValueError("Refusing to prune outside the backup directory")
            candidate.unlink(missing_ok=True)

