"""Central logging configuration for StudyScribe.

Provides :func:`get_logger`, which returns a configured logger. The first call
sets up the root ``studyscribe`` logger with two handlers:

* a console (stream) handler, and
* a rotating file handler writing to ``logs/studyscribe.log``.

Subsequent calls reuse that configuration, so importing modules can simply do::

    from app.utils.logger import get_logger
    logger = get_logger(__name__)
"""

from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from app.config.settings import settings

_ROOT_LOGGER_NAME = "studyscribe"
_configured = False

_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


def _configure_root_logger() -> None:
    """Attach console + rotating-file handlers to the root app logger once."""
    global _configured
    if _configured:
        return

    logger = logging.getLogger(_ROOT_LOGGER_NAME)
    logger.setLevel(settings.LOG_LEVEL)
    logger.propagate = False

    formatter = logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT)

    # Console handler
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.addHandler(console)

    # Rotating file handler — best effort; never crash the app over logging.
    try:
        settings.LOG_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=settings.LOG_MAX_BYTES,
            backupCount=settings.LOG_BACKUP_COUNT,
            encoding="utf-8",
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    except OSError as exc:
        logger.warning("File logging disabled (could not open log file): %s", exc)

    _configured = True


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a logger under the ``studyscribe`` namespace.

    ``name`` is typically ``__name__`` from the calling module. The root
    handlers are configured on first use.
    """
    _configure_root_logger()

    if not name or name == _ROOT_LOGGER_NAME:
        return logging.getLogger(_ROOT_LOGGER_NAME)

    # Nest all module loggers under the app root so they share its handlers.
    return logging.getLogger(f"{_ROOT_LOGGER_NAME}.{name}")
