"""CCAM procedure sampling."""

from __future__ import annotations

import numpy as np

from recode.models import Procedure, Profile
from recode.referentials import ReferentialRegistry
from recode.scenarios.diagnosis import _weighted_sample


def _procedure_description(registry: ReferentialRegistry, code: str) -> str:
    df = registry.procedure_official
    match = df.loc[df["procedure"] == code, "procedure_description"]
    return str(match.iloc[0]) if not match.empty else ""


def sample_procedure(
    profile: Profile, registry: ReferentialRegistry, rng: np.random.Generator
) -> Procedure:
    """Sample one CCAM procedure for the profile (or empty Procedure).

    Excludes pathology procedures (``Examen anatomopathologique``) per the
    original utils_v2 behaviour.
    """
    pool = registry.procedures
    pathology = set(registry.pathology_procedures)
    pool = pool[~pool["procedure"].isin(pathology)]

    if pool.empty:
        return Procedure(code="", description="")

    sampled = _weighted_sample(pool, profile, rng, max_nb=1, nb=1)
    if sampled.empty:
        return Procedure(code="", description="")

    code = str(sampled["procedure"].iloc[0])
    return Procedure(code=code, description=_procedure_description(registry, code))
