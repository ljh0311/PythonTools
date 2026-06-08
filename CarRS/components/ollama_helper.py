"""Helper to interact with Ollama LLM for car rental recommendations."""
from car_rental_recommender_core import get_ollama_enhanced_recommendations


class OllamaHelper:
    """
    Helper class to interact with Ollama LLM for car rental recommendations.
    Provides methods to get recommendations with or without ML/LLM/fallback.
    """

    def __init__(self, ollama_model="llama3", use_ml=True):
        try:
            import ollama
            self.ollama = ollama
        except ImportError:
            self.ollama = None
        self.ollama_model = ollama_model
        self.use_ml = use_ml

    def send_prompt(self, prompt, model=None, stream=False, timeout=30):
        """
        Send a prompt to Ollama and return the response (plain or JSON text).
        Returns None if Ollama or required methods aren't available, or on error.
        """
        if not self.ollama:
            return None
        model = model or self.ollama_model
        try:
            if hasattr(self.ollama, "generate"):
                return self.ollama.generate(model=model, prompt=prompt, stream=stream)
            import requests
            ollama_url = "http://localhost:11434/api/generate"
            payload = {
                "model": model,
                "prompt": prompt,
                "stream": stream,
            }
            response = requests.post(ollama_url, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json().get("response") or response.text
        except Exception:
            return None

    def get_ollama_recommendations(self, distance, duration, df, cost_analysis, is_weekend, top_n=10, use_ollama=True, use_ml=True):
        """Calls get_ollama_enhanced_recommendations with the provided parameters."""
        if not self.ollama:
            raise RuntimeError("Ollama is not available")
        return get_ollama_enhanced_recommendations(
            distance,
            duration,
            df,
            cost_analysis,
            is_weekend,
            top_n=top_n,
            use_ollama=use_ollama,
            ollama_model=self.ollama_model,
            use_ml=use_ml,
        )

    def get_fallback_recommendations(self, distance, duration, df, cost_analysis, is_weekend, top_n=10):
        """Calls get_ollama_enhanced_recommendations with use_ollama=False."""
        return get_ollama_enhanced_recommendations(
            distance,
            duration,
            df,
            cost_analysis,
            is_weekend,
            top_n=top_n,
            use_ollama=False,
            ollama_model=self.ollama_model,
            use_ml=self.use_ml,
        )

    def get_ml_recommendations(self, distance, duration, df, cost_analysis, is_weekend, top_n=10):
        """Calls get_ollama_enhanced_recommendations with use_ml=True, use_ollama=False."""
        return get_ollama_enhanced_recommendations(
            distance,
            duration,
            df,
            cost_analysis,
            is_weekend,
            top_n=top_n,
            use_ollama=False,
            ollama_model=self.ollama_model,
            use_ml=True,
        )

    def get_ollama_and_ml_recommendations(self, distance, duration, df, cost_analysis, is_weekend, top_n=10):
        """Calls get_ollama_enhanced_recommendations with use_ml=True, use_ollama=True."""
        return self.get_ollama_recommendations(
            distance, duration, df, cost_analysis, is_weekend, top_n=top_n, use_ollama=True, use_ml=True
        )

    def get_fallback_and_ml_recommendations(self, distance, duration, df, cost_analysis, is_weekend, top_n=10):
        """Calls get_ollama_enhanced_recommendations with use_ml=True, use_ollama=False."""
        return self.get_ml_recommendations(
            distance, duration, df, cost_analysis, is_weekend, top_n=top_n
        )

    def get_ollama_and_fallback_recommendations(self, distance, duration, df, cost_analysis, is_weekend, top_n=10):
        """Tries Ollama, falls back to non-Ollama if fails."""
        try:
            return self.get_ollama_recommendations(
                distance, duration, df, cost_analysis, is_weekend, top_n=top_n, use_ollama=True, use_ml=self.use_ml
            )
        except Exception:
            return self.get_fallback_recommendations(
                distance, duration, df, cost_analysis, is_weekend, top_n=top_n
            )
