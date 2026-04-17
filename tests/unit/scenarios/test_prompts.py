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
