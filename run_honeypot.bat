@echo off
setlocal enabledelayedexpansion
REM ============================================================
REM  Maze Myth Dynamic Honeypot — Windows Launcher
REM  Starts both the Honeypot (port 8001) and Dashboard (port 8002)
REM  in separate windows.
REM ============================================================

echo.
echo ============================================================
echo   Maze Myth Dynamic Honeypot - Launcher
echo ============================================================
echo.

REM ── Check Python ────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Download from https://www.python.org/
    pause
    exit /b 1
)

REM ── Create virtual environment if missing ───────────────────
if not exist "venv\" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo [OK]   Virtual environment created.
)

REM ── Activate venv ───────────────────────────────────────────
call venv\Scripts\activate.bat

REM ── Install / verify dependencies ────────────────────────────
echo [INFO] Checking dependencies...
python -c "import flask, flask_cors, faker, reportlab, fpdf, openpyxl, PIL, dotenv, google.generativeai" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing requirements (first run only)...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install dependencies.
        pause
        exit /b 1
    )
    echo [OK]   Dependencies installed.
) else (
    echo [OK]   Dependencies already installed.
)

REM ── Create required directories ──────────────────────────────
if not exist "databases\"      mkdir databases
if not exist "log_files\"      mkdir log_files
if not exist "generated_files\" mkdir generated_files

REM ── Check .env file ──────────────────────────────────────────
if not exist ".env" (
    echo [WARN] .env file not found.
    echo        Copying .env.template to .env ...
    copy .env.template .env >nul
    echo        Open .env and add your GEMINI_API_KEY before using the LLM features.
    echo.
)

REM ── Print startup info ───────────────────────────────────────
echo.
echo ============================================================
echo   Starting services...
echo ============================================================
echo.
echo   [1/2] Honeypot API    ->  http://localhost:8001
echo   [2/2] Dashboard       ->  http://localhost:8002
echo.
echo   Press Ctrl+C in either window to stop that service.
echo ============================================================
echo.

REM ── Launch Dashboard in a new window ────────────────────────
REM    We start dashboard first so it is ready when honeypot fires events.
start "Maze Myth - Dashboard (port 8002)" cmd /k "call venv\Scripts\activate.bat && echo [DASHBOARD] Starting on http://localhost:8002 && python dashboard\monitor.py"

REM ── Small delay so dashboard window appears first ────────────
timeout /t 2 /nobreak >nul

REM ── Launch Honeypot in THIS window ──────────────────────────
echo [HONEYPOT] Starting on http://localhost:8001 ...
echo.
python honeypot.py

REM ── On exit ─────────────────────────────────────────────────
deactivate
echo.
echo [INFO] Honeypot stopped. Close the Dashboard window manually.
pause
