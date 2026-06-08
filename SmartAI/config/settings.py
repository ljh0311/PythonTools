"""
Configuration settings for the Smart Robot System.
Provides centralized configuration management for all system components.
"""

import os
import yaml
from typing import Dict, Any, Optional


def get_settings() -> Dict[str, Any]:
    """
    Get the current application settings.
    
    Returns:
        Dict containing all application settings
    """
    # Default settings
    default_settings = {
        'GUI_CONFIG': {
            'splash_duration': 3000,  # 3 seconds
            'window_title': 'Smart Robot Control System',
            'theme': 'dark',
            'update_rate': 30,
            'show_debug_info': True,
            'show_sensor_data': True
        },
        'ROBOT_CONFIG': {
            'app_title': 'Smart Robot Control System',
            'app_tagline': 'Autonomous Navigation & Control',
            'version': '2.0'
        },
        'LOGGING': {
            'level': 'INFO',
            'save_logs': True,
            'log_directory': 'logs/',
            'max_log_size': '10MB',
            'backup_count': 5
        }
    }
    
    # Try to load from robot_config.yaml
    config_path = os.path.join(os.path.dirname(__file__), 'robot_config.yaml')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as file:
                robot_config = yaml.safe_load(file)
                
            # Merge robot config with default settings
            if 'control' in robot_config:
                gui_config = robot_config['control']
                default_settings['GUI_CONFIG'].update({
                    'gui_update_rate': gui_config.get('gui_update_rate', 30),
                    'show_debug_info': gui_config.get('show_debug_info', True),
                    'show_sensor_data': gui_config.get('show_sensor_data', True)
                })
            
            if 'logging' in robot_config:
                default_settings['LOGGING'].update(robot_config['logging'])
                
        except Exception as e:
            print(f"Warning: Could not load robot_config.yaml: {e}")
    
    return default_settings


def get_default_window_sizes() -> Dict[str, Dict[str, int]]:
    """
    Get default window sizes for different dialogs and windows.
    
    Returns:
        Dict containing window size configurations
    """
    return {
        'main_window': {
            'width': 1400,
            'height': 900,
            'min_width': 1000,
            'min_height': 700
        },
        'splash_screen': {
            'width': 500,
            'height': 300
        },
        'settings_dialog': {
            'width': 800,
            'height': 600,
            'min_width': 600,
            'min_height': 400
        }
    }


def save_settings(settings: Dict[str, Any]) -> bool:
    """
    Save settings to configuration file.
    
    Args:
        settings: Settings dictionary to save
        
    Returns:
        True if successful, False otherwise
    """
    try:
        config_path = os.path.join(os.path.dirname(__file__), 'robot_config.yaml')
        
        # Load existing config
        existing_config = {}
        if os.path.exists(config_path):
            with open(config_path, 'r') as file:
                existing_config = yaml.safe_load(file) or {}
        
        # Update with new settings
        if 'GUI_CONFIG' in settings:
            if 'control' not in existing_config:
                existing_config['control'] = {}
            existing_config['control'].update({
                'gui_update_rate': settings['GUI_CONFIG'].get('gui_update_rate', 30),
                'show_debug_info': settings['GUI_CONFIG'].get('show_debug_info', True),
                'show_sensor_data': settings['GUI_CONFIG'].get('show_sensor_data', True)
            })
        
        if 'LOGGING' in settings:
            existing_config['logging'] = settings['LOGGING']
        
        # Save back to file
        with open(config_path, 'w') as file:
            yaml.dump(existing_config, file, default_flow_style=False)
        
        return True
    except Exception as e:
        print(f"Error saving settings: {e}")
        return False


def get_robot_config() -> Dict[str, Any]:
    """
    Get robot-specific configuration from robot_config.yaml.
    
    Returns:
        Dict containing robot configuration
    """
    config_path = os.path.join(os.path.dirname(__file__), 'robot_config.yaml')
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as file:
                return yaml.safe_load(file) or {}
        except Exception as e:
            print(f"Error loading robot config: {e}")
    
    return {} 