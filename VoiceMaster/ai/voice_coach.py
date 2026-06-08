from ai.ollama_client import OllamaClient

class VoiceCoach:
    def __init__(self, client: OllamaClient):
        self.client = client
        self.system_prompt = (
            "You are a professional vocal coach. "
            "Provide encouraging and technical feedback on vocal performance. "
            "Focus on pitch accuracy, timing, dynamics, and breathing technique."
        )

    def provide_feedback(self, performance_data, callback=None):
        """
        performance_data: Dictionary containing pitch accuracy, timing deviations, etc.
        """
        prompt = f"Here is my vocal performance data: {performance_data}. Can you give me some coaching feedback?"
        return self.client.generate_response(prompt, self.system_prompt, callback)
