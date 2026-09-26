"""v2 Act suggestion status update tests.

Run:
  cd Telegram_dashboard
  python -m pytest backend/tests/test_v2_act.py -q
  # or: python -m unittest backend.tests.test_v2_act -v
"""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.models.store import DashboardStore
from backend.routes.v2_api import (
    ActStatusRequest,
    _chat_reply_state,
    _enrich_with_reply_state,
    act_update_status,
)
from backend.services.ai_service import AIService


class TestActStatusUpdate(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tmp.name) / "test.db"
        self.store = DashboardStore(db_path=str(self.db_path))

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_store_update_suggestion_status(self) -> None:
        saved = self.store.save_suggestions(
            "v2-act",
            [{"type": "next_action", "text": "Reply to Alice", "chat_id": 100}],
        )
        self.assertEqual(len(saved), 1)
        sid = saved[0]["id"]
        self.assertEqual(saved[0]["status"], "pending")

        updated = self.store.update_suggestion_status(sid, "done")
        self.assertIsNotNone(updated)
        assert updated is not None
        self.assertEqual(updated["status"], "done")
        self.assertEqual(updated["id"], sid)

        dismissed = self.store.update_suggestion_status(sid, "dismissed")
        assert dismissed is not None
        self.assertEqual(dismissed["status"], "dismissed")

        listed = self.store.list_suggestions(filter_hash="v2-act", include_dismissed=True)
        self.assertEqual(listed[0]["status"], "dismissed")

    def test_act_route_patches_status(self) -> None:
        saved = self.store.save_suggestions(
            "v2-act",
            [{"type": "next_action", "text": "Follow up", "chat_id": 7}],
        )
        sid = int(saved[0]["id"])

        async def run() -> None:
            with patch("backend.routes.v2_api.store", self.store), patch(
                "backend.routes.v2_api.ws_manager"
            ) as ws:
                ws.broadcast = AsyncMock()
                result = await act_update_status(sid, ActStatusRequest(status="done"))
                self.assertEqual(result["status"], "done")
                self.assertEqual(result["id"], sid)
                ws.broadcast.assert_awaited()

        asyncio.run(run())


class TestFallbackReplyDraft(unittest.TestCase):
    def test_fallback_draft_is_multi_sentence_and_references_content(self) -> None:
        svc = AIService()
        messages = [
            {
                "chat_id": 42,
                "direction": "incoming",
                "username": "cherrychrissy",
                "user_id": 1,
                "text": "i wanna show u the KEYCHAINSSSS",
                "created_at": "2026-03-01T12:00:00",
            }
        ]
        result = svc._fallback_suggestions(messages)
        self.assertEqual(result["provider"], "fallback")
        self.assertEqual(len(result["suggestions"]), 1)
        suggestion = result["suggestions"][0]
        draft = suggestion["draft"]
        sentences = [s for s in draft.replace("?", ".").split(".") if s.strip()]
        self.assertGreaterEqual(len(sentences), 2, draft)
        self.assertIn("KEYCHAIN", draft.upper())
        self.assertNotRegex(draft, r"^Hi \w+ - re:")
        self.assertTrue(suggestion.get("action"))
        self.assertIn("cherrychrissy", suggestion["action"])


class TestActReplyState(unittest.TestCase):
    def test_already_replied_when_outbound_follows_inbound(self) -> None:
        state = _chat_reply_state(
            [
                {
                    "direction": "incoming",
                    "text": "ping",
                    "created_at": "2026-03-01T10:00:00",
                },
                {
                    "direction": "outgoing",
                    "text": "pong",
                    "created_at": "2026-03-01T10:05:00",
                },
            ]
        )
        self.assertTrue(state["already_replied"])
        self.assertEqual(state["last_inbound_text"], "ping")
        self.assertEqual(state["last_outbound_text"], "pong")

    def test_needs_reply_when_inbound_is_latest(self) -> None:
        state = _chat_reply_state(
            [
                {
                    "direction": "outgoing",
                    "text": "hey",
                    "created_at": "2026-03-01T09:00:00",
                },
                {
                    "direction": "incoming",
                    "text": "need help",
                    "created_at": "2026-03-01T11:00:00",
                },
            ]
        )
        self.assertFalse(state["already_replied"])
        self.assertEqual(state["last_inbound_text"], "need help")

    def test_enrich_suggestions_merges_reply_state(self) -> None:
        by_chat = {
            9: [
                {
                    "direction": "incoming",
                    "text": "hello",
                    "created_at": "2026-03-01T08:00:00",
                }
            ]
        }
        enriched = _enrich_with_reply_state(
            [{"id": 1, "chat_id": 9, "type": "reply", "payload": {"chat_id": 9}}],
            by_chat,
        )
        self.assertFalse(enriched[0]["already_replied"])
        self.assertEqual(enriched[0]["last_inbound_text"], "hello")
        self.assertEqual(enriched[0]["payload"]["already_replied"], False)


if __name__ == "__main__":
    unittest.main()
