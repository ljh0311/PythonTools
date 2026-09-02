import csv
import io
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from backend.config import DASHBOARD_API_KEY
from backend.models.store import store
from backend.routes.deps import verify_operator
from backend.services.ai_service import ai_service
from backend.services.profile_learner import learn_from_chat as profile_learn_from_chat
from backend.services.auth_service import validate_token
from backend.services.ai_rate_limiter import RateLimitExceeded, ai_rate_limiter
from backend.services.mtproto_service import mtproto_service
from backend.services.send_errors import raise_send_http_error
from backend.services.telegram_service import telegram_service
from backend.services.ws_manager import ws_manager


router = APIRouter(prefix="/api", tags=["dashboard"])


class SendMessageRequest(BaseModel):
    chat_id: int | str
    text: str = Field(min_length=1, max_length=4096)


class QuickAction(BaseModel):
    label: str
    command: str
    enabled: bool = True


class QuickActionsRequest(BaseModel):
    actions: list[QuickAction]


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=1, max_length=1000)
    user_id: int | None = None
    username: str | None = None


class SummarizeThreadRequest(BaseModel):
    chat_id: int
    message_ids: list[int] | None = None
    force: bool = False


class FilteredAiRequest(BaseModel):
    summary_type: str = "brief"
    user_ids: str = ""
    chat_type: str | None = None
    direction: str | None = None
    ingestion_source: str | None = None
    q: str | None = None
    topics: str | None = None
    date_from: str | None = None
    date_to: str | None = None


class ReplyModeRequest(BaseModel):
    mode: str = Field(pattern="^(manual|auto|per_chat)$")


class TopicModeRequest(BaseModel):
    mode: str = Field(pattern="^(user_type|ai_assign)$")


class ChatSettingsRequest(BaseModel):
    enabled: bool | None = None
    relationship: str | None = Field(default=None, max_length=2000)
    ai_context: str | None = Field(default=None, max_length=4000)


class MessageTopicsRequest(BaseModel):
    topics: list[str] = Field(min_length=1)


class TopicBackfillRequest(BaseModel):
    limit: int = Field(default=50, ge=1, le=200)
    enable_ai_mode: bool = False


class SuggestionStatusRequest(BaseModel):
    status: str = Field(pattern="^(pending|sent|dismissed|done)$")


class FilterPresetRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    filters: dict[str, Any]


def _fetch_filtered_messages(body: FilteredAiRequest, limit: int = 500) -> tuple[list[dict], dict]:
    parsed_user_ids, chat_type, direction, date_from, date_to, ingestion_source = (
        _parse_message_filters(
            body.user_ids,
            body.chat_type,
            body.direction,
            body.date_from,
            body.date_to,
            body.ingestion_source,
        )
    )
    filters = {
        "user_ids": body.user_ids,
        "chat_type": body.chat_type,
        "direction": body.direction,
        "ingestion_source": body.ingestion_source,
        "q": body.q,
        "topics": body.topics,
        "date_from": body.date_from,
        "date_to": body.date_to,
    }
    result = store.query_messages(
        user_ids=parsed_user_ids,
        chat_type=chat_type,
        direction=direction,
        ingestion_source=ingestion_source,
        q=body.q,
        topics=body.topics,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
        offset=0,
    )
    return result["items"], filters


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/metrics", dependencies=[Depends(verify_operator)])
async def metrics() -> dict[str, Any]:
    return store.metrics()


@router.get("/users", dependencies=[Depends(verify_operator)])
async def users() -> list[dict[str, Any]]:
    return store.list_users()


@router.get("/compose-recipients", dependencies=[Depends(verify_operator)])
async def compose_recipients() -> list[dict[str, Any]]:
    store.sync_chat_settings_from_messages()
    return store.list_compose_recipients()


