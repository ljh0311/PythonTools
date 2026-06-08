#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
The Eyes - GUI Launcher

This script is a simple launcher for The Eyes GUI application.
"""

import os
import sys
import logging

# Ensure the project root is importable, then load GUI via package path.
project_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(project_dir)
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)

from src.gui_app import TheEyesGUI

if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(os.path.join(project_dir, "the_eyes_gui.log")),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger("the_eyes.launcher")
    logger.info("Starting The Eyes GUI application")
    
    # Create and run the application
    app = TheEyesGUI()
    app.mainloop() 