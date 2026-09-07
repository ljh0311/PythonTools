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
from backend.routes.v2_api import ActStatusRequest, act_update_status


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


if __name__ == "__main__":
    unittest.main()
