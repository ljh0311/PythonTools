#!/bin/bash

set -e

APP_NAME="Image Merger"
BACKEND_CMD="python backend.py"
FRONTEND_CMD="npm start"
BACKEND_PORT=5000
FRONTEND_PORT=3000

function open_terminal() {
    TITLE="$1"
    CMD="$2"

    if command -v gnome-terminal &> /dev/null; then
        gnome-terminal --title="$TITLE" -- bash -c "$CMD; exec bash" &
    elif command -v konsole &> /dev/null; then
        konsole --title "$TITLE" -e bash -c "$CMD; exec bash" &
    elif command -v xterm &> /dev/null; then
        xterm -title "$TITLE" -e "$CMD; bash" &
    else
        echo "No supported terminal emulator found (gnome-terminal, konsole, xterm)." >&2
        exit 1
    fi
}

clear
echo "==============================================="
echo "  Starting $APP_NAME Application"
echo "==============================================="
echo

echo "[1/2] Starting Python Backend Server..."
open_terminal "Backend Server" "$BACKEND_CMD"

echo "Waiting for backend to initialize..."
sleep 3

echo "[2/2] Starting React Frontend Server..."
open_terminal "Frontend Server" "$FRONTEND_CMD"

echo
echo "-----------------------------------------------"
echo "Both servers are starting up."
echo
echo "Backend Server:   http://localhost:$BACKEND_PORT"
echo "Frontend Server:  http://localhost:$FRONTEND_PORT"
echo
echo "Press Ctrl+C in this window to stop all servers."
echo "-----------------------------------------------"
echo

# Wait for all background jobs (the terminal windows) to finish (typically only happens if they are closed)
wait