@echo off
setlocal enabledelayedexpansion

echo ========================================
echo Gradle Wrapper Setup for Ollama Mod
echo ========================================
echo.

:: Check if wrapper already exists
if exist "gradlew.bat" (
    echo [INFO] Gradle wrapper already exists!
    echo.
    choice /C YN /M "Do you want to re-download it anyway"
    if errorlevel 2 goto :end
    echo.
)

:: Create gradle wrapper directory
echo [1/3] Creating gradle wrapper directory...
if not exist "gradle\wrapper" mkdir "gradle\wrapper"

:: Download gradle-wrapper.jar
echo [2/3] Downloading gradle-wrapper.jar...
echo This may take a moment...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/gradle/gradle/master/gradle/wrapper/gradle-wrapper.jar' -OutFile 'gradle\wrapper\gradle-wrapper.jar'}"
if errorlevel 1 (
    echo [ERROR] Failed to download gradle-wrapper.jar
    goto :error
)

:: Download gradle-wrapper.properties
echo [3/3] Downloading gradle-wrapper.properties...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/gradle/gradle/master/gradle/wrapper/gradle-wrapper.properties' -OutFile 'gradle\wrapper\gradle-wrapper.properties'}"
if errorlevel 1 (
    echo [ERROR] Failed to download gradle-wrapper.properties
    goto :error
)

:: Create gradlew.bat
echo Creating gradlew.bat...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/gradle/gradle/master/gradlew.bat' -OutFile 'gradlew.bat'}"
if errorlevel 1 (
    echo [ERROR] Failed to download gradlew.bat
    goto :error
)

:: Create gradlew (Unix)
echo Creating gradlew...
powershell -Command "& {[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://raw.githubusercontent.com/gradle/gradle/master/gradlew' -OutFile 'gradlew'}"

echo.
echo ========================================
echo [SUCCESS] Gradle Wrapper Setup Complete!
echo ========================================
echo.
echo Files created:
echo - gradlew.bat
echo - gradlew
echo - gradle\wrapper\gradle-wrapper.jar
echo - gradle\wrapper\gradle-wrapper.properties
echo.
echo You can now run: build-and-deploy.bat
echo.
goto :end

:error
echo.
echo ========================================
echo [FAILED] Wrapper Setup Failed!
echo ========================================
echo.
echo Alternative: Install Gradle manually
echo - Download from gradle.org/install
echo - Or use Scoop: scoop install gradle
echo.
pause
exit /b 1

:end
pause
exit /b 0
