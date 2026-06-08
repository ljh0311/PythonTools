@echo off
REM =========================================
REM The Eyes - Home Monitoring System Launcher
REM =========================================

echo Starting The Eyes Home Monitoring System...
echo.

REM Set up Python path and environment
set PYTHONPATH=%~dp0..
cd %~dp0..

REM Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Check if required packages are installed
python -c "import cv2, numpy, tkinter, PIL" >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Installing required packages...
    pip install -r requirements.txt
    if %ERRORLEVEL% NEQ 0 (
        echo Error: Failed to install required packages
        pause
        exit /b 1
    )
)

REM Launch the application
python src/gui_app.py

REM If application crashes, show message and keep window open
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo The application exited with an error code: %ERRORLEVEL%
    echo Please check the logs for more information.
    pause
    exit /b %ERRORLEVEL%
)

exit /b 0 