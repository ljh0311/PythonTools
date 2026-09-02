@echo off

REM Start Vite UI on 127.0.0.1:5173, or attach if already listening.

setlocal

cd /d "%~dp0..\frontend"



set "HOST=127.0.0.1"

set "PORT=5173"



powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0check_local_port.ps1" -HostAddress %HOST% -Port %PORT%

set "CHK=%ERRORLEVEL%"



if "%CHK%"=="0" (

    echo UI already listening on http://%HOST%:%PORT% — reusing it.

    echo This window stays open so npm start:all does not exit. Ctrl+C leaves the existing UI running.

    powershell -NoProfile -Command "while ($true) { Start-Sleep -Seconds 3600 }"

    exit /b 0

)

if "%CHK%"=="2" (

    echo Port %PORT% is in use but not usable.

    echo Stop the other process, then retry. Example:

    echo   netstat -ano ^| findstr :%PORT%

    exit /b 2

)



if not exist "node_modules\" (

    echo [frontend deps missing] Run: npm install

    exit /b 1

)



echo Starting UI on http://%HOST%:%PORT% ...

call npm run ui -- --host %HOST% --port %PORT%

exit /b %ERRORLEVEL%


