"""Chat memory store and profile learning tests.

Run:
  cd Telegram_dashboard
  python -m unittest backend.tests.test_chat_memories -v
"""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

from backend.models.store import DashboardStore
from backend.services.ai_service import AIService

SAMPLE_MESSAGES = [
    {
        "id": 1,
        "text": "I prefer email updates over calls",
        "user_id": 42,
        "username": "alice",
        "direction": "incoming",
        "created_at": "2026-01-01T10:00:00",
        "chat_id": 100,
        "chat_type": "private",
        "chat_title": "Alice",
    },
    {
        "id": 2,
        "text": "Sure, I'll send a summary every Friday",
        "user_id": 1,
        "username": "operator",
        "direction": "outgoing",
        "created_at": "2026-01-01T10:05:00",
        "chat_id": 100,
        "chat_type": "private",
        "chat_title": "Alice",
    },
]


class TestChatMemoriesStore(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.store = DashboardStore(db_path=str(self.db_path))
        self.store.sync_chat_settings_from_messages()
        self.store.update_chat_settings(100, enabled=False)

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_add_list_and_clear_ai_memories(self) -> None:
        saved = self.store.add_chat_memories(
            100,
            [
                {"type": "fact", "content": "Works in finance"},
                {"type": "preference", "content": "Prefers async updates"},
                {"type": "invalid", "content": "skipped"},
            ],
            source="ai",
        )
        self.assertEqual(len(saved), 2)

        manual = self.store.add_chat_memories(
            100,
            [{"type": "habit", "content": "Checks in on Fridays"}],
            source="manual",
        )
        self.assertEqual(len(manual), 1)

        listed = self.store.list_chat_memories(100, limit=10)
        self.assertEqual(len(listed), 3)

        cleared = self.store.clear_ai_memories(100)
        self.assertEqual(cleared, 2)
        remaining = self.store.list_chat_memories(100)
        self.assertEqual(len(remaining), 1)
        self.assertEqual(remaining[0]["source"], "manual")


class TestLearnProfileFromThread(unittest.TestCase):
    def test_fallback_when_ai_unconfigured(self) -> None:
        async def run() -> None:
            svc = AIService()
            svc.gemini = MagicMock(configured=False)
            svc.ollama = MagicMock(configured=False)
            result = await svc.learn_profile_from_thread(
                SAMPLE_MESSAGES, chat_type="private", chat_title="Alice"
            )

            self.assertTrue(result["memories"])
            self.assertTrue(result["relationship"])
            self.assertTrue(result["ai_context"])
            self.assertEqual(result["source"], "ai")

        asyncio.run(run())

    def test_ai_response_normalized(self) -> None:
        async def run() -> None:
            svc = AIService()
            svc.gemini = MagicMock(configured=True)
            svc.gemini.generate_text = AsyncMock(
                return_value=(
                    '{"memories": [{"type": "preference", "content": "Prefers email"}], '
                    '"relationship": "Alice is a finance contact.", '
                    '"ai_context": "- Preference: email updates"}'
                )
            )
            svc.ollama = MagicMock(configured=False)

            with patch("backend.services.ai_service.ai_rate_limiter") as limiter:
                limiter.check = MagicMock()
                result = await svc.learn_profile_from_thread(
                    SAMPLE_MESSAGES, chat_type="private", chat_title="Alice"
                )

            self.assertEqual(len(result["memories"]), 1)
            self.assertEqual(result["memories"][0]["type"], "preference")
            self.assertIn("Alice", result["relationship"])
            self.assertIn("email", result["ai_context"])

        asyncio.run(run())


if __name__ == "__main__":
    unittest.main()
