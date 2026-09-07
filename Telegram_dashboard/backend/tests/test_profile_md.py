"""profile_md round-trip tests.

Run:
  cd Telegram_dashboard
  python -m pytest backend/tests/test_profile_md.py -q
  # or: python -m unittest backend.tests.test_profile_md -v
"""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from backend.services import profile_md
from backend.services.profile_md import ProfileDoc


class TestProfileMdRoundTrip(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.profiles_dir = Path(self.tmp.name)
        self._patcher = patch.object(profile_md, "PROFILES_DIR", self.profiles_dir)
        self._patcher.start()

    def tearDown(self) -> None:
        self._patcher.stop()
        self.tmp.cleanup()

    def test_write_read_round_trip(self) -> None:
        doc = ProfileDoc(
            chat_id=4242,
            name="Alice Example",
            relationship="Colleague",
            summary="Direct and brief.",
            facts="- Prefers async\n- Timezone: UTC+8",
            notes="Follow up Fridays.",
        )
        written = profile_md.write_profile(doc)
        self.assertTrue(written.path and written.path.exists())
        self.assertEqual(written.path.name, "4242-alice-example.md")

        loaded = profile_md.get_profile(4242)
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded.chat_id, 4242)
        self.assertEqual(loaded.name, "Alice Example")
        self.assertEqual(loaded.relationship, "Colleague")
        self.assertIn("Direct and brief", loaded.summary)
        self.assertIn("Prefers async", loaded.facts)
        self.assertIn("Follow up Fridays", loaded.notes)

        listed = profile_md.list_profiles()
        self.assertEqual(len(listed), 1)
        self.assertEqual(listed[0]["chat_id"], 4242)
        self.assertEqual(listed[0]["filename"], "4242-alice-example.md")

    def test_save_profile_markdown_round_trip(self) -> None:
        markdown = profile_md.render_markdown(
            ProfileDoc(
                chat_id=99,
                name="Bob",
                relationship="Friend",
                summary="Met at meetup.",
                facts="- Likes coffee",
                notes="",
            )
        )
        saved = profile_md.save_profile_markdown(99, markdown)
        again = profile_md.parse_markdown(saved.path.read_text(encoding="utf-8"), path=saved.path)
        self.assertEqual(again.chat_id, 99)
        self.assertEqual(again.name, "Bob")
        self.assertIn("meetup", again.summary)
        self.assertIn("coffee", again.facts)


if __name__ == "__main__":
    unittest.main()
