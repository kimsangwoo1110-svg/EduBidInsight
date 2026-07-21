"""Production health diagnostics for database, paths, disk, and dependencies."""

import importlib.metadata
import os
import shutil
import sqlite3
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from services.migration_service import MigrationService


@dataclass(frozen=True)
class DiagnosticCheck:
    name: str
    status: str
    detail: str
    critical: bool = True


@dataclass(frozen=True)
class HealthReport:
    status: str
    generated_at: str
    checks: tuple

    def to_dict(self):
        return {
            "status": self.status,
            "generated_at": self.generated_at,
            "checks": [asdict(check) for check in self.checks],
        }

    def to_text(self):
        lines = [f"EduBid Insight Health: {self.status}", f"Generated: {self.generated_at}"]
        lines.extend(f"[{check.status}] {check.name}: {check.detail}" for check in self.checks)
        return "\n".join(lines)


class DiagnosticsService:
    REQUIRED_FILES = ("app.py", "requirements.txt", "core/version.py")
    REQUIRED_DEPENDENCIES = ("requests", "openpyxl", "customtkinter")
    MIN_FREE_BYTES = 100 * 1024 * 1024

    def __init__(self, settings, app_root=None):
        self.settings = settings
        self.app_root = Path(app_root or settings.app_root).resolve()

    def run(self):
        checks = [self._database_check()]
        checks.extend(self._directory_checks())
        checks.append(self._required_files_check())
        checks.append(self._disk_space_check())
        checks.append(self._dependencies_check())
        failed_critical = any(check.status == "FAIL" and check.critical for check in checks)
        warnings = any(check.status in {"FAIL", "WARN"} for check in checks)
        status = "Unhealthy" if failed_critical else "Degraded" if warnings else "Healthy"
        return HealthReport(
            status=status,
            generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            checks=tuple(checks),
        )

    def dependency_versions(self):
        versions = {}
        for package in self.REQUIRED_DEPENDENCIES:
            try:
                versions[package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                versions[package] = None
        return versions

    def _database_check(self):
        path = Path(self.settings.database_path)
        if not path.is_file():
            return DiagnosticCheck("Database", "FAIL", f"Not found: {path}")
        try:
            connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
            try:
                result = connection.execute("PRAGMA quick_check").fetchone()
            finally:
                connection.close()
        except sqlite3.Error as error:
            return DiagnosticCheck("Database", "FAIL", str(error))
        if not result or result[0] != "ok":
            return DiagnosticCheck("Database", "FAIL", str(result[0] if result else "No result"))
        version = MigrationService(path).current_version()
        return DiagnosticCheck("Database", "PASS", f"Connected; schema version {version}")

    def _directory_checks(self):
        checks = []
        directories = {
            "Data directory": self.settings.get("data_directory"),
            "Backup directory": self.settings.get("backup_directory"),
            "Log directory": self.settings.get("log_directory"),
            "Configuration directory": str(self.settings.settings_path.parent),
        }
        for name, value in directories.items():
            path = Path(value)
            if not path.is_dir():
                checks.append(DiagnosticCheck(name, "FAIL", f"Not found: {path}"))
                continue
            try:
                handle = tempfile.NamedTemporaryFile(prefix="edubid_check_", dir=path, delete=False)
                marker = Path(handle.name)
                handle.close()
                marker.unlink()
                checks.append(DiagnosticCheck(name, "PASS", f"Writable: {path}"))
            except OSError as error:
                checks.append(DiagnosticCheck(name, "FAIL", str(error)))
        return checks

    def _required_files_check(self):
        missing = [name for name in self.REQUIRED_FILES if not (self.app_root / name).is_file()]
        if missing:
            return DiagnosticCheck("Required files", "FAIL", "Missing: " + ", ".join(missing))
        return DiagnosticCheck("Required files", "PASS", f"{len(self.REQUIRED_FILES)} files present")

    def _disk_space_check(self):
        target = Path(self.settings.get("data_directory"))
        try:
            free = shutil.disk_usage(target).free
        except OSError as error:
            return DiagnosticCheck("Disk space", "FAIL", str(error), critical=False)
        status = "PASS" if free >= self.MIN_FREE_BYTES else "WARN"
        return DiagnosticCheck("Disk space", status, f"{free / (1024 ** 3):.2f} GB free", critical=False)

    def _dependencies_check(self):
        versions = self.dependency_versions()
        missing = [name for name, version in versions.items() if version is None]
        if missing:
            return DiagnosticCheck("Dependencies", "FAIL", "Missing: " + ", ".join(missing))
        detail = ", ".join(f"{name} {version}" for name, version in versions.items())
        return DiagnosticCheck("Dependencies", "PASS", detail)
