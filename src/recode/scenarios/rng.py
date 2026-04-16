"""Per-scenario RNG derivation for reproducible, parallel-safe generation."""

from __future__ import annotations

import hashlib

import numpy as np

from recode.models import Profile


def derive_scenario_rng(profile: Profile, base_seed: int) -> np.random.Generator:
    """Derive a ``numpy.random.Generator`` unique to ``(profile, base_seed)``.

    Combining a stable hash of profile identity with ``base_seed`` via a
    multiplicative mix ensures that:

    - same profile + same seed → same RNG state (reproducibility).
    - different profiles or seeds → uncorrelated RNG states (no bias).
    - generation order is irrelevant (parallel-safe).

    Args:
        profile: Profile to derive RNG for.
        base_seed: Base seed controlling the run.

    Returns:
        A fresh ``numpy.random.Generator`` seeded deterministically.
    """
    profile_key = (
        f"{profile.icd_primary_code}|{profile.drg_parent_code}|"
        f"{profile.case_management_type}|{profile.gender}|{profile.age_class}"
    )
    digest = hashlib.blake2b(profile_key.encode(), digest_size=8).digest()
    profile_hash = int.from_bytes(digest, "big")
    seed = (base_seed * 2_654_435_761) ^ profile_hash
    return np.random.default_rng(seed & 0xFFFFFFFF)
