"""Needs-reply / attention digest: gather open items → AI/fallback → Telegram.

Scheduled via FastAPI lifespan; also invokable on demand from the v2 UI.
Uses Act's open-items heuristic (last message inbound) — not Telegram unread counts.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone
from typing import Any

from backend.config import (
    UNREAD_DIGEST_CHAT_ID,
    UNREAD_DIGEST_ENABLED,
    UNREAD_DIGEST_INTERVAL_MIN,
    UNREAD_DIGEST_MAX_THREADS,
    UNREAD_DIGEST_QUIET_END,
    UNREAD_DIGEST_QUIET_START,
)
from backend.models.store import store
from backend.services.act_open_items import heuristic_open_items
from backend.services.ai_service import ai_service
from backend.services.telegram_service import telegram_service

logger = logging.getLogger(__name__)

SETTING_ENABLED = "unread_digest_enabled"
SETTING_FINGERPRINT = "unread_digest_fingerprint"
SETTING_SENT_AT = "unread_digest_sent_at"
_DEFAULT_INGESTION = "user_account"
_MESSAGE_FETCH_LIMIT = 500

_loop_task: asyncio.Task[None] | None = None


def digest_chat_id() -> str:
    return (UNREAD_DIGEST_CHAT_ID or "").strip()


def is_digest_enabled() -> bool:
    """Runtime toggle (SQLite) overrides env default when explicitly set."""
    raw = store.get_setting(SETTING_ENABLED, "")
    if raw in ("0", "1", "true", "false", "yes", "no"):
        return raw.lower() in ("1", "true", "yes")
    return bool(UNREAD_DIGEST_ENABLED)


def set_digest_enabled(enabled: bool) -> bool:
    store.set_setting(SETTING_ENABLED, "true" if enabled else "false")
    return enabled


def in_quiet_hours(now: datetime | None = None) -> bool:
    start = UNREAD_DIGEST_QUIET_START
    end = UNREAD_DIGEST_QUIET_END
    if start is None or end is None:
        return False
    hour = (now or datetime.now()).hour
    if start == end:
        return False
    if start < end:
        return start <= hour < end
    # Wraps midnight, e.g. 23 → 7
    return hour >= start or hour < end


def fingerprint_open_items(items: list[dict[str, Any]]) -> str:
    parts = [
        f"{i.get('chat_id')}|{i.get('last_message_at') or ''}"
        for i in sorted(items, key=lambda x: int(x.get("chat_id") or 0))
    ]
    raw = "\n".join(parts)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def gather_open_items(
    *,
    max_threads: int | None = None,
    message_limit: int = _MESSAGE_FETCH_LIMIT,
) -> list[dict[str, Any]]:
    cap = max_threads if max_threads is not None else UNREAD_DIGEST_MAX_THREADS
    messages = store.query_messages(
        ingestion_source=_DEFAULT_INGESTION,
        limit=message_limit,
        offset=0,
    )["items"]
    items = heuristic_open_items(messages)
    if cap > 0:
        items = items[:cap]
    return items


def format_heuristic_digest(items: list[dict[str, Any]]) -> str:
    lines = [
        "Needs-reply digest",
        f"{len(items)} thread(s) waiting for a reply",
        "",
    ]
    for item in items:
        title = (
            item.get("chat_title")
            or item.get("from_user")
            or f"chat {item.get('chat_id')}"
        )
        snippet = (item.get("last_text") or "").replace("\n", " ").strip()
        if len(snippet) > 120:
            snippet = snippet[:117] + "..."
        when = item.get("last_message_at") or ""
        lines.append(f"• {title}")
        if when:
            lines.append(f"  {when}")
        if snippet:
            lines.append(f"  {snippet}")
        lines.append("")
    return "\n".join(lines).strip()


def _messages_for_summarize(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Build a compact message list for AI summarize (one synthetic inbound each)."""
    out: list[dict[str, Any]] = []
    for item in items:
        out.append(
            {
                "id": None,
                "chat_id": item.get("chat_id"),
                "chat_title": item.get("chat_title"),
                "username": item.get("from_user"),
                "text": item.get("last_text") or "(no text)",
                "created_at": item.get("last_message_at"),
                "direction": "incoming",
                "chat_type": item.get("chat_type"),
            }
        )
    return out


