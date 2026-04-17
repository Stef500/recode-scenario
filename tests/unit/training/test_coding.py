"""Tests for training.coding extract_target."""

from __future__ import annotations

import pandas as pd


def test_extract_target_dp_case() -> None:
    from recode.training.coding import extract_target

    case = pd.Series(
        {
            "case_management_type": "DP",
            "case_management_type_description": "ICC",
            "icd_primary_code": "I500",
            "response_diagnosis": {
                "Insuffisance cardiaque (I500)": ["ICC"],
                "Hypertension (I10)": ["HTA"],
            },
        }
    )
    target = extract_target(case)
    assert target.icd_primary_pred == "I500"
    assert target.icd_secondary_pred == ["I10"]
    assert "Aucun" in target.coding_text


def test_extract_target_non_dp_includes_cmt() -> None:
    from recode.training.coding import extract_target

    case = pd.Series(
        {
            "case_management_type": "Z511",
            "case_management_type_description": "Chimiothérapie",
            "icd_primary_code": "Z511",
            "response_diagnosis": {
                "Chimiothérapie (Z511)": ["chimio"],
                "Cancer sein (C509)": ["cancer"],
            },
        }
    )
    target = extract_target(case)
    assert "Z511" in target.coding_text
    assert "Chimiothérapie" in target.coding_text
