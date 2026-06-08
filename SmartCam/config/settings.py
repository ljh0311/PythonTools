"""
Settings configuration for SmartCam application.

This module provides centralized configuration management for the SmartCam application,
including GUI settings, camera settings, and application preferences.
"""

import json
import os
from typing import Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

# Default settings
DEFAULT_SETTINGS = {
    "GUI_CONFIG": {
        "splash_duration": 3000,  # milliseconds
        "theme": "default",
        "window_size": "1200x800",
        "min_window_size": [800, 600],
        "deployment_window_size": "480x900",
        "deployment_fullscreen": False,
        "enable_dpad_navigation": True,
        "auto_save_settings": True,
        "show_tooltips": True,
        "enable_animations": True
    },
    "CAMERA_CONFIG": {
        "default_camera_id": 0,
        "default_resolution": [640, 480],
        "default_fps": 30,
        "auto_detect_cameras": True,
        "camera_timeout": 5000,  # milliseconds
        "retry_attempts": 3,
        # Backend selection: "auto" picks per-OS defaults
        # (Windows: DSHOW/MSMF, Linux/RPi: V4L2/GSTREAMER, macOS: AVFOUNDATION).
        # Override with a list like ["CAP_V4L2", "CAP_ANY"].
        "backend_preference": "auto"
    },
    "AI_CONFIG": {
        "enable_face_detection": True,
        "enable_motion_detection": True,
        "enable_object_detection": True,
        "detection_confidence": 0.5,
        "detection_interval": 100,  # milliseconds
        "max_detections_per_frame": 10
    },
    "STORAGE_CONFIG": {
        "output_directory": "captures",
        "auto_cleanup_enabled": True,
        "cleanup_age_hours": 24,
        "max_storage_mb": 1024,  # 1GB
        "compression_enabled": True
    },
    "ENHANCEMENT_CONFIG": {
        "default_enhancement": "auto",
        "enable_ai_enhancement": True,
        "enhancement_quality": "high",
        "save_original": True,
        "save_enhanced": True
    },
    "ERROR_HANDLING": {
        "show_detailed_errors": True,
        "log_errors_to_file": True,
        "error_log_file": "error_log.txt",
        "max_error_log_size_mb": 10
    },
    "SMART_PROCESSING_CONFIG": {
        "auto_tagging_enabled": True,
        "scene_classification_enabled": True,
        "anomaly_detection_enabled": True,
        "anomaly_sensitivity": 0.7,
        "baseline_frames": 30
    },
    "PROCESSING_PROFILE": {
        # "auto" = pick by host (RPi -> rpi, otherwise balanced).
        # Other valid names: "quality", "balanced", "performance", "rpi".
        "name": "auto"
    }
}

# Settings file path
SETTINGS_FILE = Path("config/smartcam_settings.json")


def get_settings() -> Dict[str, Any]:
    """
    Get application settings.
    
    Returns:
        Dictionary containing all application settings
    """
    try:
        if SETTINGS_FILE.exists():
            with open(SETTINGS_FILE, 'r', encoding='utf-8') as f:
                settings = json.load(f)
                # Merge with defaults to ensure all settings exist
                return _merge_settings(DEFAULT_SETTINGS, settings)
        else:
            # Create default settings file
            _save_settings(DEFAULT_SETTINGS)
            return DEFAULT_SETTINGS.copy()
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS.copy()


def update_settings(new_settings: Dict[str, Any]) -> bool:
    """
    Update application settings.
    
    Args:
        new_settings: Dictionary containing new settings to update
        
    Returns:
        True if settings were updated successfully, False otherwise
    """
    try:
        current_settings = get_settings()
        updated_settings = _merge_settings(current_settings, new_settings)
        return _save_settings(updated_settings)
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        return False


def _merge_settings(default: Dict[str, Any], custom: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge custom settings with defaults, ensuring all required settings exist.
    
    Args:
        default: Default settings dictionary
        custom: Custom settings dictionary
        
    Returns:
        Merged settings dictionary
    """
    result = default.copy()
    
    def merge_dict(target: Dict[str, Any], source: Dict[str, Any]):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                merge_dict(target[key], value)
            else:
                target[key] = value
    
    merge_dict(result, custom)
    return result


def _save_settings(settings: Dict[str, Any]) -> bool:
    """
    Save settings to file.
    
    Args:
        settings: Settings dictionary to save
        
    Returns:
        True if settings were saved successfully, False otherwise
    """
    try:
        # Ensure config directory exists
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(settings, f, indent=2, ensure_ascii=False)
        
        logger.info("Settings saved successfully")
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False


def get_gui_config() -> Dict[str, Any]:
    """
    Get GUI-specific configuration.
    
    Returns:
        GUI configuration dictionary
    """
    settings = get_settings()
    return settings.get("GUI_CONFIG", {})


def get_camera_config() -> Dict[str, Any]:
    """
    Get camera-specific configuration.
    
    Returns:
        Camera configuration dictionary
    """
    settings = get_settings()
    return settings.get("CAMERA_CONFIG", {})


def get_ai_config() -> Dict[str, Any]:
    """
    Get AI-specific configuration.
    
    Returns:
        AI configuration dictionary
    """
    settings = get_settings()
    return settings.get("AI_CONFIG", {})


def get_storage_config() -> Dict[str, Any]:
    """
    Get storage-specific configuration.
    
    Returns:
        Storage configuration dictionary
    """
    settings = get_settings()
    return settings.get("STORAGE_CONFIG", {})


def get_enhancement_config() -> Dict[str, Any]:
    """
    Get enhancement-specific configuration.
    
    Returns:
        Enhancement configuration dictionary
    """
    settings = get_settings()
    return settings.get("ENHANCEMENT_CONFIG", {})


def get_error_handling_config() -> Dict[str, Any]:
    """
    Get error handling configuration.
    
    Returns:
        Error handling configuration dictionary
    """
    settings = get_settings()
    return settings.get("ERROR_HANDLING", {})


def get_smart_processing_config() -> Dict[str, Any]:
    """
    Get smart processing configuration.
    
    Returns:
        Smart processing configuration dictionary
    """
    settings = get_settings()
    return settings.get("SMART_PROCESSING_CONFIG", {})


def get_processing_profile_name() -> str:
    """Return the configured processing profile name (e.g. "auto", "balanced")."""
    settings = get_settings()
    return settings.get("PROCESSING_PROFILE", {}).get("name", "auto")
