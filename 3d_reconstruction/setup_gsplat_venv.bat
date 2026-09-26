@echo off
chcp 65001 >nul
cd /d "%~dp0"

echo ========================================
echo  gsplat CUDA env (Python 3.12)
echo ========================================
echo.

py -3.12 --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python 3.12 is required. Install it, then run this script again.
    echo   py -3.12 --version
    pause
    exit /b 1
)

echo Python:
py -3.12 --version
echo.

echo --- nvidia-smi (brief) ---
where nvidia-smi >nul 2>&1
if errorlevel 1 (
    echo Warning: nvidia-smi not found. Will default to PyTorch cu124.
    set "CUDA_TAG=cu124"
    goto :after_cuda_detect
)

nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
for /f "tokens=*" %%A in ('nvidia-smi 2^>nul ^| findstr /i "CUDA Version"') do echo %%A
for /f "tokens=*" %%A in ('nvidia-smi 2^>nul ^| findstr /i "CUDA UMD Version"') do echo %%A

REM Prefer cu128 when driver CUDA capability is 12.8+, else cu124. Default cu124 if unsure.
set "CUDA_TAG=cu124"
set "DETECTED="

REM Parse "CUDA Version: X.Y" or "CUDA UMD Version: X.Y" via Python (robust across nvidia-smi layouts)
for /f "usebackq delims=" %%V in (`py -3.12 -c "import subprocess,re; o=subprocess.check_output('nvidia-smi',text=True,errors='ignore'); m=re.search(r'CUDA (?:UMD )?Version:\s*([\d.]+)', o); print(m.group(1) if m else '')"`) do set "DETECTED=%%V"

if not defined DETECTED (
    echo Could not parse CUDA version; defaulting to cu124.
    goto :after_cuda_detect
)
if "%DETECTED%"=="" (
    echo Could not parse CUDA version; defaulting to cu124.
    goto :after_cuda_detect
)

echo Detected CUDA capability: %DETECTED%

REM 12.8+, 13.x → cu128; 12.4–12.7 → cu124
echo %DETECTED% | findstr /R "^13\." >nul && set "CUDA_TAG=cu128" && goto :after_cuda_detect
echo %DETECTED% | findstr /R "^12\.8" >nul && set "CUDA_TAG=cu128" && goto :after_cuda_detect
echo %DETECTED% | findstr /R "^12\.9" >nul && set "CUDA_TAG=cu128" && goto :after_cuda_detect
echo %DETECTED% | findstr /R "^12\.[4567]" >nul && set "CUDA_TAG=cu124" && goto :after_cuda_detect
echo Unrecognized CUDA version %DETECTED%; defaulting to cu124.

:after_cuda_detect
echo Selected PyTorch CUDA wheel tag: %CUDA_TAG%
echo.

if exist "venv_gsplat" (
    echo Removing existing venv_gsplat...
    rmdir /s /q "venv_gsplat"
)

echo Creating venv_gsplat with Python 3.12...
py -3.12 -m venv venv_gsplat
if errorlevel 1 (
    echo Failed to create virtual environment.
    pause
    exit /b 1
)

echo Upgrading pip...
"venv_gsplat\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
    echo pip upgrade failed.
    pause
    exit /b 1
)

echo.
echo Installing PyTorch (%CUDA_TAG%)...
"venv_gsplat\Scripts\python.exe" -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/%CUDA_TAG%
if errorlevel 1 (
    echo PyTorch install failed for %CUDA_TAG%.
    if /i not "%CUDA_TAG%"=="cu124" (
        echo Falling back to cu124...
        set "CUDA_TAG=cu124"
        "venv_gsplat\Scripts\python.exe" -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu124
        if errorlevel 1 (
            echo PyTorch cu124 fallback also failed.
            pause
            exit /b 1
        )
    ) else (
        pause
        exit /b 1
    )
)

echo.
echo Installing gsplat and common deps...
"venv_gsplat\Scripts\python.exe" -m pip install gsplat viser tqdm imageio imageio-ffmpeg opencv-python pillow
if errorlevel 1 (
    echo gsplat / common deps install failed.
    pause
    exit /b 1
)

echo.
echo Trying pycolmap (optional; skip if wheel unavailable)...
"venv_gsplat\Scripts\python.exe" -m pip install pycolmap
if errorlevel 1 (
    echo Note: pycolmap pip install failed; system COLMAP binary can still be used later.
)

echo.
echo ========================================
echo  Verification
echo ========================================
"venv_gsplat\Scripts\python.exe" -c "import torch; print('torch', torch.__version__); print('cuda_available', torch.cuda.is_available()); print('cuda_device', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'n/a')"
if errorlevel 1 (
    echo torch verification failed.
    pause
    exit /b 1
)

"venv_gsplat\Scripts\python.exe" -c "import gsplat; print('gsplat OK', getattr(gsplat, '__version__', ''))"
if errorlevel 1 (
    echo gsplat import failed.
    pause
    exit /b 1
)

"venv_gsplat\Scripts\python.exe" -c "import cv2; print('cv2 OK', cv2.__version__)"
if errorlevel 1 (
    echo opencv-python (cv2) import failed.
    pause
    exit /b 1
)

echo.
echo Done. Activate with:
echo   .\venv_gsplat\Scripts\Activate.ps1
echo Or run:
echo   .\run_gaussian.bat --help
pause
