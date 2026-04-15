"""Build script: convert ANS CIM-10 OWL/Turtle dump into the two CSV referentials
consumed at runtime by utils_v2.py.

Usage:
    python scripts/build_cim10_enrichment.py \
        --source referentials/CIM_ATIH_2025/source/cim10-fr-2025.owl \
        --out-dir referentials/CIM_ATIH_2025/

The source file must be downloaded manually from the ANS SMT:
    https://smt.esante.gouv.fr/terminologie-cim-10/
(license CC BY-NC-ND 3.0 IGO; not redistributed in this repo).
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import pandas as pd
from rdflib import Graph, Namespace, RDF, RDFS, OWL
from rdflib.namespace import SKOS, DC

XKOS = Namespace("http://rdf-vocabulary.ddialliance.org/xkos#")


def parse_rdf_to_dataframes(source_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse an RDF file (ANS CIM-10 FR dump) and return (hierarchy_df, notes_df).

    Predicates expected (ANS convention):
      skos:notation       → code (dots stripped to match PMSI convention)
      rdfs:label (@fr)    → label
      rdfs:subClassOf     → parent concept
      dc:type             → one of {chapter, block, category}
      xkos:inclusionNote  → (multi) inclusion notes
      xkos:exclusionNote  → (multi) exclusion notes

    Only subjects typed as owl:Class with a skos:notation are considered concepts.
    """
    g = Graph()
    g.parse(source_path)

    concepts: dict = {}
    for subj in g.subjects(predicate=RDF.type, object=OWL.Class):
        notation = g.value(subj, SKOS.notation)
        if notation is None:
            continue
        # ANS notation contains dots (e.g. F02.00); PMSI runtime uses dotless codes.
        code = str(notation).replace(".", "").strip()
        if not code:
            continue

        # Prefer French label; fall back to any label.
        label_fr = next(
            (o for o in g.objects(subj, RDFS.label) if getattr(o, "language", None) == "fr"),
            None,
        )
        label = str(label_fr) if label_fr is not None else (str(g.value(subj, RDFS.label) or ""))

        level_value = g.value(subj, DC.type)
        level = str(level_value) if level_value is not None else ""

        parent = g.value(subj, RDFS.subClassOf)

        inclusion = [str(o).strip() for o in g.objects(subj, XKOS.inclusionNote) if str(o).strip()]
        exclusion = [str(o).strip() for o in g.objects(subj, XKOS.exclusionNote) if str(o).strip()]

        concepts[str(subj)] = {
            "code": code,
            "label": label,
            "level": level,
            "parent_uri": str(parent) if parent is not None else "",
            "inclusion_notes": inclusion,
            "exclusion_notes": exclusion,
        }

    # Pass 2: build hierarchy rows with chapter/block/category breadcrumbs.
    hierarchy_rows = []
    for uri, c in concepts.items():
        parent_code = concepts.get(c["parent_uri"], {}).get("code", "")
        chapter_code = chapter_label = ""
        block_code = block_label = ""
        category_code = category_label = ""

        # Walk up the parent chain. Since ANS uses 3 levels, the "category" slot
        # gets overwritten at each ancestor step — the topmost (3-char) category
        # wins, which is the intended prompt-breadcrumb value.
        cursor_uri = uri
        seen = set()
        while cursor_uri and cursor_uri not in seen:
            seen.add(cursor_uri)
            node = concepts.get(cursor_uri)
            if node is None:
                break
            if node["level"] == "chapter":
                chapter_code = node["code"]
                chapter_label = node["label"]
            elif node["level"] == "block":
                block_code = node["code"]
                block_label = node["label"]
            elif node["level"] == "category":
                category_code = node["code"]
                category_label = node["label"]
            cursor_uri = node["parent_uri"]

        hierarchy_rows.append({
            "code": c["code"],
            "level": c["level"],
            "parent_code": parent_code,
            "label": c["label"],
            "chapter_code": chapter_code,
            "chapter_label": chapter_label,
            "block_code": block_code,
            "block_label": block_label,
            "category_code": category_code,
            "category_label": category_label,
        })

    hierarchy_df = pd.DataFrame(hierarchy_rows).sort_values("code").reset_index(drop=True)

    note_rows = []
    for c in concepts.values():
        if c["inclusion_notes"] or c["exclusion_notes"]:
            note_rows.append({
                "code": c["code"],
                "inclusion_notes": "|".join(c["inclusion_notes"]),
                "exclusion_notes": "|".join(c["exclusion_notes"]),
            })
    notes_df = (
        pd.DataFrame(note_rows).sort_values("code").reset_index(drop=True)
        if note_rows
        else pd.DataFrame(columns=["code", "inclusion_notes", "exclusion_notes"])
    )

    return hierarchy_df, notes_df


