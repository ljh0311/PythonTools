"""Task-priority scoring, optional Ollama planning, and Tkinter Tasks tab.

Priority formula: ``urgency * 5 + heaviness * 2 + due boost``.  Urgency (1--5)
therefore dominates ordering, heaviness breaks ties in favour of consequential
work, and due dates add 6 points when overdue/today or 3 points when due within
two days.  Done tasks are excluded from plans and use a score of zero.

Ollama uses the same ``TIMELOGGER_OLLAMA_URL`` and ``TIMELOGGER_OLLAMA_MODEL``
environment variables as ``report_ai_insights``.  A deterministic heuristic is
always available when requests or Ollama is unavailable.
"""
from __future__ import annotations

import os
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any, Iterable

import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

from date_picker import add_date_picker_button

try:
    import requests
except ImportError:  # pragma: no cover - optional dependency
    requests = None  # type: ignore


DATE_FORMAT = "%d-%m-%Y"
STATUSES = ("todo", "doing", "done")


def parse_date(value: str | None) -> date | None:
    """Parse the app's display date without raising for blank/invalid input."""
    if not value:
        return None
    try:
        return datetime.strptime(value.strip(), DATE_FORMAT).date()
    except ValueError:
        return None


def priority_score(urgency: int, heaviness: int, due_date: str | None, status: str) -> int:
    """Return the documented priority score for one task."""
    if status == "done":
        return 0
    due = parse_date(due_date)
    boost = 0
    if due and due <= date.today():
        boost = 6
    elif due and due <= date.today() + timedelta(days=2):
        boost = 3
    return urgency * 5 + heaviness * 2 + boost


