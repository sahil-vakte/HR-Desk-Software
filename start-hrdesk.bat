@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo Python environment is missing. Complete the first-time setup in README.md.
    goto :failed
)
if not exist "backend\.env" (
    echo Backend configuration is missing. Run:
    echo .venv\Scripts\python.exe scripts\init_env.py
    goto :failed
)
if not exist "frontend\.env" (
    echo Frontend configuration is missing. Run:
    echo .venv\Scripts\python.exe scripts\init_env.py
    goto :failed
)
if not exist "frontend\node_modules\.bin\react-scripts.cmd" (
    echo Frontend dependencies are missing. Run npm ci inside the frontend folder.
    goto :failed
)
where npm.cmd >nul 2>&1
if errorlevel 1 (
    echo npm was not found. Install Node.js and reopen your terminal.
    goto :failed
)
".venv\Scripts\python.exe" -c "import django" >nul 2>&1
if errorlevel 1 (
    echo Backend dependencies are missing. Run:
    echo .venv\Scripts\python.exe -m pip install -r backend\requirements.txt
    goto :failed
)

start "HRDESK Backend" /D "%~dp0backend" cmd /k ""%~dp0.venv\Scripts\python.exe" manage.py runserver 8000"
start "HRDESK Frontend" /D "%~dp0frontend" cmd /k "npm.cmd start"
echo Starting HRDESK. Open http://localhost:3000 once the frontend is ready.
echo To stop HRDESK, press Ctrl+C in each server window or close both windows.
exit /b 0

:failed
echo.
pause
exit /b 1
