"""
Ollama Client for AI-powered ATC responses
Handles communication with Ollama API for generating intelligent ATC replies
"""

import requests
import json
import time
from typing import Dict, List, Optional, Any
import logging

from utils.trainee_situation import atc_prompt_hint_from_pilot_transmission

class OllamaClient:
    """Client for interacting with Ollama API for ATC responses"""

    # Default timeouts: generation can be slow (especially on CPU)
    DEFAULT_GENERATE_TIMEOUT = 300  # 5 minutes for /api/generate
    DEFAULT_CHECK_TIMEOUT = 10     # seconds for availability/tags

    # Smaller models to try when primary model times out or fails (e.g. OOM)
    FALLBACK_MODELS = ["tinyllama", "phi", "qwen2:0.5b", "llama3.2:1b", "llama3.2:3b"]

    def __init__(self, base_url: str = "http://localhost:11434", model: str = "llama2", generate_timeout: Optional[int] = None):
        """
        Initialize the Ollama client
        
        Args:
            base_url: Ollama API base URL (default: http://localhost:11434)
            model: Model name to use for generation (default: llama2)
            generate_timeout: Timeout in seconds for generation requests (default: 120).
                              Increase if Ollama often times out (e.g. slow hardware).
        """
        self.base_url = base_url.rstrip('/')
        self.model = model
        self.generate_timeout = generate_timeout if generate_timeout is not None else self.DEFAULT_GENERATE_TIMEOUT
        self.session = requests.Session()
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Test connection on initialization
        self._test_connection()
    
    def _test_connection(self) -> bool:
        """Test connection to Ollama API"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=self.DEFAULT_CHECK_TIMEOUT)
            if response.status_code == 200:
                self.logger.info(f"Successfully connected to Ollama at {self.base_url}")
                return True
            else:
                self.logger.warning(f"Ollama API returned status code {response.status_code}")
                return False
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Failed to connect to Ollama: {e}")
            return False
    
    def is_available(self) -> bool:
        """Check if Ollama is available and responding"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags", timeout=self.DEFAULT_CHECK_TIMEOUT)
            return response.status_code == 200
        except:
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available models"""
        try:
            response = self.session.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [model["name"] for model in models]
            return []
        except Exception as e:
            self.logger.error(f"Error getting available models: {e}")
            return []
    
    def generate_atc_response(self, 
                            pilot_message: str,
                            aircraft_info: Dict[str, Any],
                            airport_info: Dict[str, Any],
                            context: List[str] = None,
                            traffic_aircraft: List[Dict[str, Any]] = None,
                            phraseology_standard: str = "ICAO",
                            temperature: float = 0.7) -> str:
        """
        Generate an ATC response using Ollama
        
        Args:
            pilot_message: The pilot's message/request
            aircraft_info: Information about the aircraft (callsign, type, location, etc.)
            airport_info: Information about the airport (runways, taxiways, weather, etc.)
            context: Previous communication history
            temperature: Generation temperature (0.0 to 1.0)
            
        Returns:
            Generated ATC response
        """
        if not self.is_available():
            return self._fallback_response(pilot_message, aircraft_info)

        # Build the prompt with enhanced context
        prompt = self._build_atc_prompt(
            pilot_message,
            aircraft_info,
            airport_info,
            context,
            traffic_aircraft,
            phraseology_standard
        )

        # Try primary model first, then fallback to smaller models before giving up
        models_to_try = [self.model] + [
            m for m in self.FALLBACK_MODELS if m != self.model
        ]

        last_error = None
        for model_name in models_to_try:
            try:
                result = self._generate_with_model(
                    model_name=model_name,
                    prompt=prompt,
                    temperature=temperature,
                    num_predict=200,
                )
                if result is not None:
                    # Enforce phraseology
                    from utils.phraseology_validator import PhraseologyValidator
                    from utils.trainee_situation import repair_conflicting_clearance

                    validator = PhraseologyValidator()
                    result = validator.enforce_phraseology(result)
                    result, _ = repair_conflicting_clearance(result)
                    self.logger.info(f"Generated ATC response with model {model_name}: {result}")
                    return result
            except Exception as e:
                last_error = e
                self.logger.warning(f"Model {model_name} failed: {e}, trying next fallback.")
                continue

        self.logger.error(f"All models failed. Last error: {last_error}")
        return "Please reduce memory usage."

    def _generate_with_model(
        self,
        model_name: str,
        prompt: str,
        temperature: float = 0.7,
        num_predict: int = 200,
    ) -> Optional[str]:
        """Call /api/generate with the given model. Returns cleaned response or None; raises on request error."""
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "top_k": 40,
                "num_predict": num_predict,
                "repeat_penalty": 1.2,
                "stop": ["\n\n", "PILOT:", "ATC:", "END"]
            }
        }
        response = self.session.post(
            f"{self.base_url}/api/generate",
            json=payload,
            timeout=self.generate_timeout
        )
        if response.status_code != 200:
            self.logger.error(f"Ollama API error: {response.status_code} - {response.text}")
            return None
        result = response.json()
        generated_text = result.get("response", "").strip()
        if not generated_text:
            return None
        return self._clean_response(generated_text)

    def generate_from_prompt(
        self,
        prompt: str,
        temperature: float = 0.45,
        num_predict: int = 280,
    ) -> str:
        """
        Run a free-form prompt through Ollama with the same model fallback chain as ATC chat.
        Used for auxiliary tools (e.g. plain-language to pilot radio phraseology).
        """
        if not self.is_available():
            return ""
        models_to_try = [self.model] + [m for m in self.FALLBACK_MODELS if m != self.model]
        last_error = None
        for model_name in models_to_try:
            try:
                result = self._generate_with_model(
                    model_name=model_name,
                    prompt=prompt,
                    temperature=temperature,
                    num_predict=num_predict,
                )
                if result:
                    return result
            except Exception as e:
                last_error = e
                self.logger.warning("Model %s failed: %s, trying next fallback.", model_name, e)
                continue
        self.logger.error("generate_from_prompt failed: %s", last_error)
        return ""

    def _build_atc_prompt(self, 
                         pilot_message: str,
                         aircraft_info: Dict[str, Any],
                         airport_info: Dict[str, Any],
                         context: List[str] = None,
                         traffic_aircraft: List[Dict[str, Any]] = None,
                         phraseology_standard: str = "ICAO") -> str:
        """Build a comprehensive prompt for ATC response generation"""
        
        # Base system prompt with enhanced phraseology enforcement for commercial aviation
        system_prompt = f"""You are an experienced Air Traffic Controller (ATC) at a commercial airport. You must respond to pilot communications in a professional, clear, and concise manner using standard {phraseology_standard} aviation phraseology for commercial aircraft operations.

