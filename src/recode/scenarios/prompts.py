"""Prompt construction: user + system + prefix.

Preserves original strings byte-for-byte for golden-file compatibility.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from recode.models import Gender, Scenario

if TYPE_CHECKING:
    from recode.referentials import ReferentialRegistry


def _interpret_gender(gender: Gender) -> str:
    return "Masculin" if gender == 1 else "Féminin"


def build_user_prompt(  # noqa: PLR0912, PLR0915
    scenario: Scenario,
    *,
    registry: ReferentialRegistry | None = None,
) -> str:
    """Build the user prompt describing the clinical scenario.

    Reproduces the exact format of ``utils_v2.py:make_prompts_marks_from_scenario``
    (lines 1162-1261). Sections appear in the same order as the original.
    """
    parts: list[str] = ["**SCÉNARIO DE DÉPART :**\n"]
    p = scenario.patient
    s = scenario.stay
    d = scenario.diagnosis
    c = scenario.cancer
    proc = scenario.procedure

    parts.append(f"- Âge du patient : {p.age} ans\n")
    parts.append(f"- Sexe du patient : {_interpret_gender(p.gender)}\n")
    parts.append(f"- Date d'entrée : {s.date_entry.strftime('%d/%m/%Y')}\n")
    parts.append(f"- Date de sortie : {s.date_discharge.strftime('%d/%m/%Y')}\n")
    parts.append(f"- Date de naissance : {p.date_of_birth.strftime('%d/%m/%Y')}\n")
    parts.append(f"- Nom du patient : {p.last_name}\n")
    parts.append(f"- Prénom du patient : {p.first_name}\n")

    if c is not None:
        parts.append(
            f"- Localisation anatomique de la tumeur primaire : "
            f"{d.icd_primary_description} ({d.icd_primary_code})\n"
        )
        if c.histological_type:
            parts.append(
                f"- Type anatomopathologique de la tumeur primaire : {c.histological_type}\n"
            )
        else:
            parts.append(
                "- Type anatomopathologique de la tumeur primaire : "
                "Vous choisirez vous même un type histologique cohérent "
                "avec la localisation anatomique\n"
            )
        if c.score_tnm:
            parts.append(f"- Score TNM : {c.score_tnm}\n")
        else:
            parts.append(
                "- Score TNM : Si la notion de score de TNM est pertinente "
                "avec le type histologique et la localisation anatomique, "
                "vous choisirez un score TNM\n"
            )
        if c.stage:
            parts.append(f"- Stade tumoral : {c.stage}\n")
        if c.biomarkers:
            parts.append(f"- Biomarqueurs tumoraux : {c.biomarkers}\n")
        else:
            parts.append(
                "- Biomarqueurs tumoraux : Vous choisirez des biomarqueurs "
                "tumoraux cohérents avec la localisation anatomique et "
                "l'histologie de la tumeur\n"
            )

    if s.admission_mode:
        parts.append(f"- Mode d'entrée' : {s.admission_mode}\n")
    if s.discharge_disposition:
        parts.append(f"- Mode de sortie' : {s.discharge_disposition}\n")

    parts.append(
        f"- Contexte de l'hospitalisation : {d.case_management_type_text}. "
        f"{d.case_management_description}\n"
    )
    parts.append("- Codage CIM10 :\n")
    parts.append(
        f"   * Diagnostic principal : {d.icd_primary_description} ({d.icd_primary_code})\n"
    )
    parts.append("   * Diagnostic associés : \n")
    parts.append(f"{d.text_secondary_icd_official}\n")

    if proc.code and scenario.drg_parent_code[2:3] in ("C", "K"):
        parts.append(f"* Acte CCAM :\n{proc.description.lower()}\n")

    parts.append(
        f"- Nom du médecin / signataire : {s.physician_first_name} {s.physician_last_name}\n"
    )
    if s.department:
        parts.append(f"- Service : {s.department}\n")
    if s.hospital:
        parts.append(f"- Hôpital : {s.hospital}\n")

    if c is not None:
        parts.append("Ce cas clinique concerne un patient présentant un cancer\n")
        if c.histological_type:
            parts.append(
                "Vous choisirez un épisode de traitement sachant que les "
                "recommandations pour ce stade du cancer sont les suivantes :\n"
            )
            parts.append(f"   - Schéma thérapeutique : {c.treatment_recommendation}\n")
            if c.chemotherapy_regimen:
                parts.append(f"   - Protocole de chimiothérapie : {c.chemotherapy_regimen}\n")
        parts.append(
            "Veillez à bien préciser le type histologique et la valeur des "
            "biomarqueurs si recherchés\n"
        )

    return "".join(parts)


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
