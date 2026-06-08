@echo off
setlocal enabledelayedexpansion

echo Setting up The Eyes Web Version...

:: Store the current directory
set "CURRENT_DIR=%~dp0"
cd /d "%CURRENT_DIR%"

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo Python is not installed! Please install Python 3.8 or higher.
    pause
    exit /b 1
)

:: Check if Node.js is installed
node --version >nul 2>&1
if errorlevel 1 (
    echo Node.js is not installed! Please install Node.js 14 or higher.
    pause
    exit /b 1
)

:: Check if backend directory exists
if not exist "backend" (
    echo Error: backend directory not found!
    echo Please ensure you are running this script from the web_version directory.
    pause
    exit /b 1
)

:: Check if frontend directory exists
if not exist "frontend" (
    echo Error: frontend directory not found!
    echo Please ensure you are running this script from the web_version directory.
    pause
    exit /b 1
)

:: Create and activate virtual environment
echo Creating Python virtual environment...
if exist venv (
    echo Virtual environment already exists. Removing old one...
    rmdir /s /q venv
)
python -m venv venv
if errorlevel 1 (
    echo Failed to create virtual environment!
    pause
    exit /b 1
)

:: Activate virtual environment
call venv\Scripts\activate
if errorlevel 1 (
    echo Failed to activate virtual environment!
    pause
    exit /b 1
)

:: Install Python dependencies
echo Installing Python dependencies...
cd backend
if not exist requirements.txt (
    echo Error: requirements.txt not found in backend directory!
    cd ..
    pause
    exit /b 1
)
pip install -r requirements.txt
if errorlevel 1 (
    echo Failed to install Python dependencies!
    cd ..
    pause
    exit /b 1
)
cd ..

:: Install Node.js dependencies
echo Installing Node.js dependencies...
cd frontend
if not exist package.json (
    echo Error: package.json not found in frontend directory!
    cd ..
    pause
    exit /b 1
)
call npm install
if errorlevel 1 (
    echo Failed to install Node.js dependencies!
    cd ..
    pause
    exit /b 1
)
cd ..

echo.
echo Setup completed successfully!
echo.
echo To run the application, use run.bat
pause 