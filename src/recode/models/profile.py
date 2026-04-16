"""Profile — input to scenario generation.

Corresponds to one row of df_classification_profile (from BN PMSI).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Gender = Literal[1, 2]
AdmissionType = Literal["Inpatient", "Outpatient"]
AgeClass = str
IcdCode = str
DrgCode = str


class Profile(BaseModel):
    """Demographic + clinical profile from national PMSI data.

    Field names are English snake_case; ``serialization_alias`` keeps the
    legacy French CSV column names for golden-file compatibility.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True, extra="ignore")

    drg_parent_code: DrgCode
    drg_parent_description: str | None = None
    icd_primary_code: IcdCode
    icd_primary_parent_code: IcdCode | None = None
    case_management_type: IcdCode
    age_class: AgeClass = Field(alias="cage")
    age_class_2: AgeClass = Field(alias="cage2")
    gender: Gender = Field(alias="sexe")
    length_of_stay: int | None = Field(default=None, alias="los")
    los_mean: float | None = None
    los_sd: float | None = None
    weight: int = Field(default=1, alias="nb")
    admission_mode: str | None = None
    admission_type: AdmissionType
    discharge_disposition: str | None = None
    icd_secondary_codes: list[IcdCode] = Field(default_factory=list, alias="icd_secondary_code")
    specialty: str | None = None
    age_exact: int | None = Field(default=None, alias="age2")
