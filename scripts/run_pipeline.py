"""End-to-end replacement of ``generate_scenarios_v4.ipynb`` using the new ``recode`` pipeline.

Reads a classification-profile Parquet, samples N profiles by weight, runs
``ScenarioGenerator``, builds prompts + prefix, and writes a CSV ready for
the downstream Mistral batch step.

Usage::

    uv run python scripts/run_pipeline.py \
        --profile-file data/scenarios_bn_final_20260126.parquet \
        --n 100 --seed 42 \
        --out runs/2026-04-16/scenarios.csv
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd
from loguru import logger
from tqdm import tqdm

sys.path.insert(0, "src")

from recode.models import Profile
from recode.referentials import ReferentialRegistry
from recode.scenarios.generator import ScenarioGenerator
from recode.scenarios.prompts import (
    build_prefix,
    build_system_prompt,
    build_user_prompt,
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile-file",
        type=Path,
        required=True,
        help="Parquet path to the classification profile table.",
    )
    parser.add_argument("--n", type=int, default=100, help="Number of scenarios to generate.")
    parser.add_argument("--seed", type=int, default=42, help="Base RNG seed.")
    parser.add_argument(
        "--query", type=str, default=None, help="Optional pandas query to pre-filter profiles."
    )
    parser.add_argument("--processed-dir", type=Path, default=Path("referentials/processed"))
    parser.add_argument("--constants-dir", type=Path, default=Path("referentials/constants"))
    parser.add_argument("--templates-dir", type=Path, default=Path("templates"))
    parser.add_argument("--out", type=Path, required=True, help="Output CSV path.")
    args = parser.parse_args()

    registry = ReferentialRegistry(
        processed_dir=args.processed_dir, constants_dir=args.constants_dir
    )
    generator = ScenarioGenerator(registry=registry, base_seed=args.seed)

    df = pd.read_parquet(args.profile_file)
    if args.query:
        df = df.query(args.query)
    sample = df.sample(n=args.n, weights="nb", random_state=args.seed).reset_index(drop=True)
    logger.info("Sampled {} profiles from {} candidates", len(sample), len(df))

    rows: list[dict] = []
    for _, raw in tqdm(sample.iterrows(), total=len(sample), desc="scenarios"):
        profile = Profile.model_validate(raw.to_dict())
        scenario = generator.generate(profile)
        row = scenario.to_csv_row()
        row["user_prompt"] = build_user_prompt(scenario)
        row["system_prompt"] = build_system_prompt(scenario, templates_dir=args.templates_dir)
        prefix = build_prefix(scenario)
        row["prefix"] = prefix
        row["prefix_len"] = len(prefix)
        rows.append(row)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(args.out)
    logger.success("Wrote {} scenarios → {}", len(rows), args.out)


if __name__ == "__main__":
    main()
