"""Application-wide rotating file logging configuration."""

import logging
import os
from logging.handlers import RotatingFileHandler


LOGGER_NAME = "edubid"
LOG_FILE_NAME = "edubid.log"


def configure_logging(log_dir="logs", level=logging.INFO, force=False):
    """Configure and return the shared EduBid logger."""
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    if force:
        for handler in list(logger.handlers):
            handler.close()
            logger.removeHandler(handler)

    if not logger.handlers:
        os.makedirs(log_dir, exist_ok=True)
        handler = RotatingFileHandler(
            os.path.join(log_dir, LOG_FILE_NAME),
            maxBytes=1_000_000,
            backupCount=5,
            encoding="utf-8",
        )
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
            )
        )
        logger.addHandler(handler)

    return logger


def get_logger(component=None):
    """Return the application logger or one of its component children."""
    root_logger = configure_logging()
    return root_logger.getChild(component) if component else root_logger
