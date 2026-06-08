@echo off
echo Starting The Eyes Web Version...

:: Check if virtual environment exists
if not exist venv (
    echo Virtual environment not found! Please run setup.bat first.
    pause
    exit /b 1
)

:: Activate virtual environment
call venv\Scripts\activate

:: Start backend server in a new window
start "The Eyes Backend" cmd /k "cd backend && python main.py"

:: Wait a moment for the backend to start
timeout /t 3 /nobreak >nul

:: Start frontend server in a new window
start "The Eyes Frontend" cmd /k "cd frontend && npm start"

echo.
echo The application is starting...
echo Backend will be available at: http://localhost:8000
echo Frontend will be available at: http://localhost:3000
echo.
echo Press any key to close all servers...
pause >nul

:: Kill the backend and frontend processes
taskkill /FI "WINDOWTITLE eq The Eyes Backend*" /F
taskkill /FI "WINDOWTITLE eq The Eyes Frontend*" /F