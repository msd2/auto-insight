# api + worker + migrate image (one image, three run_commands — see
# infra/app.tf). Build context is the REPO ROOT (source_dir "/" in the app
# spec), which is why COPY paths are api/-prefixed.
#
# Lives under infra/ rather than api/ deliberately: it is deploy plumbing
# owned by WP 0.4, and App Platform's dockerfile_path is repo-root-relative
# so the location costs nothing.
#
# TODO(wp0.4-execution): never built against a real daemon in the authoring
# environment (no Docker available) — expect first-build nits.

FROM python:3.12-slim

# uv (same tool as local dev / CI) — copy the static binary, no curl dance.
COPY --from=ghcr.io/astral-sh/uv:0.7 /uv /uvx /usr/local/bin/

WORKDIR /app

# Dependency layer first for build caching.
COPY api/pyproject.toml api/uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Application code (includes alembic.ini + alembic/ so the migrate job works).
COPY api/ ./
RUN uv sync --frozen --no-dev

# Make the venv the default python environment for whatever run_command the
# app spec supplies (uvicorn / procrastinate / alembic).
ENV PATH="/app/.venv/bin:$PATH"

EXPOSE 8000

# Default = api; worker and migrate override via run_command in app.tf.
CMD ["uvicorn", "autoinsight.main:app", "--host", "0.0.0.0", "--port", "8000"]
