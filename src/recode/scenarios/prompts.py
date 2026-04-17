"""Prompt construction: user + system + prefix.

``build_user_prompt`` is an orchestrator — each section of the prompt is a
small pure helper below. Preserves original strings byte-for-byte (golden
tests lock the format).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from recode.models import (
    CancerContext,
    Diagnosis,
    Gender,
    Patient,
    Procedure,
    Scenario,
    Stay,
)
from recode.scenarios.cim10_enrichment import (
    format_cim10_enrichment,
    is_enrichable_das,
)

if TYPE_CHECKING:
    from recode.referentials import ReferentialRegistry


_HEADER = "**SCÉNARIO DE DÉPART :**\n"

_FALLBACK_HISTOLOGICAL = (
    "- Type anatomopathologique de la tumeur primaire : "
    "Vous choisirez vous même un type histologique cohérent "
    "avec la localisation anatomique\n"
)

_FALLBACK_TNM = (
    "- Score TNM : Si la notion de score de TNM est pertinente "
    "avec le type histologique et la localisation anatomique, "
    "vous choisirez un score TNM\n"
)

_FALLBACK_BIOMARKERS = (
    "- Biomarqueurs tumoraux : Vous choisirez des biomarqueurs "
    "tumoraux cohérents avec la localisation anatomique et "
    "l'histologie de la tumeur\n"
)


def _interpret_gender(gender: Gender) -> str:
    return "Masculin" if gender == 1 else "Féminin"


def _format_patient_identity(p: Patient, s: Stay) -> str:
    return (
        f"- Âge du patient : {p.age} ans\n"
        f"- Sexe du patient : {_interpret_gender(p.gender)}\n"
        f"- Date d'entrée : {s.date_entry.strftime('%d/%m/%Y')}\n"
        f"- Date de sortie : {s.date_discharge.strftime('%d/%m/%Y')}\n"
        f"- Date de naissance : {p.date_of_birth.strftime('%d/%m/%Y')}\n"
        f"- Nom du patient : {p.last_name}\n"
        f"- Prénom du patient : {p.first_name}\n"
    )


def _format_cancer_tumor_info(d: Diagnosis, c: CancerContext | None) -> str:
    if c is None:
        return ""
    parts: list[str] = [
        f"- Localisation anatomique de la tumeur primaire : "
        f"{d.icd_primary_description} ({d.icd_primary_code})\n",
        f"- Type anatomopathologique de la tumeur primaire : {c.histological_type}\n"
        if c.histological_type
        else _FALLBACK_HISTOLOGICAL,
        f"- Score TNM : {c.score_tnm}\n" if c.score_tnm else _FALLBACK_TNM,
    ]
    if c.stage:
        parts.append(f"- Stade tumoral : {c.stage}\n")
    parts.append(
        f"- Biomarqueurs tumoraux : {c.biomarkers}\n" if c.biomarkers else _FALLBACK_BIOMARKERS
    )
    return "".join(parts)


def _format_admission_discharge(s: Stay) -> str:
    parts: list[str] = []
    if s.admission_mode:
        parts.append(f"- Mode d'entrée' : {s.admission_mode}\n")
    if s.discharge_disposition:
        parts.append(f"- Mode de sortie' : {s.discharge_disposition}\n")
    return "".join(parts)


def _format_icd_coding_block(d: Diagnosis, registry: ReferentialRegistry | None) -> str:
    header = (
        f"- Contexte de l'hospitalisation : {d.case_management_type_text}. "
        f"{d.case_management_description}\n"
        "- Codage CIM10 :\n"
        f"   * Diagnostic principal : {d.icd_primary_description} ({d.icd_primary_code})\n"
    )
    if registry is None or not registry.has_cim10_enrichment():
        # Fallback: pre-built DAS text, as in legacy utils_v2.
        return header + "   * Diagnostic associés : \n" + f"{d.text_secondary_icd_official}\n"

    hierarchy, notes = registry.cim10_lookups
    dp_enrichment = format_cim10_enrichment(d.icd_primary_code, hierarchy, notes)
    das_block = ["   * Diagnostic associés : \n"]
    for das_code in d.icd_secondary_codes:
        desc = registry.icd_description_for(das_code)
        das_block.append(f"- {desc} ({das_code})\n" if desc else f"- ({das_code})\n")
        if is_enrichable_das(das_code):
            das_block.append(format_cim10_enrichment(das_code, hierarchy, notes))
    return header + dp_enrichment + "".join(das_block)


def _format_procedure(proc: Procedure, drg_parent_code: str) -> str:
    # DRG roots with position 2 in ("C", "K") are surgery / endoscopy — the only
    # ones that carry a CCAM acte line in the legacy format.
    if proc.code and drg_parent_code[2:3] in ("C", "K"):
        return f"* Acte CCAM :\n{proc.description.lower()}\n"
    return ""


def _format_physician_info(s: Stay) -> str:
    parts = [f"- Nom du médecin / signataire : {s.physician_first_name} {s.physician_last_name}\n"]
    if s.department:
        parts.append(f"- Service : {s.department}\n")
    if s.hospital:
        parts.append(f"- Hôpital : {s.hospital}\n")
    return "".join(parts)


def _format_cancer_instructions(c: CancerContext | None) -> str:
    if c is None:
        return ""
    parts = ["Ce cas clinique concerne un patient présentant un cancer\n"]
    if c.histological_type:
        parts.append(
            "Vous choisirez un épisode de traitement sachant que les "
            "recommandations pour ce stade du cancer sont les suivantes :\n"
        )
        parts.append(f"   - Schéma thérapeutique : {c.treatment_recommendation}\n")
        if c.chemotherapy_regimen:
            parts.append(f"   - Protocole de chimiothérapie : {c.chemotherapy_regimen}\n")
    parts.append(
        "Veillez à bien préciser le type histologique et la valeur des biomarqueurs si recherchés\n"
    )
    return "".join(parts)


def build_user_prompt(
    scenario: Scenario,
    *,
    registry: ReferentialRegistry | None = None,
) -> str:
    """Build the user prompt describing the clinical scenario.

    Sections, in order:

    1. Patient identity (age, gender, dates, names).
    2. Cancer tumor info (only if ``scenario.cancer is not None``).
    3. Admission / discharge modes.
    4. ICD-10 coding block (contexte + DP + DAS), with optional CIM-10
       hierarchy / Inclus / Exclus enrichment when ``registry`` is provided.
    5. Procedure (CCAM) line (surgery / endoscopy DRGs only).
    6. Physician / department / hospital.
    7. Cancer instructions trailer (only if ``scenario.cancer is not None``).

    Output is byte-identical to ``utils_v2.py:make_prompts_marks_from_scenario``
    when ``registry`` is ``None`` — locked by regression tests.
    """
    return "".join(
        [
            _HEADER,
            _format_patient_identity(scenario.patient, scenario.stay),
            _format_cancer_tumor_info(scenario.diagnosis, scenario.cancer),
            _format_admission_discharge(scenario.stay),
            _format_icd_coding_block(scenario.diagnosis, registry),
            _format_procedure(scenario.procedure, scenario.drg_parent_code),
            _format_physician_info(scenario.stay),
            _format_cancer_instructions(scenario.cancer),
        ]
    )


def build_system_prompt(scenario: Scenario, *, templates_dir: Path = Path("templates")) -> str:
    """Read the system prompt template matching the scenario's template_name."""
    template_path = templates_dir / scenario.template_name
    return template_path.read_text(encoding="utf-8")


_PREFIX_NON_CANCER = """Le compte rendu suivant respecte les élements suivants :
        - les diagnostics ont une formulation moins formelle que la définition du code
        - le plan du CRH est conforme aux recommandations.
        """

_PREFIX_CANCER = """Le compte rendu suivant respecte les élements suivants :
        - les diagnostics ont une formulation moins formelle que la définition du code
        - le type histologique et la valeur des biomarqueurs si recherchés
        - le plan du CRH est conforme aux recommandations.
        """


def build_prefix(scenario: Scenario) -> str:
    """Return the assistant-message prefix (cancer vs non-cancer)."""
    return _PREFIX_CANCER if scenario.cancer is not None else _PREFIX_NON_CANCER
