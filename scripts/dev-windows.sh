#!/bin/bash
# Start backend (FastAPI :8000) + frontend (Next.js :3000) for development (Windows / Git Bash).
# For WSL/Linux use scripts/dev-wsl.sh instead.
#
# Env-marker reinstall:
#   node_modules and .venv carry win32 vs linux native binaries that are NOT
#   interchangeable. Each install stamps a marker (.dev-env) with the env that
#   built it ("windows"). On start this script reinstalls ONLY when the existing
#   artifacts were built by a different env (i.e. you last ran dev-wsl.sh), or
#   are missing. Same env twice in a row = no reinstall.
#
# Usage:
#   ./scripts/dev-windows.sh           # reinstall only if env changed / missing, then start both
#   ./scripts/dev-windows.sh --clean   # force wipe .venv + node_modules + .next, reinstall, start

set -uo pipefail

ENV_TAG="windows"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="$PROJECT_DIR/kestrel-backend"
FRONTEND_DIR="$PROJECT_DIR/kestrel-web"
FE_MARKER="$FRONTEND_DIR/node_modules/.dev-env"
BE_MARKER="$BACKEND_DIR/.venv/.dev-env"

cd "$PROJECT_DIR"

FORCE_CLEAN=0
[[ "${1:-}" == "--clean" || "${1:-}" == "-c" ]] && FORCE_CLEAN=1

echo "🦅 Kestrel (Windows) — Starting development servers..."
echo "================================================"

# --- Dependency checks -------------------------------------------------------
if ! command -v uv &> /dev/null; then
  echo "❌ uv not found. Install: https://astral.sh/uv"
  exit 1
fi
if ! command -v node &> /dev/null; then
  echo "❌ node not found."
  exit 1
fi
# Prefer pnpm; fall back to npx if unavailable.
PM="pnpm"
command -v pnpm &> /dev/null || PM="npx-next"

# --- Decide what needs (re)installing ----------------------------------------
fe_reason=""; be_reason=""
if [[ $FORCE_CLEAN -eq 1 ]]; then
  fe_reason="--clean"; be_reason="--clean"
else
  if [ ! -d "$FRONTEND_DIR/node_modules" ]; then fe_reason="missing"
  elif [ "$(cat "$FE_MARKER" 2>/dev/null)" != "$ENV_TAG" ]; then fe_reason="env changed → $ENV_TAG"; fi
  if [ ! -d "$BACKEND_DIR/.venv" ]; then be_reason="missing"
  elif [ "$(cat "$BE_MARKER" 2>/dev/null)" != "$ENV_TAG" ]; then be_reason="env changed → $ENV_TAG"; fi
fi

# --- Backend reinstall -------------------------------------------------------
if [ -n "$be_reason" ]; then
  echo "📦 Backend deps ($be_reason) — wiping .venv + reinstalling (uv sync)..."
  rm -rf "$BACKEND_DIR/.venv"
  ( cd "$BACKEND_DIR" && uv sync ) || { echo "❌ uv sync failed"; exit 1; }
  echo "$ENV_TAG" > "$BE_MARKER"
else
  echo "✓ Backend deps OK (built by: $ENV_TAG) — skipping reinstall."
fi

# --- Frontend reinstall ------------------------------------------------------
if [ -n "$fe_reason" ]; then
  echo "📦 Frontend deps ($fe_reason) — wiping node_modules + .next + reinstalling..."
  rm -rf "$FRONTEND_DIR/node_modules" "$FRONTEND_DIR/.next"
  if [ "$PM" = "pnpm" ]; then
    ( cd "$FRONTEND_DIR" && pnpm install ) || { echo "❌ pnpm install failed"; exit 1; }
  else
    ( cd "$FRONTEND_DIR" && npm install ) || { echo "❌ npm install failed"; exit 1; }
  fi
  echo "$ENV_TAG" > "$FE_MARKER"
else
  echo "✓ Frontend deps OK (built by: $ENV_TAG) — skipping reinstall."
fi

