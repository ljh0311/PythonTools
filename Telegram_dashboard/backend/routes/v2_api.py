"""v2 personal-awareness API: Talk / Act / Profiles."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.models.store import store
from backend.routes.deps import verify_operator
from backend.services.act_reply_state import enrich_suggestions, flatten_suggestion
from backend.services.ai_rate_limiter import RateLimitExceeded
from backend.services.ai_service import ai_service
from backend.services.mtproto_service import mtproto_service
from backend.services.profile_learner import learn_from_chat as profile_learn_from_chat
from backend.services import profile_md
from backend.services.send_errors import raise_send_http_error
from backend.services.ws_manager import ws_manager

router = APIRouter(prefix="/api/v2", tags=["v2"])

V2_ACT_FILTER_HASH = "v2-act"
_DEFAULT_INGESTION = "user_account"


class ActStatusRequest(BaseModel):
    status: str = Field(pattern="^(pending|done|dismissed|sent)$")


class ActSendRequest(BaseModel):
    text: str | None = Field(default=None, max_length=4096)


class ProfilePutRequest(BaseModel):
    markdown: str | None = None
    name: str | None = Field(default=None, max_length=200)
    summary: str | None = None
    relationship: str | None = None
    facts: str | None = None
    notes: str | None = None


def _raise_ai_http_error(exc: Exception) -> None:
    if isinstance(exc, RateLimitExceeded):
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    raise exc


def _user_account_messages(limit: int = 500) -> list[dict[str, Any]]:
    return store.query_messages(
        ingestion_source=_DEFAULT_INGESTION,
        limit=limit,
        offset=0,
    )["items"]


def _heuristic_open_items(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
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


# --- Talk ------------------------------------------------------------------


@router.get("/talk/threads", dependencies=[Depends(verify_operator)])
async def talk_threads(
    chat_type: str | None = None,
    q: str | None = None,
    limit: int = 20,
    offset: int = 0,
    ingestion_source: str = _DEFAULT_INGESTION,
) -> dict[str, Any]:
    if ingestion_source not in ("bot", "user_account"):
        raise HTTPException(
            status_code=400, detail="ingestion_source must be bot or user_account"
        )
    if chat_type and chat_type not in ("private", "group", "channel"):
        raise HTTPException(
            status_code=400, detail="chat_type must be private, group, or channel"
        )
    return store.query_threads(
        chat_type=chat_type,
        q=q,
        ingestion_source=ingestion_source,
        thread_limit=min(limit, 50),
        thread_offset=max(offset, 0),
    )


@router.get("/talk/threads/{chat_id}/messages", dependencies=[Depends(verify_operator)])
async def talk_thread_messages(
    chat_id: int,
    limit: int = 100,
    ingestion_source: str = _DEFAULT_INGESTION,
) -> dict[str, Any]:
    if ingestion_source not in ("bot", "user_account"):
        raise HTTPException(
            status_code=400, detail="ingestion_source must be bot or user_account"
        )
    messages = store.get_messages_by_chat_id(chat_id)
    if ingestion_source:
        messages = [
            m for m in messages if (m.get("ingestion_source") or "bot") == ingestion_source
        ]
    capped = messages[-min(max(limit, 1), 500) :]
    return {
        "chat_id": chat_id,
        "items": capped,
        "total": len(messages),
        "limit": min(max(limit, 1), 500),
    }


# --- Act -------------------------------------------------------------------


async def _mtproto_send_ready() -> dict[str, Any]:
    status = await mtproto_service.get_status()
    ready = bool(status.get("authorized") and status.get("connected"))
    reason = ""
    if ready:
        pass
    elif not status.get("configured"):
        reason = "MTProto not configured (TELEGRAM_API_ID / TELEGRAM_API_HASH)"
    elif not status.get("authorized"):
        reason = "Personal Telegram account not logged in (run mtproto_login.py)"
    elif not status.get("connected"):
        reason = "Personal Telegram account not connected"
    else:
        reason = "Personal account send unavailable"
    return {
        "ready": ready,
        "reason": reason,
        "status": status,
    }


@router.get("/act", dependencies=[Depends(verify_operator)])
async def act_queue(include_dismissed: bool = False) -> dict[str, Any]:
    suggestions = store.list_suggestions(
        filter_hash=V2_ACT_FILTER_HASH,
        include_dismissed=include_dismissed,
    )
    # Triage lifecycle: pending / done / sent (dismissed only when requested)
    if not include_dismissed:
        suggestions = [
            s for s in suggestions if s.get("status") in ("pending", "done", "sent")
        ]
    messages = _user_account_messages(limit=400)
    enriched = enrich_suggestions(suggestions, messages)
    send_info = await _mtproto_send_ready()
    return {
        "suggestions": enriched,
        "open_items": _heuristic_open_items(messages),
        "filter_hash": V2_ACT_FILTER_HASH,
        "send_available": send_info["ready"],
        "send_unavailable_reason": send_info["reason"],
    }


@router.post("/act/refresh", dependencies=[Depends(verify_operator)])
async def act_refresh() -> dict[str, Any]:
    messages = _user_account_messages(limit=500)
    chat_ids = list({m["chat_id"] for m in messages if m.get("chat_id") is not None})
    relationship_map = store.get_relationship_map(chat_ids)
    ai_context_map = store.get_ai_context_map(chat_ids)
    try:
        suggest_result = await ai_service.suggest_actions(
            messages, relationship_map, ai_context_map=ai_context_map
        )
        intel = await ai_service.conversation_intel(
            messages,
            relationship_map=relationship_map,
            ai_context_map=ai_context_map,
        )
    except RateLimitExceeded as exc:
        _raise_ai_http_error(exc)

    saved = store.save_suggestions(
        V2_ACT_FILTER_HASH, suggest_result.get("suggestions", [])
    )
    enriched = enrich_suggestions(saved, messages)
    send_info = await _mtproto_send_ready()
    return {
        "filter_hash": V2_ACT_FILTER_HASH,
        "suggestions": enriched,
        "summary": suggest_result.get("summary"),
        "provider": suggest_result.get("provider"),
        "intel": intel,
        "open_items": _heuristic_open_items(messages),
        "degraded": bool(suggest_result.get("degraded")),
        "send_available": send_info["ready"],
        "send_unavailable_reason": send_info["reason"],
    }


@router.patch("/act/{suggestion_id}", dependencies=[Depends(verify_operator)])
async def act_update_status(
    suggestion_id: int, body: ActStatusRequest
) -> dict[str, Any]:
    try:
        updated = store.update_suggestion_status(suggestion_id, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    await ws_manager.broadcast("suggestion_updated", updated)
    return flatten_suggestion(updated)


@router.post("/act/{suggestion_id}/send", dependencies=[Depends(verify_operator)])
async def act_send_draft(
    suggestion_id: int, body: ActSendRequest = ActSendRequest()
) -> dict[str, Any]:
    """Send draft via MTProto user account, then mark suggestion sent."""
    listed = store.list_suggestions(filter_hash=V2_ACT_FILTER_HASH, include_dismissed=True)
    match = next((s for s in listed if int(s.get("id") or 0) == int(suggestion_id)), None)
    if not match:
        raise HTTPException(status_code=404, detail="Suggestion not found")

    flat = flatten_suggestion(match)
    chat_id = flat.get("chat_id")
    text = (body.text or flat.get("draft") or "").strip()
    if chat_id is None:
        raise HTTPException(status_code=400, detail="Suggestion has no chat_id")
    if not text:
        raise HTTPException(status_code=400, detail="No draft text to send")

    send_info = await _mtproto_send_ready()
    if not send_info["ready"]:
        raise HTTPException(
            status_code=503,
            detail=send_info["reason"] or "Personal account send unavailable",
        )

    try:
        result = await mtproto_service.send_message(int(chat_id), text)
    except Exception as exc:
        raise_send_http_error(exc)

    status = send_info["status"]
    user = (status.get("user") or {}) if isinstance(status, dict) else {}
    store.add_message(
        user.get("id", 0),
        user.get("username"),
        "outgoing",
        text,
        chat_id=int(chat_id),
        message_id=result.get("message_id"),
        chat_type="private",
        ingestion_source="user_account",
    )

    updated = store.update_suggestion_status(suggestion_id, "sent")
    if not updated:
        raise HTTPException(status_code=404, detail="Suggestion not found after send")
    flat_updated = flatten_suggestion(updated)
    flat_updated["reply_state"] = "sent"
    flat_updated["draft_suppressed"] = True
    flat_updated["display_draft"] = ""
    flat_updated["last_outbound_text"] = text
    await ws_manager.broadcast("suggestion_updated", flat_updated)
    await ws_manager.broadcast(
        "message_sent",
        {"chat_id": chat_id, "text": text, "via": "user_account", "source": "act"},
    )
    return {"send": result, "suggestion": flat_updated}


# --- Profiles --------------------------------------------------------------


@router.get("/profiles", dependencies=[Depends(verify_operator)])
async def profiles_list() -> dict[str, Any]:
    return {"items": profile_md.list_profiles()}


@router.get("/profiles/{chat_id}", dependencies=[Depends(verify_operator)])
async def profiles_get(chat_id: int) -> dict[str, Any]:
    doc = profile_md.get_profile(chat_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Profile not found")
    return doc.to_dict()


@router.put("/profiles/{chat_id}", dependencies=[Depends(verify_operator)])
async def profiles_put(chat_id: int, body: ProfilePutRequest) -> dict[str, Any]:
    if body.markdown is not None:
        doc = profile_md.save_profile_markdown(chat_id, body.markdown)
        return doc.to_dict()

    existing = profile_md.get_profile(chat_id)
    if not existing and all(
        v is None
        for v in (body.name, body.summary, body.relationship, body.facts, body.notes)
    ):
        raise HTTPException(status_code=400, detail="No profile fields to save")

    doc = profile_md.ProfileDoc(
        chat_id=chat_id,
        name=body.name if body.name is not None else (existing.name if existing else f"Chat {chat_id}"),
        summary=body.summary if body.summary is not None else (existing.summary if existing else ""),
        relationship=(
            body.relationship
            if body.relationship is not None
            else (existing.relationship if existing else "")
        ),
        facts=body.facts if body.facts is not None else (existing.facts if existing else ""),
        notes=body.notes if body.notes is not None else (existing.notes if existing else ""),
        extra_frontmatter=existing.extra_frontmatter if existing else {},
    )
    return profile_md.write_profile(doc).to_dict()


@router.post("/profiles/{chat_id}/refresh", dependencies=[Depends(verify_operator)])
async def profiles_refresh(chat_id: int) -> dict[str, Any]:
    messages = store.get_messages_by_chat_id(chat_id)
    if not messages:
        raise HTTPException(status_code=404, detail="No messages for this chat")

    chat_meta = {
        "chat_type": messages[-1].get("chat_type"),
        "chat_title": messages[-1].get("chat_title"),
    }
    try:
        learned = await profile_learn_from_chat(chat_id, messages, chat_meta)
    except RateLimitExceeded as exc:
        _raise_ai_http_error(exc)

    saved = store.update_chat_settings(
        chat_id,
        relationship=learned.relationship,
        relationship_source=learned.relationship_source,
        ai_context=learned.ai_context,
    )
    saved_memories: list[dict[str, Any]] = []
    if learned.facts:
        store.clear_ai_memories(chat_id)
        saved_memories = store.add_chat_memories(
            chat_id,
            [{"type": "fact", "content": f} for f in learned.facts],
            source="ai",
        )

    name = (
        (saved or {}).get("chat_title")
        or messages[-1].get("chat_title")
        or f"Chat {chat_id}"
    )
    doc = profile_md.upsert_from_learn(
        chat_id,
        name=str(name),
        relationship=learned.relationship,
        ai_context=learned.ai_context,
        facts=learned.facts,
    )
    await ws_manager.broadcast("chat_reply_updated", saved)
    return {
        "profile": doc.to_dict(),
        "settings": saved,
        "learn": learned.to_learn_meta(),
        "memories": saved_memories or store.list_chat_memories(chat_id, limit=5),
    }
