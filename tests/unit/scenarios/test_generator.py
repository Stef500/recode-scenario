"""Tests for ScenarioGenerator facade."""

from __future__ import annotations

from pathlib import Path

FIXTURES = Path("tests/fixtures/referentials")


def test_generator_produces_scenario() -> None:
    from recode.models import Profile, Scenario
    from recode.referentials import ReferentialRegistry
    from recode.scenarios.generator import ScenarioGenerator

    reg = ReferentialRegistry(processed_dir=FIXTURES, constants_dir=FIXTURES / "constants")
    gen = ScenarioGenerator(registry=reg, base_seed=42)
    p = Profile(
        drg_parent_code="05M09",
        icd_primary_code="I500",
        case_management_type="I500",
        age_class="[80-[",
        age_class_2="[50-[",
        gender=2,
        weight=1,
        admission_type="Inpatient",
        length_of_stay=7,
        admission_mode="URGENCES",
        specialty="CARDIOLOGIE",
        drg_parent_description="Insuffisances cardiaques",
    )
    s = gen.generate(p)
    assert isinstance(s, Scenario)
    assert s.patient.age >= 80
    assert s.stay.admission_type == "Inpatient"


def test_generator_reproducible() -> None:
    from recode.models import Profile
    from recode.referentials import ReferentialRegistry
    from recode.scenarios.generator import ScenarioGenerator

    reg = ReferentialRegistry(processed_dir=FIXTURES, constants_dir=FIXTURES / "constants")
    gen1 = ScenarioGenerator(registry=reg, base_seed=42)
    gen2 = ScenarioGenerator(registry=reg, base_seed=42)
    p = Profile(
        drg_parent_code="05M09",
        icd_primary_code="I500",
        case_management_type="I500",
        age_class="[80-[",
        age_class_2="[50-[",
        gender=2,
        weight=1,
        admission_type="Inpatient",
        length_of_stay=7,
        admission_mode="URGENCES",
        specialty="CARDIOLOGIE",
        drg_parent_description="Insuffisances cardiaques",
    )
    s1 = gen1.generate(p)
    s2 = gen2.generate(p)
    assert s1.patient.first_name == s2.patient.first_name
    assert s1.stay.date_entry == s2.stay.date_entry
    assert s1.diagnosis.coding_rule == s2.diagnosis.coding_rule


def test_generate_batch_iterates() -> None:
    from recode.models import Profile
    from recode.referentials import ReferentialRegistry
    from recode.scenarios.generator import ScenarioGenerator

    reg = ReferentialRegistry(processed_dir=FIXTURES, constants_dir=FIXTURES / "constants")
    gen = ScenarioGenerator(registry=reg, base_seed=42)
    profiles = [
        Profile(
            drg_parent_code="05M09",
            icd_primary_code="I500",
            case_management_type="I500",
            age_class="[80-[",
            age_class_2="[50-[",
            gender=2,
            weight=1,
            admission_type="Inpatient",
            length_of_stay=7,
            admission_mode="URGENCES",
            specialty="CARDIOLOGIE",
            drg_parent_description="Insuffisances cardiaques",
        ),
        Profile(
            drg_parent_code="14Z10",
            icd_primary_code="O800",
            case_management_type="O800",
            age_class="[18-30[",
            age_class_2="[18-50[",
            gender=2,
            weight=1,
            admission_type="Inpatient",
            length_of_stay=3,
            admission_mode="DOMICILE",
            specialty="OBSTETRIQUE",
            drg_parent_description="Accouchements voie basse",
        ),
    ]
    scenarios = list(gen.generate_batch(iter(profiles)))
    assert len(scenarios) == 2
