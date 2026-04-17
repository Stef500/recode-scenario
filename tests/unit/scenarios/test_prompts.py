"""Tests for prompts module."""

from __future__ import annotations

from datetime import date
from pathlib import Path


def _make_scenario(is_cancer: bool = False):  # type: ignore[no-untyped-def]
    from recode.models import (
        CancerContext,
        Diagnosis,
        Patient,
        Procedure,
        Scenario,
        Stay,
    )

    cancer = (
        CancerContext(
            histological_type="Carcinome canalaire",
            score_tnm="T2N0M0",
            stage="II",
            biomarkers="HER2-",
            treatment_recommendation="Chirurgie + RT",
            chemotherapy_regimen="AC-T",
        )
        if is_cancer
        else None
    )
    return Scenario(
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
            department="CARDIOLOGIE",
            physician_first_name="Marie",
            physician_last_name="Martin",
        ),
        diagnosis=Diagnosis(
            icd_primary_code="C509" if is_cancer else "I500",
            icd_primary_description="Sein" if is_cancer else "ICC",
            icd_parent_code="C50" if is_cancer else "I50",
            case_management_type="C509" if is_cancer else "I500",
            case_management_type_description="desc",
            case_management_type_text="texte hospit",
            icd_secondary_codes=["I10"],
            text_secondary_icd_official="- HTA (I10)\n",
            coding_rule="D1",
            case_management_description="",
        ),
        procedure=Procedure(code="", description=""),
        cancer=cancer,
        drg_parent_code="05M09",
        drg_parent_description="ICC",
        los_mean=7.5,
        los_sd=2.5,
        template_name="medical_inpatient.txt",
    )


def test_build_user_prompt_contains_patient_info() -> None:
    from recode.scenarios.prompts import build_user_prompt

    s = _make_scenario()
    prompt = build_user_prompt(s)
    assert "Jean" in prompt
    assert "Dupont" in prompt
    assert "10/03/2025" in prompt
    assert "65" in prompt


def test_build_user_prompt_cancer_includes_tnm() -> None:
    from recode.scenarios.prompts import build_user_prompt

    s = _make_scenario(is_cancer=True)
    prompt = build_user_prompt(s)
    assert "T2N0M0" in prompt
    assert "Carcinome canalaire" in prompt
    assert "HER2-" in prompt


def test_build_system_prompt_reads_template(tmp_path: Path) -> None:
    from recode.scenarios.prompts import build_system_prompt

    tmpl_dir = tmp_path / "templates"
    tmpl_dir.mkdir()
    (tmpl_dir / "medical_inpatient.txt").write_text("Vous êtes un médecin.")
    s = _make_scenario()
    prompt = build_system_prompt(s, templates_dir=tmpl_dir)
    assert prompt == "Vous êtes un médecin."


def test_build_prefix_non_cancer() -> None:
    from recode.scenarios.prompts import build_prefix

    s = _make_scenario()
    prefix = build_prefix(s)
    assert "les diagnostics" in prefix
    assert "biomarqueurs" not in prefix


def test_build_prefix_cancer_mentions_biomarkers() -> None:
    from recode.scenarios.prompts import build_prefix

    s = _make_scenario(is_cancer=True)
    prefix = build_prefix(s)
    assert "biomarqueurs" in prefix


def test_build_user_prompt_without_registry_byte_identical_to_default() -> None:
    """build_user_prompt(scenario) unchanged when registry is not provided."""
    from recode.scenarios.prompts import build_user_prompt

    sc = _make_scenario()
    prompt_default = build_user_prompt(sc)
    prompt_none = build_user_prompt(sc, registry=None)
    assert prompt_default == prompt_none
    assert "- Codage CIM10 :\n" in prompt_default
    assert "   * Diagnostic associés : \n" in prompt_default


