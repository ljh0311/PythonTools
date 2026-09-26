"""Unread / needs-reply digest service tests.

Run:
  cd Telegram_dashboard
  python -m pytest backend/tests/test_unread_digest.py -q
"""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import AsyncMock, PropertyMock, patch

from backend.models.store import DashboardStore
from backend.services import unread_digest_service as digest
from backend.services.act_open_items import heuristic_open_items


def _sample_items() -> list[dict]:
    return [
        {
            "chat_id": 10,
            "chat_title": "Alice",
            "chat_type": "private",
            "last_message_at": "2026-09-10T10:00:00",
            "last_text": "Can you review this?",
            "from_user": "alice",
            "reason": "last_inbound_unanswered",
        },
        {
            "chat_id": 20,
            "chat_title": "Bob",
            "chat_type": "private",
            "last_message_at": "2026-09-10T11:00:00",
            "last_text": "Ping when free",
            "from_user": "bob",
            "reason": "last_inbound_unanswered",
        },
    ]


class TestHeuristicOpenItems(unittest.TestCase):
    def test_inbound_latest_is_open(self) -> None:
        messages = [
            {
                "chat_id": 1,
                "chat_type": "private",
                "direction": "outgoing",
                "text": "hi",
                "created_at": "2026-01-01T10:00:00",
                "username": "me",
            },
            {
                "chat_id": 1,
                "chat_type": "private",
                "direction": "incoming",
                "text": "need help",
                "created_at": "2026-01-01T11:00:00",
                "username": "alice",
                "user_id": 9,
            },
        ]
        items = heuristic_open_items(messages)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["chat_id"], 1)
        self.assertIn("need help", items[0]["last_text"])

    def test_outbound_latest_skipped(self) -> None:
        messages = [
            {
                "chat_id": 2,
                "chat_type": "private",
                "direction": "incoming",
                "text": "hi",
                "created_at": "2026-01-01T10:00:00",
            },
            {
                "chat_id": 2,
                "chat_type": "private",
                "direction": "outgoing",
                "text": "replied",
                "created_at": "2026-01-01T11:00:00",
            },
        ]
        self.assertEqual(heuristic_open_items(messages), [])


class TestDigestService(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.store = DashboardStore(db_path=str(self.db_path))
        self._patches = [
            patch.object(digest, "store", self.store),
            patch.object(digest, "UNREAD_DIGEST_ENABLED", True),
            patch.object(digest, "UNREAD_DIGEST_CHAT_ID", "999001"),
            patch.object(digest, "UNREAD_DIGEST_QUIET_START", None),
            patch.object(digest, "UNREAD_DIGEST_QUIET_END", None),
        ]
        for p in self._patches:
            p.start()

    def tearDown(self) -> None:
        for p in self._patches:
            p.stop()
        self.tmp.cleanup()

    def test_empty_open_items_no_send(self) -> None:
        async def run() -> None:
            with (
                patch.object(digest, "gather_open_items", return_value=[]),
                patch.object(
                    type(digest.telegram_service),
                    "configured",
                    new_callable=PropertyMock,
                    return_value=True,
                ),
                patch.object(
                    digest.telegram_service,
                    "send_message",
                    new_callable=AsyncMock,
                ) as send,
            ):
                result = await digest.run_digest(force=True)
                self.assertFalse(result["sent"])
                self.assertEqual(result["reason"], "empty")
                send.assert_not_awaited()

        asyncio.run(run())

    def test_watermark_unchanged_no_send(self) -> None:
        items = _sample_items()
        fp = digest.fingerprint_open_items(items)
        self.store.set_setting(digest.SETTING_FINGERPRINT, fp)

        async def run() -> None:
            with (
                patch.object(digest, "gather_open_items", return_value=items),
                patch.object(
                    type(digest.telegram_service),
                    "configured",
                    new_callable=PropertyMock,
                    return_value=True,
                ),
                patch.object(
                    digest.telegram_service,
                    "send_message",
                    new_callable=AsyncMock,
                ) as send,
            ):
                result = await digest.run_digest(force=False)
                self.assertFalse(result["sent"])
                self.assertEqual(result["reason"], "unchanged")
                send.assert_not_awaited()

        asyncio.run(run())

    def test_ai_fail_still_sends_heuristic(self) -> None:
        items = _sample_items()

        async def run() -> None:
            with (
                patch.object(digest, "gather_open_items", return_value=items),
                patch.object(
                    type(digest.telegram_service),
                    "configured",
                    new_callable=PropertyMock,
                    return_value=True,
                ),
                patch.object(
                    digest.telegram_service,
                    "send_message",
                    new_callable=AsyncMock,
                ) as send,
                patch.object(
                    digest.ai_service,
                    "summarize_messages",
                    new_callable=AsyncMock,
                    side_effect=RuntimeError("ollama down"),
                ),
            ):
                result = await digest.run_digest(force=True)
                self.assertTrue(result["sent"])
                self.assertEqual(result["provider"], "heuristic")
                send.assert_awaited_once()
                body = send.await_args.args[1]
                self.assertIn("Needs-reply digest", body)
                self.assertIn("Alice", body)
                self.assertIn("Bob", body)
                saved_fp = self.store.get_setting(digest.SETTING_FINGERPRINT, "")
                self.assertEqual(saved_fp, digest.fingerprint_open_items(items))

        asyncio.run(run())

    def test_quiet_hours_skip(self) -> None:
        with (
            patch.object(digest, "UNREAD_DIGEST_QUIET_START", 22),
            patch.object(digest, "UNREAD_DIGEST_QUIET_END", 7),
        ):
            self.assertTrue(digest.in_quiet_hours(datetime(2026, 9, 10, 23, 0, 0)))
            self.assertTrue(digest.in_quiet_hours(datetime(2026, 9, 10, 3, 0, 0)))
            self.assertFalse(digest.in_quiet_hours(datetime(2026, 9, 10, 12, 0, 0)))


if __name__ == "__main__":
    unittest.main()
