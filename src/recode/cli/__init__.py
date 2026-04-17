"""recode — unified CLI for the scenario-generation pipeline."""

from __future__ import annotations

from importlib.metadata import version as pkg_version
from pathlib import Path

import typer

from recode.cli.llm_cmd import app as llm_app
from recode.cli.scenarios_cmd import app as scenarios_app
from recode.cli.training_cmd import app as training_app
from recode.logging import setup_logging

app = typer.Typer(
    name="recode",
    no_args_is_help=True,
    help="Generate clinical scenarios for LLM training",
)

app.add_typer(scenarios_app, name="scenarios")
app.add_typer(llm_app, name="llm")
app.add_typer(training_app, name="training")


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"recode {pkg_version('recode')}")
        raise typer.Exit


@app.callback()
def main(
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Enable DEBUG logs"),
    log_file: Path | None = typer.Option(None, "--log-file"),
    version: bool | None = typer.Option(
        None,
        "--version",
        callback=_version_callback,
        is_eager=True,
    ),
) -> None:
    """Configure logging for the invocation."""
    setup_logging(verbose=verbose, log_file=log_file)
