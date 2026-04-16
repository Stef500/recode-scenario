"""Tests for training.extract."""

from __future__ import annotations

import json
from pathlib import Path

_GOOD_BODY_1 = (
    "```json\n"
    "{"
    '"CR": "Compte-rendu 1.", '
    '"formulations": {'
    '"diagnostics": {"Insuffisance cardiaque (I500)": ["ICC"]}, '
    '"informations": {"age": 65}'
    "}"
    "}\n"
    "```"
)
_GOOD_BODY_2 = (
    "```json\n"
    "{"
    '"CR": "Compte-rendu 2.", '
    '"formulations": {'
    '"diagnostics": {"Diabète (E11)": ["DT2"]}, '
    '"informations": {"age": 70}'
    "}"
    "}\n"
    "```"
)


def _batch_line(custom_id: str, content: str | None) -> dict:
    if content is None:
        return {"custom_id": custom_id}
    return {
        "custom_id": custom_id,
        "response": {"body": {"choices": [{"message": {"content": content}}]}},
    }


def test_load_batch_jsonl(tmp_path: Path) -> None:
    from recode.training.extract import load_batch_jsonl

    path = tmp_path / "batch_0.json"
    lines = [
        {"custom_id": "1", "foo": "bar"},
        {"custom_id": "2", "foo": "baz"},
    ]
    path.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")

    loaded = load_batch_jsonl(path)
    assert loaded == lines


def test_extract_clinical_reports_parses_good_rows(tmp_path: Path) -> None:
    from recode.training.extract import extract_clinical_reports

    path = tmp_path / "batch_0.json"
    lines = [
        _batch_line("7", _GOOD_BODY_1),
        _batch_line("8", _GOOD_BODY_2),
    ]
    path.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")

    df = extract_clinical_reports(path)
    assert len(df) == 2
    assert list(df["custom_id"]) == [7, 8]
    assert df["clinical_report"].tolist() == ["Compte-rendu 1.", "Compte-rendu 2."]
    assert df["response_diagnosis"].iloc[0] == {"Insuffisance cardiaque (I500)": ["ICC"]}
    assert df["response_structured_data"].iloc[1] == {"age": 70}


def test_extract_clinical_reports_skips_missing_response(tmp_path: Path) -> None:
    from recode.training.extract import extract_clinical_reports

    path = tmp_path / "batch_0.json"
    lines = [
        _batch_line("1", None),  # no "response" key
        {"custom_id": "2", "response": None},  # falsy response
        _batch_line("3", _GOOD_BODY_1),
    ]
    path.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")

    df = extract_clinical_reports(path)
    assert list(df["custom_id"]) == [3]


def test_extract_clinical_reports_skips_unparseable_content(tmp_path: Path) -> None:
    from recode.training.extract import extract_clinical_reports

    path = tmp_path / "batch_0.json"
    lines = [
        _batch_line("1", "no json block at all"),
        _batch_line("2", _GOOD_BODY_1),
    ]
    path.write_text("\n".join(json.dumps(line) for line in lines), encoding="utf-8")

    df = extract_clinical_reports(path)
    assert list(df["custom_id"]) == [2]
