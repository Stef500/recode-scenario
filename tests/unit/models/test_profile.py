"""Tests for Profile model."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def _valid_payload() -> dict[str, object]:
    return {
        "drg_parent_code": "09C04",
        "icd_primary_code": "C509",
        "case_management_type": "C509",
        "age_class": "[40-50[",
        "age_class_2": "[18-50[",
        "gender": 2,
        "weight": 100,
        "admission_type": "Inpatient",
    }


def test_profile_minimal_valid() -> None:
    from recode.models import Profile

    p = Profile(**_valid_payload())  # type: ignore[arg-type]
    assert p.drg_parent_code == "09C04"
    assert p.gender == 2


def test_profile_serializes_with_csv_aliases() -> None:
    from recode.models import Profile

    p = Profile(**_valid_payload())  # type: ignore[arg-type]
    d = p.model_dump(by_alias=True)
    assert d["cage"] == "[40-50["
    assert d["cage2"] == "[18-50["
    assert d["sexe"] == 2
    assert d["nb"] == 100


def test_profile_accepts_input_with_legacy_aliases() -> None:
    from recode.models import Profile

    p = Profile.model_validate(
        {
            "drg_parent_code": "09C04",
            "icd_primary_code": "C509",
            "case_management_type": "C509",
            "cage": "[40-50[",
            "cage2": "[18-50[",
            "sexe": 2,
            "nb": 100,
            "admission_type": "Inpatient",
        }
    )
    assert p.age_class == "[40-50["


def test_profile_frozen() -> None:
    from recode.models import Profile

    p = Profile(**_valid_payload())  # type: ignore[arg-type]
    with pytest.raises(ValidationError):
        p.gender = 1  # type: ignore[misc]


def test_profile_rejects_invalid_admission_type() -> None:
    from recode.models import Profile

    payload = _valid_payload() | {"admission_type": "Invalid"}
    with pytest.raises(ValidationError):
        Profile(**payload)  # type: ignore[arg-type]
