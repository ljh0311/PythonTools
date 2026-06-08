import ollama
import threading

class OllamaClient:
    def __init__(self, model="llama3"):
        self.model = model
        self.client = ollama.Client()

    def generate_response(self, prompt, system_prompt=None, callback=None):
        """
        Generates a response from Ollama.
        If callback is provided, it runs in a thread and calls the callback with the result.
        """
        if callback:
            thread = threading.Thread(target=self._generate_thread, args=(prompt, system_prompt, callback))
            thread.start()
            return None
        else:
            return self._generate(prompt, system_prompt)

    def _generate(self, prompt, system_prompt):
        try:
            messages = []
            if system_prompt:
                messages.append({'role': 'system', 'content': system_prompt})
            messages.append({'role': 'user', 'content': prompt})
            
            response = self.client.chat(model=self.model, messages=messages)
            return response['message']['content']
        except Exception as e:
            return f"Error connecting to Ollama: {str(e)}. Make sure Ollama is running and '{self.model}' is installed."

    def _generate_thread(self, prompt, system_prompt, callback):
        result = self._generate(prompt, system_prompt)
        callback(result)

    def list_models(self):
        try:
            return self.client.list()
        except Exception:
            return []
