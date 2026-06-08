#!/usr/bin/env python3
"""
Single runtime entrypoint for the unified power-management app.
"""

import argparse
import os
import sys


def _ensure_paths() -> None:
    """Make local and workspace imports reliable when run directly."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    workspace_root = os.path.dirname(current_dir)
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)
    if workspace_root not in sys.path:
        sys.path.insert(0, workspace_root)


def main(argv=None) -> int:
    _ensure_paths()

    parser = argparse.ArgumentParser(
        description="Unified launcher for brightness and battery tools."
    )
    parser.add_argument(
        "--mode",
        choices=["gui", "test-gui"],
        default="gui",
        help="Runtime mode to launch.",
    )
    args = parser.parse_args(argv)

    if args.mode == "gui":
        from brightness_gui import main as gui_main

        gui_main()
        return 0

    if args.mode == "test-gui":
        from test_gui import main as test_gui_main

        test_gui_main()
        return 0

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
