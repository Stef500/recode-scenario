"""Tests for procedures module."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pandas as pd


def _mock_registry(procedures_df: pd.DataFrame | None = None) -> MagicMock:
    reg = MagicMock()
    reg.procedure_official = pd.DataFrame(
        [
            {"procedure": "JQGA004", "procedure_description": "Césarienne"},
            {"procedure": "DAFA001", "procedure_description": "Examen anatomopathologique"},
        ]
    )
    reg.procedures = (
        procedures_df
        if procedures_df is not None
        else pd.DataFrame(
            columns=["procedure", "drg_parent_code", "icd_primary_code", "cage2", "sexe", "nb"]
        )
    )
    reg.pathology_procedures = pd.Series(["DAFA001"])
    return reg


def test_sample_procedure_empty_returns_empty() -> None:
    from recode.models import Profile
    from recode.scenarios.procedures import sample_procedure

    p = Profile(
        drg_parent_code="14C06",
        icd_primary_code="O829",
        case_management_type="O829",
        age_class="[30-40[",
        age_class_2="[18-50[",
        gender=2,
        weight=1,
        admission_type="Inpatient",
    )
    rng = np.random.default_rng(42)
    proc = sample_procedure(p, _mock_registry(), rng)
    assert proc.code == ""
    assert proc.description == ""


def test_sample_procedure_returns_procedure_when_available() -> None:
    from recode.models import Profile
    from recode.scenarios.procedures import sample_procedure

    procs = pd.DataFrame(
        [
            {
                "procedure": "JQGA004",
                "drg_parent_code": "14C06",
                "icd_primary_code": "O829",
                "cage2": "[18-50[",
                "sexe": 2,
                "nb": 50,
            }
        ]
    )
    reg = _mock_registry(procs)
    p = Profile(
        drg_parent_code="14C06",
        icd_primary_code="O829",
        case_management_type="O829",
        age_class="[30-40[",
        age_class_2="[18-50[",
        gender=2,
        weight=1,
        admission_type="Inpatient",
    )
    rng = np.random.default_rng(42)
    proc = sample_procedure(p, reg, rng)
    assert proc.code == "JQGA004"
    assert "Césarienne" in proc.description