CRITICAL REQUIREMENTS:
- Use ONLY standard aviation phraseology (roger, wilco, affirmative, negative, cleared, etc.)
- NEVER use informal language (yes, no, ok, got it, please, thanks)
- ALWAYS include the aircraft callsign at the beginning of your response
- Commercial aircraft typically use airline callsigns (e.g., "Singapore 123", "Malaysia 456", not "N123AB")
- Provide clear, unambiguous instructions
- Consider aircraft type (A320, B737, etc.), location, weather, and traffic situation
- Ensure safety and efficiency
- Be professional and concise
- REACT TO THE SITUATION: Your response must match what the pilot is asking for NOW. If they are requesting takeoff, give takeoff clearance or denial. If they are reporting altitude, acknowledge and give the next instruction (e.g. contact next frequency, turn, speed, or traffic). If they are ready to taxi, give taxi instructions. Do not give the same clearance twice.
- PROGRESS THE SCENARIO: Read the communication history. If you (ATC) already gave a specific instruction (e.g. "climb and maintain FL250"), do NOT repeat it. Give the next logical step: e.g. handoff ("Contact departure on 123.45"), traffic call, heading change, or acknowledgment only if that is all that is needed.
- For commercial operations, use flight levels (FL) above transition altitude, feet below
- Use SID/STAR names when applicable (e.g., "Cleared via SID EKIKA 1A", "Descend via STAR KEPAS 1A")
- Use waypoint names in clearances when following procedures

