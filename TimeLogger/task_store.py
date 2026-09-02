"""SQLite persistence and stable task ordering for Time Logger tasks."""
from __future__ import annotations

from datetime import date, datetime
import sqlite3
from typing import Any, Iterable, Mapping

DATE_FORMAT = "%d-%m-%Y"
VALID_STATUSES = ("todo", "doing", "done")
VALID_SORT_FIELDS = ("priority", "urgency", "heaviness", "due_date", "created_date", "title")
TASK_COLUMNS = "id, title, notes, status, due_date, urgency, heaviness, created_date, completed_date"


def ensure_tasks_table(conn: sqlite3.Connection) -> None:
    """Create the task table and migrate the earlier effort column when present."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'todo',
            due_date TEXT NOT NULL DEFAULT '',
            urgency INTEGER NOT NULL DEFAULT 3,
            heaviness INTEGER NOT NULL DEFAULT 3,
            created_date TEXT NOT NULL,
            completed_date TEXT NOT NULL DEFAULT ''
        )
        """
    )
    columns = {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    if "heaviness" not in columns:
        conn.execute("ALTER TABLE tasks ADD COLUMN heaviness INTEGER NOT NULL DEFAULT 3")
        if "effort" in columns:
            conn.execute("UPDATE tasks SET heaviness = effort WHERE effort BETWEEN 1 AND 5")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_completed_date ON tasks(completed_date)")
    conn.commit()


def priority_score(urgency: int, heaviness: int) -> int:
    """Return the explicit priority score (urgency × 2 plus heaviness)."""
    return _level(urgency, "urgency") * 2 + _level(heaviness, "heaviness")


def create_task(
    conn: sqlite3.Connection,
    title: str,
    *,
    notes: str = "",
    status: str = "todo",
    due_date: str = "",
    urgency: int = 3,
    heaviness: int = 3,
    created_date: str | None = None,
) -> dict[str, Any]:
    """Create a task and return its normalized record."""
    title = _required_title(title)
    status = _status(status)
    due_date = _date_or_blank(due_date, "due date")
    created_date = _date_or_today(created_date)
    completed_date = created_date if status == "done" else ""
    cursor = conn.execute(
        """INSERT INTO tasks
           (title, notes, status, due_date, urgency, heaviness, created_date, completed_date)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, str(notes or "").strip(), status, due_date, _level(urgency, "urgency"),
         _level(heaviness, "heaviness"), created_date, completed_date),
    )
    conn.commit()
    return get_task(conn, cursor.lastrowid)  # type: ignore[arg-type]


def get_task(conn: sqlite3.Connection, task_id: int) -> dict[str, Any] | None:
    """Return one task by id, or None when it does not exist."""
    row = conn.execute(f"SELECT {TASK_COLUMNS} FROM tasks WHERE id = ?", (int(task_id),)).fetchone()
    return _row_to_task(row) if row else None


def update_task(conn: sqlite3.Connection, task_id: int, **changes: Any) -> dict[str, Any]:
    """Update permitted task fields and return the resulting record."""
    existing = get_task(conn, task_id)
    if not existing:
        raise ValueError("Task not found")
    allowed = {"title", "notes", "status", "due_date", "urgency", "heaviness", "created_date", "completed_date"}
    unknown = set(changes) - allowed
    if unknown:
        raise ValueError(f"Unsupported task fields: {', '.join(sorted(unknown))}")
    merged = {**existing, **changes}
    merged["title"] = _required_title(merged["title"])
    merged["status"] = _status(merged["status"])
    merged["due_date"] = _date_or_blank(merged["due_date"], "due date")
    merged["created_date"] = _date_or_today(merged["created_date"])
    merged["urgency"] = _level(merged["urgency"], "urgency")
    merged["heaviness"] = _level(merged["heaviness"], "heaviness")
    if merged["status"] == "done":
        merged["completed_date"] = _date_or_today(merged.get("completed_date"))
    else:
        merged["completed_date"] = ""
    fields = tuple(allowed)
    conn.execute(
        f"UPDATE tasks SET {', '.join(f'{field} = ?' for field in fields)} WHERE id = ?",
        tuple(merged[field] for field in fields) + (int(task_id),),
    )
    conn.commit()
    return get_task(conn, task_id)  # type: ignore[return-value]


def delete_task(conn: sqlite3.Connection, task_id: int) -> bool:
    """Delete a task, returning whether a row was removed."""
    cursor = conn.execute("DELETE FROM tasks WHERE id = ?", (int(task_id),))
    conn.commit()
    return cursor.rowcount > 0


def list_tasks(
    conn: sqlite3.Connection,
    *,
    status: str | None = None,
    sort_by: str = "priority",
    descending: bool = True,
) -> list[dict[str, Any]]:
    """Return all tasks, optionally restricted to one status and stably sorted."""
    if status is not None:
        status = _status(status)
        rows = conn.execute(f"SELECT {TASK_COLUMNS} FROM tasks WHERE status = ?", (status,)).fetchall()
    else:
        rows = conn.execute(f"SELECT {TASK_COLUMNS} FROM tasks").fetchall()
    return sort_tasks((_row_to_task(row) for row in rows), sort_by=sort_by, descending=descending)


def list_open_tasks(conn: sqlite3.Connection, *, sort_by: str = "priority") -> list[dict[str, Any]]:
    """Return todo and doing tasks in stable priority order."""
    rows = conn.execute(f"SELECT {TASK_COLUMNS} FROM tasks WHERE status != 'done'").fetchall()
    return sort_tasks((_row_to_task(row) for row in rows), sort_by=sort_by)


def list_completed_tasks_in_range(
    conn: sqlite3.Connection, from_date: str, to_date: str
) -> list[dict[str, Any]]:
    """Return tasks completed inclusively within dd-mm-yyyy date bounds."""
    from_text = _date_or_blank(from_date, "from date")
    to_text = _date_or_blank(to_date, "to date")
    if not from_text or not to_text:
        raise ValueError("Both summary dates are required")
    low, high = sorted((_date_key(from_text), _date_key(to_text)))
    rows = conn.execute(f"SELECT {TASK_COLUMNS} FROM tasks WHERE status = 'done'").fetchall()
    tasks = [_row_to_task(row) for row in rows]
    return sort_tasks(
        (task for task in tasks if low <= _date_key(task["completed_date"]) <= high),
        sort_by="completed_date",
        descending=False,
    )


def sort_tasks(
    tasks: Iterable[Mapping[str, Any]], *, sort_by: str = "priority", descending: bool = True
) -> list[dict[str, Any]]:
    """Stable-sort task mappings by a supported field, with id as deterministic tie-breaker."""
    if sort_by not in VALID_SORT_FIELDS:
        raise ValueError(f"Unsupported sort field: {sort_by}")
    normalized = [dict(task) for task in tasks]
    for task in normalized:
        task["priority"] = priority_score(task["urgency"], task["heaviness"])
    key = _sort_key(sort_by)
    return sorted(normalized, key=lambda task: (key(task), int(task.get("id") or 0)), reverse=descending)


def _sort_key(sort_by: str):
    if sort_by == "priority":
        return lambda task: int(task["priority"])
    if sort_by in ("urgency", "heaviness"):
        return lambda task: int(task[sort_by])
    if sort_by in ("due_date", "created_date"):
        return lambda task: _date_key(str(task.get(sort_by) or ""))
    return lambda task: str(task.get("title") or "").casefold()


def _row_to_task(row: sqlite3.Row | tuple[Any, ...]) -> dict[str, Any]:
    columns = ("id", "title", "notes", "status", "due_date", "urgency", "heaviness", "created_date", "completed_date")
    task = dict(zip(columns, row))
    task["priority"] = priority_score(task["urgency"], task["heaviness"])
    return task


def _required_title(value: Any) -> str:
    title = str(value or "").strip()
    if not title:
        raise ValueError("Task title is required")
    return title


def _status(value: Any) -> str:
    status = str(value or "").strip().lower()
    if status not in VALID_STATUSES:
        raise ValueError("Status must be todo, doing, or done")
    return status


def _level(value: Any, label: str) -> int:
    try:
        level = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label.title()} must be between 1 and 5") from exc
    if not 1 <= level <= 5:
        raise ValueError(f"{label.title()} must be between 1 and 5")
    return level


def _date_or_today(value: Any) -> str:
    return _date_or_blank(value, "date") or date.today().strftime(DATE_FORMAT)


def _date_or_blank(value: Any, label: str) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    try:
        return datetime.strptime(text, DATE_FORMAT).strftime(DATE_FORMAT)
    except ValueError as exc:
        raise ValueError(f"{label.title()} must use dd-mm-yyyy") from exc


def _date_key(value: str) -> str:
    return datetime.strptime(value, DATE_FORMAT).strftime("%Y%m%d") if value else "99999999"
