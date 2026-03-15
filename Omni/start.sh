#!/usr/bin/env bash
# VisionGuide AI — Start all services

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV_DIR="$SCRIPT_DIR/.venv"
CONFIG_ENV="$SCRIPT_DIR/config/.env"

echo "=== VisionGuide AI 2026 Startup ==="

# ── BACKEND ─────────────────────────────────────────────────────────────────
echo ""
echo "[1/3] Setting up Python virtual environment..."
if [ ! -d "$VENV_DIR" ]; then
  python3 -m venv "$VENV_DIR"
fi
source "$VENV_DIR/bin/activate"

echo "[2/3] Installing backend dependencies..."
pip install -q -r "$BACKEND_DIR/requirements.txt"

echo "[3/3] Starting FastAPI backend on http://localhost:8000 ..."
# Export env vars from config/.env
set -a
[ -f "$CONFIG_ENV" ] && source "$CONFIG_ENV"
set +a

cd "$BACKEND_DIR"
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
BACKEND_PID=$!
echo "  Backend PID: $BACKEND_PID"
cd "$SCRIPT_DIR"

# ── FRONTEND ─────────────────────────────────────────────────────────────────
echo ""
echo "[4/3] Starting Vite frontend on http://localhost:5173 ..."
cd "$FRONTEND_DIR"
npm install --silent
npm run dev &
FRONTEND_PID=$!
echo "  Frontend PID: $FRONTEND_PID"
cd "$SCRIPT_DIR"

echo ""
echo "=== All services started ==="
echo "  Backend:  http://localhost:8000"
echo "  Frontend: http://localhost:5173"
echo "  API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop."

# Wait for both
wait $BACKEND_PID $FRONTEND_PID
