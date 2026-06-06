import json
import sqlite3
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timedelta
from threading import Lock
from typing import Any

from backend.config import DATABASE_PATH

MESSAGE_COLUMNS = (
    "id",
    "user_id",
    "username",
    "direction",
    "text",
    "created_at",
    "chat_id",
    "message_id",
    "chat_type",
    "chat_title",
    "reply_to_message_id",
)


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

    def _migrate_messages(self, conn: sqlite3.Connection) -> None:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(messages)")}
        additions = {
            "chat_id": "INTEGER",
            "message_id": "INTEGER",
            "chat_type": "TEXT",
            "chat_title": "TEXT",
            "reply_to_message_id": "INTEGER",
        }
        for column, col_type in additions.items():
            if column not in existing:
                conn.execute(f"ALTER TABLE messages ADD COLUMN {column} {col_type}")

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_chat_type ON messages(chat_type)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)"
        )

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
            self._migrate_messages(conn)
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
        self,
        user_id: int,
        username: str | None,
        direction: str,
        text: str,
        *,
        chat_id: int | None = None,
        message_id: int | None = None,
        chat_type: str | None = None,
        chat_title: str | None = None,
        reply_to_message_id: int | None = None,
    ) -> dict[str, Any]:
        created_at = datetime.utcnow().isoformat()
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO messages (
                    user_id, username, direction, text, created_at,
                    chat_id, message_id, chat_type, chat_title, reply_to_message_id
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user_id,
                    username,
                    direction,
                    text,
                    created_at,
                    chat_id,
                    message_id,
                    chat_type,
                    chat_title,
                    reply_to_message_id,
                ),
            )
            return self._row_to_message(
                conn.execute(
                    "SELECT * FROM messages WHERE id = ?", (cur.lastrowid,)
                ).fetchone()
            )

    def _row_to_message(self, row: sqlite3.Row) -> dict[str, Any]:
        return dict(row)

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

    def list_users(self) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                """
                SELECT
                    u.user_id,
                    u.username,
                    u.first_name,
                    u.last_name,
                    u.last_seen,
                    COUNT(m.id) AS message_count
                FROM users u
                LEFT JOIN messages m ON m.user_id = u.user_id
                GROUP BY u.user_id
                ORDER BY u.last_seen DESC
                """
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            parts = [item.get("first_name") or "", item.get("last_name") or ""]
            display = " ".join(p for p in parts if p).strip()
            if not display:
                display = item.get("username") or f"User {item['user_id']}"
            item["display_name"] = display
            result.append(item)
        return result

    def query_messages(
        self,
        *,
        user_ids: list[int] | None = None,
        chat_type: str | None = None,
        direction: str | None = None,
        q: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict[str, Any]:
        clauses: list[str] = []
        params: list[Any] = []

        if user_ids:
            placeholders = ",".join("?" for _ in user_ids)
            clauses.append(f"user_id IN ({placeholders})")
            params.extend(user_ids)

        if chat_type:
            clauses.append("chat_type = ?")
            params.append(chat_type)

        if direction:
            clauses.append("direction = ?")
            params.append(direction)

        if q:
            clauses.append("LOWER(text) LIKE ?")
            params.append(f"%{q.lower()}%")

        if date_from:
            clauses.append("created_at >= ?")
            params.append(date_from)

        if date_to:
            clauses.append("created_at <= ?")
            params.append(date_to)

        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""

        with self._conn() as conn:
            total = conn.execute(
                f"SELECT COUNT(*) FROM messages {where}", params
            ).fetchone()[0]
            rows = conn.execute(
                f"""
                SELECT * FROM messages {where}
                ORDER BY id DESC
                LIMIT ? OFFSET ?
                """,
                [*params, limit, offset],
            ).fetchall()

        return {
            "items": [self._row_to_message(row) for row in rows],
            "total": total,
            "limit": limit,
            "offset": offset,
        }

    def get_messages_by_chat_id(self, chat_id: int) -> list[dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE chat_id = ? ORDER BY created_at ASC",
                (chat_id,),
            ).fetchall()
        return [self._row_to_message(row) for row in rows]

    def get_messages_by_ids(self, message_ids: list[int]) -> list[dict[str, Any]]:
        if not message_ids:
            return []
        placeholders = ",".join("?" for _ in message_ids)
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM messages WHERE id IN ({placeholders}) ORDER BY created_at ASC",
                message_ids,
            ).fetchall()
        return [self._row_to_message(row) for row in rows]

    def query_threads(
        self,
        *,
        user_ids: list[int] | None = None,
        chat_type: str | None = None,
        direction: str | None = None,
        q: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        thread_limit: int = 20,
        thread_offset: int = 0,
        message_cap: int = 500,
    ) -> dict[str, Any]:
        batch = self.query_messages(
            user_ids=user_ids,
            chat_type=chat_type,
            direction=direction,
            q=q,
            date_from=date_from,
            date_to=date_to,
            limit=message_cap,
            offset=0,
        )
        grouped: dict[str, dict[str, Any]] = {}
        for msg in batch["items"]:
            key = str(msg.get("chat_id") if msg.get("chat_id") is not None else f"msg-{msg['id']}")
            if key not in grouped:
                grouped[key] = {
                    "chat_id": msg.get("chat_id"),
                    "chat_type": msg.get("chat_type"),
                    "chat_title": msg.get("chat_title"),
                    "messages": [],
                    "participants": set(),
                    "latest_at": msg.get("created_at"),
                }
            thread = grouped[key]
            thread["messages"].append(msg)
            if msg.get("username"):
                thread["participants"].add(f"@{msg['username']}")
            elif msg.get("user_id"):
                thread["participants"].add(f"User {msg['user_id']}")
            if (msg.get("created_at") or "") > (thread.get("latest_at") or ""):
                thread["latest_at"] = msg.get("created_at")

        threads = []
        for thread in grouped.values():
            thread["messages"].sort(key=lambda m: m.get("created_at", ""))
            thread["participants"] = sorted(thread["participants"])
            thread["message_count"] = len(thread["messages"])
            threads.append(thread)

        threads.sort(key=lambda t: t.get("latest_at") or "", reverse=True)
        total_threads = len(threads)
        page = threads[thread_offset : thread_offset + thread_limit]

        return {
            "threads": page,
            "total": total_threads,
            "total_messages": batch["total"],
            "limit": thread_limit,
            "offset": thread_offset,
        }

    def recent_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.query_messages(limit=limit, offset=0)["items"]

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
