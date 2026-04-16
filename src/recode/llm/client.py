"""Thin Mistral client factory."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mistralai.client import Mistral

if TYPE_CHECKING:
    from recode.config import Settings


def make_client(settings: Settings | None = None) -> Mistral:
    """Instantiate a Mistral client using the API key from Settings.

    Args:
        settings: Optional Settings instance; defaults to reading fresh from env.

    Returns:
        A Mistral client ready for batch/chat operations.
    """
    from recode.config import Settings

    cfg = settings or Settings()
    return Mistral(api_key=cfg.mistral_api_key.get_secret_value())
