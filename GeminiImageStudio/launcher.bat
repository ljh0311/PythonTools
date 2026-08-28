@echo off

chcp 65001 >nul

setlocal

cd /d "%~dp0"



echo Gemini Image Studio — local launcher

echo.



if not exist "%~dp0.venv\Scripts\python.exe" (

    echo [.venv missing] Create it first:

    echo   python -m venv .venv

    echo   .venv\Scripts\pip install -r requirements.txt

    echo.

    pause

    exit /b 1

)



if not exist "%~dp0.env" (

    echo [note] No .env found. Copy .env.example to .env and set GEMINI_API_KEY.

    echo        Health works without a key; generate will return 400 until set.

    echo.

)



if not exist "%~dp0frontend\node_modules\" (

    echo [frontend deps missing] Run once:

    echo   cd frontend ^&^& npm install

    echo.

    pause

    exit /b 1

)



REM --- API on 8765: reuse healthy instance, else start, else fail clearly ---

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\check_local_port.ps1" -HostAddress 127.0.0.1 -Port 8765 -HealthUrl "http://127.0.0.1:8765/api/health"

set "API_CHK=%ERRORLEVEL%"



if "%API_CHK%"=="0" (

    echo API already running on http://127.0.0.1:8765 — reusing it.

) else if "%API_CHK%"=="2" (

    echo [error] Port 8765 is in use, but /api/health did not respond.

    echo         Another program may own the port. Find and stop it:

    echo           netstat -ano ^| findstr :8765

    echo         Then re-run this launcher.

    echo.

    pause

    exit /b 2

) else (

    echo Starting API on http://127.0.0.1:8765 ...

    start "Gemini Image Studio API" cmd /k cd /d "%~dp0" ^&^& .venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8765

)



REM --- UI on 5173 ---

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\check_local_port.ps1" -HostAddress 127.0.0.1 -Port 5173

set "UI_CHK=%ERRORLEVEL%"



if "%UI_CHK%"=="0" (

    echo UI already listening on http://127.0.0.1:5173 — reusing it.

) else if "%UI_CHK%"=="2" (

    echo [error] Port 5173 is in use but not usable. Free it and retry:

    echo           netstat -ano ^| findstr :5173

    echo.

    pause

    exit /b 2

) else (

    echo Starting UI on http://127.0.0.1:5173 ...

    start "Gemini Image Studio UI" cmd /k cd /d "%~dp0frontend" ^&^& npm run dev -- --host 127.0.0.1 --port 5173

)



echo.

echo Open http://127.0.0.1:5173 in your browser.

echo API docs: http://127.0.0.1:8765/docs

echo If you see WinError 10048, a previous instance still holds the port —

echo this launcher now reuses a healthy API instead of binding twice.

echo.

pause

endlocal


