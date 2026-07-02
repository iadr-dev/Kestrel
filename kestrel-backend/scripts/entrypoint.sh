#!/bin/bash
# Container entrypoint. Behaviour is env-driven so the SAME image runs in dev and
# prod without edits:
#
#   ENVIRONMENT=development  -> single worker, --reload, runs seed (convenience)
#   ENVIRONMENT=production   -> WEB_CONCURRENCY workers (default 4), no reload
#
# Multi-worker note: DuckDB is single-writer. In a scaled prod deployment the API
# workers should run with DUCKDB_READ_ONLY=true and RUN_SCHEDULER=false, while a
# SEPARATE container runs the writer/scheduler (RUN_SCHEDULER=true, read-write).
# See app/main.py and app/db/duckdb/engine.py.
set -e

ENVIRONMENT="${ENVIRONMENT:-development}"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

if [ "$ENVIRONMENT" = "production" ]; then
    WORKERS="${WEB_CONCURRENCY:-4}"
    echo "Starting Kestrel API (production, ${WORKERS} workers)..."
    exec uvicorn app.main:app --host "$HOST" --port "$PORT" --workers "$WORKERS"
else
    echo "Seeding figures (dev convenience)..."
    python -m scripts.seed_figures 2>/dev/null || echo "Figures seed: skipped (already seeded or error)"
    echo "Starting Kestrel API (development, reload)..."
    exec uvicorn app.main:app --host "$HOST" --port "$PORT" --reload
fi
