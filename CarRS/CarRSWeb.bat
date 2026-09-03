@echo off
cd /d "%~dp0"
echo Installing web deps if needed...
python -m pip install -q -r requirements-web.txt
echo.
python scripts\run_web.py
pause
