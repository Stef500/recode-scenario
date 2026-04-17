"""Scenario — output of generation, composed of typed sub-models."""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from recode.models.profile import AdmissionType, DrgCode, Gender, IcdCode


class Patient(BaseModel):
    """Patient identity + demographics."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    age: int
    gender: Gender = Field(alias="sexe")
    first_name: str
    last_name: str
    date_of_birth: date


class Stay(BaseModel):
    """Hospitalization context."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    date_entry: date
    date_discharge: date
    admission_mode: str | None
    admission_type: AdmissionType
    discharge_disposition: str | None
    hospital: str
    department: str | None
    physician_first_name: str = Field(alias="first_name_med")
    physician_last_name: str = Field(alias="last_name_med")


class Diagnosis(BaseModel):
    """Primary + secondary ICD coding, with ATIH coding rule resolution."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    icd_primary_code: IcdCode
    icd_primary_description: str
    icd_parent_code: IcdCode
    case_management_type: IcdCode
    case_management_type_description: str
    case_management_type_text: str
    icd_secondary_codes: list[IcdCode] = Field(alias="icd_secondary_code")
    text_secondary_icd_official: str
    coding_rule: str
    case_management_description: str


class Procedure(BaseModel):
    """Primary CCAM procedure (empty when medical scenario)."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    code: str = Field(alias="procedure")
    description: str = Field(alias="text_procedure")


class CancerContext(BaseModel):
    """Present only for cancer primary diagnoses."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    histological_type: str | None
    score_tnm: str | None = Field(alias="score_TNM")
    stage: str | None = Field(alias="cancer_stage")
    biomarkers: str | None
    # Typo "recommandation" intentional: historical CSV column.
    treatment_recommendation: str | None = Field(alias="treatment_recommandation")
    chemotherapy_regimen: str | None


class Scenario(BaseModel):
    """Complete clinical scenario generated from a Profile."""

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    patient: Patient
    stay: Stay
    diagnosis: Diagnosis
    procedure: Procedure
    cancer: CancerContext | None = None
    drg_parent_code: DrgCode
    drg_parent_description: str
    los_mean: float
    los_sd: float
    template_name: str

    def to_csv_row(self) -> dict[str, Any]:
        """Flatten sub-models to the legacy CSV column layout.

        Uses ``model_dump(by_alias=True)`` on each sub-model and merges
        them into a single flat dict. Cancer fields are always present
        (None when no cancer context), for column stability across rows.
        """
        row: dict[str, Any] = {}
        row.update(self.patient.model_dump(by_alias=True))
        row.update(self.stay.model_dump(by_alias=True))
        row.update(self.diagnosis.model_dump(by_alias=True))
        row.update(self.procedure.model_dump(by_alias=True))

        cancer_keys = [
            "histological_type",
            "score_TNM",
            "cancer_stage",
            "biomarkers",
            "treatment_recommandation",
            "chemotherapy_regimen",
        ]
        if self.cancer is not None:
            row.update(self.cancer.model_dump(by_alias=True))
        else:
            for k in cancer_keys:
                row[k] = None

        row["drg_parent_code"] = self.drg_parent_code
        row["drg_parent_description"] = self.drg_parent_description
        row["los_mean"] = self.los_mean
        row["los_sd"] = self.los_sd
        row["template_name"] = self.template_name
        return row
