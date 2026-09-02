@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo mcollama headless smoke test
echo (no Minecraft needed)
echo ========================================
echo.

python smoke_test_mcollama.py %*
set "RC=%ERRORLEVEL%"
if %RC% NEQ 0 (
    echo.
    echo Smoke test failed with exit code %RC%.
    pause
    exit /b %RC%
)

echo.
echo Smoke test passed.
pause
