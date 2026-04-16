"""`recode llm batch` command."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import typer
from loguru import logger

from recode.config import Settings
from recode.llm import BatchRequest, download_output, make_client, run_batch

app = typer.Typer(help="Run Mistral batch jobs")


@app.command("batch")
def batch(
    scenarios_csv: Path = typer.Option(..., "--scenarios", "-s"),
    output_dir: Path = typer.Option(..., "--out", "-o"),
    model: str | None = typer.Option(None, "--model", "-m"),
    batch_size: int | None = typer.Option(None, "--batch-size"),
) -> None:
    """Split scenarios into batches, submit to Mistral, download outputs."""
    settings = Settings()
    model_ = model or settings.operational.mistral_model
    size = batch_size or settings.operational.batch_size

    df = pd.read_csv(scenarios_csv, index_col=0)
    client = make_client(settings)
    n_batches = (len(df) + size - 1) // size
    output_dir.mkdir(parents=True, exist_ok=True)

    for i in range(n_batches):
        chunk = df.iloc[i * size : (i + 1) * size].reset_index(drop=True)
        requests = [
            BatchRequest(
                custom_id=str(idx),
                system_prompt=str(row["system_prompt"]),
                user_prompt=str(row["user_prompt"]),
                prefix=str(row["prefix"]),
            )
            for idx, row in chunk.iterrows()
        ]
        info = run_batch(
            client, requests, model=model_, poll_interval=settings.operational.poll_interval_seconds
        )
        if info.output_file_id:
            download_output(client, info.output_file_id, output_dir / f"batch_{i}.json")
        chunk.to_csv(output_dir / f"batch_{i}.csv")
        logger.success("Batch {}/{} done", i + 1, n_batches)