PHRASEOLOGY RULES:
- Use "roger" for acknowledgment, "wilco" for will comply
- Use "affirmative" for yes, "negative" for no
- Use "cleared" for clearances (cleared for takeoff, cleared to land, cleared to taxi, cleared via SID/STAR)
- Use "maintain" for altitude/heading/speed instructions (e.g., "Maintain flight level 250", "Maintain 3000 feet")
- Use "contact" for frequency changes (e.g., "Contact departure on 123.45")
- Always specify runway numbers (e.g., "runway 02L" not just "runway")
- Use "pushback approved" for gate pushback clearances
- Use "start approved" for engine start clearances
- For commercial aircraft: Use "climb and maintain" or "descend and maintain" with flight levels/altitudes
- Use "cross [waypoint] at [altitude]" for altitude restrictions
- Use "reduce speed to [speed] knots" for speed restrictions
- Use "hold at [waypoint]" for holding pattern instructions
- Use "go around" or "missed approach" procedures when needed

SCENARIO PROGRESSION (IMPORTANT):
- Read the RECENT COMMUNICATION HISTORY. Identify the LAST ATC instruction you gave. Do NOT repeat that instruction.
- Respond only to the CURRENT pilot message. If the pilot is merely acknowledging, respond with the next step (e.g. frequency change, or "roger" if nothing else is needed). If the pilot is requesting something new, give that clearance or instruction. Vary your responses naturally according to phase of flight and what was already said.
- Vary wording where phraseology allows (e.g. "Roger" vs "Wilco", different but correct runway/frequency mentions) so responses feel natural and situation-specific, not copy-pasted.
- ANTI-LOOP: If you asked the pilot for information (altitude, heading, intentions) and they answered in the CURRENT message or clearly confirmed, acknowledge and proceed (e.g. issue descend/climb clearance if requested, traffic, frequency, or "standby"). Do NOT send the same question twice in a row.
- Stay task-focused: no counseling, empathy, or unrelated small talk (e.g. do not comment on "severe weather" unless issuing a weather-related instruction or hazard).
- FREQUENCY / SECTOR: If the pilot simulates switching frequency after you said "contact [unit] on [freq]", you are still the handing-off unit until they call the next unit — acknowledge briefly (e.g. Wilco, good day). When they then call "Departure" or "Approach" (with you / checking in), you are that radar unit — use radar contact / SID climb / heading or level instructions, not generic tower holding phraseology unless the scenario is still tower.

Respond with ONLY the ATC instruction/response, no explanations or additional text."""

        pilot_training = (aircraft_info.get("training_mode") or "").lower() == "pilot"
        pilot_training_block = ""
        if pilot_training:
            pilot_training_block = """
PILOT_TRAINING_MODE (MANDATORY):
- The pilot is a trainee practicing radio technique.
- If your LAST clearance to them required a readback (cleared for takeoff/land, taxi, hold short, SID/STAR, runway assignment, squawk, etc.) and they reply with only an acknowledgment (e.g. "Roger", "Wilco", "Copy") without repeating those items, respond with "negative" (or equivalent) and tell them they must read back the clearance elements — do NOT repeat the entire clearance again as if it were new traffic; coaching only.
- If their readback is correct and complete, acknowledge with "Roger, readback correct" or similar and then continue the scenario (next frequency, next instruction, or standby as appropriate).
- ACCEPT EQUIVALENT PHRASEOLOGY: "cleared to land" and "cleared for landing" are the same intent; "contact ground on 134.9" matches "contact ground control on frequency 134.9"; minor word order changes are fine if runway, frequency, and clearance type are correct.
- When the readback is adequate, do NOT repeat the same handoff or frequency instruction again; a brief "Roger, readback correct" (or "Wilco") is enough unless something was actually wrong.
- Radiotelephony (e.g. "Singapore 123") is an acceptable readback for an ICAO-style callsign (e.g. "SIA123") when the flight number matches.
- INFORMATION REQUESTS: If you asked for altitude/heading/status and the pilot provided it (or confirmed), do NOT ask the same question again. Give the next instruction or "say again" only if the transmission was unreadable.
- NO CHIT-CHAT: Do not offer condolences, therapy-style empathy, or non-operational remarks; keep transmissions brief and standard phraseology.
"""

        # Build context information
        context_info = pilot_training_block + f"""
