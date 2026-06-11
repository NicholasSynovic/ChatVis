"""Logging configuration for ChatVis.

Exposes a single ``configure_logging`` entry point used by ``chatvis.main``.
All submodules should obtain their logger via
``logging.getLogger(__name__)`` so messages propagate to the ``chatvis``
root configured here.
"""

import logging
import sys
import time
from pathlib import Path

LOGGER_NAME: str = "chatvis"
LOG_FORMAT: str = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
DATE_FORMAT: str = "%Y-%m-%dT%H:%M:%SZ"


def configure_logging(
    log_to_file: bool,
    level: int = logging.INFO,
) -> Path | None:
    """Install stdout (and optionally file) handlers on the ``chatvis`` logger.

    Args:
        log_to_file: when ``True``, also write log records to
            ``<cwd>/chatvis_<unix-seconds>.log`` (clobbering any existing
            file at that path).
        level: logging level for both handlers and the ``chatvis`` logger.

    Returns:
        The path to the log file when file logging is enabled, otherwise
        ``None``.
    """
    logger: logging.Logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False

    # Make repeat calls idempotent (handy in tests / interactive sessions).
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()

    formatter: logging.Formatter = logging.Formatter(
        fmt=LOG_FORMAT,
        datefmt=DATE_FORMAT,
    )
    # Emit timestamps in UTC regardless of the host timezone.
    formatter.converter = time.gmtime

    stream_handler: logging.StreamHandler = logging.StreamHandler(sys.stdout)
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    log_path: Path | None = None
    if log_to_file:
        log_path = Path.cwd() / f"chatvis_{int(time.time())}.log"
        file_handler: logging.FileHandler = logging.FileHandler(
            filename=log_path,
            mode="w",
            encoding="utf-8",
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return log_path
