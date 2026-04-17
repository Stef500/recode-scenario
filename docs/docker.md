# Docker

`recode` ships with a multi-stage Dockerfile and a docker-compose setup so
the whole pipeline can run inside a container with host volumes for I/O.

## What the image contains

**Shipped inside the image** (self-sufficient for scenario generation):

- Resolved virtual environment (`uv sync --frozen --no-dev`, Python 3.12).
- `src/recode/` — application source and CLI.
- `templates/` — prompt templates read at runtime.
- `referentials/processed/` — canonical Parquets (`cim10_hierarchy.parquet`,
  `cim10_notes.parquet`, etc.).
- `referentials/constants/` — YAML constants (cancer codes, DRG / ICD categories).
- `config/default.yaml` — operational parameters.

**Intentionally excluded**:

- `referentials/raw/` (57 MB of source CSVs/XLSX). Only needed to regenerate
  Parquets via `scripts/prepare_referentials.py`, a dev/ops task — run it
  locally on a clone, then rebuild the image. If you need a container capable
  of rebuilding referentials, we can publish a `:full` tag variant.
- `tests/`, `arXiv/`, `.worktrees/`.

Final image size: ~650-800 MB (pandas + pyarrow + numpy + mistralai are
incompressible).

## Build

```bash
docker build -t recode:latest .
```

Or via compose:

```bash
docker compose build
```

## Configuration

Set the Mistral API key (and any other `RECODE_*` overrides) in a local
`.env` at the repo root:

```bash
cp .env.example .env
# then edit .env and fill RECODE_MISTRAL_API_KEY
```

The `docker-compose.yml` loads it automatically. For plain `docker run`,
pass it explicitly:

```bash
docker run --rm --env-file .env recode:latest --help
```

## Running the CLI

The image's `ENTRYPOINT` is `recode`, so you pass subcommands directly.

### Generate scenarios

```bash
docker compose run --rm recode scenarios generate \
    --profile-file data/profiles.parquet \
    --n 1000 --seed 42 \
    --out runs/docker/scenarios.csv
```

`./data/` and `./runs/` on the host are mounted into `/app/data` and
`/app/runs` inside the container.

### Submit a Mistral batch

```bash
docker compose run --rm recode llm batch \
    --scenarios-csv runs/docker/scenarios.csv \
    --out-dir runs/docker/batches
```

### Prepare training file

```bash
docker compose run --rm recode training prepare \
    --job-dir runs/docker/batches \
    --out runs/docker/training.csv
```

## Plain `docker run` examples

Without compose, mount volumes explicitly:

```bash
docker run --rm \
    --env-file .env \
    -v "$(pwd)/data:/app/data" \
    -v "$(pwd)/runs:/app/runs" \
    recode:latest scenarios generate \
    --profile-file data/profiles.parquet --n 10
```

## Regenerating referentials (optional)

If you need to rebuild `referentials/processed/*.parquet` from raw sources,
do it outside the container:

```bash
uv run python scripts/prepare_referentials.py
# then rebuild the image to pick up the fresh Parquets
docker compose build
```

## Troubleshooting

- **`ModuleNotFoundError: recode`** — the image expects `/app/.venv` on
  `PATH`. Verify with `docker run --rm recode:latest python -c "import recode"`.
- **Parquet not found** — check `referentials/processed/` was actually copied
  (`docker run --rm recode:latest ls referentials/processed`). If you edited
  `.dockerignore`, it may have excluded them.
- **Missing `MISTRAL_API_KEY`** — pydantic-settings reads from env; pass
  `--env-file .env` or `-e RECODE_MISTRAL_API_KEY=...` on `docker run`.