AIRPORT INFORMATION:
- Name: {airport_info.get('name', 'Unknown')}
- ICAO: {airport_info.get('icao', 'Unknown')}
- Runways: {', '.join(airport_info.get('runways', []))}
- Taxiways: {', '.join(airport_info.get('taxiways', []))}
- Weather: Wind {airport_info.get('wind', 'Unknown')}, Visibility {airport_info.get('visibility', 'Unknown')}, Ceiling {airport_info.get('ceiling', 'Unknown')}

AIRCRAFT INFORMATION (use this callsign and type for your response; they are current for this request):
- Callsign: {aircraft_info.get('callsign', 'Unknown')}
- Type: {aircraft_info.get('aircraft_type', 'Unknown')}
- Location: {aircraft_info.get('location', 'Unknown')}
- Status: {aircraft_info.get('status', 'Unknown')}
- Squawk: {aircraft_info.get('squawk_code', '1200')}
- Altitude: {aircraft_info.get('altitude', 'N/A')}
- Heading: {aircraft_info.get('heading', 'N/A')}
"""
        last_clear = (aircraft_info.get("last_atc_clearance") or "").strip()
        if last_clear:
            context_info += (
                "\nLAST SUBSTANTIVE CLEARANCE YOU (ATC) ALREADY ISSUED TO THIS AIRCRAFT "
                "(do not repeat the same clearance; if the pilot is only reading back, say roger/readback correct):\n"
                f'"{last_clear}"\n'
            )
        
        # Add traffic information if available
        if traffic_aircraft:
            context_info += "\nTRAFFIC INFORMATION:\n"
            for traffic in traffic_aircraft:
                context_info += f"- {traffic.get('callsign', 'Unknown')} ({traffic.get('aircraft_type', 'Unknown')}) "
                context_info += f"at {traffic.get('position', 'Unknown')}"
                if traffic.get('altitude'):
                    context_info += f", altitude {traffic.get('altitude')}"
                context_info += "\n"
        
        # Add scenario information if available
        if 'scenario' in airport_info:
            scenario = airport_info['scenario']
            context_info += "\nSCENARIO INFORMATION:\n"
            context_info += f"- Type: {scenario.get('type', 'Unknown')}\n"
            context_info += f"- Name: {scenario.get('name', 'Unknown')}\n"
            if scenario.get('objectives'):
                context_info += f"- Objectives: {', '.join(scenario.get('objectives', []))}\n"
            context_info += "\n"
        
        # Add recent context if available
        context_info += "\nRECENT COMMUNICATION HISTORY (read this to understand what has already happened):\n"
        last_atc = None
        if context:
            for msg in context[-10:]:  # Last 10 messages for better context
                context_info += f"- {msg}\n"
                if "ATC:" in msg:
                    last_atc = msg.split("ATC:", 1)[-1].strip()
        else:
            context_info += "- No recent communication history\n"
        
        if last_atc:
            context_info += f"\nLAST ATC INSTRUCTION (do not repeat this; give the next step or a different response): \"{last_atc}\"\n"

        tx_hint = atc_prompt_hint_from_pilot_transmission(pilot_message)
        if tx_hint:
            context_info += f"\n{tx_hint}\n"

        # Add the current pilot message
        context_info += f"""
CURRENT PILOT MESSAGE:
PILOT: {pilot_message}

Respond to this message only. React to what the pilot is saying or requesting. Do not repeat your last instruction. Use standard phraseology and include the callsign.

ATC RESPONSE:"""

        return system_prompt + context_info
    
    def _clean_response(self, response: str) -> str:
        """Clean and format the generated response"""
        # Remove any leading/trailing whitespace
        response = response.strip()
        
        # Remove any "ATC:" prefixes if they exist
        if response.startswith("ATC:"):
            response = response[4:].strip()
        
        # Remove any quotes
        response = response.strip('"\'')
        
        # Ensure it ends with a period if it doesn't already
        if response and not response.endswith(('.', '!')):
            response += '.'
        
        return response
    
    def _fallback_response(self, pilot_message: str, aircraft_info: Dict[str, Any]) -> str:
        """Generate a fallback response when Ollama is not available"""
        callsign = aircraft_info.get('callsign', 'Aircraft')
        
        # Simple keyword-based fallback responses
        pilot_message_lower = pilot_message.lower()
        
        if any(word in pilot_message_lower for word in ['request', 'permission', 'clearance']):
            if 'takeoff' in pilot_message_lower:
                return f"{callsign}, cleared for takeoff."
            elif 'taxi' in pilot_message_lower:
                return f"{callsign}, taxi to runway via taxiway A."
            elif 'landing' in pilot_message_lower:
                return f"{callsign}, cleared to land runway 27."
        
        elif 'ready' in pilot_message_lower:
            return f"{callsign}, roger, standby."
        
        elif 'contact' in pilot_message_lower:
            return f"{callsign}, contact ground on 121.9."
        
        else:
            return f"{callsign}, roger."
    
    def generate_atis_message(self, airport_info: Dict[str, Any]) -> str:
        """Generate ATIS information using Ollama"""
        if not self.is_available():
            return self._fallback_atis(airport_info)
        
        prompt = f"""Generate a standard ATIS (Automatic Terminal Information Service) message for the following airport:

