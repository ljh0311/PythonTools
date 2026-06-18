"""
Crash Log Analyzer - AI-powered crash log analysis using Ollama
"""

from typing import Dict, List, Optional

from ollama_client import OllamaClient


class CrashLogAnalyzer:
    """Crash log analysis with Ollama integration"""

    def __init__(
        self,
        url: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout: int = 60,
    ):
        self.client = OllamaClient(url=url, model=model, timeout=timeout)

    @property
    def ollama_url(self) -> str:
        return self.client.ollama_url

    @property
    def model(self) -> str:
        return self.client.model

    @property
    def timeout(self) -> int:
        return self.client.timeout

    def configure(
        self,
        url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        self.client.configure(url=url, model=model, timeout=timeout)

    def check_ollama_connection(self) -> bool:
        return self.client.check_connection()

    def get_available_models(self) -> List[str]:
        return self.client.get_available_models()

    def analyze_crash_log(self, log_content: str) -> Dict:
        if not self.check_ollama_connection():
            return {"error": "Ollama is not running or not accessible"}

        prompt = f"""
        Analyze this Minecraft crash log and provide a detailed analysis. Focus on:
        1. The root cause of the crash
        2. Which mod(s) might be causing the issue
        3. Potential solutions or workarounds
        4. Compatibility issues between mods

        Crash log:
        {log_content[:8000]}

        Please provide a structured analysis with clear recommendations. If there is no mod causing the crash, say so. If there is no major issues, say so.
        """

        result = self.client.generate(prompt, timeout=self.client.timeout)
        if "error" in result:
            return result
        return {
            "analysis": result.get("response", ""),
            "model_used": result.get("model_used", self.model),
            "timestamp": result.get("timestamp", ""),
        }

    def suggest_mod_fixes(self, mod_name: str, error_description: str) -> Dict:
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

        result = self.client.generate(prompt, timeout=self.client.timeout)
        if "error" in result:
            return result
        return {
            "suggestions": result.get("response", ""),
            "model_used": result.get("model_used", self.model),
            "timestamp": result.get("timestamp", ""),
        }

    def analyze_with_ai(self, prompt: str) -> Dict:
        if not self.check_ollama_connection():
            return {"error": "Ollama is not running or not accessible"}

        result = self.client.generate(prompt, timeout=max(self.client.timeout, 120))
        if "error" in result:
            return result
        return {
            "analysis": result.get("response", ""),
            "model_used": result.get("model_used", self.model),
            "timestamp": result.get("timestamp", ""),
        }

    def analyze_with_ollama(self, prompt: str) -> str:
        if not self.check_ollama_connection():
            return "Ollama is not running or not accessible"

        result = self.client.generate(prompt, timeout=max(self.client.timeout, 120))
        if "error" in result:
            return result["error"]
        return result.get("response", "No response from AI")
