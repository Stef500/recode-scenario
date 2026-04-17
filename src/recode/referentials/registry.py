"""Central access point to all processed referentials (Parquet + YAML).

Loads lazily with caching (``functools.cached_property``). Each property is
validated against its Pandera schema on first access.

Intended to be injected into ``ScenarioGenerator`` for testability.
"""

from __future__ import annotations

from functools import cached_property
from pathlib import Path
from typing import Any

import pandas as pd
import yaml
from loguru import logger

from recode.referentials.constants import (
    CancerCodes,
    DrgCategories,
    IcdCategories,
    ProcedureCodes,
)
from recode.referentials.schemas import (
    CancerTreatmentSchema,
    ChronicSchema,
    Cim10HierarchySchema,
    Cim10NotesSchema,
    DrgGroupsSchema,
    DrgStatisticsSchema,
    HospitalsSchema,
    IcdOfficialSchema,
    IcdSynonymsSchema,
    NamesSchema,
    ProcedureOfficialSchema,
    ProceduresSchema,
    SecondaryIcdSchema,
    SpecialtySchema,
)


class ReferentialRegistry:
    """Typed, cached access to all processed referentials."""

    def __init__(self, processed_dir: Path, constants_dir: Path) -> None:
        """Initialize a registry with the given data locations.

        Args:
            processed_dir: Directory containing Parquet files produced by
                ``scripts/prepare_referentials.py``.
            constants_dir: Directory containing YAML constants files.
        """
        self._processed = Path(processed_dir)
        self._constants = Path(constants_dir)
        logger.debug("ReferentialRegistry({}, {})", self._processed, self._constants)

    def _load_parquet(self, name: str) -> pd.DataFrame:
        path = self._processed / f"{name}.parquet"
        if not path.exists():
            msg = f"Referential parquet not found: {path}"
            raise FileNotFoundError(msg)
        return pd.read_parquet(path)

    # ---- Tabular referentials (Parquet + Pandera) ----

    @cached_property
    def icd_official(self) -> pd.DataFrame:
        """Official ICD-10 codes with descriptions."""
        return IcdOfficialSchema.validate(self._load_parquet("icd_official"))

    @cached_property
    def drg_statistics(self) -> pd.DataFrame:
        """DRG length-of-stay statistics."""
        return DrgStatisticsSchema.validate(self._load_parquet("drg_statistics"))

    @cached_property
    def drg_groups(self) -> pd.DataFrame:
        """DRG code → description mapping."""
        return DrgGroupsSchema.validate(self._load_parquet("drg_groups"))

    @cached_property
    def cancer_treatments(self) -> pd.DataFrame:
        """Cancer treatment recommendations (synthetic ATIH table)."""
        return CancerTreatmentSchema.validate(self._load_parquet("cancer_treatments"))

    @cached_property
    def names(self) -> pd.DataFrame:
        """First/last names with gender for patient identity sampling."""
        return NamesSchema.validate(self._load_parquet("names"))

    @cached_property
    def hospitals(self) -> pd.DataFrame:
        """Hospital name list."""
        return HospitalsSchema.validate(self._load_parquet("hospitals"))

    @cached_property
    def specialty(self) -> pd.DataFrame:
        """DRG → specialty mapping."""
        return SpecialtySchema.validate(self._load_parquet("specialty"))

    @cached_property
    def chronic(self) -> pd.DataFrame:
        """Chronic-disease flags for ICD codes."""
        return ChronicSchema.validate(self._load_parquet("chronic"))

    @cached_property
    def complications(self) -> pd.DataFrame:
        """CMA (complications) list."""
        return self._load_parquet("complications")

    @cached_property
    def icd_synonyms(self) -> pd.DataFrame:
        """ICD code → synonym descriptions."""
        return IcdSynonymsSchema.validate(self._load_parquet("icd_synonyms"))

    @cached_property
    def procedure_official(self) -> pd.DataFrame:
        """Official CCAM procedure codes."""
        return ProcedureOfficialSchema.validate(self._load_parquet("procedure_official"))

    @cached_property
    def procedures(self) -> pd.DataFrame:
        """Procedure code distribution (from BN PMSI)."""
        return ProceduresSchema.validate(self._load_parquet("procedures"))

    @cached_property
    def secondary_icd(self) -> pd.DataFrame:
        """Secondary diagnosis distribution (from BN PMSI)."""
        return SecondaryIcdSchema.validate(self._load_parquet("secondary_icd"))

    @cached_property
    def pathology_procedures(self) -> pd.Series:
        """CCAM codes for anatomopathology examinations (excluded from sampling)."""
        df = self.procedure_official
        mask = df["procedure_description"].str.contains(
            "Examen anatomopathologique", na=False
        )
        return df.loc[mask, "procedure"]

    # ---- YAML constants (typed dataclasses) ----

    @cached_property
    def cancer_codes(self) -> CancerCodes:
        """Cancer-related ICD code categories."""
        return CancerCodes.from_yaml(self._constants / "cancer_codes.yaml")

    @cached_property
    def drg_categories(self) -> DrgCategories:
        """DRG root code groupings."""
        return DrgCategories.from_yaml(self._constants / "drg_categories.yaml")

    @cached_property
    def icd_categories(self) -> IcdCategories:
        """ICD code categories for ATIH rule resolution."""
        return IcdCategories.from_yaml(self._constants / "icd_categories.yaml")

    @cached_property
    def procedure_codes(self) -> ProcedureCodes:
        """CCAM procedure code categories."""
        return ProcedureCodes.from_yaml(self._constants / "procedure_codes.yaml")

    # ---- Coding rules (loaded from templates/regles_atih.yml) ----

    @cached_property
    def coding_rules_raw(self) -> dict[str, dict[str, Any]]:
        """ATIH coding rules loaded from ``templates/regles_atih.yml``."""
        path = Path("templates/regles_atih.yml")
        data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
        return {
            d["id"]: {
                "texte": d["clinical_coding_scenario"],
                "criteres": d["classification_profile_criteria"],
            }
            for d in data["regles"]
        }

    # ---- CIM-10 enrichment ----

    @cached_property
    def cim10_hierarchy(self) -> pd.DataFrame:
        """CIM-10 hierarchy (chapter > block > category > leaf)."""
        return Cim10HierarchySchema.validate(self._load_parquet("cim10_hierarchy"))

    @cached_property
    def cim10_notes(self) -> pd.DataFrame:
        """CIM-10 inclusion/exclusion notes per code."""
        return Cim10NotesSchema.validate(self._load_parquet("cim10_notes"))

    @cached_property
    def cim10_lookups(self) -> tuple[dict[str, Any], dict[str, Any]]:
        """Pre-built O(1) lookup dicts for format_cim10_enrichment."""
        # Deferred import: avoids a potential circular import as
        # ``cim10_enrichment`` grows to import other modules.
        from recode.scenarios.cim10_enrichment import build_lookups  # noqa: PLC0415

        return build_lookups(self.cim10_hierarchy, self.cim10_notes)

    def has_cim10_enrichment(self) -> bool:
        """True iff both enrichment Parquets exist (non-destructive check)."""
        return (self._processed / "cim10_hierarchy.parquet").exists() and (
            self._processed / "cim10_notes.parquet"
        ).exists()

    # ---- ICD description helper (used by prompts with enrichment) ----

    @cached_property
    def _icd_descriptions(self) -> dict[str, str]:
        """Internal: ICD code → description dict, built once from icd_official."""
        df = self.icd_official
        return dict(zip(df["icd_code"], df["icd_code_description"], strict=True))

    def icd_description_for(self, code: str) -> str:
        """Lookup ICD-10 description; return ``""`` if code is unknown."""
        return self._icd_descriptions.get(code, "")
