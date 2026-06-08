@echo off
echo Cleaning up The Eyes Web Version...

:: Kill any running servers
taskkill /FI "WINDOWTITLE eq The Eyes Backend*" /F 2>nul
taskkill /FI "WINDOWTITLE eq The Eyes Frontend*" /F 2>nul

:: Remove virtual environment
if exist venv (
    echo Removing virtual environment...
    rmdir /s /q venv
)

:: Remove node_modules
if exist frontend\node_modules (
    echo Removing node_modules...
    rmdir /s /q frontend\node_modules
)

:: Remove build files
if exist frontend\build (
    echo Removing build files...
    rmdir /s /q frontend\build
)

echo Cleanup completed!
pause 