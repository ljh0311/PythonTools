"""
Shared Ollama HTTP client for McHandler apps.
"""

import requests
from datetime import datetime
from typing import Dict, List, Optional


class OllamaClient:
    """HTTP wrapper for Ollama generate/tags APIs."""

    def __init__(
        self,
        url: str = "http://localhost:11434",
        model: str = "llama3.2",
        timeout: int = 60,
    ):
        self.ollama_url = url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def configure(
        self,
        url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> None:
        if url is not None:
            self.ollama_url = url.rstrip("/")
        if model is not None:
            self.model = model
        if timeout is not None:
            self.timeout = timeout

    def check_connection(self) -> bool:
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_available_models(self) -> List[str]:
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=self.timeout)
            if response.status_code == 200:
                models = response.json().get("models", [])
                return [model["name"] for model in models]
        except Exception:
            pass
        return []

    def generate(self, prompt: str, timeout: Optional[int] = None) -> Dict:
        request_timeout = timeout if timeout is not None else self.timeout
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                },
                timeout=request_timeout,
            )
            if response.status_code == 200:
                result = response.json()
                return {
                    "response": result.get("response", ""),
                    "model_used": self.model,
                    "timestamp": datetime.now().isoformat(),
                }
            return {"error": f"Ollama API error: {response.status_code}"}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}
