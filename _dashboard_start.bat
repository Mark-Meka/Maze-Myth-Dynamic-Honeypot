@echo off
REM Helper called by run_honeypot.bat to start the dashboard in its own window.
REM This file exists so the main launcher doesn't need nested quotes
REM (which break on paths that contain spaces, like "Grad Project").
cd /d "%~dp0"
call venv\Scripts\activate.bat
echo.
echo [DASHBOARD] Starting on http://localhost:8002
echo.
python dashboard\monitor.py
pause
