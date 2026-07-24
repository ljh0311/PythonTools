"""Profile learner tests (native path + optional SmartPersona stub).

Run:
  cd Telegram_dashboard
  python -m unittest backend.tests.test_profile_learner -v
"""

from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

from backend.services.profile_learner import (
    LearnResult,
    _merge_ai_context,
    learn_from_chat,
)

SAMPLE_MESSAGES = [
    {
        "id": 1,
        "text": "Call me yappy, not y4ppy",
        "user_id": 42,
        "username": "alice",
        "direction": "incoming",
        "created_at": "2026-01-01T10:00:00",
        "chat_id": 100,
        "chat_type": "private",
        "chat_title": "Alice",
    },
]


class TestProfileLearnerHelpers(unittest.TestCase):
    def test_merge_ai_context_appends_new_bullets(self) -> None:
        merged = _merge_ai_context("- Alias: yappy", ["Voice: informal tone"])
        self.assertIn("yappy", merged)
        self.assertIn("informal", merged.lower())


class TestLearnFromChat(unittest.TestCase):
    def test_native_learn_updates_relationship_and_context(self) -> None:
        async def run() -> None:
            with patch("backend.services.profile_learner.ai_service") as ai:
                ai.learn_from_thread = AsyncMock(
                    return_value={
                        "relationship": "Alice is a direct contact.",
                        "ai_context": "- Alias: yappy",
                        "facts": ["Prefers async updates"],
                        "source": "ai",
                    }
                )
                with patch(
                    "backend.services.profile_learner._try_smartpersona_bullets",
                    AsyncMock(return_value=[]),
                ):
                    result = await learn_from_chat(
                        100,
                        SAMPLE_MESSAGES,
                        {"chat_type": "private", "chat_title": "Alice"},
                    )

            self.assertIsInstance(result, LearnResult)
            self.assertIn("Alice", result.relationship)
            self.assertIn("yappy", result.ai_context)
            self.assertFalse(result.smartpersona_used)
            self.assertEqual(result.provider, "native")

        asyncio.run(run())

    def test_smartpersona_bullets_merge_into_ai_context(self) -> None:
        async def run() -> None:
            with patch("backend.services.profile_learner.ai_service") as ai:
                ai.learn_from_thread = AsyncMock(
                    return_value={
                        "relationship": "Alice is a direct contact.",
                        "ai_context": "- Alias: yappy",
                        "facts": [],
                        "source": "ai",
                    }
                )
                with patch(
                    "backend.services.profile_learner._try_smartpersona_bullets",
                    AsyncMock(return_value=["Voice: informal tone"]),
                ):
                    result = await learn_from_chat(100, SAMPLE_MESSAGES, {})

            self.assertTrue(result.smartpersona_used)
            self.assertEqual(result.provider, "native+smartpersona")
            self.assertIn("informal", result.ai_context.lower())

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
