@echo off
REM The Eyes - Main Launcher

ECHO The Eyes Project - Select an option:
ECHO 1. Run The Eyes GUI
ECHO 2. Run Network Camera Scanner
ECHO 3. Exit

CHOICE /C 123 /N /M "Enter your choice (1-3): "

IF ERRORLEVEL 3 GOTO Exit
IF ERRORLEVEL 2 GOTO RunCameraScanner
IF ERRORLEVEL 1 GOTO RunTheEyes

:RunTheEyes
ECHO Starting The Eyes GUI...
python src\run_gui.py
GOTO Exit

:RunCameraScanner
ECHO Starting Network Camera Scanner...
python src\camera\camera_scanner_gui.py
GOTO Exit

:Exit 