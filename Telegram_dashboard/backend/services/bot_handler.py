import re
from typing import Any

from backend.models.store import store
from backend.services.ai_service import ai_service
from backend.services.telegram_service import telegram_service


COMMAND_PATTERN = re.compile(r"^/(\w+)")
SUPPORTED_CHAT_TYPES = {"private", "group", "channel"}


def _message_from_update(update: dict[str, Any]) -> dict[str, Any] | None:
    return (
        update.get("message")
        or update.get("edited_message")
        or update.get("channel_post")
        or update.get("edited_channel_post")
    )


def _normalize_chat_type(chat: dict[str, Any]) -> str | None:
    chat_type = chat.get("type", "")
    if chat_type == "supergroup":
        return "group"
    if chat_type in SUPPORTED_CHAT_TYPES:
        return chat_type
    return None


def _is_bot_message(message: dict[str, Any]) -> bool:
    return bool((message.get("from") or {}).get("is_bot"))


def _author_from_message(
    message: dict[str, Any], chat: dict[str, Any]
) -> tuple[int | None, str | None, dict[str, Any]]:
    user = message.get("from") or {}
    if user.get("id"):
        return user.get("id"), user.get("username"), user

    sender_chat = message.get("sender_chat") or chat
    chat_id = sender_chat.get("id") or chat.get("id")
    username = sender_chat.get("username") or chat.get("username")
    title = sender_chat.get("title") or chat.get("title") or "Channel"
    return chat_id, username, {
        "id": chat_id,
        "username": username,
        "first_name": title,
        "last_name": "",
    }


async def _maybe_assign_topics(message_id: int, text: str) -> list[str]:
    if store.get_topic_mode() != "ai_assign":
        return []
    topics = await ai_service.assign_topics(text)
    return store.add_message_topics(message_id, topics, source="ai")


async def handle_telegram_update(update: dict[str, Any]) -> dict[str, Any] | None:
    message = _message_from_update(update)
    if not message:
        store.add_event("unsupported_update", update)
        return None

    chat = message.get("chat", {})
    chat_type = _normalize_chat_type(chat)

    if chat_type is None:
        store.add_event("unsupported_chat_type", {"chat": chat, "update": update})
        return None

    text = (message.get("text") or message.get("caption") or "").strip()
    if not text:
        store.add_event("empty_message", {"message_id": message.get("message_id")})
        return None

    user_id, username, user = _author_from_message(message, chat)
    chat_id = chat.get("id")
    chat_title = chat.get("title") if chat_type in ("group", "channel") else None
    telegram_message_id = message.get("message_id")
    from_bot = _is_bot_message(message)

    if (
        chat_id is not None
        and telegram_message_id
        and store.has_telegram_message(chat_id, telegram_message_id)
    ):
        return None

    if user_id and not from_bot:
        store.upsert_user(user)

    direction = "outgoing" if from_bot else "incoming"
    stored = store.add_message(
        user_id or 0,
        username,
        direction,
        text,
        chat_id=chat_id,
        message_id=telegram_message_id,
        chat_type=chat_type,
        chat_title=chat_title,
        reply_to_message_id=(message.get("reply_to_message") or {}).get("message_id"),
    )

    if from_bot:
        return {
            "user_id": user_id,
            "chat_id": chat_id,
            "chat_type": chat_type,
            "message": stored,
            "reply": None,
            "auto_replied": False,
            "topics": [],
        }

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
        sent_message_id = None
        if telegram_service.configured and chat_id:
            send_result = await telegram_service.send_message(chat_id, reply)
            sent_message_id = (send_result.get("result") or {}).get("message_id")
        store.add_message(
            0,
            username or "bot",
            "outgoing",
            reply,
            chat_id=chat_id,
            message_id=sent_message_id,
            chat_type=chat_type,
            chat_title=chat_title,
        )

    return {
        "user_id": user_id,
        "chat_id": chat_id,
        "chat_type": chat_type,
        "message": stored,
        "reply": reply,
        "auto_replied": reply is not None,
        "topics": topics,
    }
