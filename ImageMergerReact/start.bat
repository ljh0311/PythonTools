@echo off
setlocal ENABLEEXTENSIONS
title Image Merger Starter

REM === Simple output without ANSI codes for better compatibility ===
echo ===============================
echo   Starting Image Merger Application
echo ===============================
echo.

REM === Start Backend Server ===
echo [1/2] Starting Python Backend Server...
start "Backend Server" cmd /k "python backend.py"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to start backend server.
    goto :end
)

REM === Backend delay ===
echo Waiting 3 seconds for backend to initialize...
timeout /t 3 /nobreak > nul

REM === Start Frontend Server ===
echo [2/2] Starting React Frontend Server...
start "Frontend Server" cmd /k "npm start"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to start frontend server.
    goto :end
)

REM === Info output ===
echo.
echo Both servers are starting...
echo Backend will be available at: http://localhost:5000
echo Frontend will be available at: http://localhost:3000
echo.

REM === Wait for user key ===
echo Press any key to close this window. Closing will NOT terminate running servers.
pause > nul 

:end
endlocal