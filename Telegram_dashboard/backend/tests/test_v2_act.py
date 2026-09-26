"""Act reply-state + triage status tests.

Run:
  cd Telegram_dashboard
  python -m pytest backend/tests/test_v2_act.py backend/tests/test_act_reply_state.py -q
"""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.models.store import DashboardStore
from backend.routes.v2_api import ActStatusRequest, act_update_status
from backend.services.act_reply_state import (
    build_fallback_reply_suggestion,
    enrich_suggestion,
    reply_state_for_messages,
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

        sent = self.store.update_suggestion_status(sid, "sent")
        assert sent is not None
        self.assertEqual(sent["status"], "sent")

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

                sent = await act_update_status(sid, ActStatusRequest(status="sent"))
                self.assertEqual(sent["status"], "sent")

        asyncio.run(run())


class TestReplyStateHelper(unittest.TestCase):
    def test_needs_reply_when_last_inbound(self) -> None:
        msgs = [
            {"direction": "outgoing", "text": "hi", "created_at": "2026-01-01T10:00:00"},
            {"direction": "incoming", "text": "can you help?", "created_at": "2026-01-01T11:00:00"},
        ]
        state = reply_state_for_messages(msgs)
        self.assertTrue(state["needs_reply"])
        self.assertFalse(state["already_replied"])
        self.assertEqual(state["reply_state"], "needs_reply")
        self.assertIn("can you help", state["last_inbound_text"])

    def test_already_replied_when_last_outbound(self) -> None:
        msgs = [
            {"direction": "incoming", "text": "ping", "created_at": "2026-01-01T10:00:00"},
            {"direction": "outgoing", "text": "pong — done", "created_at": "2026-01-01T11:00:00"},
        ]
        state = reply_state_for_messages(msgs)
        self.assertTrue(state["already_replied"])
        self.assertFalse(state["needs_reply"])
        self.assertEqual(state["reply_state"], "already_replied")
        self.assertIn("pong", state["last_outbound_text"])

    def test_fallback_already_replied_empty_draft(self) -> None:
        msgs = [
            {
                "chat_id": 42,
                "direction": "incoming",
                "text": "Need approval",
                "username": "alice",
                "created_at": "2026-01-01T10:00:00",
            },
            {
                "chat_id": 42,
                "direction": "outgoing",
                "text": "Approved yesterday",
                "created_at": "2026-01-01T12:00:00",
            },
        ]
        item = build_fallback_reply_suggestion(42, msgs)
        assert item is not None
        self.assertEqual(item["draft"], "")
        self.assertTrue(item["already_replied"])
        self.assertTrue(item["draft_suppressed"])
        self.assertIn("Already replied", item["action"])

    def test_fallback_needs_reply_content_aware(self) -> None:
        msgs = [
            {
                "chat_id": 9,
                "direction": "incoming",
                "text": "What time works for the call?",
                "username": "bob",
                "user_id": 9,
                "created_at": "2026-01-01T10:00:00",
            },
        ]
        item = build_fallback_reply_suggestion(9, msgs)
        assert item is not None
        self.assertTrue(item["needs_reply"])
        self.assertIn("What time works", item["draft"])
        self.assertNotIn("I'll follow up shortly", item["draft"])
        self.assertTrue(item["ai_unavailable"])

    def test_enrich_suppresses_draft_when_already_replied(self) -> None:
        item = {
            "id": 1,
            "status": "pending",
            "type": "reply",
            "payload": {
                "type": "reply",
                "chat_id": 5,
                "draft": 'Hi alice - re: "old"',
                "user": "alice",
            },
        }
        enriched = enrich_suggestion(
            item,
            {
                5: {
                    "reply_state": "already_replied",
                    "needs_reply": False,
                    "already_replied": True,
                    "last_inbound_text": "old",
                    "last_outbound_text": "Already handled",
                    "last_inbound_at": None,
                    "last_outbound_at": None,
                    "last_direction": "outgoing",
                }
            },
        )
        self.assertEqual(enriched["display_draft"], "")
        self.assertTrue(enriched["draft_suppressed"])
        self.assertEqual(enriched["last_outbound_text"], "Already handled")

    def test_ai_fallback_skips_fake_template_for_answered(self) -> None:
        svc = AIService.__new__(AIService)
        messages = [
            {
                "chat_id": 1,
                "direction": "incoming",
                "text": "hello?",
                "username": "x",
                "user_id": 1,
                "created_at": "2026-01-01T10:00:00",
            },
            {
                "chat_id": 1,
                "direction": "outgoing",
                "text": "answered",
                "created_at": "2026-01-01T11:00:00",
            },
            {
                "chat_id": 2,
                "direction": "incoming",
                "text": "still waiting on the invoice?",
                "username": "y",
                "user_id": 2,
                "created_at": "2026-01-01T12:00:00",
            },
        ]
        result = svc._fallback_suggestions(messages)
        by_chat = {s.get("chat_id"): s for s in result["suggestions"]}
        self.assertIn(1, by_chat)
        self.assertEqual(by_chat[1]["draft"], "")
        self.assertTrue(by_chat[1]["already_replied"])
        self.assertIn(2, by_chat)
        self.assertIn("invoice", by_chat[2]["draft"])
        self.assertNotIn("I'll follow up shortly", by_chat[2]["draft"])


if __name__ == "__main__":
    unittest.main()
