# Legacy v2

This directory contains the pre-refacto implementation (as of tag
`baseline/corrected`, 2026-04-15):

- `utils_v2.py` — monolithic module, kept as a regression reference.
- `generate_scenarios_v4.ipynb` — original orchestration notebook.

These files are **not imported** by the active codebase. They remain in the
repo so that:

- `scripts/generate_golden.py` can regenerate the golden CSV if needed.
- `scripts/compare_outputs.py` can diff legacy vs new outputs for investigation.

Do not modify these files unless you also regenerate
`tests/fixtures/golden_scenarios.csv` and re-run the regression suite.
