"""Act queue quality + performance logging.

Tracks:
- false needs-reply (AI/store claim vs live last-message direction)
- missing dues (open unanswered chats omitted before merge; empty due_hint)
- queue refresh / load timing
- triage feedback (dismiss/done on needs-reply items)
"""

from __future__ import annotations

import logging
import time
from typing import Any

logger = logging.getLogger("act_quality")


def _chat_id(item: dict[str, Any]) -> int | None:
    raw = item.get("chat_id")
    if raw is None:
        return None
    try:
        return int(raw)
    except (TypeError, ValueError):
        return None


def analyze_queue_quality(
    *,
    raw_suggestions: list[dict[str, Any]],
    enriched_before_merge: list[dict[str, Any]],
    open_items: list[dict[str, Any]],
    final_queue: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compute quality counters for one Act load/refresh."""
    false_needs: list[dict[str, Any]] = []
    for item in enriched_before_merge:
        status = item.get("status") or "pending"
        if status != "pending":
            continue
        # Stored/AI draft treated as a live reply need, but history says already replied
        claimed_reply = (item.get("type") or "") == "reply" and bool(
            (item.get("draft") or "").strip()
        )
        if claimed_reply and item.get("already_replied"):
            false_needs.append(
                {
                    "chat_id": _chat_id(item),
                    "suggestion_id": item.get("id"),
                    "reason": "draft_while_already_replied",
                }
            )
        if item.get("ai_draft_ignored"):
            # Deduplicate by chat when both signals fire
            cid = _chat_id(item)
            if not any(f.get("chat_id") == cid for f in false_needs):
                false_needs.append(
                    {
                        "chat_id": cid,
                        "suggestion_id": item.get("id"),
                        "reason": "ai_draft_ignored",
                    }
                )

    covered_chats = {
        _chat_id(s)
        for s in enriched_before_merge
        if s.get("needs_reply") and (s.get("status") or "pending") == "pending"
    }
    covered_chats.discard(None)

    missing_dues: list[dict[str, Any]] = []
    for oi in open_items:
        cid = _chat_id(oi)
        if cid is None or cid in covered_chats:
            continue
        missing_dues.append(
            {
                "chat_id": cid,
                "last_message_at": oi.get("last_message_at"),
                "reason": "open_item_not_in_suggestions",
            }
        )

    needs_pending = [
        s
        for s in final_queue
        if s.get("needs_reply") and (s.get("status") or "pending") == "pending"
    ]
    missing_due_hints = [
        {
            "chat_id": _chat_id(s),
            "suggestion_id": s.get("id"),
            "reason": "empty_due_hint",
        }
        for s in needs_pending
        if not (s.get("due_hint") or "").strip()
    ]

    return {
        "raw_suggestion_count": len(raw_suggestions),
        "enriched_count": len(enriched_before_merge),
        "final_queue_count": len(final_queue),
        "open_items_count": len(open_items),
        "needs_reply_count": len(needs_pending),
        "false_needs_reply_count": len(false_needs),
        "false_needs_reply": false_needs[:20],
        "missing_dues_count": len(missing_dues),
        "missing_dues": missing_dues[:20],
        "missing_due_hint_count": len(missing_due_hints),
        "missing_due_hints": missing_due_hints[:20],
        "merged_from_open_items": sum(
            1 for s in final_queue if s.get("from_open_items")
        ),
    }


def log_act_queue_event(
    event: str,
    metrics: dict[str, Any],
    *,
    duration_ms: float | None = None,
    provider: str | None = None,
    degraded: bool | None = None,
) -> None:
    payload = {
        "event": event,
        **metrics,
    }
    if duration_ms is not None:
        payload["duration_ms"] = round(duration_ms, 1)
    if provider is not None:
        payload["provider"] = provider
    if degraded is not None:
        payload["degraded"] = degraded

    # One-line summary for grepping logs
    logger.info(
        "act_queue %s needs=%s false_needs=%s missing_dues=%s missing_due_hint=%s "
        "queue=%s open=%s duration_ms=%s provider=%s degraded=%s",
        event,
        metrics.get("needs_reply_count"),
        metrics.get("false_needs_reply_count"),
        metrics.get("missing_dues_count"),
        metrics.get("missing_due_hint_count"),
        metrics.get("final_queue_count"),
        metrics.get("open_items_count"),
        payload.get("duration_ms"),
        provider,
        degraded,
    )
    if metrics.get("false_needs_reply_count"):
        logger.warning(
            "act_quality false_needs_reply count=%s samples=%s",
            metrics["false_needs_reply_count"],
            metrics.get("false_needs_reply"),
        )
    if metrics.get("missing_dues_count"):
        logger.warning(
            "act_quality missing_dues count=%s samples=%s",
            metrics["missing_dues_count"],
            metrics.get("missing_dues"),
        )
    if metrics.get("missing_due_hint_count"):
        logger.info(
            "act_quality missing_due_hint count=%s samples=%s",
            metrics["missing_due_hint_count"],
            metrics.get("missing_due_hints"),
        )


def log_triage_feedback(
    *,
    suggestion_id: int,
    new_status: str,
    flat: dict[str, Any],
) -> None:
    """User triage signal — dismiss/done on a needs-reply card may be a false positive."""
    needs = bool(flat.get("needs_reply"))
    already = bool(flat.get("already_replied"))
    signal = None
    if new_status == "dismissed" and needs and not already:
        signal = "possible_false_needs_reply"
    elif new_status == "done" and needs and not already:
        signal = "handled_offline_or_false_needs"
    elif new_status == "sent":
        signal = "sent_from_act"

    logger.info(
        "act_triage suggestion_id=%s status=%s signal=%s chat_id=%s "
        "needs_reply=%s already_replied=%s reply_state=%s due_hint=%r",
        suggestion_id,
        new_status,
        signal,
        flat.get("chat_id"),
        needs,
        already,
        flat.get("reply_state"),
        flat.get("due_hint") or "",
    )


class ActTimer:
    def __init__(self) -> None:
        self._start = time.perf_counter()

    def ms(self) -> float:
        return (time.perf_counter() - self._start) * 1000.0
