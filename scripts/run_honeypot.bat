@echo off
setlocal

REM ============================================================
REM  Maze Myth Dynamic Honeypot — Windows Launcher
REM  Double-click from anywhere — always uses the correct folder.
REM ============================================================

REM ── Always run from the folder this .bat file lives in ───────
cd /d "%~dp0"

echo.
echo ============================================================
echo   Maze Myth Dynamic Honeypot - Launcher
echo ============================================================
echo   Project: %~dp0
echo ============================================================
echo.

REM ── Check Python ─────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH.
    echo         Download from https://www.python.org/
    pause
    exit /b 1
)

REM ── Create virtual environment if missing ────────────────────
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

REM ── Activate venv ────────────────────────────────────────────
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Could not activate virtual environment.
    pause
    exit /b 1
)

REM ── Install / verify dependencies ──────────────────────────
echo [INFO] Checking dependencies...
python -c "import flask, flask_cors, faker, reportlab, fpdf, openpyxl, dotenv, google.generativeai" >nul 2>&1
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

REM ── Create required directories ────────────────────────────
if not exist "databases\"       mkdir databases
if not exist "log_files\"       mkdir log_files
if not exist "generated_files\" mkdir generated_files

REM ── Check .env file ────────────────────────────────────────
if not exist ".env" (
    echo [WARN] .env not found — copying from .env.template
    copy .env.template .env >nul
    echo        Edit .env and add your GEMINI_API_KEY.
    echo.
    pause
)

REM ── Startup info ───────────────────────────────────────────
echo.
echo ============================================================
echo   Starting services...
echo   [1/2] Honeypot  ->  http://localhost:8001
echo   [2/2] Dashboard ->  http://localhost:8002
echo   Press Ctrl+C in either window to stop.
echo ============================================================
echo.

REM ── Launch Dashboard in a NEW window ──────────────────────
REM  We launch _dashboard_start.bat directly to avoid nested-quote
REM  issues that occur when the project path contains spaces.
start "Maze Myth - Dashboard" "%~dp0_dashboard_start.bat"

REM ── Small delay so dashboard window appears first ──────────
ping -n 3 127.0.0.1 >nul

REM ── Start Honeypot in THIS window ─────────────────────────
echo [HONEYPOT] Starting on http://localhost:8001 ...
echo.
python honeypot.py

REM ── On exit ────────────────────────────────────────────────
deactivate
echo.
echo [INFO] Honeypot stopped. Close the Dashboard window manually.
pause
