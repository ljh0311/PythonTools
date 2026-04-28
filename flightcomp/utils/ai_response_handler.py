"""
AI Response Handler for ATC System
Integrates Ollama AI with the ATC window for intelligent responses
"""

import threading
import time
from typing import Dict, List, Optional, Any, Callable
from utils.ollama_client import OllamaClient
import logging

class AIResponseHandler:
    """Handles AI-powered responses for the ATC system"""
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the AI response handler
        
        Args:
            config: Configuration dictionary containing AI settings
        """
        self.config = config
        self.ollama_client = None
        self.is_enabled = config.get("ai_enabled", True)
        self.model = config.get("ai_model", "llama2")
        self.base_url = config.get("ollama_url", "http://localhost:11434")
        self.temperature = config.get("ai_temperature", 0.7)
        
        # Communication history for context
        self.communication_history: List[str] = []
        self.max_history = 20
        
        # Callback for updating UI
        self.ui_update_callback: Optional[Callable] = None
        
        # Initialize logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Initialize Ollama client if enabled
        if self.is_enabled:
            self._initialize_ollama()
    
    def _initialize_ollama(self):
        """Initialize the Ollama client"""
        try:
            self.ollama_client = OllamaClient(
                base_url=self.base_url,
                model=self.model
            )
            
            if self.ollama_client.is_available():
                self.logger.info(f"Ollama AI initialized successfully with model: {self.model}")
            else:
                self.logger.warning("Ollama is not available. AI responses will use fallback mode.")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize Ollama: {e}")
            self.ollama_client = None
    
    def set_ui_update_callback(self, callback: Callable):
        """Set callback for updating UI when AI responses are generated"""
        self.ui_update_callback = callback
    
    def add_to_history(self, sender: str, message: str):
        """Add a message to the communication history"""
        timestamp = time.strftime("%H:%M:%S")
        history_entry = f"[{timestamp}] {sender}: {message}"
        
        self.communication_history.append(history_entry)
        
        # Keep only the last max_history entries
        if len(self.communication_history) > self.max_history:
            self.communication_history = self.communication_history[-self.max_history:]
    
    def generate_atc_response(self,
                            pilot_message: str,
                            aircraft_info: Dict[str, Any],
                            airport_info: Dict[str, Any],
                            response_type: str = "general",
                            standby_index: Optional[int] = None) -> str:
        """
        Generate an AI-powered ATC response

        Args:
            pilot_message: The pilot's message
            aircraft_info: Aircraft information
            airport_info: Airport information
            response_type: Type of response (general, taxi, takeoff, landing, etc.)
            standby_index: Line index of the placeholder in the log (for in-place replacement).

        Returns:
            Generated ATC response
        """
        if not self.is_enabled or not self.ollama_client:
            return self._generate_fallback_response(pilot_message, aircraft_info, response_type, airport_info)

        # Add pilot message to history
        self.add_to_history("PILOT", pilot_message)

        # Generate response in a separate thread to avoid blocking UI
        response_thread = threading.Thread(
            target=self._generate_response_async,
            args=(pilot_message, aircraft_info, airport_info, response_type, standby_index)
        )
        response_thread.daemon = True
        response_thread.start()

        # Return immediate acknowledgment
        callsign = aircraft_info.get('callsign', 'Aircraft')
        return f"{callsign}, roger, standby."
    
    def _generate_response_async(self,
                                 pilot_message: str,
                                 aircraft_info: Dict[str, Any],
                                 airport_info: Dict[str, Any],
                                 response_type: str,
                                 standby_index: Optional[int] = None):
        """Generate response asynchronously and update UI"""
        try:
            # Get recent context (last 10 messages for better scenario progression)
            context = self.communication_history[-10:] if self.communication_history else []

            # Get traffic information if available
            traffic_aircraft = []
            if "traffic" in airport_info:
                traffic_aircraft = airport_info.get("traffic", [])

            # Generate AI response with enhanced context
            ai_response = self.ollama_client.generate_atc_response(
                pilot_message=pilot_message,
                aircraft_info=aircraft_info,
                airport_info=airport_info,
                context=context,
                traffic_aircraft=traffic_aircraft,
                phraseology_standard=self.config.get("phraseology_standard", "ICAO"),
                temperature=self.temperature
            )
            ai_response = self._sanitize_phraseology(ai_response, aircraft_info)

            # Add AI response to history
            self.add_to_history("ATC", ai_response)

            # Update UI with the generated response (pass standby_index for in-place replace)
            if self.ui_update_callback:
                self.ui_update_callback(ai_response, standby_index=standby_index)
            else:
                self.logger.debug("No UI callback set!")

        except Exception as e:
            self.logger.error(f"Error generating AI response: {e}")
            fallback = self._generate_fallback_response(
                pilot_message,
                aircraft_info,
                response_type,
                airport_info
            )
            if self.ui_update_callback:
                self.ui_update_callback(fallback, standby_index=standby_index)
            else:
                self.logger.debug("No UI callback set for fallback!")

    def _sanitize_phraseology(self, response: str, aircraft_info: Dict[str, Any]) -> str:
        """Apply small phraseology cleanup to AI output."""
        callsign = aircraft_info.get("callsign", "Aircraft")
        if not response:
            return f"{callsign}, roger."

        cleaned = response.strip()
        informal_replacements = {
            "thanks": "roger",
            "thank you": "roger",
            "okay": "roger",
            "ok": "roger",
            "yeah": "affirmative",
            "yep": "affirmative",
        }
        lowered = cleaned.lower()
        for src, target in informal_replacements.items():
            lowered = lowered.replace(src, target)
        cleaned = lowered.capitalize()

        if not cleaned.upper().startswith(callsign.upper()):
            cleaned = f"{callsign}, {cleaned}"

        if not cleaned.endswith("."):
            cleaned += "."

        return cleaned
    
    def _generate_fallback_response(self, 
                                  pilot_message: str,
                                  aircraft_info: Dict[str, Any],
                                  response_type: str,
                                  airport_info: Optional[Dict[str, Any]] = None) -> str:
        """Generate a fallback response when AI is not available"""
        callsign = aircraft_info.get('callsign', 'Aircraft')
        pilot_message_lower = pilot_message.lower()
        runway = "27"
        if airport_info:
            runways = airport_info.get("runways", [])
            if isinstance(runways, list) and runways:
                runway = runways[0]
        
        # Enhanced fallback responses based on message content
        if response_type == "taxi":
            return f"{callsign}, taxi to runway {runway} via taxiway A, hold short runway {runway}."
        if response_type == "takeoff":
            return f"{callsign}, runway {runway}, line up and wait."
        if response_type == "landing":
            return f"{callsign}, runway {runway}, continue approach, report established."

        if 'request' in pilot_message_lower or 'permission' in pilot_message_lower:
            if 'takeoff' in pilot_message_lower:
                return f"{callsign}, cleared for takeoff runway {runway}."
            elif 'taxi' in pilot_message_lower:
                return f"{callsign}, taxi to runway {runway} via taxiway A."
            elif 'landing' in pilot_message_lower:
                return f"{callsign}, cleared to land runway {runway}."
            elif 'pushback' in pilot_message_lower:
                return f"{callsign}, pushback approved."
        
        elif 'ready' in pilot_message_lower:
            if 'departure' in pilot_message_lower:
                return f"{callsign}, cleared for takeoff runway {runway}."
            elif 'taxi' in pilot_message_lower:
                return f"{callsign}, taxi to runway {runway} via taxiway A."
            else:
                return f"{callsign}, roger, standby."
        
        elif 'contact' in pilot_message_lower:
            return f"{callsign}, contact ground on 121.9."
        
        elif 'squawk' in pilot_message_lower:
            return f"{callsign}, squawk 1200."
        
        elif 'position' in pilot_message_lower:
            return f"{callsign}, roger, line up and wait runway {runway}."
        
        elif 'holding' in pilot_message_lower:
            return f"{callsign}, continue holding, expect clearance in 5 minutes."
        
        else:
            return f"{callsign}, roger."
    
    def generate_atis_message(self, airport_info: Dict[str, Any]) -> str:
        """Generate ATIS message using AI"""
        if not self.is_enabled or not self.ollama_client:
            return self._generate_fallback_atis(airport_info)
        
        try:
            return self.ollama_client.generate_atis_message(airport_info)
        except Exception as e:
            self.logger.error(f"Error generating ATIS: {e}")
            return self._generate_fallback_atis(airport_info)
    
    def _generate_fallback_atis(self, airport_info: Dict[str, Any]) -> str:
        """Generate fallback ATIS message"""
        icao = airport_info.get('icao', 'Unknown')
        wind = airport_info.get('wind', 'Calm')
        visibility = airport_info.get('visibility', '10 miles')
        ceiling = airport_info.get('ceiling', 'Clear')
        runways = airport_info.get('runways', ['27'])
        
        return f"ATIS {icao} Information Alpha. Wind {wind}. Visibility {visibility}. Ceiling {ceiling}. Runway {runways[0]} in use. Advise on initial contact you have information Alpha."
    
    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models"""
        if self.ollama_client:
            return self.ollama_client.get_available_models()
        return []
    
    def is_ai_available(self) -> bool:
        """Check if AI is available and working"""
        return (self.is_enabled and 
                self.ollama_client and 
                self.ollama_client.is_available())
    
    def update_config(self, new_config: Dict[str, Any]):
        """Update configuration and reinitialize if needed"""
        old_enabled = self.is_enabled
        old_model = self.model
        old_url = self.base_url
        
        self.config.update(new_config)
        self.is_enabled = new_config.get("ai_enabled", self.is_enabled)
        self.model = new_config.get("ai_model", self.model)
        self.base_url = new_config.get("ollama_url", self.base_url)
        self.temperature = new_config.get("ai_temperature", self.temperature)
        
        # Reinitialize if settings changed
        if (old_enabled != self.is_enabled or 
            old_model != self.model or 
            old_url != self.base_url):
            self._initialize_ollama()
    
    def clear_history(self):
        """Clear communication history"""
        self.communication_history.clear()
    
    def get_history(self) -> List[str]:
        """Get communication history"""
        return self.communication_history.copy()
