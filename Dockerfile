# syntax=docker/dockerfile:1.7

# -------- Stage 1 : build ---------------------------------------------------
# uv's official image ships with uv pre-installed on top of Python 3.12-slim.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

WORKDIR /app

# Dependencies only first — maximizes cache hits on source-only edits.
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Install the project itself on top of the cached deps layer.
COPY src/ ./src/
COPY README.md ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev


# -------- Stage 2 : runtime -------------------------------------------------
# Smaller base (no uv/cargo). Copies only the resolved .venv + runtime assets.
FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

# Runtime assets shipped inside the image:
#   - Resolved virtual environment (includes recode itself via editable install).
#   - Application source.
#   - Templates (read at runtime by build_system_prompt).
#   - Processed referentials (Parquets committed to the repo).
#   - Constant YAML files (cancer codes, DRG / ICD / procedure categories).
#   - Operational config defaults.
#
# Intentionally NOT shipped: referentials/raw/ (57 MB), tests/, arXiv/.
# Regenerate Parquets locally via `scripts/prepare_referentials.py` if needed.
COPY --from=builder /app/.venv /app/.venv
COPY src/ ./src/
COPY templates/ ./templates/
COPY referentials/processed/ ./referentials/processed/
COPY referentials/constants/ ./referentials/constants/
COPY config/ ./config/

# data/ and runs/ are expected to be mounted at runtime (volumes).
# Pre-create so the paths resolve even when nothing is mounted yet.
RUN mkdir -p /app/data /app/runs

ENTRYPOINT ["recode"]
CMD ["--help"]
