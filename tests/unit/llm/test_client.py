"""Tests for make_client factory."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


def test_make_client_uses_secret_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("RECODE_MISTRAL_API_KEY", "sk-test-abc")
    monkeypatch.setenv("RECODE_DATA_DIR", str(tmp_path))
    with patch("recode.llm.client.Mistral") as mock_mistral:
        mock_mistral.return_value = MagicMock()
        from recode.llm.client import make_client

        make_client()
        mock_mistral.assert_called_once_with(api_key="sk-test-abc")
