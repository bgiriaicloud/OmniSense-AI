#!/usr/bin/env bash
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"
VENV_DIR="$SCRIPT_DIR/.venv"
CONFIG_ENV="$SCRIPT_DIR/config/.env"

source "$VENV_DIR/bin/activate"
set -a
[ -f "$CONFIG_ENV" ] && source "$CONFIG_ENV"
set +a

echo "Starting Backend..."
cd "$BACKEND_DIR"
uvicorn app.main:app --host 0.0.0.0 --port 8000 > "$SCRIPT_DIR/backend.log" 2>&1 &
BACKEND_PID=$!

echo "Starting Frontend..."
cd "$FRONTEND_DIR"
npm run dev > "$SCRIPT_DIR/frontend.log" 2>&1 &
FRONTEND_PID=$!

echo "Services started."
echo "Backend:  http://localhost:8000 (PID: $BACKEND_PID)"
echo "Frontend: http://localhost:5173 (PID: $FRONTEND_PID)"

# Keep script running to keep children alive if needed, 
# though & usually detaches enough in many environments.
# But for background tool usage, we want this script to finish 
# while leaving the processes running.
disown $BACKEND_PID
disown $FRONTEND_PID
