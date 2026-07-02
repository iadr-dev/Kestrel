#!/bin/bash
# Production launcher for a SINGLE-HOST bare-metal run (no Docker).
#
# Use this when you're running directly on a rented VM and don't want containers.
# For a scaled/containerised deploy use docker-compose.prod.yml instead (separate
# writer + read-replica services). This script runs ONE backend process that is both
# the writer AND the API — fine for a small/single-box deployment.
#
# Differences from dev-wsl.sh (why you can't just flip ENVIRONMENT and reuse that):
#   - NO --reload (production server mode)
#   - requires Redis (the app raises on startup in production without it)
#   - serves the frontend's prebuilt standalone output, not `next dev`
#
# Prerequisites:
#   - kestrel-backend/.env.production filled in (copy from .env.production.example)
#   - Redis configured (UPSTASH_REDIS_REST_URL / _TOKEN)
#   - frontend built once:  (cd kestrel-web && pnpm install && pnpm build)
#
# Usage:  ./scripts/prod-start.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/kestrel-backend"
FRONTEND_DIR="$PROJECT_DIR/kestrel-web"

ENV_FILE="$BACKEND_DIR/.env.production"
WORKERS="${WEB_CONCURRENCY:-4}"

echo "🦅 Kestrel — PRODUCTION (single-host)"
echo "======================================"

# --- Preflight --------------------------------------------------------------
[ -f "$ENV_FILE" ] || { echo "❌ $ENV_FILE missing. Copy from .env.production.example and fill it in."; exit 1; }

# Required prod vars (the app would raise later anyway; fail fast with a clear message).
# shellcheck disable=SC2046
set -a; . "$ENV_FILE"; set +a
[ -n "${UPSTASH_REDIS_REST_URL:-}" ] && [ -n "${UPSTASH_REDIS_REST_TOKEN:-}" ] \
  || { echo "❌ Redis is required in production (UPSTASH_REDIS_REST_URL / _TOKEN in $ENV_FILE)."; exit 1; }
[ -n "${JWT_SECRET_KEY:-}" ] || { echo "❌ JWT_SECRET_KEY is required (see .env.production.example)."; exit 1; }

[ -d "$BACKEND_DIR/.venv" ] || { echo "❌ Backend venv missing. Run: (cd kestrel-backend && uv sync)"; exit 1; }
[ -d "$FRONTEND_DIR/.next/standalone" ] || { echo "❌ Frontend not built. Run: (cd kestrel-web && pnpm install && pnpm build)"; exit 1; }

# --- Backend: ONE process that writes + schedules + serves the API ----------
# Single-host = single writer, so RUN_SCHEDULER=true and DUCKDB_READ_ONLY=false
# (the .env defaults), and WEB_CONCURRENCY=1 so only one process owns the
# read-write DuckDB connection. (To scale, move to docker-compose.prod.yml.)
echo "🔧 Starting backend (production, 1 writer process) on :8000 ..."
cd "$BACKEND_DIR"
ENVIRONMENT=production RUN_SCHEDULER=true DUCKDB_READ_ONLY=false \
  .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 &
BACKEND_PID=$!

# --- Frontend: prebuilt standalone server -----------------------------------
echo "🎨 Starting frontend (standalone) on :3000 ..."
cd "$FRONTEND_DIR"
NODE_ENV=production NEXT_PUBLIC_API_URL="${NEXT_PUBLIC_API_URL:-http://localhost:8000/api/v1}" \
  node .next/standalone/server.js &
FRONTEND_PID=$!

cd "$PROJECT_DIR"
echo "======================================"
echo "✓ Backend:  http://localhost:8000  (writer + scheduler, $WORKERS-worker note: forced to 1 here)"
echo "✓ Frontend: http://localhost:3000"
echo "Press Ctrl+C to stop."
echo "======================================"

cleanup() { echo; echo "Shutting down..."; kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true; wait 2>/dev/null || true; echo "Done."; }
trap cleanup EXIT INT TERM
wait
