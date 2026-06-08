import os

# Application Settings
APP_NAME = "VoiceMaster"
APP_VERSION = "0.1.0"

# Directory Settings
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECTS_DIR = os.path.join(BASE_DIR, "projects")
TEMP_DIR = os.path.join(BASE_DIR, "temp")

# Ensure directories exist
os.makedirs(PROJECTS_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)

# Default UI Settings
THEME_COLOR = "#2c3e50"
ACCENT_COLOR = "#3498db"
DARK_MODE = True
