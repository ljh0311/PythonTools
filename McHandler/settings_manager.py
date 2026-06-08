"""
Settings Manager - Handle application settings persistence
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional

class SettingsManager:
    """Handle application settings persistence"""
    
    def __init__(self, config_file: str = "config.json"):
        self.config_file = Path(config_file)
        self.settings = self._load_default_settings()
        self.load_settings()
    
    def _load_default_settings(self) -> Dict[str, Any]:
        """Load default settings"""
        return {
            'ollama': {
                'url': 'http://localhost:11434',
                'model': 'llama3.2',
                'timeout': 60
            },
            'application': {
                'default_minecraft_dir': '',
                'auto_backup': True,
                'dark_mode': False,
                'window_geometry': '1200x800'
            },
            'directories': {
                'minecraft_dir': '',
                'shaderpack_dir': '',
                'compatibility_dir': ''
            },
            'ui': {
                'theme': 'default',
                'font_size': 10,
                'show_tooltips': True
            }
        }
    
    def load_settings(self) -> Dict[str, Any]:
        """Load settings from file"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    loaded_settings = json.load(f)
                    # Merge with defaults to ensure all keys exist
                    self._merge_settings(self.settings, loaded_settings)
            except Exception as e:
                print(f"Error loading settings: {e}")
                # Keep default settings if loading fails
        
        return self.settings
    
    def save_settings(self) -> bool:
        """Save settings to file"""
        try:
            # Ensure directory exists
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error saving settings: {e}")
            return False
    
    def get_setting(self, key_path: str, default: Any = None) -> Any:
        """Get a setting value using dot notation (e.g., 'ollama.url')"""
        keys = key_path.split('.')
        value = self.settings
        
        try:
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def set_setting(self, key_path: str, value: Any) -> bool:
        """Set a setting value using dot notation"""
        keys = key_path.split('.')
        current = self.settings
        
        try:
            # Navigate to the parent of the target key
            for key in keys[:-1]:
                if key not in current:
                    current[key] = {}
                current = current[key]
            
            # Set the value
            current[keys[-1]] = value
            return True
        except Exception as e:
            print(f"Error setting setting {key_path}: {e}")
            return False
    
    def _merge_settings(self, default: Dict, loaded: Dict):
        """Recursively merge loaded settings with defaults"""
        for key, value in loaded.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_settings(default[key], value)
            else:
                default[key] = value
    
    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self.settings = self._load_default_settings()
        self.save_settings()
    
    def export_settings(self, export_path: str) -> bool:
        """Export settings to a file"""
        try:
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error exporting settings: {e}")
            return False
    
    def import_settings(self, import_path: str) -> bool:
        """Import settings from a file"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_settings = json.load(f)
            
            # Merge with current settings
            self._merge_settings(self.settings, imported_settings)
            self.save_settings()
            return True
        except Exception as e:
            print(f"Error importing settings: {e}")
            return False
