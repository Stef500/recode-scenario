"""`recode training prepare` command."""

from __future__ import annotations

from pathlib import Path

import typer
from loguru import logger

from recode.training import prepare_training_files

app = typer.Typer(help="Prepare LLM-generated reports for fine-tuning")


@app.command("prepare")
def prepare(
    job_dir: Path = typer.Option(..., "--job-dir", "-j"),
    output: Path = typer.Option(..., "--out", "-o"),
    limit: int | None = typer.Option(None, "--limit"),
) -> None:
    """Aggregate batch outputs, parse responses, write training-ready CSV."""
    df = prepare_training_files(job_dir, n_examples=limit)
    output.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output)
    logger.success("Wrote {} training rows → {}", len(df), output)
