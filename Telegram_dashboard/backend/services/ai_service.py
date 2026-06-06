from backend.services.providers.gemini import GeminiProvider
from backend.services.providers.ollama import OllamaProvider


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

    def _format_transcript(self, messages: list[dict]) -> str:
        lines = []
        for msg in sorted(messages, key=lambda m: m.get("created_at", "")):
            name = msg.get("username") or f"User {msg.get('user_id')}"
            lines.append(f"{name}: {msg.get('text', '')}")
        return "\n".join(lines)

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

    async def summarize_thread(self, messages: list[dict]) -> dict:
        if not messages:
            return {"summary": "No messages in this conversation.", "provider": "none"}

        transcript = self._format_transcript(messages)
        system = (
            "You summarize Telegram conversations for an operator dashboard. "
            "Write 1-3 clear English sentences. Explain who said what, "
            "note any updates, conflicts, or action items. Be concise."
        )
        prompt = f"Summarize this conversation:\n\n{transcript}"

        errors: list[str] = []
        if self.gemini.configured:
            try:
                summary = await self.gemini.generate_text(prompt, system=system)
                return {"summary": summary, "provider": "gemini"}
            except Exception as exc:
                errors.append(str(exc))

        if self.ollama.configured:
            try:
                if await self.ollama.is_available():
                    summary = await self.ollama.generate_text(prompt, system=system)
                    return {"summary": summary, "provider": "ollama"}
            except Exception as exc:
                errors.append(str(exc))

        summary = self._fallback_thread_summary(messages)
        if errors:
            summary += f" (AI unavailable: {'; '.join(errors)})"
        return {"summary": summary, "provider": "fallback"}

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
