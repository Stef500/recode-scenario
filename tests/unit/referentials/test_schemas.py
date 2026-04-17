"""Tests for Pandera schemas."""

from __future__ import annotations

import pandas as pd
import pandera.errors as pae
import pytest


def test_icd_official_schema_validates_good_df() -> None:
    from recode.referentials.schemas import IcdOfficialSchema

    df = pd.DataFrame(
        [
            {"icd_code": "C509", "icd_code_description": "Tumeur sein", "aut_mco": 1},
            {"icd_code": "E110", "icd_code_description": "Diabète", "aut_mco": 1},
        ]
    )
    validated = IcdOfficialSchema.validate(df)
    assert len(validated) == 2


def test_icd_official_schema_rejects_bad_code() -> None:
    from recode.referentials.schemas import IcdOfficialSchema

    df = pd.DataFrame([{"icd_code": "INVALID", "icd_code_description": "bad", "aut_mco": 1}])
    with pytest.raises(pae.SchemaError):
        IcdOfficialSchema.validate(df)


def test_drg_statistics_schema() -> None:
    from recode.referentials.schemas import DrgStatisticsSchema

    df = pd.DataFrame(
        [
            {"drg_parent_code": "09C04", "los_mean": 4.5, "los_sd": 1.5},
            {"drg_parent_code": "14Z10", "los_mean": 3.2, "los_sd": 0.8},
        ]
    )
    DrgStatisticsSchema.validate(df)


def test_drg_statistics_rejects_negative_los() -> None:
    from recode.referentials.schemas import DrgStatisticsSchema

    df = pd.DataFrame([{"drg_parent_code": "09C04", "los_mean": -1.0, "los_sd": 1.5}])
    with pytest.raises(pae.SchemaError):
        DrgStatisticsSchema.validate(df)
