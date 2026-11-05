#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "=========================================================="
echo " Starting Agentic QE Harness (Claude Code Desktop UI)"
echo " Backend: Python FastAPI (port 8000)"
echo " Frontend: Next.js & React (port 3000)"
echo " Protocol: Microsoft Agent Framework (MAF 2.0) & AG-UI"
echo "=========================================================="

# Kill any existing processes on 8000 and 3000
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
lsof -ti:3000 | xargs kill -9 2>/dev/null || true

# Start Python backend
echo "Starting Python FastAPI backend..."
python3 backend/main.py &
BACKEND_PID=$!

sleep 2

# Start Next.js frontend
echo "Starting Next.js frontend..."
npm run dev &
FRONTEND_PID=$!

echo ""
echo "🚀 Agentic QE Harness is live!"
echo "👉 Open http://localhost:3000 in your browser"
echo ""

wait $BACKEND_PID $FRONTEND_PID
