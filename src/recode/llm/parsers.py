"""LLM response parsers: extract JSON, clean markdown, validate structure."""

from __future__ import annotations

import json
import re
from typing import Any

from loguru import logger
from pydantic import BaseModel, ConfigDict


class GenerationOutput(BaseModel):
    """Structured output extracted from an LLM response."""

    model_config = ConfigDict(frozen=True)

    clinical_report: str
    diagnoses: dict[str, list[str]]
    structured_data: dict[str, Any]


_JSON_BLOCK = re.compile(r"```json(.*?)```", re.DOTALL)
_BOLD = re.compile(r"\*\*(.*?)\*\*")
_HEADER = re.compile(r"^##+ .*$|^--+$", re.MULTILINE)


def extract_json_block(text: str) -> str | None:
    """Extract the content between the first ``json ... `` fence."""
    m = _JSON_BLOCK.search(text)
    return m.group(1).strip() if m else None


def clean_markdown(text: str) -> str:
    """Strip ``**bold**`` markers and ``##`` headers / ``--`` separators."""
    return _HEADER.sub("", _BOLD.sub(r"\1", text))


def fix_multiline_cr(json_text: str) -> str:
    """Escape raw newlines inside the multi-line ``CR`` value."""

    def replacer(match: re.Match[str]) -> str:
        content = match.group(1).replace('"', '\\"').replace('\\\\"', '\\"').replace("\n", "\\n")
        return f'"CR": "{content}"{match.group(2)}'

    return re.sub(r'"CR":\s*"(.*?)"(,\s*"formulations")', replacer, json_text, flags=re.DOTALL)


def strip_comments(json_text: str) -> str:
    """Remove ``//`` line comments and ``/* block */`` comments from JSON."""
    json_text = re.sub(r"//.*", "", json_text)
    return re.sub(r"/\*.*?(?:\*/|\n)", "", json_text, flags=re.DOTALL)


def parse_generation(response: str) -> GenerationOutput | None:
    """Parse a raw LLM response into a validated GenerationOutput (or None)."""
    block = extract_json_block(response)
    if block is None:
        return None
    try:
        data = json.loads(strip_comments(fix_multiline_cr(block)))
    except json.JSONDecodeError as exc:
        logger.warning("Failed to parse JSON: {}", exc)
        return None
    if not (isinstance(data, dict) and "CR" in data and "formulations" in data):
        return None
    formulations = data.get("formulations")
    if not (
        isinstance(formulations, dict)
        and "diagnostics" in formulations
        and "informations" in formulations
    ):
        return None
    return GenerationOutput(
        clinical_report=clean_markdown(data["CR"]).strip(),
        diagnoses=formulations["diagnostics"],
        structured_data=formulations["informations"],
    )
