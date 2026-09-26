@echo off
chcp 65001 >nul
cd /d "%~dp0"

REM Ensure COLMAP is visible even if this terminal started before PATH was updated.
if exist "%LOCALAPPDATA%\Programs\COLMAP\COLMAP.bat" (
    set "PATH=%LOCALAPPDATA%\Programs\COLMAP;%PATH%"
)

if not exist "venv_gsplat\Scripts\python.exe" (
    echo Error: venv_gsplat not found. Run setup_gsplat_venv.bat first.
    exit /b 1
)

"venv_gsplat\Scripts\python.exe" src\gaussian_cli.py %*
