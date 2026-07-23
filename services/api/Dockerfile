# NAWA API — runnable with zero local Python (uv brings its own Python 3.12).
# Build context is this directory (services/api).

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

WORKDIR /app

# Install dependencies first (cached layer) from the lockfile only.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Then the source + install the project itself.
COPY . .
RUN uv sync --frozen --no-dev

# Ensure the entrypoint is executable (the +x bit may be lost on Windows hosts).
RUN chmod +x /app/docker-entrypoint.sh

# Non-root user.
RUN useradd --uid 10001 --create-home appuser && chown -R appuser:appuser /app
USER appuser

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

# entrypoint runs migrations (and optional seed) before serving.
ENTRYPOINT ["/app/docker-entrypoint.sh"]
