"""Application-wide rotating file logging configuration."""

import logging
import os
import sys
import threading
from logging.handlers import RotatingFileHandler


LOGGER_NAME = "edubid"
LOG_FILES = {
    "application": "application.log",
    "import": "import.log",
    "error": "error.log",
    "crash": "crash.log",
}
# Backward-compatible public name used by existing integrations.
LOG_FILE_NAME = LOG_FILES["application"]


class _ComponentFilter(logging.Filter):
    def __init__(self, prefixes):
        super().__init__()
        self.prefixes = tuple(prefixes)

    def filter(self, record):
        return any(record.name.startswith(prefix) for prefix in self.prefixes)


def configure_logging(log_dir="logs", level=logging.INFO, force=False):
    """Configure categorized, automatically rotating production logs."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if force:
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

    if not logger.handlers:
        os.makedirs(log_dir, exist_ok=True)
        formatter = logging.Formatter(
            "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
        )

        def add_handler(kind, handler_level, log_filter=None):
            handler = RotatingFileHandler(
                os.path.join(log_dir, LOG_FILES[kind]),
                maxBytes=2_000_000,
                backupCount=5,
                encoding="utf-8",
            )
            handler.setLevel(handler_level)
            handler.setFormatter(formatter)
            if log_filter:
                handler.addFilter(log_filter)
            logger.addHandler(handler)

        add_handler("application", level)
        add_handler(
            "import",
            level,
            _ComponentFilter(("edubid.import", "edubid.connector", "edubid.sync")),
        )
        add_handler("error", logging.ERROR)

        crash_handler = RotatingFileHandler(
            os.path.join(log_dir, LOG_FILES["crash"]),
            maxBytes=2_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        crash_handler.setLevel(logging.CRITICAL)
        crash_handler.setFormatter(formatter)
        crash_handler.addFilter(_ComponentFilter(("edubid.crash",)))
        logger.addHandler(crash_handler)

    return logger


def get_logger(component=None):
    """Return the application logger or one of its component children."""
    root_logger = configure_logging()
    return root_logger.getChild(component) if component else root_logger


def install_crash_logging(log_dir="logs"):
    """Capture uncaught main-thread and worker-thread failures."""
    configure_logging(log_dir=log_dir)
    crash_logger = get_logger("crash")

    def exception_hook(exception_type, exception, traceback):
        if issubclass(exception_type, KeyboardInterrupt):
            sys.__excepthook__(exception_type, exception, traceback)
            return
        crash_logger.critical(
            "uncaught application exception",
            exc_info=(exception_type, exception, traceback),
        )

    def thread_hook(arguments):
        crash_logger.critical(
            "uncaught thread exception | thread=%s",
            arguments.thread.name if arguments.thread else "unknown",
            exc_info=(arguments.exc_type, arguments.exc_value, arguments.exc_traceback),
        )

    sys.excepthook = exception_hook
    if hasattr(threading, "excepthook"):
        threading.excepthook = thread_hook
