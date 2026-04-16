# recode-scenario

Generate synthetic clinical scenarios from French PMSI data for LLM-based
clinical report generation.

Each scenario combines:

- a clinical scenario — medico-economic data sampled from the French national
  hospitalisation claims database (*Base nationale PMSI*)
- a document template
- an instruction for the model

A Mistral batch pipeline turns these prompts into complete synthetic discharge
reports, which in turn feed a fine-tuning dataset.

## Install

```bash
git clone https://github.com/24p11/recode-scenario.git
cd recode-scenario
uv sync
cp .env.example .env           # then edit MISTRAL_API_KEY
```

## Quickstart

```bash
# 1. (one-shot) prepare referentials from raw sources
uv run python scripts/prepare_referentials.py

# 2. generate 1000 scenarios
uv run recode scenarios generate \
    --profile-file data/profiles.parquet \
    --n 1000 --seed 42 \
    --out runs/2026-04-15/scenarios.csv

# 3. run Mistral batch
uv run recode llm batch \
    --scenarios runs/2026-04-15/scenarios.csv \
    --out runs/2026-04-15/batches/

# 4. prepare training data
uv run recode training prepare \
    --job-dir runs/2026-04-15/batches/ \
    --out runs/2026-04-15/training.csv
```

## Configuration

Secrets live in `.env` (gitignored) with the `RECODE_` prefix. Operational
parameters live in `config/default.yaml` (versioned, reviewable in PR).

## Architecture

See `docs/architecture.md` and `docs/internal/specs/2026-04-15-refacto-design.md`.

- `src/recode/scenarios/` — deterministic scenario generation (pure)
- `src/recode/llm/` — Mistral batch orchestration
- `src/recode/training/` — fine-tuning data preparation
- `src/recode/referentials/` — typed access to Parquet/YAML referentials
- `src/recode/models/` — Pydantic domain models

## Development

```bash
uv run pytest                  # run tests
uv run ruff check              # lint
uv run ruff format             # auto-format
uv run mypy src/recode         # type check
uv run pre-commit install      # install git hooks
```

## Tests

- Unit: `tests/unit/`
- Integration: `tests/integration/` (mock Mistral)
- Regression: `tests/regression/test_golden_scenarios.py` — byte-regression on
  10 synthetic profiles against `tests/fixtures/golden_scenarios.csv`.

```bash
uv run pytest -m regression    # regression tests only
uv run pytest -m "not slow"    # skip slow tests
```

---

## Domain reference

### Variables dictionary

- `drg_code`
- `drg_description`
- `drg_parent_code`
- `drg_parent_code_description`
- `icd_code`
- `icd_code_description`
- `icd_parent_code`
- `icd_parent_code_description`
- `icd_primary_code` — principal diagnosis
- `icd_primary_code_definition` — principal diagnosis definition
- `icd_secondary` — related diagnosis
- `cage` — age classes `[0-1[`, `[1-5[`, `[5-10[`, `[10-15[`, `[15-18[`, `[18-30[`, `[30-40[`, `[40-50[`, `[50-60[`, `[60-70[`, `[70-80[`, `[80-[`
- `cage2` — age classes `[0-1[`, `[1-5[`, `[5-10[`, `[10-15[`, `[15-18[`, `[18-50[`, `[50-[`
- `sexe` — 1 (M) / 2 (F)
- `admission_mode`
- `discharge_disposition`
- `admission_type`

### Table `classification_profile`

- `drg_parent_code`
- `icd_primary_code`
- `icd_primary_parent_code`
- `case_management_type`
- `cage`
- `cage2`
- `sexe`

### Table `secondary_diagnosis`

- `drg_parent_code`
- `icd_primary_parent_code`
- `cage2`
- `sexe`

### Cancer — synthetic treatment recommendation table

- `primary_site`
- `histological_type`
- `Stage`
- `TNM_score`
  - `T` — tumour (TNM)
  - `N` — nodes (TNM)
  - `M` — metastasis (TNM)
- `biomarkers`
- `treatment_recommandation`
- `chemotherapy_regimen`

Use the `col_names` options of the project's load functions to align the column
names of source files with this dictionary.

### PMSI / English glossary

| French PMSI term | English equivalent | Notes / Context |
|---|---|---|
| `Résumé PMSI` | Patient-level coded abstract / Discharge abstract | Structured data for each hospitalisation — ICD diagnoses, procedures, demographics. |
| `Code diagnostic principal (DP)` | Primary diagnosis (`ICD code`) | Main reason for hospitalisation. |
| `Codes diagnostics associés (DAS)` | Secondary diagnoses (`ICD codes`) | Comorbidities or complications during the stay. |
| `Actes` | Procedures / `ICD procedure codes` | Coded interventions performed during hospitalisation. |
| `GHM (Groupe Homogène de Malades)` | `DRG (Diagnosis-Related Group)` | Classification for resource use / reimbursement purposes. |
| `CMD (Catégorie Majeure de Diagnostic)` | `MDC (Major Diagnostic Category)` | Top-level DRG grouping by body system or disease category. |
| `Données de séjour` vs `Données de patient` | `Case-level data` vs `Patient-level data` | Individual hospitalisation record used for DRG assignment or analysis. |
| `Mode entrée` | `Admission mode` | How the patient was admitted to the hospital. |
| `Mode de sortie` | `Discharge disposition` | How the patient was discharged, including deceased. |
| `Mode d'hospitalisation` | `Type of admission` | Inpatient vs outpatient admission. |
| Variables normalisées | Normalized variables / Standardised coded fields | Coded fields derived from the patient record (ICD, procedures, demographics). |

### Hospitalisation management type

A clinical abstraction derived from the combination of the principal diagnosis
(`DP`) and the linked diagnosis (`DR`). This combination determines the DRG
assignment and reflects the patient's management mode during the hospital stay.

Management types follow the ATIH coding rules — see the recap table
[Guide Situations cliniques](https://docs.google.com/spreadsheets/d/1XRVeSn3VFSaM8o7bJYz7gGcyAFWN9Gn7Ko4x-tAOYjs/edit?usp=sharing).

**Management types for chronic diseases**

| Cancer | Diabetes | Other chronic diseases |
|---|---|---|
| Hospital admission with initial diagnosis of the cancer | Hospital admission with initial diagnosis of diabetes | Hospital admission with initial diagnosis of the disease |
| Hospital admission for cancer workup | Hospital admission for diabetes initial workup | Hospital admission for diagnostic workup |
| Hospital admission for initiation of treatment | Hospital admission for initiation of treatment of the diabetes | Hospital admission for initiation of treatment |
| Hospital admission for relapse or recurrence of the cancer | Hospital admission for change in therapeutic strategy | Hospital admission for acute exacerbation of the disease |
| Hospital admission for surgery | | |
