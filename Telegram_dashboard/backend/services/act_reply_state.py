"""Act queue reply-state helpers: needs reply vs already replied."""

from __future__ import annotations

from typing import Any


def snippet(text: str | None, limit: int = 240) -> str:
    value = (text or "").strip()
    if len(value) <= limit:
        return value
    return value[: limit - 1].rstrip() + "…"


def messages_by_chat(messages: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    by_chat: dict[int, list[dict[str, Any]]] = {}
    for msg in messages:
        chat_id = msg.get("chat_id")
        if chat_id is None:
            continue
        by_chat.setdefault(int(chat_id), []).append(msg)
    return by_chat


def reply_state_for_messages(chat_messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive triage reply-state from a single chat's message history."""
    ordered = sorted(chat_messages, key=lambda m: m.get("created_at") or "")
    empty = {
        "reply_state": "unknown",
        "needs_reply": False,
        "already_replied": False,
        "last_inbound_text": "",
        "last_outbound_text": "",
        "last_inbound_at": None,
        "last_outbound_at": None,
        "last_direction": None,
    }
    if not ordered:
        return empty

    inbound = [m for m in ordered if m.get("direction") == "incoming"]
    outbound = [m for m in ordered if m.get("direction") == "outgoing"]
    last = ordered[-1]
    last_in = inbound[-1] if inbound else None
    last_out = outbound[-1] if outbound else None
    direction = last.get("direction")
    needs_reply = direction == "incoming"
    already_replied = direction == "outgoing"

    if needs_reply:
        reply_state = "needs_reply"
    elif already_replied:
        reply_state = "already_replied"
    else:
        reply_state = "unknown"

    return {
        "reply_state": reply_state,
        "needs_reply": needs_reply,
        "already_replied": already_replied,
        "last_inbound_text": snippet(last_in.get("text") if last_in else ""),
        "last_outbound_text": snippet(last_out.get("text") if last_out else ""),
        "last_inbound_at": last_in.get("created_at") if last_in else None,
        "last_outbound_at": last_out.get("created_at") if last_out else None,
        "last_direction": direction,
    }


def reply_state_map(messages: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {
        chat_id: reply_state_for_messages(msgs)
        for chat_id, msgs in messages_by_chat(messages).items()
    }


def flatten_suggestion(item: dict[str, Any]) -> dict[str, Any]:
    """Normalize list_suggestions (nested payload) and save_suggestions (flat)."""
    payload = item.get("payload") if isinstance(item.get("payload"), dict) else {}
    flat: dict[str, Any] = {**payload}
    for key in ("id", "status", "filter_hash", "created_at", "type"):
        if item.get(key) is not None:
            flat[key] = item[key]
    if not flat.get("type"):
        flat["type"] = "next_action"
    if "chat_id" not in flat and item.get("chat_id") is not None:
        flat["chat_id"] = item["chat_id"]
    return flat


def content_aware_fallback_draft(user: str, inbound_text: str, rel: str = "") -> str:
    """Outline draft grounded in last inbound — not a fake finished reply."""
    text = inbound_text.strip()
    name = ""
    if user and not str(user).startswith("User "):
        name = f", {user}"
    lines: list[str] = []
    if "?" in text:
        lines.append(f"Thanks for the note{name}.")
        lines.append(f'On your question about: "{snippet(text, 120)}"')
        lines.append("— [answer here]")
    else:
        lines.append(f"Got your message{name}:")
        lines.append(f'"{snippet(text, 140)}"')
        lines.append("— [your reply here]")
    if rel:
        lines.append(f"(context: {rel[:60]})")
    return "\n".join(lines)


def build_fallback_reply_suggestion(
    chat_id: int | None,
    chat_messages: list[dict[str, Any]],
    relationship_map: dict[int, str] | None = None,
) -> dict[str, Any] | None:
    """Build one fallback Act card from chat history (reply-state aware)."""
    state = reply_state_for_messages(chat_messages)
    ordered = sorted(chat_messages, key=lambda m: m.get("created_at") or "")
    if not ordered:
        return None

    inbound = [m for m in ordered if m.get("direction") == "incoming"]
    latest_in = inbound[-1] if inbound else None
    if latest_in:
        user = latest_in.get("username") or f"User {latest_in.get('user_id')}"
    else:
        last = ordered[-1]
        user = last.get("username") or last.get("chat_title") or f"Chat {chat_id}"

    rel = ""
    if chat_id is not None and relationship_map:
        rel = relationship_map.get(int(chat_id), "") or ""

    if state["already_replied"]:
        return {
            "type": "reply",
            "chat_id": chat_id,
            "user": user,
            "draft": "",
            "action": "Already replied — no draft needed",
            "priority": "low",
            "confidence": 0.9,
            "due_hint": "",
            "ai_unavailable": True,
            "draft_suppressed": True,
            "display_draft": "",
            **state,
        }

    if not state["needs_reply"]:
        return None

    inbound_text = state["last_inbound_text"]
    draft = (
        content_aware_fallback_draft(str(user), inbound_text, rel)
        if inbound_text
        else ""
    )
    action = f"Reply to {user}"
    if rel:
        action = f"{action} ({rel[:80]})"

    return {
        "type": "reply",
        "chat_id": chat_id,
        "user": user,
        "draft": draft,
        "action": action,
        "priority": "medium",
        "confidence": 0.45,
        "due_hint": "",
        "ai_unavailable": True,
        "draft_suppressed": False,
        "display_draft": draft,
        **state,
    }


def enrich_suggestion(
    item: dict[str, Any], state_by_chat: dict[int, dict[str, Any]]
) -> dict[str, Any]:
    """Attach live reply-state; suppress fake drafts when already replied / sent."""
    flat = flatten_suggestion(item)
    status = flat.get("status") or "pending"
    chat_id = flat.get("chat_id")
    state = state_by_chat.get(int(chat_id)) if chat_id is not None else None

    if state:
        flat.update(state)
    else:
        flat.setdefault("reply_state", "unknown")
        flat.setdefault("needs_reply", False)
        flat.setdefault("already_replied", False)
        flat.setdefault("last_inbound_text", "")
        flat.setdefault("last_outbound_text", "")

    if status == "sent":
        flat["reply_state"] = "sent"
        flat["draft_suppressed"] = True
        flat["display_draft"] = ""
    elif flat.get("already_replied") and status == "pending":
        flat["draft_suppressed"] = True
        flat["display_draft"] = ""
        flat["ai_draft_ignored"] = True
    else:
        flat["draft_suppressed"] = False
        flat["display_draft"] = flat.get("draft") or ""

    return flat


def enrich_suggestions(
    suggestions: list[dict[str, Any]], messages: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    state_by_chat = reply_state_map(messages)
    return [enrich_suggestion(item, state_by_chat) for item in suggestions]
