@echo off
rem Run Agentic QE Platform & Harness on Windows (FastAPI on 8000, Next.js on 3000)
setlocal enabledelayedexpansion

cd /d "%~dp0"

echo ==========================================================
echo  Starting Agentic QE Harness (Claude Code Desktop UI)
echo  Backend: Python FastAPI (port 8000)
echo  Frontend: Next.js ^& React (port 3000)
echo  Protocol: Microsoft Agent Framework (MAF 2.0) ^& AG-UI
echo ==========================================================

rem Ensure database is migrated and seeded
set "PYTHONPATH=%~dp0src;%~dp0;%PYTHONPATH%"
where py >nul 2>nul
if %errorlevel%==0 (
    py -3 -c "from backend import db; from backend.core.seed_data import seed_database; db.migrate(); seed_database()"
) else (
    python -c "from backend import db; from backend.core.seed_data import seed_database; db.migrate(); seed_database()"
)

rem Start Python FastAPI backend in a new window
echo Starting Python FastAPI backend on port 8000...
if %errorlevel%==0 (
    start "AQE Backend (port 8000)" py -3 -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
) else (
    start "AQE Backend (port 8000)" python -m uvicorn backend.app:app --host 127.0.0.1 --port 8000
)

timeout /t 2 /nobreak >nul

rem Start Next.js frontend in a new window
echo Starting Next.js frontend on port 3000...
start "AQE Frontend (port 3000)" cmd /c "npm --prefix src\frontend run dev"

echo.
echo ==========================================================
echo  🚀 Agentic QE Harness is live!
echo  👉 Open http://localhost:3000 in your browser
echo ==========================================================
echo.
