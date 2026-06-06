import json
from typing import Any

import httpx

from backend.config import GEMINI_API_KEY, GEMINI_MODEL
from backend.services.ai_tools import SYSTEM_PROMPT, execute_tool, gemini_tools


class GeminiProvider:
    name = "gemini"

    def __init__(self, api_key: str = GEMINI_API_KEY, model: str = GEMINI_MODEL):
        self.api_key = api_key
        self.model = model

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _endpoint(self) -> str:
        return (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )

    async def _generate(self, contents: list[dict[str, Any]]) -> dict[str, Any]:
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": contents,
            "tools": [{"function_declarations": gemini_tools()}],
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                self._endpoint(),
                params={"key": self.api_key},
                json=payload,
            )
            response.raise_for_status()
            return response.json()

    async def chat(self, user_text: str, store) -> str:
        contents = [{"role": "user", "parts": [{"text": user_text}]}]
        result = await self._generate(contents)
        candidate = result["candidates"][0]["content"]
        parts = candidate.get("parts", [])

        function_calls = [part["functionCall"] for part in parts if "functionCall" in part]
        if function_calls:
            model_content = {"role": "model", "parts": parts}
            contents.append(model_content)

            for call in function_calls:
                tool_result = await execute_tool(
                    call["name"],
                    call.get("args", {}),
                    store,
                )
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": call["name"],
                                    "response": {"result": tool_result},
                                }
                            }
                        ],
                    }
                )

            final = await self._generate(contents)
            final_parts = final["candidates"][0]["content"].get("parts", [])
            text_parts = [part["text"] for part in final_parts if "text" in part]
            return "\n".join(text_parts).strip() or "I could not generate a response."

        text_parts = [part["text"] for part in parts if "text" in part]
        return "\n".join(text_parts).strip() or "I could not generate a response."
