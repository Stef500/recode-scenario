"""Tests for typed YAML constants."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


def test_cancer_codes_from_yaml(tmp_path: Path) -> None:
    from recode.referentials.constants import CancerCodes

    yaml_file = tmp_path / "cancer.yaml"
    yaml_file.write_text(
        yaml.safe_dump(
            {
                "metastasis_lymph_nodes": ["C770", "C771"],
                "metastasis_other": ["C780"],
                "contact_treatment": ["Z511"],
                "chemotherapy_non_tumoral": ["Z512"],
            }
        )
    )
    codes = CancerCodes.from_yaml(yaml_file)
    assert "C770" in codes.metastasis_lymph_nodes
    assert isinstance(codes.metastasis_lymph_nodes, frozenset)
    assert codes.metastasis_other == frozenset({"C780"})


def test_cancer_codes_immutable() -> None:
    from recode.referentials.constants import CancerCodes

    codes = CancerCodes(
        metastasis_lymph_nodes=frozenset({"C770"}),
        metastasis_other=frozenset(),
        contact_treatment=frozenset(),
        chemotherapy_non_tumoral=frozenset(),
    )
    with pytest.raises((AttributeError, TypeError)):
        codes.metastasis_lymph_nodes = frozenset({"X"})  # type: ignore[misc]


def test_drg_categories_from_yaml(tmp_path: Path) -> None:
    from recode.referentials.constants import DrgCategories

    yaml_file = tmp_path / "drg.yaml"
    yaml_file.write_text(
        yaml.safe_dump(
            {
                "chemotherapy_root_codes": ["28Z07"],
                "radiotherapy_root_codes": ["17K04"],
                "vaginal_delivery_groups": ["14Z10"],
                "c_section_groups": ["14C06"],
                "transplant": [],
                "transfusion": ["28Z14"],
                "apheresis": [],
                "palliative_care": [],
                "stomies": [],
                "deceased": [],
                "diagnostic_workup": [],
            }
        )
    )
    cats = DrgCategories.from_yaml(yaml_file)
    assert "28Z07" in cats.chemotherapy_root_codes
    assert "14C06" in cats.c_section_groups


def test_icd_categories_from_yaml(tmp_path: Path) -> None:
    from recode.referentials.constants import IcdCategories

    yaml_file = tmp_path / "icd.yaml"
    yaml_file.write_text(
        yaml.safe_dump(
            {
                "ascites": ["R18"],
                "pleural_effusion": ["J90"],
                "chronic_intractable_pain": [],
                "cosmetic_surgery": [],
                "plastic_surgery": [],
                "comfort_intervention": [],
                "prophylactic_intervention": [],
                "overnight_study": [],
                "sensitization_tests": [],
                "exclusions": [],
                "exclusion_specialty": [],
            }
        )
    )
    cats = IcdCategories.from_yaml(yaml_file)
    assert "R18" in cats.ascites


def test_procedure_codes_from_yaml(tmp_path: Path) -> None:
    from recode.referentials.constants import ProcedureCodes

    yaml_file = tmp_path / "proc.yaml"
    yaml_file.write_text(
        yaml.safe_dump(
            {"vaginal_delivery": ["JQGD001"], "c_section": ["JQGA002"]}
        )
    )
    codes = ProcedureCodes.from_yaml(yaml_file)
    assert "JQGD001" in codes.vaginal_delivery
