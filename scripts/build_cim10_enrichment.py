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
from rdflib import Graph, Namespace, RDF
from rdflib.namespace import SKOS

ANS = Namespace("https://smt.esante.gouv.fr/terminologie/ans#")


def parse_rdf_to_dataframes(source_path: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Parse an RDF file and return (hierarchy_df, notes_df).

    Predicates expected:
      skos:notation         → code
      skos:prefLabel (@fr)  → label
      skos:broader          → parent concept
      ans:level             → one of {chapter, block, category, leaf}
      ans:inclusionNote     → (multi) inclusion notes
      ans:exclusionNote     → (multi) exclusion notes

    If the real ANS dump uses different predicates, adjust this function.
    """
    g = Graph()
    g.parse(source_path)

    # Pass 1: collect per-concept data keyed by URI.
    # Restrict to explicit SKOS Concepts to avoid picking up OWL axioms, blank
    # nodes, or other non-concept subjects that happen to have a skos:notation.
    concepts: dict = {}
    for subj in g.subjects(predicate=RDF.type, object=SKOS.Concept):
        code = g.value(subj, SKOS.notation)
        if code is None:
            continue
        code = str(code)
        label = g.value(subj, SKOS.prefLabel)
        level = g.value(subj, ANS.level)
        parent = g.value(subj, SKOS.broader)
        inclusion = [str(o) for o in g.objects(subj, ANS.inclusionNote)]
        exclusion = [str(o) for o in g.objects(subj, ANS.exclusionNote)]
        concepts[str(subj)] = {
            "code": code,
            "label": str(label) if label is not None else "",
            "level": str(level) if level is not None else "",
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

        # Walk up the parent chain to find chapter/block/category.
        cursor_uri = uri
        seen = set()
        while cursor_uri and cursor_uri not in seen:
            seen.add(cursor_uri)
            node = concepts.get(cursor_uri)
            if node is None:
                break
            if node["level"] == "chapter":
                chapter_code = node["code"]; chapter_label = node["label"]
            elif node["level"] == "block":
                block_code = node["code"]; block_label = node["label"]
            elif node["level"] == "category":
                category_code = node["code"]; category_label = node["label"]
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

    # Notes rows: only concepts with at least one note.
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

    # Level distribution sanity check — catches predicate-mapping drift where
    # ans:level is missed entirely and all concepts get level="".
    level_counts = df["level"].value_counts().to_dict()
    if level_counts.get("chapter", 0) == 0:
        warnings.append(
            "No concepts with level='chapter' — ans:level predicate mapping likely wrong. "
            f"Observed levels: {sorted(level_counts.keys())}"
        )
    if level_counts.get("leaf", 0) < expected_count // 2:
        warnings.append(
            f"Suspiciously few leaves: {level_counts.get('leaf', 0)} "
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
