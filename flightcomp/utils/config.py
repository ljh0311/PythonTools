"""
Configuration Module
Manages user preferences and settings
"""
import json
import os
from typing import Any, Dict, Optional, Union

from utils.logging_config import get_logger

logger = get_logger(__name__)


class Config:
    """
    Manages application configuration: load/save from JSON and access with defaults.
    Expects to be run with CWD = project root so aviation_assistant_config.json and atc_notes resolve.
    """

    def __init__(self) -> None:
        self.config_file = "aviation_assistant_config.json"
        self.default_config: Dict[str, Any] = {
            # Role selection settings
            "preferred_role": None,  # "pilot" or "atc"
            "remember_role_preference": False,
            "skip_role_selection": False,
            # Pilot settings
            "experience_level": "advanced",
            "aircraft_type": "jet",
            "default_aircraft_type": "A320",
            "voice_enabled": True,
            "voice_rate": 150,
            "phraseology_region": "US",
            "auto_save_notes": True,
            "notes_directory": "atc_notes",
            "ui_theme": "light",
            "font_size": 12,
            # ATC settings
            "atc_role": "ground",
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
            },
            # AI Settings
            "ai_enabled": True,
            "ai_model": "llama2",
            "ollama_url": "http://localhost:11434",
            "ai_temperature": 0.7,
            "response_type": "general",
            "auto_response": False,
            "max_history": 20,
            "timeout": 30,
            # X-Plane / FlyWithLua bridge
            "xplane_bridge_enabled": False,
            "xplane_bridge_listen_port": 49000,
            "xplane_bridge_send_port": 49001,
        }
        self.config: Dict[str, Any] = self.load_config()

    def load_config(self) -> Dict[str, Any]:
        """Load configuration from file or return defaults. Merges with default_config for missing keys."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    loaded_config = json.load(f)
                for key, value in self.default_config.items():
                    if key not in loaded_config:
                        loaded_config[key] = value
                return loaded_config
            except (json.JSONDecodeError, OSError) as e:
                logger.warning("Error loading config file. Using defaults: %s", e)
                return self.default_config.copy()
        return self.default_config.copy()

    def save_config(self) -> bool:
        """Save current configuration to file. Returns True on success."""
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
            return True
        except OSError as e:
            logger.error("Error saving configuration: %s", e)
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value; falls back to default_config then default."""
        if key in self.config:
            return self.config[key]
        if key in self.default_config:
            return self.default_config[key]
        return default

    def set(self, key: str, value: Any) -> bool:
        """Set a configuration value. Returns True if key is known."""
        if key in self.default_config or key in self.config:
            self.config[key] = value
            return True
        return False

    def reset_to_defaults(self) -> bool:
        """Reset configuration to defaults and save."""
        self.config = self.default_config.copy()
        return self.save_config()

    def get_all(self) -> Dict[str, Any]:
        """Return a copy of the current config dict."""
        return self.config.copy()

    def copy(self) -> "Config":
        """Create a new Config instance with the same config dict."""
        new_config = Config()
        new_config.config = self.config.copy()
        return new_config

    def update(self, other_config: Union["Config", Dict[str, Any]]) -> None:
        """Update config with values from another Config or dict."""
        if isinstance(other_config, Config):
            self.config.update(other_config.config)
        elif isinstance(other_config, dict):
            self.config.update(other_config)
        else:
            raise ValueError("Expected Config object or dictionary")

    def validate_experience_level(self, level: str) -> bool:
        """Validate experience level value."""
        return level in ("beginner", "intermediate", "advanced")

    def validate_aircraft_type(self, aircraft: str) -> bool:
        """Validate aircraft type value."""
        return aircraft in ("single_engine", "multi_engine", "turboprop", "jet")

    def validate_atc_role(self, role: str) -> bool:
        """Validate ATC role value."""
        return role in ("ground", "tower", "approach", "departure")

    def get_frequency(self, position: str) -> str:
        """Get frequency for a specific ATC position."""
        frequencies = self.get("frequencies") or {}
        return frequencies.get(position, "")

    def set_frequency(self, position: str, frequency: str) -> bool:
        """Set frequency for a specific ATC position."""
        frequencies = (self.get("frequencies") or {}).copy()
        frequencies[position] = frequency
        return self.set("frequencies", frequencies)


def ensure_config_directory() -> bool:
    """Create the atc_notes configuration directory if it does not exist. Returns True."""
    if not os.path.exists("atc_notes"):
        os.makedirs("atc_notes")
    return True
