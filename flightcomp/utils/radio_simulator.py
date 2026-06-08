"""
Radio Simulator for Pilot Training
Provides realistic radio communication simulation with audio effects
"""

import time
import threading
import queue
from typing import Optional, Callable, List, Dict, Any
from dataclasses import dataclass, field
from enum import Enum
import random
from utils.logging_config import get_logger

logger = get_logger(__name__)


class RadioQuality(Enum):
    """Radio signal quality levels"""
    EXCELLENT = "excellent"
    GOOD = "good"
    FAIR = "fair"
    POOR = "poor"
    VERY_POOR = "very_poor"


@dataclass
class RadioMessage:
    """Represents a radio message"""
    sender: str
    message: str
    timestamp: float
    quality: RadioQuality = RadioQuality.GOOD
    frequency: Optional[str] = None
    duration: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "sender": self.sender,
            "message": self.message,
            "timestamp": self.timestamp,
            "quality": self.quality.value,
            "frequency": self.frequency,
            "duration": self.duration
        }


class RadioSimulator:
    """Simulates realistic radio communications"""
    
    def __init__(self, speech_engine=None):
        """
        Initialize radio simulator
        
        Args:
            speech_engine: Optional speech engine for text-to-speech
        """
        self.speech_engine = speech_engine
        self.message_queue = queue.Queue()
        self.message_history: List[RadioMessage] = []
        self.is_playing = False
        self.quality = RadioQuality.GOOD
        self.volume = 1.0
        self.enabled = True
        self.callbacks: Dict[str, Callable] = {}
        
        # Audio effect parameters
        self.static_level = 0.1
        self.distortion_level = 0.05
        self.delay_ms = 50
    
    def set_quality(self, quality: RadioQuality):
        """Set radio signal quality"""
        self.quality = quality
        
        # Adjust parameters based on quality
        if quality == RadioQuality.EXCELLENT:
            self.static_level = 0.0
            self.distortion_level = 0.0
            self.delay_ms = 0
        elif quality == RadioQuality.GOOD:
            self.static_level = 0.05
            self.distortion_level = 0.02
            self.delay_ms = 30
        elif quality == RadioQuality.FAIR:
            self.static_level = 0.15
            self.distortion_level = 0.08
            self.delay_ms = 100
        elif quality == RadioQuality.POOR:
            self.static_level = 0.3
            self.distortion_level = 0.15
            self.delay_ms = 200
        else:  # VERY_POOR
            self.static_level = 0.5
            self.distortion_level = 0.25
            self.delay_ms = 300
    
    def transmit(self, sender: str, message: str, frequency: Optional[str] = None):
        """
        Transmit a radio message
        
        Args:
            sender: Callsign or identifier of sender
            message: Message text
            frequency: Radio frequency (optional)
        """
        if not self.enabled:
            return
        
        radio_message = RadioMessage(
            sender=sender,
            message=message,
            timestamp=time.time(),
            quality=self.quality,
            frequency=frequency
        )
        
        # Add to history
        self.message_history.append(radio_message)
        # Keep only last 100 messages
        if len(self.message_history) > 100:
            self.message_history = self.message_history[-100:]
        
        # Queue for playback
        self.message_queue.put(radio_message)
        
        # Notify callback
        if "message_received" in self.callbacks:
            self.callbacks["message_received"](radio_message)
        
        # Start playback if not already playing
        if not self.is_playing:
            self._start_playback()
    
    def _start_playback(self):
        """Start playing queued messages"""
        if self.is_playing:
            return
        
        self.is_playing = True
        playback_thread = threading.Thread(target=self._playback_worker, daemon=True)
        playback_thread.start()
    
    def _playback_worker(self):
        """Worker thread for playing messages"""
        while True:
            try:
                # Get message from queue with timeout
                try:
                    message = self.message_queue.get(timeout=0.1)
                except queue.Empty:
                    # No more messages, stop playback
                    self.is_playing = False
                    break
                
                # Simulate radio delay
                if self.delay_ms > 0:
                    time.sleep(self.delay_ms / 1000.0)
                
                # Apply radio effects to message text
                processed_message = self._apply_radio_effects(message)
                
                # Play message using speech engine if available
                if self.speech_engine and self.speech_engine.is_speech_available():
                    # Format message with sender
                    full_message = f"{message.sender}, {processed_message}"
                    self.speech_engine.speak(full_message)
                    
                    # Estimate duration (rough calculation: ~150 words per minute)
                    word_count = len(full_message.split())
                    message.duration = (word_count / 150.0) * 60.0
                else:
                    # No speech engine, just log
                    logger.debug("[RADIO] %s: %s", message.sender, processed_message)
                    message.duration = 2.0  # Default duration
                
                # Notify playback complete
                if "message_played" in self.callbacks:
                    self.callbacks["message_played"](message)
                
                # Small delay between messages
                time.sleep(0.5)
                
            except Exception as e:
                logger.warning("Error in radio playback: %s", e)
                self.is_playing = False
                break
    
    def _apply_radio_effects(self, message: RadioMessage) -> str:
        """
        Apply radio effects to message text
        
        Returns:
            Processed message with effects applied
        """
        text = message.message
        
        # Apply quality-based effects
        if self.quality == RadioQuality.POOR or self.quality == RadioQuality.VERY_POOR:
            # Simulate word loss or distortion
            words = text.split()
            if random.random() < 0.1:  # 10% chance of word loss
                if len(words) > 1:
                    words.pop(random.randint(0, len(words) - 1))
                text = " ".join(words)
            
            # Add static indicators
            if random.random() < 0.2:  # 20% chance of static
                text = f"[static] {text} [static]"
        
        return text
    
    def get_message_history(self, limit: int = 50) -> List[RadioMessage]:
        """Get recent message history"""
        return self.message_history[-limit:]
    
    def clear_history(self):
        """Clear message history"""
        self.message_history.clear()
    
    def register_callback(self, event: str, callback: Callable):
        """Register callback for radio events"""
        self.callbacks[event] = callback
    
    def enable(self):
        """Enable radio simulator"""
        self.enabled = True
    
    def disable(self):
        """Disable radio simulator"""
        self.enabled = False
    
    def set_volume(self, volume: float):
        """Set radio volume (0.0 to 1.0)"""
        self.volume = max(0.0, min(1.0, volume))
        if self.speech_engine:
            # Adjust speech engine volume if supported
            pass


