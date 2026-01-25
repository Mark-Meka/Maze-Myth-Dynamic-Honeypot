@echo off
echo ========================================
echo PROJECT DAEDALUS: STARTING MONITORING
echo ========================================
echo.

REM Start Honeypot on port 8001
echo [1/2] Starting Honeypot System...
start "Honeypot" cmd /k "cd /d %~dp0.. && python honeypot.py"
timeout /t 3 >nul

REM Start Monitor Dashboard on port 8002
echo [2/2] Starting Real-Time Monitor...
start "Dashboard" cmd /k "cd /d %~dp0 && python monitor.py"
timeout /t 3 >nul

echo.
echo ========================================
echo SYSTEM READY
echo ========================================
echo Honeypot:  http://localhost:8001
echo Dashboard: http://localhost:8002
echo ========================================
echo.
echo Opening dashboard...
timeout /t 2 >nul

start "" "http://localhost:8002"

echo.
echo Dashboard is live! Run attacks to see real-time monitoring.
echo Press any key to stop all servers...
pause >nul

echo.
echo Stopping servers...
taskkill /FI "WindowTitle eq Honeypot*" /F >nul 2>&1
taskkill /FI "WindowTitle eq Dashboard*" /F >nul 2>&1

echo Done.
