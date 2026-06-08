"""
Audio Effects for Radio Communication
Provides audio processing for realistic radio effects
"""

import random
from typing import List, Optional
from enum import Enum
from utils.radio_simulator import RadioQuality


class AudioEffectType(Enum):
    """Types of audio effects"""
    STATIC = "static"
    DISTORTION = "distortion"
    DELAY = "delay"
    ECHO = "echo"
    FILTER = "filter"
    COMPRESSION = "compression"


class AudioProcessor:
    """Processes audio for radio effects"""
    
    def __init__(self):
        """Initialize audio processor"""
        self.effects_enabled = True
    
    def apply_radio_effects(self, 
                           text: str, 
                           quality: RadioQuality) -> str:
        """
        Apply radio effects to text (simulated)
        
        In a full implementation, this would process actual audio samples.
        For now, we simulate effects through text modifications.
        
        Args:
            text: Original text
            quality: Radio quality level
        
        Returns:
            Text with simulated radio effects
        """
        if not self.effects_enabled:
            return text
        
        processed = text
        
        # Apply quality-based text modifications
        if quality == RadioQuality.POOR or quality == RadioQuality.VERY_POOR:
            # Simulate word loss
            words = processed.split()
            if len(words) > 2 and random.random() < 0.15:
                # Remove a random word
                words.pop(random.randint(0, len(words) - 1))
                processed = " ".join(words)
            
            # Add static indicators
            if random.random() < 0.25:
                processed = f"[static] {processed} [static]"
            
            # Simulate partial word loss
            if random.random() < 0.1:
                words = processed.split()
                if words:
                    idx = random.randint(0, len(words) - 1)
                    word = words[idx]
                    if len(word) > 3:
                        words[idx] = word[:len(word)//2] + "..."
                    processed = " ".join(words)
        
        elif quality == RadioQuality.FAIR:
            # Occasional static
            if random.random() < 0.1:
                processed = f"[brief static] {processed}"
        
        return processed
    
    def simulate_transmission_delay(self, quality: RadioQuality) -> float:
        """
        Get transmission delay in seconds based on quality
        
        Returns:
            Delay in seconds
        """
        delays = {
            RadioQuality.EXCELLENT: 0.0,
            RadioQuality.GOOD: 0.03,
            RadioQuality.FAIR: 0.1,
            RadioQuality.POOR: 0.2,
            RadioQuality.VERY_POOR: 0.3
        }
        return delays.get(quality, 0.1)
    
    def get_quality_description(self, quality: RadioQuality) -> str:
        """Get human-readable quality description"""
        descriptions = {
            RadioQuality.EXCELLENT: "Excellent - Clear signal",
            RadioQuality.GOOD: "Good - Minor static",
            RadioQuality.FAIR: "Fair - Some static and distortion",
            RadioQuality.POOR: "Poor - Heavy static, possible word loss",
            RadioQuality.VERY_POOR: "Very Poor - Severe static, frequent word loss"
        }
        return descriptions.get(quality, "Unknown quality")

