"""Shared Act open-items heuristic (needs-reply / last-inbound unanswered)."""

from __future__ import annotations

from typing import Any


def heuristic_open_items(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Private/group threads whose latest message is inbound (needs attention)."""
    by_chat: dict[int, list[dict[str, Any]]] = {}
    for msg in messages:
        chat_id = msg.get("chat_id")
        if chat_id is None:
            continue
        if msg.get("chat_type") not in ("private", "group", None):
            continue
        by_chat.setdefault(int(chat_id), []).append(msg)

    open_items: list[dict[str, Any]] = []
    for chat_id, chat_messages in by_chat.items():
        ordered = sorted(chat_messages, key=lambda m: m.get("created_at") or "")
        if not ordered:
            continue
        latest = ordered[-1]
        if latest.get("direction") != "incoming":
            continue
        open_items.append(
            {
                "chat_id": chat_id,
                "chat_title": latest.get("chat_title"),
                "chat_type": latest.get("chat_type"),
                "last_message_at": latest.get("created_at"),
                "last_text": (latest.get("text") or "")[:240],
                "from_user": latest.get("username") or f"User {latest.get('user_id')}",
                "reason": "last_inbound_unanswered",
            }
        )
    open_items.sort(key=lambda i: i.get("last_message_at") or "", reverse=True)
    return open_items
