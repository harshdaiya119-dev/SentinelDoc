#!/usr/bin/env bash
# ==============================================================================
# SentinelDoc — Single-Command Full-Stack Runner
# Problem Statement 3 (Cybersecurity Track) — IEEE SRM AP Hackathon
# ==============================================================================
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

echo "======================================================================"
echo "      SentinelDoc — Personal Data Leak Detector & Redactor"
echo "======================================================================"

# 1. Export PATH for Node.js and npm
export PATH="$HOME/.local/bin:$PATH"

if ! command -v node >/dev/null 2>&1 || ! command -v npm >/dev/null 2>&1; then
  echo "[ERROR] Node.js or npm not found in PATH (~/.local/bin)."
  echo "Please verify Node LTS is installed."
  exit 1
fi

echo "[1/4] Node.js $(node -v) and npm $(npm -v) detected."

# 2. Activate Python Virtual Environment
if [ -d "$ROOT_DIR/.venv" ]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.venv/bin/activate"
  echo "[2/4] Python virtual environment activated ($(python3 --version))."
else
  echo "[ERROR] Virtual environment (.venv) not found at $ROOT_DIR/.venv."
  exit 1
fi

# 3. Ensure frontend dependencies are ready
if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "[3/4] Installing frontend dependencies..."
  (cd "$ROOT_DIR/frontend" && npm install)
else
  echo "[3/4] Frontend dependencies validated."
fi

# Process IDs
BACKEND_PID=""
FRONTEND_PID=""

cleanup() {
  echo ""
  echo ">> Shutting down SentinelDoc services..."
  if [ -n "$FRONTEND_PID" ] && kill -0 "$FRONTEND_PID" 2>/dev/null; then
    echo "   Stopping Vite frontend (PID $FRONTEND_PID)..."
    kill -TERM "$FRONTEND_PID" 2>/dev/null || true
  fi
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo "   Stopping FastAPI backend (PID $BACKEND_PID)..."
    kill -TERM "$BACKEND_PID" 2>/dev/null || true
  fi
  wait 2>/dev/null || true
  echo ">> All SentinelDoc services stopped cleanly."
}

trap cleanup INT TERM EXIT

# 4. Launch FastAPI backend on port 8000
echo "[4/4] Launching FastAPI backend on http://0.0.0.0:8000 ..."
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!

# Wait for backend health check
echo "      Waiting for FastAPI backend to report healthy..."
HEALTH_MAX_TRIES=30
HEALTH_COUNT=0
while [ $HEALTH_COUNT -lt $HEALTH_MAX_TRIES ]; do
  if curl -s "http://127.0.0.1:8000/health" | grep -q "healthy"; then
    echo "      FastAPI backend is LIVE and healthy on port 8000!"
    break
  fi
  sleep 1
  HEALTH_COUNT=$((HEALTH_COUNT + 1))
done

if [ $HEALTH_COUNT -eq $HEALTH_MAX_TRIES ]; then
  echo "[ERROR] FastAPI backend failed to become healthy within 30 seconds."
  exit 1
fi

# Launch Vite frontend on port 5173
echo "      Launching React + Vite frontend on http://0.0.0.0:5173 ..."
(cd "$ROOT_DIR/frontend" && npm run dev -- --host 0.0.0.0 --port 5173) &
FRONTEND_PID=$!

echo ""
echo "======================================================================"
echo "   SentinelDoc Security Console is running!"
echo "   - Frontend UI:    http://localhost:5173"
echo "   - Backend API:    http://localhost:8000"
echo "   - API Docs:       http://localhost:8000/docs"
echo "======================================================================"
echo "   Press Ctrl+C to terminate all services."
echo ""

# Wait on background processes
wait "$BACKEND_PID" "$FRONTEND_PID"
