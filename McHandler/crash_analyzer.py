"""
Crash Log Analyzer - AI-powered crash log analysis using Ollama
"""

import requests
from datetime import datetime
from typing import Dict, List

class CrashLogAnalyzer:
    """Crash log analysis with Ollama integration"""
    
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
    
    def analyze_crash_log(self, log_content: str) -> Dict:
        """Analyze crash log using Ollama AI"""
        if not self.check_ollama_connection():
            return {"error": "Ollama is not running or not accessible"}
        
        # Prepare the prompt for crash log analysis
        prompt = f"""
        Analyze this Minecraft crash log and provide a detailed analysis. Focus on:
        1. The root cause of the crash
        2. Which mod(s) might be causing the issue
        3. Potential solutions or workarounds
        4. Compatibility issues between mods
        
        Crash log:
        {log_content[:8000]}  # Limit to avoid token limits
        
        Please provide a structured analysis with clear recommendations. If there is no mod causing the crash, say so. If there is no major issues, say so.
        """
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
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
    
    def suggest_mod_fixes(self, mod_name: str, error_description: str) -> Dict:
        """Get AI suggestions for fixing mod issues"""
        if not self.check_ollama_connection():
            return {"error": "Ollama is not running or not accessible"}
        
        prompt = f"""
        A Minecraft mod named "{mod_name}" is causing issues. Error description: {error_description}
        
        Please provide:
        1. Common causes for this type of error with this mod
        2. Potential solutions (version updates, configuration changes, etc.)
        3. Alternative mods if this one is problematic
        4. Configuration recommendations
        
        Be specific and practical in your suggestions.
        """
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return {
                    "suggestions": result.get("response", ""),
                    "model_used": self.model,
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {"error": f"Ollama API error: {response.status_code}"}
                
        except Exception as e:
            return {"error": f"Suggestion failed: {str(e)}"}
    
    def analyze_with_ai(self, prompt: str) -> Dict:
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
    
    def analyze_with_ollama(self, prompt: str) -> str:
        """Simple AI analysis that returns just the response text"""
        if not self.check_ollama_connection():
            return "Ollama is not running or not accessible"
        
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=120
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("response", "No response from AI")
            else:
                return f"Ollama API error: {response.status_code}"
                
        except Exception as e:
            return f"Analysis failed: {str(e)}"