"""Tests for the recode CLI skeleton."""

from __future__ import annotations

from typer.testing import CliRunner


def test_cli_help_works() -> None:
    from recode.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "scenarios" in result.stdout
    assert "llm" in result.stdout
    assert "training" in result.stdout


def test_cli_version_flag() -> None:
    from recode.cli import app

    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0