def validate_hierarchy(df: pd.DataFrame, expected_count: int = 19075, tolerance: int = 500) -> list[str]:
    """Return a list of human-readable warnings; empty list = all good."""
    warnings: list[str] = []

    non_chapter = df[df["level"] != "chapter"]
    missing_parent = non_chapter[non_chapter["parent_code"] == ""]
    if len(missing_parent) > 0:
        warnings.append(f"{len(missing_parent)} non-chapter codes have empty parent_code")

    count = len(df)
    if abs(count - expected_count) > tolerance:
        warnings.append(f"Unexpected concept count: {count} (expected ~{expected_count} ± {tolerance})")

    # Level distribution sanity check — ANS uses {chapter, block, category}.
    level_counts = df["level"].value_counts().to_dict()
    if level_counts.get("chapter", 0) == 0:
        warnings.append(
            "No concepts with level='chapter' — dc:type predicate mapping likely wrong. "
            f"Observed levels: {sorted(level_counts.keys())}"
        )
    if level_counts.get("category", 0) < expected_count // 2:
        warnings.append(
            f"Suspiciously few categories: {level_counts.get('category', 0)} "
            f"(expected > {expected_count // 2})"
        )

    return warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Path to the ANS RDF dump (OWL/Turtle)")
    parser.add_argument("--out-dir", required=True, help="Directory where CSVs will be written")
    args = parser.parse_args()

    source_path = Path(args.source)
    if not source_path.exists():
        print(f"ERROR: source file not found: {source_path}", file=sys.stderr)
        return 2

    print(f"Parsing {source_path} ...")
    try:
        hierarchy_df, notes_df = parse_rdf_to_dataframes(str(source_path))
    except Exception as exc:  # pragma: no cover — surfaced to operator
        print(f"ERROR: RDF parsing failed: {exc}", file=sys.stderr)
        return 2

    warnings = validate_hierarchy(hierarchy_df)
    for w in warnings:
        print(f"  WARN: {w}", file=sys.stderr)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    hierarchy_path = out_dir / "cim10_hierarchy.csv"
    notes_path = out_dir / "cim10_notes.csv"

    hierarchy_df.to_csv(hierarchy_path, index=False, quoting=csv.QUOTE_ALL)
    notes_df.to_csv(notes_path, index=False, quoting=csv.QUOTE_ALL)

    print(f"Wrote {len(hierarchy_df)} hierarchy rows to {hierarchy_path}")
    print(f"Wrote {len(notes_df)} notes rows to {notes_path}")
    inclusion_count = (notes_df['inclusion_notes'] != '').sum() if len(notes_df) else 0
    exclusion_count = (notes_df['exclusion_notes'] != '').sum() if len(notes_df) else 0
    print(f"Codes with inclusion notes: {inclusion_count}")
    print(f"Codes with exclusion notes: {exclusion_count}")

    # Non-zero exit when validation found something worth the operator's attention.
    return 1 if warnings else 0


if __name__ == "__main__":
    sys.exit(main())
