#!/usr/bin/env bash
#
# AI Smart Camera launcher for Linux / Raspberry Pi.
#
# Usage:
#   ./run_smart_camera.sh           # interactive menu
#   ./run_smart_camera.sh gui       # launch GUI app
#   ./run_smart_camera.sh cli       # launch CLI app
#
# On Raspberry Pi OS / Debian, you may need:
#   sudo apt-get install -y python3-tk libatlas-base-dev libgl1
#

set -euo pipefail

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

PYTHON_BIN="${PYTHON_BIN:-python3}"

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Error: $PYTHON_BIN is not installed or not in PATH" >&2
    echo "Please install Python 3.8 or higher." >&2
    exit 1
fi

echo "AI Smart Camera System Launcher"
echo "================================"
echo

# Lightweight dependency check: only verify opencv-python is importable.
if ! "$PYTHON_BIN" -c "import cv2" >/dev/null 2>&1; then
    echo "OpenCV not detected. Installing requirements..."
    "$PYTHON_BIN" -m pip install -r requirements.txt
fi

run_gui() {
    echo "Starting GUI Application..."
    exec "$PYTHON_BIN" gui_app.py "$@"
}

run_cli() {
    echo "Starting Command Line Interface..."
    exec "$PYTHON_BIN" main.py "$@"
}

if [ $# -gt 0 ]; then
    case "$1" in
        gui) shift; run_gui "$@" ;;
        cli) shift; run_cli "$@" ;;
        *) echo "Unknown mode: $1" >&2; exit 2 ;;
    esac
fi

echo "Choose an option:"
echo "  1) GUI Application (Recommended)"
echo "  2) Command Line Interface"
echo "  3) Exit"
echo
read -r -p "Enter your choice (1-3): " choice
case "$choice" in
    1) run_gui ;;
    2) run_cli ;;
    3) echo "Exiting..."; exit 0 ;;
    *) echo "Invalid choice. Starting GUI Application..."; run_gui ;;
esac
