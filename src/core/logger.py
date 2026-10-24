"""
Central logging configuration.

Call ``setup_logging`` once at startup; every module then simply uses
``logging.getLogger(__name__)``.
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
ROOT_LOGGER_NAME = "src"


def setup_logging(level: str = "INFO", log_dir: str | None = "logs") -> logging.Logger:
    """Configure console (and optional rotating file) handlers for the app."""
    logger = logging.getLogger(ROOT_LOGGER_NAME)
    logger.setLevel(level)

    if logger.handlers:  # already configured (e.g. called twice in tests)
        return logger

    formatter = logging.Formatter(LOG_FORMAT)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    if log_dir:
        path = Path(log_dir)
        path.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            path / "app.log",
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    # Keep third-party libraries quiet unless something goes wrong
    for noisy in ("urllib3", "apscheduler", "sqlalchemy.engine"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

    return logger
