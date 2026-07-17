"""Logging configuration.

Console logging always; rotating file logging when the log directory is
writable. Call ``setup_logging()`` once at application startup.
"""

import logging
import logging.config
import sys
from pathlib import Path

from app.core.config import get_settings

LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"


def setup_logging() -> None:
    settings = get_settings()

    handlers: dict[str, dict] = {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
            "stream": sys.stdout,
        }
    }

    log_path = Path(settings.log_file)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        handlers["file"] = {
            "class": "logging.handlers.RotatingFileHandler",
            "formatter": "default",
            "filename": str(log_path),
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
        }
    except OSError:  # pragma: no cover - read-only filesystem
        pass

    logging.config.dictConfig(
        {
            "version": 1,
            "disable_existing_loggers": False,
            "formatters": {"default": {"format": LOG_FORMAT}},
            "handlers": handlers,
            "root": {"level": settings.log_level, "handlers": list(handlers)},
            "loggers": {
                "uvicorn": {"level": settings.log_level},
                "uvicorn.access": {"level": settings.log_level},
                "sqlalchemy.engine": {
                    "level": "INFO" if settings.database_echo else "WARNING"
                },
            },
        }
    )


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
