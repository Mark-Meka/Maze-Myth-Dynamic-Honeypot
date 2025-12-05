@echo off
REM Run Honeypot (Windows)
REM Quick launcher for the API honeypot system

echo ============================================================
echo [HONEYPOT] Starting API Honeypot System
echo ============================================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/
    pause
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv\" (
    echo [INFO] Creating virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment
        pause
        exit /b 1
    )
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if requirements are installed
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Installing requirements...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Failed to install requirements
        pause
        exit /b 1
    )
)

REM Check if directories exist
if not exist "databases\" (
    echo [INFO] Setting up honeypot directories...
    python setup_honeypot.py
)

echo.
echo ============================================================
echo [OK] Environment ready!
echo ============================================================
echo.
echo Starting API Honeypot on http://localhost:8001
echo.
echo Available endpoints:
echo   - API Documentation: http://localhost:8001/docs
echo   - Health Check: http://localhost:8001/health
echo   - Root: http://localhost:8001/
echo.
echo Press Ctrl+C to stop the server
echo ============================================================
echo.

REM Run the honeypot
python api_honeypot.py

REM Deactivate on exit
deactivate
pause
