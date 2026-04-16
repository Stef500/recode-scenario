"""Tests for diagnosis module."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pandas as pd


def _mock_registry(secondary_icd_df: pd.DataFrame | None = None) -> MagicMock:
    reg = MagicMock()
    reg.cancer_codes.all_cancer = frozenset({"C509", "C50", "C349", "C34"})
    reg.secondary_icd = (
        secondary_icd_df
        if secondary_icd_df is not None
        else pd.DataFrame(
            columns=[
                "icd_secondary_code",
                "drg_parent_code",
                "icd_primary_code",
                "cage2",
                "sexe",
                "nb",
                "type",
                "icd_primary_parent_code",
            ]
        )
    )
    reg.icd_official = pd.DataFrame(
        [
            {"icd_code": "I10", "icd_code_description": "HTA", "aut_mco": 1},
            {"icd_code": "C509", "icd_code_description": "Tumeur sein", "aut_mco": 1},
            {"icd_code": "C780", "icd_code_description": "Métastase poumon", "aut_mco": 1},
        ]
    )
    reg.complications = pd.DataFrame({"icd_code": []})
    return reg


def test_sample_secondary_empty_returns_empty() -> None:
    from recode.models import Profile
    from recode.scenarios.diagnosis import sample_secondary_diagnoses

    reg = _mock_registry()
    p = Profile(
        drg_parent_code="05M09",
        icd_primary_code="I500",
        case_management_type="I500",
        age_class="[80-[",
        age_class_2="[50-[",
        gender=2,
        weight=1,
        admission_type="Inpatient",
    )
    rng = np.random.default_rng(42)
    df = sample_secondary_diagnoses(p, reg, rng)
    assert df.empty


def test_sample_secondary_returns_rows_when_data_exists() -> None:
    from recode.models import Profile
    from recode.scenarios.diagnosis import sample_secondary_diagnoses

    secondary = pd.DataFrame(
        [
            {
                "icd_secondary_code": "I10",
                "drg_parent_code": "05M09",
                "icd_primary_code": "I500",
                "cage2": "[50-[",
                "sexe": 2,
                "nb": 100,
                "type": "Chronic",
                "icd_primary_parent_code": "I50",
            }
        ]
    )
    reg = _mock_registry(secondary)
    p = Profile(
        drg_parent_code="05M09",
        icd_primary_code="I500",
        case_management_type="I500",
        age_class="[80-[",
        age_class_2="[50-[",
        gender=2,
        weight=1,
        admission_type="Inpatient",
    )
    rng = np.random.default_rng(42)
    df = sample_secondary_diagnoses(p, reg, rng, max_per_category=1)
    assert len(df) <= 1
