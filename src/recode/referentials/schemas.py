"""Pandera schemas for processed referentials.

Each schema corresponds to a parquet file in ``referentials/processed/``.
"""

from __future__ import annotations

import pandera.pandas as pa
from pandera.typing import Series


class IcdOfficialSchema(pa.DataFrameModel):
    """Official ICD-10 codes (ATIH nomenclature)."""

    icd_code: Series[str] = pa.Field(str_matches=r"^[A-Z]\d{2,4}\+?\d*$")
    icd_code_description: Series[str]
    aut_mco: Series[int] = pa.Field(in_range={"min_value": 0, "max_value": 5})

    class Config:
        """Pandera validation config."""

        strict = "filter"
        coerce = True


class DrgStatisticsSchema(pa.DataFrameModel):
    """DRG length-of-stay statistics (mean + std)."""

    drg_parent_code: Series[str] = pa.Field(str_matches=r"^\d{2}[A-Z]\d{2}$")
    los_mean: Series[float] = pa.Field(ge=0, nullable=True)
    los_sd: Series[float] = pa.Field(ge=0, nullable=True)

    class Config:
        """Pandera validation config."""

        strict = "filter"
        coerce = True


class DrgGroupsSchema(pa.DataFrameModel):
    """DRG codes → human-readable descriptions."""

    drg_parent_code: Series[str] = pa.Field(str_matches=r"^\d{2}[A-Z]\d{2}$")
    drg_parent_description: Series[str]

    class Config:
        """Pandera validation config."""

        strict = "filter"
        coerce = True


class CancerTreatmentSchema(pa.DataFrameModel):
    """Cancer treatment recommendations (synthetic ATIH table)."""

    icd_parent_code: Series[str]
    primary_site: Series[str]
    histological_type: Series[str]
    stage: Series[str]
    biomarkers: Series[str] = pa.Field(nullable=True)
    treatment_recommendation: Series[str]
    chemotherapy_regimen: Series[str] = pa.Field(nullable=True)

    class Config:
        """Pandera validation config."""

        strict = "filter"
        coerce = True


class NamesSchema(pa.DataFrameModel):
    """First name / last name with gender for patient identity sampling."""

    prenom: Series[str]
    nom: Series[str]
    sexe: Series[int] = pa.Field(isin=[1, 2])

    class Config:
        """Pandera validation config."""

        strict = "filter"
        coerce = True


class HospitalsSchema(pa.DataFrameModel):
    """Hospital names (for random sampling)."""

    hospital: Series[str]

    class Config:
        """Pandera validation config."""

        strict = "filter"
        coerce = True


class SpecialtySchema(pa.DataFrameModel):
    """DRG → medical specialty mapping (with age + ratio)."""

    drg_parent_code: Series[str]
    specialty: Series[str]
    ratio: Series[float] = pa.Field(ge=0, le=1, nullable=True)
    age: Series[str] = pa.Field(nullable=True)

    class Config:
        """Pandera validation config."""

        strict = "filter"
        coerce = True


class SecondaryIcdSchema(pa.DataFrameModel):
    """Secondary diagnosis distribution (from BN PMSI)."""

    icd_secondary_code: Series[str]
    drg_parent_code: Series[str] = pa.Field(nullable=True)
    icd_primary_code: Series[str] = pa.Field(nullable=True)
    cage2: Series[str]
    sexe: Series[int] = pa.Field(isin=[1, 2])
    nb: Series[int] = pa.Field(ge=0)
    type: Series[str] = pa.Field(isin=["Chronic", "Acute", "Cancer", "Metastasis", "Metastasis LN"])

    class Config:
        """Pandera validation config."""

        strict = "filter"
        coerce = True


class ProceduresSchema(pa.DataFrameModel):
    """Procedure code distribution."""

    procedure: Series[str]
    drg_parent_code: Series[str]
    icd_primary_code: Series[str]
    cage2: Series[str]
    sexe: Series[int] = pa.Field(isin=[1, 2])
    nb: Series[int] = pa.Field(ge=0)

    class Config:
        """Pandera validation config."""

        strict = "filter"
        coerce = True


class ProcedureOfficialSchema(pa.DataFrameModel):
    """Official CCAM procedure codes with descriptions."""

    procedure: Series[str]
    procedure_description: Series[str]

    class Config:
        """Pandera validation config."""

        strict = "filter"
        coerce = True


class ClassificationProfileSchema(pa.DataFrameModel):
    """Profile entries sampled from BN PMSI for scenario generation."""

    drg_parent_code: Series[str]
    icd_primary_code: Series[str]
    case_management_type: Series[str]
    cage: Series[str]
    cage2: Series[str]
    sexe: Series[int] = pa.Field(isin=[1, 2])
    nb: Series[int] = pa.Field(ge=0)
    admission_type: Series[str] = pa.Field(isin=["Inpatient", "Outpatient"])

    class Config:
        """Pandera validation config."""

        strict = "filter"
        coerce = True


class ChronicSchema(pa.DataFrameModel):
    """Chronic-disease flag for ICD codes.

    ``chronic`` is a severity/type code (observed values: 0-6 in ATIH data).
    """

    code: Series[str]
    chronic: Series[int] = pa.Field(ge=0, le=9)
    libelle: Series[str] = pa.Field(nullable=True)

    class Config:
        """Pandera validation config."""

        strict = "filter"
        coerce = True


class ComplicationsSchema(pa.DataFrameModel):
    """CMA (complications) list."""

    icd_code: Series[str]

    class Config:
        """Pandera validation config."""

        strict = "filter"
        coerce = True


class IcdSynonymsSchema(pa.DataFrameModel):
    """ICD code → synonym descriptions."""

    icd_code: Series[str]
    icd_code_description: Series[str]

    class Config:
        """Pandera validation config."""

        strict = "filter"
        coerce = True


class Cim10HierarchySchema(pa.DataFrameModel):
    """Hiérarchie CIM-10 (chapter > block > category > leaf)."""

    code: Series[str] = pa.Field(nullable=False, unique=True)
    level: Series[str] = pa.Field(isin=["chapter", "block", "category", "leaf"])
    parent_code: Series[str] = pa.Field(nullable=False)
    label: Series[str] = pa.Field(nullable=False)
    chapter_code: Series[str] = pa.Field(nullable=False)
    chapter_label: Series[str] = pa.Field(nullable=False)
    block_code: Series[str] = pa.Field(nullable=False)
    block_label: Series[str] = pa.Field(nullable=False)
    category_code: Series[str] = pa.Field(nullable=False)
    category_label: Series[str] = pa.Field(nullable=False)

    class Config:
        """Pandera validation config."""

        strict = True


class Cim10NotesSchema(pa.DataFrameModel):
    """Notes Inclus/Exclus CIM-10 par code (items joints par '|')."""

    code: Series[str] = pa.Field(nullable=False, unique=True)
    inclusion_notes: Series[str] = pa.Field(nullable=False)
    exclusion_notes: Series[str] = pa.Field(nullable=False)

    class Config:
        """Pandera validation config."""

        strict = True