def _parse_message_filters(
    user_ids: str,
    chat_type: str | None,
    direction: str | None,
    date_from: str | None,
    date_to: str | None,
    ingestion_source: str | None = None,
) -> tuple[list[int] | None, str | None, str | None, str | None, str | None, str | None]:
    parsed_user_ids: list[int] | None = None
    if user_ids.strip():
        parsed_user_ids = [int(uid) for uid in user_ids.split(",") if uid.strip()]

    if chat_type and chat_type not in ("private", "group", "channel"):
        raise HTTPException(
            status_code=400, detail="chat_type must be private, group, or channel"
        )

    if direction and direction not in ("incoming", "outgoing"):
        raise HTTPException(status_code=400, detail="direction must be incoming or outgoing")

    if ingestion_source and ingestion_source not in ("bot", "user_account"):
        raise HTTPException(
            status_code=400, detail="ingestion_source must be bot or user_account"
        )

    if date_from and len(date_from) == 10:
        date_from = f"{date_from}T00:00:00"
    if date_to and len(date_to) == 10:
        date_to = f"{date_to}T23:59:59"

    return parsed_user_ids, chat_type, direction, date_from, date_to, ingestion_source


async def _expand_topics_filter(topics: str | None) -> str | None:
    """Use AI to expand a free-text topic filter into related tags + keywords."""
    if not topics or not topics.strip():
        return topics
    available = [item["name"] for item in store.list_topics()]
    try:
        expanded = await ai_service.expand_filter_query(topics.strip(), available)
    except Exception:
        return topics
    terms: list[str] = []
    seen: set[str] = set()
    for term in [*expanded.get("topics", []), *expanded.get("keywords", [])]:
        cleaned = str(term).strip().lower()
        if cleaned and cleaned not in seen:
            seen.add(cleaned)
            terms.append(cleaned)
    return ",".join(terms) if terms else topics


