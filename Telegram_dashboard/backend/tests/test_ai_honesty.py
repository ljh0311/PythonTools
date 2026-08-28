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


class TestAIGenerationHonesty(unittest.TestCase):
    def test_gemini_failure_surfaces_ollama_fallback_reason(self) -> None:
        async def run() -> None:
            svc = AIService()
            svc.gemini = MagicMock(configured=True)
            svc.gemini.generate_text = AsyncMock(
                side_effect=RuntimeError("API key invalid")
            )
            svc.ollama = MagicMock(configured=True)
            svc.ollama.is_available = AsyncMock(return_value=True)
            svc.ollama.generate_text = AsyncMock(return_value="Ollama summary")

            with patch("backend.services.ai_service.ai_rate_limiter") as limiter:
                limiter.check = MagicMock()
                with patch("backend.services.ai_service.summary_cache") as cache:
                    cache.get.return_value = None
                    cache.set = MagicMock()
                    result = await svc.summarize_messages(SAMPLE_MESSAGES)

            self.assertEqual(result["provider"], "ollama")
            self.assertTrue(result.get("degraded"))
            self.assertIn("Gemini failed", result.get("failure_reason", ""))
            self.assertIn("API key invalid", result.get("failure_reason", ""))

        asyncio.run(run())

    def test_no_providers_surfaces_fallback_reason(self) -> None:
        async def run() -> None:
            svc = AIService()
            svc.gemini = MagicMock(configured=True)
            svc.gemini.generate_text = AsyncMock(
                side_effect=RuntimeError("rate limited")
            )
            svc.ollama = MagicMock(configured=False)
            svc.ollama.is_available = AsyncMock(return_value=False)

            with patch("backend.services.ai_service.ai_rate_limiter") as limiter:
                limiter.check = MagicMock()
                with patch("backend.services.ai_service.summary_cache") as cache:
                    cache.get.return_value = None
                    cache.set = MagicMock()
                    result = await svc.summarize_messages(SAMPLE_MESSAGES)

            self.assertEqual(result["provider"], "fallback")
            self.assertTrue(result.get("degraded"))
            self.assertIn("Gemini failed", result.get("failure_reason", ""))
            self.assertIn("rate limited", result.get("failure_reason", ""))

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
            svc.ollama = MagicMock(configured=False)
            svc.ollama.is_available = AsyncMock(return_value=False)

            with patch("backend.services.ai_service.ai_rate_limiter") as limiter:
                limiter.check = MagicMock()
                result = await svc.conversation_intel(SAMPLE_MESSAGES)

            self.assertEqual(result["provider"], "gemini")
            self.assertEqual(result["topics_summary"], "Billing and scheduling updates were discussed.")
            self.assertEqual(result["sentiment_summary"], "The tone is urgent but cooperative.")
            self.assertEqual(result["needs_summary"], "They need a reply confirming next steps.")
            self.assertEqual(result["key_points"], ["Billing issue raised", "Meeting requested"])
            self.assertEqual(result["message_count"], 1)
            self.assertEqual(result["messages_analyzed"], 1)

        asyncio.run(run())

    def test_conversation_intel_fallback_marks_degraded(self) -> None:
        async def run() -> None:
            svc = AIService()
            svc.gemini = MagicMock(configured=True)
            svc.gemini.generate_text = AsyncMock(side_effect=RuntimeError("boom"))
            svc.ollama = MagicMock(configured=False)
            svc.ollama.is_available = AsyncMock(return_value=False)

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


if __name__ == "__main__":
    unittest.main()
