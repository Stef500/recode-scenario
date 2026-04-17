"""Cancer-specific context (treatment recommendation lookup)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from recode.models import CancerContext, Profile
from recode.referentials import ReferentialRegistry

_TREATMENT_TRIGGER_CMT = frozenset({"DP", "Z511"})

# Sentinel strings used in the ATIH treatment table to mean "inapplicable";
# we surface them as None rather than literal strings.
_SENTINEL_VALUES = frozenset({"Variable", "Non pertinent"})

# Shared empty instance — safe because CancerContext is frozen.
_EMPTY_CANCER = CancerContext(
    histological_type=None,
    score_tnm=None,
    stage=None,
    biomarkers=None,
    treatment_recommendation=None,
    chemotherapy_regimen=None,
)


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


def _keep_or_none(value: Any) -> str | None:
    """Drop ATIH sentinel values ('Variable' / 'Non pertinent') → None, else str."""
    if value in _SENTINEL_VALUES:
        return None
    return None if value is None else str(value)


def _nan_to_none(value: Any) -> str | None:
    """Normalize pandas NaN to None for optional string fields."""
    return None if pd.isna(value) else str(value)


def _cancer_context_from_row(row: pd.Series) -> CancerContext:
    """Build a CancerContext from a single treatment-recommendation row."""
    tnm = row.get("tnm") if "tnm" in row.index else None
    return CancerContext(
        histological_type=str(row["histological_type"]),
        score_tnm=_keep_or_none(tnm),
        stage=_keep_or_none(row.get("stage")),
        biomarkers=_nan_to_none(row.get("biomarkers")),
        treatment_recommendation=str(row["treatment_recommendation"]),
        chemotherapy_regimen=_nan_to_none(row.get("chemotherapy_regimen")),
    )


def build_cancer_context(
    profile: Profile, registry: ReferentialRegistry, rng: np.random.Generator
) -> CancerContext | None:
    """Return a CancerContext when the profile is cancer-related, else None.

    Semantics preserved from ``utils_v2.py:993-1014``:

    - non-cancer primary → ``None``
    - cancer primary with ``case_management_type`` in ``{DP, Z511}`` → try to
      load a treatment recommendation; drops the ATIH sentinel values
      ``"Variable"`` and ``"Non pertinent"`` for TNM/stage.
    - cancer primary but different ``case_management_type`` → empty CancerContext.
    - cancer primary with no matching treatment row → empty CancerContext.
    """
    if not is_cancer(profile, registry):
        return None
    if profile.case_management_type not in _TREATMENT_TRIGGER_CMT:
        return _EMPTY_CANCER
    row_df = _sample_treatment_row(profile, registry, rng)
    if row_df.empty:
        return _EMPTY_CANCER
    return _cancer_context_from_row(row_df.iloc[0])
