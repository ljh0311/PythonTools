@echo off
echo AI Smart Camera System Launcher
echo ================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.8 or higher
    pause
    exit /b 1
)

REM Check if requirements are installed
echo Checking dependencies...
pip show opencv-python >nul 2>&1
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
)

echo.
echo Starting AI Smart Camera System...
echo.
echo Choose an option:
echo 1. GUI Application (Recommended)
echo 2. Command Line Interface
echo 3. Exit
echo.

set /p choice="Enter your choice (1-3): "

if "%choice%"=="1" (
    echo Starting GUI Application...
    python gui_app.py
) else if "%choice%"=="2" (
    echo Starting Command Line Interface...
    python main.py
) else if "%choice%"=="3" (
    echo Exiting...
    exit /b 0
) else (
    echo Invalid choice. Starting GUI Application...
    python gui_app.py
)

pause 