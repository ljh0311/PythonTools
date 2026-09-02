@echo off
setlocal enabledelayedexpansion
cd /d "%~dp0"

echo ========================================
echo Ollama Mod - Package Beta
echo ========================================

set "DIST=dist"
set "MOD_VERSION="
for /f "tokens=2 delims==" %%a in ('findstr /b "mod_version=" gradle.properties') do set "MOD_VERSION=%%a"

if "%MOD_VERSION%"=="" (
    echo [ERROR] Could not read mod_version from gradle.properties
    exit /b 1
)

echo [1/3] Building %MOD_VERSION%...
call gradlew.bat clean build --console=plain
if errorlevel 1 (
    echo [ERROR] Build failed
    exit /b 1
)

set "FABRIC_JAR=fabric\build\libs\ollamamod-fabric-%MOD_VERSION%.jar"
set "FORGE_JAR=forge\build\libs\ollamamod-forge-%MOD_VERSION%.jar"

if not exist "%FABRIC_JAR%" (
    echo [ERROR] Missing %FABRIC_JAR%
    exit /b 1
)
if not exist "%FORGE_JAR%" (
    echo [ERROR] Missing %FORGE_JAR%
    exit /b 1
)

echo [2/3] Copying to %DIST%\...
if not exist "%DIST%" mkdir "%DIST%"
copy /Y "%FABRIC_JAR%" "%DIST%\" >nul
copy /Y "%FORGE_JAR%" "%DIST%\" >nul

echo [3/3] Running smoke test (no Ollama required)...
python smoke_test_mcollama.py --skip-build --skip-ollama
if errorlevel 1 (
    echo [ERROR] Smoke test failed
    exit /b 1
)

echo.
echo ========================================
echo Packaged beta %MOD_VERSION%
echo   %DIST%\ollamamod-fabric-%MOD_VERSION%.jar
echo   %DIST%\ollamamod-forge-%MOD_VERSION%.jar
echo ========================================
exit /b 0
