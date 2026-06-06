import json
import sqlite3
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta
from threading import Lock
from typing import Any

from backend.config import DATABASE_PATH


class DashboardStore:
    def __init__(self, db_path: str = str(DATABASE_PATH)):
        self.db_path = db_path
        self._lock = Lock()
        self._init_db()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    last_seen TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS messages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    username TEXT,
                    direction TEXT NOT NULL,
                    text TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS command_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    command TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS feedback (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    username TEXT,
                    rating INTEGER,
                    comment TEXT,
                    created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS quick_actions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    label TEXT NOT NULL,
                    command TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1
                );
                """
            )
            count = conn.execute("SELECT COUNT(*) FROM quick_actions").fetchone()[0]
            if count == 0:
                defaults = [
                    ("Help", "/help"),
                    ("Status", "/status"),
                    ("Analytics", "/analytics"),
                    ("Feedback", "/feedback"),
                ]
                conn.executemany(
                    "INSERT INTO quick_actions (label, command) VALUES (?, ?)",
                    defaults,
                )

    def upsert_user(self, user: dict[str, Any]) -> None:
        now = datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO users (user_id, username, first_name, last_name, last_seen)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET
                    username=excluded.username,
                    first_name=excluded.first_name,
                    last_name=excluded.last_name,
                    last_seen=excluded.last_seen
                """,
                (
                    user.get("id"),
                    user.get("username"),
                    user.get("first_name"),
                    user.get("last_name"),
                    now,
                ),
            )

    def add_message(
        self, user_id: int, username: str | None, direction: str, text: str
    ) -> dict[str, Any]:
        created_at = datetime.utcnow().isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO messages (user_id, username, direction, text, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, username, direction, text, created_at),
            )
            return {
                "id": cur.lastrowid,
                "user_id": user_id,
                "username": username,
                "direction": direction,
                "text": text,
                "created_at": created_at,
            }

    def add_event(self, event_type: str, payload: dict[str, Any]) -> dict[str, Any]:
        created_at = datetime.utcnow().isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                "INSERT INTO events (event_type, payload, created_at) VALUES (?, ?, ?)",
                (event_type, json.dumps(payload), created_at),
            )
            return {
                "id": cur.lastrowid,
                "event_type": event_type,
                "payload": payload,
                "created_at": created_at,
            }

    def track_command(self, command: str) -> None:
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO command_usage (command, created_at) VALUES (?, ?)",
                (command, datetime.utcnow().isoformat()),
            )

    def add_feedback(
        self, user_id: int | None, username: str | None, rating: int, comment: str
    ) -> dict[str, Any]:
        created_at = datetime.utcnow().isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO feedback (user_id, username, rating, comment, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (user_id, username, rating, comment, created_at),
            )
            return {
                "id": cur.lastrowid,
                "user_id": user_id,
                "username": username,
                "rating": rating,
                "comment": comment,
                "created_at": created_at,
            }

    def connected_users_count(self) -> int:
        cutoff = (datetime.utcnow() - timedelta(hours=24)).isoformat()
        with self._conn() as conn:
            row = conn.execute(
                "SELECT COUNT(*) AS c FROM users WHERE last_seen >= ?", (cutoff,)
            ).fetchone()
            return int(row["c"])

    def recent_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, username, direction, text, created_at
                FROM messages ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def recent_events(self, limit: int = 50) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, event_type, payload, created_at FROM events ORDER BY id DESC LIMIT ?",
                (limit,),
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item["payload"])
            result.append(item)
        return result

    def command_usage_over_time(self, days: int = 7) -> dict[str, list]:
        cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT date(created_at) AS day, command, COUNT(*) AS count
                FROM command_usage
                WHERE created_at >= ?
                GROUP BY day, command
                ORDER BY day
                """,
                (cutoff,),
            ).fetchall()

        by_day: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        commands: set[str] = set()
        for row in rows:
            by_day[row["day"]][row["command"]] = row["count"]
            commands.add(row["command"])

        labels = sorted(by_day.keys())
        datasets = []
        for command in sorted(commands):
            datasets.append(
                {
                    "label": command,
                    "data": [by_day[day].get(command, 0) for day in labels],
                }
            )
        return {"labels": labels, "datasets": datasets}

    def list_quick_actions(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, label, command, enabled FROM quick_actions ORDER BY id"
            ).fetchall()
        return [dict(r) for r in rows]

    def save_quick_actions(self, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        with self._conn() as conn:
            conn.execute("DELETE FROM quick_actions")
            for action in actions:
                conn.execute(
                    "INSERT INTO quick_actions (label, command, enabled) VALUES (?, ?, ?)",
                    (action["label"], action["command"], int(action.get("enabled", True))),
                )
        return self.list_quick_actions()

    def recent_feedback(self, limit: int = 20) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT id, user_id, username, rating, comment, created_at
                FROM feedback ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def metrics(self) -> dict[str, Any]:
        with self._conn() as conn:
            total_messages = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
            total_commands = conn.execute("SELECT COUNT(*) FROM command_usage").fetchone()[0]
        return {
            "connected_users": self.connected_users_count(),
            "total_messages": total_messages,
            "total_commands": total_commands,
        }


store = DashboardStore()