Airport: {airport_info.get('name', 'Unknown')} ({airport_info.get('icao', 'Unknown')})
Runways: {', '.join(airport_info.get('runways', []))}
Wind: {airport_info.get('wind', 'Unknown')}
Visibility: {airport_info.get('visibility', 'Unknown')}
Ceiling: {airport_info.get('ceiling', 'Unknown')}

Generate a concise ATIS message in standard format with a designator (A, B, C, etc.)."""

        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "top_p": 0.9,
                    "num_predict": 150,
                    "stop": ["\n\n", "END"]
                }
            }
            
            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.generate_timeout
            )
            
            if response.status_code == 200:
                result = response.json()
                atis_text = result.get("response", "").strip()
                return atis_text if atis_text else self._fallback_atis(airport_info)
            else:
                return self._fallback_atis(airport_info)
                
        except Exception as e:
            self.logger.error(f"Error generating ATIS: {e}")
            return self._fallback_atis(airport_info)
    
    def decode_atis(self, atis_message: str) -> Dict[str, Any]:
        """Decode an ATIS message using Ollama"""
        if not self.is_available():
            # If Ollama is not available, return fallback decoded structure
            from utils.atis_decoder import ATISDecoder
            decoder = ATISDecoder()
            return decoder.decode_atis(atis_message)

        prompt = (
            "Parse and extract the following ATIS message into a structured JSON object with keys: "
            "airport, information, time, runway_info, weather (wind, visibility, clouds, temperature if given), "
            "altimeter, frequency, remarks. Use ISO 8601 for time if present. "
            "Return ONLY the JSON. ATIS message:\n"
            f"{atis_message.strip()}"
        )
        try:
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.2,
                    "top_p": 0.9,
                    "num_predict": 300,
                    "stop": ["\n\n", "END"]
                }
            }

            response = self.session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.generate_timeout,
            )
            if response.status_code == 200:
                import json
                result = response.json()
                atis_json_str = result.get("response", "").strip()
                # Try to extract json object safely
                try:
                    decoded = json.loads(atis_json_str)
                    return decoded
                except Exception:
                    # Sometimes LLMs add preamble/text, try to extract JSON
                    import re
                    match = re.search(r'\{.*\}', atis_json_str, re.DOTALL)
                    if match:
                        return json.loads(match.group(0))
                    else:
                        self.logger.error("Ollama decode_atis did not return JSON, falling back.")
            else:
                self.logger.error(f"Ollama ATIS decode failed with status {response.status_code}")

        except Exception as e:
            self.logger.error(f"Error decoding ATIS with Ollama: {e}")

        # If Ollama fails, fall back to local decoder
        from utils.atis_decoder import ATISDecoder
        decoder = ATISDecoder()
        return decoder.decode_atis(atis_message)
    
    def _fallback_atis(self, airport_info: Dict[str, Any]) -> str:
        """Generate a fallback ATIS message"""
        icao = airport_info.get('icao', 'Unknown')
        wind = airport_info.get('wind', 'Calm')
        visibility = airport_info.get('visibility', '10 miles')
        ceiling = airport_info.get('ceiling', 'Clear')
        runways = airport_info.get('runways', ['27'])
        
        return f"ATIS {icao} Information Alpha. Wind {wind}. Visibility {visibility}. Ceiling {ceiling}. Runway {runways[0]} in use. Advise on initial contact you have information Alpha."
