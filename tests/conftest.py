"""Shared pytest fixtures."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def tmp_config_yaml(tmp_path: Path) -> Path:
    """Minimal operational YAML config for tests."""
    path = tmp_path / "config.yaml"
    path.write_text(
        "mistral_model: test-model\n"
        "batch_size: 10\n"
        "poll_interval_seconds: 0.1\n"
        "max_secondary_codes: 1\n"
        "distinct_chapter_default: false\n"
        "rng_base_seed: 1\n"
    )
    return path
