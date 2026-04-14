#!/bin/bash
set -e

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
RUN_DIR="$ROOT_DIR/.run"
VENV_DIR="$ROOT_DIR/.venv-mac"
BACKEND_LOG="$RUN_DIR/backend.log"
FRONTEND_LOG="$RUN_DIR/frontend.log"
BACKEND_PID_FILE="$RUN_DIR/backend.pid"
FRONTEND_PID_FILE="$RUN_DIR/frontend.pid"

mkdir -p "$RUN_DIR"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing required command: $1"
    echo "Install it, then run this launcher again."
    exit 1
  fi
}

require_cmd python3
require_cmd node
require_cmd npm

if ! command -v exiftool >/dev/null 2>&1; then
  echo "Warning: exiftool not found. Install with: brew install exiftool"
fi

cd "$ROOT_DIR"

if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi

# shellcheck disable=SC1091
source "$VENV_DIR/bin/activate"
python -m pip install --upgrade pip >/dev/null
python -m pip install -r "$ROOT_DIR/backend/requirements.txt" >/dev/null

if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  npm --prefix "$ROOT_DIR/frontend" install >/dev/null
fi

if lsof -iTCP:8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Backend already running on port 8000."
else
  nohup "$VENV_DIR/bin/python" -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 >"$BACKEND_LOG" 2>&1 &
  echo $! >"$BACKEND_PID_FILE"
fi

# Wait up to 20s for backend.
for _ in {1..40}; do
  if curl -sSf "http://127.0.0.1:8000/health" >/dev/null 2>&1; then
    break
  fi
  sleep 0.5
done

if lsof -iTCP:5173 -sTCP:LISTEN -t >/dev/null 2>&1; then
  echo "Frontend already running on port 5173."
else
  nohup npm --prefix "$ROOT_DIR/frontend" run dev -- --host 127.0.0.1 --port 5173 >"$FRONTEND_LOG" 2>&1 &
  echo $! >"$FRONTEND_PID_FILE"
fi

open "http://127.0.0.1:5173"

echo "TrackTECH Meta Updater started."
echo "Frontend: http://127.0.0.1:5173"
echo "Backend:  http://127.0.0.1:8000/health"
echo "Logs:"
echo "  $BACKEND_LOG"
echo "  $FRONTEND_LOG"