def _make_registry_with_cim10(tmp_path):  # type: ignore[no-untyped-def]
    """Build a registry with minimal parquets to exercise the enriched branch."""
    import pandas as pd

    from recode.referentials import ReferentialRegistry

    proc = tmp_path / "proc"
    proc.mkdir()
    const = tmp_path / "const"
    const.mkdir()

    pd.DataFrame(
        {
            "code": ["A048", "A049"],
            "level": ["leaf", "leaf"],
            "parent_code": ["A04", "A04"],
            "label": ["l1", "l2"],
            "chapter_code": ["I", "I"],
            "chapter_label": ["Mal. inf.", "Mal. inf."],
            "block_code": ["A00-A09", "A00-A09"],
            "block_label": ["Intest.", "Intest."],
            "category_code": ["A04", "A04"],
            "category_label": ["Autres inf.", "Autres inf."],
        }
    ).to_parquet(proc / "cim10_hierarchy.parquet", index=False)

    pd.DataFrame(
        {
            "code": ["A048"],
            "inclusion_notes": ["inc1|inc2"],
            "exclusion_notes": ["exc1"],
        }
    ).to_parquet(proc / "cim10_notes.parquet", index=False)

    pd.DataFrame(
        {
            "icd_code": ["A048", "A049", "E119", "I10"],
            "icd_code_description": [
                "Autres infections bactériennes précisées",
                "Infection bactérienne, sans précision",
                "Diabète de type 2, sans complication",
                "Hypertension essentielle",
            ],
            "aut_mco": [1, 1, 1, 1],
        }
    ).to_parquet(proc / "icd_official.parquet", index=False)

    return ReferentialRegistry(processed_dir=proc, constants_dir=const)


def _make_scenario_for_enrichment(*, dp_code: str, das_codes: list[str]):  # type: ignore[no-untyped-def]
    """Scenario whose DP and DAS can be customised to exercise enrichment rules."""
    sc = _make_scenario()
    return sc.model_copy(
        update={
            "diagnosis": sc.diagnosis.model_copy(
                update={
                    "icd_primary_code": dp_code,
                    "icd_primary_description": "Default DP description",
                    "icd_secondary_codes": das_codes,
                    "text_secondary_icd_official": "".join(f"- desc ({c})\n" for c in das_codes),
                }
            ),
        }
    )


def test_build_user_prompt_enriched_dp_with_registry(tmp_path) -> None:
    from recode.scenarios.prompts import build_user_prompt

    reg = _make_registry_with_cim10(tmp_path)
    sc = _make_scenario_for_enrichment(dp_code="A048", das_codes=["E119"])

    prompt = build_user_prompt(sc, registry=reg)

    assert "     Hiérarchie : Chapitre I — Mal. inf." in prompt
    assert "                  > Bloc A00-A09 — Intest." in prompt
    assert "     Inclus : inc1 ; inc2" in prompt
    assert "     Exclus : exc1" in prompt


def test_build_user_prompt_enriched_das_dot_eight(tmp_path) -> None:
    from recode.scenarios.prompts import build_user_prompt

    reg = _make_registry_with_cim10(tmp_path)
    # DP I10 is not in lookups → no DP enrichment; DAS A048 ends with 8 → enriched.
    sc = _make_scenario_for_enrichment(dp_code="I10", das_codes=["A048", "E119"])

    prompt = build_user_prompt(sc, registry=reg)

    # DP I10 yields no enrichment block
    assert "- Codage CIM10 :\n   * Diagnostic principal :" in prompt
    # A048 is 4-char ending with 8 -> enriched after its line
    assert "     Inclus : inc1 ; inc2" in prompt


def test_build_user_prompt_enriched_silent_when_code_unknown(tmp_path) -> None:
    from recode.scenarios.prompts import build_user_prompt

    reg = _make_registry_with_cim10(tmp_path)
    sc = _make_scenario_for_enrichment(dp_code="ZZZZZ", das_codes=[])

    prompt = build_user_prompt(sc, registry=reg)

    # No parasite lines when DP is unknown
    assert "Hiérarchie" not in prompt
    assert "Inclus" not in prompt
    assert "Exclus" not in prompt
    assert "- Codage CIM10 :" in prompt
    assert "   * Diagnostic associés :" in prompt
