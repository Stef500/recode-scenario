"""Extract ICD coding targets for fine-tuning."""

from __future__ import annotations

import re
from typing import Final

import pandas as pd
from pydantic import BaseModel, ConfigDict

_CODE_PARENS: Final = re.compile(r"\(([A-Z]\d{2,5}\+?\d*)\)")
_CODE_BARE: Final = re.compile(r"[A-Z]\d{2,5}\+?\d*")
_DESCRIPTION: Final = re.compile(r"[A-Z][a-z].*")


class IcdCodingTarget(BaseModel):
    """ICD coding target for a single generated clinical report."""

    model_config = ConfigDict(frozen=True)

    icd_primary_pred: str
    icd_secondary_pred: list[str]
    coding_text: str
    coding_list: list[str]


def _normalize_code(text_code: str) -> tuple[str, str]:
    m = _CODE_PARENS.search(text_code)
    if m:
        return m.group(1), text_code
    bare = _CODE_BARE.search(text_code)
    code = bare.group(0) if bare else ""
    desc_m = _DESCRIPTION.search(text_code)
    desc = desc_m.group(0) if desc_m else ""
    return code, f"{desc}({code})"


def extract_target(case: pd.Series) -> IcdCodingTarget:
    """Build an ICD coding target from a row of the joined batch result.

    Preserves the historical output format byte-for-byte, including the
    intentional typo ``"Diagnotics associés"`` (downstream consumer contract).
    """
    pcid = "- Diagnostic principal : \n"
    # "Diagnotics" typo preserved intentionally
    sicd = "- Diagnotics associés : \n"
    cmt = "- Motif de recours au soin (code en Z du chapitre XXI): \n"
    if case["case_management_type"] == "DP":
        cmt += "* Aucun\n"
    else:
        cmt += f"* {case['case_management_type_description']}({case['case_management_type']})\n"

    icd_primary = ""
    icd_secondary: list[str] = []
    coding_list: list[str] = []

    for text_code, formulations in case["response_diagnosis"].items():
        code, formatted = _normalize_code(text_code)
        joined = ",".join(formulations)
        if code and re.search(code, case["icd_primary_code"]):
            pcid += f"* {formatted} - {joined}\n"
            icd_primary = code
        else:
            sicd += f"* {formatted} - {joined}\n"
            if code:
                icd_secondary.append(code)
        if code:
            coding_list.append(code)

    return IcdCodingTarget(
        icd_primary_pred=icd_primary,
        icd_secondary_pred=icd_secondary,
        coding_text=pcid + sicd + cmt,
        coding_list=coding_list,
    )
