#!/bin/sh
# Runs DB migrations (always) and the demo seed (when SEED_ON_START=true),
# then starts the API. Waits for Postgres to accept connections first.
set -e

echo "Waiting for Postgres..."
until uv run python -m nawa_api.scripts.wait_for_db 2>/dev/null; do
  sleep 1
done
echo "Postgres is up."

echo "Running migrations..."
uv run alembic upgrade head

if [ "$SEED_ON_START" = "true" ]; then
  echo "Seeding demo data (this takes ~30s)..."
  uv run python -m nawa_api.seed
fi

echo "Starting API on :8000"
exec uv run uvicorn nawa_api.main:app --host 0.0.0.0 --port 8000
