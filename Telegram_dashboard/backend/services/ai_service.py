import json
import logging
import re
from datetime import datetime
from typing import Any

from backend.services.providers.gemini import GeminiProvider
from backend.services.providers.ollama import OllamaProvider
from backend.services.redaction_service import redaction_service
from backend.services.ai_rate_limiter import ai_rate_limiter
from backend.services.summary_cache import summary_cache
from backend.services.summary_corrector import align_summary_with_context

logger = logging.getLogger(__name__)

AI_SUGGEST_MESSAGE_CAP = 60
AI_SUGGEST_RETRY_CAP = 25

SUMMARY_PROMPTS = {
    "brief": "Write a brief English summary in 2-3 sentences.",
    "detailed": "Write a detailed English summary covering all key points.",
    "bullets": "Write an English bullet-point summary with one bullet per key topic.",
    "unanswered": (
        "List unanswered questions or requests that still need the user's attention. "
        "Use English bullet points."
    ),
}

RELATIONSHIP_SYSTEM = (
    "You describe who the other party is in a Telegram conversation for an user dashboard. "
    "Return ONLY valid JSON with no markdown fences. "
    "Schema: {\"relationship\": string} — 2-3 concise English sentences covering: "
    "who they are, their role or relationship to the user, communication style if evident, "
    "and what they typically need help with or contact for. "
    "For group chats, the group title is the chat name, not a participant who spoke."
)

LEARN_FROM_THREAD_SYSTEM = (
    "You analyze a Telegram conversation to build context for a user dashboard assistant. "
    "Return ONLY valid JSON with no markdown fences. "
    "Schema: {\"relationship\": string, \"ai_context\": string, \"facts\": [string]}. "
    "relationship: 2-3 concise English sentences — who they are, their role or relationship, "
    "communication style if evident, what they typically need. "
    "ai_context: bullet-style notes (aliases, nicknames, preferences, how to address them, "
    "topics they care about) useful when drafting replies — short lines, not prose. "
    "facts: optional list of 0-8 short standalone facts worth remembering. "
    "For group chats, the group title is the chat name, not a participant who spoke."
)

LEARN_FROM_THREAD_CAP = 80

PROFILE_LEARN_SYSTEM = (
    "You analyze Telegram conversations to build a durable contact profile for an operator dashboard. "
    "Return ONLY valid JSON with no markdown fences. "
    "Schema: {"
    "\"memories\": [{\"type\": \"fact\"|\"preference\"|\"relationship\"|\"habit\"|\"voice\", \"content\": string}], "
    "\"relationship\": string, "
    "\"ai_context\": string"
    "}. "
    "memories: 3-8 concise English items capturing stable facts, preferences, relationship cues, habits, "
    "and communication style (voice). Skip one-off logistics unless they reveal a pattern. "
    "relationship: 2-3 sentences describing who they are and how they relate to the operator. "
    "ai_context: short bullet-style notes the AI should remember when drafting replies "
    "(names, topics, tone, constraints). "
    "Only attribute speech to usernames in the transcript. "
    "Group or channel titles are never speakers."
)

CHAT_MEMORY_TYPES = frozenset({"fact", "preference", "relationship", "habit", "voice"})

TOPIC_SYSTEM = (
    "You classify Telegram messages for an user dashboard. "
    "Return ONLY valid JSON with no markdown fences. "
    "Schema: {\"topics\": [string]} — 1-3 short lowercase topic tags "
    "(e.g. billing, support, scheduling, budget, etc.)."
)

FILTER_EXPAND_SYSTEM = (
    "You expand a search phrase into related topic tags and keywords for filtering Telegram messages. "
    "Return ONLY valid JSON with no markdown fences. "
    "Schema: {\"topics\": [string], \"keywords\": [string]}. "
    "topics: up to 8 short lowercase tags (prefer names from the available list when relevant, "
    "plus close synonyms). "
    "keywords: up to 8 lowercase words or short phrases to match in message text "
    "(synonyms, related concepts). "
    "Always include the original query terms. Do not invent long sentences."
)

SUGGEST_SYSTEM = (
    "You are an assistant for a Telegram user dashboard. "
    "Analyze conversations and return ONLY valid JSON with no markdown fences. "
    "Write summary and drafts in English. "
    "Only attribute speech to usernames in the transcript. "
    "A group or channel title is never a person who spoke. "
    "Schema: {\"summary\": string, \"suggestions\": [{\"type\": \"reply\"|\"next_action\", "
    "\"chat_id\": number|null, \"user\": string, \"draft\": string, \"action\": string, "
    "\"priority\": \"high\"|\"medium\"|\"low\", \"confidence\": number, \"due_hint\": string}]}"
)

CONVERSATION_INTEL_SYSTEM = (
    "You analyze filtered Telegram conversations for a user dashboard. "
    "Return ONLY valid JSON with no markdown fences. "
    "Write all fields in clear English. "
    "Only attribute speech to usernames in the transcript. "
    "Group or channel titles are never speakers. "
    "Schema: {"
    "\"topics_summary\": string, "
    "\"sentiment_summary\": string, "
    "\"needs_summary\": string, "
    "\"key_points\": [string]"
    "}. "
    "topics_summary: 2-4 concise sentences about what people discussed. "
    "sentiment_summary: 1-3 concise sentences about emotional tone, urgency, or friction. "
    "needs_summary: 2-4 concise sentences focused on what others want, expect, need approved, or need answered from the operator. "
    "key_points: 3-7 short standalone bullets as plain strings. "
    "Do not include markdown bullets inside strings."
)

THREAD_SUMMARY_SYSTEM = (
    "You summarize Telegram conversations for a user dashboard. "
    "Write 1-3 clear English sentences about what was actually discussed. "
    "Only attribute statements to usernames shown before each colon in the transcript. "
    "Never treat a group chat title or channel name as a person who spoke or replied. "
    "When referring to the chat, use the exact group/channel name from the metadata block. "
    "Do not invent a different group name. Be concise."
)

