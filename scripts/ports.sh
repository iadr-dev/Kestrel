#!/bin/bash
# Check (and optionally kill) processes holding the Kestrel dev ports.
#   8000 = backend (FastAPI/uvicorn), 3000 = frontend (Next.js)
#
# Usage:
#   ./scripts/ports.sh           # report what's listening on 8000 / 3000
#   ./scripts/ports.sh --kill    # kill whatever holds those ports
#   ./scripts/ports.sh -k 8000   # kill only the given port(s)
#
# Works on WSL/Linux (fuser/ss/lsof) and Windows Git Bash (netstat/taskkill).

set -uo pipefail

KILL=0
PORTS=()
for arg in "$@"; do
  case "$arg" in
    --kill|-k) KILL=1 ;;
    *[0-9]) PORTS+=("$arg") ;;
  esac
done
[ ${#PORTS[@]} -eq 0 ] && PORTS=(8000 3000)

label_for() {
  case "$1" in
    8000) echo "backend (FastAPI)" ;;
    3000) echo "frontend (Next.js)" ;;
    *)    echo "port $1" ;;
  esac
}

is_windows() {
  [[ "$OSTYPE" == "msys" || "$OSTYPE" == "cygwin" || "$(uname -s)" == *MINGW* || "$(uname -s)" == *MSYS* ]]
}

# Print listening PIDs for a port (one per line). Empty if none.
pids_on_port() {
  local port="$1"
  if is_windows; then
    netstat -ano 2>/dev/null | grep -E ":${port}[[:space:]].*LISTENING" \
      | awk '{print $NF}' | sort -u
  elif command -v fuser &> /dev/null; then
    fuser "${port}/tcp" 2>/dev/null | tr -s ' ' '\n' | grep -E '^[0-9]+$' | sort -u
  elif command -v lsof &> /dev/null; then
    lsof -ti ":${port}" -sTCP:LISTEN 2>/dev/null | sort -u
  elif command -v ss &> /dev/null; then
    ss -ltnp "sport = :${port}" 2>/dev/null | grep -oE 'pid=[0-9]+' | cut -d= -f2 | sort -u
  fi
}

kill_pid() {
  local pid="$1"
  if is_windows; then
    taskkill //PID "$pid" //F &> /dev/null
  else
    kill -9 "$pid" 2>/dev/null
  fi
}

echo "🦅 Kestrel — port check"
echo "================================================"

any_found=0
for port in "${PORTS[@]}"; do
  mapfile -t pids < <(pids_on_port "$port")
  if [ ${#pids[@]} -eq 0 ]; then
    echo "✓ $port ($(label_for "$port")): free"
    continue
  fi
  any_found=1
  echo "● $port ($(label_for "$port")): in use by PID(s): ${pids[*]}"
  if [ $KILL -eq 1 ]; then
    for pid in "${pids[@]}"; do
      if kill_pid "$pid"; then
        echo "   ✓ killed PID $pid"
      else
        echo "   ✗ failed to kill PID $pid (try sudo / elevated shell)"
      fi
    done
  fi
done

echo "================================================"
if [ $any_found -eq 0 ]; then
  echo "All target ports are free."
elif [ $KILL -eq 0 ]; then
  echo "Re-run with --kill to free the ports above."
fi