class AudioEffects:
    """Audio effects for radio simulation"""
    
    @staticmethod
    def add_static(audio_data, static_level: float = 0.1):
        """Add static noise to audio"""
        # In a real implementation, this would process audio samples
        # For now, this is a placeholder
        return audio_data
    
    @staticmethod
    def add_distortion(audio_data, distortion_level: float = 0.05):
        """Add distortion to audio"""
        # In a real implementation, this would process audio samples
        return audio_data
    
    @staticmethod
    def add_delay(audio_data, delay_ms: int = 50):
        """Add delay/echo effect to audio"""
        # In a real implementation, this would process audio samples
        return audio_data
    
    @staticmethod
    def simulate_radio_quality(audio_data, quality: RadioQuality):
        """Apply radio quality effects to audio"""
        if quality == RadioQuality.EXCELLENT:
            return audio_data
        elif quality == RadioQuality.GOOD:
            return AudioEffects.add_static(audio_data, 0.05)
        elif quality == RadioQuality.FAIR:
            return AudioEffects.add_static(
                AudioEffects.add_distortion(audio_data, 0.05), 
                0.15
            )
        elif quality == RadioQuality.POOR:
            return AudioEffects.add_delay(
                AudioEffects.add_static(
                    AudioEffects.add_distortion(audio_data, 0.15),
                    0.3
                ),
                200
            )
        else:  # VERY_POOR
            return AudioEffects.add_delay(
                AudioEffects.add_static(
                    AudioEffects.add_distortion(audio_data, 0.25),
                    0.5
                ),
                300
            )

