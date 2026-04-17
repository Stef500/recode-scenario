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


_INDENT = " " * 5  # Top-level line prefix (Hiérarchie / Inclus / Exclus).
_SUBLINE = " " * 18 + "> "  # Nested hierarchy line prefix (Bloc / Catégorie).


def _split_notes(raw: str) -> list[str]:
    r"""Split a multi-item note field.

    Real ATIH CSVs use ``\n``; legacy specs and fixtures used ``|``. Accept
    either, and drop empty items.
    """
    if not raw:
        return []
    # Split on both separators
    parts: list[str] = []
    for chunk in raw.split("\n"):
        parts.extend(chunk.split("|"))
    return [p.strip() for p in parts if p.strip()]


def build_lookups(
    hierarchy_df: pd.DataFrame,
    notes_df: pd.DataFrame,
) -> tuple[dict[str, _HierarchyRow], dict[str, _NotesRow]]:
    r"""DataFrame → O(1) lookup dicts.

    Filters the hierarchy to leaf-level codes; only leaf codes are looked
    up at prompt format time. Accepts both the real ANS ATIH convention
    (``category``) and the legacy mini-fixture convention (``leaf``). Notes
    stored as ``"\n"``- or ``"|"``-joined strings are split back into lists.
    """
    # Real ANS ATIH CIM-10 uses `category` for leaf codes (3-level hierarchy).
    # `leaf` is kept for backward-compat with mini-fixtures / future data.
    leaf_levels = ("category", "leaf")
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
        if row["level"] in leaf_levels
    }
    # Real ATIH CSVs use "\n" as intra-field separator for multi-item notes.
    # `|` is kept for backward-compat with docs/specs that describe the old format.
    notes: dict[str, _NotesRow] = {
        row["code"]: {
            "inclusion_notes": _split_notes(row["inclusion_notes"]),
            "exclusion_notes": _split_notes(row["exclusion_notes"]),
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

    Indentation is controlled by ``_INDENT`` (5 spaces, top-level lines) and
    ``_SUBLINE`` (18 spaces + ``"> "``, nested Bloc / Catégorie lines). The
    canonical format is locked by the golden-string tests in
    ``tests/unit/scenarios/test_cim10_enrichment.py``.

    Lines emitted in order (each terminated by ``\n``):

    - ``Hiérarchie : Chapitre X — label``  (when ``chapter_code`` known)
    - ``> Bloc B — label``                  (when ``block_code`` known)
    - ``> Catégorie C — label``             (when ``category_code`` known)
    - ``Inclus : a ; b ; c``                (when at least one inclusion note)
    - ``Exclus : a ; b``                    (when at least one exclusion note)

    Returns ``""`` when nothing is known for ``code`` — caller can
    unconditionally append the result.
    """
    lines: list[str] = []

    h = hierarchy.get(code)
    if h and h["chapter_code"]:
        lines.append(f"{_INDENT}Hiérarchie : Chapitre {h['chapter_code']} — {h['chapter_label']}")
        if h["block_code"]:
            lines.append(f"{_SUBLINE}Bloc {h['block_code']} — {h['block_label']}")
        if h["category_code"]:
            lines.append(f"{_SUBLINE}Catégorie {h['category_code']} — {h['category_label']}")

    n = notes.get(code)
    if n:
        if n["inclusion_notes"]:
            lines.append(f"{_INDENT}Inclus : " + " ; ".join(n["inclusion_notes"]))
        if n["exclusion_notes"]:
            lines.append(f"{_INDENT}Exclus : " + " ; ".join(n["exclusion_notes"]))

    return "\n".join(lines) + "\n" if lines else ""


def is_enrichable_das(code: str) -> bool:
    """Return True iff ``code`` matches the CIM-10 'other specified' rule.

    A DAS code is enriched iff it has 4 characters ending in ``8`` (e.g.
    ``A048``, ``E118``). The ``.8`` codes are ATIH's 'Autres' residual
    category — exactly the codes most prone to narrative ambiguity, hence
    the target of enrichment.
    """
    return len(code) == 4 and code.endswith("8")
