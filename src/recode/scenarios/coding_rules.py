"""Declarative ATIH coding-rule table.

Transcribes ``utils_v2.py:define_text_management_type`` (lines 676-962) from
a long if/elif cascade into an ordered tuple of rule resolvers.

The order is preserved exactly because semantics rely on earliest-match-wins.
Every rule cites its original line range as a comment.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from recode.models import CancerContext, IcdCode, Procedure, Profile
from recode.referentials import ReferentialRegistry

# ICD codes for diabetes chronic conditions (utils_v2.py loads from CSV; we
# hardcode the known prefix-based subset used by the cascade rule D5).
_DIABETES_CHRONIC_CODES_PREFIX = frozenset({"E10", "E11", "E12", "E13", "E14"})

# ICD codes excluded from acute-exacerbation D5 rule (utils_v2.py:936).
_D5_EXCLUDE_PREFIXES = frozenset({"E05", "J45", "K85"})

# Procedures considered "botulic toxin injection" (utils_v2.py loads from CSV).
# Minimal empty default; production usage reads referentials/raw/procedure_botulic_toxine.csv.
_BOTULIC_TOXIN_PROCEDURES: frozenset[str] = frozenset()


@dataclass(frozen=True, slots=True)
class CodingInput:
    """Raw inputs to the coding-rule cascade, before any derived fields.

    Carries everything that ``resolve_coding_rule`` and ``_derive_context``
    need. Separating this from :class:`CodingContext` makes the "raw inputs"
    vs "derived state" split explicit.
    """

    profile: Profile
    cancer: CancerContext | None
    registry: ReferentialRegistry
    procedure: Procedure
    icd_primary_description: str = ""
    case_management_type_description: str = ""


@dataclass(frozen=True, slots=True)
class CodingContext:
    """State passed to each coding rule predicate.

    Built by :func:`_derive_context` from a :class:`CodingInput`, augmented
    with derived fields (admission-type text, template infix/suffix).
    """

    profile: Profile
    cancer: CancerContext | None
    registry: ReferentialRegistry
    procedure: Procedure
    icd_primary_description: str
    case_management_type_description: str
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


def _tmpl_medical(ctx: CodingContext) -> str:
    """Build ``medical_{in|out}patient{_onco}.txt``."""
    return f"medical_{ctx.template_infix}patient{ctx.template_onco_suffix}.txt"


def _tmpl_medical_plain(ctx: CodingContext) -> str:
    """medical_{in|out}patient.txt (no onco suffix)."""
    return f"medical_{ctx.template_infix}patient.txt"


def _tmpl_medical_outpatient(_ctx: CodingContext) -> str:
    return "medical_outpatient.txt"


def _tmpl_medical_inpatient(_ctx: CodingContext) -> str:
    return "medical_inpatient.txt"


def _tmpl_surgery(ctx: CodingContext) -> str:
    """Build ``surgery_{in|out}patient.txt``."""
    return f"surgery_{ctx.template_infix}patient.txt"


# --- Predicates -------------------------------------------------------------


def _has_cancer_histology(ctx: CodingContext) -> bool:
    return (
        ctx.cancer is not None
        and ctx.cancer.histological_type is not None
        and ctx.profile.drg_parent_code[2:3] not in ("C", "K")
    )


def _in_overnight_study(ctx: CodingContext) -> bool:
    return ctx.profile.case_management_type in ctx.registry.icd_categories.overnight_study


def _in_sensitization_tests(ctx: CodingContext) -> bool:
    return ctx.profile.case_management_type in ctx.registry.icd_categories.sensitization_tests


def _in_transfusion_group(ctx: CodingContext) -> bool:
    return ctx.profile.drg_parent_code in ctx.registry.drg_categories.transfusion


def _in_apheresis_group(ctx: CodingContext) -> bool:
    return ctx.profile.drg_parent_code in ctx.registry.drg_categories.apheresis


def _in_ascites(ctx: CodingContext) -> bool:
    return ctx.profile.icd_primary_code in ctx.registry.icd_categories.ascites


def _in_pleural_effusion(ctx: CodingContext) -> bool:
    return ctx.profile.icd_primary_code in ctx.registry.icd_categories.pleural_effusion


def _is_botulic_outpatient(ctx: CodingContext) -> bool:
    return (
        ctx.procedure.code in _BOTULIC_TOXIN_PROCEDURES
        and ctx.profile.admission_type == "Outpatient"
    )


def _in_chronic_pain(ctx: CodingContext) -> bool:
    return ctx.profile.icd_primary_code in ctx.registry.icd_categories.chronic_intractable_pain


def _is_surgical_not_delivery(ctx: CodingContext) -> bool:
    vaginal = ctx.registry.drg_categories.vaginal_delivery_groups
    csection = ctx.registry.drg_categories.c_section_groups
    delivery_groups = vaginal | csection
    return (
        ctx.profile.drg_parent_code[2:3] == "C"
        and ctx.profile.drg_parent_code not in delivery_groups
    )


def _in_cosmetic_surgery(ctx: CodingContext) -> bool:
    return ctx.profile.case_management_type in ctx.registry.icd_categories.cosmetic_surgery


def _in_plastic_surgery(ctx: CodingContext) -> bool:
    return ctx.profile.case_management_type in ctx.registry.icd_categories.plastic_surgery


def _in_comfort_intervention(ctx: CodingContext) -> bool:
    return ctx.profile.case_management_type in ctx.registry.icd_categories.comfort_intervention


def _in_stomies(ctx: CodingContext) -> bool:
    return ctx.profile.drg_parent_code in ctx.registry.drg_categories.stomies


def _is_colonic_endoscopy(ctx: CodingContext) -> bool:
    # T8: utils_v2.py:813 — only C186 in original code.
    return ctx.profile.icd_primary_code == "C186"


def _in_palliative_care(ctx: CodingContext) -> bool:
    return ctx.profile.drg_parent_code in ctx.registry.drg_categories.palliative_care


def _in_legal_abortion(ctx: CodingContext) -> bool:
    # Placeholder: utils_v2.py reads icd_codes_legal_abortion from CSV.
    return ctx.profile.case_management_type.startswith("Z332") or (
        ctx.profile.case_management_type in {"O04", "O040", "O041"}
    )


def _in_medical_abortion(ctx: CodingContext) -> bool:
    # Placeholder: utils_v2.py reads icd_codes_medical_abortion from CSV.
    return ctx.profile.case_management_type in {"O035", "O036", "O048"}


def _in_delivery(ctx: CodingContext) -> bool:
    vaginal = ctx.registry.drg_categories.vaginal_delivery_groups
    csection = ctx.registry.drg_categories.c_section_groups
    return ctx.profile.drg_parent_code in (vaginal | csection)


def _is_deceased(ctx: CodingContext) -> bool:
    return (
        ctx.profile.drg_parent_code in ctx.registry.drg_categories.deceased
        or ctx.profile.discharge_disposition == "DECES"
    )


# --- Text builders ----------------------------------------------------------


def _text_other_cancer(_ctx: CodingContext) -> str:
    return "Hospitalisation pour prise en charge du cancer"


def _text_overnight(_ctx: CodingContext) -> str:
    return "Prise en charge pour exploration nocturne ou apparentée telle"


def _text_sensitization(_ctx: CodingContext) -> str:
    return (
        "Prise en charge en hospitalistion de jour pour réalisation de test "
        "de réactivité allergiques"
    )


def _text_repeated_treatment(ctx: CodingContext) -> str:
    desc = ctx.profile.drg_parent_description or ""
    return f"Prise en charge pour {desc.lower()}"


def _text_ascites(ctx: CodingContext) -> str:
    return f"Prise en charge pour ponction d'ascite  {ctx.text_admission_type}"


def _text_pleural(ctx: CodingContext) -> str:
    return f"Prise en charge pour ponction pleurale {ctx.text_admission_type}"


def _text_botulic(_ctx: CodingContext) -> str:
    return "Prise en charge en hospitalisation ambulatoire pour injection de toxine botulique"


def _text_chronic_pain(ctx: CodingContext) -> str:
    return f"Prise en charge d'une douleur chronique rebelle {ctx.text_admission_type}"


def _text_surgical(ctx: CodingContext) -> str:
    desc = (ctx.profile.drg_parent_description or "").lower()
    return f"Prise en charge {ctx.text_admission_type} pour {desc}"


def _text_procedure(ctx: CodingContext) -> str:
    proc_desc = ctx.procedure.description.lower()
    return f"Prise en charge {ctx.text_admission_type} pour {proc_desc}"


def _text_stomies(ctx: CodingContext) -> str:
    desc = (ctx.profile.drg_parent_description or "").lower()
    return f"Prise en charge {ctx.text_admission_type} pour {desc}"


def _text_endoscopy(ctx: CodingContext) -> str:
    desc = (ctx.profile.drg_parent_description or "").lower()
    return f"Prise en charge {ctx.text_admission_type} pour {desc}"


def _text_palliative(ctx: CodingContext) -> str:
    return f"Prise en charge {ctx.text_admission_type} pour soins palliatifs"


def _text_legal_abortion(_ctx: CodingContext) -> str:
    return "Prise en charge pour interruption volontaire de grossesse"


def _text_medical_abortion(_ctx: CodingContext) -> str:
    return "Prise en charge pour interruption médicale de grossesse"


def _text_deceased(_ctx: CodingContext) -> str:
    return "Hospitalisation au cours de laquelle le patient est décédé"


# --- Delivery template (random urg vs hospit) -------------------------------


def _delivery_template(ctx: CodingContext, rng: np.random.Generator | None) -> str:
    """Return the delivery template ``.txt`` name.

    Uses a random flip (85/15 hospit vs urg from utils_v2.py:846) based on
    the supplied RNG. When no RNG is available (e.g. in unit tests), falls
    back to the 'hospit' variant deterministically.
    """
    if rng is not None:
        suffix = "_urg" if int(rng.choice(2, p=[0.85, 0.15])) == 1 else "_hospit"
    else:
        suffix = "_hospit"

    csection_procs = ctx.registry.procedure_codes.c_section
    if ctx.procedure.code in csection_procs:
        return f"delivery_inpatient_csection{suffix}.txt"
    return f"delivery_inpatient{suffix}.txt"


def _text_delivery(ctx: CodingContext) -> str:
    csection_procs = ctx.registry.procedure_codes.c_section
    if ctx.procedure.code in csection_procs:
        return "Prise en charge pour accouchement par césarienne"
    return "Prise en charge pour accouchement par voie basse"


# --- Declarative table in cascade order -------------------------------------
# Each rule cites its original utils_v2.py line range.

CODING_RULES: tuple[CodingRuleResolver, ...] = (
    # lines 719-721: cancer with histology, DRG not C/K
    CodingRuleResolver("other", _has_cancer_histology, _text_other_cancer, _tmpl_medical_inpatient),
    # lines 725-729: D3-1 overnight study
    CodingRuleResolver("D3-1", _in_overnight_study, _text_overnight, _tmpl_medical_outpatient),
    # lines 732-735: D3-2 sensitization tests
    CodingRuleResolver(
        "D3-2", _in_sensitization_tests, _text_sensitization, _tmpl_medical_outpatient
    ),
    # lines 738-741: T1 transfusion
    CodingRuleResolver(
        "T1", _in_transfusion_group, _text_repeated_treatment, _tmpl_medical_outpatient
    ),
    # lines 744-747: T1 apheresis
    CodingRuleResolver(
        "T1", _in_apheresis_group, _text_repeated_treatment, _tmpl_medical_outpatient
    ),
    # lines 753-756: T2-R18 ascites puncture
    CodingRuleResolver("T2-R18", _in_ascites, _text_ascites, _tmpl_medical_plain),
    # lines 759-762: T2-J9 pleural effusion puncture
    CodingRuleResolver("T2-J9", _in_pleural_effusion, _text_pleural, _tmpl_medical_plain),
    # lines 766-769: T2-Toxine botulic toxin outpatient
    CodingRuleResolver("T2-Toxine", _is_botulic_outpatient, _text_botulic, _tmpl_medical_plain),
    # lines 772-775: T2-R52 chronic intractable pain
    CodingRuleResolver("T2-R52", _in_chronic_pain, _text_chronic_pain, _tmpl_medical_plain),
    # lines 779-782: T3 surgery (not delivery)
    CodingRuleResolver("T3", _is_surgical_not_delivery, _text_surgical, _tmpl_surgery),
    # lines 786-789: T4 cosmetic surgery
    CodingRuleResolver("T4", _in_cosmetic_surgery, _text_procedure, _tmpl_surgery),
    # lines 793-796: T5 plastic surgery
    CodingRuleResolver("T5", _in_plastic_surgery, _text_procedure, _tmpl_surgery),
    # lines 800-803: T6 comfort intervention
    CodingRuleResolver("T6", _in_comfort_intervention, _text_procedure, _tmpl_surgery),
    # lines 806-809: T7 stomies
    CodingRuleResolver("T7", _in_stomies, _text_stomies, _tmpl_medical_plain),
    # lines 813-816: T8 C186 endoscopy
    CodingRuleResolver("T8", _is_colonic_endoscopy, _text_endoscopy, _tmpl_medical_plain),
    # lines 821-824: T11 palliative care
    CodingRuleResolver("T11", _in_palliative_care, _text_palliative, _tmpl_medical_plain),
    # lines 829-832: Legal_Abortion
    CodingRuleResolver(
        "Legal_Abortion", _in_legal_abortion, _text_legal_abortion, _tmpl_medical_plain
    ),
    # lines 836-839: Medical_Abortion
    CodingRuleResolver(
        "Medical_Abortion", _in_medical_abortion, _text_medical_abortion, _tmpl_medical_plain
    ),
    # lines 842-862: T12 delivery (handled separately because template depends on rng)
    # We use a sentinel rule_id and let resolve_coding_rule() branch on _in_delivery
    # to build the (text, template) pair with access to the RNG.
)


# --- Context construction ---------------------------------------------------


def _derive_context(inp: CodingInput) -> CodingContext:
    is_cancer_primary = inp.profile.icd_primary_code in inp.registry.cancer_codes.all_cancer
    template_onco_suffix = "_onco" if is_cancer_primary else ""
    if inp.profile.admission_type == "Outpatient":
        text_admission = " en hospitalisation ambulatoire"
        template_infix = "out"
    else:
        # typo "hospialisation" preserved from utils_v2.py:705 for golden parity
        text_admission = "en hospialisation complète"
        template_infix = "in"
    return CodingContext(
        profile=inp.profile,
        cancer=inp.cancer,
        registry=inp.registry,
        procedure=inp.procedure,
        icd_primary_description=inp.icd_primary_description,
        case_management_type_description=inp.case_management_type_description,
        text_admission_type=text_admission,
        template_infix=template_infix,
        template_onco_suffix=template_onco_suffix,
    )


def resolve_coding_rule(
    inp: CodingInput,
    *,
    rng: np.random.Generator | None = None,
) -> tuple[str, str, str]:
    """Return ``(rule_id, text, template_name)`` for the coding input.

    Iterates CODING_RULES in order; first match wins. Delivery (T12) and
    chronic-disease cases (T1-chemo/radio, D1/D5/D9, S1-Chronic) are handled
    explicitly because they depend on the RNG or on cancer/chronic flags.
    Falls back to the default medical template when no rule fires.
    """
    ctx = _derive_context(inp)

    # Walk the declarative table in order (first match wins).
    for rule in CODING_RULES:
        if rule.predicate(ctx):
            return rule.rule_id, rule.text(ctx), rule.template(ctx)

    # Delivery (T12) — branches on procedure + RNG for urg vs hospit suffix.
    if _in_delivery(ctx):
        return "T12", _text_delivery(ctx), _delivery_template(ctx, rng)

    # Deceased (utils_v2.py:864-866) — no coding_rule assigned in original.
    if _is_deceased(ctx):
        return "", _text_deceased(ctx), _tmpl_medical_plain(ctx)

    # Chronic-primary branch (utils_v2.py:881-945).
    return _resolve_chronic(ctx, rng)


def _resolve_chronic(  # noqa: PLR0911
    ctx: CodingContext, rng: np.random.Generator | None
) -> tuple[str, str, str]:
    """Handle the `icd_primary_code in chronic` branch of the cascade."""
    profile = ctx.profile
    # Approximate the chronic check: utils_v2.py reads a CSV; here we mark
    # any cancer or diabetes-prefixed code as chronic (subset used downstream).
    icd_prefix = profile.icd_primary_code[:3]
    is_cancer_primary = profile.icd_primary_code in ctx.registry.cancer_codes.all_cancer
    is_diabetes_chronic = icd_prefix in _DIABETES_CHRONIC_CODES_PREFIX
    is_chronic = is_cancer_primary or is_diabetes_chronic
    if not is_chronic:
        return _resolve_acute(ctx)

    # T1 chemotherapy (utils_v2.py:884-891)
    if profile.drg_parent_code in ctx.registry.drg_categories.chemotherapy_root_codes:
        text = f"Prise en charge {ctx.text_admission_type}pour cure de chimiothérapie"
        if ctx.cancer is not None and ctx.cancer.chemotherapy_regimen is not None:
            text += f". Le protocole actuellement suivi est : {ctx.cancer.chemotherapy_regimen}"
        return "T1", text, f"medical_{ctx.template_infix}patient_onco.txt"

    # T1 medication (utils_v2.py:894-897)
    if profile.case_management_type == "Z512":
        text = (
            f"Prise en charge {ctx.text_admission_type}pour administration d'un "
            "traitement médicamenteux nécessitant une hospitalisation"
        )
        return "T1", text, f"medical_{ctx.template_infix}patient.txt"

    # T1 radiotherapy (utils_v2.py:900-903)
    if profile.drg_parent_code in ctx.registry.drg_categories.radiotherapy_root_codes:
        text = (
            f"Prise en charge {ctx.text_admission_type} pour réalisation du traitement "
            "par radiothérapie"
        )
        return "T1", text, f"medical_{ctx.template_infix}patient_onco.txt"

    # D1/D5/D9 for DP case_management_type (utils_v2.py:906-939)
    if profile.case_management_type == "DP":
        return _resolve_dp_chronic(ctx, rng, is_cancer_primary, is_diabetes_chronic)

    # S1-Chronic supervision (utils_v2.py:942-945)
    # Placeholder: icd_codes_supervision_chronic_disease loaded from CSV in utils_v2.
    # We approximate with "Z09" which is supervision after treatment.
    if profile.case_management_type.startswith("Z09"):
        text = f"Surveillance {ctx.text_admission_type} de {ctx.icd_primary_description}"
        return "S1-Chronic", text, _tmpl_medical(ctx)

    return _resolve_acute(ctx)


def _resolve_dp_chronic(
    ctx: CodingContext,
    rng: np.random.Generator | None,
    is_cancer_primary: bool,
    is_diabetes_chronic: bool,
) -> tuple[str, str, str]:
    """Handle the DP (direct primary) branch for chronic diseases."""
    option = int(rng.choice(4, p=[0.4, 0.2, 0.2, 0.2])) if rng is not None else 0

    desc = ctx.icd_primary_description
    template = _tmpl_medical(ctx)

    if option == 0:
        return (
            "D1",
            f"Première hospitalisation  {ctx.text_admission_type} pour découverte de {desc}",
            template,
        )
    if option == 1:
        return (
            "D9",
            f"Hospitalisation {ctx.text_admission_type} pour bilan initial "
            f"pré-trérapeutique de {desc}",
            template,
        )
    # option 2 & 3 map to D5 per the original cascade (with subtle differences
    # on cancer vs diabetes vs other).
    if is_cancer_primary:
        return (
            "D5",
            f"Hospitalisation {ctx.text_admission_type} pour rechutte après traitement de  {desc}",
            template,
        )
    if is_diabetes_chronic:
        return (
            "D5",
            f"Hospitalisation {ctx.text_admission_type} pour changement de stratégie "
            f"thérapeutique  {desc}",
            template,
        )
    if ctx.profile.icd_primary_code[:3] not in _D5_EXCLUDE_PREFIXES:
        return (
            "D5",
            f"Hospitalisation {ctx.text_admission_type} pour poussée aigue de la maladie  {desc}",
            template,
        )
    # Fallback: empty rule_id (no case matched in original).
    return "", "", template


def _resolve_acute(ctx: CodingContext) -> tuple[str, str, str]:
    """Handle the acute-pathology fallback (utils_v2.py:948-961)."""
    if ctx.profile.case_management_type == "DP":
        text = (
            f"Pour prise en charge diagnostique et thérapeutique du diagnotic principal "
            f"{ctx.text_admission_type}"
        )
    else:
        text = (
            f"Pour prise en charge {ctx.text_admission_type} pour "
            f"{ctx.case_management_type_description}"
        )
    return "other", text, _tmpl_medical(ctx)


# Backwards-compat exports for users of the stub signature
__all__ = [
    "CODING_RULES",
    "CodingContext",
    "CodingInput",
    "CodingRuleResolver",
    "IcdCode",
    "resolve_coding_rule",
]
