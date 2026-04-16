"""Tests for cancer module."""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pandas as pd


def _mock_registry() -> MagicMock:
    reg = MagicMock()
    reg.cancer_codes.all_cancer = frozenset({"C509", "C50", "C349", "C34"})
    reg.cancer_treatments = pd.DataFrame(
        [
            {
                "icd_parent_code": "C50",
                "primary_site": "Sein",
                "histological_type": "Carcinome canalaire infiltrant",
                "stage": "II",
                "biomarkers": "RH+/HER2-",
                "treatment_recommendation": "Chirurgie + RT",
                "chemotherapy_regimen": "AC-T",
            }
        ]
    )
    return reg


def test_build_cancer_context_non_cancer_returns_none() -> None:
    from recode.models import Profile
    from recode.scenarios.cancer import build_cancer_context

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
    ctx = build_cancer_context(p, _mock_registry(), rng)
    assert ctx is None


def test_build_cancer_context_cancer_returns_context() -> None:
    from recode.models import CancerContext, Profile
    from recode.scenarios.cancer import build_cancer_context

    p = Profile(
        drg_parent_code="09C04",
        icd_primary_code="C509",
        icd_primary_parent_code="C50",
        case_management_type="C509",
        age_class="[40-50[",
        age_class_2="[18-50[",
        gender=2,
        weight=1,
        admission_type="Inpatient",
    )
    rng = np.random.default_rng(42)
    # case_management_type is not in DP/Z511 so treatment row lookup skipped
    ctx = build_cancer_context(p, _mock_registry(), rng)
    assert isinstance(ctx, CancerContext)
    assert ctx.histological_type is None


def test_build_cancer_context_with_dp_pulls_treatment() -> None:
    from recode.models import CancerContext, Profile
    from recode.scenarios.cancer import build_cancer_context

    p = Profile(
        drg_parent_code="09C04",
        icd_primary_code="C509",
        icd_primary_parent_code="C50",
        case_management_type="DP",
        age_class="[40-50[",
        age_class_2="[18-50[",
        gender=2,
        weight=1,
        admission_type="Inpatient",
    )
    rng = np.random.default_rng(42)
    ctx = build_cancer_context(p, _mock_registry(), rng)
    assert isinstance(ctx, CancerContext)
    assert ctx.histological_type == "Carcinome canalaire infiltrant"
    assert ctx.treatment_recommendation == "Chirurgie + RT"
