"""End-to-end smoke test: scenarios CLI produces a valid CSV on fixtures."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import pytest
from typer.testing import CliRunner

pytestmark = pytest.mark.slow


def test_scenarios_generate_e2e(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    ref_absolute = Path("tests/fixtures/referentials").resolve()
    monkeypatch.setenv("RECODE_MISTRAL_API_KEY", "sk-test-unused")
    monkeypatch.setenv("RECODE_REFERENTIALS_PROCESSED", str(ref_absolute))
    monkeypatch.setenv("RECODE_REFERENTIALS_CONSTANTS", str(ref_absolute / "constants"))

    from recode.cli import app

    runner = CliRunner()

    profiles = pd.read_parquet("tests/fixtures/profiles.parquet")
    profile_file = tmp_path / "profiles.parquet"
    profiles.to_parquet(profile_file)

    out_csv = tmp_path / "scenarios.csv"
    # Use a fake templates dir with the 10 expected template names so
    # build_system_prompt succeeds.
    tmpl_dir = tmp_path / "templates"
    tmpl_dir.mkdir()
    for name in (
        "medical_inpatient.txt",
        "medical_outpatient.txt",
        "medical_inpatient_onco.txt",
        "medical_outpatient_onco.txt",
        "surgery_inpatient.txt",
        "surgery_outpatient.txt",
        "surgery_inpatient_onco.txt",
        "surgery_outpatient_onco.txt",
        "delivery_inpatient_hospit.txt",
        "delivery_inpatient_urg.txt",
        "delivery_inpatient_csection_hospit.txt",
        "delivery_inpatient_csection_urg.txt",
    ):
        (tmpl_dir / name).write_text("TEMPLATE")

    # build_system_prompt reads from Path("templates") by default — run from tmp_path
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(
        app,
        [
            "scenarios",
            "generate",
            "--profile-file",
            str(profile_file),
            "--n",
            "5",
            "--seed",
            "42",
            "--out",
            str(out_csv),
        ],
    )
    assert result.exit_code == 0, result.output
    assert out_csv.exists()

    df = pd.read_csv(out_csv)
    assert len(df) == 5
    assert "user_prompt" in df.columns
    assert "system_prompt" in df.columns
    assert "prefix" in df.columns
