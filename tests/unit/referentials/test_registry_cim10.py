"""Tests for ReferentialRegistry CIM-10 extensions."""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def registry_without_cim10(tmp_path):
    from recode.referentials import ReferentialRegistry

    proc = tmp_path / "proc"
    proc.mkdir()
    const = tmp_path / "const"
    const.mkdir()
    return ReferentialRegistry(processed_dir=proc, constants_dir=const)


@pytest.fixture
def registry_with_cim10(tmp_path):
    from recode.referentials import ReferentialRegistry

    proc = tmp_path / "proc"
    proc.mkdir()
    const = tmp_path / "const"
    const.mkdir()

    pd.DataFrame(
        {
            "code": ["A048"],
            "level": ["leaf"],
            "parent_code": ["A04"],
            "label": ["l"],
            "chapter_code": ["I"],
            "chapter_label": ["ci"],
            "block_code": ["A00-A09"],
            "block_label": ["cb"],
            "category_code": ["A04"],
            "category_label": ["cc"],
        }
    ).to_parquet(proc / "cim10_hierarchy.parquet", index=False)

    pd.DataFrame(
        {
            "code": ["A048"],
            "inclusion_notes": ["x|y"],
            "exclusion_notes": [""],
        }
    ).to_parquet(proc / "cim10_notes.parquet", index=False)

    return ReferentialRegistry(processed_dir=proc, constants_dir=const)


def test_has_cim10_enrichment_false_when_missing(registry_without_cim10) -> None:
    assert registry_without_cim10.has_cim10_enrichment() is False


def test_has_cim10_enrichment_true_when_present(registry_with_cim10) -> None:
    assert registry_with_cim10.has_cim10_enrichment() is True


def test_cim10_hierarchy_cached_property(registry_with_cim10) -> None:
    df = registry_with_cim10.cim10_hierarchy
    assert list(df["code"]) == ["A048"]
    # cached_property: second access returns same object
    assert registry_with_cim10.cim10_hierarchy is df


def test_cim10_notes_cached_property(registry_with_cim10) -> None:
    df = registry_with_cim10.cim10_notes
    assert list(df["code"]) == ["A048"]


def test_cim10_lookups_builds_from_dataframes(registry_with_cim10) -> None:
    h, n = registry_with_cim10.cim10_lookups
    assert h["A048"]["chapter_code"] == "I"
    assert n["A048"]["inclusion_notes"] == ["x", "y"]


def test_cim10_lookups_cached(registry_with_cim10) -> None:
    lookups1 = registry_with_cim10.cim10_lookups
    lookups2 = registry_with_cim10.cim10_lookups
    assert lookups1 is lookups2
