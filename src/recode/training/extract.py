"""Load raw batch JSONL outputs and parse them into clinical reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from recode.llm.parsers import parse_generation


def load_batch_jsonl(batch_json: Path) -> list[dict[str, Any]]:
    """Read a JSONL file into a list of dicts."""
    return [json.loads(line) for line in batch_json.read_text(encoding="utf-8").splitlines()]


def extract_clinical_reports(batch_json: Path) -> pd.DataFrame:
    """Parse a batch output JSONL into (custom_id, clinical_report, diagnoses, structured_data)."""
    raw = load_batch_jsonl(batch_json)
    parsed: list[dict[str, Any]] = []
    for item in raw:
        if "response" not in item or not item["response"]:
            continue
        content = item["response"]["body"]["choices"][0]["message"]["content"]
        gen = parse_generation(content)
        if gen is None:
            logger.warning("Skipping unparseable response (custom_id={})", item.get("custom_id"))
            continue
        parsed.append(
            {
                "custom_id": int(item["custom_id"]),
                "clinical_report": gen.clinical_report,
                "response_diagnosis": gen.diagnoses,
                "response_structured_data": gen.structured_data,
            }
        )
    return pd.DataFrame(parsed)
