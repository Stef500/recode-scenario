"""Tests for recode.logging."""

from __future__ import annotations

import time
from pathlib import Path

from loguru import logger


def test_setup_logging_default() -> None:
    """setup_logging with no args configures stderr only."""
    from recode.logging import setup_logging

    setup_logging()
    logger.info("test message")


def test_setup_logging_with_file(tmp_path: Path) -> None:
    """setup_logging with log_file creates parent dirs + writes DEBUG to file."""
    from recode.logging import setup_logging

    log_file = tmp_path / "logs/app.log"
    setup_logging(verbose=True, log_file=log_file)
    logger.debug("debug message visible")
    logger.info("info message")
    time.sleep(0.05)
    assert log_file.parent.exists()
    assert log_file.exists()
    content = log_file.read_text()
    assert "debug message visible" in content
    assert "info message" in content
