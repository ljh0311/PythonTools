#!/usr/bin/env python3
"""Compatibility launcher for human-detection CLI test."""

from run import main

if __name__ == "__main__":
    raise SystemExit(main(["--mode", "human-detection-cli"]))
