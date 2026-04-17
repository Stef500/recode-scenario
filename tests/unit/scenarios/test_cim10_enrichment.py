"""Tests for scenarios.cim10_enrichment."""

from __future__ import annotations

import pandas as pd


def _make_hierarchy_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "code": ["I", "A00-A09", "A04", "A048"],
            "level": ["chapter", "block", "category", "leaf"],
            "parent_code": ["", "I", "A00-A09", "A04"],
            "label": ["Chap", "Bloc", "Cat", "Leaf"],
            "chapter_code": ["", "", "", "I"],
            "chapter_label": ["", "", "", "Mal. inf."],
            "block_code": ["", "", "", "A00-A09"],
            "block_label": ["", "", "", "Intest."],
            "category_code": ["", "", "", "A04"],
            "category_label": ["", "", "", "Autres inf."],
        }
    )


def _make_notes_df() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "code": ["A048", "E119"],
            "inclusion_notes": ["a|b|c", ""],
            "exclusion_notes": ["", "x|y"],
        }
    )


def test_build_lookups_filters_to_leaf() -> None:
    from recode.scenarios.cim10_enrichment import build_lookups

    h, _ = build_lookups(_make_hierarchy_df(), _make_notes_df())
    assert list(h.keys()) == ["A048"]  # only the leaf


def test_build_lookups_hierarchy_row_shape() -> None:
    from recode.scenarios.cim10_enrichment import build_lookups

    h, _ = build_lookups(_make_hierarchy_df(), _make_notes_df())
    row = h["A048"]
    assert row["chapter_code"] == "I"
    assert row["chapter_label"] == "Mal. inf."
    assert row["block_code"] == "A00-A09"
    assert row["block_label"] == "Intest."
    assert row["category_code"] == "A04"
    assert row["category_label"] == "Autres inf."


def test_build_lookups_notes_split_pipe() -> None:
    from recode.scenarios.cim10_enrichment import build_lookups

    _, n = build_lookups(_make_hierarchy_df(), _make_notes_df())
    assert n["A048"]["inclusion_notes"] == ["a", "b", "c"]
    assert n["A048"]["exclusion_notes"] == []
    assert n["E119"]["inclusion_notes"] == []
    assert n["E119"]["exclusion_notes"] == ["x", "y"]


def test_build_lookups_empty_dfs() -> None:
    from recode.scenarios.cim10_enrichment import build_lookups

    h, n = build_lookups(
        pd.DataFrame(
            columns=[
                "code",
                "level",
                "parent_code",
                "label",
                "chapter_code",
                "chapter_label",
                "block_code",
                "block_label",
                "category_code",
                "category_label",
            ]
        ),
        pd.DataFrame(columns=["code", "inclusion_notes", "exclusion_notes"]),
    )
    assert h == {}
    assert n == {}


def test_format_hierarchy_only_no_notes() -> None:
    from recode.scenarios.cim10_enrichment import format_cim10_enrichment

    hierarchy = {
        "E119": {
            "chapter_code": "IV",
            "chapter_label": "Maladies endocriniennes",
            "block_code": "E10-E14",
            "block_label": "Diabète sucré",
            "category_code": "E11",
            "category_label": "Diabète sucré de type 2",
        }
    }
    notes: dict = {}
    result = format_cim10_enrichment("E119", hierarchy, notes)

    expected = (
        "     Hiérarchie : Chapitre IV — Maladies endocriniennes\n"
        "                  > Bloc E10-E14 — Diabète sucré\n"
        "                  > Catégorie E11 — Diabète sucré de type 2\n"
    )
    assert result == expected


def test_format_unknown_code_returns_empty() -> None:
    from recode.scenarios.cim10_enrichment import format_cim10_enrichment

    assert format_cim10_enrichment("ZZZZ", {}, {}) == ""
