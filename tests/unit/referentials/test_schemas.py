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


def test_cim10_hierarchy_schema_valid():
    from recode.referentials.schemas import Cim10HierarchySchema

    df = pd.DataFrame({
        "code": ["I", "A00-A09", "A04", "A048"],
        "level": ["chapter", "block", "category", "leaf"],
        "parent_code": ["", "I", "A00-A09", "A04"],
        "label": ["chap", "bloc", "cat", "leaf"],
        "chapter_code": ["", "", "", "I"],
        "chapter_label": ["", "", "", "Mal. inf."],
        "block_code": ["", "", "", "A00-A09"],
        "block_label": ["", "", "", "Intest."],
        "category_code": ["", "", "", "A04"],
        "category_label": ["", "", "", "Autres inf."],
    })
    validated = Cim10HierarchySchema.validate(df)
    assert len(validated) == 4


def test_cim10_hierarchy_schema_rejects_bad_level():
    from recode.referentials.schemas import Cim10HierarchySchema

    df = pd.DataFrame({
        "code": ["X"],
        "level": ["bogus"],
        "parent_code": [""],
        "label": ["x"],
        "chapter_code": [""], "chapter_label": [""],
        "block_code": [""], "block_label": [""],
        "category_code": [""], "category_label": [""],
    })
    with pytest.raises(Exception):  # pandera raises SchemaError / pandera.errors.SchemaError
        Cim10HierarchySchema.validate(df)


def test_cim10_hierarchy_schema_rejects_duplicate_code():
    from recode.referentials.schemas import Cim10HierarchySchema

    df = pd.DataFrame({
        "code": ["A048", "A048"],
        "level": ["leaf", "leaf"],
        "parent_code": ["A04", "A04"],
        "label": ["x", "x"],
        "chapter_code": ["I", "I"], "chapter_label": ["", ""],
        "block_code": ["", ""], "block_label": ["", ""],
        "category_code": ["", ""], "category_label": ["", ""],
    })
    with pytest.raises(Exception):
        Cim10HierarchySchema.validate(df)


def test_cim10_notes_schema_valid():
    from recode.referentials.schemas import Cim10NotesSchema

    df = pd.DataFrame({
        "code": ["A048", "E119"],
        "inclusion_notes": ["a|b", ""],
        "exclusion_notes": ["", "c"],
    })
    validated = Cim10NotesSchema.validate(df)
    assert len(validated) == 2


def test_cim10_notes_schema_rejects_duplicate_code():
    from recode.referentials.schemas import Cim10NotesSchema

    df = pd.DataFrame({
        "code": ["A048", "A048"],
        "inclusion_notes": ["", ""],
        "exclusion_notes": ["", ""],
    })
    with pytest.raises(Exception):
        Cim10NotesSchema.validate(df)