class TaskStore:
    """Small SQLite repository isolated from the time-log data operations."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn
        self.ensure_schema()

    def ensure_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT DEFAULT '',
                urgency INTEGER NOT NULL CHECK(urgency BETWEEN 1 AND 5),
                heaviness INTEGER NOT NULL CHECK(heaviness BETWEEN 1 AND 5),
                status TEXT NOT NULL DEFAULT 'todo'
                    CHECK(status IN ('todo', 'doing', 'done')),
                due_date TEXT,
                created_at TEXT NOT NULL,
                completed_at TEXT
            )
            """
        )
        columns = {
            row[1] for row in self.conn.execute("PRAGMA table_info(tasks)").fetchall()
        }
        # A short-lived pre-release used ``effort`` for this field.  Preserve
        # those rows while normalising the public schema to ``heaviness``.
        if "heaviness" not in columns:
            self.conn.execute("ALTER TABLE tasks ADD COLUMN heaviness INTEGER NOT NULL DEFAULT 3")
            if "effort" in columns:
                self.conn.execute("UPDATE tasks SET heaviness = effort")
        if "description" not in columns:
            self.conn.execute("ALTER TABLE tasks ADD COLUMN description TEXT DEFAULT ''")
            if "notes" in columns:
                self.conn.execute("UPDATE tasks SET description = notes")
        if "created_at" not in columns:
            self.conn.execute("ALTER TABLE tasks ADD COLUMN created_at TEXT DEFAULT ''")
            if "created_date" in columns:
                self.conn.execute("UPDATE tasks SET created_at = created_date")
        if "completed_at" not in columns:
            self.conn.execute("ALTER TABLE tasks ADD COLUMN completed_at TEXT")
            if "completed_date" in columns:
                self.conn.execute(
                    "UPDATE tasks SET completed_at = CASE WHEN completed_date != '' "
                    "THEN completed_date || ' 00:00' END"
                )
        self.conn.commit()

    def all(self) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, title, description, urgency, heaviness, status, due_date, "
            "created_at, completed_at FROM tasks"
        ).fetchall()
        tasks = [self._row_to_task(row) for row in rows]
        return sorted(
            tasks,
            key=lambda task: (
                task["status"] == "done",
                -task["score"],
                task["due_date"] or "99-99-9999",
                task["id"],
            ),
        )

    def save(self, task_id: int | None, values: dict[str, Any]) -> int:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        completed_at = now if values["status"] == "done" else None
        if task_id:
            self.conn.execute(
                """UPDATE tasks SET title=?, description=?, urgency=?, heaviness=?,
                   status=?, due_date=?, completed_at=? WHERE id=?""",
                (
                    values["title"],
                    values["description"],
                    values["urgency"],
                    values["heaviness"],
                    values["status"],
                    values["due_date"],
                    completed_at,
                    task_id,
                ),
            )
            self.conn.commit()
            return task_id
        cursor = self.conn.execute(
            """INSERT INTO tasks
               (title, description, urgency, heaviness, status, due_date, created_at, completed_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                values["title"],
                values["description"],
                values["urgency"],
                values["heaviness"],
                values["status"],
                values["due_date"],
                now,
                completed_at,
            ),
        )
        self.conn.commit()
        return int(cursor.lastrowid)

    def delete(self, task_id: int) -> None:
        self.conn.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        self.conn.commit()

    def mark_done(self, task_id: int) -> None:
        self.conn.execute(
            "UPDATE tasks SET status='done', completed_at=? WHERE id=?",
            (datetime.now().strftime("%Y-%m-%d %H:%M"), task_id),
        )
        self.conn.commit()

    def completed_between(self, start: date, end: date) -> list[dict[str, Any]]:
        tasks = self.all()
        return [
            task for task in tasks
            if task["completed_at"]
            and (completed := _completion_date(task["completed_at"]))
            and start <= completed <= end
        ]

    @staticmethod
    def _row_to_task(row: tuple[Any, ...]) -> dict[str, Any]:
        task = dict(
            zip(
                ("id", "title", "description", "urgency", "heaviness", "status",
                 "due_date", "created_at", "completed_at"),
                row,
            )
        )
        task["score"] = priority_score(
            int(task["urgency"]), int(task["heaviness"]), task["due_date"], task["status"]
        )
        return task


def _completion_date(value: str) -> date | None:
    """Read current timestamps and legacy dd-mm-yyyy completion values."""
    for fmt in ("%Y-%m-%d %H:%M", "%d-%m-%Y %H:%M", DATE_FORMAT):
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def heuristic_plan(tasks: Iterable[dict[str, Any]], capacity: int, limit: int = 5) -> list[dict[str, Any]]:
    """Pick the highest scoring unfinished tasks that fit the heaviness budget."""
    chosen: list[dict[str, Any]] = []
    used = 0
    for task in tasks:
        if task["status"] == "done" or len(chosen) >= limit:
            continue
        cost = int(task["heaviness"])
        if used + cost <= capacity:
            chosen.append(task)
            used += cost
    return chosen


def plan_my_day(tasks: list[dict[str, Any]], capacity: int) -> tuple[list[dict[str, Any]], str]:
    """Return a capacity-safe plan and an optional Ollama narrative."""
    selected = heuristic_plan(tasks, capacity)
    if not selected:
        return [], "No unfinished tasks fit this capacity. Add a task or raise the capacity."

    fallback = (
        f"Heuristic plan: {len(selected)} task(s), {sum(t['heaviness'] for t in selected)}/{capacity} "
        "heaviness points. Work from the highest priority down; stop when the capacity budget is spent."
    )
    if not requests:
        return selected, fallback + "\n\nSource: built-in priority rules (requests/Ollama unavailable)."

    task_lines = "\n".join(
        f"- {task['title']} | urgency {task['urgency']}, heaviness {task['heaviness']}, "
        f"due {task['due_date'] or 'none'}, score {task['score']}"
        for task in selected
    )
    prompt = (
        "You are a concise productivity coach. Explain this capacity-limited task plan in "
        "3-5 short bullets. Do not add tasks or exceed the stated capacity.\n"
        f"Capacity: {capacity} heaviness points\nSelected tasks:\n{task_lines}"
    )
    try:
        response = requests.post(
            os.environ.get("TIMELOGGER_OLLAMA_URL", "http://localhost:11434/api/generate"),
            json={"model": os.environ.get("TIMELOGGER_OLLAMA_MODEL", "llama3"), "prompt": prompt, "stream": False},
            timeout=45,
        )
        response.raise_for_status()
        narrative = response.json().get("response", "").strip()
        if narrative:
            return selected, narrative + "\n\nSource: local Ollama."
    except Exception:
        pass
    return selected, fallback + "\n\nSource: built-in rules (Ollama unavailable or returned no text)."


class TaskPriorityTab:
    """Tkinter task UI: CRUD form, priority list, visual matrix, planning and summaries."""

    def __init__(self, app: Any) -> None:
        self.app = app
        self.store = TaskStore(app.conn)
        self.selected_id: int | None = None
        self._build()
        self.refresh()

    def _build(self) -> None:
        self.frame = ttk.Frame(self.app.notebook)
        self.app.notebook.add(self.frame, text="Tasks")
        self.frame.columnconfigure(1, weight=1)
        self.frame.rowconfigure(0, weight=1)

        self._build_editor()
        self._build_dashboard()

    def _build_editor(self) -> None:
        editor = ttk.LabelFrame(self.frame, text="Task details")
        editor.grid(row=0, column=0, sticky="nsw", padx=(12, 6), pady=12)
        self.title_var = tk.StringVar()
        self.urgency_var = tk.IntVar(value=3)
        self.heaviness_var = tk.IntVar(value=3)
        self.status_var = tk.StringVar(value="todo")
        self.due_var = tk.StringVar()

        ttk.Label(editor, text="Title").grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        ttk.Entry(editor, textvariable=self.title_var, width=29).grid(row=1, column=0, columnspan=2, padx=8, sticky="ew")
        ttk.Label(editor, text="Description").grid(row=2, column=0, sticky="w", padx=8, pady=(8, 2))
        self.description = scrolledtext.ScrolledText(editor, width=29, height=5, wrap=tk.WORD)
        self.description.grid(row=3, column=0, columnspan=2, padx=8, sticky="ew")

        ttk.Label(editor, text="Urgency (1 low — 5 high)").grid(row=4, column=0, sticky="w", padx=8, pady=(8, 2))
        ttk.Spinbox(editor, from_=1, to=5, textvariable=self.urgency_var, width=8).grid(row=4, column=1, sticky="e", padx=8, pady=(8, 2))
        ttk.Label(editor, text="Heaviness (1 light — 5 heavy)").grid(row=5, column=0, sticky="w", padx=8, pady=2)
        ttk.Spinbox(editor, from_=1, to=5, textvariable=self.heaviness_var, width=8).grid(row=5, column=1, sticky="e", padx=8, pady=2)
        ttk.Label(editor, text="Status").grid(row=6, column=0, sticky="w", padx=8, pady=2)
        ttk.Combobox(editor, textvariable=self.status_var, values=STATUSES, state="readonly", width=9).grid(row=6, column=1, sticky="e", padx=8, pady=2)
        ttk.Label(editor, text="Due date").grid(row=7, column=0, sticky="w", padx=8, pady=2)
        due = ttk.Frame(editor)
        due.grid(row=7, column=1, sticky="e", padx=8, pady=2)
        ttk.Entry(due, textvariable=self.due_var, width=11).pack(side=tk.LEFT)
        add_date_picker_button(due, self.due_var, self.app.root, title="Task due date").pack(side=tk.LEFT, padx=(2, 0))
        ttk.Label(editor, text="dd-mm-yyyy; optional", foreground="#1565C0").grid(row=8, column=0, columnspan=2, sticky="w", padx=8)

        buttons = ttk.Frame(editor)
        buttons.grid(row=9, column=0, columnspan=2, pady=10)
        ttk.Button(buttons, text="Save task", command=self.save).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons, text="New / clear", command=self.clear).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons, text="Mark done", command=self.mark_done).pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons, text="Delete", command=self.delete).pack(side=tk.LEFT, padx=2)

    def _build_dashboard(self) -> None:
        dashboard = ttk.Frame(self.frame)
        dashboard.grid(row=0, column=1, sticky="nsew", padx=(6, 12), pady=12)
        dashboard.columnconfigure(0, weight=1)
        dashboard.rowconfigure(1, weight=1)

        tools = ttk.Frame(dashboard)
        tools.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Label(tools, text="Today capacity:").pack(side=tk.LEFT)
        self.capacity_var = tk.IntVar(value=10)
        ttk.Spinbox(tools, from_=1, to=30, textvariable=self.capacity_var, width=5).pack(side=tk.LEFT, padx=4)
        ttk.Button(tools, text="AI: Plan my day", command=self.show_plan).pack(side=tk.LEFT, padx=4)
        ttk.Button(tools, text="Refresh", command=self.refresh).pack(side=tk.LEFT, padx=4)

        view = ttk.PanedWindow(dashboard, orient=tk.VERTICAL)
        view.grid(row=1, column=0, sticky="nsew")
        matrix_box = ttk.LabelFrame(view, text="Priority matrix — urgency → / heaviness ↓")
        list_box = ttk.LabelFrame(view, text="Sorted priority list")
        view.add(matrix_box, weight=2)
        view.add(list_box, weight=3)
        self._build_matrix(matrix_box)
        self._build_list(list_box)

        bottom = ttk.Frame(dashboard)
        bottom.grid(row=2, column=0, sticky="ew", pady=(8, 0))
        ttk.Label(bottom, text="Completed summary:").pack(side=tk.LEFT)
        self.summary_period = tk.StringVar(value="Day")
        ttk.Combobox(bottom, textvariable=self.summary_period, values=("Day", "Week", "Month"), width=7, state="readonly").pack(side=tk.LEFT, padx=4)
        ttk.Button(bottom, text="Show summary", command=self.show_summary).pack(side=tk.LEFT)

    def _build_matrix(self, parent: ttk.LabelFrame) -> None:
        parent.columnconfigure(0, weight=1)
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(1, weight=1)
        parent.rowconfigure(2, weight=1)
        ttk.Label(parent, text="LOW URGENCY (1–2)", anchor="center").grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        ttk.Label(parent, text="HIGH URGENCY (3–5)", anchor="center").grid(row=0, column=1, sticky="ew", padx=4, pady=(4, 0))
        ttk.Label(parent, text="HEAVY (3–5)").grid(row=1, column=2, padx=4)
        ttk.Label(parent, text="LIGHT (1–2)").grid(row=2, column=2, padx=4)
        self.matrix_cells: dict[str, tk.Listbox] = {}
        cells = (
            ("low_heavy", 1, 0, "#FFF3CD", "Schedule"),
            ("high_heavy", 1, 1, "#F8D7DA", "Do first"),
            ("low_light", 2, 0, "#D1ECF1", "Fill-in"),
            ("high_light", 2, 1, "#D4EDDA", "Quick wins"),
        )
        for key, row, column, color, title in cells:
            cell = tk.Frame(parent, bg=color, highlightbackground="#B0B0B0", highlightthickness=1)
            cell.grid(row=row, column=column, sticky="nsew", padx=4, pady=4)
            tk.Label(cell, text=title, bg=color, font=("Arial", 9, "bold")).pack(anchor="w", padx=5, pady=(3, 0))
            listbox = tk.Listbox(cell, height=5, bg=color, borderwidth=0, activestyle="none")
            listbox.pack(fill="both", expand=True, padx=4, pady=3)
            listbox.bind("<<ListboxSelect>>", lambda event, box=listbox: self.select_matrix_task(box))
            self.matrix_cells[key] = listbox

    def _build_list(self, parent: ttk.LabelFrame) -> None:
        columns = ("title", "status", "urgency", "heavy", "due", "score")
        self.tree = ttk.Treeview(parent, columns=columns, show="headings", height=8)
        headings = ("Task", "Status", "Urgency", "Heavy", "Due", "Score")
        widths = (260, 70, 65, 60, 95, 55)
        for col, heading, width in zip(columns, headings, widths):
            self.tree.heading(col, text=heading)
            self.tree.column(col, width=width, anchor="w" if col == "title" else "center")
        self.tree.pack(side=tk.LEFT, fill="both", expand=True, padx=(4, 0), pady=4)
        scrollbar = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.pack(side=tk.RIGHT, fill="y", padx=(0, 4), pady=4)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.bind("<<TreeviewSelect>>", self.select_tree_task)

    def refresh(self) -> None:
        self.tasks = self.store.all()
        for item in self.tree.get_children():
            self.tree.delete(item)
        for task in self.tasks:
            self.tree.insert(
                "", tk.END, iid=str(task["id"]),
                values=(task["title"], task["status"], task["urgency"], task["heaviness"],
                        task["due_date"] or "—", task["score"]),
            )
        for listbox in self.matrix_cells.values():
            listbox.delete(0, tk.END)
            listbox.task_ids = []  # type: ignore[attr-defined]
        for task in self.tasks:
            if task["status"] == "done":
                continue
            key = ("high" if task["urgency"] >= 3 else "low") + "_" + ("heavy" if task["heaviness"] >= 3 else "light")
            listbox = self.matrix_cells[key]
            listbox.insert(tk.END, f"[{task['score']}] {task['title']}")
            listbox.task_ids.append(task["id"])  # type: ignore[attr-defined]

    def _selected_task(self) -> dict[str, Any] | None:
        return next((task for task in self.tasks if task["id"] == self.selected_id), None)

    def _load_task(self, task_id: int) -> None:
        self.selected_id = task_id
        task = self._selected_task()
        if not task:
            return
        self.title_var.set(task["title"])
        self.description.delete("1.0", tk.END)
        self.description.insert("1.0", task["description"])
        self.urgency_var.set(task["urgency"])
        self.heaviness_var.set(task["heaviness"])
        self.status_var.set(task["status"])
        self.due_var.set(task["due_date"] or "")

    def select_tree_task(self, _event: Any) -> None:
        selection = self.tree.selection()
        if selection:
            self._load_task(int(selection[0]))

    def select_matrix_task(self, listbox: tk.Listbox) -> None:
        selection = listbox.curselection()
        if selection:
            self._load_task(listbox.task_ids[selection[0]])  # type: ignore[attr-defined]

    def save(self) -> None:
        title = self.title_var.get().strip()
        due = self.due_var.get().strip()
        if not title:
            messagebox.showwarning("Title required", "Enter a task title.")
            return
        if due and not parse_date(due):
            messagebox.showwarning("Invalid due date", "Use dd-mm-yyyy for the due date.")
            return
        self.store.save(
            self.selected_id,
            {
                "title": title,
                "description": self.description.get("1.0", tk.END).strip(),
                "urgency": self.urgency_var.get(),
                "heaviness": self.heaviness_var.get(),
                "status": self.status_var.get(),
                "due_date": due or None,
            },
        )
        self.clear()
        self.refresh()

    def clear(self) -> None:
        self.selected_id = None
        self.title_var.set("")
        self.description.delete("1.0", tk.END)
        self.urgency_var.set(3)
        self.heaviness_var.set(3)
        self.status_var.set("todo")
        self.due_var.set("")
        self.tree.selection_remove(self.tree.selection())

    def mark_done(self) -> None:
        if not self.selected_id:
            messagebox.showwarning("Select a task", "Select a task from the list or matrix first.")
            return
        self.store.mark_done(self.selected_id)
        self.clear()
        self.refresh()

    def delete(self) -> None:
        if not self.selected_id:
            messagebox.showwarning("Select a task", "Select a task before deleting it.")
            return
        if messagebox.askyesno("Delete task", "Delete the selected task?"):
            self.store.delete(self.selected_id)
            self.clear()
            self.refresh()

    def show_plan(self) -> None:
        selected, narrative = plan_my_day(self.tasks, self.capacity_var.get())
        lines = [f"{index}. {task['title']} — score {task['score']}, {task['heaviness']} points"
                 for index, task in enumerate(selected, start=1)]
        messagebox.showinfo("Plan my day", "\n".join(lines) + "\n\n" + narrative)

    def show_summary(self) -> None:
        today = date.today()
        period = self.summary_period.get()
        if period == "Day":
            start = end = today
        elif period == "Week":
            start, end = today - timedelta(days=today.weekday()), today
        else:
            start, end = today.replace(day=1), today
        completed = self.store.completed_between(start, end)
        effort = sum(int(task["heaviness"]) for task in completed)
        narrative = (
            f"{period} summary ({start.strftime(DATE_FORMAT)} – {end.strftime(DATE_FORMAT)}): "
            f"{len(completed)} completed task(s), clearing {effort} heaviness points."
        )
        titles = "\n".join(f"• {task['title']} ({task['heaviness']} points)" for task in completed) or "• No completed tasks in this period."
        messagebox.showinfo(f"{period} summary", narrative + "\n\n" + titles)
