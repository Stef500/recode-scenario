"""ATIH coding rules (loaded from templates/regles_atih.yml)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class CodingRuleCriteria(BaseModel):
    """Predicate criteria for a coding rule."""

    model_config = ConfigDict(frozen=True, extra="allow")

    primary_diagnosis: str | None = None


class CodingRule(BaseModel):
    """One coding rule row from the ATIH coding rules YAML."""

    model_config = ConfigDict(frozen=True, extra="ignore")

    id: str
    instruction_id: str
    clinical_coding_scenario: str
    icd10_coding_instruction_atih: str = ""
    icd10_coding_instruction: str = ""
    criteria: CodingRuleCriteria = CodingRuleCriteria()
