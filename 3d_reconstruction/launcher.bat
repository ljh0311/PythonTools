@echo off
chcp 65001 >nul
echo Starting 3D Reconstruction Launcher...
echo.

REM Change to the script directory
cd /d "%~dp0"

REM Use project-local virtual environment
set "PYTHON_EXE=%~dp0venv\Scripts\python.exe"
if not exist "%PYTHON_EXE%" (
    echo Error: Project virtual environment not found.
    echo Run setup_venv.bat first to create it.
    pause
    exit /b 1
)

REM Launch the basic launcher GUI
"%PYTHON_EXE%" src\basic_launcher_gui.py

if errorlevel 1 (
    echo.
    echo Error launching the GUI. Please check the error message above.
    pause
) 