"""Compare legacy utils_v2 vs new recode pipeline on the fixture profiles.

Runs both code paths on ``tests/fixtures/profiles.parquet`` with ``base_seed=42``
and diffs column-by-column. Exits non-zero on any divergence (outside the
columns expected to differ due to new RNG paths).

Usage::

    uv run python scripts/compare_outputs.py
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, "src")
sys.path.insert(0, "arXiv/legacy_v2")
sys.path.insert(0, ".")

FIXTURES = Path("tests/fixtures")
REF = FIXTURES / "referentials"
BASE_SEED = 42


def _build_legacy() -> pd.DataFrame:
    from scripts.generate_golden import _PREFIX_CANCER, _PREFIX_NON_CANCER, setup_generator
    from utils_v2 import derive_scenario_rng

    gs = setup_generator()
    profiles = pd.read_parquet(FIXTURES / "profiles.parquet")
    rows: list[dict] = []
    for _, raw in profiles.iterrows():
        profile = raw.copy()
        rng = derive_scenario_rng(profile, base_seed=BASE_SEED)
        scenario = gs.generate_scenario_from_profile(profile, rng=rng)
        user_prompt = gs.make_prompts_marks_from_scenario(scenario)
        try:
            system_prompt = gs.create_system_prompt(scenario)
        except (FileNotFoundError, OSError):
            system_prompt = ""
        prefix = (
            _PREFIX_CANCER
            if scenario["icd_primary_code"] in gs.icd_codes_cancer
            else _PREFIX_NON_CANCER
        )
        row = dict(scenario)
        row["user_prompt"] = user_prompt
        row["system_prompt"] = system_prompt
        row["prefix"] = prefix
        row["prefix_len"] = len(prefix)
        rows.append(row)
    return pd.DataFrame(rows)


def _build_new() -> pd.DataFrame:
    from recode.models import Profile
    from recode.referentials import ReferentialRegistry
    from recode.scenarios.generator import ScenarioGenerator
    from recode.scenarios.prompts import build_prefix, build_user_prompt

    reg = ReferentialRegistry(processed_dir=REF, constants_dir=REF / "constants")
    gen = ScenarioGenerator(registry=reg, base_seed=BASE_SEED)
    profiles = pd.read_parquet(FIXTURES / "profiles.parquet")
    rows: list[dict] = []
    for _, raw in profiles.iterrows():
        p = Profile.model_validate(raw.to_dict())
        s = gen.generate(p)
        row = s.to_csv_row()
        row["user_prompt"] = build_user_prompt(s)
        row["prefix"] = build_prefix(s)
        row["prefix_len"] = len(row["prefix"])
        # system_prompt reads templates/*.txt — skip if files missing in tests
        row["system_prompt"] = ""
        rows.append(row)
    return pd.DataFrame(rows)


# Columns known to diverge because the new code samples differently.
_EXPECTED_DIVERGING_COLUMNS = frozenset(
    {
        "date_entry",
        "date_discharge",
        "date_of_birth",
        "first_name",
        "last_name",
        "first_name_med",
        "last_name_med",
        "hospital",
        "department",
        "age",
        "user_prompt",
        "system_prompt",
        "text_secondary_icd_official",
        "icd_secondary_code",
        "text_procedure",
        "procedure",
        "cancer_stage",
        "score_TNM",
        "histological_type",
        "treatment_recommandation",
        "chemotherapy_regimen",
        "biomarkers",
        "case_management_type_text",
        "coding_rule",
        "case_management_description",
        "template_name",
        "los_mean",
        "los_sd",
    }
)


def main() -> None:
    legacy = _build_legacy()
    new = _build_new()
    common_cols = sorted(set(legacy.columns) & set(new.columns))
    print(f"Comparing {len(common_cols)} common columns across {len(legacy)} rows")

    strict_divergences: list[tuple[str, int]] = []
    loose_divergences: list[tuple[str, int]] = []
    for col in common_cols:
        try:
            mismatch = (legacy[col].fillna("__NA__") != new[col].fillna("__NA__")).sum()
        except TypeError:
            mismatch = (legacy[col].astype(str) != new[col].astype(str)).sum()
        if mismatch == 0:
            continue
        if col in _EXPECTED_DIVERGING_COLUMNS:
            loose_divergences.append((col, int(mismatch)))
        else:
            strict_divergences.append((col, int(mismatch)))

    if loose_divergences:
        print("\n--- Expected divergences (RNG path differences) ---")
        for col, n in loose_divergences:
            print(f"  {col}: {n} rows differ")

    if strict_divergences:
        print("\n--- UNEXPECTED DIVERGENCES ---")
        for col, n in strict_divergences:
            print(f"  {col}: {n} rows differ")
        sys.exit(1)

    print("\nOK — all profile-derived columns match between legacy and new pipelines.")


if __name__ == "__main__":
    main()
