@echo off
echo ===================================
echo    Aviation Operations Assistant
echo ===================================
echo.

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Error: Python is not installed or not in your PATH.
    echo Please install Python from https://www.python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

REM Check if requirements are installed
echo Checking dependencies...
python -c "import pyttsx3, pygame, PIL" >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing required dependencies...
    python -m pip install -r requirements.txt
    if %errorlevel% neq 0 (
        echo.
        echo Error installing dependencies. Please try manually:
        echo python -m pip install -r requirements.txt
        echo.
        pause
        exit /b 1
    )
    echo Dependencies installed successfully!
) else (
    echo Dependencies check passed!
)

echo.
echo Starting Aviation Operations Assistant...
echo.
python main.py
if %errorlevel% neq 0 (
    echo.
    echo Application closed with errors.
    echo If you need assistance, please check the documentation or contact support.
    echo.
    pause
)

exit /b 0 