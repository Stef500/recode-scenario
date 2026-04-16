"""Tests for CodingRule model."""

from __future__ import annotations


def test_coding_rule_from_yaml_dict() -> None:
    from recode.models import CodingRule

    data = {
        "id": "D1",
        "instruction_id": "Règle D1",
        "clinical_coding_scenario": "HOSPITALISATION POUR DIAGNOSTIC...",
        "icd10_coding_instruction_atih": "...",
        "icd10_coding_instruction": "...",
        "criteria": {"primary_diagnosis": "!= Z"},
    }
    rule = CodingRule.model_validate(data)
    assert rule.id == "D1"
    assert rule.criteria.primary_diagnosis == "!= Z"
