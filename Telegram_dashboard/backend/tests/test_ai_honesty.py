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


if __name__ == "__main__":
    unittest.main()
