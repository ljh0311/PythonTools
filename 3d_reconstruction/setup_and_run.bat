@echo off
echo Setting up Live 3D Reconstruction...
echo.

:: Check if Python is installed
where python >nul 2>nul
if %ERRORLEVEL% NEQ 0 (
    echo Python is not installed or not in your PATH.
    echo Please install Python from https://www.python.org/downloads/
    pause
    exit /b 1
)

:: Install dependencies
echo Installing required dependencies...
python -m pip install numpy opencv-python
python -m pip install open3d --no-cache-dir
python -m pip install pyntcloud plyfile tqdm matplotlib

:: Check for errors
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Error installing dependencies. 
    echo Please see TROUBLESHOOTING.md for help.
    pause
    exit /b 1
)

echo.
echo Dependencies installed successfully!
echo.
echo Starting Live 3D Reconstruction...
echo.
echo Controls:
echo   - Press SPACE to add keyframes
echo   - Press R to start reconstruction
echo   - Press S to save the reconstruction
echo   - Press ESC to exit
echo.

:: Run the application
python src/live_reconstruction_app.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred while running the application.
    echo Please see TROUBLESHOOTING.md for help.
    pause
) 