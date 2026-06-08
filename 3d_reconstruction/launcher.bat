@echo off
chcp 65001 >nul
echo Starting 3D Reconstruction Launcher...
echo.

REM Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    echo Please install Python 3.7 or higher and try again
    pause
    exit /b 1
)

REM Change to the script directory
cd /d "%~dp0"

REM Launch the basic launcher GUI
python src\basic_launcher_gui.py

if errorlevel 1 (
    echo.
    echo Error launching the GUI. Please check the error message above.
    pause
) 