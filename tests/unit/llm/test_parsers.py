"""Tests for LLM parsers."""

from __future__ import annotations

RESPONSE_GOOD = """Some text before
```json
{
  "CR": "Compte-rendu avec **gras**.\\n\\nLigne 2.",
  "formulations": {
    "diagnostics": {"Insuffisance cardiaque (I500)": ["ICC"]},
    "informations": {"age": 65}
  }
}
```
Trailing text
"""


def test_extract_json_block() -> None:
    from recode.llm.parsers import extract_json_block

    block = extract_json_block(RESPONSE_GOOD)
    assert block is not None
    assert '"CR"' in block


def test_extract_json_block_no_match() -> None:
    from recode.llm.parsers import extract_json_block

    assert extract_json_block("no code block here") is None


def test_clean_markdown_strips_bold() -> None:
    from recode.llm.parsers import clean_markdown

    assert clean_markdown("**bold**") == "bold"


def test_clean_markdown_strips_headers() -> None:
    from recode.llm.parsers import clean_markdown

    assert "##" not in clean_markdown("## Title\ncontent")


def test_strip_comments() -> None:
    from recode.llm.parsers import strip_comments

    assert "comment" not in strip_comments('{"x": 1} // comment')
    assert "block" not in strip_comments('{"x": 1} /* block */')


def test_parse_generation_happy_path() -> None:
    from recode.llm.parsers import parse_generation

    out = parse_generation(RESPONSE_GOOD)
    assert out is not None
    assert "Ligne 2" in out.clinical_report
    assert "Insuffisance cardiaque (I500)" in out.diagnoses


def test_parse_generation_malformed_returns_none() -> None:
    from recode.llm.parsers import parse_generation

    assert parse_generation("not a valid response") is None
