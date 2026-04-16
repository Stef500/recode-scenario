"""`recode scenarios generate` command."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer
from loguru import logger
from tqdm import tqdm

from recode.config import Settings
from recode.models import Profile
from recode.referentials import ReferentialRegistry
from recode.scenarios.generator import ScenarioGenerator
from recode.scenarios.prompts import build_prefix, build_system_prompt, build_user_prompt

app = typer.Typer(help="Generate clinical scenarios from PMSI profiles")


@app.command("generate")
def generate(
    profile_file: Path = typer.Option(
        ..., "--profile-file", help="Parquet path of classification profiles"
    ),
    n_scenarios: int = typer.Option(100, "--n", min=1),
    seed: int = typer.Option(42, help="Base seed for deterministic generation"),
    query: str | None = typer.Option(None, help="Optional pandas query to filter"),
    output: Path = typer.Option(..., "--out", "-o"),
) -> None:
    """Sample N profiles, generate scenarios with prompts, write CSV."""
    settings = Settings()
    registry = ReferentialRegistry(
        processed_dir=settings.referentials_processed,
        constants_dir=settings.referentials_constants,
    )
    df = pd.read_parquet(profile_file)
    if query:
        df = df.query(query)
    sample = df.sample(n=n_scenarios, weights="nb", replace=True, random_state=seed).reset_index(
        drop=True
    )
    logger.info("Sampled {} profiles from {} candidates", len(sample), len(df))

    generator = ScenarioGenerator(registry=registry, base_seed=seed)
    rows: list[dict[str, object]] = []
    for _, raw in tqdm(sample.iterrows(), total=len(sample), desc="scenarios"):
        profile = Profile.model_validate(raw.to_dict())
        scenario = generator.generate(profile)
        row = scenario.to_csv_row()
        row["user_prompt"] = build_user_prompt(scenario)
        row["system_prompt"] = build_system_prompt(scenario)
        prefix = build_prefix(scenario)
        row["prefix"] = prefix
        row["prefix_len"] = len(prefix)
        rows.append(row)

    output.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(output)
    logger.success("Wrote {} scenarios → {}", len(rows), output)
