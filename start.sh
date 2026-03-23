#!/usr/bin/env bash
set -e

ROOT="$(cd "$(dirname "$0")" && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

# ── Load nvm if npm is not in PATH ───────────────────────────────────────────
if ! command -v npm &>/dev/null; then
  export NVM_DIR="$HOME/.nvm"
  [ -s "$NVM_DIR/nvm.sh" ] && source "$NVM_DIR/nvm.sh"
fi

if ! command -v npm &>/dev/null; then
  echo "Error: npm not found. Install Node.js or make sure nvm is set up."
  exit 1
fi

echo "=== VoiceTTS Local Launcher ==="

# ── Frontend build (if not already built or forced) ─────────────────────────
if [ ! -d "$BACKEND/static" ] || [ "$1" = "--rebuild" ]; then
  echo "[1/2] Building frontend…"
  cd "$FRONTEND"
  npm install
  npm run build
  echo "      Done → backend/static/"
else
  echo "[1/2] Frontend already built. Use --rebuild to force."
fi

# ── Python virtualenv ───────────────────────────────────────────────────────
VENV="$BACKEND/.venv"
if [ ! -d "$VENV" ]; then
  echo "[2/2] Creating Python venv & installing deps…"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install --upgrade pip
  "$VENV/bin/pip" install -r "$BACKEND/requirements.txt"
else
  echo "[2/2] Python venv exists."
fi

echo ""
echo "Starting backend on http://0.0.0.0:8080 …"
echo "Open:  http://localhost:8080  (or your machine's IP for mobile)"
echo "       Ctrl+C to stop."
echo ""

cd "$BACKEND"
"$VENV/bin/uvicorn" main:app --host 0.0.0.0 --port 8080 --reload
