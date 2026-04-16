"""Primary + secondary ICD diagnosis assembly."""

from __future__ import annotations

import numpy as np
import pandas as pd
from loguru import logger

from recode.models import CancerContext, Diagnosis, Profile
from recode.referentials import ReferentialRegistry


def _build_profile_query(profile: Profile, df_columns: list[str]) -> str:
    """Build a pandas query string filtering a DataFrame by matching profile fields."""
    profile_dict = profile.model_dump(by_alias=True)
    parts: list[str] = []
    for k, v in profile_dict.items():
        if k not in df_columns:
            continue
        if isinstance(v, str):
            parts.append(f"{k}=={v!r}")
        elif isinstance(v, int | float) and not pd.isna(v):
            parts.append(f"{k}=={v}")
    return " & ".join(parts)


def _weighted_sample(
    pool: pd.DataFrame,
    profile: Profile,
    rng: np.random.Generator,
    *,
    max_nb: int = 2,
    distinct_chapter: bool = False,
    nb: int | None = None,
    col_weights: str = "nb",
) -> pd.DataFrame:
    """Sample rows from ``pool`` matching ``profile``, optionally per chapter."""
    if pool.empty:
        return pd.DataFrame(columns=pool.columns)

    query = _build_profile_query(profile, list(pool.columns))
    df_sel = pool.query(query) if query else pool.copy()

    if col_weights not in df_sel.columns or df_sel[col_weights].sum() == 0:
        df_sel = df_sel.assign(**{col_weights: 1})

    if df_sel.empty:
        return pd.DataFrame(columns=pool.columns)

    n_max = int(min(len(df_sel), max_nb))
    n_final = nb if nb is not None else int(rng.integers(0, n_max + 1))
    n_final = min(n_final, len(df_sel))

    if n_final <= 0:
        return pd.DataFrame(columns=pool.columns)

    if distinct_chapter and "icd_secondary_code" in df_sel.columns:
        df_sample = pd.DataFrame(columns=df_sel.columns)
        chapters: list[str] = []
        for _ in range(n_final):
            cand = df_sel[~df_sel["icd_secondary_code"].str.slice(0, 1).isin(chapters)]
            if cand.empty:
                break
            state = int(rng.integers(0, 2**31))
            pick = cand.sample(n=1, replace=False, weights=col_weights, random_state=state)
            df_sample = pd.concat([df_sample, pick])
            chapters = df_sample["icd_secondary_code"].str.slice(0, 1).to_list()
        return df_sample

    state = int(rng.integers(0, 2**31))
    return df_sel.sample(n=n_final, replace=False, weights=col_weights, random_state=state)


def _icd_description(registry: ReferentialRegistry, code: str) -> str:
    df = registry.icd_official
    match = df.loc[df["icd_code"] == code, "icd_code_description"]
    return str(match.iloc[0]) if not match.empty else ""


def sample_secondary_diagnoses(
    profile: Profile,
    registry: ReferentialRegistry,
    rng: np.random.Generator,
    *,
    max_per_category: int = 2,
    distinct_chapter: bool = True,
) -> pd.DataFrame:
    """Sample secondary diagnoses by category: chronic, metastases, complications.

    Reproduces ``utils_v2.py:1031-1131`` but decomposed into pure calls.
    Each row of the returned frame has ``icd_secondary_code`` + description.
    """
    pool = registry.secondary_icd
    if pool.empty:
        return pd.DataFrame(columns=["icd_secondary_code", "icd_code_description_official"])

    is_cancer_primary = profile.icd_primary_code in registry.cancer_codes.all_cancer
    samples: list[pd.DataFrame] = []

    chronic_types = ["Chronic"] if is_cancer_primary else ["Chronic", "Cancer"]
    chronic_pool = pool[pool["type"].isin(chronic_types)]
    chronic = _weighted_sample(
        chronic_pool, profile, rng, max_nb=max_per_category, distinct_chapter=distinct_chapter
    )
    samples.append(chronic)

    has_cancer_secondary = (
        not chronic.empty
        and chronic["icd_secondary_code"].isin(registry.cancer_codes.all_cancer).any()
    )
    if is_cancer_primary or has_cancer_secondary:
        ln_pool = pool[pool["type"] == "Metastasis LN"]
        meta_ln = _weighted_sample(ln_pool, profile, rng, max_nb=1, nb=1)
        samples.append(meta_ln)
        meta_pool = pool[pool["type"] == "Metastasis"]
        meta = _weighted_sample(meta_pool, profile, rng, max_nb=max_per_category)
        samples.append(meta)

    acute_pool = pool[pool["type"] == "Acute"]
    acute = _weighted_sample(acute_pool, profile, rng, max_nb=max_per_category)
    samples.append(acute)

    combined = pd.concat(samples, ignore_index=True).drop_duplicates("icd_secondary_code")
    combined["icd_code_description_official"] = combined["icd_secondary_code"].map(
        lambda c: _icd_description(registry, c)
    )
    return combined


def build_diagnosis(
    profile: Profile,
    registry: ReferentialRegistry,
    cancer: CancerContext | None,
    rng: np.random.Generator,
) -> Diagnosis:
    """Assemble the Diagnosis sub-model (primary + secondary + coding rule)."""
    from recode.scenarios.coding_rules import resolve_coding_rule

    primary_desc = _icd_description(registry, profile.icd_primary_code)
    cmt_desc = _icd_description(registry, profile.case_management_type)

    secondary = sample_secondary_diagnoses(profile, registry, rng)
    secondary_text = "".join(
        f"- {row['icd_code_description_official']} ({row['icd_secondary_code']})\n"
        for _, row in secondary.iterrows()
    )

    rule_id, rule_text, _template = resolve_coding_rule(profile, cancer, registry)
    rule_description = ""
    try:
        raw = registry.coding_rules_raw
        rule_description = str(raw.get(rule_id, {}).get("texte", ""))
    except (FileNotFoundError, KeyError, ValueError) as exc:
        logger.warning("Failed to read coding rule description: {}", exc)

    return Diagnosis(
        icd_primary_code=profile.icd_primary_code,
        icd_primary_description=primary_desc,
        icd_parent_code=profile.icd_primary_code[:3],
        case_management_type=profile.case_management_type,
        case_management_type_description=cmt_desc,
        case_management_type_text=rule_text,
        icd_secondary_codes=secondary["icd_secondary_code"].tolist(),
        text_secondary_icd_official=secondary_text,
        coding_rule=rule_id,
        case_management_description=rule_description,
    )
