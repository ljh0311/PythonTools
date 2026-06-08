#!/usr/bin/env python3
"""
SmartCam Launcher

This script provides a convenient way to launch the SmartCam application
with various options including splash screen, error handling, and progress dialogs.
"""

import sys
import os
import argparse
from pathlib import Path

# Add the current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def main():
    """Main launcher function for SmartCam AI."""
    parser = argparse.ArgumentParser(
        description="SmartCam AI - Advanced Camera Intelligence System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python launch_smartcam.py                    # Launch with default settings
  python launch_smartcam.py --splash           # Launch with splash screen
  python launch_smartcam.py --gui              # Launch GUI version
  python launch_smartcam.py --console          # Launch console version
  python launch_smartcam.py --device 2         # Launch PC UI version
        """
    )

    # Command line arguments
    parser.add_argument("--splash", action="store_true",
                        help="Show splash screen on startup")
    parser.add_argument("--gui", action="store_true",
                        help="Launch GUI version (default if not --console)")
    parser.add_argument("--console", action="store_true",
                        help="Launch console (CLI) version")
    parser.add_argument("--device", type=int, choices=[1, 2], default=1,
                        help="Device type: 1=Deployment UI, 2=PC UI (default: 1)")
    parser.add_argument("--debug", action="store_true",
                        help="Enable debug mode (sets SMARTCAM_DEBUG=1)")

    args = parser.parse_args()

    # Enable debug mode if requested
    if args.debug:
        os.environ['SMARTCAM_DEBUG'] = '1'

    # Provide input summary in debug mode for transparency
    if args.debug:
        print("SmartCam launch arguments:", vars(args))

    try:
        from utils.ai_stack_status import print_startup_banner

        print_startup_banner()

        # Prefer explicit selection; default is GUI if neither specified
        if args.console and args.gui:
            print("Warning: Both --console and --gui specified; defaulting to GUI.")
        if args.console:
            print("🚀 Launching SmartCam Console Version (CLI)...")
            try:
                from main import main as console_main
            except ImportError as e:
                print(f"❌ Import error: {e}\nIs main.py present and correct?")
                print("Try: pip install -r requirements.txt")
                return 1
            console_main()
        else:
            print("🚀 Launching SmartCam GUI Version...")
            try:
                from gui_app import _run_direct, _run_with_splash_screen
            except ImportError as e:
                print(f"❌ Failed to import required GUI modules: {e}")
                print("Try: pip install -r requirements.txt")
                return 1

            run_mode_text = "with splash screen" if args.splash else "without splash screen"
            print(f"Starting GUI {run_mode_text} (Device={args.device})...")

            if args.splash:
                _run_with_splash_screen(args.device)
            else:
                _run_direct(args.device)
    except Exception as e:
        import traceback
        print(f"❌ Unhandled exception while launching SmartCam:\n{e}")
        if args.debug:
            traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main()) 