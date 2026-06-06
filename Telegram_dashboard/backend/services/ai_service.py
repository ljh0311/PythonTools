import json
import re
from datetime import datetime
from typing import Any

from backend.services.providers.gemini import GeminiProvider
from backend.services.providers.ollama import OllamaProvider
from backend.services.redaction_service import redaction_service
from backend.services.summary_cache import summary_cache

SUMMARY_PROMPTS = {
    "brief": "Write a brief English summary in 2-3 sentences.",
    "detailed": "Write a detailed English summary covering all key points.",
    "bullets": "Write an English bullet-point summary with one bullet per key topic.",
    "unanswered": (
        "List unanswered questions or requests that still need the operator's attention. "
        "Use English bullet points."
    ),
}

RELATIONSHIP_SYSTEM = (
    "You describe who the other party is in a Telegram conversation for an operator dashboard. "
    "Return ONLY valid JSON with no markdown fences. "
    "Schema: {\"relationship\": string} — 2-3 concise English sentences covering: "
    "who they are, their role or relationship to the operator, communication style if evident, "
    "and what they typically need help with."
)

TOPIC_SYSTEM = (
    "You classify Telegram messages for an operator dashboard. "
    "Return ONLY valid JSON with no markdown fences. "
    "Schema: {\"topics\": [string]} — 1-3 short lowercase topic tags "
    "(e.g. billing, support, scheduling, budget)."
)

SUGGEST_SYSTEM = (
    "You are an assistant for a Telegram operator dashboard. "
    "Analyze conversations and return ONLY valid JSON with no markdown fences. "
    "Write summary and drafts in English. "
    "Schema: {\"summary\": string, \"suggestions\": [{\"type\": \"reply\"|\"next_action\", "
    "\"chat_id\": number|null, \"user\": string, \"draft\": string, \"action\": string, "
    "\"priority\": \"high\"|\"medium\"|\"low\", \"confidence\": number, \"due_hint\": string}]}"
)


