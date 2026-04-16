"""Tests for Scenario model + sub-models."""

from __future__ import annotations

from datetime import date


def _make_scenario():  # type: ignore[no-untyped-def]
    from recode.models import (
        Diagnosis,
        Patient,
        Procedure,
        Scenario,
        Stay,
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
            icd_primary_code="I500",
            icd_primary_description="ICC",
            icd_parent_code="I50",
            case_management_type="I500",
            case_management_type_description="ICC",
            case_management_type_text="",
            icd_secondary_codes=["I10"],
            text_secondary_icd_official="- HTA (I10)\n",
            coding_rule="D1",
            case_management_description="Hospit diagnostic",
        ),
        procedure=Procedure(code="", description=""),
        cancer=None,
        drg_parent_code="05M09",
        drg_parent_description="Insuf cardiaque",
        los_mean=7.5,
        los_sd=2.5,
        template_name="medical_inpatient.txt",
    )


def test_scenario_constructs() -> None:
    s = _make_scenario()
    assert s.patient.age == 65
    assert s.cancer is None


def test_scenario_to_csv_row_flattens() -> None:
    s = _make_scenario()
    row = s.to_csv_row()
    assert row["sexe"] == 1
    assert row["age"] == 65
    assert row["first_name"] == "Jean"
    assert row["icd_primary_code"] == "I500"
    assert row["drg_parent_code"] == "05M09"
    assert row["template_name"] == "medical_inpatient.txt"
    assert row["first_name_med"] == "Marie"
    assert row["cancer_stage"] is None
    assert row["score_TNM"] is None


def test_scenario_to_csv_row_includes_cancer_fields_when_present() -> None:
    from recode.models import CancerContext

    s = _make_scenario().model_copy(
        update={
            "cancer": CancerContext(
                histological_type="Adénocarcinome",
                score_tnm="T2N1M0",
                stage="II",
                biomarkers="HER2+",
                treatment_recommendation="Chirurgie",
                chemotherapy_regimen=None,
            )
        }
    )
    row = s.to_csv_row()
    assert row["histological_type"] == "Adénocarcinome"
    assert row["score_TNM"] == "T2N1M0"
    assert row["cancer_stage"] == "II"
    assert row["treatment_recommandation"] == "Chirurgie"
