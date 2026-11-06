#!/bin/bash
set -e

echo "=================================================="
echo " Starting Agentic QE Frontend (Azure App Service / Kudu)"
echo " Timestamp: $(date -u)"
echo " Working Dir: $(pwd)"
echo " Node: $(node --version 2>&1 || which node)"
echo " NPM: $(npm --version 2>&1 || which npm)"
echo "=================================================="

APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_ROOT"

# Optimize memory consumption for Basic B1 (1.75 GB RAM)
export NODE_OPTIONS="${NODE_OPTIONS:---max-old-space-size=1024}"
export NEXT_TELEMETRY_DISABLED=1
LISTEN_PORT="${PORT:-3000}"

if [ -z "$ATLAS_BACKEND_URL" ]; then
    echo "[frontend WARNING] ATLAS_BACKEND_URL is not set. Defaulting to http://127.0.0.1:8000"
    export ATLAS_BACKEND_URL="http://127.0.0.1:8000"
fi

# Run startup.js if available (compiles standalone and executes)
if [ -f "startup.js" ]; then
    echo "[frontend] Launching startup.js build and serve runner..."
    exec node startup.js
elif [ -d ".next/standalone" ]; then
    echo "[frontend] Starting pre-built standalone server..."
    cd .next/standalone
    exec node server.js
elif [ -d ".next" ]; then
    echo "[frontend] Starting Next.js production server..."
    exec npx next start -p "$LISTEN_PORT" -H 0.0.0.0
else
    echo "[frontend] Running npm install & npm run build..."
    npm ci --no-audit --no-fund
    npm run build
    exec npx next start -p "$LISTEN_PORT" -H 0.0.0.0
fi
