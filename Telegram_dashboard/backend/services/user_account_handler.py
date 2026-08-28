from __future__ import annotations

from typing import Any

from telethon import events
from telethon.tl.types import Channel, Chat, User

from backend.services.message_ingest import ingest_message


def _chat_type_from_entity(entity: Any) -> str | None:
    if isinstance(entity, User):
        return "private"
    if isinstance(entity, Channel):
        return "channel" if entity.broadcast else "group"
    if isinstance(entity, Chat):
        return "group"
    return None


def _chat_title_from_entity(entity: Any) -> str | None:
    title = getattr(entity, "title", None)
    if title:
        return title
    if isinstance(entity, User):
        parts = [entity.first_name or "", entity.last_name or ""]
        name = " ".join(p for p in parts if p).strip()
        return name or entity.username
    return None


async def handle_mtproto_message(
    event: events.NewMessage.Event,
    account_user_id: int,
    account_user: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    text = (event.message.message or event.message.text or "").strip()
    if not text and event.message.media:
        text = f"[{type(event.message.media).__name__}]"
    if not text:
        return None

    chat = await event.get_chat()
    chat_type = _chat_type_from_entity(chat)
    if not chat_type:
        return None

    chat_id = event.chat_id
    direction = "outgoing" if event.out else "incoming"

    sender = await event.get_sender()
    if isinstance(sender, User):
        sender_id = sender.id
        username = sender.username
        user_payload = {
            "id": sender.id,
            "username": sender.username,
            "first_name": sender.first_name,
            "last_name": sender.last_name,
        }
    elif direction == "outgoing":
        sender_id = account_user_id
        username = account_user.get("username") if account_user else None
        user_payload = account_user
    else:
        sender_id = event.sender_id or 0
        username = None
        user_payload = None

    chat_title = _chat_title_from_entity(chat)
    if chat_type == "private" and direction == "outgoing":
        chat_title = _chat_title_from_entity(chat)

    reply_to = None
    if event.message.reply_to and getattr(event.message.reply_to, "reply_to_msg_id", None):
        reply_to = event.message.reply_to.reply_to_msg_id

    telegram_date = None
    if event.message.date:
        telegram_date = event.message.date.replace(tzinfo=None).isoformat()

    return await ingest_message(
        user_id=sender_id,
        username=username,
        direction=direction,
        text=text,
        chat_id=chat_id,
        message_id=event.id,
        chat_type=chat_type,
        chat_title=chat_title,
        reply_to_message_id=reply_to,
        ingestion_source="user_account",
        telegram_date=telegram_date,
        user_payload=user_payload,
        auto_reply=False,
    )
