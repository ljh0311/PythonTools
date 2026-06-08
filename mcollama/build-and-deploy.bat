@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Ollama Mod - Build and Deploy Script
echo (Using mrtmod Gradle wrapper)
echo ========================================
echo.

set "MODS_FOLDER=C:\Users\user\AppData\Roaming\ATLauncher\instances\Homestead\mods"
set "MOD_VERSION=1.0.0"
set "FABRIC_JAR=fabric\build\libs\ollamamod-fabric-%MOD_VERSION%.jar"
set "FORGE_JAR=forge\build\libs\ollamamod-forge-%MOD_VERSION%.jar"
set "MRTMOD_GRADLEW=..\mrtmod\mtr-ollama-integration\gradlew.bat"

echo [%date% %time%] Starting build process...
echo.

if exist "gradlew.bat" (
    echo [INFO] Using local Gradle wrapper
    set "GRADLE_CMD=gradlew.bat"
) else (
    if exist "%MRTMOD_GRADLEW%" (
        echo [INFO] Using Gradle wrapper from mrtmod project
        set "GRADLE_CMD=%MRTMOD_GRADLEW%"
    ) else (
        echo [INFO] Checking for system Gradle installation...
        where gradle >nul 2>&1
        if errorlevel 1 (
            echo [ERROR] No Gradle found!
            echo.
            echo Solutions:
            echo   1. Run PowerShell as Administrator and try: choco install gradle
            echo   2. Install Gradle manually from gradle.org/install
            echo   3. Download wrapper files from another Gradle project
            echo   4. Use Scoop ^(no admin needed^): scoop install gradle
            echo.
            goto :error
        )
        echo [INFO] Using system Gradle installation
        set "GRADLE_CMD=gradle"
    )
)
echo.

echo [1/4] Cleaning old build artifacts...
call %GRADLE_CMD% clean
if errorlevel 1 (
    echo [ERROR] Failed to clean old builds!
    goto :error
)
echo [SUCCESS] Old builds cleaned
echo.

echo [2/4] Building Fabric and Forge versions...
echo This may take a few minutes...
call %GRADLE_CMD% build
if errorlevel 1 (
    echo [ERROR] Build failed! Check the output above for errors.
    goto :error
)
echo [SUCCESS] Build completed successfully
echo.

echo [3/4] Verifying build artifacts...
if not exist "%FABRIC_JAR%" (
    echo [ERROR] Fabric JAR not found at: %FABRIC_JAR%
    goto :error
)
echo [FOUND] Fabric JAR: %FABRIC_JAR%

if not exist "%FORGE_JAR%" (
    echo [ERROR] Forge JAR not found at: %FORGE_JAR%
    goto :error
)
echo [FOUND] Forge JAR: %FORGE_JAR%
echo.

echo [4/4] Deploying to mods folder...

if not exist "%MODS_FOLDER%" (
    echo [INFO] Creating mods folder: %MODS_FOLDER%
    mkdir "%MODS_FOLDER%"
)

echo [INFO] Removing old versions...
del /Q "%MODS_FOLDER%\ollamamod-fabric-*.jar" 2>nul
del /Q "%MODS_FOLDER%\ollamamod-forge-*.jar" 2>nul

echo [INFO] Copying Fabric JAR...
copy /Y "%FABRIC_JAR%" "%MODS_FOLDER%\"
if errorlevel 1 (
    echo [ERROR] Failed to copy Fabric JAR!
    goto :error
)

echo [INFO] Copying Forge JAR...
copy /Y "%FORGE_JAR%" "%MODS_FOLDER%\"
if errorlevel 1 (
    echo [ERROR] Failed to copy Forge JAR!
    goto :error
)

echo.
echo ========================================
echo [SUCCESS] Build and Deploy Complete!
echo ========================================
echo.
echo Deployed to: %MODS_FOLDER%
echo - ollamamod-fabric-%MOD_VERSION%.jar
echo - ollamamod-forge-%MOD_VERSION%.jar
echo.
echo [%date% %time%] Process finished successfully
echo.
goto :end

:error
echo.
echo ========================================
echo [FAILED] Build and Deploy Failed!
echo ========================================
echo.
echo Please check the error messages above.
echo Common issues:
echo - Java 17 or later required ^(you have Java 11^)
echo - Download Java 17+ from: adoptium.net or oracle.com/java
echo - Java/Gradle not installed or not in PATH
echo - Network issues downloading dependencies
echo - Insufficient disk space
echo - Mods folder permissions
echo.
pause
exit /b 1

:end
echo Press any key to exit...
pause >nul
exit /b 0
