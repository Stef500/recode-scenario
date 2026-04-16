"""Tests for derive_scenario_rng."""

from __future__ import annotations

import numpy as np


def _make_profile(**overrides):  # type: ignore[no-untyped-def]
    from recode.models import Profile

    defaults = {
        "drg_parent_code": "09C04",
        "icd_primary_code": "C509",
        "case_management_type": "C509",
        "age_class": "[40-50[",
        "age_class_2": "[18-50[",
        "gender": 2,
        "weight": 100,
        "admission_type": "Inpatient",
    }
    defaults.update(overrides)
    return Profile(**defaults)


def test_rng_reproducible_same_seed_same_profile() -> None:
    from recode.scenarios.rng import derive_scenario_rng

    rng1 = derive_scenario_rng(_make_profile(), base_seed=42)
    rng2 = derive_scenario_rng(_make_profile(), base_seed=42)
    assert [int(rng1.integers(0, 10**6)) for _ in range(5)] == [
        int(rng2.integers(0, 10**6)) for _ in range(5)
    ]


def test_rng_differs_different_seed() -> None:
    from recode.scenarios.rng import derive_scenario_rng

    rng1 = derive_scenario_rng(_make_profile(), base_seed=42)
    rng2 = derive_scenario_rng(_make_profile(), base_seed=43)
    assert [int(rng1.integers(0, 10**6)) for _ in range(5)] != [
        int(rng2.integers(0, 10**6)) for _ in range(5)
    ]


def test_rng_differs_different_profile() -> None:
    from recode.scenarios.rng import derive_scenario_rng

    p1 = _make_profile(icd_primary_code="C509")
    p2 = _make_profile(icd_primary_code="C349")
    rng1 = derive_scenario_rng(p1, base_seed=42)
    rng2 = derive_scenario_rng(p2, base_seed=42)
    assert [int(rng1.integers(0, 10**6)) for _ in range(5)] != [
        int(rng2.integers(0, 10**6)) for _ in range(5)
    ]


def test_rng_returns_numpy_generator() -> None:
    from recode.scenarios.rng import derive_scenario_rng

    rng = derive_scenario_rng(_make_profile(), base_seed=0)
    assert isinstance(rng, np.random.Generator)
