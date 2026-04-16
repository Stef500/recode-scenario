"""Tests for demographics module."""

from __future__ import annotations

import datetime

import numpy as np
import pytest
from hypothesis import given
from hypothesis import strategies as st


def test_parse_age_class_bounded() -> None:
    from recode.scenarios.demographics import _parse_age_class

    assert _parse_age_class("[40-50[") == (40, 50)
    assert _parse_age_class("[0-1[") == (0, 1)


def test_parse_age_class_open_upper() -> None:
    from recode.scenarios.demographics import _parse_age_class

    assert _parse_age_class("[80-[") == (80, 90)


def test_parse_age_class_invalid() -> None:
    from recode.scenarios.demographics import _parse_age_class

    with pytest.raises(ValueError, match="Invalid age_class"):
        _parse_age_class("invalid")


def test_sample_age_in_range() -> None:
    from recode.scenarios.demographics import sample_age

    rng = np.random.default_rng(42)
    for _ in range(100):
        age = sample_age("[40-50[", rng)
        assert 40 <= age <= 50


def test_random_date_in_year() -> None:
    from recode.scenarios.demographics import random_date_in_year

    rng = np.random.default_rng(0)
    for _ in range(50):
        d = random_date_in_year(2025, rng, exclude_weekends=False)
        assert d.year == 2025


def test_random_date_excludes_weekends() -> None:
    from recode.scenarios.demographics import random_date_in_year

    rng = np.random.default_rng(0)
    for _ in range(30):
        d = random_date_in_year(2025, rng, exclude_weekends=True)
        assert d.weekday() < 5


def test_random_date_between_bounded() -> None:
    from recode.scenarios.demographics import random_date_between

    rng = np.random.default_rng(0)
    start = datetime.date(2025, 1, 1)
    end = datetime.date(2025, 12, 31)
    for _ in range(50):
        d = random_date_between(start, end, rng)
        assert start <= d <= end


@given(
    start=st.dates(min_value=datetime.date(2000, 1, 1), max_value=datetime.date(2030, 1, 1)),
    delta_days=st.integers(min_value=0, max_value=3650),
)
def test_random_date_between_property(start: datetime.date, delta_days: int) -> None:
    from recode.scenarios.demographics import random_date_between

    rng = np.random.default_rng(123)
    end = start + datetime.timedelta(days=delta_days)
    d = random_date_between(start, end, rng)
    assert start <= d <= end


def test_compute_stay_dates_outpatient_same_day() -> None:
    from recode.models import Profile
    from recode.scenarios.demographics import compute_stay_dates

    p = Profile(
        drg_parent_code="02C05",
        icd_primary_code="H251",
        case_management_type="H251",
        age_class="[70-80[",
        age_class_2="[50-[",
        gender=2,
        weight=1,
        admission_type="Outpatient",
    )
    rng = np.random.default_rng(42)
    entry, discharge = compute_stay_dates(p, 2025, rng)
    assert entry == discharge


def test_compute_stay_dates_inpatient_uses_los() -> None:
    from recode.models import Profile
    from recode.scenarios.demographics import compute_stay_dates

    p = Profile(
        drg_parent_code="05M09",
        icd_primary_code="I500",
        case_management_type="I500",
        age_class="[80-[",
        age_class_2="[50-[",
        gender=2,
        weight=1,
        admission_type="Inpatient",
        length_of_stay=7,
    )
    rng = np.random.default_rng(42)
    entry, discharge = compute_stay_dates(p, 2025, rng)
    assert (discharge - entry).days == 7
