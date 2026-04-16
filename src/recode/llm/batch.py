"""Mistral batch-job orchestration: build payloads, upload, poll, download."""

from __future__ import annotations

import json
import time
from collections.abc import Iterable
from io import BytesIO
from pathlib import Path
from typing import TYPE_CHECKING, Any

from loguru import logger
from pydantic import BaseModel, ConfigDict, Field
from tenacity import retry, stop_after_attempt, wait_exponential

if TYPE_CHECKING:
    from mistralai.client import Mistral


class BatchRequest(BaseModel):
    """Single request inside a batch job."""

    model_config = ConfigDict(frozen=True)

    custom_id: str
    system_prompt: str
    user_prompt: str
    prefix: str
    max_tokens: int = Field(default=128_000, ge=1)


class BatchJobInfo(BaseModel):
    """Summary info for a completed batch job."""

    model_config = ConfigDict(frozen=True)

    job_id: str
    status: str
    total: int
    succeeded: int
    failed: int
    output_file_id: str | None


def build_jsonl_buffer(requests: Iterable[BatchRequest]) -> BytesIO:
    """Serialize ``requests`` to a JSONL byte buffer."""
    buf = BytesIO()
    for req in requests:
        payload = {
            "custom_id": req.custom_id,
            "body": {
                "max_tokens": req.max_tokens,
                "messages": [
                    {"role": "system", "content": req.system_prompt},
                    {"role": "user", "content": req.user_prompt},
                    {"role": "assistant", "content": req.prefix, "prefix": True},
                ],
            },
        }
        buf.write(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
        buf.write(b"\n")
    return buf


@retry(wait=wait_exponential(multiplier=2, min=4, max=60), stop=stop_after_attempt(5))
def upload_input(client: Mistral, requests: list[BatchRequest]) -> Any:
    """Upload the JSONL batch file to Mistral, with exponential retry."""
    # Import File lazily: its location depends on the installed mistralai version.
    from mistralai.models import File

    buf = build_jsonl_buffer(requests)
    return client.files.upload(
        file=File(file_name="batch.jsonl", content=buf.getvalue()), purpose="batch"
    )


def run_batch(
    client: Mistral,
    requests: list[BatchRequest],
    *,
    model: str,
    poll_interval: float = 2.0,
) -> BatchJobInfo:
    """Submit a batch, poll until completion, return summary info."""
    input_file = upload_input(client, requests)
    logger.info("Uploaded {} requests (file {})", len(requests), getattr(input_file, "id", "?"))
    job = client.batch.jobs.create(
        input_files=[input_file.id],
        model=model,
        endpoint="/v1/chat/completions",
        metadata={"job_type": "scenario_generation"},
    )
    logger.info("Batch job {} created (status={})", job.id, job.status)

    while job.status in {"QUEUED", "RUNNING"}:
        time.sleep(poll_interval)
        job = client.batch.jobs.get(job_id=job.id)
        logger.debug(
            "Job {} {}/{}",
            job.id,
            job.succeeded_requests + job.failed_requests,
            job.total_requests,
        )

    logger.success(
        "Batch {} completed (status={}, ok={}, ko={})",
        job.id,
        job.status,
        job.succeeded_requests,
        job.failed_requests,
    )
    return BatchJobInfo(
        job_id=job.id,
        status=job.status,
        total=job.total_requests,
        succeeded=job.succeeded_requests,
        failed=job.failed_requests,
        output_file_id=getattr(job, "output_file", None),
    )


def download_output(client: Mistral, file_id: str, dest: Path) -> None:
    """Download a batch output file to ``dest`` (creates parent dirs)."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    stream = client.files.download(file_id=file_id)
    with dest.open("wb") as f:
        for chunk in stream.stream:
            f.write(chunk)
    logger.success("Downloaded batch output → {}", dest)
