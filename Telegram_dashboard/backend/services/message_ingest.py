from datetime import datetime, timezone
from typing import Any

from backend.models.store import store
from backend.services.ai_service import ai_service


async def maybe_assign_topics(message_id: int, text: str) -> list[str]:
    if store.get_topic_mode() != "ai_assign":
        return []
    topics = await ai_service.assign_topics(text)
    return store.add_message_topics(message_id, topics, source="ai")


async def ingest_message(
    *,
    user_id: int,
    username: str | None,
    direction: str,
    text: str,
    chat_id: int | None,
    message_id: int | None,
    chat_type: str | None,
    chat_title: str | None = None,
    reply_to_message_id: int | None = None,
    ingestion_source: str = "bot",
    telegram_date: str | None = None,
    user_payload: dict[str, Any] | None = None,
    auto_reply: bool = False,
    send_reply=None,
) -> dict[str, Any] | None:
    """Store a message if new. Returns result dict or None when duplicate skipped."""
    if user_payload:
        store.upsert_user(user_payload)

    stored, created = store.add_message(
        user_id,
        username,
        direction,
        text,
        chat_id=chat_id,
        message_id=message_id,
        chat_type=chat_type,
        chat_title=chat_title,
        reply_to_message_id=reply_to_message_id,
        ingestion_source=ingestion_source,
        telegram_date=telegram_date,
    )
    if not created:
        return None

    topics = await maybe_assign_topics(stored["id"], text)
    store.add_event(
        "message_received",
        {
            "user_id": user_id,
            "chat_id": chat_id,
            "chat_type": chat_type,
            "text": text,
            "topics": topics,
            "ingestion_source": ingestion_source,
        },
    )

    reply: str | None = None
    if auto_reply and ingestion_source == "bot" and store.should_auto_reply(chat_id):
        reply = await ai_service.process_message(text, store)
        store.add_message(
            user_id,
            username,
            "outgoing",
            reply,
            chat_id=chat_id,
            chat_type=chat_type,
            chat_title=chat_title,
            ingestion_source="bot",
        )
        if send_reply and chat_id:
            await send_reply(chat_id, reply)

    return {
        "user_id": user_id,
        "chat_id": chat_id,
        "chat_type": chat_type,
        "message": stored,
        "reply": reply,
        "auto_replied": reply is not None,
        "topics": topics,
        "ingestion_source": ingestion_source,
    }


def telegram_timestamp_to_iso(timestamp: int | None) -> str | None:
    if not timestamp:
        return None
    return datetime.fromtimestamp(timestamp, tz=timezone.utc).replace(tzinfo=None).isoformat()
