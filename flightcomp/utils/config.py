"""
Configuration Module
Manages user preferences and settings
"""
import json
import os

class Config:
    def __init__(self):
        self.config_file = "aviation_assistant_config.json"
        self.default_config = {
            # Role selection settings
            "preferred_role": None,  # "pilot" or "atc"
            "remember_role_preference": False,
            "skip_role_selection": False,
            
            # Pilot settings
            "experience_level": "beginner",  # beginner, intermediate, advanced
            "aircraft_type": "single_engine",  # single_engine, multi_engine, turboprop, jet
            "voice_enabled": True,
            "voice_rate": 150,  # Words per minute
            "phraseology_region": "US",  # US, ICAO, UK, etc.
            "auto_save_notes": True,
            "notes_directory": "atc_notes",
            "ui_theme": "light",  # light, dark
            "font_size": 12,
            
            # ATC settings
            "atc_role": "ground",  # ground, tower, approach, departure
            "airport_icao": "KXYZ",
            "airport_name": "Example Airport",
            "runways": ["27", "09", "36", "18"],
            "active_runways": ["27", "36"],
            "default_altimeter": "2992",
            "controller_callsign": "Example Ground",
            "frequencies": {
                "ground": "121.9",
                "tower": "118.7",
                "approach": "119.1",
                "departure": "125.5"
            }
        }
        self.config = self.load_config()
    
    def load_config(self):
        """Load configuration from file or create with defaults"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    
                    # Update with any missing default keys
                    for key, value in self.default_config.items():
                        if key not in loaded_config:
                            loaded_config[key] = value
                    
                    return loaded_config
            except (json.JSONDecodeError, IOError):
                print(f"Error loading config file. Using defaults.")
                return self.default_config.copy()
        else:
            return self.default_config.copy()
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            return True
        except IOError:
            print("Error saving configuration")
            return False
    
    def get(self, key, default=None):
        """Get a configuration value"""
        if key in self.config:
            return self.config[key]
        elif key in self.default_config:
            return self.default_config[key]
        else:
            return default
    
    def set(self, key, value):
        """Set a configuration value"""
        if key in self.default_config or key in self.config:
            self.config[key] = value
            return True
        return False
    
    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self.config = self.default_config.copy()
        return self.save_config()
    
    def get_all(self):
        """Get all configuration values"""
        return self.config.copy()
    
    def validate_experience_level(self, level):
        """Validate experience level value"""
        valid_levels = ["beginner", "intermediate", "advanced"]
        return level in valid_levels
    
    def validate_aircraft_type(self, aircraft):
        """Validate aircraft type value"""
        valid_types = ["single_engine", "multi_engine", "turboprop", "jet"]
        return aircraft in valid_types
    
    def validate_atc_role(self, role):
        """Validate ATC role value"""
        valid_roles = ["ground", "tower", "approach", "departure"]
        return role in valid_roles
    
    def get_frequency(self, position):
        """Get frequency for a specific ATC position"""
        frequencies = self.get("frequencies")
        return frequencies.get(position, "")
    
    def set_frequency(self, position, frequency):
        """Set frequency for a specific ATC position"""
        frequencies = self.get("frequencies").copy()
        frequencies[position] = frequency
        return self.set("frequencies", frequencies)

# Function to create config directory if it doesn't exist
def ensure_config_directory():
    """Create configuration directory if it doesn't exist"""
    if not os.path.exists("atc_notes"):
        os.makedirs("atc_notes")
    return True 