FILTERED_SUMMARY_SYSTEM = (
    "You summarize Telegram messages for a user dashboard. "
    "Only attribute speech to usernames in the transcript. "
    "Bracketed chat labels are group/channel titles, not speakers."
)


class AIService:
    def __init__(self):
        self.gemini = GeminiProvider()
        self.ollama = OllamaProvider()
        self._filter_expand_cache: dict[str, tuple[float, dict[str, list[str]]]] = {}

    @property
    def configured(self) -> bool:
        return self.gemini.configured or self.ollama.configured

    async def provider_status(self) -> dict:
        return {
            "gemini": {
                "configured": self.gemini.configured,
                "model": self.gemini.model,
            },
            "ollama": {
                "configured": self.ollama.configured,
                "model": self.ollama.model,
                "available": await self.ollama.is_available(),
                "base_url": self.ollama.base_url,
            },
            "primary": "gemini" if self.gemini.configured else "ollama",
            "fallback": "ollama" if self.gemini.configured and self.ollama.configured else None,
            "fallback_commands": True,
            "rate_limit": ai_rate_limiter.status(),
        }

    def _speaker_label(self, msg: dict) -> str:
        if msg.get("username"):
            return f"@{msg['username']}"
        return f"User {msg.get('user_id')}"

    def _chat_label(self, msg: dict) -> str:
        chat_type = msg.get("chat_type") or "chat"
        chat_title = (msg.get("chat_title") or "").strip()
        if chat_type == "group" and chat_title:
            return f'Group "{chat_title}"'
        if chat_type == "channel" and chat_title:
            return f'Channel "{chat_title}"'
        if chat_title:
            return f'Chat "{chat_title}"'
        return chat_type

    def _thread_metadata_block(self, messages: list[dict]) -> str:
        if not messages:
            return ""

        first = messages[0]
        chat_type = first.get("chat_type") or "chat"
        chat_title = (first.get("chat_title") or "").strip()
        participants = sorted(
            {
                self._speaker_label(m)
                for m in messages
                if m.get("username") or m.get("user_id")
            }
        )

        lines = ["Conversation metadata:"]
        if chat_type == "group" and chat_title:
            lines.append(
                f'- Group name: "{chat_title}" '
                "(chat title only - not a participant who spoke)"
            )
        elif chat_type == "channel" and chat_title:
            lines.append(
                f'- Channel name: "{chat_title}" '
                "(channel title only - not a participant who spoke)"
            )
        elif chat_title:
            lines.append(f'- Chat: "{chat_title}"')
        if participants:
            lines.append(f"- Speakers in this thread: {', '.join(participants)}")
        lines.append(
            "- In the transcript, only the @username before the colon is the speaker."
        )
        return "\n".join(lines) + "\n\n"

    def _format_transcript(self, messages: list[dict], *, use_redacted: bool = True) -> str:
        if not messages:
            return ""

        single_chat = len({m.get("chat_id") for m in messages if m.get("chat_id") is not None}) <= 1
        chat_type = messages[0].get("chat_type")
        omit_chat_prefix = single_chat and chat_type in ("group", "channel")

        lines = []
        for msg in sorted(messages, key=lambda m: m.get("created_at", "")):
            speaker = self._speaker_label(msg)
            text = msg.get("text_redacted") if use_redacted and msg.get("text_redacted") else msg.get("text", "")
            if omit_chat_prefix:
                lines.append(f"{speaker}: {text}")
            else:
                chat = self._chat_label(msg)
                lines.append(f"[{chat}] {speaker}: {text}")
        return "\n".join(lines)

    def _prepare_messages(self, messages: list[dict]) -> tuple[list[dict], int, bool]:
        redacted, count, applied = redaction_service.redact_messages(messages)
        return redacted, count, applied

    def _apply_generation_meta(
        self, result: dict[str, Any], meta: dict[str, Any]
    ) -> None:
        if meta.get("degraded"):
            result["degraded"] = True
        if meta.get("failure_reason"):
            result["failure_reason"] = meta["failure_reason"]

    async def _generate_text(
        self, prompt: str, system: str
    ) -> tuple[str, str, dict[str, Any]]:
        ai_rate_limiter.check()
        meta: dict[str, Any] = {}
        gemini_error: str | None = None

        if self.gemini.configured:
            try:
                text = await self.gemini.generate_text(prompt, system=system)
                return text, "gemini", meta
            except Exception as exc:
                gemini_error = f"{type(exc).__name__}: {exc}"
                logger.warning(
                    "Gemini text generation failed, trying fallback: %s",
                    gemini_error,
                    exc_info=True,
                )

        if self.ollama.configured and await self.ollama.is_available():
            text = await self.ollama.generate_text(prompt, system=system)
            if gemini_error:
                meta["degraded"] = True
                meta["failure_reason"] = (
                    f"Gemini failed ({gemini_error}); using Ollama fallback"
                )
            return text, "ollama", meta

        if gemini_error:
            raise RuntimeError(
                f"Gemini failed ({gemini_error}); no fallback provider available"
            )
        raise RuntimeError("No AI provider available")

    def _parse_json_response(self, raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        fence = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if fence:
            cleaned = fence.group(1).strip()
        elif cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned).strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            start = cleaned.find("{")
            if start < 0:
                raise
            depth = 0
            for index, char in enumerate(cleaned[start:], start):
                if char == "{":
                    depth += 1
                elif char == "}":
                    depth -= 1
                    if depth == 0:
                        return json.loads(cleaned[start : index + 1])
            raise

    async def summarize_messages(
        self,
        messages: list[dict],
        summary_type: str = "brief",
        filters: dict[str, Any] | None = None,
        relationship_map: dict[int, str] | None = None,
        ai_context_map: dict[int, str] | None = None,
    ) -> dict[str, Any]:
        if not messages:
            return {
                "summary": "No messages match the current filters.",
                "message_count": 0,
                "originals": [],
                "provider": "none",
                "redaction_applied": False,
                "redaction_count": 0,
                "generated_at": datetime.utcnow().isoformat(),
                "cached": False,
            }

        filters = filters or {}
        cached = summary_cache.get(filters, summary_type)
        if cached:
            return cached

        redacted, redaction_count, redaction_applied = self._prepare_messages(messages)
        instruction = SUMMARY_PROMPTS.get(summary_type, SUMMARY_PROMPTS["brief"])
        system = f"{FILTERED_SUMMARY_SYSTEM} {instruction} Output in English."
        transcript = self._format_transcript(redacted)
        context_block = self._chat_context_block(relationship_map, ai_context_map)
        metadata_block = self._thread_metadata_block(redacted) if len(redacted) else ""
        prompt = (
            f"{context_block}{metadata_block}"
            f"Summarize these {len(messages)} messages:\n\n{transcript}"
        )

        gen_meta: dict[str, Any] = {}
        try:
            summary, provider, gen_meta = await self._generate_text(prompt, system)
        except RuntimeError as exc:
            summary = self._fallback_thread_summary(messages)
            provider = "fallback"
            gen_meta = {"degraded": True, "failure_reason": str(exc)}

        summary, name_corrections = self._align_summary_names(
            summary,
            messages,
            relationship_map=relationship_map,
            ai_context_map=ai_context_map,
        )

        originals = [
            {
                "id": m.get("id"),
                "username": m.get("username"),
                "text": m.get("text"),
                "created_at": m.get("created_at"),
                "chat_id": m.get("chat_id"),
            }
            for m in sorted(messages, key=lambda m: m.get("created_at", ""))
        ]

        result = {
            "summary": summary,
            "message_count": len(messages),
            "originals": originals,
            "message_highlights": self._fallback_message_highlights(messages)
            if provider == "fallback"
            else [],
            "provider": provider,
            "name_corrections": name_corrections,
            "summary_type": summary_type,
            "redaction_applied": redaction_applied,
            "redaction_count": redaction_count,
            "generated_at": datetime.utcnow().isoformat(),
            "cached": False,
        }
        self._apply_generation_meta(result, gen_meta)
        summary_cache.set(filters, summary_type, result)
        return result

    def get_cached_thread_summary(
        self, chat_id: int, message_ids: list[int]
    ) -> dict[str, Any] | None:
        from backend.models.store import store

        cached = store.get_thread_summary(chat_id)
        if not cached:
            return None

        current_hash = store.thread_content_hash(message_ids)
        cached["stale"] = cached.get("content_hash") != current_hash
        return cached

    async def summarize_thread(
        self,
        messages: list[dict],
        *,
        chat_id: int | None = None,
        force: bool = False,
        relationship: str = "",
        ai_context: str = "",
    ) -> dict[str, Any]:
        from backend.models.store import store

        if not messages:
            return {
                "summary": "No messages in this conversation.",
                "provider": "none",
                "cached": False,
                "stale": False,
            }

        message_ids = [int(m["id"]) for m in messages if m.get("id") is not None]
        content_hash = store.thread_content_hash(message_ids)

        if chat_id is not None and not force:
            cached = store.get_thread_summary(chat_id)
            if cached:
                cached = dict(cached)
                cached["stale"] = cached.get("content_hash") != content_hash
                cached["cached"] = True
                return cached

        redacted, redaction_count, redaction_applied = self._prepare_messages(messages)
        transcript = self._format_transcript(redacted)
        metadata_block = self._thread_metadata_block(redacted)
        context_block = self._chat_context_block(
            {chat_id: relationship} if chat_id is not None and relationship else None,
            {chat_id: ai_context} if chat_id is not None and ai_context else None,
        )
        prompt = (
            f"{context_block}{metadata_block}"
            f"Summarize this conversation:\n\n{transcript}"
        )

        gen_meta: dict[str, Any] = {}
        try:
            summary, provider, gen_meta = await self._generate_text(
                prompt, THREAD_SUMMARY_SYSTEM
            )
        except RuntimeError as exc:
            summary = self._fallback_thread_summary(messages)
            provider = "fallback"
            gen_meta = {"degraded": True, "failure_reason": str(exc)}

        summary, name_corrections = self._align_summary_names(
            summary,
            messages,
            relationship=relationship,
            ai_context=ai_context,
        )

        result = {
            "summary": summary,
            "provider": provider,
            "name_corrections": name_corrections,
            "redaction_applied": redaction_applied,
            "redaction_count": redaction_count,
            "content_hash": content_hash,
            "cached": False,
            "stale": False,
            "generated_at": datetime.utcnow().isoformat(),
        }
        self._apply_generation_meta(result, gen_meta)

        if chat_id is not None:
            saved = store.save_thread_summary(
                chat_id,
                content_hash,
                summary=summary,
                provider=provider,
                redaction_applied=redaction_applied,
                redaction_count=redaction_count,
            )
            result["generated_at"] = saved["generated_at"]

        return result

    def _align_summary_names(
        self,
        summary: str,
        messages: list[dict],
        *,
        relationship: str = "",
        ai_context: str = "",
        relationship_map: dict[int, str] | None = None,
        ai_context_map: dict[int, str] | None = None,
    ) -> tuple[str, list[dict[str, str]]]:
        if relationship_map:
            relationship = "\n".join(
                part for part in relationship_map.values() if part and str(part).strip()
            )
        if ai_context_map:
            ai_context = "\n".join(
                part for part in ai_context_map.values() if part and str(part).strip()
            )
        corrected, corrections = align_summary_with_context(
            summary,
            messages,
            ai_context=ai_context,
            relationship=relationship,
        )
        return corrected, corrections

    def _chat_context_block(
        self,
        relationship_map: dict[int, str] | None = None,
        ai_context_map: dict[int, str] | None = None,
    ) -> str:
        chat_ids: set[int] = set()
        if relationship_map:
            chat_ids.update(relationship_map.keys())
        if ai_context_map:
            chat_ids.update(ai_context_map.keys())

        sections: list[str] = []
        for chat_id in sorted(chat_ids):
            parts: list[str] = []
            relationship = (relationship_map or {}).get(chat_id, "").strip()
            notes = (ai_context_map or {}).get(chat_id, "").strip()
            if relationship:
                parts.append(f"Who they are: {relationship}")
            if notes:
                parts.append(f"Operator notes: {notes}")
            if parts:
                sections.append(f"- Chat {chat_id}:\n  " + "\n  ".join(parts))

        if not sections:
            return ""
        return (
            "Background context from the operator "
            "(use when interpreting names, aliases, and topics):\n"
            + "\n".join(sections)
            + "\n\n"
        )

    def _relationship_context_block(
        self, relationship_map: dict[int, str] | None
    ) -> str:
        return self._chat_context_block(relationship_map=relationship_map)

    def _fallback_relationship(
        self, messages: list[dict], chat_type: str | None, chat_title: str | None
    ) -> str:
        if chat_type == "group":
            label = chat_title or "this group"
            participants = sorted(
                {
                    m.get("username") or f"User {m.get('user_id')}"
                    for m in messages
                    if m.get("user_id")
                }
            )
            names = ", ".join(participants[:4]) if participants else "team members"
            return (
                f"Group chat ({label}) with {names}. "
                "They coordinate updates and requests as a team."
            )

        incoming = [m for m in messages if m.get("direction") == "incoming"]
        latest = sorted(incoming or messages, key=lambda m: m.get("created_at", ""))[-1]
        user = latest.get("username") or f"User {latest.get('user_id')}"
        snippet = (latest.get("text") or "")[:120]
        return (
            f"Private chat with {user}. "
            f"Recent focus: \"{snippet}\". "
            "Treat them as a direct contact who expects a personal reply."
        )

    async def generate_relationship(
        self,
        messages: list[dict],
        *,
        chat_type: str | None = None,
        chat_title: str | None = None,
    ) -> dict[str, str]:
        if not messages:
            return {"relationship": "No messages yet.", "source": "ai"}

        redacted, _, _ = self._prepare_messages(messages)
        transcript = self._format_transcript(redacted)
        label = chat_title or chat_type or "chat"
        prompt = (
            f"Describe who the other party is in this {label} conversation "
            f"based on these messages:\n\n{transcript}"
        )

        if not self.configured:
            return {
                "relationship": self._fallback_relationship(messages, chat_type, chat_title),
                "source": "ai",
            }

        try:
            raw, _provider, gen_meta = await self._generate_text(
                prompt, RELATIONSHIP_SYSTEM
            )
            parsed = self._parse_json_response(raw)
            relationship = str(parsed.get("relationship", "")).strip()
            if not relationship:
                raise ValueError("Empty relationship")
            result = {"relationship": relationship, "source": "ai"}
            self._apply_generation_meta(result, gen_meta)
            return result
        except Exception as exc:
            logger.warning(
                "generate_relationship AI failed, using heuristic fallback: %s",
                exc,
                exc_info=True,
            )
            return {
                "relationship": self._fallback_relationship(
                    messages, chat_type, chat_title
                ),
                "source": "fallback",
                "degraded": True,
                "failure_reason": f"{type(exc).__name__}: {exc}",
            }

    def _merge_learn_facts(self, ai_context: str, facts: list[Any]) -> str:
        lines = [str(f).strip() for f in facts if str(f).strip()]
        if not lines:
            return ai_context.strip()
        facts_block = "\n".join(f"- {line}" for line in lines)
        base = ai_context.strip()
        return f"{base}\n\n{facts_block}".strip() if base else facts_block

    async def learn_from_thread(
        self,
        messages: list[dict],
        *,
        chat_type: str | None = None,
        chat_title: str | None = None,
    ) -> dict[str, Any]:
        capped = messages[-LEARN_FROM_THREAD_CAP:]
        if not capped:
            return {
                "relationship": "No messages yet.",
                "ai_context": "",
                "facts": [],
                "source": "ai",
            }

        fallback = {
            "relationship": self._fallback_relationship(capped, chat_type, chat_title),
            "ai_context": "",
            "facts": [],
            "source": "fallback",
            "degraded": True,
        }

        if not self.configured:
            return {
                "relationship": fallback["relationship"],
                "ai_context": "",
                "facts": [],
                "source": "ai",
            }

        redacted, _, _ = self._prepare_messages(capped)
        transcript = self._format_transcript(redacted)
        label = chat_title or chat_type or "chat"
        prompt = (
            f"Learn who the other party is and useful drafting context from this {label} "
            f"conversation:\n\n{transcript}"
        )

        try:
            raw, _provider, gen_meta = await self._generate_text(
                prompt, LEARN_FROM_THREAD_SYSTEM
            )
            parsed = self._parse_json_response(raw)
            relationship = str(parsed.get("relationship", "")).strip()
            if not relationship:
                raise ValueError("Empty relationship")
            ai_context = str(parsed.get("ai_context", "")).strip()
            facts_raw = parsed.get("facts") or []
            facts = [str(f).strip() for f in facts_raw if str(f).strip()]
            result: dict[str, Any] = {
                "relationship": relationship,
                "ai_context": self._merge_learn_facts(ai_context, facts),
                "facts": facts,
                "source": "ai",
            }
            self._apply_generation_meta(result, gen_meta)
            return result
        except Exception as exc:
            logger.warning(
                "learn_from_thread AI failed, using heuristic fallback: %s",
                exc,
                exc_info=True,
            )
            fallback["failure_reason"] = f"{type(exc).__name__}: {exc}"
            return fallback

    def _normalize_learned_memories(
        self, raw_memories: list[Any] | None
    ) -> list[dict[str, str]]:
        normalized: list[dict[str, str]] = []
        seen: set[str] = set()
        for item in raw_memories or []:
            if not isinstance(item, dict):
                continue
            mem_type = str(item.get("type", "fact")).strip().lower()
            content = str(item.get("content", "")).strip()
            if mem_type not in CHAT_MEMORY_TYPES or not content:
                continue
            key = f"{mem_type}:{content.lower()}"
            if key in seen:
                continue
            seen.add(key)
            normalized.append({"type": mem_type, "content": content})
        return normalized

    def _fallback_profile_memories(
        self, messages: list[dict], chat_type: str | None, chat_title: str | None
    ) -> list[dict[str, str]]:
        if not messages:
            return []

        incoming = [m for m in messages if m.get("direction") == "incoming"]
        latest = sorted(incoming or messages, key=lambda m: m.get("created_at", ""))[-1]
        user = latest.get("username") or f"User {latest.get('user_id')}"
        snippet = (latest.get("text") or "").strip()[:160]

        memories: list[dict[str, str]] = []
        if chat_type == "group":
            label = chat_title or "this group"
            memories.append(
                {
                    "type": "relationship",
                    "content": f"Group chat ({label}) used for team coordination.",
                }
            )
        else:
            memories.append(
                {
                    "type": "relationship",
                    "content": f"Private contact {user} who messages directly.",
                }
            )

        if snippet:
            memories.append(
                {"type": "fact", "content": f"Recent topic: {snippet}"}
            )

        avg_len = sum(len((m.get("text") or "")) for m in messages[-10:]) / max(
            len(messages[-10:]), 1
        )
        if avg_len < 40:
            memories.append(
                {
                    "type": "voice",
                    "content": "Keeps messages short and direct.",
                }
            )
        elif avg_len > 120:
            memories.append(
                {
                    "type": "voice",
                    "content": "Writes longer, detailed messages.",
                }
            )

        return memories[:6]

    def _synthesize_ai_context(self, memories: list[dict[str, str]]) -> str:
        if not memories:
            return ""
        lines = []
        for item in memories:
            label = item["type"].replace("_", " ").title()
            lines.append(f"- {label}: {item['content']}")
        return "\n".join(lines)

    async def learn_profile_from_thread(
        self,
        messages: list[dict],
        *,
        chat_type: str | None = None,
        chat_title: str | None = None,
        existing_memories: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        if not messages:
            return {
                "memories": [],
                "relationship": "No messages yet.",
                "ai_context": "",
                "source": "ai",
            }

        if not self.configured:
            memories = self._fallback_profile_memories(
                messages, chat_type, chat_title
            )
            relationship = self._fallback_relationship(
                messages, chat_type, chat_title
            )
            return {
                "memories": memories,
                "relationship": relationship,
                "ai_context": self._synthesize_ai_context(memories),
                "source": "ai",
            }

        redacted, _, _ = self._prepare_messages(messages)
        transcript = self._format_transcript(redacted)
        metadata = self._thread_metadata_block(redacted)
        label = chat_title or chat_type or "chat"
        existing_block = ""
        if existing_memories:
            lines = [
                f"- [{m.get('type', 'fact')}] {m.get('content', '')}"
                for m in existing_memories[:12]
                if m.get("content")
            ]
            if lines:
                existing_block = (
                    "Existing profile memories (update or replace as needed):\n"
                    + "\n".join(lines)
                    + "\n\n"
                )
        prompt = (
            f"{existing_block}"
            f"Extract a durable profile from this {label} conversation:\n\n"
            f"{metadata}{transcript}"
        )

        try:
            raw, _provider, gen_meta = await self._generate_text(
                prompt, PROFILE_LEARN_SYSTEM
            )
            parsed = self._parse_json_response(raw)
            memories = self._normalize_learned_memories(parsed.get("memories"))
            if not memories:
                memories = self._fallback_profile_memories(
                    messages, chat_type, chat_title
                )
            relationship = str(parsed.get("relationship", "")).strip()
            if not relationship:
                relationship = self._fallback_relationship(
                    messages, chat_type, chat_title
                )
            ai_context = str(parsed.get("ai_context", "")).strip()
            if not ai_context:
                ai_context = self._synthesize_ai_context(memories)
            result: dict[str, Any] = {
                "memories": memories,
                "relationship": relationship,
                "ai_context": ai_context,
                "source": "ai",
            }
            self._apply_generation_meta(result, gen_meta)
            return result
        except Exception as exc:
            logger.warning(
                "learn_profile_from_thread AI failed, using heuristic fallback: %s",
                exc,
                exc_info=True,
            )
            memories = self._fallback_profile_memories(
                messages, chat_type, chat_title
            )
            return {
                "memories": memories,
                "relationship": self._fallback_relationship(
                    messages, chat_type, chat_title
                ),
                "ai_context": self._synthesize_ai_context(memories),
                "source": "fallback",
                "degraded": True,
                "failure_reason": f"{type(exc).__name__}: {exc}",
            }

    @staticmethod
    def _clip_for_draft(text: str, limit: int = 120) -> str:
        cleaned = " ".join((text or "").split())
        if len(cleaned) <= limit:
            return cleaned
        return cleaned[: limit - 1].rstrip() + "…"

    def _build_fallback_reply_draft(self, user: str, text: str) -> tuple[str, str]:
        """Heuristic multi-sentence reply: acknowledge + react + next step."""
        display = user or "there"
        snippet = self._clip_for_draft(text, 120)
        if not snippet:
            draft = (
                f"Hey {display}, I saw your message. "
                "Happy to help — what would you like to do next?"
            )
            action = f"Ask {display} what they need and propose a next step"
            return draft, action

        lower = snippet.lower()
        if "?" in snippet:
            react = "Good question — I want to make sure I answer it clearly."
            next_step = "Here's my take: … — does that cover what you needed?"
            action = f"Answer {display}'s question and confirm it lands"
        elif any(k in lower for k in ("show", "share", "send", "look", "see", "pic", "photo")):
            react = "That sounds interesting — I'd love to see it."
            next_step = "Want to send a photo or a quick link when you have a sec?"
            action = f"Invite {display} to share what they mentioned"
        elif any(k in lower for k in ("meet", "call", "when", "free", "schedule", "tomorrow")):
            react = "Happy to figure out timing with you."
            next_step = "What days or times work best on your side?"
            action = f"Propose scheduling options with {display}"
        elif any(k in lower for k in ("thank", "thanks", "thx", "appreciate")):
            react = "You're welcome — glad it helped."
            next_step = "Anything else you want to tackle next?"
            action = f"Acknowledge thanks from {display} and offer further help"
        else:
            react = "Got it — that makes sense."
            next_step = "What would be the most useful next step from your side?"
            action = f"Reply to {display} about their latest message and ask a clear next step"

        draft = (
            f'Hey {display} — thanks for the note about "{snippet}". '
            f"{react} {next_step}"
        )
        return draft, action

    def _fallback_suggestions(
        self,
        messages: list[dict],
        relationship_map: dict[int, str] | None = None,
    ) -> dict[str, Any]:
        suggestions = []
        by_chat: dict[int | None, list[dict]] = {}
        for msg in messages:
            by_chat.setdefault(msg.get("chat_id"), []).append(msg)

        for chat_id, chat_messages in by_chat.items():
            incoming = [m for m in chat_messages if m.get("direction") == "incoming"]
            if not incoming:
                continue
            latest = sorted(incoming, key=lambda m: m.get("created_at", ""))[-1]
            user = latest.get("username") or f"User {latest.get('user_id')}"
            text = (latest.get("text") or "").strip()
            draft, action = self._build_fallback_reply_draft(user, text)
            rel = (relationship_map or {}).get(chat_id or 0, "")
            if rel:
                action = f"{action} ({self._clip_for_draft(rel, 80)})"
            suggestions.append(
                {
                    "type": "reply",
                    "chat_id": chat_id,
                    "user": user,
                    "draft": draft,
                    "action": action,
                    "priority": "medium",
                    "confidence": 0.45,
                    "due_hint": "",
                }
            )

        if not suggestions:
            suggestions.append(
                {
                    "type": "next_action",
                    "chat_id": None,
                    "user": "",
                    "draft": "",
                    "action": "Review filtered messages and respond to pending items.",
                    "priority": "low",
                    "confidence": 0.4,
                    "due_hint": "today",
                }
            )

        return {
            "summary": self._fallback_thread_summary(messages),
            "message_highlights": self._fallback_message_highlights(messages),
            "suggestions": suggestions,
            "provider": "fallback",
        }

    def _fallback_message_highlights(
        self, messages: list[dict], *, limit: int = 20
    ) -> list[dict[str, Any]]:
        highlights = []
        for msg in sorted(messages, key=lambda m: m.get("created_at", ""), reverse=True)[:limit]:
            highlights.append(
                {
                    "username": msg.get("username"),
                    "user_id": msg.get("user_id"),
                    "text": msg.get("text", ""),
                    "created_at": msg.get("created_at"),
                    "chat_title": msg.get("chat_title"),
                    "chat_type": msg.get("chat_type"),
                    "direction": msg.get("direction"),
                }
            )
        return list(reversed(highlights))

    def _fallback_thread_summary(self, messages: list[dict]) -> str:
        if not messages:
            return "No messages to summarize."
        if len(messages) == 1:
            m = messages[0]
            name = m.get("username") or f"User {m.get('user_id')}"
            return f"Latest from {name}: \"{(m.get('text') or '')[:120]}\""

        speakers = {
            m.get("username") or f"User {m.get('user_id')}"
            for m in messages
            if m.get("username") or m.get("user_id")
        }
        chats = {m.get("chat_title") or m.get("chat_type") for m in messages if m.get("chat_id")}
        chat_part = f" across {len(chats)} chat{'s' if len(chats) != 1 else ''}" if chats else ""
        return (
            f"{len(messages)} messages from {len(speakers)} contact{'s' if len(speakers) != 1 else ''}"
            f"{chat_part}. AI summary unavailable - see recent messages below."
        )

    def _cap_messages_for_ai(
        self, messages: list[dict], limit: int = AI_SUGGEST_MESSAGE_CAP
    ) -> list[dict]:
        sorted_msgs = sorted(messages, key=lambda m: m.get("created_at", ""))
        if len(sorted_msgs) <= limit:
            return sorted_msgs
        return sorted_msgs[-limit:]

    async def _suggest_from_batch(
        self,
        messages: list[dict],
        relationship_map: dict[int, str] | None,
        ai_context_map: dict[int, str] | None,
        *,
        strict_json: bool = False,
    ) -> dict[str, Any]:
        redacted, redaction_count, redaction_applied = self._prepare_messages(messages)
        transcript = self._format_transcript(redacted)
        metadata_block = self._thread_metadata_block(redacted)
        context_block = self._chat_context_block(relationship_map, ai_context_map)
        prompt = (
            "Analyze these Telegram messages. Suggest reply drafts for chats needing a response "
            "and next actions for the user. "
            "Only attribute speech to usernames in the transcript. "
            "Group or channel titles are not speakers.\n\n"
            f"{context_block}{metadata_block}{transcript}"
        )
        system = SUGGEST_SYSTEM
        if strict_json:
            system += (
                " Return ONLY a single JSON object matching the schema. "
                "No prose, no markdown fences, no text before or after the JSON."
            )
        raw, provider, gen_meta = await self._generate_text(prompt, system)
        parsed = self._parse_json_response(raw)
        suggestions = parsed.get("suggestions", [])
        if not isinstance(suggestions, list):
            raise ValueError("AI response missing suggestions array")
        result = {
            "summary": parsed.get("summary", ""),
            "suggestions": suggestions,
            "provider": provider,
            "redaction_applied": redaction_applied,
            "redaction_count": redaction_count,
        }
        self._apply_generation_meta(result, gen_meta)
        return result

    async def suggest_actions(
        self,
        messages: list[dict],
        relationship_map: dict[int, str] | None = None,
        ai_context_map: dict[int, str] | None = None,
    ) -> dict[str, Any]:
        if not messages:
            return {
                "summary": "No messages to analyze.",
                "suggestions": [],
                "provider": "none",
                "redaction_applied": False,
                "redaction_count": 0,
            }

        if not self.configured:
            result = self._fallback_suggestions(messages, relationship_map)
            result["messages_total"] = len(messages)
            return result

        total = len(messages)
        last_error: Exception | None = None
        for limit, strict in (
            (AI_SUGGEST_MESSAGE_CAP, False),
            (AI_SUGGEST_RETRY_CAP, True),
        ):
            batch = self._cap_messages_for_ai(messages, limit)
            try:
                result = await self._suggest_from_batch(
                    batch,
                    relationship_map,
                    ai_context_map,
                    strict_json=strict,
                )
                result["messages_analyzed"] = len(batch)
                result["messages_total"] = total
                result["truncated_for_ai"] = len(batch) < total
                return result
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "suggest_actions failed (limit=%s, strict=%s): %s",
                    limit,
                    strict,
                    exc,
                )

        result = self._fallback_suggestions(messages, relationship_map)
        result["redaction_applied"] = False
        result["redaction_count"] = 0
        result["messages_total"] = total
        result["degraded"] = True
        if last_error:
            result["failure_reason"] = str(last_error)
        return result

    def _fallback_conversation_intel(self, messages: list[dict]) -> dict[str, Any]:
        sorted_messages = sorted(messages, key=lambda m: m.get("created_at", ""))
        incoming = [m for m in sorted_messages if m.get("direction") == "incoming"]
        outgoing = [m for m in sorted_messages if m.get("direction") == "outgoing"]
        recent = sorted_messages[-5:]

        participants = sorted(
            {
                m.get("username") or f"User {m.get('user_id')}"
                for m in sorted_messages
                if m.get("username") or m.get("user_id")
            }
        )
        participant_text = ", ".join(participants[:5]) if participants else "your contacts"

        latest_incoming = incoming[-1] if incoming else None
        latest_outgoing = outgoing[-1] if outgoing else None
        latest_incoming_text = (latest_incoming or {}).get("text", "").strip()
        latest_outgoing_text = (latest_outgoing or {}).get("text", "").strip()

        needs_summary = "No clear unanswered need was detected."
        if latest_incoming_text:
            needs_summary = (
                "The clearest current need appears in the latest incoming message: "
                f"\"{latest_incoming_text[:180]}\". "
                "This likely needs a reply, confirmation, or next step from you."
            )
        elif latest_outgoing_text:
            needs_summary = (
                "The recent conversation mostly shows your outgoing updates. "
                "Check whether the other side still needs a confirmation or reply."
            )

        sentiment_summary = (
            "Tone could not be deeply analyzed without AI. "
            "Use the recent messages below to judge urgency, mood, or tension."
        )
        if incoming and not outgoing:
            sentiment_summary = (
                "The thread is currently one-sided toward incoming messages, which may indicate pending attention. "
                "Review the latest requests for urgency or frustration."
            )

        key_points = [
            f"{(item.get('username') or f'User {item.get('user_id')}')}: {(item.get('text') or '').strip()[:180]}"
            for item in recent
            if (item.get("text") or "").strip()
        ]

        return {
            "topics_summary": (
                f"{len(messages)} filtered messages involving {participant_text}. "
                "AI conversation intel is unavailable, so this is a lightweight overview based on recent message flow."
            ),
            "sentiment_summary": sentiment_summary,
            "needs_summary": needs_summary,
            "key_points": key_points[:5],
            "message_highlights": self._fallback_message_highlights(messages),
            "provider": "fallback",
        }

    async def conversation_intel(
        self,
        messages: list[dict],
        relationship_map: dict[int, str] | None = None,
        ai_context_map: dict[int, str] | None = None,
    ) -> dict[str, Any]:
        if not messages:
            return {
                "topics_summary": "No messages match the current filters.",
                "sentiment_summary": "No conversation sentiment to analyze.",
                "needs_summary": "No current needs detected because no messages matched.",
                "key_points": [],
                "provider": "none",
                "message_count": 0,
                "messages_total": 0,
                "messages_analyzed": 0,
                "truncated_for_ai": False,
                "redaction_applied": False,
                "redaction_count": 0,
                "generated_at": datetime.utcnow().isoformat(),
            }

        total = len(messages)
        batch = self._cap_messages_for_ai(messages, AI_SUGGEST_MESSAGE_CAP)

        if not self.configured:
            result = self._fallback_conversation_intel(messages)
            result.update(
                {
                    "message_count": total,
                    "messages_total": total,
                    "messages_analyzed": len(batch),
                    "truncated_for_ai": len(batch) < total,
                    "redaction_applied": False,
                    "redaction_count": 0,
                    "generated_at": datetime.utcnow().isoformat(),
                }
            )
            return result

        redacted, redaction_count, redaction_applied = self._prepare_messages(batch)
        transcript = self._format_transcript(redacted)
        metadata_block = self._thread_metadata_block(redacted)
        context_block = self._chat_context_block(relationship_map, ai_context_map)
        prompt = (
            "Analyze these Telegram messages and explain: "
            "what people talked about, what they felt, and what they need from the operator.\n\n"
            f"{context_block}{metadata_block}{transcript}"
        )

        try:
            raw, provider, gen_meta = await self._generate_text(prompt, CONVERSATION_INTEL_SYSTEM)
            parsed = self._parse_json_response(raw)
            key_points = parsed.get("key_points", [])
            if not isinstance(key_points, list):
                raise ValueError("AI response missing key_points array")

            result = {
                "topics_summary": str(parsed.get("topics_summary", "")).strip(),
                "sentiment_summary": str(parsed.get("sentiment_summary", "")).strip(),
                "needs_summary": str(parsed.get("needs_summary", "")).strip(),
                "key_points": [str(item).strip() for item in key_points if str(item).strip()][:7],
                "provider": provider,
                "message_count": total,
                "messages_total": total,
                "messages_analyzed": len(batch),
                "truncated_for_ai": len(batch) < total,
                "redaction_applied": redaction_applied,
                "redaction_count": redaction_count,
                "generated_at": datetime.utcnow().isoformat(),
            }
            self._apply_generation_meta(result, gen_meta)
            if not result["topics_summary"]:
                raise ValueError("AI response missing topics_summary")
            if not result["sentiment_summary"]:
                raise ValueError("AI response missing sentiment_summary")
            if not result["needs_summary"]:
                raise ValueError("AI response missing needs_summary")
            return result
        except Exception as exc:
            logger.warning("conversation_intel failed, using fallback: %s", exc, exc_info=True)
            result = self._fallback_conversation_intel(messages)
            result.update(
                {
                    "message_count": total,
                    "messages_total": total,
                    "messages_analyzed": len(batch),
                    "truncated_for_ai": len(batch) < total,
                    "redaction_applied": redaction_applied,
                    "redaction_count": redaction_count,
                    "generated_at": datetime.utcnow().isoformat(),
                    "degraded": True,
                    "failure_reason": f"{type(exc).__name__}: {exc}",
                }
            )
            return result

    async def assign_topics(self, text: str) -> list[str]:
        redacted_text = redaction_service.redact(text).text
        prompt = f"Assign topic tags to this message:\n\n{redacted_text}"

        if not self.configured:
            lowered = redacted_text.lower()
            tags: list[str] = []
            keywords = {
                "billing": ("billing", "invoice", "payment", "pricing", "nric"),
                "scheduling": ("schedule", "demo", "standup", "meeting", "pm"),
                "budget": ("budget", "approval", "finance"),
                "support": ("help", "issue", "problem"),
            }
            for tag, words in keywords.items():
                if any(word in lowered for word in words):
                    tags.append(tag)
            return tags[:3] or ["general"]

        try:
            raw, _provider, _gen_meta = await self._generate_text(prompt, TOPIC_SYSTEM)
            parsed = self._parse_json_response(raw)
            topics = parsed.get("topics", [])
            return [str(t).strip().lower() for t in topics if str(t).strip()][:3]
        except Exception as exc:
            logger.warning("assign_topics AI failed, using keyword fallback: %s", exc)
            return ["general"]

    async def expand_filter_query(
        self, query: str, available_topics: list[str] | None = None
    ) -> dict[str, list[str]]:
        """Expand a free-text filter into related topic tags + text keywords."""
        cleaned = (query or "").strip()
        if not cleaned:
            return {"topics": [], "keywords": []}

        cache_key = cleaned.lower()
        cached = self._filter_expand_cache.get(cache_key)
        if cached and (datetime.utcnow().timestamp() - cached[0]) < 300:
            return cached[1]

        seed_terms = [t.strip().lower() for t in cleaned.replace(",", " ").split() if t.strip()]
        fallback = {
            "topics": seed_terms[:8],
            "keywords": seed_terms[:8],
        }

        if not self.configured:
            self._filter_expand_cache[cache_key] = (datetime.utcnow().timestamp(), fallback)
            return fallback

        topic_list = ", ".join((available_topics or [])[:80]) or "(none yet)"
        prompt = (
            f"Search phrase: {cleaned}\n"
            f"Available topic tags: {topic_list}\n"
            "Expand into related topics and keywords for message search."
        )
        try:
            raw, _provider, _gen_meta = await self._generate_text(prompt, FILTER_EXPAND_SYSTEM)
            parsed = self._parse_json_response(raw)
            topics = [
                str(t).strip().lower()
                for t in (parsed.get("topics") or [])
                if str(t).strip()
            ][:8]
            keywords = [
                str(k).strip().lower()
                for k in (parsed.get("keywords") or [])
                if str(k).strip()
            ][:8]
            for term in seed_terms:
                if term not in topics:
                    topics.insert(0, term)
                if term not in keywords:
                    keywords.insert(0, term)
            result = {"topics": topics[:8], "keywords": keywords[:8]}
            self._filter_expand_cache[cache_key] = (datetime.utcnow().timestamp(), result)
            return result
        except Exception as exc:
            logger.warning("expand_filter_query failed, using seed terms: %s", exc)
            self._filter_expand_cache[cache_key] = (datetime.utcnow().timestamp(), fallback)
            return fallback

    async def process_message(self, user_text: str, store) -> str:
        errors: list[str] = []

        if self.gemini.configured:
            try:
                return await self.gemini.chat(user_text, store)
            except Exception as exc:
                errors.append(f"Gemini: {exc}")

        if self.ollama.configured:
            try:
                if not await self.ollama.is_available():
                    raise RuntimeError("Ollama is not reachable. Start it with: ollama serve")
                return await self.ollama.chat(user_text, store)
            except Exception as exc:
                errors.append(f"Ollama: {exc}")

        if errors:
            return (
                "AI providers unavailable.\n"
                + "\n".join(errors)
                + "\n\n"
                + self._fallback_response(user_text, store)
            )

        return self._fallback_response(user_text, store)

    def _fallback_response(self, user_text: str, store) -> str:
        lowered = user_text.lower().strip()
        if lowered.startswith("/help"):
            return (
                "Available commands:\n"
                "/help - Show help\n"
                "/status - Dashboard metrics\n"
                "/analytics - Command usage summary\n"
                "/feedback <rating 1-5> <comment> - Submit feedback"
            )
        if lowered.startswith("/status"):
            metrics = store.metrics()
            return (
                f"Connected users (24h): {metrics['connected_users']}\n"
                f"Total messages: {metrics['total_messages']}\n"
                f"Total commands: {metrics['total_commands']}"
            )
        if lowered.startswith("/analytics"):
            usage = store.command_usage_over_time()
            if not usage["labels"]:
                return "No command usage recorded yet."
            lines = ["Command usage (last 7 days):"]
            for dataset in usage["datasets"]:
                total = sum(dataset["data"])
                lines.append(f"- {dataset['label']}: {total}")
            return "\n".join(lines)
        if lowered.startswith("/feedback"):
            parts = user_text.split(maxsplit=2)
            if len(parts) < 3:
                return "Usage: /feedback <rating 1-5> <comment>"
            try:
                rating = int(parts[1])
            except ValueError:
                return "Rating must be a number between 1 and 5."
            comment = parts[2]
            store.add_feedback(None, "telegram_user", rating, comment)
            return "Thank you for your feedback!"
        return (
            "I received your message. Configure GEMINI_API_KEY for cloud AI, "
            "or run Ollama locally as a fallback. Try /help for built-in commands."
        )


ai_service = AIService()
