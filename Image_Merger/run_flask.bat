@echo off
setlocal EnableDelayedExpansion
echo Starting Image Merger Flask Application...
echo.

:: Get the IP address of this machine
for /f "tokens=2 delims=:" %%a in ('ipconfig ^| findstr /c:"IPv4 Address"') do (
    set IP_ADDRESS=%%a
    set IP_ADDRESS=!IP_ADDRESS:~1!
    goto :found_ip
)
:found_ip

echo =================================================================
echo Local access: http://localhost:5000
echo Network access (for other devices): http://!IP_ADDRESS!:5000
echo =================================================================
echo.
echo Press Ctrl+C to stop the server
echo.

:: Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    call venv\Scripts\activate.bat
) else (
    echo WARNING: Virtual environment not found. Dependencies may be missing.
)

:: Run the Flask application with network access enabled
set FLASK_APP=app.py
set FLASK_DEBUG=1
python -m flask run --host=0.0.0.0

pause 