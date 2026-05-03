"""
AI Response Handler for ATC System
Integrates Ollama AI with the ATC window for intelligent responses
"""

import threading
import time
import re
from collections import deque
from typing import Dict, List, Optional, Any, Callable
from utils.ollama_client import OllamaClient
from utils.trainee_situation import (
    repair_conflicting_clearance,
    normalize_for_dedupe,
    pilot_message_sounds_like_readback,
    clearance_requires_readback,
    pilot_ack_only,
    readback_training_reminder_line,
    pilot_answered_information_request_about_altitude,
    pilot_requests_descend_maintain_fl,
    pilot_requests_climb_maintain_fl,
    pilot_indicates_frequency_change_compliance,
    pilot_sector_initial_checkin,
)
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

        # Latest AI request id (for stale-callback suppression in UI)
        self._dispatch_seq: int = 0
        # Last substantive ATC line issued to the pilot (for prompt + dedupe)
        self._last_substantive_atc: str = ""
        # Last full ATC line (normalized) in pilot training — catches repeat questions
        # that are not "substantive" clearances and therefore bypass _dedupe_clearance_response.
        self._last_pilot_mode_atc_norm: str = ""
        self._pilot_recent_atc_norms: deque[str] = deque(maxlen=10)
        
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

    @property
    def last_dispatch_seq(self) -> int:
        """Monotonic id of the most recently started generate_atc_response call."""
        return self._dispatch_seq

    def generate_response(self, prompt: str) -> str:
        """Synchronous single-shot generation for helper prompts (e.g. readbacks, phraseology translation)."""
        if not self.is_enabled or not self.ollama_client:
            return ""
        try:
            return self.ollama_client.generate_from_prompt(
                prompt.strip(),
                temperature=self.temperature,
                num_predict=280,
            )
        except Exception as e:
            self.logger.error("generate_response failed: %s", e)
            return ""
    
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
            Generated ATC response (stub text when AI runs async; full text when AI is off)
        """
        self._dispatch_seq += 1
        request_id = self._dispatch_seq
        self.add_to_history("PILOT", pilot_message)

        if not self.is_enabled or not self.ollama_client:
            training_mode = (aircraft_info.get("training_mode") or "").lower()
            last_sub = self._last_substantive_atc
            if (
                training_mode == "pilot"
                and last_sub
                and clearance_requires_readback(last_sub)
                and pilot_ack_only(pilot_message)
            ):
                callsign = aircraft_info.get("callsign", "Aircraft")
                ai_response = self._sanitize_phraseology(
                    readback_training_reminder_line(callsign), aircraft_info
                )
            elif sc := self._short_circuit_frequency_handoff_ack(
                pilot_message, aircraft_info
            ):
                ai_response = self._sanitize_phraseology(sc, aircraft_info)
            else:
                ai_response = self._generate_fallback_response(
                    pilot_message, aircraft_info, response_type, airport_info
                )
                ai_response, _ = repair_conflicting_clearance(ai_response or "")
                ai_response = self._sanitize_phraseology(ai_response, aircraft_info)
                ai_response = self._dedupe_clearance_response(
                    ai_response, pilot_message, aircraft_info
                )
                ai_response = self._squash_pilot_mode_duplicate_atc_output(
                    ai_response, pilot_message, aircraft_info
                )
            self.add_to_history("ATC", ai_response)
            self._note_pilot_mode_atc_norm(ai_response, aircraft_info)
            if self._is_substantive_atc(ai_response):
                self._last_substantive_atc = ai_response
            if self.ui_update_callback:
                self.ui_update_callback(
                    ai_response,
                    standby_index=standby_index,
                    request_id=request_id,
                )
            return ai_response

        response_thread = threading.Thread(
            target=self._generate_response_async,
            args=(pilot_message, aircraft_info, airport_info, response_type, standby_index, request_id),
        )
        response_thread.daemon = True
        response_thread.start()

        callsign = aircraft_info.get("callsign", "Aircraft")
        return f"{callsign}, roger, standby."
    
    def _generate_response_async(self,
                                 pilot_message: str,
                                 aircraft_info: Dict[str, Any],
                                 airport_info: Dict[str, Any],
                                 response_type: str,
                                 standby_index: Optional[int] = None,
                                 request_id: int = 0):
        """Generate response asynchronously and update UI"""
        try:
            training_mode = (aircraft_info.get("training_mode") or "").lower()
            last_sub = self._last_substantive_atc

            # Pilot training: teach readback discipline instead of repeating clearances
            if (
                training_mode == "pilot"
                and last_sub
                and clearance_requires_readback(last_sub)
                and pilot_ack_only(pilot_message)
            ):
                callsign = aircraft_info.get("callsign", "Aircraft")
                ai_response = readback_training_reminder_line(callsign)
                ai_response = self._sanitize_phraseology(ai_response, aircraft_info)
                self.add_to_history("ATC", ai_response)
                self._note_pilot_mode_atc_norm(ai_response, aircraft_info)
                if self.ui_update_callback:
                    self.ui_update_callback(
                        ai_response,
                        standby_index=standby_index,
                        request_id=request_id,
                    )
                return

            if sc := self._short_circuit_frequency_handoff_ack(pilot_message, aircraft_info):
                ai_response = self._sanitize_phraseology(sc, aircraft_info)
                self.add_to_history("ATC", ai_response)
                self._note_pilot_mode_atc_norm(ai_response, aircraft_info)
                if self.ui_update_callback:
                    self.ui_update_callback(
                        ai_response,
                        standby_index=standby_index,
                        request_id=request_id,
                    )
                return

            # Get recent context (last 10 messages for better scenario progression)
            context = self.communication_history[-10:] if self.communication_history else []

            # Get traffic information if available
            traffic_aircraft = []
            if "traffic" in airport_info:
                traffic_aircraft = airport_info.get("traffic", [])

            ai_aircraft_info = dict(aircraft_info)
            ai_aircraft_info["last_atc_clearance"] = self._last_substantive_atc

            # Generate AI response with enhanced context
            ai_response = self.ollama_client.generate_atc_response(
                pilot_message=pilot_message,
                aircraft_info=ai_aircraft_info,
                airport_info=airport_info,
                context=context,
                traffic_aircraft=traffic_aircraft,
                phraseology_standard=self.config.get("phraseology_standard", "ICAO"),
                temperature=self.temperature
            )
            ai_response, _repair_notes = repair_conflicting_clearance(ai_response or "")
            ai_response = self._sanitize_phraseology(ai_response, aircraft_info)
            ai_response = self._dedupe_clearance_response(
                ai_response, pilot_message, aircraft_info
            )
            ai_response = self._squash_pilot_mode_duplicate_atc_output(
                ai_response, pilot_message, aircraft_info
            )

            # Add AI response to history
            self.add_to_history("ATC", ai_response)
            if self._is_substantive_atc(ai_response):
                self._last_substantive_atc = ai_response
            self._note_pilot_mode_atc_norm(ai_response, aircraft_info)

            # Update UI with the generated response (pass standby_index for in-place replace)
            if self.ui_update_callback:
                self.ui_update_callback(
                    ai_response,
                    standby_index=standby_index,
                    request_id=request_id,
                )
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
            fallback, _ = repair_conflicting_clearance(fallback)
            fallback = self._sanitize_phraseology(fallback, aircraft_info)
            fallback = self._dedupe_clearance_response(
                fallback, pilot_message, aircraft_info
            )
            fallback = self._squash_pilot_mode_duplicate_atc_output(
                fallback, pilot_message, aircraft_info
            )
            self._note_pilot_mode_atc_norm(fallback, aircraft_info)
            if self.ui_update_callback:
                self.ui_update_callback(
                    fallback,
                    standby_index=standby_index,
                    request_id=request_id,
                )
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

    def _short_circuit_frequency_handoff_ack(
        self, pilot_message: str, aircraft_info: Dict[str, Any]
    ) -> Optional[str]:
        """Deterministic tower reply when the pilot only states/simulates switching frequency."""
        if (aircraft_info.get("training_mode") or "").lower() != "pilot":
            return None
        if not pilot_indicates_frequency_change_compliance(pilot_message):
            return None
        cs = aircraft_info.get("callsign", "Aircraft")
        return f"{cs}, wilco, good day."

    def _note_pilot_mode_atc_norm(
        self, atc_line: str, aircraft_info: Dict[str, Any]
    ) -> None:
        if (aircraft_info.get("training_mode") or "").lower() != "pilot":
            return
        if atc_line and atc_line.strip():
            n = normalize_for_dedupe(atc_line)
            self._last_pilot_mode_atc_norm = n
            if len(n) >= 20:
                self._pilot_recent_atc_norms.append(n)

    def _squash_pilot_mode_duplicate_atc_output(
        self,
        response: str,
        pilot_message: str,
        aircraft_info: Dict[str, Any],
    ) -> str:
        """
        If the model repeats the exact same ATC line as last time (common when
        `_last_substantive_atc` did not advance because the line was only a question),
        replace with standard phraseology instead of looping.
        """
        if (aircraft_info.get("training_mode") or "").lower() != "pilot":
            return response
        if not response or not response.strip():
            return response
        n_new = normalize_for_dedupe(response)
        if len(n_new) < 20:
            return response
        prev = self._last_pilot_mode_atc_norm
        infoish = bool(
            re.search(
                r"(altitude|heading|what|confirm|flight\s*level|level|position|report|"
                r"emergency|weather|procedure)",
                n_new,
            )
        )
        seen_again = n_new in self._pilot_recent_atc_norms
        consecutive_same = bool(prev and n_new == prev)
        if not consecutive_same and not (infoish and seen_again):
            return response
        cs = aircraft_info.get("callsign", "Aircraft")
        pl = (pilot_message or "").strip()
        if re.fullmatch(r"what[\s?!.'-]*", pl, re.I):
            return self._sanitize_phraseology(
                f"{cs}, say again your altitude and request.", aircraft_info
            )
        if pilot_answered_information_request_about_altitude(pl):
            fl_d = pilot_requests_descend_maintain_fl(pl)
            if fl_d:
                return self._sanitize_phraseology(
                    f"{cs}, roger, descend and maintain flight level {fl_d}.",
                    aircraft_info,
                )
            fl_c = pilot_requests_climb_maintain_fl(pl)
            if fl_c:
                return self._sanitize_phraseology(
                    f"{cs}, roger, climb and maintain flight level {fl_c}.",
                    aircraft_info,
                )
            return self._sanitize_phraseology(
                f"{cs}, roger, standby for further instructions.", aircraft_info
            )
        return self._sanitize_phraseology(f"{cs}, say again.", aircraft_info)

    def _is_substantive_atc(self, msg: str) -> bool:
        if not msg or len(msg.strip()) < 12:
            return False
        low = msg.lower()
        if re.match(r"^[\w\s]+,\s*roger\.?$", msg.strip(), re.I):
            return False
        if "readback correct" in low:
            return False
        return bool(
            re.search(
                r"\b(cleared|taxi|line up|hold short|contact\s+\w+|"
                r"maintain|climb|descend|turn|squawk|pushback|start)\b",
                low,
            )
        )

    def _dedupe_clearance_response(
        self, response: str, pilot_message: str, aircraft_info: Dict[str, Any]
    ) -> str:
        """If the model repeats the last substantive clearance, shorten to an acknowledgment."""
        callsign = aircraft_info.get("callsign", "Aircraft")
        prev = self._last_substantive_atc
        if not prev or not response:
            return response
        n_prev = normalize_for_dedupe(prev)
        n_new = normalize_for_dedupe(response)
        if len(n_prev) < 24 or len(n_new) < 24:
            return response
        if n_prev != n_new:
            return response

        if pilot_message_sounds_like_readback(pilot_message):
            return f"{callsign}, roger, readback correct."
        return f"{callsign}, roger."

    def _generate_fallback_response(self, 
                                  pilot_message: str,
                                  aircraft_info: Dict[str, Any],
                                  response_type: str,
                                  airport_info: Optional[Dict[str, Any]] = None) -> str:
        """Generate a fallback response when AI is not available"""
        callsign = aircraft_info.get('callsign', 'Aircraft')
        pilot_message_lower = pilot_message.lower()
        if pilot_indicates_frequency_change_compliance(pilot_message):
            return f"{callsign}, wilco, good day."
        sector = pilot_sector_initial_checkin(pilot_message)
        if sector in ("departure", "approach", "center", "radar"):
            return (
                f"{callsign}, radar contact, climb via SID unless otherwise instructed."
            )
        if sector in ("tower", "ground", "delivery"):
            return f"{callsign}, roger, go ahead."
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
        self._last_substantive_atc = ""
        self._last_pilot_mode_atc_norm = ""
        self._pilot_recent_atc_norms.clear()
    
    def get_history(self) -> List[str]:
        """Get communication history"""
        return self.communication_history.copy()
