from ai.ollama_client import OllamaClient
import numpy as np

class MixingAdvisor:
    def __init__(self, client: OllamaClient):
        self.client = client
        self.system_prompt = (
            "You are a professional mix engineer. "
            "Analyze the audio characteristics provided and give specific, actionable mixing advice. "
            "Suggest EQ adjustments, compression settings, and spatial effects."
        )

    def advise_on_audio(self, audio_stats, callback=None):
        """
        audio_stats: A dictionary with audio analysis data (e.g., peak, rms, spectral balance).
        """
        prompt = f"I have a vocal track with these characteristics: {audio_stats}. What mixing steps do you recommend?"
        return self.client.generate_response(prompt, self.system_prompt, callback)