# --- Backend .env ------------------------------------------------------------
if [ ! -f "$BACKEND_DIR/.env" ] && [ -f "$BACKEND_DIR/.env.example" ]; then
  echo "⚠️  No .env found. Copying from .env.example..."
  cp "$BACKEND_DIR/.env.example" "$BACKEND_DIR/.env"
  echo "   Edit kestrel-backend/.env to add your API keys."
fi

# --- Free stale ports --------------------------------------------------------
if command -v fuser &> /dev/null; then
  for port in 8000 3000; do fuser -k "$port/tcp" 2>/dev/null || true; done
elif command -v netstat &> /dev/null; then
  for port in 8000 3000; do
    pid=$(netstat -ano 2>/dev/null | grep ":${port}.*LISTENING" | awk '{print $NF}' | head -1)
    [ -n "$pid" ] && taskkill //PID "$pid" //F 2>/dev/null || true
  done
fi
sleep 1

# --- Start backend (logged, so a crash is visible) ---------------------------
BACKEND_LOG="${TEMP:-/tmp}/kestrel-backend.log"
echo ""
echo "🔧 Starting backend (FastAPI) on :8000 ...  (log: $BACKEND_LOG)"
cd "$BACKEND_DIR"
UVICORN_ARGS=(app.main:app --reload --port 8000 --reload-delay 2)
if [ -f ".venv/Scripts/uvicorn.exe" ]; then
  .venv/Scripts/uvicorn "${UVICORN_ARGS[@]}" > >(tee "$BACKEND_LOG") 2>&1 &
elif [ -f ".venv/bin/uvicorn" ]; then
  .venv/bin/uvicorn "${UVICORN_ARGS[@]}" > >(tee "$BACKEND_LOG") 2>&1 &
else
  uv run uvicorn "${UVICORN_ARGS[@]}" > >(tee "$BACKEND_LOG") 2>&1 &
fi
BACKEND_PID=$!

# --- Start frontend ----------------------------------------------------------
echo "🎨 Starting frontend (Next.js) on :3000 ..."
cd "$FRONTEND_DIR"
if [ "$PM" = "pnpm" ]; then
  pnpm dev --port 3000 &
else
  npx next dev --port 3000 &
fi
FRONTEND_PID=$!

cd "$PROJECT_DIR"

# --- Verify backend actually listens (else /api proxy → ECONNREFUSED) --------
echo ""
echo "⏳ Waiting for backend on :8000 (first boot runs scrape jobs; can take 1–2 min) ..."
backend_up=0
backend_dead=0
for _ in $(seq 1 120); do
  if ! kill -0 "$BACKEND_PID" 2>/dev/null; then backend_dead=1; break; fi
  curl -s -o /dev/null --connect-timeout 1 "http://127.0.0.1:8000/api/v1/health" 2>/dev/null && { backend_up=1; break; }
  sleep 1
done

echo ""
echo "================================================"
if [ "$backend_up" -eq 1 ]; then
  echo "✓ Backend:  http://localhost:8000  (healthy)"
elif [ "$backend_dead" -eq 1 ]; then
  echo "❌ Backend process EXITED — it crashed on startup. Last log lines:"
  echo "------------------------------------------------"
  tail -n 25 "$BACKEND_LOG" 2>/dev/null | sed 's/^/   /'
  echo "------------------------------------------------"
  echo "   Full log: $BACKEND_LOG"
else
  echo "⏳ Backend still starting (process alive, slow boot job). It should answer shortly."
  echo "   Watch:  tail -f $BACKEND_LOG"
fi
echo "✓ Frontend: http://localhost:3000"
echo "✓ API docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop both servers."
echo "================================================"

# --- Cleanup on exit ---------------------------------------------------------
cleanup() {
  echo ""
  echo "Shutting down..."
  kill "$BACKEND_PID" 2>/dev/null
  kill "$FRONTEND_PID" 2>/dev/null
  wait 2>/dev/null
  echo "Done."
}
trap cleanup EXIT INT TERM
wait
