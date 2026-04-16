"""Typed constants loaded from YAML files.

These replace the hardcoded Python lists in the original utils_v2.py:179-216.
Each dataclass is frozen and uses frozenset for fast membership tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


def _load_yaml(path: Path) -> dict[str, Any]:
    data: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data


def _frozensets(data: dict[str, Any]) -> dict[str, frozenset[str]]:
    return {k: frozenset(v) for k, v in data.items()}


@dataclass(frozen=True, slots=True)
class CancerCodes:
    """ICD codes related to cancer management."""

    metastasis_lymph_nodes: frozenset[str]
    metastasis_other: frozenset[str]
    contact_treatment: frozenset[str]
    chemotherapy_non_tumoral: frozenset[str]

    @classmethod
    def from_yaml(cls, path: Path) -> CancerCodes:
        """Load a CancerCodes from the given YAML file."""
        return cls(**_frozensets(_load_yaml(path)))


@dataclass(frozen=True, slots=True)
class DrgCategories:
    """DRG root code groupings by management type."""

    chemotherapy_root_codes: frozenset[str]
    radiotherapy_root_codes: frozenset[str]
    vaginal_delivery_groups: frozenset[str]
    c_section_groups: frozenset[str]
    transplant: frozenset[str]
    transfusion: frozenset[str]
    apheresis: frozenset[str]
    palliative_care: frozenset[str]
    stomies: frozenset[str]
    deceased: frozenset[str]
    diagnostic_workup: frozenset[str]

    @classmethod
    def from_yaml(cls, path: Path) -> DrgCategories:
        """Load a DrgCategories from the given YAML file."""
        return cls(**_frozensets(_load_yaml(path)))


@dataclass(frozen=True, slots=True)
class IcdCategories:
    """ICD code categories for ATIH rule resolution."""

    ascites: frozenset[str]
    pleural_effusion: frozenset[str]
    chronic_intractable_pain: frozenset[str]
    cosmetic_surgery: frozenset[str]
    plastic_surgery: frozenset[str]
    comfort_intervention: frozenset[str]
    prophylactic_intervention: frozenset[str]
    overnight_study: frozenset[str]
    sensitization_tests: frozenset[str]
    exclusions: frozenset[str]
    exclusion_specialty: frozenset[str]

    @classmethod
    def from_yaml(cls, path: Path) -> IcdCategories:
        """Load an IcdCategories from the given YAML file."""
        return cls(**_frozensets(_load_yaml(path)))


@dataclass(frozen=True, slots=True)
class ProcedureCodes:
    """CCAM procedure codes by delivery method."""

    vaginal_delivery: frozenset[str]
    c_section: frozenset[str]

    @classmethod
    def from_yaml(cls, path: Path) -> ProcedureCodes:
        """Load a ProcedureCodes from the given YAML file."""
        return cls(**_frozensets(_load_yaml(path)))
