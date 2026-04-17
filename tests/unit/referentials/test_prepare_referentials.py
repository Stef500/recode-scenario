"""Tests for scripts.prepare_referentials CIM-10 functions."""

from __future__ import annotations

import sys

import pandas as pd
import pytest

sys.path.insert(0, "scripts")


@pytest.fixture
def tmp_pipeline(tmp_path, monkeypatch):
    raw = tmp_path / "raw" / "CIM_ATIH_2025"
    raw.mkdir(parents=True)
    out = tmp_path / "processed"
    out.mkdir()
    monkeypatch.chdir(tmp_path)
    # Les constantes RAW / OUT sont relatives au cwd via Path("referentials/...")
    (tmp_path / "referentials").mkdir()
    (tmp_path / "referentials" / "raw").symlink_to(tmp_path / "raw")
    (tmp_path / "referentials" / "processed").symlink_to(tmp_path / "processed")
    return raw, out


def test_prepare_cim10_hierarchy_writes_parquet(tmp_pipeline) -> None:
    raw, out = tmp_pipeline

    pd.DataFrame(
        {
            "code": ["A048"],
            "level": ["leaf"],
            "parent_code": ["A04"],
            "label": ["lab"],
            "chapter_code": ["I"],
            "chapter_label": ["c"],
            "block_code": ["b"],
            "block_label": ["b"],
            "category_code": ["c"],
            "category_label": ["c"],
        }
    ).to_csv(raw / "cim10_hierarchy.csv", index=False)

    from prepare_referentials import prepare_cim10_hierarchy

    prepare_cim10_hierarchy()

    result = pd.read_parquet(out / "cim10_hierarchy.parquet")
    assert list(result["code"]) == ["A048"]


def test_prepare_cim10_notes_writes_parquet(tmp_pipeline) -> None:
    raw, out = tmp_pipeline

    pd.DataFrame(
        {
            "code": ["A048"],
            "inclusion_notes": ["a|b"],
            "exclusion_notes": [""],
        }
    ).to_csv(raw / "cim10_notes.csv", index=False)

    from prepare_referentials import prepare_cim10_notes

    prepare_cim10_notes()

    result = pd.read_parquet(out / "cim10_notes.parquet")
    assert list(result["code"]) == ["A048"]
    assert result.loc[0, "inclusion_notes"] == "a|b"


def test_prepare_cim10_notes_empty_strings_not_na(tmp_pipeline) -> None:
    """pd.read_csv must not turn empty strings into NaN (schema rejects NaN in str)."""
    raw, out = tmp_pipeline

    pd.DataFrame(
        {
            "code": ["A048", "E119"],
            "inclusion_notes": ["a", ""],
            "exclusion_notes": ["", "b"],
        }
    ).to_csv(raw / "cim10_notes.csv", index=False)

    from prepare_referentials import prepare_cim10_notes

    prepare_cim10_notes()

    result = pd.read_parquet(out / "cim10_notes.parquet")
    assert result.loc[1, "inclusion_notes"] == ""
    assert result.loc[0, "exclusion_notes"] == ""
