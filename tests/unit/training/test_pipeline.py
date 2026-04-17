"""Tests for training.pipeline.prepare_training_files."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd


def _make_body(cr: str, dxlabel: str, dxcode: str, dxshort: str, age: int) -> str:
    payload = json.dumps(
        {
            "CR": cr,
            "formulations": {
                "diagnostics": {f"{dxlabel} ({dxcode})": [dxshort]},
                "informations": {"age": age},
            },
        }
    )
    return f"```json\n{payload}\n```"


def _write_batch(path: Path, items: list[tuple[str, str]]) -> None:
    """items: list of (custom_id, response_body)."""
    lines = [
        {
            "custom_id": cid,
            "response": {"body": {"choices": [{"message": {"content": body}}]}},
        }
        for cid, body in items
    ]
    path.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")


def _write_scenarios_csv(path: Path, custom_ids: list[int]) -> None:
    df = pd.DataFrame(
        {
            "icd_primary_code": ["I500"] * len(custom_ids),
            "case_management_type": ["DP"] * len(custom_ids),
            "case_management_type_description": ["ICC"] * len(custom_ids),
        },
        index=custom_ids,
    )
    df.index.name = "custom_id"
    df.to_csv(path)


def test_prepare_training_files_full(tmp_path: Path) -> None:
    from recode.training.pipeline import prepare_training_files

    body = _make_body("CR1", "Insuffisance cardiaque", "I500", "ICC", 65)
    _write_batch(tmp_path / "batch_0.json", [("0", body), ("1", body)])
    _write_scenarios_csv(tmp_path / "batch_0.csv", [0, 1])

    df = prepare_training_files(tmp_path)
    assert len(df) == 2
    assert set(df.columns) >= {
        "icd_primary_pred",
        "icd_secondary_pred",
        "icd_coding_text",
        "icd_coding_list",
        "encounter_id",
        "batch",
        "clinical_report",
    }
    assert list(df["icd_primary_pred"]) == ["I500", "I500"]
    # encounter_id is padded to at least 10 chars
    assert all(len(eid) >= 10 for eid in df["encounter_id"])


def test_prepare_training_files_n_examples_cap(tmp_path: Path) -> None:
    from recode.training.pipeline import prepare_training_files

    body = _make_body("CR", "Insuffisance cardiaque", "I500", "ICC", 65)
    _write_batch(tmp_path / "batch_0.json", [(str(i), body) for i in range(3)])
    _write_scenarios_csv(tmp_path / "batch_0.csv", [0, 1, 2])
    _write_batch(tmp_path / "batch_1.json", [(str(i), body) for i in range(3)])
    _write_scenarios_csv(tmp_path / "batch_1.csv", [0, 1, 2])

    df = prepare_training_files(tmp_path, n_examples=4)
    assert len(df) == 4


def test_prepare_training_files_empty_dir(tmp_path: Path) -> None:
    from recode.training.pipeline import prepare_training_files

    df = prepare_training_files(tmp_path)
    assert df.empty


def test_prepare_training_files_skips_unindexed_filename(tmp_path: Path) -> None:
    from recode.training.pipeline import prepare_training_files

    # Filename with no digits — should be skipped with a warning, not crash.
    body = _make_body("CR", "Insuffisance cardiaque", "I500", "ICC", 65)
    _write_batch(tmp_path / "batch_X.json", [("0", body)])
    _write_scenarios_csv(tmp_path / "batch_X.csv", [0])

    df = prepare_training_files(tmp_path)
    assert df.empty


def test_prepare_training_files_warns_on_missing_csv(tmp_path: Path) -> None:
    from recode.training.pipeline import prepare_training_files

    body = _make_body("CR", "Insuffisance cardiaque", "I500", "ICC", 65)
    _write_batch(tmp_path / "batch_0.json", [("0", body)])
    # No matching batch_0.csv — branch skips this batch.

    df = prepare_training_files(tmp_path)
    assert df.empty
