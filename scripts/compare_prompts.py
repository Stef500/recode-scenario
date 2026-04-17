"""Verify legacy (main) vs new (refacto-excl) prompts are iso modulo CIM-10.

For each scenario:
  1. Run legacy `make_prompts_marks_from_scenario(dict)` from main/utils_v2.py
  2. Run new `build_user_prompt(Scenario, registry=None)` → fallback branch
  3. Run new `build_user_prompt(Scenario, registry=reg)` → enriched branch

Expected:
  - (1) and (2) byte-identical         → proves no regression outside CIM-10
  - diff(2, 3) ⊂ CIM-10 enrichment    → proves enrichment is additive-only
"""

from __future__ import annotations

import difflib
import importlib.util
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

import pandas as pd

from recode.models import (
    CancerContext,
    Diagnosis,
    Patient,
    Procedure,
    Scenario,
    Stay,
)
from recode.referentials import ReferentialRegistry
from recode.scenarios.prompts import build_user_prompt

_TMP = Path(tempfile.gettempdir())
LEGACY_PATH = _TMP / "recode_legacy" / "utils_v2_legacy.py"
REGISTRY_DIR = _TMP / "compare_prompts"


def load_legacy():
    """Load main's utils_v2.py as an isolated module.

    Stubs mistralai/httpx imports that the legacy module does at import time
    (only used by batch-job helpers we never call here).
    """
    if not LEGACY_PATH.exists():
        LEGACY_PATH.parent.mkdir(parents=True, exist_ok=True)
        src = subprocess.check_output(
            ["git", "show", "main:utils_v2.py"],  # noqa: S607
        )
        LEGACY_PATH.write_bytes(src)

    import types

    for name in ("mistralai",):
        if name not in sys.modules:
            stub = types.ModuleType(name)
            stub.File = object
            stub.Mistral = object
            sys.modules[name] = stub

    spec = importlib.util.spec_from_file_location("utils_v2_legacy", LEGACY_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["utils_v2_legacy"] = mod
    spec.loader.exec_module(mod)
    return mod


def make_legacy_instance(legacy, *, icd_codes_cancer=()):
    """Build a generate_scenario instance without running __init__."""
    inst = legacy.generate_scenario.__new__(legacy.generate_scenario)
    inst.icd_codes_cancer = list(icd_codes_cancer)
    return inst


# ---------------------------------------------------------------------------
# Registry (same fixtures for all scenarios)
# ---------------------------------------------------------------------------
def build_registry(tmp: Path) -> ReferentialRegistry:
    proc = tmp / "proc"
    proc.mkdir(parents=True, exist_ok=True)
    const = tmp / "const"
    const.mkdir(parents=True, exist_ok=True)

    pd.DataFrame(
        {
            "code": ["A048", "A049", "K528", "C509"],
            "level": ["leaf"] * 4,
            "parent_code": ["A04", "A04", "K52", "C50"],
            "label": ["A048", "A049", "K528", "C509"],
            "chapter_code": ["I", "I", "XI", "II"],
            "chapter_label": [
                "Maladies infectieuses et parasitaires",
                "Maladies infectieuses et parasitaires",
                "Maladies de l'appareil digestif",
                "Tumeurs",
            ],
            "block_code": ["A00-A09", "A00-A09", "K50-K52", "C50-C50"],
            "block_label": [
                "Maladies intestinales infectieuses",
                "Maladies intestinales infectieuses",
                "Entérites et colites non infectieuses",
                "Tumeur maligne du sein",
            ],
            "category_code": ["A04", "A04", "K52", "C50"],
            "category_label": [
                "Autres infections intestinales bactériennes",
                "Autres infections intestinales bactériennes",
                "Autres gastro-entérites et colites non infectieuses",
                "Tumeur maligne du sein",
            ],
        }
    ).to_parquet(proc / "cim10_hierarchy.parquet", index=False)

    pd.DataFrame(
        {
            "code": ["A048", "C509"],
            "inclusion_notes": [
                "infections à Clostridium|infections à Yersinia",
                "",
            ],
            "exclusion_notes": [
                "intoxication alimentaire bactérienne (A05.-)",
                "tumeur de la peau du sein (C43.5, C44.5)",
            ],
        }
    ).to_parquet(proc / "cim10_notes.parquet", index=False)

    pd.DataFrame(
        {
            "icd_code": ["A048", "A049", "E119", "K528", "I500", "I10", "C509"],
            "icd_code_description": [
                "Autres infections intestinales bactériennes précisées",
                "Infection intestinale bactérienne, sans précision",
                "Diabète sucré de type 2, sans complication",
                "Autres colites et gastroentérites non infectieuses",
                "Insuffisance cardiaque, sans précision",
                "Hypertension essentielle",
                "Tumeur maligne du sein, sans précision",
            ],
            "aut_mco": [1] * 7,
        }
    ).to_parquet(proc / "icd_official.parquet", index=False)

    return ReferentialRegistry(processed_dir=proc, constants_dir=const)


# ---------------------------------------------------------------------------
# Scenarios: pairs of (legacy dict, new Scenario object)
# ---------------------------------------------------------------------------
def scenario_pair_a():
    """Non-cancer, infection digestive, DAS mixte (dont un .8)."""
    legacy = {
        "age": 65,
        "sexe": 1,
        "date_entry": date(2025, 3, 10),
        "date_discharge": date(2025, 3, 15),
        "date_of_birth": date(1960, 1, 15),
        "last_name": "Dupont",
        "first_name": "Jean",
        "admission_mode": "URGENCES",
        "discharge_disposition": "DOMICILE",
        "case_management_type": "A048",
        "case_management_type_text": "Diagnostic principal",
        "case_management_description": "",
        "icd_primary_description": "Autres infections intestinales bactériennes précisées",
        "icd_primary_code": "A048",
        "text_secondary_icd_official": (
            "- Diabète sucré de type 2, sans complication (E119)\n"
            "- Infection intestinale bactérienne, sans précision (A049)\n"
            "- Autres colites et gastroentérites non infectieuses (K528)\n"
        ),
        "first_name_med": "Marie",
        "last_name_med": "Martin",
        "specialty": "GASTRO",
        "hospital": "CHU Test",
    }
    new = Scenario(
        patient=Patient(
            age=65,
            gender=1,
            first_name="Jean",
            last_name="Dupont",
            date_of_birth=date(1960, 1, 15),
        ),
        stay=Stay(
            date_entry=date(2025, 3, 10),
            date_discharge=date(2025, 3, 15),
            admission_mode="URGENCES",
            admission_type="Inpatient",
            discharge_disposition="DOMICILE",
            hospital="CHU Test",
            department="GASTRO",
            physician_first_name="Marie",
            physician_last_name="Martin",
        ),
        diagnosis=Diagnosis(
            icd_primary_code="A048",
            icd_primary_description="Autres infections intestinales bactériennes précisées",
            icd_parent_code="A04",
            case_management_type="A048",
            case_management_type_description="",
            case_management_type_text="Diagnostic principal",
            icd_secondary_codes=["E119", "A049", "K528"],
            text_secondary_icd_official=(
                "- Diabète sucré de type 2, sans complication (E119)\n"
                "- Infection intestinale bactérienne, sans précision (A049)\n"
                "- Autres colites et gastroentérites non infectieuses (K528)\n"
            ),
            coding_rule="D1",
            case_management_description="",
        ),
        procedure=Procedure(code="", description=""),
        cancer=None,
        drg_parent_code="06M05",
        drg_parent_description="Infections digestives",
        los_mean=6.0,
        los_sd=2.0,
        template_name="medical_inpatient.txt",
    )
    return "A: infection digestive (non cancer)", legacy, new, ()


def scenario_pair_b():
    """Cancer du sein, DAS simple (I10, non enrichi)."""
    legacy = {
        "age": 58,
        "sexe": 2,
        "date_entry": date(2025, 6, 1),
        "date_discharge": date(2025, 6, 4),
        "date_of_birth": date(1967, 5, 20),
        "last_name": "Bernard",
        "first_name": "Claire",
        "icd_primary_description": "Sein",
        "histological_type": "Carcinome canalaire",
        "score_TNM": "T2N0M0",
        "cancer_stage": "II",
        "biomarkers": "HER2-",
        "icd_primary_code": "C509",
        "admission_mode": "PROGRAMMÉ",
        "discharge_disposition": "DOMICILE",
        "case_management_type": "C509",
        "case_management_type_text": "Diagnostic principal",
        "case_management_description": "",
        "text_secondary_icd_official": "- Hypertension essentielle (I10)\n",
        "first_name_med": "Paul",
        "last_name_med": "Durand",
        "specialty": "ONCOLOGIE",
        "hospital": "Institut Curie",
        "treatment_recommandation": "Chirurgie + RT",
        "chemotherapy_regimen": "AC-T",
    }
    new = Scenario(
        patient=Patient(
            age=58,
            gender=2,
            first_name="Claire",
            last_name="Bernard",
            date_of_birth=date(1967, 5, 20),
        ),
        stay=Stay(
            date_entry=date(2025, 6, 1),
            date_discharge=date(2025, 6, 4),
            admission_mode="PROGRAMMÉ",
            admission_type="Inpatient",
            discharge_disposition="DOMICILE",
            hospital="Institut Curie",
            department="ONCOLOGIE",
            physician_first_name="Paul",
            physician_last_name="Durand",
        ),
        diagnosis=Diagnosis(
            icd_primary_code="C509",
            icd_primary_description="Sein",
            icd_parent_code="C50",
            case_management_type="C509",
            case_management_type_description="",
            case_management_type_text="Diagnostic principal",
            icd_secondary_codes=["I10"],
            text_secondary_icd_official="- Hypertension essentielle (I10)\n",
            coding_rule="D1",
            case_management_description="",
        ),
        procedure=Procedure(code="", description=""),
        cancer=CancerContext(
            histological_type="Carcinome canalaire",
            score_tnm="T2N0M0",
            stage="II",
            biomarkers="HER2-",
            treatment_recommendation="Chirurgie + RT",
            chemotherapy_regimen="AC-T",
        ),
        drg_parent_code="09M05",
        drg_parent_description="Tumeurs du sein",
        los_mean=3.0,
        los_sd=1.0,
        template_name="medical_inpatient.txt",
    )
    return "B: cancer du sein", legacy, new, ("C509",)


def scenario_pair_c():
    """Insuffisance cardiaque, DAS simple (I10), DP non-.8 (I500)."""
    legacy = {
        "age": 78,
        "sexe": 1,
        "date_entry": date(2025, 1, 5),
        "date_discharge": date(2025, 1, 12),
        "date_of_birth": date(1946, 11, 2),
        "last_name": "Petit",
        "first_name": "André",
        "admission_mode": "URGENCES",
        "discharge_disposition": "DOMICILE",
        "case_management_type": "I500",
        "case_management_type_text": "Diagnostic principal",
        "case_management_description": "",
        "icd_primary_description": "Insuffisance cardiaque, sans précision",
        "icd_primary_code": "I500",
        "text_secondary_icd_official": "- Hypertension essentielle (I10)\n",
        "first_name_med": "Sophie",
        "last_name_med": "Lefèvre",
        "specialty": "CARDIO",
        "hospital": "CHU Pitié",
    }
    new = Scenario(
        patient=Patient(
            age=78,
            gender=1,
            first_name="André",
            last_name="Petit",
            date_of_birth=date(1946, 11, 2),
        ),
        stay=Stay(
            date_entry=date(2025, 1, 5),
            date_discharge=date(2025, 1, 12),
            admission_mode="URGENCES",
            admission_type="Inpatient",
            discharge_disposition="DOMICILE",
            hospital="CHU Pitié",
            department="CARDIO",
            physician_first_name="Sophie",
            physician_last_name="Lefèvre",
        ),
        diagnosis=Diagnosis(
            icd_primary_code="I500",
            icd_primary_description="Insuffisance cardiaque, sans précision",
            icd_parent_code="I50",
            case_management_type="I500",
            case_management_type_description="",
            case_management_type_text="Diagnostic principal",
            icd_secondary_codes=["I10"],
            text_secondary_icd_official="- Hypertension essentielle (I10)\n",
            coding_rule="D1",
            case_management_description="",
        ),
        procedure=Procedure(code="", description=""),
        cancer=None,
        drg_parent_code="05M09",
        drg_parent_description="Insuffisance cardiaque",
        los_mean=7.0,
        los_sd=2.5,
        template_name="medical_inpatient.txt",
    )
    return "C: insuffisance cardiaque (non cancer, DP non-.8)", legacy, new, ()


# ---------------------------------------------------------------------------
# Compare
# ---------------------------------------------------------------------------
def run():
    legacy_mod = load_legacy()
    REGISTRY_DIR.mkdir(exist_ok=True)
    reg = build_registry(REGISTRY_DIR)

    all_ok = True
    for name, legacy_dict, new_sc, cancer_codes in (
        scenario_pair_a(),
        scenario_pair_b(),
        scenario_pair_c(),
    ):
        print("\n" + "=" * 80)
        print(name)
        print("=" * 80)

        legacy_inst = make_legacy_instance(legacy_mod, icd_codes_cancer=cancer_codes)
        prompt_legacy = legacy_inst.make_prompts_marks_from_scenario(legacy_dict)
        prompt_new_fallback = build_user_prompt(new_sc)
        prompt_new_enriched = build_user_prompt(new_sc, registry=reg)

        # --- Check 1: legacy (main) == new fallback (registry=None) ---
        if prompt_legacy == prompt_new_fallback:
            print("[OK] legacy (main) == new (registry=None)  → iso byte-à-byte")
        else:
            all_ok = False
            print("[FAIL] legacy (main) != new (registry=None)")
            print("--- diff legacy → new-fallback ---")
            sys.stdout.writelines(
                difflib.unified_diff(
                    prompt_legacy.splitlines(keepends=True),
                    prompt_new_fallback.splitlines(keepends=True),
                    fromfile="legacy (main)",
                    tofile="new (registry=None)",
                    n=2,
                )
            )

        # --- Check 2: diff fallback → enriched ne doit contenir QUE du CIM-10 ---
        diff = list(
            difflib.unified_diff(
                prompt_new_fallback.splitlines(keepends=True),
                prompt_new_enriched.splitlines(keepends=True),
                fromfile="new (registry=None)",
                tofile="new (registry=reg)",
                n=1,
            )
        )
        if not diff:
            print("[INFO] registry=None == registry=reg (pas d'enrichissement attendu)")
        else:
            added = [ln for ln in diff if ln.startswith("+") and not ln.startswith("+++")]
            removed = [ln for ln in diff if ln.startswith("-") and not ln.startswith("---")]
            cim10_markers = ("Hiérarchie", "Inclus", "Exclus", "> Bloc", "> Catégorie")
            # Suppressions tolérées : ligne DAS remplacée par sa variante registry (desc officielle)
            # et la ligne vide issue du "\n" final du text_secondary_icd_official.
            suspicious_removed = [
                ln
                for ln in removed
                if ln.strip() not in ("-",)  # blank line
                and "(" not in ln  # DAS line with code in parens
                and not any(m in ln for m in cim10_markers)
            ]
            suspicious_added = [
                ln
                for ln in added
                if not any(m in ln for m in cim10_markers) and "(" not in ln  # DAS re-rendered line
            ]
            print(f"  ajouts     : {len(added)} lignes")
            print(f"  suppressions: {len(removed)} lignes")
            if suspicious_added or suspicious_removed:
                all_ok = False
                print("[FAIL] diff contient des lignes non CIM-10 :")
                for ln in suspicious_added + suspicious_removed:
                    print("   ", ln.rstrip())
            else:
                print("[OK] diff fallback → enriched ne contient que du CIM-10 + re-rendu DAS")
            print("  --- diff (registry=None → registry=reg) ---")
            for ln in diff:
                sys.stdout.write("  " + ln)

    print("\n" + "=" * 80)
    print("RÉSULTAT GLOBAL :", "OK" if all_ok else "ÉCHEC")
    print("=" * 80)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(run())
