import json
from typing import Any

import httpx

TOOL_SPECS = [
    {
        "name": "get_metrics",
        "description": "Retrieve dashboard metrics such as connected users and message counts.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "analyze_command_usage",
        "description": "Analyze command usage trends over the last 7 days.",
        "parameters": {"type": "object", "properties": {}, "required": []},
    },
    {
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
]

SYSTEM_PROMPT = (
    "You are a helpful Telegram assistant connected to a dashboard. "
    "Use tools when users ask for metrics, analytics, or external notifications."
)


def openai_tools() -> list[dict[str, Any]]:
    return [
        {"type": "function", "function": spec}
        for spec in TOOL_SPECS
    ]


def _gemini_type(schema_type: str) -> str:
    mapping = {
        "object": "OBJECT",
        "string": "STRING",
        "integer": "INTEGER",
        "number": "NUMBER",
        "boolean": "BOOLEAN",
        "array": "ARRAY",
    }
    return mapping.get(schema_type.lower(), schema_type.upper())


def _to_gemini_schema(schema: dict[str, Any]) -> dict[str, Any]:
    converted: dict[str, Any] = {"type": _gemini_type(schema.get("type", "object"))}
    if "properties" in schema:
        converted["properties"] = {
            key: _to_gemini_schema(value)
            for key, value in schema["properties"].items()
        }
    if "required" in schema:
        converted["required"] = schema["required"]
    return converted


def gemini_tools() -> list[dict[str, Any]]:
    return [
        {
            "name": spec["name"],
            "description": spec["description"],
            "parameters": _to_gemini_schema(spec["parameters"]),
        }
        for spec in TOOL_SPECS
    ]


async def execute_tool(name: str, args: dict[str, Any], store) -> str:
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
