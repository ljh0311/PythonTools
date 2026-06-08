#!/usr/bin/env python3
"""
Compatibility launcher for test GUI.

Canonical entrypoint is BrightnessController/run.py
"""

from run import main


if __name__ == "__main__":
    raise SystemExit(main(["--mode", "test-gui"]))
