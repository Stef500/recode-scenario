"""Cancer-specific context (treatment recommendation lookup)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from recode.models import CancerContext, Profile
from recode.referentials import ReferentialRegistry

_TREATMENT_TRIGGER_CMT = frozenset({"DP", "Z511"})


def is_cancer(profile: Profile, registry: ReferentialRegistry) -> bool:
    """Whether the primary diagnosis falls under cancer codes."""
    return profile.icd_primary_code in registry.cancer_codes.all_cancer


def _sample_treatment_row(
    profile: Profile, registry: ReferentialRegistry, rng: np.random.Generator
) -> pd.DataFrame:
    """Sample one treatment recommendation matching the profile's parent code."""
    parent_code = profile.icd_primary_parent_code or profile.icd_primary_code[:3]
    matches = registry.cancer_treatments[
        registry.cancer_treatments["icd_parent_code"] == parent_code
    ]
    if matches.empty:
        return matches
    state = int(rng.integers(0, 2**31))
    return matches.sample(n=1, random_state=state)


def build_cancer_context(
    profile: Profile, registry: ReferentialRegistry, rng: np.random.Generator
) -> CancerContext | None:
    """Return a CancerContext when the profile is cancer-related, else None.

    Semantics preserved from utils_v2.py:993-1014:
    - non-cancer primary → None
    - cancer primary with case_management_type in {DP, Z511} → try to load
      treatment recommendation, keeping only non-"Variable"/"Non pertinent"
      TNM/stage
    - cancer primary but different case_management_type → CancerContext with
      all None
    """
    if not is_cancer(profile, registry):
        return None

    empty = CancerContext(
        histological_type=None,
        score_tnm=None,
        stage=None,
        biomarkers=None,
        treatment_recommendation=None,
        chemotherapy_regimen=None,
    )

    if profile.case_management_type not in _TREATMENT_TRIGGER_CMT:
        return empty

    row_df = _sample_treatment_row(profile, registry, rng)
    if row_df.empty:
        return empty
    row = row_df.iloc[0]

    tnm = row.get("tnm") if "tnm" in row.index else None
    stage = row.get("stage")
    score_tnm = tnm if tnm not in ("Variable", "Non pertinent") else None
    kept_stage = stage if stage not in ("Variable", "Non pertinent") else None

    chemo = row.get("chemotherapy_regimen")
    if pd.isna(chemo):
        chemo = None

    biomarkers = row.get("biomarkers")
    if pd.isna(biomarkers):
        biomarkers = None

    return CancerContext(
        histological_type=str(row["histological_type"]),
        score_tnm=score_tnm,
        stage=kept_stage,
        biomarkers=biomarkers,
        treatment_recommendation=str(row["treatment_recommendation"]),
        chemotherapy_regimen=chemo,
    )
