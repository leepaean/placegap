#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

for command in python3 node npm; do
  if ! command -v "$command" >/dev/null 2>&1; then
    echo "Missing required command: $command"
    echo "Install Python 3.11+ and Node.js 22+, then run this script again."
    exit 1
  fi
done

if [ ! -d .venv ]; then
  echo "Creating Python environment…"
  python3 -m venv .venv
fi

source .venv/bin/activate

echo "Installing/updating backend dependencies…"
python -m pip install -q -e ".[dev]"

if [ ! -d frontend/node_modules ]; then
  echo "Installing frontend dependencies…"
  (cd frontend && npm install --no-audit --no-fund)
fi

cleanup() {
  echo "\nStopping PlaceGap…"
  kill "${BACKEND_PID:-}" "${FRONTEND_PID:-}" 2>/dev/null || true
}
trap cleanup EXIT INT TERM

PLACEGAP_DB_PATH="${PLACEGAP_DB_PATH:-$ROOT/placegap.db}" \
  python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

(cd frontend && npm run dev -- --host 127.0.0.1) &
FRONTEND_PID=$!

echo
printf '%s\n' "PlaceGap is starting:" "  UI:  http://127.0.0.1:5173" "  API: http://127.0.0.1:8000/docs" "Press Ctrl+C to stop both services."

wait
