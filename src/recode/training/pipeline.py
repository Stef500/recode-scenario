"""Aggregate all batch outputs of a job into a training-ready DataFrame."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pandas as pd
from loguru import logger

from recode.training.coding import extract_target
from recode.training.extract import extract_clinical_reports


def prepare_training_files(job_dir: Path, *, n_examples: int | None = None) -> pd.DataFrame:
    """Aggregate ``batch_*.json`` + ``batch_*.csv`` in ``job_dir`` into one DataFrame.

    Args:
        job_dir: Directory containing the batch output artifacts.
        n_examples: Optional cap on the number of rows collected.

    Returns:
        DataFrame with the scenario inputs joined to parsed clinical reports
        and ICD coding targets.
    """
    json_files = sorted(job_dir.glob("batch_*.json"))
    frames: list[pd.DataFrame] = []
    collected = 0

    for json_file in json_files:
        idx_match = re.search(r"\d+", json_file.stem)
        if idx_match is None:
            logger.warning("Skipping file with no batch index: {}", json_file)
            continue
        idx = int(idx_match.group(0))

        parsed = extract_clinical_reports(json_file)
        if n_examples is not None and (collected + len(parsed)) > n_examples:
            parsed = parsed.iloc[: n_examples - collected]
        collected += len(parsed)

        scenarios_csv = json_file.with_suffix(".csv")
        if not scenarios_csv.exists():
            logger.warning("Missing scenarios CSV for {}", json_file)
            continue
        df_scenarios = pd.read_csv(scenarios_csv, index_col=0)

        joined = df_scenarios.merge(parsed, right_on="custom_id", left_index=True, how="inner")
        joined = joined.assign(batch=idx)
        frames.append(joined)

        if n_examples is not None and collected >= n_examples:
            break

    if not frames:
        return pd.DataFrame()

    df = pd.concat(frames, ignore_index=True)
    df = df[df["clinical_report"].notna()].copy()

    now_string = dt.datetime.now().strftime("%Y%m%d%H%M%S%f")
    df["encounter_id"] = now_string + df["batch"].astype(str) + df["custom_id"].astype(str)
    df["encounter_id"] = df["encounter_id"].str.pad(width=10, side="left", fillchar="0")

    targets = [extract_target(row) for _, row in df.iterrows()]
    df["icd_primary_pred"] = [t.icd_primary_pred for t in targets]
    df["icd_secondary_pred"] = [t.icd_secondary_pred for t in targets]
    df["icd_coding_text"] = [t.coding_text for t in targets]
    df["icd_coding_list"] = [t.coding_list for t in targets]
    return df
