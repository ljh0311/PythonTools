"""AI honesty regression tests.

Reproduction (before fix):
  `_generate_text` caught Gemini errors with `except Exception: pass`, then silently
  fell back to Ollama or a generic fallback summary. Operators saw "AI summary
  unavailable" with no indication Gemini failed vs Ollama missing.

Run:
  cd Telegram_dashboard
  python -m unittest backend.tests.test_ai_honesty -v
"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.ai_service import AIService

SAMPLE_MESSAGES = [
    {
        "id": 1,
        "text": "Need help with billing",
        "user_id": 42,
        "username": "alice",
        "created_at": "2026-01-01T10:00:00",
        "chat_id": 100,
    }
]


def _mock_ollama(
    svc: AIService,
    *,
    configured: bool = True,
    model: str = "llama3.2",
    names: list[str] | None = None,
    text: str | list[str] = "Ollama summary",
) -> MagicMock:
    svc.ollama = MagicMock(configured=configured)
    svc.ollama.model = model
    if not configured:
        svc.ollama.list_model_names = AsyncMock(return_value=None)
        svc.ollama.generate_text = AsyncMock(side_effect=RuntimeError("not configured"))
        return svc.ollama
    svc.ollama.list_model_names = AsyncMock(
        return_value=names if names is not None else [f"{model}:latest"]
    )
    svc.ollama._model_installed = MagicMock(return_value=True)
    if isinstance(text, list):
        svc.ollama.generate_text = AsyncMock(side_effect=text)
    else:
        svc.ollama.generate_text = AsyncMock(return_value=text)
    return svc.ollama


class TestAIGenerationHonesty(unittest.TestCase):
    def test_gemini_failure_surfaces_ollama_fallback_reason(self) -> None:
        async def run() -> None:
            svc = AIService()
            svc.gemini = MagicMock(configured=True)
            svc.gemini.generate_text = AsyncMock(
                side_effect=RuntimeError("API key invalid")
            )
            _mock_ollama(svc, text="Ollama summary")

            with patch("backend.services.ai_service.AI_PRIMARY_PROVIDER", "gemini"):
                with patch("backend.services.ai_service.ai_rate_limiter") as limiter:
                    limiter.check = MagicMock()
                    with patch("backend.services.ai_service.summary_cache") as cache:
                        cache.get.return_value = None
                        cache.set = MagicMock()
                        result = await svc.summarize_messages(SAMPLE_MESSAGES)

            self.assertEqual(result["provider"], "ollama")
            self.assertTrue(result.get("degraded"))
            reason = result.get("failure_reason", "")
            self.assertTrue(
                "API key invalid" in reason
                or "Gemini" in reason
                or "invalid" in reason.lower(),
                reason,
            )

        asyncio.run(run())

    def test_no_providers_surfaces_fallback_reason(self) -> None:
        async def run() -> None:
            svc = AIService()
            svc.gemini = MagicMock(configured=True)
            svc.gemini.generate_text = AsyncMock(
                side_effect=RuntimeError("rate limited")
            )
            _mock_ollama(svc, configured=False)

            with patch("backend.services.ai_service.AI_PRIMARY_PROVIDER", "gemini"):
                with patch("backend.services.ai_service.ai_rate_limiter") as limiter:
                    limiter.check = MagicMock()
                    with patch("backend.services.ai_service.summary_cache") as cache:
                        cache.get.return_value = None
                        cache.set = MagicMock()
                        result = await svc.summarize_messages(SAMPLE_MESSAGES)

            self.assertEqual(result["provider"], "fallback")
            self.assertTrue(result.get("degraded"))
            reason = result.get("failure_reason", "")
            self.assertTrue(
                "rate" in reason.lower()
                or "429" in reason
                or "limited" in reason.lower(),
                reason,
            )

        asyncio.run(run())

    def test_conversation_intel_parses_strict_json(self) -> None:
        async def run() -> None:
            svc = AIService()
            svc.gemini = MagicMock(configured=True)
            svc.gemini.generate_text = AsyncMock(
                return_value=(
                    '{"topics_summary":"Billing and scheduling updates were discussed.",'
                    '"sentiment_summary":"The tone is urgent but cooperative.",'
                    '"needs_summary":"They need a reply confirming next steps.",'
                    '"key_points":["Billing issue raised","Meeting requested"]}'
                )
            )
            _mock_ollama(svc, configured=False)

            with patch("backend.services.ai_service.AI_PRIMARY_PROVIDER", "gemini"):
                with patch("backend.services.ai_service.ai_rate_limiter") as limiter:
                    limiter.check = MagicMock()
                    result = await svc.conversation_intel(SAMPLE_MESSAGES)

            self.assertEqual(result["provider"], "gemini")
            self.assertEqual(
                result["topics_summary"],
                "Billing and scheduling updates were discussed.",
            )
            self.assertEqual(
                result["sentiment_summary"], "The tone is urgent but cooperative."
            )
            self.assertEqual(
                result["needs_summary"],
                "They need a reply confirming next steps.",
            )
            self.assertEqual(
                result["key_points"], ["Billing issue raised", "Meeting requested"]
            )
            self.assertEqual(result["message_count"], 1)
            self.assertEqual(result["messages_analyzed"], 1)

        asyncio.run(run())

    def test_conversation_intel_fallback_marks_degraded(self) -> None:
        async def run() -> None:
            svc = AIService()
            svc.gemini = MagicMock(configured=True)
            svc.gemini.generate_text = AsyncMock(side_effect=RuntimeError("boom"))
            _mock_ollama(svc, configured=False)

            with patch("backend.services.ai_service.AI_PRIMARY_PROVIDER", "gemini"):
                with patch("backend.services.ai_service.ai_rate_limiter") as limiter:
                    limiter.check = MagicMock()
                    result = await svc.conversation_intel(SAMPLE_MESSAGES)

            self.assertEqual(result["provider"], "fallback")
            self.assertTrue(result.get("degraded"))
            self.assertIn("RuntimeError: boom", result.get("failure_reason", ""))
            self.assertIn("topics_summary", result)
            self.assertIn("sentiment_summary", result)
            self.assertIn("needs_summary", result)

        asyncio.run(run())

    def test_provider_error_redacts_api_key_in_url(self) -> None:
        from backend.services.ai_service import _safe_provider_error

        err = RuntimeError(
            "HTTPStatusError: Client error '429' for url "
            "'https://generativelanguage.googleapis.com/v1beta/models/x:generateContent?key=SECRET123'"
        )
        safe = _safe_provider_error(err)
        self.assertNotIn("SECRET123", safe)
        self.assertIn("key=[REDACTED]", safe)

    def test_rejects_garbled_ollama_text_and_uses_heuristic_summary(self) -> None:
        async def run() -> None:
            svc = AIService()
            svc.gemini = MagicMock(configured=True)
            svc.gemini.generate_text = AsyncMock(
                side_effect=RuntimeError(
                    "HTTPStatusError: Client error '429 Too Many Requests' for url "
                    "'https://generativelanguage.googleapis.com/v1beta/models/"
                    "gemini-3.6-flash:generateContent?key=SECRET'"
                )
            )
            _mock_ollama(svc, text="@" * 31)

            with patch("backend.services.ai_service.AI_PRIMARY_PROVIDER", "gemini"):
                with patch("backend.services.ai_service.OLLAMA_FALLBACK_MODELS", []):
                    with patch("backend.services.ai_service.ai_rate_limiter") as limiter:
                        limiter.check = MagicMock()
                        with patch("backend.services.ai_service.summary_cache") as cache:
                            cache.get.return_value = None
                            cache.set = MagicMock()
                            result = await svc.summarize_messages(SAMPLE_MESSAGES)

            self.assertEqual(result["provider"], "fallback")
            self.assertTrue(result.get("degraded"))
            self.assertNotIn(
                "@", result.get("summary", "")[:5] * 0 + result.get("summary", "")
            )
            self.assertNotIn("SECRET", result.get("failure_reason", ""))
            self.assertNotIn(
                "generativelanguage.googleapis.com", result.get("failure_reason", "")
            )
            self.assertIn("rate-limited", result.get("failure_reason", "").lower())

        asyncio.run(run())

    def test_garbled_primary_ollama_retries_fallback_model(self) -> None:
        async def run() -> None:
            svc = AIService()
            svc.gemini = MagicMock(configured=True)
            svc.gemini.generate_text = AsyncMock(
                side_effect=RuntimeError("Gemini rate-limited (429)")
            )
            ollama = _mock_ollama(
                svc,
                model="llama3.2",
                names=["llama3.2:latest", "qwen2.5:3b"],
                text=["@" * 31, "Clear local summary about billing."],
            )

            with patch("backend.services.ai_service.AI_PRIMARY_PROVIDER", "gemini"):
                with patch(
                    "backend.services.ai_service.OLLAMA_FALLBACK_MODELS",
                    ["qwen2.5:3b"],
                ):
                    with patch("backend.services.ai_service.ai_rate_limiter") as limiter:
                        limiter.check = MagicMock()
                        with patch("backend.services.ai_service.summary_cache") as cache:
                            cache.get.return_value = None
                            cache.set = MagicMock()
                            result = await svc.summarize_messages(SAMPLE_MESSAGES)

            self.assertEqual(result["provider"], "ollama")
            self.assertIn("billing", result.get("summary", "").lower())
            self.assertEqual(ollama.generate_text.await_count, 2)

        asyncio.run(run())

    def test_is_usable_ai_text_rejects_at_signs(self) -> None:
        from backend.services.ai_service import _is_usable_ai_text

        self.assertFalse(_is_usable_ai_text("@" * 31))
        self.assertTrue(
            _is_usable_ai_text("They asked about keychains and want a reply.")
        )

    def test_gemini_429_falls_back_to_ollama_with_redacted_reason(self) -> None:
        async def run() -> None:
            svc = AIService()
            svc.gemini = MagicMock(configured=True)
            svc.gemini.generate_text = AsyncMock(
                side_effect=RuntimeError(
                    "HTTPStatusError: Client error '429 Too Many Requests' for url "
                    "'https://generativelanguage.googleapis.com/v1beta/models/"
                    "gemini-3.6-flash:generateContent?key=SECRET_KEY_VALUE'"
                )
            )
            _mock_ollama(svc, text="Local summary")

            with patch("backend.services.ai_service.AI_PRIMARY_PROVIDER", "gemini"):
                with patch("backend.services.ai_service.ai_rate_limiter") as limiter:
                    limiter.check = MagicMock()
                    with patch("backend.services.ai_service.summary_cache") as cache:
                        cache.get.return_value = None
                        cache.set = MagicMock()
                        result = await svc.summarize_messages(SAMPLE_MESSAGES)

            self.assertEqual(result["provider"], "ollama")
            self.assertTrue(result.get("degraded"))
            reason = result.get("failure_reason", "")
            self.assertIn("429", reason)
            self.assertNotIn("SECRET_KEY_VALUE", reason)
            self.assertNotIn("generativelanguage.googleapis.com", reason)
            self.assertIn("Ollama", reason)

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
