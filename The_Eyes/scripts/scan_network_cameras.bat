@echo off
echo Running Network Camera Scanner...
echo.

REM Check if Python is available
python --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH.
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Install required packages if they're not already installed
echo Checking and installing required packages...
pip install -q requests ipaddress

REM Run the scanner script
python network_camera_scanner.py %*

echo.
pause 