"""Cancer treatment recommendations (synthetic ATIH table)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from recode.models.profile import IcdCode


class TreatmentRecommendation(BaseModel):
    """One row of cancer_treatments.parquet."""

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="ignore")

    icd_parent_code: IcdCode = Field(alias="Code CIM")
    primary_site: str = Field(alias="Localisation")
    histological_type: str = Field(alias="Type Histologique")
    stage: str = Field(alias="Stade")
    biomarkers: str | None = Field(default=None, alias="Marqueurs Tumoraux")
    treatment_recommendation: str = Field(alias="Traitement")
    chemotherapy_regimen: str | None = Field(default=None, alias="Protocole de Chimiothérapie")
    tnm: str | None = None
