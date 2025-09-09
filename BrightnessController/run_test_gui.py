#!/usr/bin/env python3
"""
Simple launcher for the Human Detection Test GUI
"""

import sys
import os

# Add current directory to path to ensure imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from test_gui import main
    print("🚀 Starting Human Detection Test GUI...")
    main()
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please install required dependencies:")
    print("pip install -r requirements_test_gui.txt")
except Exception as e:
    print(f"❌ Error starting GUI: {e}")
    print("Please check that all dependencies are installed correctly.")
