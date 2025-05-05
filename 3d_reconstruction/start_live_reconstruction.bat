@echo off
echo Starting Live 3D Reconstruction...
echo.
echo Press SPACE to add keyframes
echo Press R to start reconstruction
echo Press S to save the reconstruction
echo Press ESC to exit
echo.

python src/live_reconstruction_app.py %*

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo An error occurred. Make sure you have all dependencies installed:
    echo pip install -r requirements.txt
    echo.
    echo For more information, see README_Live_3D.md
    pause
) 