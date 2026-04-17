"""Aggregate all batch outputs of a job into a training-ready DataFrame."""

from __future__ import annotations

import datetime as dt
import re
from pathlib import Path

import pandas as pd
from loguru import logger

from recode.training.coding import extract_target
from recode.training.extract import extract_clinical_reports


def _extract_batch_index(json_file: Path) -> int | None:
    """Return the integer index embedded in ``batch_N.json``; None if malformed."""
    idx_match = re.search(r"\d+", json_file.stem)
    return int(idx_match.group(0)) if idx_match else None


def _cap_rows(parsed: pd.DataFrame, *, collected: int, budget: int | None) -> pd.DataFrame:
    """Cap ``parsed`` so that ``collected + len(parsed) <= budget``.

    Pass through untouched when ``budget`` is ``None``.
    """
    if budget is None or collected + len(parsed) <= budget:
        return parsed
    return parsed.iloc[: budget - collected]


def _join_scenarios(parsed: pd.DataFrame, json_file: Path, batch_idx: int) -> pd.DataFrame | None:
    """Merge parsed reports with the sibling ``batch_N.csv``; None if missing."""
    scenarios_csv = json_file.with_suffix(".csv")
    if not scenarios_csv.exists():
        logger.warning("Missing scenarios CSV for {}", json_file)
        return None
    df_scenarios = pd.read_csv(scenarios_csv, index_col=0)
    joined = df_scenarios.merge(parsed, right_on="custom_id", left_index=True, how="inner")
    return joined.assign(batch=batch_idx)


def _collect_batch_frames(job_dir: Path, n_examples: int | None) -> list[pd.DataFrame]:
    """Walk ``batch_*.json`` files and collect joined frames, capping at ``n_examples``."""
    frames: list[pd.DataFrame] = []
    collected = 0
    for json_file in sorted(job_dir.glob("batch_*.json")):
        idx = _extract_batch_index(json_file)
        if idx is None:
            logger.warning("Skipping file with no batch index: {}", json_file)
            continue
        parsed = _cap_rows(
            extract_clinical_reports(json_file), collected=collected, budget=n_examples
        )
        collected += len(parsed)
        joined = _join_scenarios(parsed, json_file, idx)
        if joined is not None:
            frames.append(joined)
        if n_examples is not None and collected >= n_examples:
            break
    return frames


def _add_encounter_id(df: pd.DataFrame) -> pd.DataFrame:
    """Build ``encounter_id`` = timestamp + batch + custom_id (left-padded to 10)."""
    now_string = dt.datetime.now().strftime("%Y%m%d%H%M%S%f")
    df = df.copy()
    df["encounter_id"] = now_string + df["batch"].astype(str) + df["custom_id"].astype(str)
    df["encounter_id"] = df["encounter_id"].str.pad(width=10, side="left", fillchar="0")
    return df


def _add_icd_targets(df: pd.DataFrame) -> pd.DataFrame:
    """Extract ICD primary + secondary + coding text into prediction columns."""
    targets = [extract_target(row) for _, row in df.iterrows()]
    df = df.copy()
    df["icd_primary_pred"] = [t.icd_primary_pred for t in targets]
    df["icd_secondary_pred"] = [t.icd_secondary_pred for t in targets]
    df["icd_coding_text"] = [t.coding_text for t in targets]
    df["icd_coding_list"] = [t.coding_list for t in targets]
    return df


def prepare_training_files(job_dir: Path, *, n_examples: int | None = None) -> pd.DataFrame:
    """Aggregate ``batch_*.json`` + ``batch_*.csv`` in ``job_dir`` into one DataFrame.

    Args:
        job_dir: Directory containing the batch output artifacts.
        n_examples: Optional cap on the number of rows collected.

    Returns:
        DataFrame with scenario inputs joined to parsed clinical reports and
        ICD coding targets. Empty DataFrame if no batch file yields rows.
    """
    frames = _collect_batch_frames(job_dir, n_examples)
    if not frames:
        return pd.DataFrame()
    df = pd.concat(frames, ignore_index=True)
    df = df[df["clinical_report"].notna()].copy()
    return _add_icd_targets(_add_encounter_id(df))
