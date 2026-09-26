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


def is_placeholder_peer_label(value: Any) -> bool:
    """True for empty or raw chat-id labels like 'chat -100…' / 'Chat 123'."""
    text = str(value or "").strip()
    if not text:
        return True
    lowered = text.lower()
    if lowered.startswith("chat ") or lowered.startswith("chat-"):
        rest = text.split(None, 1)[-1] if " " in text else text[4:]
        rest = rest.lstrip("-")
        return rest.isdigit()
    if lowered.startswith("user ") and text[5:].strip().isdigit():
        return False  # still a weak name, but keep for private fallbacks
    return False


def chat_peer_meta(chat_messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Best title + last inbound sender for Act card headers."""
    ordered = sorted(chat_messages, key=lambda m: m.get("created_at") or "")
    if not ordered:
        return {
            "chat_title": "",
            "chat_type": None,
            "from_user": "",
            "display_title": "",
        }
    latest = ordered[-1]
    chat_title = ""
    chat_type = None
    for msg in reversed(ordered):
        if not chat_title and (msg.get("chat_title") or "").strip():
            chat_title = str(msg.get("chat_title")).strip()
        if chat_type is None and msg.get("chat_type"):
            chat_type = msg.get("chat_type")
        if chat_title and chat_type:
            break

    inbound = [m for m in ordered if m.get("direction") == "incoming"]
    last_in = inbound[-1] if inbound else latest
    from_user = (last_in.get("username") or "").strip()
    if not from_user and last_in.get("user_id") is not None:
        from_user = f"User {last_in.get('user_id')}"

    ctype = chat_type or latest.get("chat_type")
    if ctype in ("group", "channel") and chat_title:
        display_title = chat_title
    elif from_user and not is_placeholder_peer_label(from_user):
        display_title = from_user
    elif chat_title:
        display_title = chat_title
    else:
        display_title = from_user

    return {
        "chat_title": chat_title,
        "chat_type": ctype,
        "from_user": from_user,
        "display_title": display_title,
    }


def peer_meta_map(messages: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    return {
        chat_id: chat_peer_meta(msgs)
        for chat_id, msgs in messages_by_chat(messages).items()
    }


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
    item: dict[str, Any],
    state_by_chat: dict[int, dict[str, Any]],
    peer_by_chat: dict[int, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Attach live reply-state; suppress fake drafts when already replied / sent."""
    flat = flatten_suggestion(item)
    status = flat.get("status") or "pending"
    chat_id = flat.get("chat_id")
    state = state_by_chat.get(int(chat_id)) if chat_id is not None else None
    peer = (peer_by_chat or {}).get(int(chat_id)) if chat_id is not None else None

    if state:
        flat.update(state)
    else:
        flat.setdefault("reply_state", "unknown")
        flat.setdefault("needs_reply", False)
        flat.setdefault("already_replied", False)
        flat.setdefault("last_inbound_text", "")
        flat.setdefault("last_outbound_text", "")

    if peer:
        if peer.get("chat_title"):
            flat["chat_title"] = peer["chat_title"]
        if peer.get("chat_type"):
            flat["chat_type"] = peer["chat_type"]
        if is_placeholder_peer_label(flat.get("user")) and peer.get("from_user"):
            flat["user"] = peer["from_user"]
        flat["display_title"] = (
            peer.get("display_title")
            or flat.get("user")
            or peer.get("chat_title")
            or flat.get("display_title")
            or ""
        )
    else:
        user = flat.get("user") or ""
        title = flat.get("chat_title") or ""
        if is_placeholder_peer_label(user):
            flat["display_title"] = title or user
        else:
            flat["display_title"] = user or title

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
    peer_by_chat = peer_meta_map(messages)
    return [
        enrich_suggestion(item, state_by_chat, peer_by_chat) for item in suggestions
    ]


def _queue_bucket(item: dict[str, Any]) -> int:
    status = item.get("status") or "pending"
    if item.get("needs_reply") and status == "pending":
        return 0
    if status == "pending" and not item.get("already_replied"):
        return 1
    if status == "pending":
        return 2
    if status == "done":
        return 3
    if status == "sent":
        return 4
    return 5


def sort_act_queue(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Needs-reply pending first (newest inbound), then other pending, then done/sent."""

    def when(item: dict[str, Any]) -> str:
        return (
            item.get("last_inbound_at")
            or item.get("created_at")
            or item.get("last_outbound_at")
            or ""
        )

    # Newest first within bucket via stable sort
    dated = sorted(items, key=when, reverse=True)
    return sorted(dated, key=_queue_bucket)


def merge_open_items(
    suggestions: list[dict[str, Any]], open_items: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Ensure every unanswered chat appears even if AI omitted a draft."""
    covered: set[int] = set()
    for item in suggestions:
        chat_id = item.get("chat_id")
        if chat_id is None:
            continue
        if item.get("needs_reply") and (item.get("status") or "pending") == "pending":
            covered.add(int(chat_id))

    merged = list(suggestions)
    for oi in open_items:
        chat_id = oi.get("chat_id")
        if chat_id is None or int(chat_id) in covered:
            continue
        who = oi.get("chat_title") or oi.get("from_user") or f"Chat {chat_id}"
        last_text = oi.get("last_text") or ""
        ctype = oi.get("chat_type")
        from_user = oi.get("from_user") or ""
        merged.append(
            {
                "id": f"open-{chat_id}",
                "status": "pending",
                "type": "reply",
                "chat_id": int(chat_id),
                "chat_title": oi.get("chat_title") or "",
                "chat_type": ctype,
                "user": from_user or who,
                "display_title": who,
                "draft": "",
                "display_draft": "",
                "action": f"Reply to {from_user or who}",
                "priority": "high",
                "confidence": 0.7,
                "due_hint": "today",
                "created_at": oi.get("last_message_at"),
                "reply_state": "needs_reply",
                "needs_reply": True,
                "already_replied": False,
                "last_inbound_text": last_text,
                "last_outbound_text": "",
                "last_inbound_at": oi.get("last_message_at"),
                "last_outbound_at": None,
                "last_direction": "incoming",
                "draft_suppressed": False,
                "ai_unavailable": True,
                "from_open_items": True,
            }
        )
        covered.add(int(chat_id))
    return sort_act_queue(merged)
