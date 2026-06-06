import re
from typing import Any

from backend.models.store import store
from backend.services.ai_service import ai_service
from backend.services.telegram_service import telegram_service


COMMAND_PATTERN = re.compile(r"^/(\w+)")
SUPPORTED_CHAT_TYPES = {"private", "group"}


def _normalize_chat_type(chat: dict[str, Any]) -> str | None:
    chat_type = chat.get("type", "")
    if chat_type == "channel":
        return None
    if chat_type in SUPPORTED_CHAT_TYPES:
        return chat_type
    return None


async def _maybe_assign_topics(message_id: int, text: str) -> list[str]:
    if store.get_topic_mode() != "ai_assign":
        return []
    topics = await ai_service.assign_topics(text)
    return store.add_message_topics(message_id, topics, source="ai")


async def handle_telegram_update(update: dict[str, Any]) -> dict[str, Any] | None:
    message = update.get("message") or update.get("edited_message")
    if not message:
        store.add_event("unsupported_update", update)
        return None

    user = message.get("from", {})
    chat = message.get("chat", {})
    chat_type = _normalize_chat_type(chat)

    if chat_type is None:
        store.add_event("unsupported_chat_type", {"chat": chat, "update": update})
        return None

    text = (message.get("text") or message.get("caption") or "").strip()
    if not text:
        store.add_event("empty_message", {"message_id": message.get("message_id")})
        return None

    user_id = user.get("id")
    chat_id = chat.get("id")
    username = user.get("username")
    chat_title = chat.get("title") if chat_type == "group" else None

    store.upsert_user(user)
    stored = store.add_message(
        user_id,
        username,
        "incoming",
        text,
        chat_id=chat_id,
        message_id=message.get("message_id"),
        chat_type=chat_type,
        chat_title=chat_title,
        reply_to_message_id=(message.get("reply_to_message") or {}).get("message_id"),
    )
    topics = await _maybe_assign_topics(stored["id"], text)
    store.add_event(
        "message_received",
        {
            "user_id": user_id,
            "chat_id": chat_id,
            "chat_type": chat_type,
            "text": text,
            "topics": topics,
        },
    )

    match = COMMAND_PATTERN.match(text)
    if match:
        store.track_command(f"/{match.group(1)}")

    reply: str | None = None
    if store.should_auto_reply(chat_id):
        reply = await ai_service.process_message(text, store)
        store.add_message(
            user_id,
            username,
            "outgoing",
            reply,
            chat_id=chat_id,
            chat_type=chat_type,
            chat_title=chat_title,
        )
        if telegram_service.configured and chat_id:
            await telegram_service.send_message(chat_id, reply)

    return {
        "user_id": user_id,
        "chat_id": chat_id,
        "chat_type": chat_type,
        "message": stored,
        "reply": reply,
        "auto_replied": reply is not None,
        "topics": topics,
    }
