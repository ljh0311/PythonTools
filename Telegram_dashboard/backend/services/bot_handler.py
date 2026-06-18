import re
from typing import Any

from backend.models.store import store
from backend.services.message_ingest import ingest_message
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

    async def send_reply(target_chat_id: int, reply_text: str) -> None:
        if telegram_service.configured:
            await telegram_service.send_message(target_chat_id, reply_text)

    result = await ingest_message(
        user_id=user_id,
        username=username,
        direction="incoming",
        text=text,
        chat_id=chat_id,
        message_id=message.get("message_id"),
        chat_type=chat_type,
        chat_title=chat_title,
        reply_to_message_id=(message.get("reply_to_message") or {}).get("message_id"),
        ingestion_source="bot",
        user_payload=user,
        auto_reply=True,
        send_reply=send_reply,
    )
    if not result:
        return None

    match = COMMAND_PATTERN.match(text)
    if match:
        store.track_command(f"/{match.group(1)}")

    return result
