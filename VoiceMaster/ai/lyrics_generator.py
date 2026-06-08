from ai.ollama_client import OllamaClient

class LyricsGenerator:
    def __init__(self, client: OllamaClient):
        self.client = client
        self.system_prompt = (
            "You are a professional songwriter and lyricist. "
            "Help the user write creative, rhyming, and meaningful lyrics for their music. "
            "Provide suggestions for verses, choruses, and bridges based on the user's theme or mood."
        )

    def generate_lyrics(self, theme, genre="Pop", callback=None):
        prompt = f"Write lyrics for a {genre} song about: {theme}"
        return self.client.generate_response(prompt, self.system_prompt, callback)

    def refine_lyrics(self, current_lyrics, feedback, callback=None):
        prompt = f"Here are my current lyrics:\n\n{current_lyrics}\n\nPlease refine them based on this feedback: {feedback}"
        return self.client.generate_response(prompt, self.system_prompt, callback)
