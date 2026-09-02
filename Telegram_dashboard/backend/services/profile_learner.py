"""Learn relationship + ai_context from chat threads (native AI + optional SmartPersona)."""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from backend.config import BASE_DIR, SMARTPERSONA_ENABLED, SMARTPERSONA_PATH
from backend.services.ai_service import ai_service

logger = logging.getLogger(__name__)

LEARN_MESSAGE_CAP = 80

# Optional SmartPersona — requires Ollama running (SmartPersonaBrain uses ollama_client).
_REFLECTION_PREFIXES = (
    "FACT:",
    "PREFERENCE:",
    "EVENT:",
    "HABIT:",
    "BELIEF:",
    "RELATIONSHIP:",
    "VOICE:",
    "TOPIC_STYLE:",
    "REACTION:",
)


@dataclass
class LearnResult:
    relationship: str
    ai_context: str
    relationship_source: str = "ai"
    facts: list[str] = field(default_factory=list)
    message_count: int = 0
    provider: str = "native"
    smartpersona_used: bool = False
    degraded: bool = False
    failure_reason: str | None = None

    def to_learn_meta(self) -> dict[str, Any]:
        return {
            "message_count": self.message_count,
            "facts": self.facts,
            "source": self.relationship_source,
            "provider": self.provider,
            "smartpersona_used": self.smartpersona_used,
            "degraded": self.degraded,
            "failure_reason": self.failure_reason,
        }


def _smartpersona_dir() -> Path | None:
    path = Path(SMARTPERSONA_PATH)
    if not path.is_dir():
        default = BASE_DIR.parent / "SmartPersona"
        if default.is_dir():
            return default
        return None
    return path


def _reflection_lines_to_bullets(raw: str) -> list[str]:
    bullets: list[str] = []
    for line in (raw or "").splitlines():
        line = line.strip()
        if not line or line.upper() == "NONE":
            continue
        matched = False
        for prefix in _REFLECTION_PREFIXES:
            idx = line.upper().find(prefix)
            if idx >= 0:
                rest = line[idx + len(prefix) :].strip()
                if rest:
                    label = prefix.rstrip(":").replace("_", " ").title()
                    bullets.append(f"{label}: {rest}")
                matched = True
                break
        if not matched:
            if line.startswith("- "):
                bullets.append(line[2:].strip())
            elif len(line) > 3:
                bullets.append(line)
    return bullets


def _merge_ai_context(base: str, extra_bullets: list[str]) -> str:
    seen = {line.strip().lower() for line in base.splitlines() if line.strip()}
    additions: list[str] = []
    for bullet in extra_bullets:
        text = bullet.strip()
        key = text.lower()
        if key and key not in seen:
            seen.add(key)
            additions.append(text)
    if not additions:
        return base.strip()
    extra_block = "\n".join(
        f"- {b}" if not b.startswith("- ") else b for b in additions
    )
    base = base.strip()
    return extra_block if not base else f"{base}\n\n{extra_block}"


def _format_transcript_for_sp(messages: list[dict]) -> tuple[str, list[str]]:
    lines: list[str] = []
    participants: set[str] = set()
    for msg in sorted(messages, key=lambda m: m.get("created_at", "")):
        user = msg.get("username") or f"User {msg.get('user_id')}"
        if msg.get("username"):
            participants.add(str(msg["username"]))
        text = (msg.get("text") or "").strip()
        if text:
            lines.append(f"{user}: {text}")
    return "\n".join(lines), sorted(participants)


def _smartpersona_reflect_sync(transcript: str, participants: list[str]) -> list[str]:
    """Thin sync wrapper around SmartPersonaBrain.reflect_on_conversation (Ollama must be up)."""
    sp_path = _smartpersona_dir()
    if not sp_path:
        logger.info("SmartPersona not enabled: path missing")
        return []

    sp_str = str(sp_path.resolve())
    if sp_str not in sys.path:
        sys.path.insert(0, sp_str)

    try:
        from brain import SmartPersonaBrain  # type: ignore[import-untyped]
    except ImportError as exc:
        logger.info("SmartPersona import failed (%s); not enabled", exc)
        return []

    try:
        brain = SmartPersonaBrain(persist=False)
        result = brain.reflect_on_conversation(
            transcript, conversation_participants=participants or None
        )
        raw = (result or {}).get("reflection") or ""
        return _reflection_lines_to_bullets(raw)
    except Exception as exc:
        logger.warning("SmartPersona reflect failed: %s", exc, exc_info=True)
        return []


async def _try_smartpersona_bullets(messages: list[dict]) -> list[str]:
    if not SMARTPERSONA_ENABLED:
        logger.debug("SmartPersona not enabled (SMARTPERSONA_ENABLED != true)")
        return []

    transcript, participants = _format_transcript_for_sp(messages)
    if not transcript.strip():
        return []

    return await asyncio.to_thread(
        _smartpersona_reflect_sync, transcript, participants
    )


async def learn_from_chat(
    chat_id: int,
    messages: list[dict],
    chat_meta: dict[str, Any] | None = None,
) -> LearnResult:
    """Learn relationship + ai_context; native AI always, SmartPersona optional enhancement."""
    meta = chat_meta or {}
    chat_type = meta.get("chat_type")
    chat_title = meta.get("chat_title")
    capped = messages[-LEARN_MESSAGE_CAP:]

    native = await ai_service.learn_from_thread(
        capped, chat_type=chat_type, chat_title=chat_title
    )

    ai_context = native.get("ai_context", "")
    smartpersona_used = False
    provider = "native"

    sp_bullets = await _try_smartpersona_bullets(capped)
    if sp_bullets:
        ai_context = _merge_ai_context(ai_context, sp_bullets)
        smartpersona_used = True
        provider = "native+smartpersona"

    return LearnResult(
        relationship=native.get("relationship", ""),
        ai_context=ai_context,
        relationship_source=native.get("source", "ai"),
        facts=native.get("facts") or [],
        message_count=len(capped),
        provider=provider,
        smartpersona_used=smartpersona_used,
        degraded=bool(native.get("degraded")),
        failure_reason=native.get("failure_reason"),
    )
