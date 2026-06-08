#!/usr/bin/env python3
"""Seed demo messages and Sprint 3 settings for local testing."""

import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.models.store import store  # noqa: E402

NOW = datetime.utcnow()

TOPIC_MAP = {
    "billing": [1],
    "scheduling": [3, 4, 5, 6],
    "budget": [8],
    "pricing": [7],
}


def seed() -> None:
    users = [
        {"id": 101, "username": "alice", "first_name": "Alice", "last_name": "Tan"},
        {"id": 102, "username": "bob_dev", "first_name": "Bob", "last_name": "Lim"},
        {"id": 103, "username": "carol", "first_name": "Carol", "last_name": "Wong"},
    ]
    for user in users:
        store.upsert_user(user)

    store.set_reply_mode("manual")
    store.set_topic_mode("user_type")

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

    message_ids: list[int] = []
    for user_id, username, direction, text, chat_id, msg_id, chat_type, chat_title, hours_ago in samples:
        created = (NOW - timedelta(hours=hours_ago)).isoformat()
        with store._conn() as conn:
            cur = conn.execute(
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
            message_ids.append(int(cur.lastrowid))

    for topic, indexes in TOPIC_MAP.items():
        for idx in indexes:
            if idx <= len(message_ids):
                store.add_message_topics(message_ids[idx - 1], [topic], source="ai")

    store.set_chat_auto_reply(2001, True)
    store.sync_chat_settings_from_messages()

    relationships = {
        1001: (
            "Alice Tan (@alice) — private customer contacting about billing and pricing. "
            "She shares sensitive details and expects prompt, professional support."
        ),
        1002: (
            "Bob Lim (@bob_dev) — developer contact requesting product demos. "
            "Technical audience; prefers clear scheduling and follow-up."
        ),
        2001: (
            "Project Alpha group — internal team chat with Carol and Bob coordinating standups, "
            "timelines, and budget approvals. Fast-moving operational updates."
        ),
    }
    for chat_id, relationship in relationships.items():
        store.set_chat_relationship(chat_id, relationship, source="ai")

    print(f"Seeded {len(samples)} messages, topics, relationships, and workflow settings.")


if __name__ == "__main__":
    seed()