async def summarize_digest(items: list[dict[str, Any]]) -> tuple[str, str]:
    """Return (body_text, provider). Falls back to heuristic list on AI failure."""
    heuristic = format_heuristic_digest(items)
    try:
        result = await ai_service.summarize_messages(
            _messages_for_summarize(items),
            summary_type="unanswered",
        )
        summary = (result.get("summary") or "").strip()
        provider = str(result.get("provider") or "unknown")
        if result.get("degraded") or provider == "fallback" or not summary:
            return heuristic, "heuristic"
        return f"Needs-reply digest\n\n{summary}", provider
    except Exception as exc:  # noqa: BLE001 — digest must still send
        logger.warning("unread digest AI failed: %s", exc)
        return heuristic, "heuristic"


async def run_digest(
    *,
    force: bool = False,
    skip_quiet: bool = False,
) -> dict[str, Any]:
    """Gather → summarize/fallback → send. Returns a status dict (never raises for empty)."""
    if not force and not is_digest_enabled():
        return {"sent": False, "reason": "disabled"}

    if not force and not skip_quiet and in_quiet_hours():
        return {"sent": False, "reason": "quiet_hours"}

    chat_id = digest_chat_id()
    if not chat_id:
        return {"sent": False, "reason": "no_chat_id"}

    if not telegram_service.configured:
        return {"sent": False, "reason": "bot_not_configured"}

    items = gather_open_items()
    if not items:
        return {"sent": False, "reason": "empty", "open_items_count": 0}

    fp = fingerprint_open_items(items)
    prev = store.get_setting(SETTING_FINGERPRINT, "")
    if not force and prev and prev == fp:
        return {
            "sent": False,
            "reason": "unchanged",
            "fingerprint": fp,
            "open_items_count": len(items),
        }

    body, provider = await summarize_digest(items)
    # Telegram messages max 4096; keep digest short
    if len(body) > 3900:
        body = body[:3897] + "..."

    await telegram_service.send_message(chat_id, body)
    sent_at = datetime.now(timezone.utc).isoformat()
    store.set_setting(SETTING_FINGERPRINT, fp)
    store.set_setting(SETTING_SENT_AT, sent_at)

    logger.info(
        "unread digest sent chat=%s threads=%s provider=%s",
        chat_id,
        len(items),
        provider,
    )
    return {
        "sent": True,
        "reason": "ok",
        "fingerprint": fp,
        "open_items_count": len(items),
        "provider": provider,
        "sent_at": sent_at,
        "chat_id": chat_id,
    }


def digest_status() -> dict[str, Any]:
    return {
        "enabled": is_digest_enabled(),
        "env_enabled": bool(UNREAD_DIGEST_ENABLED),
        "chat_id_configured": bool(digest_chat_id()),
        "interval_min": UNREAD_DIGEST_INTERVAL_MIN,
        "max_threads": UNREAD_DIGEST_MAX_THREADS,
        "quiet_start": UNREAD_DIGEST_QUIET_START,
        "quiet_end": UNREAD_DIGEST_QUIET_END,
        "in_quiet_hours": in_quiet_hours(),
        "last_fingerprint": store.get_setting(SETTING_FINGERPRINT, "") or None,
        "last_sent_at": store.get_setting(SETTING_SENT_AT, "") or None,
        "bot_configured": telegram_service.configured,
    }


async def _digest_loop() -> None:
    interval_sec = max(60, UNREAD_DIGEST_INTERVAL_MIN * 60)
    logger.info(
        "unread digest loop started interval_min=%s",
        UNREAD_DIGEST_INTERVAL_MIN,
    )
    # Initial delay so startup does not compete with MTProto connect
    await asyncio.sleep(min(30, interval_sec))
    while True:
        try:
            if is_digest_enabled():
                result = await run_digest(force=False)
                if result.get("sent"):
                    logger.info("unread digest loop: sent")
                else:
                    logger.debug("unread digest loop skipped: %s", result.get("reason"))
        except asyncio.CancelledError:
            raise
        except Exception:  # noqa: BLE001
            logger.exception("unread digest loop iteration failed")
        await asyncio.sleep(interval_sec)


def start_digest_loop() -> asyncio.Task[None] | None:
    """Start background loop when env enabled OR when we want the loop for runtime toggle.

    Loop always starts so a UI enable can take effect without restart; each tick
    checks is_digest_enabled().
    """
    global _loop_task
    if _loop_task and not _loop_task.done():
        return _loop_task
    _loop_task = asyncio.create_task(_digest_loop(), name="unread_digest_loop")
    return _loop_task


async def stop_digest_loop() -> None:
    global _loop_task
    if _loop_task and not _loop_task.done():
        _loop_task.cancel()
        try:
            await _loop_task
        except asyncio.CancelledError:
            pass
    _loop_task = None
