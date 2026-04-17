"""Format CIM-10 enrichment blocks for prompt injection.

Provides hierarchy + inclusion/exclusion notes lookups for injection into the
'Codage CIM10' section of the user prompt.
"""

from __future__ import annotations

from typing import TypedDict

import pandas as pd


class _HierarchyRow(TypedDict):
    chapter_code: str
    chapter_label: str
    block_code: str
    block_label: str
    category_code: str
    category_label: str


class _NotesRow(TypedDict):
    inclusion_notes: list[str]
    exclusion_notes: list[str]


def build_lookups(
    hierarchy_df: pd.DataFrame,
    notes_df: pd.DataFrame,
) -> tuple[dict[str, _HierarchyRow], dict[str, _NotesRow]]:
    """DataFrame → O(1) lookup dicts.

    Filters the hierarchy to ``level == "leaf"``; only leaf codes are looked
    up at prompt format time. Notes stored as ``"|"``-joined strings are split
    back into lists.
    """
    hierarchy: dict[str, _HierarchyRow] = {
        row["code"]: {
            "chapter_code": row["chapter_code"],
            "chapter_label": row["chapter_label"],
            "block_code": row["block_code"],
            "block_label": row["block_label"],
            "category_code": row["category_code"],
            "category_label": row["category_label"],
        }
        for row in hierarchy_df.to_dict("records")
        if row["level"] == "leaf"
    }
    notes: dict[str, _NotesRow] = {
        row["code"]: {
            "inclusion_notes": [s for s in row["inclusion_notes"].split("|") if s],
            "exclusion_notes": [s for s in row["exclusion_notes"].split("|") if s],
        }
        for row in notes_df.to_dict("records")
    }
    return hierarchy, notes


def format_cim10_enrichment(
    code: str,
    hierarchy: dict[str, _HierarchyRow],
    notes: dict[str, _NotesRow],
) -> str:
    r"""Return the multi-line enrichment block for an ICD-10 leaf code.

    Lines appear in this order, each indented with 5 spaces, each terminated
    by ``\n``:

    - ``Hiérarchie : Chapitre X — label`` (if chapter_code known)
    - ``                 > Bloc B — label`` (if block_code known)
    - ``                 > Catégorie C — label`` (if category_code known)
    - ``Inclus : a ; b ; c`` (if any inclusion note)
    - ``Exclus : a ; b`` (if any exclusion note)

    Returns ``""`` when neither hierarchy nor notes are available — caller
    can unconditionally append the result.
    """
    lines: list[str] = []

    h = hierarchy.get(code)
    if h and h["chapter_code"]:
        lines.append(f"     Hiérarchie : Chapitre {h['chapter_code']} — {h['chapter_label']}")
        if h["block_code"]:
            lines.append(f"                  > Bloc {h['block_code']} — {h['block_label']}")
        if h["category_code"]:
            lines.append(
                f"                  > Catégorie {h['category_code']} — {h['category_label']}"
            )

    n = notes.get(code)
    if n:
        if n["inclusion_notes"]:
            lines.append("     Inclus : " + " ; ".join(n["inclusion_notes"]))
        if n["exclusion_notes"]:
            lines.append("     Exclus : " + " ; ".join(n["exclusion_notes"]))

    return "\n".join(lines) + "\n" if lines else ""
