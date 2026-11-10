#!/bin/bash
set -e

echo "=================================================="
echo " Starting Agentic QE Backend (Azure App Service / Kudu)"
echo " Timestamp: $(date -u)"
echo " Working Dir: $(pwd)"
echo " Python: $(python3 --version 2>&1 || which python)"
echo "=================================================="

APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_ROOT"

ATLAS_HOME="${ATLAS_HOME:-/home/atlas}"
mkdir -p "$ATLAS_HOME"

VENV_PATH="$ATLAS_HOME/venv"

# Prefer existing Oryx virtual environment if present
if [ -d "/antenv" ]; then
    echo "[backend] Using Oryx virtualenv at /antenv"
    source /antenv/bin/activate
elif [ -d "$APP_ROOT/antenv" ]; then
    echo "[backend] Using local Oryx virtualenv at $APP_ROOT/antenv"
    source "$APP_ROOT/antenv/bin/activate"
elif [ -f "$VENV_PATH/bin/activate" ]; then
    echo "[backend] Using existing persistent virtualenv at $VENV_PATH"
    source "$VENV_PATH/bin/activate"
else
    echo "[backend] Creating new persistent virtualenv at $VENV_PATH..."
    python3 -m venv "$VENV_PATH"
    source "$VENV_PATH/bin/activate"
    echo "[backend] Installing requirements from requirements.txt..."
    pip install --no-cache-dir --disable-pip-version-check -r requirements.txt
fi

# SQLite journal: the data folder is on the App Service /home network share, which lacks the shared memory WAL needs (config.py).
export ATLAS_DATA_DIR="${ATLAS_DATA_DIR:-$ATLAS_HOME/data}"
export ATLAS_SQLITE_JOURNAL="${ATLAS_SQLITE_JOURNAL:-DELETE}"
mkdir -p "$ATLAS_DATA_DIR"

# Ensure python can locate backend modules
export PYTHONPATH="$APP_ROOT/src:$APP_ROOT:$PYTHONPATH"

# Azure App Service sets $PORT, default to 8000
LISTEN_PORT="${PORT:-8000}"
echo "[backend] Starting Uvicorn on 0.0.0.0:$LISTEN_PORT with 1 worker..."

exec uvicorn backend.app:app --host 0.0.0.0 --port "$LISTEN_PORT" --workers 1 --proxy-headers
