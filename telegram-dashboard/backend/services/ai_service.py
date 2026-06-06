import json
from typing import Any

import httpx

from backend.config import OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_metrics",
            "description": "Retrieve dashboard metrics such as connected users and message counts.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_command_usage",
            "description": "Analyze command usage trends over the last 7 days.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "webhook_notify",
            "description": "Send a notification payload to an external webhook URL.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string"},
                    "message": {"type": "string"},
                },
                "required": ["url", "message"],
            },
        },
    },
]


class AIService:
    def __init__(
        self,
        api_key: str = OPENAI_API_KEY,
        base_url: str = OPENAI_BASE_URL,
        model: str = OPENAI_MODEL,
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    async def _call_tool(self, name: str, args: dict[str, Any], store) -> str:
        from backend.models.store import DashboardStore

        assert isinstance(store, DashboardStore)

        if name == "get_metrics":
            return json.dumps(store.metrics(), indent=2)
        if name == "analyze_command_usage":
            return json.dumps(store.command_usage_over_time(), indent=2)
        if name == "webhook_notify":
            url = args.get("url", "")
            message = args.get("message", "")
            if not url:
                return "Webhook URL is required."
            try:
                async with httpx.AsyncClient(timeout=15) as client:
                    response = await client.post(url, json={"message": message})
                    return f"Webhook responded with status {response.status_code}"
            except Exception as exc:
                return f"Webhook failed: {exc}"
        return f"Unknown tool: {name}"

    async def _chat_completion(self, messages: list[dict[str, Any]]) -> dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "tools": TOOLS,
            "tool_choice": "auto",
        }
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions", headers=headers, json=payload
            )
            response.raise_for_status()
            return response.json()

    async def process_message(self, user_text: str, store) -> str:
        if not self.configured:
            return self._fallback_response(user_text, store)

        messages = [
            {
                "role": "system",
                "content": (
                    "You are a helpful Telegram assistant connected to a dashboard. "
                    "Use tools when users ask for metrics, analytics, or external notifications."
                ),
            },
            {"role": "user", "content": user_text},
        ]

        try:
            result = await self._chat_completion(messages)
            choice = result["choices"][0]["message"]

            if choice.get("tool_calls"):
                tool_messages = messages + [choice]
                for tool_call in choice["tool_calls"]:
                    fn = tool_call["function"]
                    args = json.loads(fn.get("arguments") or "{}")
                    tool_result = await self._call_tool(fn["name"], args, store)
                    tool_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": tool_result,
                        }
                    )
                final = await self._chat_completion(tool_messages)
                return final["choices"][0]["message"]["content"]

            return choice.get("content") or "I could not generate a response."
        except Exception as exc:
            return f"AI processing error: {exc}. Falling back to local response.\n\n{self._fallback_response(user_text, store)}"

    def _fallback_response(self, user_text: str, store) -> str:
        lowered = user_text.lower().strip()
        if lowered.startswith("/help"):
            return (
                "Available commands:\n"
                "/help - Show help\n"
                "/status - Dashboard metrics\n"
                "/analytics - Command usage summary\n"
                "/feedback <rating 1-5> <comment> - Submit feedback"
            )
        if lowered.startswith("/status"):
            metrics = store.metrics()
            return (
                f"Connected users (24h): {metrics['connected_users']}\n"
                f"Total messages: {metrics['total_messages']}\n"
                f"Total commands: {metrics['total_commands']}"
            )
        if lowered.startswith("/analytics"):
            usage = store.command_usage_over_time()
            if not usage["labels"]:
                return "No command usage recorded yet."
            lines = ["Command usage (last 7 days):"]
            for dataset in usage["datasets"]:
                total = sum(dataset["data"])
                lines.append(f"- {dataset['label']}: {total}")
            return "\n".join(lines)
        if lowered.startswith("/feedback"):
            parts = user_text.split(maxsplit=2)
            if len(parts) < 3:
                return "Usage: /feedback <rating 1-5> <comment>"
            try:
                rating = int(parts[1])
            except ValueError:
                return "Rating must be a number between 1 and 5."
            comment = parts[2]
            store.add_feedback(None, "telegram_user", rating, comment)
            return "Thank you for your feedback!"
        return (
            "I received your message. Configure OPENAI_API_KEY for full AI responses, "
            "or try /help for available commands."
        )


ai_service = AIService()
