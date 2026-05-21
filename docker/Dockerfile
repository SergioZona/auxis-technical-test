# ── Build stage ───────────────────────────────────────────────────────────────
FROM python:3.14-slim AS builder

WORKDIR /app

# Install UV
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Copy dependency files first (layer cache)
COPY pyproject.toml uv.lock README.md ./

# Install build tools (needed to compile Rust/C dependencies on Python 3.14)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    cargo \
    rustc \
    && rm -rf /var/lib/apt/lists/*

# Install only runtime dependencies (no dev group)
RUN uv sync --frozen --no-group dev --no-editable

# Copy source code
COPY src/ ./src/
COPY ui/ ./ui/

# ── Runtime stage ─────────────────────────────────────────────────────────────
FROM python:3.14-slim AS runtime

WORKDIR /app

# Non-root user for security
RUN useradd --create-home --shell /bin/bash appuser

# Copy installed packages and app from builder (read-only for security)
COPY --from=builder /app/.venv /app/.venv
COPY --from=builder /app/src /app/src
COPY --from=builder /app/ui /app/ui

# Create data directory and ensure ownership
RUN mkdir -p /app/data && chown -R appuser:appuser /app/data

# Activate venv
ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app/src"
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

USER appuser

# Pre-download the FastEmbed model to bake it into the Docker image
# This avoids unauthenticated HF Hub warnings and slow startup times at runtime.
RUN python -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"

EXPOSE 8000

# Secrets (DATABASE_PASSWORD, SECRET_KEY) must be injected at runtime:
#   docker run --env-file src/env/PROD.env \
#     -e DATABASE_PASSWORD=<secret> \
#     -e SECRET_KEY=<secret> \
#     hexagonal-app:1.0.0

HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')"

CMD ["uvicorn", "app.infrastructure.main:app", "--host", "0.0.0.0", "--port", "8000"]
