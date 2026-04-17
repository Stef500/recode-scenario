"""ScenarioGenerator — public facade for the scenario generation pipeline."""

from __future__ import annotations

from collections.abc import Iterable, Iterator

from loguru import logger

from recode.models import Profile, Scenario
from recode.referentials import ReferentialRegistry
from recode.scenarios.cancer import build_cancer_context
from recode.scenarios.coding_rules import resolve_coding_rule
from recode.scenarios.demographics import (
    build_patient,
    build_stay,
    compute_stay_dates,
    pick_year,
)
from recode.scenarios.diagnosis import build_diagnosis
from recode.scenarios.procedures import sample_procedure
from recode.scenarios.rng import derive_scenario_rng


class ScenarioGenerator:
    """Stateless scenario generator.

    Thread-safe: all state lives on the injected ``ReferentialRegistry``
    (lazy-read) and the per-call ``numpy.random.Generator``.
    """

    def __init__(self, registry: ReferentialRegistry, base_seed: int = 0) -> None:
        """Initialize the generator.

        Args:
            registry: Referential registry providing all look-up data.
            base_seed: Base seed controlling the run's reproducibility.
        """
        self._registry = registry
        self._base_seed = base_seed
        logger.debug("ScenarioGenerator(base_seed={})", base_seed)

    def generate(self, profile: Profile) -> Scenario:
        """Generate one scenario from a profile."""
        rng = derive_scenario_rng(profile, self._base_seed)
        year = pick_year(rng)
        date_entry, date_discharge = compute_stay_dates(profile, year, rng)
        cancer = build_cancer_context(profile, self._registry, rng)
        patient = build_patient(profile, date_entry, self._registry, rng)
        stay = build_stay(profile, date_entry, date_discharge, self._registry, rng)
        procedure = sample_procedure(profile, self._registry, rng)
        diagnosis = build_diagnosis(profile, self._registry, cancer, rng, procedure=procedure)

        _rule_id, _rule_text, template = resolve_coding_rule(
            profile,
            cancer,
            self._registry,
            procedure=procedure,
            icd_primary_description=diagnosis.icd_primary_description,
            case_management_type_description=diagnosis.case_management_type_description,
            rng=rng,
        )

        return Scenario(
            patient=patient,
            stay=stay,
            diagnosis=diagnosis,
            procedure=procedure,
            cancer=cancer,
            drg_parent_code=profile.drg_parent_code,
            drg_parent_description=self._resolve_drg_description(profile),
            los_mean=profile.los_mean if profile.los_mean is not None else 0.0,
            los_sd=profile.los_sd if profile.los_sd is not None else 0.0,
            template_name=template,
        )

    def generate_batch(self, profiles: Iterable[Profile]) -> Iterator[Scenario]:
        """Iterate over profiles yielding scenarios (lazy, parallelizable)."""
        for p in profiles:
            yield self.generate(p)

    def _resolve_drg_description(self, profile: Profile) -> str:
        if profile.drg_parent_description:
            return profile.drg_parent_description
        groups = self._registry.drg_groups
        match = groups.loc[
            groups["drg_parent_code"] == profile.drg_parent_code, "drg_parent_description"
        ]
        return str(match.iloc[0]) if not match.empty else ""
