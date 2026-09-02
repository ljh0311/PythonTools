@echo off

REM Start API on 127.0.0.1:8765, or attach to an already-healthy instance.

setlocal

cd /d "%~dp0.."



set "HOST=127.0.0.1"

set "PORT=8765"

if defined PORT_OVERRIDE set "PORT=%PORT_OVERRIDE%"



powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check_local_port.ps1" -HostAddress %HOST% -Port %PORT% -HealthUrl "http://%HOST%:%PORT%/api/health"

set "CHK=%ERRORLEVEL%"



if "%CHK%"=="0" (

    echo API already running on http://%HOST%:%PORT% — reusing it.

    echo This window stays open so npm start:all does not exit. Ctrl+C leaves the existing server running.

    powershell -NoProfile -Command "while ($true) { Start-Sleep -Seconds 3600 }"

    exit /b 0

)

if "%CHK%"=="2" (

    echo Port %PORT% is in use but /api/health did not respond.

    echo Stop the other process, then retry. Example:

    echo   netstat -ano ^| findstr :%PORT%

    exit /b 2

)



if not exist "%~dp0..\.venv\Scripts\python.exe" (

    echo [.venv missing] Create it first: python -m venv .venv

    exit /b 1

)



echo Starting API on http://%HOST%:%PORT% ...

.venv\Scripts\python.exe -m uvicorn backend.main:app --host %HOST% --port %PORT%

exit /b %ERRORLEVEL%


