import json
import uuid
from typing import Any

import httpx

from backend.config import OLLAMA_BASE_URL, OLLAMA_MODEL
from backend.services.ai_tools import SYSTEM_PROMPT, execute_tool, openai_tools


class OllamaProvider:
    name = "ollama"

    def __init__(self, base_url: str = OLLAMA_BASE_URL, model: str = OLLAMA_MODEL):
        self.base_url = base_url.rstrip("/")
        self.model = model

    @property
    def configured(self) -> bool:
        return bool(self.base_url and self.model)

    async def is_available(self) -> bool:
        if not self.configured:
            return False
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                host = self.base_url.removesuffix("/v1")
                response = await client.get(f"{host}/api/tags")
                return response.status_code == 200
        except Exception:
            return False

    async def _chat_completion(
        self, messages: list[dict[str, Any]], *, use_tools: bool = True
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": messages,
            "stream": False,
        }
        if use_tools:
            payload["tools"] = openai_tools()
            payload["tool_choice"] = "auto"
        async with httpx.AsyncClient(timeout=120) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def generate_text(self, prompt: str, system: str = "") -> str:
        messages: list[dict[str, Any]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})
        result = await self._chat_completion(messages, use_tools=False)
        return result["choices"][0]["message"].get("content") or "Unable to generate summary."

    async def chat(self, user_text: str, store) -> str:
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
