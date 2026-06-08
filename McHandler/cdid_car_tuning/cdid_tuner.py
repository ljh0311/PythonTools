"""
CDID Car Tuning Assistant - AI-powered car tuning using Ollama
(Roblox CDID car tuning experience)
"""

import requests
from datetime import datetime
from typing import Dict, List, Optional


class CDIDTuner:
    """CDID car tuning assistant with Ollama integration"""
    
    def __init__(self):
        self.ollama_url = "http://localhost:11434"
        self.model = "llama3.2"  # Default model, can be changed
        
    def check_ollama_connection(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_available_models(self) -> List[str]:
        """Get list of available Ollama models"""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                return [model['name'] for model in models]
        except:
            pass
        return []
    
    def get_tuning_suggestions(
        self,
        car_description: str,
        tuning_goals: str,
        focus_areas: List[str] = None,
        ecu_available: bool = False,
        ecu_stage: Optional[int] = None,
        internal_electronics_available: bool = False,
        internal_electronics_stage: Optional[int] = None,
        turbo_charger: Optional[int] = None,
        boost_per_turbo: Optional[int] = None,
        super_charger: Optional[int] = None,
        super_charger_boost: Optional[int] = None,
        front_diff_power: Optional[int] = None,
        front_diff_coast: Optional[int] = None,
        front_diff_preload: Optional[int] = None,
        rear_diff_power: Optional[int] = None,
        rear_diff_coast: Optional[int] = None,
        rear_diff_preload: Optional[int] = None,
        front_stiffness: Optional[int] = None,
        front_ride_height: Optional[int] = None,
        front_damping: Optional[int] = None,
        rear_stiffness: Optional[int] = None,
        rear_ride_height: Optional[int] = None,
        rear_damping: Optional[int] = None,
    ) -> Dict:
        """Generate tuning suggestions using Ollama AI.
        ecu_stage / internal_electronics_stage: 1, 2, or 3 when respective tuning is available.
        Optional turbo, supercharger, differential and front/rear suspension values are included in the prompt when provided.
        """
        if not self.check_ollama_connection():
            return {"error": "Ollama is not running or not accessible"}
        
        if focus_areas is None:
            focus_areas = ["engine", "suspension"]
        
        focus_text = ", ".join(focus_areas)
        
        # Build optional "Current setup" block for turbo, supercharger, differential
        current_setup_lines = []
        if turbo_charger is not None:
            current_setup_lines.append(f"Turbo Charger: {turbo_charger}")
        if boost_per_turbo is not None:
            current_setup_lines.append(f"Boost / 1 turbo: {boost_per_turbo}")
        if super_charger is not None:
            current_setup_lines.append(f"Super Charger: {super_charger}")
        if super_charger_boost is not None:
            current_setup_lines.append(f"Super Charger Boost: {super_charger_boost}")
        if front_diff_power is not None:
            current_setup_lines.append(f"Front Diff Power: {front_diff_power}")
        if front_diff_coast is not None:
            current_setup_lines.append(f"Front Diff Coast: {front_diff_coast}")
        if front_diff_preload is not None:
            current_setup_lines.append(f"Front Diff Preload: {front_diff_preload}")
        if rear_diff_power is not None:
            current_setup_lines.append(f"Rear Diff Power: {rear_diff_power}")
        if rear_diff_coast is not None:
            current_setup_lines.append(f"Rear Diff Coast: {rear_diff_coast}")
        if rear_diff_preload is not None:
            current_setup_lines.append(f"Rear Diff Preload: {rear_diff_preload}")
        if front_stiffness is not None:
            current_setup_lines.append(f"Front Stiffness: {front_stiffness}")
        if front_ride_height is not None:
            current_setup_lines.append(f"Front Ride height: {front_ride_height}")
        if front_damping is not None:
            current_setup_lines.append(f"Front Damping: {front_damping}")
        if rear_stiffness is not None:
            current_setup_lines.append(f"Rear Stiffness: {rear_stiffness}")
        if rear_ride_height is not None:
            current_setup_lines.append(f"Rear Ride height: {rear_ride_height}")
        if rear_damping is not None:
            current_setup_lines.append(f"Rear Damping: {rear_damping}")
        current_setup_text = ""
        if current_setup_lines:
            current_setup_text = "\n\nCurrent setup (use these values as context and suggest concrete adjustments where relevant):\n" + "\n".join(current_setup_lines)
        has_turbo_super = any(x is not None for x in (turbo_charger, boost_per_turbo, super_charger, super_charger_boost))
        has_diff = any(x is not None for x in (front_diff_power, front_diff_coast, front_diff_preload, rear_diff_power, rear_diff_coast, rear_diff_preload))
        
        # Build availability and stage context for ECU / Internal Electronics
        ecu_context = ""
        if ecu_available and ecu_stage in (1, 2, 3):
            ecu_context = f"\nECU tuning is AVAILABLE for this car. User has Stage {ecu_stage} ECU. Include ECU tuning suggestions."
        else:
            ecu_context = "\nECU tuning is NOT available for this car. Do not recommend or suggest ECU tuning."
        
        ie_context = ""
        if internal_electronics_available and internal_electronics_stage in (1, 2, 3):
            ie_context = f"\nInternal Electronics tuning is AVAILABLE. User has Stage {internal_electronics_stage} Internal Electronics. Include Internal Electronics tuning suggestions."
        else:
            ie_context = "\nInternal Electronics tuning is NOT available. Do not recommend or suggest Internal Electronics tuning."
        
        # Optional prompt sections for ECU and Internal Electronics when available
        ecu_section = ""
        if ecu_available and ecu_stage in (1, 2, 3):
            ecu_section = f"""
**ECU TUNING (Stage {ecu_stage}):**
- ECU stage {ecu_stage} specific settings: [recommendations for this stage]
- Power/timing/response: [specific recommendations]
- Other ECU parameters: [any other relevant settings]
"""
        ie_section = ""
        if internal_electronics_available and internal_electronics_stage in (1, 2, 3):
            ie_section = f"""
**INTERNAL ELECTRONICS TUNING (Stage {internal_electronics_stage}):**
- Internal Electronics stage {internal_electronics_stage} specific settings: [recommendations for this stage]
- Electronic systems and response: [specific recommendations]
- Other internal electronics parameters: [any other relevant settings]
"""
        
        turbo_diff_section = ""
        if has_turbo_super:
            turbo_diff_section += """
**TURBO & SUPERCHARGER:**
- Turbo/Boost settings: [specific recommendations based on their current values]
- Supercharger settings: [specific recommendations]
"""
        if has_diff:
            turbo_diff_section += """
**DIFFERENTIAL:**
- Front diff Power/Coast/Preload: [specific recommendations for handling]
- Rear diff Power/Coast/Preload: [specific recommendations]
"""
        
        # Prepare the prompt for tuning suggestions
        prompt = f"""You are an expert car tuning advisor for CDID (a Roblox car tuning experience). 
A user wants help tuning their car. Provide specific, actionable tuning recommendations.

Important note: In CDID, users cannot change how much air is in their tyre. Do not recommend changing tyre air pressure.
{ecu_context}
{ie_context}

Car Description:
{car_description}

Tuning Goals:
{tuning_goals}

Focus Areas: {focus_text}
{current_setup_text}

Consider the current setup values above when giving recommendations; suggest concrete adjustments for turbo, supercharger, or differential where relevant.

Please provide tuning suggestions in the following format:

**ENGINE TUNING:**
- Power/Torque settings: [specific recommendations]
- Gear ratios: [specific recommendations]
- RPM limits: [specific recommendations]
- Other engine parameters: [any other relevant settings]

**SUSPENSION TUNING:**
In CDID, stiffness, ride height and damping go from 0 to 1500 and are set separately for front and rear (six sliders in total). Rear suspension in CDID responds differently: at equal slider values the rear is softer at low values and stiffer at high values (exponential-type response). Give separate front and rear recommendations and account for this rear behavior. Use specific values in 0–1500 (e.g. 400, 850, 1200).
- Front Stiffness / Ride height / Damping: [specific recommendations]
- Rear Stiffness / Ride height / Damping: [specific recommendations; remember rear is softer at low and stiffer at high for same value]
- Other suspension parameters: [any other relevant settings]
{ecu_section}
{ie_section}
{turbo_diff_section}
**GENERAL ADVICE:**
- Trade-offs to consider: [what they might lose/gain]
- Testing recommendations: [how to test the changes]
- Additional tips: [any other helpful advice]

Be specific with numbers and values where applicable. Explain why each recommendation helps achieve their tuning goals.
"""
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120  # Longer timeout for complex analysis
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "suggestions": result.get("response", ""),
                    "model_used": self.model,
                    "timestamp": datetime.now().isoformat(),
                    "type": "tuning_suggestions"
                }
            else:
                return {"error": f"Ollama API error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Tuning suggestions failed: {str(e)}"}
    
    def diagnose_tuning_problem(self, problem_description: str, current_settings: str = "") -> Dict:
        """Diagnose tuning problems using Ollama AI"""
        if not self.check_ollama_connection():
            return {"error": "Ollama is not running or not accessible"}
        
        # Prepare the prompt for problem diagnosis
        settings_context = f"\nCurrent Settings:\n{current_settings}" if current_settings else ""
        
        prompt = f"""You are an expert car tuning advisor for CDID (a Roblox car tuning experience).
A user is experiencing a problem with their car tuning. Diagnose the issue and provide solutions.

Important note: In CDID, users cannot adjust tyre air pressure. Do not suggest changing tyre pressure as a solution or recommendation.

Problem Description:
{problem_description}
{settings_context}

Please provide a diagnosis in the following format:

**PROBLEM ANALYSIS:**
- Likely cause: [what is causing the problem]
- Affected systems: [which parts of the car are affected]

**SOLUTION:**
- Step 1: [first thing to try]
- Step 2: [second adjustment]
- Step 3: [third adjustment]
- Additional steps: [any other fixes]

**PARAMETER RECOMMENDATIONS:**
- Engine settings: [specific values to try]
- Suspension settings: [specific values to try]
- Other adjustments: [any other relevant changes, but do NOT mention tyre air pressure]

**TESTING:**
- How to verify the fix: [what to test]
- What to watch for: [signs of improvement or issues]

Be specific and actionable. Provide concrete tuning values where possible. Do not mention changing tyre air pressure.
"""
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120  # Longer timeout for complex analysis
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "diagnosis": result.get("response", ""),
                    "model_used": self.model,
                    "timestamp": datetime.now().isoformat(),
                    "type": "problem_diagnosis"
                }
            else:
                return {"error": f"Ollama API error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Diagnosis failed: {str(e)}"}
    
    def analyze_with_ollama(self, prompt: str) -> Dict:
        """General AI analysis using Ollama"""
        if not self.check_ollama_connection():
            return {"error": "Ollama is not running or not accessible"}
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120  # Longer timeout for complex analysis
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "analysis": result.get("response", ""),
                    "model_used": self.model,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"error": f"Ollama API error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}
    
    def set_model(self, model_name: str):
        """Set the Ollama model to use"""
        self.model = model_name
