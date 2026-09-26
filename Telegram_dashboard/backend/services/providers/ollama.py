import json
import logging
import uuid
from typing import Any

import httpx

from backend.config import OLLAMA_BASE_URL, OLLAMA_MODEL

logger = logging.getLogger(__name__)


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model)

    def _model_installed(self, names: list[str], model: str | None = None) -> bool:
        target = (model or self.model).lower()
        for name in names:
            lowered = name.lower()
            if lowered == target or lowered.startswith(f"{target}:"):
                return True
            if lowered.split(":", 1)[0] == target.split(":", 1)[0] and ":" not in target:
                return True
            if lowered.split(":", 1)[0] == target:
                return True
        return False

    async def list_model_names(self) -> list[str] | None:
        """Return installed model names, or None if Ollama is unreachable."""
        if not self.configured:
            return None
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                host = self.base_url.removesuffix("/v1")
                response = await client.get(f"{host}/api/tags")
                if response.status_code != 200:
                    return None
                models = response.json().get("models", [])
                return [m.get("name", "") for m in models if m.get("name")]
        except Exception:
            return None

    async def is_available(self) -> bool:
        names = await self.list_model_names()
        if names is None:
            return False
        return self._model_installed(names)

    async def _chat_completion(
        self,
        messages: list[dict[str, Any]],
        *,
        use_tools: bool = True,
        model: str | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "stream": False,
        }
        if use_tools:
            from backend.services.ai_tools import openai_tools

            payload["tools"] = openai_tools()
            payload["tool_choice"] = "auto"
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def generate_text(
        self, prompt: str, system: str = "", *, model: str | None = None
    ) -> str:
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        result = await self._chat_completion(messages, use_tools=False, model=model)
        return result["choices"][0]["message"].get("content") or "Unable to generate summary."

    async def chat(self, user_text: str, store) -> str:
        from backend.services.ai_tools import SYSTEM_PROMPT, execute_tool

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ]
        result = await self._chat_completion(messages)
        choice = result["choices"][0]["message"]

        if choice.get("tool_calls"):
            tool_messages = messages + [choice]
            for tool_call in choice["tool_calls"]:
                fn = tool_call["function"]
                args = json.loads(fn.get("arguments") or "{}")
                tool_result = await execute_tool(fn["name"], args, store)
                tool_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id") or str(uuid.uuid4()),
                        "content": tool_result,
                    }
                )
            final = await self._chat_completion(tool_messages)
            return final["choices"][0]["message"].get("content") or "I could not generate a response."

        return choice.get("content") or "I could not generate a response."
