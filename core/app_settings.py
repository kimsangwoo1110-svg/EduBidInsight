"""Persistent application settings and portable-mode path resolution."""

import json
import os
import sys
from pathlib import Path
from threading import RLock


DEFAULT_AUTO_REFRESH_SECONDS = 300
DEFAULT_WINDOW_SIZE = "1500x900"
DEFAULT_THEME = "Light"
MAX_RECENT_FILES = 10


class AppSettings:
    """Manage validated v1.0 settings in one JSON document."""

    def __init__(self, settings_path=None, app_root=None, portable=None):
        self.app_root = Path(app_root or Path(__file__).resolve().parents[1]).resolve()
        self.portable_mode = self.detect_portable_mode(self.app_root) if portable is None else bool(portable)
        self.user_root = self._user_root()
        default_settings_path = self.user_root / "config" / "app_settings.json"
        self.settings_path = Path(settings_path or default_settings_path).resolve()
        self._lock = RLock()
        self._values = self.defaults()
        self.load()

    def defaults(self):
        root = self.user_root
        return {
            "data_directory": str((root / "data").resolve()),
            "backup_directory": str((root / "backups").resolve()),
            "log_directory": str((root / "logs").resolve()),
            "auto_refresh_interval": DEFAULT_AUTO_REFRESH_SECONDS,
            "theme": DEFAULT_THEME,
            "window_size": DEFAULT_WINDOW_SIZE,
            "recent_files": [],
            "portable_mode": self.portable_mode,
        }

    def load(self):
        with self._lock:
            if not self.settings_path.exists():
                return self
            try:
                with self.settings_path.open("r", encoding="utf-8") as settings_file:
                    loaded = json.load(settings_file)
            except (OSError, json.JSONDecodeError) as error:
                raise ValueError(f"Invalid settings file: {self.settings_path}") from error
            self._values.update(self._validated(loaded))
        return self

    def save(self):
        with self._lock:
            self._values = self._validated(self._values)
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.settings_path.with_suffix(self.settings_path.suffix + ".tmp")
            with temporary.open("w", encoding="utf-8") as settings_file:
                json.dump(self._values, settings_file, ensure_ascii=False, indent=2)
                settings_file.flush()
                os.fsync(settings_file.fileno())
            os.replace(temporary, self.settings_path)
        return self.settings_path

    def get(self, key, default=None):
        return self._values.get(key, default)

    def set(self, key, value):
        candidate = dict(self._values)
        candidate[key] = value
        self._values = self._validated(candidate)
        return self

    def update(self, values):
        candidate = dict(self._values)
        candidate.update(values)
        self._values = self._validated(candidate)
        return self

    def add_recent_file(self, file_path):
        selected = str(Path(file_path).resolve())
        recent = [item for item in self.get("recent_files", []) if item != selected]
        self.set("recent_files", [selected, *recent][:MAX_RECENT_FILES])
        return self

    def ensure_directories(self):
        for key in ("data_directory", "backup_directory", "log_directory"):
            Path(self.get(key)).mkdir(parents=True, exist_ok=True)
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)

    @property
    def database_path(self):
        return str((Path(self.get("data_directory")) / "edubid.db").resolve())

    @property
    def backup_directory(self):
        return str(Path(self.get("backup_directory")).resolve())

    @property
    def log_directory(self):
        return str(Path(self.get("log_directory")).resolve())

    def to_dict(self):
        return dict(self._values)

    @staticmethod
    def detect_portable_mode(app_root=None):
        root = Path(app_root or Path(__file__).resolve().parents[1]).resolve()
        environment = str(os.environ.get("EDUBID_PORTABLE", "")).strip().casefold()
        if environment in {"1", "true", "yes", "on"}:
            return True
        if environment in {"0", "false", "no", "off"}:
            return False
        if (root / "portable.flag").exists():
            return True
        # Source checkouts are self-contained; frozen builds need the marker.
        return not bool(getattr(sys, "frozen", False))

    def _user_root(self):
        if self.portable_mode:
            return self.app_root
        local = os.environ.get("LOCALAPPDATA") or os.environ.get("APPDATA")
        if local:
            return (Path(local) / "EduBidInsight").resolve()
        return (Path.home() / ".edubid_insight").resolve()

    @staticmethod
    def _validated(values):
        result = dict(values)
        for key in ("data_directory", "backup_directory", "log_directory"):
            selected = str(result.get(key) or "").strip()
            if not selected:
                raise ValueError(f"{key} is required")
            result[key] = str(Path(selected).expanduser().resolve())
        try:
            interval = int(result.get("auto_refresh_interval", DEFAULT_AUTO_REFRESH_SECONDS))
        except (TypeError, ValueError) as error:
            raise ValueError("auto_refresh_interval must be an integer") from error
        if not 30 <= interval <= 86_400:
            raise ValueError("auto_refresh_interval must be between 30 and 86400 seconds")
        result["auto_refresh_interval"] = interval
        theme = str(result.get("theme") or DEFAULT_THEME).title()
        if theme not in {"Light", "Dark", "System"}:
            raise ValueError(f"Unsupported theme: {theme}")
        result["theme"] = theme
        window_size = str(result.get("window_size") or DEFAULT_WINDOW_SIZE).lower().strip()
        parts = window_size.split("x", 1)
        if len(parts) != 2 or not all(part.isdigit() for part in parts):
            raise ValueError("window_size must use WIDTHxHEIGHT")
        width, height = (int(part) for part in parts)
        if width < 800 or height < 600:
            raise ValueError("window_size must be at least 800x600")
        result["window_size"] = f"{width}x{height}"
        recent = result.get("recent_files") or []
        if not isinstance(recent, list):
            raise ValueError("recent_files must be a list")
        result["recent_files"] = [str(item) for item in recent[:MAX_RECENT_FILES]]
        result["portable_mode"] = bool(result.get("portable_mode", False))
        return result


_default_settings = None


def get_app_settings(force_reload=False):
    global _default_settings
    if force_reload or _default_settings is None:
        _default_settings = AppSettings()
    return _default_settings