class AIService:
    def __init__(self):
        self.gemini = GeminiProvider()
        self.ollama = OllamaProvider()

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
            "fallback_commands": True,
        }

    def _format_transcript(self, messages: list[dict], *, use_redacted: bool = True) -> str:
        lines = []
        for msg in sorted(messages, key=lambda m: m.get("created_at", "")):
            name = msg.get("username") or f"User {msg.get('user_id')}"
            text = msg.get("text_redacted") if use_redacted and msg.get("text_redacted") else msg.get("text", "")
            chat = msg.get("chat_title") or msg.get("chat_type") or "chat"
            lines.append(f"[{chat}] {name}: {text}")
        return "\n".join(lines)

    def _prepare_messages(self, messages: list[dict]) -> tuple[list[dict], int, bool]:
        redacted, count, applied = redaction_service.redact_messages(messages)
        return redacted, count, applied

    async def _generate_text(self, prompt: str, system: str) -> tuple[str, str]:
        if self.gemini.configured:
            try:
                return await self.gemini.generate_text(prompt, system=system), "gemini"
            except Exception:
                pass
        if self.ollama.configured and await self.ollama.is_available():
            return await self.ollama.generate_text(prompt, system=system), "ollama"
        raise RuntimeError("No AI provider available")

    def _parse_json_response(self, raw: str) -> dict[str, Any]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
        return json.loads(cleaned)

    async def summarize_messages(
        self,
        messages: list[dict],
        summary_type: str = "brief",
        filters: dict[str, Any] | None = None,
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
        system = (
            "You summarize Telegram messages for an operator dashboard. "
            f"{instruction} Keep the original language context in mind but output in English."
        )
        transcript = self._format_transcript(redacted)
        prompt = f"Summarize these {len(messages)} messages:\n\n{transcript}"

        try:
            summary, provider = await self._generate_text(prompt, system)
        except RuntimeError:
            summary = self._fallback_thread_summary(messages)
            provider = "fallback"

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
            "provider": provider,
            "summary_type": summary_type,
            "redaction_applied": redaction_applied,
            "redaction_count": redaction_count,
            "generated_at": datetime.utcnow().isoformat(),
            "cached": False,
        }
        summary_cache.set(filters, summary_type, result)
        return result

    async def summarize_thread(self, messages: list[dict]) -> dict:
        if not messages:
            return {"summary": "No messages in this conversation.", "provider": "none"}

        redacted, redaction_count, redaction_applied = self._prepare_messages(messages)
        system = (
            "You summarize Telegram conversations for an operator dashboard. "
            "Write 1-3 clear English sentences. Explain who said what, "
            "note any updates, conflicts, or action items. Be concise."
        )
        transcript = self._format_transcript(redacted)
        prompt = f"Summarize this conversation:\n\n{transcript}"

        try:
            summary, provider = await self._generate_text(prompt, system)
        except RuntimeError:
            summary = self._fallback_thread_summary(messages)
            provider = "fallback"

        return {
            "summary": summary,
            "provider": provider,
            "redaction_applied": redaction_applied,
            "redaction_count": redaction_count,
        }

    def _relationship_context_block(
        self, relationship_map: dict[int, str] | None
    ) -> str:
        if not relationship_map:
            return ""
        lines = [
            f"- Chat {chat_id}: {relationship}"
            for chat_id, relationship in relationship_map.items()
            if relationship
        ]
        if not lines:
            return ""
        return "Relationship context (who each receiving party is):\n" + "\n".join(lines) + "\n\n"

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
            raw, _provider = await self._generate_text(prompt, RELATIONSHIP_SYSTEM)
            parsed = self._parse_json_response(raw)
            relationship = str(parsed.get("relationship", "")).strip()
            if not relationship:
                raise ValueError("Empty relationship")
            return {"relationship": relationship, "source": "ai"}
        except Exception:
            return {
                "relationship": self._fallback_relationship(messages, chat_type, chat_title),
                "source": "ai",
            }

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
            rel = (relationship_map or {}).get(chat_id or 0, "")
            greeting = f"Hi {user}, thanks for your message."
            if rel:
                greeting = f"Hi {user}, thanks for reaching out."
            suggestions.append(
                {
                    "type": "reply",
                    "chat_id": chat_id,
                    "user": user,
                    "draft": f"{greeting} I'll follow up shortly.",
                    "action": "",
                    "priority": "medium",
                    "confidence": 0.5,
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
            "suggestions": suggestions,
            "provider": "fallback",
        }

    async def suggest_actions(
        self,
        messages: list[dict],
        relationship_map: dict[int, str] | None = None,
    ) -> dict[str, Any]:
        if not messages:
            return {
                "summary": "No messages to analyze.",
                "suggestions": [],
                "provider": "none",
                "redaction_applied": False,
                "redaction_count": 0,
            }

        redacted, redaction_count, redaction_applied = self._prepare_messages(messages)
        transcript = self._format_transcript(redacted)
        context_block = self._relationship_context_block(relationship_map)
        prompt = (
            "Analyze these Telegram messages. Suggest reply drafts for chats needing a response "
            "and next actions for the operator. "
            "Use the relationship context to tailor tone and content to who the receiving party is.\n\n"
            f"{context_block}{transcript}"
        )

        if not self.configured:
            result = self._fallback_suggestions(messages, relationship_map)
            result["redaction_applied"] = redaction_applied
            result["redaction_count"] = redaction_count
            return result

        try:
            raw, provider = await self._generate_text(prompt, SUGGEST_SYSTEM)
            parsed = self._parse_json_response(raw)
            suggestions = parsed.get("suggestions", [])
            return {
                "summary": parsed.get("summary", ""),
                "suggestions": suggestions,
                "provider": provider,
                "redaction_applied": redaction_applied,
                "redaction_count": redaction_count,
            }
        except Exception:
            result = self._fallback_suggestions(messages, relationship_map)
            result["redaction_applied"] = redaction_applied
            result["redaction_count"] = redaction_count
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
            raw, _provider = await self._generate_text(prompt, TOPIC_SYSTEM)
            parsed = self._parse_json_response(raw)
            topics = parsed.get("topics", [])
            return [str(t).strip().lower() for t in topics if str(t).strip()][:3]
        except Exception:
            return ["general"]

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

    def _fallback_thread_summary(self, messages: list[dict]) -> str:
        if len(messages) == 1:
            m = messages[0]
            name = m.get("username") or f"User {m.get('user_id')}"
            return f"{name} sent a message: {m.get('text', '')}"
        parts = []
        for msg in sorted(messages, key=lambda m: m.get("created_at", "")):
            name = msg.get("username") or f"User {msg.get('user_id')}"
            parts.append(f"{name} said \"{msg.get('text', '')}\"")
        return "Conversation summary: " + " Then, ".join(parts)

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
