@echo off
rem Agentic QE MAF 2.0 Terminal Harness Runner for Windows (CMD)
setlocal enabledelayedexpansion

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_ROOT=%%~fI"

set "PYTHONPATH=%PROJECT_ROOT%\src;%PROJECT_ROOT%;%PYTHONPATH%"

where py >nul 2>nul
if %errorlevel%==0 (
    py -3 "%PROJECT_ROOT%\src\backend\cli.py" %*
) else (
    python "%PROJECT_ROOT%\src\backend\cli.py" %*
)
