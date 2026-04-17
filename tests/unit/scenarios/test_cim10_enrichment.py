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


def test_format_full_dp_with_hierarchy_and_notes() -> None:
    from recode.scenarios.cim10_enrichment import format_cim10_enrichment

    hierarchy = {
        "A048": {
            "chapter_code": "I",
            "chapter_label": "Maladies infectieuses et parasitaires",
            "block_code": "A00-A09",
            "block_label": "Maladies intestinales infectieuses",
            "category_code": "A04",
            "category_label": "Autres infections intestinales bactériennes",
        }
    }
    notes = {
        "A048": {
            "inclusion_notes": ["infections à Clostridium", "infections à Yersinia"],
            "exclusion_notes": ["intoxication alimentaire bactérienne (A05.-)"],
        }
    }
    result = format_cim10_enrichment("A048", hierarchy, notes)

    expected = (
        "     Hiérarchie : Chapitre I — Maladies infectieuses et parasitaires\n"
        "                  > Bloc A00-A09 — Maladies intestinales infectieuses\n"
        "                  > Catégorie A04 — Autres infections intestinales bactériennes\n"
        "     Inclus : infections à Clostridium ; infections à Yersinia\n"
        "     Exclus : intoxication alimentaire bactérienne (A05.-)\n"
    )
    assert result == expected


def test_format_notes_only_no_hierarchy() -> None:
    from recode.scenarios.cim10_enrichment import format_cim10_enrichment

    hierarchy: dict = {}
    notes = {
        "Z999": {
            "inclusion_notes": ["only-inclusion"],
            "exclusion_notes": [],
        }
    }
    result = format_cim10_enrichment("Z999", hierarchy, notes)
    assert result == "     Inclus : only-inclusion\n"


def test_format_empty_notes_row_treated_as_no_notes() -> None:
    """A notes row with both lists empty (after split filter) yields no lines."""
    from recode.scenarios.cim10_enrichment import format_cim10_enrichment

    hierarchy: dict = {}
    notes = {"A048": {"inclusion_notes": [], "exclusion_notes": []}}
    assert format_cim10_enrichment("A048", hierarchy, notes) == ""


def test_is_enrichable_das_true_for_four_char_ending_eight() -> None:
    from recode.scenarios.cim10_enrichment import is_enrichable_das

    assert is_enrichable_das("A048") is True
    assert is_enrichable_das("E118") is True


def test_is_enrichable_das_false_otherwise() -> None:
    from recode.scenarios.cim10_enrichment import is_enrichable_das

    assert is_enrichable_das("A04") is False  # 3 chars
    assert is_enrichable_das("A0480") is False  # 5 chars
    assert is_enrichable_das("E119") is False  # ends in 9
    assert is_enrichable_das("") is False  # empty
