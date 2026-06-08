@echo off
echo ========================================
echo Starting The Eyes Web Version
echo ========================================
echo.

:: Check if virtual environment exists
if not exist venv (
    echo ERROR: Virtual environment not found!
    echo Please run setup.bat first to create the virtual environment.
    echo.
    pause
    exit /b 1
)

:: Check if node_modules exists
if not exist frontend\node_modules (
    echo ERROR: Frontend dependencies not installed!
    echo Please run setup.bat first to install frontend dependencies.
    echo.
    pause
    exit /b 1
)

echo Starting backend server...
echo.

:: Activate virtual environment and start backend
call venv\Scripts\activate
start "The Eyes Backend" cmd /k "cd backend && echo Starting backend on http://localhost:8000 && python main.py"

:: Wait for backend to start
echo Waiting for backend to start...
timeout /t 5 /nobreak >nul

:: Check if backend is running
echo Checking if backend is running...
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% neq 0 (
    echo WARNING: Backend may not be running properly.
    echo Check the backend window for any error messages.
    echo.
)

echo.
echo Starting frontend server...
echo.

:: Start frontend
start "The Eyes Frontend" cmd /k "cd frontend && echo Starting frontend on http://localhost:3000 && npm start"

:: Wait for frontend to start
echo Waiting for frontend to start...
timeout /t 10 /nobreak >nul

echo.
echo ========================================
echo Application Started!
echo ========================================
echo.
echo Backend:  http://localhost:8000
echo Frontend: http://localhost:3000
echo.
echo IMPORTANT NOTES:
echo - Make sure you have at least 2 cameras connected
echo - Allow camera access when prompted by your browser
echo - The application needs HTTPS for camera access (except on localhost)
echo.
echo Press any key to close all servers...
pause >nul

echo.
echo Stopping servers...
taskkill /FI "WINDOWTITLE eq The Eyes Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq The Eyes Frontend*" /F >nul 2>&1
echo Servers stopped. 