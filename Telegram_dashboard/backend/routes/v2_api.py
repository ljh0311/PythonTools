"""v2 personal-awareness API: Talk / Act / Profiles."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from backend.models.store import store
from backend.routes.deps import verify_operator
from backend.services.ai_rate_limiter import RateLimitExceeded
from backend.services.ai_service import ai_service
from backend.services.profile_learner import learn_from_chat as profile_learn_from_chat
from backend.services import profile_md
from backend.services.ws_manager import ws_manager

router = APIRouter(prefix="/api/v2", tags=["v2"])

V2_ACT_FILTER_HASH = "v2-act"
_DEFAULT_INGESTION = "user_account"


class ActStatusRequest(BaseModel):
    status: str = Field(pattern="^(pending|done|dismissed)$")


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


def _chat_reply_state(chat_messages: list[dict[str, Any]]) -> dict[str, Any]:
    """Derive inbound/outbound reply state from stored chat messages."""
    ordered = sorted(chat_messages, key=lambda m: m.get("created_at") or "")
    incoming = [m for m in ordered if m.get("direction") == "incoming"]
    outgoing = [m for m in ordered if m.get("direction") == "outgoing"]
    last_in = incoming[-1] if incoming else None
    last_out = outgoing[-1] if outgoing else None
    last_in_at = (last_in or {}).get("created_at") or ""
    last_out_at = (last_out or {}).get("created_at") or ""
    already_replied = bool(last_in and last_out and last_out_at >= last_in_at)
    return {
        "already_replied": already_replied,
        "last_inbound_text": ((last_in or {}).get("text") or "")[:240],
        "last_outbound_text": ((last_out or {}).get("text") or "")[:240],
        "last_inbound_at": last_in_at or None,
        "last_outbound_at": last_out_at or None,
    }


def _messages_by_chat(messages: list[dict[str, Any]]) -> dict[int, list[dict[str, Any]]]:
    by_chat: dict[int, list[dict[str, Any]]] = {}
    for msg in messages:
        chat_id = msg.get("chat_id")
        if chat_id is None:
            continue
        by_chat.setdefault(int(chat_id), []).append(msg)
    return by_chat


def _enrich_with_reply_state(
    items: list[dict[str, Any]],
    by_chat: dict[int, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for item in items:
        row = dict(item)
        payload = row.get("payload")
        chat_id = row.get("chat_id")
        if chat_id is None and isinstance(payload, dict):
            chat_id = payload.get("chat_id")
        state = (
            _chat_reply_state(by_chat.get(int(chat_id), []))
            if chat_id is not None
            else {
                "already_replied": False,
                "last_inbound_text": "",
                "last_outbound_text": "",
                "last_inbound_at": None,
                "last_outbound_at": None,
            }
        )
        row.update(state)
        if isinstance(payload, dict):
            row["payload"] = {**payload, **state}
        enriched.append(row)
    return enriched


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
        reply_state = _chat_reply_state(chat_messages)
        open_items.append(
            {
                "chat_id": chat_id,
                "chat_title": latest.get("chat_title"),
                "chat_type": latest.get("chat_type"),
                "last_message_at": latest.get("created_at"),
                "last_text": (latest.get("text") or "")[:240],
                "from_user": latest.get("username") or f"User {latest.get('user_id')}",
                "reason": "last_inbound_unanswered",
                **reply_state,
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


@router.get("/act", dependencies=[Depends(verify_operator)])
async def act_queue(include_dismissed: bool = False) -> dict[str, Any]:
    suggestions = store.list_suggestions(
        filter_hash=V2_ACT_FILTER_HASH,
        include_dismissed=include_dismissed,
    )
    # Prefer pending/done; drop "sent" noise unless include_dismissed
    if not include_dismissed:
        suggestions = [s for s in suggestions if s.get("status") in ("pending", "done")]
    messages = _user_account_messages(limit=400)
    by_chat = _messages_by_chat(messages)
    return {
        "suggestions": _enrich_with_reply_state(suggestions, by_chat),
        "open_items": _heuristic_open_items(messages),
        "filter_hash": V2_ACT_FILTER_HASH,
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
    by_chat = _messages_by_chat(messages)
    return {
        "filter_hash": V2_ACT_FILTER_HASH,
        "suggestions": _enrich_with_reply_state(saved, by_chat),
        "summary": suggest_result.get("summary"),
        "provider": suggest_result.get("provider"),
        "intel": intel,
        "open_items": _heuristic_open_items(messages),
        "degraded": bool(suggest_result.get("degraded")),
        "failure_reason": suggest_result.get("failure_reason"),
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
    return updated


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
