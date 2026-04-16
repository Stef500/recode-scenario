"""Declarative ATIH coding-rule table.

Transcribes ``utils_v2.py:define_text_management_type`` (lines 653-938) from
a long if/elif cascade into an ordered tuple of rule resolvers.

The order is preserved exactly because semantics rely on earliest-match-wins.

Task 3.9 fills in the complete rule set. This stub exposes the signature.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from recode.models import CancerContext, Profile
from recode.referentials import ReferentialRegistry


@dataclass(frozen=True, slots=True)
class CodingContext:
    """State passed to each coding rule predicate."""

    profile: Profile
    cancer: CancerContext | None
    registry: ReferentialRegistry
    text_admission_type: str
    template_infix: str
    template_onco_suffix: str


@dataclass(frozen=True, slots=True)
class CodingRuleResolver:
    """One row in the declarative coding rule table."""

    rule_id: str
    predicate: Callable[[CodingContext], bool]
    text: Callable[[CodingContext], str]
    template: Callable[[CodingContext], str]


def _template_medical_inpatient(_ctx: CodingContext) -> str:
    return "medical_inpatient.txt"


CODING_RULES: tuple[CodingRuleResolver, ...] = ()


def _derive_template_fragments(
    profile: Profile, cancer: CancerContext | None, registry: ReferentialRegistry
) -> CodingContext:
    is_cancer_primary = profile.icd_primary_code in registry.cancer_codes.all_cancer
    template_onco_suffix = "_onco" if is_cancer_primary else ""
    if profile.admission_type == "Outpatient":
        text_admission = " en hospitalisation ambulatoire"
        template_infix = "out"
    else:
        # typo préservée ligne 682 utils_v2.py
        text_admission = "en hospialisation complète"
        template_infix = "in"
    return CodingContext(
        profile=profile,
        cancer=cancer,
        registry=registry,
        text_admission_type=text_admission,
        template_infix=template_infix,
        template_onco_suffix=template_onco_suffix,
    )


def resolve_coding_rule(
    profile: Profile, cancer: CancerContext | None, registry: ReferentialRegistry
) -> tuple[str, str, str]:
    """Return ``(rule_id, text, template_name)`` for the profile.

    Iterates CODING_RULES in order; first match wins. Falls back to the
    default medical template when no rule fires.
    """
    ctx = _derive_template_fragments(profile, cancer, registry)
    for rule in CODING_RULES:
        if rule.predicate(ctx):
            return rule.rule_id, rule.text(ctx), rule.template(ctx)
    return "default", "", _template_medical_inpatient(ctx)
