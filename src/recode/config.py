"""Application settings: secrets from .env + operational params from YAML."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Self

import yaml
from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class OperationalConfig(BaseModel):
    """Operational parameters (versioned in ``config/default.yaml``)."""

    model_config = ConfigDict(frozen=True)

    mistral_model: str = "mistral-large-latest"
    batch_size: int = Field(100, ge=1, le=1000)
    poll_interval_seconds: float = Field(2.0, ge=0.1)
    max_secondary_codes: int = Field(2, ge=0)
    distinct_chapter_default: bool = True
    rng_base_seed: int = 42


class Settings(BaseSettings):
    """Application settings: secrets (env) + operational (YAML)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_prefix="RECODE_",
        extra="ignore",
    )

    mistral_api_key: SecretStr
    data_dir: Path = Path("data")
    referentials_raw: Path = Path("referentials/raw")
    referentials_processed: Path = Path("referentials/processed")
    referentials_constants: Path = Path("referentials/constants")
    results_dir: Path = Path("runs")
    config_file: Path = Path("config/default.yaml")
    operational: OperationalConfig = Field(default_factory=OperationalConfig)

    @model_validator(mode="after")
    def _load_yaml_operational(self) -> Self:
        """Load operational params from the YAML file referenced by config_file.

        Only runs if operational was left at its default (i.e. no explicit
        override passed to the constructor).
        """
        if self.operational != OperationalConfig():
            return self
        if not self.config_file.exists():
            return self
        data: Any = yaml.safe_load(self.config_file.read_text(encoding="utf-8"))
        object.__setattr__(self, "operational", OperationalConfig(**data))
        return self
