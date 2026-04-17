# Architecture

## Overview

`recode` is split into three subpackages with clear boundaries:

- `scenarios/` — pure, deterministic scenario generation from PMSI profiles
- `llm/` — Mistral batch API orchestration (I/O, retry, polling)
- `training/` — parse LLM outputs and assemble training targets

Shared across subpackages:

- `models/` — Pydantic v2 domain models (`Profile`, `Scenario`, `CodingRule`, …)
- `referentials/` — typed access to processed data (Parquet + YAML) with
  Pandera schema validation
- `config/` — pydantic-settings for secrets + YAML for operational params
- `cli/` — Typer entry points exposing `recode scenarios`, `recode llm`,
  `recode training`

## Data flow

```
raw referentials (Excel/CSV)
        │
        ▼
scripts/prepare_referentials.py
        │
        ▼
referentials/processed/*.parquet  +  referentials/constants/*.yaml
        │
        ▼
ReferentialRegistry (lazy, cached, Pandera-validated)
        │
        ▼
  ScenarioGenerator(profile, rng) → Scenario (pydantic)
        │
        ▼
  user_prompt + system_prompt + prefix
        │
        ▼
  Mistral batch ──► batch_i.json
        │
        ▼
  prepare_training_files ──► training.csv
```

## Reproducibility

Scenario generation is fully deterministic given a `(profile, base_seed)` pair.
The `derive_scenario_rng()` function derives a per-profile
`np.random.Generator` by combining `base_seed` with a stable hash of profile
identity. Parallel execution is safe: scenario N does not affect scenario M≠N.

The regression test `tests/regression/test_golden_scenarios.py` asserts
byte-equivalent output against `tests/fixtures/golden_scenarios.csv`, which was
generated from the corrected baseline `utils_v2.py` (tagged
`baseline/corrected`).

## ATIH coding rules

The original `define_text_managment_type` cascade has been transcribed into a
declarative ordered table `CODING_RULES` in
`src/recode/scenarios/coding_rules.py`. Each rule is a
`CodingRuleResolver(rule_id, predicate, text, template)`. Iteration order is
semantically significant: first match wins. Modify the table only after adding
a regression test for the new rule.
