@echo off
setlocal enabledelayedexpansion

:: Set title
title Image Merger Server Control

:menu
cls
echo ===================================
echo Image Merger Server Control Panel
echo ===================================
echo.
echo 1. Start Local Server
echo 2. Start Network Server
echo 3. Restart Server
echo 4. Check Network Status
echo 5. Exit
echo.
set /p choice="Enter your choice (1-5): "

if "%choice%"=="1" goto start_local
if "%choice%"=="2" goto start_network
if "%choice%"=="3" goto restart_server
if "%choice%"=="4" goto check_network
if "%choice%"=="5" goto end

echo Invalid choice. Please try again.
timeout /t 2 >nul
goto menu

:start_local
cls
echo Starting local server...
call :activate_venv
set FLASK_APP=app.py
set FLASK_DEBUG=1
python -m flask run
goto end

:start_network
cls
echo Starting network server...
call :activate_venv
set FLASK_APP=app.py
set FLASK_DEBUG=1
echo.
echo Your IP addresses (use one of these):
ipconfig | findstr /c:"IPv4 Address"
echo.
echo Use one of these IP addresses to connect from other devices: http://YOUR_IP:5000
echo Local access: http://localhost:5000
echo.
python -m flask run --host=0.0.0.0
goto end

:restart_server
cls
echo Stopping any running Flask servers...
taskkill /f /im python.exe /fi "WINDOWTITLE eq Flask*" >nul 2>&1
timeout /t 2 /nobreak >nul
goto menu

:check_network
cls
echo Checking network connectivity...
echo.
echo Checking if port 5000 is in use...
netstat -an | findstr ":5000"
echo.
echo Your IP addresses:
ipconfig | findstr /c:"IPv4 Address"
echo.
echo Checking Windows Firewall status...
netsh advfirewall show allprofiles state
echo.
echo Python executable path:
where python
echo.
pause
goto menu

:activate_venv
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found. Dependencies may be missing.
    timeout /t 3 >nul
)
exit /b

:end
echo.
echo Server stopped. Press any key to return to menu...
pause >nul
goto menu 