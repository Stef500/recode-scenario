"""Tests for recode.config."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError


def test_settings_loads_api_key_from_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, tmp_config_yaml: Path
) -> None:
    """Settings must read MISTRAL_API_KEY from RECODE_MISTRAL_API_KEY env var."""
    monkeypatch.setenv("RECODE_MISTRAL_API_KEY", "sk-test-123")
    monkeypatch.setenv("RECODE_DATA_DIR", str(tmp_path))
    from recode.config import Settings

    settings = Settings(config_file=tmp_config_yaml, _env_file=None)  # type: ignore[call-arg]
    assert settings.mistral_api_key.get_secret_value() == "sk-test-123"
    assert settings.operational.mistral_model == "test-model"


def test_settings_fails_without_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Settings must raise if MISTRAL_API_KEY missing."""
    monkeypatch.delenv("RECODE_MISTRAL_API_KEY", raising=False)
    from recode.config import Settings

    with pytest.raises(ValidationError):
        Settings(_env_file=None)  # type: ignore[call-arg]


def test_operational_config_defaults() -> None:
    """OperationalConfig has sensible defaults."""
    from recode.config import OperationalConfig

    cfg = OperationalConfig()
    assert cfg.mistral_model == "mistral-large-latest"
    assert 1 <= cfg.batch_size <= 1000
    assert cfg.rng_base_seed == 42
