"""Loguru configuration helper."""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

LOG_FORMAT = (
    "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
    "<level>{level: <8}</level> | "
    "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
    "<level>{message}</level>"
)


def setup_logging(*, verbose: bool = False, log_file: Path | None = None) -> None:
    """Configure loguru: stderr sink + optional rotating file sink.

    Args:
        verbose: If True, console level is DEBUG (default INFO).
        log_file: Optional path to a log file. Parent dirs are created.
            File sink level is always DEBUG with 50MB rotation and
            14 days retention.
    """
    logger.remove()
    console_level = "DEBUG" if verbose else "INFO"
    logger.add(sys.stderr, level=console_level, format=LOG_FORMAT, colorize=True)
    if log_file is not None:
        log_file.parent.mkdir(parents=True, exist_ok=True)
        logger.add(
            log_file,
            level="DEBUG",
            format=LOG_FORMAT,
            rotation="50 MB",
            retention="14 days",
            compression="zip",
        )
        logger.info("Logging to file: {}", log_file)
