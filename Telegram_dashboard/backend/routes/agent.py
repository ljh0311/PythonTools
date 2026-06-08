from fastapi import APIRouter, Depends

from backend.config import HOST, PORT
from backend.routes.deps import verify_operator


router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.get("/manifest", dependencies=[Depends(verify_operator)])
async def agent_manifest() -> dict:
    base = f"http://{HOST}:{PORT}" if HOST != "0.0.0.0" else "http://localhost:8000"
    return {
        "name": "telegram-dashboard",
        "version": "1.0.0",
        "description": "Operator dashboard for Telegram messages, AI summaries, and workflow control.",
        "auth": {
            "type": "api_key",
            "header": "X-API-Key",
            "alt": "Authorization: Bearer <token>",
        },
        "openapi_url": f"{base}/openapi.json",
        "base_url": base,
        "tools": [
            {
                "name": "get_metrics",
                "method": "GET",
                "path": "/api/metrics",
                "description": "Connected users, total messages, commands.",
            },
            {
                "name": "list_messages",
                "method": "GET",
                "path": "/api/messages",
                "description": "Filter messages. Query: user_ids, chat_type, direction, q, topics, date_from, date_to, limit, offset.",
            },
            {
                "name": "list_threads",
                "method": "GET",
                "path": "/api/inbox/threads",
                "description": "Conversations grouped by chat_id with same filters as messages.",
            },
            {
                "name": "summarize",
                "method": "POST",
                "path": "/api/ai/summarize",
                "description": "Summarize filtered messages. Body: summary_type (brief|detailed|bullets|unanswered) + filter fields.",
            },
            {
                "name": "suggest_actions",
                "method": "POST",
                "path": "/api/ai/suggest-actions",
                "description": "AI reply drafts and next actions for filtered messages.",
            },
            {
                "name": "send_message",
                "method": "POST",
                "path": "/api/send",
                "description": "Send Telegram message. Body: { chat_id, text }.",
            },
            {
                "name": "get_reply_mode",
                "method": "GET",
                "path": "/api/settings/reply-mode",
                "description": "Current auto-reply mode and per-chat settings with relationship context.",
            },
            {
                "name": "set_reply_mode",
                "method": "PUT",
                "path": "/api/settings/reply-mode",
                "description": "Set mode: manual | auto | per_chat.",
            },
            {
                "name": "export_messages",
                "method": "GET",
                "path": "/api/export/messages",
                "description": "Export filtered messages as CSV. Same query params as /api/messages.",
            },
        ],
    }
