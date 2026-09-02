@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo Creating 3d_reconstruction virtual environment (Python 3.12)...
echo.

py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python 3.12 is required. Install it, then run this script again.
    pause
    exit /b 1
)

if exist "venv" (
    echo Removing existing venv...
    rmdir /s /q "venv"
)

py -3.12 -m venv venv
if errorlevel 1 (
    echo Failed to create virtual environment.
    pause
    exit /b 1
)

echo Installing dependencies...
"venv\Scripts\python.exe" -m pip install --upgrade pip
"venv\Scripts\python.exe" -m pip install numpy opencv-python open3d scipy pillow tqdm matplotlib pyntcloud plyfile

echo.
echo Verifying install...
"venv\Scripts\python.exe" -c "import open3d, cv2; print('Setup complete. open3d', open3d.__version__)"
if errorlevel 1 (
    echo Verification failed.
    pause
    exit /b 1
)

echo.
echo Done. Activate with:
echo   .\venv\Scripts\Activate.ps1
echo Or run:
echo   .\launcher.bat
pause
