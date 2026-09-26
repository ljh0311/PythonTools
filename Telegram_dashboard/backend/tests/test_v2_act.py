"""Act reply-state + quality logging tests.

Run:
  cd Telegram_dashboard
  python -m pytest backend/tests/test_v2_act.py backend/tests/test_act_quality.py -q
"""

from __future__ import annotations

import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, patch

from backend.models.store import DashboardStore
from backend.routes.v2_api import ActStatusRequest, act_update_status
from backend.services.act_quality import analyze_queue_quality
from backend.services.act_reply_state import (
    build_fallback_reply_suggestion,
    chat_peer_meta,
    enrich_suggestion,
    enrich_suggestions,
    is_placeholder_peer_label,
    merge_open_items,
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

    def test_already_replied_when_last_outbound(self) -> None:
        msgs = [
            {"direction": "incoming", "text": "ping", "created_at": "2026-01-01T10:00:00"},
            {"direction": "outgoing", "text": "pong — done", "created_at": "2026-01-01T11:00:00"},
        ]
        state = reply_state_for_messages(msgs)
        self.assertTrue(state["already_replied"])
        self.assertEqual(state["reply_state"], "already_replied")

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

    def test_placeholder_peer_label(self) -> None:
        self.assertTrue(is_placeholder_peer_label("chat -1003482571977"))
        self.assertTrue(is_placeholder_peer_label("Chat 42"))
        self.assertFalse(is_placeholder_peer_label("Ahmosl"))

    def test_group_display_title_prefers_chat_title(self) -> None:
        msgs = [
            {
                "chat_id": -1001,
                "chat_type": "group",
                "chat_title": "IS THIS BALI",
                "direction": "incoming",
                "username": "Ahmosl",
                "text": "sheesh",
                "created_at": "2026-01-01T11:00:00",
            }
        ]
        meta = chat_peer_meta(msgs)
        self.assertEqual(meta["display_title"], "IS THIS BALI")
        self.assertEqual(meta["from_user"], "Ahmosl")

        item = {
            "id": 9,
            "status": "pending",
            "type": "reply",
            "payload": {
                "type": "reply",
                "chat_id": -1001,
                "user": "chat -1001",
                "draft": "",
            },
        }
        enriched = enrich_suggestions([item], msgs)[0]
        self.assertEqual(enriched["display_title"], "IS THIS BALI")
        self.assertEqual(enriched["user"], "Ahmosl")
        self.assertEqual(enriched["chat_title"], "IS THIS BALI")

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
        self.assertEqual(by_chat[1]["draft"], "")
        self.assertTrue(by_chat[1]["already_replied"])
        self.assertIn("invoice", by_chat[2]["draft"])


class TestActQuality(unittest.TestCase):
    def test_detects_false_needs_and_missing_dues(self) -> None:
        enriched = [
            {
                "id": 1,
                "status": "pending",
                "type": "reply",
                "chat_id": 10,
                "draft": "fake reply",
                "already_replied": True,
                "needs_reply": False,
                "ai_draft_ignored": True,
                "due_hint": "",
            }
        ]
        open_items = [
            {
                "chat_id": 99,
                "last_message_at": "2026-01-02T10:00:00",
                "last_text": "are you free today?",
                "from_user": "bob",
            }
        ]
        final = merge_open_items(enriched, open_items)
        metrics = analyze_queue_quality(
            raw_suggestions=enriched,
            enriched_before_merge=enriched,
            open_items=open_items,
            final_queue=final,
        )
        self.assertGreaterEqual(metrics["false_needs_reply_count"], 1)
        self.assertEqual(metrics["missing_dues_count"], 1)
        self.assertEqual(metrics["merged_from_open_items"], 1)
        self.assertTrue(any(s.get("chat_id") == 99 for s in final))


if __name__ == "__main__":
    unittest.main()