@router.get("/messages", dependencies=[Depends(verify_operator)])
async def messages(
    user_ids: str = "",
    chat_type: str | None = None,
    direction: str | None = None,
    ingestion_source: str | None = None,
    q: str | None = None,
    topics: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    parsed_user_ids, chat_type, direction, date_from, date_to, ingestion_source = (
        _parse_message_filters(
            user_ids, chat_type, direction, date_from, date_to, ingestion_source
        )
    )
    topics = await _expand_topics_filter(topics)
    return store.query_messages(
        user_ids=parsed_user_ids,
        chat_type=chat_type,
        direction=direction,
        ingestion_source=ingestion_source,
        q=q,
        topics=topics,
        date_from=date_from,
        date_to=date_to,
        limit=min(limit, 200),
        offset=offset,
    )


@router.get("/inbox/threads", dependencies=[Depends(verify_operator)])
async def inbox_threads(
    user_ids: str = "",
    chat_type: str | None = None,
    direction: str | None = None,
    ingestion_source: str | None = None,
    q: str | None = None,
    topics: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 20,
    offset: int = 0,
) -> dict[str, Any]:
    parsed_user_ids, chat_type, direction, date_from, date_to, ingestion_source = (
        _parse_message_filters(
            user_ids, chat_type, direction, date_from, date_to, ingestion_source
        )
    )
    topics = await _expand_topics_filter(topics)
    return store.query_threads(
        user_ids=parsed_user_ids,
        chat_type=chat_type,
        direction=direction,
        ingestion_source=ingestion_source,
        q=q,
        topics=topics,
        date_from=date_from,
        date_to=date_to,
        thread_limit=min(limit, 50),
        thread_offset=offset,
    )


def _thread_messages(body: SummarizeThreadRequest) -> list[dict[str, Any]]:
    if body.message_ids:
        return store.get_messages_by_ids(body.message_ids)
    return store.get_messages_by_chat_id(body.chat_id)


def _raise_ai_http_error(exc: Exception) -> None:
    if isinstance(exc, RateLimitExceeded):
        raise HTTPException(
            status_code=429,
            detail=str(exc),
            headers={"Retry-After": str(exc.retry_after)},
        ) from exc
    raise exc


@router.get("/ai/thread-summary/{chat_id}", dependencies=[Depends(verify_operator)])
async def get_thread_summary(
    chat_id: int,
    message_ids: str = "",
) -> dict[str, Any]:
    ids = [int(x) for x in message_ids.split(",") if x.strip()] if message_ids.strip() else []
    if not ids:
        messages = store.get_messages_by_chat_id(chat_id)
        ids = [int(m["id"]) for m in messages if m.get("id") is not None]
    cached = ai_service.get_cached_thread_summary(chat_id, ids)
    if not cached:
        return {"chat_id": chat_id, "cached": False, "summary": None}
    return {"chat_id": chat_id, **cached}


@router.post("/ai/summarize-thread", dependencies=[Depends(verify_operator)])
async def summarize_thread(body: SummarizeThreadRequest) -> dict[str, Any]:
    messages = _thread_messages(body)
    if not messages:
        raise HTTPException(status_code=404, detail="No messages for this chat")
    try:
        result = await ai_service.summarize_thread(
            messages,
            chat_id=body.chat_id,
            force=body.force,
            relationship=store.get_relationship_map([body.chat_id]).get(body.chat_id, ""),
            ai_context=store.get_ai_context_map([body.chat_id]).get(body.chat_id, ""),
        )
    except RateLimitExceeded as exc:
        _raise_ai_http_error(exc)
    return {"chat_id": body.chat_id, **result}


@router.post("/ai/summarize", dependencies=[Depends(verify_operator)])
async def summarize_filtered(body: FilteredAiRequest) -> dict[str, Any]:
    if body.summary_type not in ("brief", "detailed", "bullets", "unanswered"):
        raise HTTPException(status_code=400, detail="Invalid summary_type")
    messages, filters = _fetch_filtered_messages(body)
    chat_ids = list({m["chat_id"] for m in messages if m.get("chat_id") is not None})
    try:
        return await ai_service.summarize_messages(
            messages,
            summary_type=body.summary_type,
            filters={**filters, "summary_type": body.summary_type},
            relationship_map=store.get_relationship_map(chat_ids),
            ai_context_map=store.get_ai_context_map(chat_ids),
        )
    except RateLimitExceeded as exc:
        _raise_ai_http_error(exc)


@router.post("/ai/suggest-actions", dependencies=[Depends(verify_operator)])
async def suggest_actions(body: FilteredAiRequest) -> dict[str, Any]:
    messages, filters = _fetch_filtered_messages(body)
    chat_ids = list({m["chat_id"] for m in messages if m.get("chat_id") is not None})
    relationship_map = store.get_relationship_map(chat_ids)
    ai_context_map = store.get_ai_context_map(chat_ids)
    try:
        result = await ai_service.suggest_actions(
            messages, relationship_map, ai_context_map=ai_context_map
        )
    except RateLimitExceeded as exc:
        _raise_ai_http_error(exc)
    fhash = store.filter_hash(filters)
    saved = store.save_suggestions(fhash, result.get("suggestions", []))
    return {**result, "filter_hash": fhash, "suggestions": saved}


@router.post("/ai/conversation-intel", dependencies=[Depends(verify_operator)])
async def conversation_intel(body: FilteredAiRequest) -> dict[str, Any]:
    messages, _filters = _fetch_filtered_messages(body)
    chat_ids = list({m["chat_id"] for m in messages if m.get("chat_id") is not None})
    try:
        return await ai_service.conversation_intel(
            messages,
            relationship_map=store.get_relationship_map(chat_ids),
            ai_context_map=store.get_ai_context_map(chat_ids),
        )
    except RateLimitExceeded as exc:
        _raise_ai_http_error(exc)


async def _ensure_chat_relationships() -> None:
    store.sync_chat_settings_from_messages()
    for chat_id in store.chats_missing_relationship():
        messages = store.get_messages_by_chat_id(chat_id)
        if not messages:
            continue
        chat_type = messages[-1].get("chat_type")
        chat_title = messages[-1].get("chat_title")
        generated = await ai_service.generate_relationship(
            messages, chat_type=chat_type, chat_title=chat_title
        )
        store.set_chat_relationship(
            chat_id, generated["relationship"], source=generated["source"]
        )


@router.get("/settings/reply-mode", dependencies=[Depends(verify_operator)])
async def get_reply_mode() -> dict[str, Any]:
    await _ensure_chat_relationships()
    return {
        "mode": store.get_reply_mode(),
        "chats": store.list_chat_settings(),
    }


@router.put("/settings/reply-mode", dependencies=[Depends(verify_operator)])
async def set_reply_mode(body: ReplyModeRequest) -> dict[str, Any]:
    try:
        store.set_reply_mode(body.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    store.sync_chat_settings_from_messages()
    payload = {"mode": body.mode, "chats": store.list_chat_settings()}
    await ws_manager.broadcast("reply_mode_updated", payload)
    return payload


@router.get("/settings/chat-replies/{chat_id}", dependencies=[Depends(verify_operator)])
async def get_chat_settings(chat_id: int) -> dict[str, Any]:
    store.sync_chat_settings_from_messages()
    saved = store.get_chat_setting(chat_id)
    if not saved:
        raise HTTPException(status_code=404, detail="Chat not found")
    return saved


@router.put("/settings/chat-replies/{chat_id}", dependencies=[Depends(verify_operator)])
async def update_chat_settings(chat_id: int, body: ChatSettingsRequest) -> dict[str, Any]:
    if body.enabled is None and body.relationship is None and body.ai_context is None:
        raise HTTPException(status_code=400, detail="No settings to update")
    try:
        saved = store.update_chat_settings(
            chat_id,
            enabled=body.enabled,
            relationship=body.relationship,
            relationship_source="manual" if body.relationship is not None else None,
            ai_context=body.ai_context,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    await ws_manager.broadcast("chat_reply_updated", saved)
    return saved


@router.post(
    "/settings/chat-replies/{chat_id}/regenerate-relationship",
    dependencies=[Depends(verify_operator)],
)
async def regenerate_chat_relationship(chat_id: int) -> dict[str, Any]:
    messages = store.get_messages_by_chat_id(chat_id)
    if not messages:
        raise HTTPException(status_code=404, detail="No messages for this chat")
    chat_type = messages[-1].get("chat_type")
    chat_title = messages[-1].get("chat_title")
    generated = await ai_service.generate_relationship(
        messages, chat_type=chat_type, chat_title=chat_title
    )
    saved = store.set_chat_relationship(
        chat_id, generated["relationship"], source=generated["source"]
    )
    await ws_manager.broadcast("chat_relationship_updated", saved)
    return saved


@router.post(
    "/settings/chat-replies/{chat_id}/learn",
    dependencies=[Depends(verify_operator)],
)
async def learn_from_chat(chat_id: int) -> dict[str, Any]:
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
    await ws_manager.broadcast("chat_reply_updated", saved)
    return {
        "settings": saved,
        "learn": learned.to_learn_meta(),
        "memories": saved_memories or store.list_chat_memories(chat_id, limit=5),
    }


@router.get("/chats/{chat_id}/memories", dependencies=[Depends(verify_operator)])
async def list_chat_memories(chat_id: int, limit: int = 10) -> dict[str, Any]:
    if not store.get_chat_setting(chat_id):
        store.sync_chat_settings_from_messages()
    if not store.get_chat_setting(chat_id):
        raise HTTPException(status_code=404, detail="Chat not found")
    memories = store.list_chat_memories(chat_id, limit=min(limit, 50))
    return {"chat_id": chat_id, "memories": memories}


@router.post("/chats/{chat_id}/learn", dependencies=[Depends(verify_operator)])
async def learn_chat_profile(chat_id: int) -> dict[str, Any]:
    messages = store.get_messages_by_chat_id(chat_id)
    if not messages:
        raise HTTPException(status_code=404, detail="No messages for this chat")
    chat_type = messages[-1].get("chat_type")
    chat_title = messages[-1].get("chat_title")
    existing = store.list_chat_memories(chat_id, limit=12)
    try:
        learned = await ai_service.learn_profile_from_thread(
            messages,
            chat_type=chat_type,
            chat_title=chat_title,
            existing_memories=existing,
        )
    except RateLimitExceeded as exc:
        _raise_ai_http_error(exc)

    store.clear_ai_memories(chat_id)
    saved_memories = store.add_chat_memories(
        chat_id, learned.get("memories", []), source="ai"
    )
    saved_settings = store.update_chat_settings(
        chat_id,
        relationship=learned.get("relationship", ""),
        relationship_source="ai",
        ai_context=learned.get("ai_context", ""),
    )
    payload = {
        "chat_id": chat_id,
        "memories": saved_memories,
        "relationship": saved_settings.get("relationship", ""),
        "ai_context": saved_settings.get("ai_context", ""),
        "settings": saved_settings,
        "source": learned.get("source", "ai"),
    }
    if learned.get("degraded"):
        payload["degraded"] = True
        payload["failure_reason"] = learned.get("failure_reason")
    await ws_manager.broadcast("chat_profile_learned", payload)
    return payload


@router.get("/settings/topic-mode", dependencies=[Depends(verify_operator)])
async def get_topic_mode() -> dict[str, str]:
    return {"mode": store.get_topic_mode()}


@router.put("/settings/topic-mode", dependencies=[Depends(verify_operator)])
async def set_topic_mode(body: TopicModeRequest) -> dict[str, str]:
    try:
        mode = store.set_topic_mode(body.mode)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await ws_manager.broadcast("topic_mode_updated", {"mode": mode})
    return {"mode": mode}


@router.get("/topics", dependencies=[Depends(verify_operator)])
async def list_topics() -> list[dict[str, Any]]:
    return store.list_topics()


@router.post("/topics/backfill", dependencies=[Depends(verify_operator)])
async def backfill_topics(body: TopicBackfillRequest) -> dict[str, Any]:
    current_mode = store.get_topic_mode()
    if current_mode != "ai_assign" and not body.enable_ai_mode:
        raise HTTPException(
            status_code=400,
            detail=(
                "Topic mode is user_type — AI tagging is disabled. "
                "Switch to AI assign in Workflow settings, or pass enable_ai_mode: true."
            ),
        )

    # Persist AI assign so future inbound messages keep getting tags.
    if body.enable_ai_mode and current_mode != "ai_assign":
        current_mode = store.set_topic_mode("ai_assign")
        await ws_manager.broadcast("topic_mode_updated", {"mode": current_mode})

    untagged = store.list_recent_untagged_messages(body.limit)
    tagged = 0
    topics_created: set[str] = set()

    for msg in untagged:
        text = (msg.get("text") or "").strip()
        if not text:
            continue
        try:
            topics = await ai_service.assign_topics(text)
        except RateLimitExceeded as exc:
            if tagged == 0:
                _raise_ai_http_error(exc)
            break
        if not topics:
            continue
        added = store.add_message_topics(msg["id"], topics, source="ai")
        if added:
            tagged += 1
            topics_created.update(added)

    return {
        "processed": len(untagged),
        "tagged": tagged,
        "topics_created": sorted(topics_created),
        "topic_mode": current_mode,
    }


@router.post("/messages/{message_id}/topics", dependencies=[Depends(verify_operator)])
async def add_message_topics(message_id: int, body: MessageTopicsRequest) -> dict[str, Any]:
    added = store.add_message_topics(message_id, body.topics, source="manual")
    return {"message_id": message_id, "topics": added}


@router.delete(
    "/messages/{message_id}/topics/{topic_name}",
    dependencies=[Depends(verify_operator)],
)
async def remove_message_topic(message_id: int, topic_name: str) -> dict[str, Any]:
    removed = store.remove_message_topic(message_id, topic_name)
    if not removed:
        raise HTTPException(status_code=404, detail="Topic not found on message")
    return {"message_id": message_id, "removed": topic_name}


@router.get("/suggestions", dependencies=[Depends(verify_operator)])
async def list_suggestions(
    filter_hash: str | None = None,
    include_dismissed: bool = False,
) -> list[dict[str, Any]]:
    return store.list_suggestions(filter_hash, include_dismissed)


@router.patch("/suggestions/{suggestion_id}", dependencies=[Depends(verify_operator)])
async def update_suggestion_status(
    suggestion_id: int, body: SuggestionStatusRequest
) -> dict[str, Any]:
    try:
        updated = store.update_suggestion_status(suggestion_id, body.status)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not updated:
        raise HTTPException(status_code=404, detail="Suggestion not found")
    await ws_manager.broadcast("suggestion_updated", updated)
    return updated


@router.get("/events", dependencies=[Depends(verify_operator)])
async def events(limit: int = 50) -> list[dict[str, Any]]:
    return store.recent_events(limit)


@router.get("/analytics/commands", dependencies=[Depends(verify_operator)])
async def command_analytics(days: int = 7) -> dict[str, Any]:
    return store.command_usage_over_time(days)


@router.get("/quick-actions", dependencies=[Depends(verify_operator)])
async def get_quick_actions() -> list[dict[str, Any]]:
    return store.list_quick_actions()


@router.put("/quick-actions", dependencies=[Depends(verify_operator)])
async def update_quick_actions(body: QuickActionsRequest) -> list[dict[str, Any]]:
    actions = [action.model_dump() for action in body.actions]
    saved = store.save_quick_actions(actions)
    await ws_manager.broadcast("quick_actions_updated", {"actions": saved})
    return saved


@router.get("/feedback", dependencies=[Depends(verify_operator)])
async def feedback(limit: int = 20) -> list[dict[str, Any]]:
    return store.recent_feedback(limit)


@router.post("/feedback", dependencies=[Depends(verify_operator)])
async def submit_feedback(body: FeedbackRequest) -> dict[str, Any]:
    item = store.add_feedback(body.user_id, body.username, body.rating, body.comment)
    await ws_manager.broadcast("feedback_received", item)
    return item


@router.post("/send", dependencies=[Depends(verify_operator)])
async def send_message(body: SendMessageRequest) -> dict[str, Any]:
    if not telegram_service.configured:
        raise HTTPException(status_code=400, detail="Telegram bot token not configured")

    raw_target = str(body.chat_id).strip()
    chat_id_int = store.resolve_compose_target(raw_target)
    if chat_id_int is None and raw_target.lstrip("-").isdigit():
        chat_id_int = int(raw_target)
    if chat_id_int is None:
        raise HTTPException(
            status_code=400,
            detail="Unknown recipient. Pick @username from the list or enter a numeric chat ID.",
        )

    try:
        result = await telegram_service.send_message(chat_id_int, body.text)
    except Exception as exc:
        raise_send_http_error(exc)
    store.add_message(
        0,
        "operator",
        "outgoing",
        body.text,
        chat_id=chat_id_int,
        chat_type="private",
        ingestion_source="bot",
    )
    await ws_manager.broadcast(
        "message_sent", {"chat_id": body.chat_id, "text": body.text}
    )
    return result


@router.get("/ai/status", dependencies=[Depends(verify_operator)])
async def ai_status() -> dict[str, Any]:
    return await ai_service.provider_status()


@router.get("/bot/status", dependencies=[Depends(verify_operator)])
async def bot_status() -> dict[str, Any]:
    if not telegram_service.configured:
        return {"configured": False, "bot": None}
    try:
        me = await telegram_service.get_me()
        return {"configured": True, "bot": me.get("result")}
    except Exception as exc:
        return {"configured": True, "bot": None, "error": str(exc)}


@router.get("/setup-status", dependencies=[Depends(verify_operator)])
async def setup_status() -> dict[str, Any]:
    warnings: list[str] = []

    bot: dict[str, Any] = {
        "configured": telegram_service.configured,
        "verified": False,
        "username": None,
    }
    if not bot["configured"]:
        warnings.append("Telegram bot token not configured (TELEGRAM_BOT_TOKEN)")
    else:
        try:
            me = await telegram_service.get_me()
            bot_user = me.get("result")
            if bot_user:
                bot["verified"] = True
                bot["username"] = bot_user.get("username")
            else:
                warnings.append("Bot token set but verification returned no bot profile")
        except Exception as exc:
            warnings.append(f"Bot token invalid or unreachable: {exc}")

    ua_raw = await mtproto_service.get_status()
    user_account = {
        "configured": bool(ua_raw.get("configured")),
        "authorized": bool(ua_raw.get("authorized")),
        "listening": bool(ua_raw.get("listening")),
    }
    if not user_account["configured"]:
        warnings.append(
            "User account not configured (TELEGRAM_API_ID + TELEGRAM_API_HASH)"
        )
    elif not user_account["authorized"]:
        warnings.append("User account not logged in (run scripts/mtproto_login.py)")
    elif not user_account["listening"]:
        warnings.append(
            "User account logged in but not listening (set MTProto_ENABLED=true and restart)"
        )

    ai_raw = await ai_service.provider_status()
    ai = {
        "gemini": bool(ai_raw.get("gemini", {}).get("configured")),
        "ollama": bool(
            ai_raw.get("ollama", {}).get("configured")
            and ai_raw.get("ollama", {}).get("available")
        ),
    }
    if not ai["gemini"] and not ai["ollama"]:
        warnings.append("No AI provider available (configure GEMINI_API_KEY or Ollama)")

    return {"bot": bot, "user_account": user_account, "ai": ai, "warnings": warnings}


@router.get("/export/messages", dependencies=[Depends(verify_operator)])
async def export_messages(
    user_ids: str = "",
    chat_type: str | None = None,
    direction: str | None = None,
    ingestion_source: str | None = None,
    q: str | None = None,
    topics: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    limit: int = 1000,
) -> StreamingResponse:
    parsed_user_ids, chat_type, direction, date_from, date_to, ingestion_source = (
        _parse_message_filters(
            user_ids, chat_type, direction, date_from, date_to, ingestion_source
        )
    )
    result = store.query_messages(
        user_ids=parsed_user_ids,
        chat_type=chat_type,
        direction=direction,
        ingestion_source=ingestion_source,
        q=q,
        topics=topics,
        date_from=date_from,
        date_to=date_to,
        limit=min(limit, 5000),
        offset=0,
    )
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(
        [
            "id",
            "user_id",
            "username",
            "direction",
            "text",
            "chat_id",
            "chat_type",
            "chat_title",
            "created_at",
            "ingestion_source",
            "topics",
        ]
    )
    for item in result["items"]:
        topics_str = ",".join(t["name"] for t in item.get("topics", []))
        writer.writerow(
            [
                item.get("id"),
                item.get("user_id"),
                item.get("username"),
                item.get("direction"),
                item.get("text"),
                item.get("chat_id"),
                item.get("chat_type"),
                item.get("chat_title"),
                item.get("created_at"),
                item.get("ingestion_source", "bot"),
                topics_str,
            ]
        )
    buffer.seek(0)
    return StreamingResponse(
        iter([buffer.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=messages-export.csv"},
    )


@router.get("/presets", dependencies=[Depends(verify_operator)])
async def list_presets() -> list[dict[str, Any]]:
    return store.list_filter_presets()


@router.post("/presets", dependencies=[Depends(verify_operator)])
async def save_preset(body: FilterPresetRequest) -> dict[str, Any]:
    return store.save_filter_preset(body.name, body.filters)


@router.delete("/presets/{preset_id}", dependencies=[Depends(verify_operator)])
async def delete_preset(preset_id: int) -> dict[str, str]:
    if not store.delete_filter_preset(preset_id):
        raise HTTPException(status_code=404, detail="Preset not found")
    return {"status": "deleted"}


@router.websocket("/ws")
async def dashboard_ws(websocket: WebSocket, api_key: str = "", token: str = ""):
    credential = token or api_key
    if not validate_token(credential):
        await websocket.close(code=1008)
        return

    await ws_manager.connect(websocket)
    try:
        await websocket.send_json(
            {
                "event": "snapshot",
                "data": {
                    "metrics": store.metrics(),
                    "messages": store.recent_messages(20),
                    "events": store.recent_events(20),
                    "quick_actions": store.list_quick_actions(),
                    "analytics": store.command_usage_over_time(),
                    "feedback": store.recent_feedback(10),
                },
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
