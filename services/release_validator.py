"""v1.0 release validation composed from settings and health diagnostics."""

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from core.version import __version__
from services.diagnostics_service import DiagnosticsService
from services.migration_service import MigrationService


@dataclass(frozen=True)
class ValidationItem:
    name: str
    passed: bool
    detail: str


@dataclass(frozen=True)
class ReleaseValidationReport:
    ready: bool
    version: str
    generated_at: str
    checks: tuple

    def to_dict(self):
        return {
            "ready": self.ready,
            "version": self.version,
            "generated_at": self.generated_at,
            "checks": [asdict(check) for check in self.checks],
        }


class ReleaseValidator:
    def __init__(self, settings, app_root=None):
        self.settings = settings
        self.app_root = Path(app_root or settings.app_root).resolve()

    def validate(self):
        health = DiagnosticsService(self.settings, self.app_root).run()
        check_by_name = {check.name: check for check in health.checks}
        database = check_by_name.get("Database")
        directory_checks = [check for check in health.checks if "directory" in check.name.casefold()]
        dependencies = check_by_name.get("Dependencies")
        settings_valid, settings_detail = self._settings_check()
        version_valid, version_detail = self._version_check()
        schema_version = MigrationService(self.settings.database_path).current_version()
        checks = (
            ValidationItem("Database", bool(database and database.status == "PASS"), database.detail if database else "Missing diagnostic"),
            ValidationItem("Configuration", settings_valid, settings_detail),
            ValidationItem("Permissions", bool(directory_checks) and all(item.status == "PASS" for item in directory_checks), "; ".join(item.detail for item in directory_checks)),
            ValidationItem("Dependencies", bool(dependencies and dependencies.status == "PASS"), dependencies.detail if dependencies else "Missing diagnostic"),
            ValidationItem("Version consistency", version_valid and schema_version == MigrationService.CURRENT_VERSION, f"{version_detail}; schema {schema_version}"),
        )
        return ReleaseValidationReport(
            ready=all(check.passed for check in checks),
            version=__version__,
            generated_at=datetime.now().astimezone().isoformat(timespec="seconds"),
            checks=checks,
        )

    def _settings_check(self):
        if not self.settings.settings_path.is_file():
            return False, f"Settings file is missing: {self.settings.settings_path}"
        try:
            self.settings._validated(self.settings.to_dict())
            return True, f"Valid JSON configuration: {self.settings.settings_path}"
        except ValueError as error:
            return False, str(error)

    def _version_check(self):
        release_file = self.app_root / "RELEASE.md"
        if not release_file.is_file():
            return False, "RELEASE.md is missing"
        try:
            release_text = release_file.read_text(encoding="utf-8")
        except OSError as error:
            return False, str(error)
        if __version__ not in release_text:
            return False, f"RELEASE.md does not contain {__version__}"
        return True, f"Application and release documentation: {__version__}"
