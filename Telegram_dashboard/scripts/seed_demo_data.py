#!/usr/bin/env python3
"""Seed Sprint 1 demo messages for local testing."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.models.store import store  # noqa: E402

NOW = datetime.utcnow()


def seed() -> None:
    users = [
        {"id": 101, "username": "alice", "first_name": "Alice", "last_name": "Tan"},
        {"id": 102, "username": "bob_dev", "first_name": "Bob", "last_name": "Lim"},
        {"id": 103, "username": "carol", "first_name": "Carol", "last_name": "Wong"},
    ]
    for user in users:
        store.upsert_user(user)

    samples = [
        (101, "alice", "incoming", "Hi, my NRIC is S1234567A and I need help with billing", 1001, 1001, "private", None, 2),
        (101, "alice", "outgoing", "Sure, I can help with billing.", 1001, None, "private", None, 1),
        (102, "bob_dev", "incoming", "Can we schedule a demo for the new feature?", 1002, 2001, "private", None, 3),
        (103, "carol", "incoming", "Team standup moved to 3pm today", 2001, 3001, "group", "Project Alpha", 4),
        (102, "bob_dev", "incoming", "I'll join the standup at 2pm", 2001, 3002, "group", "Project Alpha", 3),
        (103, "carol", "incoming", "The standup is moved to 4pm instead", 2001, 3003, "group", "Project Alpha", 2),
        (101, "alice", "incoming", "Please send the updated pricing sheet", 1001, 2002, "private", None, 1),
        (103, "carol", "incoming", "Budget approval needed before Friday", 2001, 3004, "group", "Project Alpha", 1),
    ]

    for user_id, username, direction, text, chat_id, msg_id, chat_type, chat_title, hours_ago in samples:
        created = (NOW - timedelta(hours=hours_ago)).isoformat()
        with store._conn() as conn:
            conn.execute(
                """
                INSERT INTO messages (
                    user_id, username, direction, text, created_at,
                    chat_id, message_id, chat_type, chat_title
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    direction,
                    text,
                    created,
                    chat_id,
                    msg_id,
                    chat_type,
                    chat_title,
                ),
            )

    print(f"Seeded {len(samples)} messages for {len(users)} users.")


if __name__ == "__main__":
    seed()
