"""Tests for batch request building."""

from __future__ import annotations

import json


def test_batch_request_model() -> None:
    from recode.llm.batch import BatchRequest

    r = BatchRequest(custom_id="0", system_prompt="sys", user_prompt="user", prefix="pref")
    assert r.max_tokens == 128_000


def test_build_jsonl_buffer_structure() -> None:
    from recode.llm.batch import BatchRequest, build_jsonl_buffer

    reqs = [
        BatchRequest(custom_id="0", system_prompt="s0", user_prompt="u0", prefix="p0"),
        BatchRequest(custom_id="1", system_prompt="s1", user_prompt="u1", prefix="p1"),
    ]
    buf = build_jsonl_buffer(reqs)
    lines = buf.getvalue().decode().strip().split("\n")
    assert len(lines) == 2
    r0 = json.loads(lines[0])
    assert r0["custom_id"] == "0"
    assert r0["body"]["messages"][0]["role"] == "system"
    assert r0["body"]["messages"][-1]["prefix"] is True
