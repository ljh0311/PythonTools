"""Tkinter Tasks tab builder for the Time Logger application."""
from __future__ import annotations

from datetime import date, timedelta
import sqlite3
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk
from typing import Any

from date_picker import add_date_picker_button
import task_ai
import task_store


def attach_tasks_tab(notebook: ttk.Notebook, conn: sqlite3.Connection, root: tk.Misc) -> "TasksTab":
    """Attach a fully functional Tasks tab and return its controller."""
    return TasksTab(notebook, conn, root)


class TasksTab:
    """Own the Tasks tab widgets and coordinate task store and AI modules."""

    def __init__(self, notebook: ttk.Notebook, conn: sqlite3.Connection, root: tk.Misc):
        self.conn, self.root = conn, root
        self.selected_id: int | None = None
        self.sort_var = tk.StringVar(value="priority")
        self.status_filter_var = tk.StringVar(value="open")
        self.title_var = tk.StringVar()
        self.status_var = tk.StringVar(value="todo")
        self.due_date_var = tk.StringVar()
        self.urgency_var = tk.IntVar(value=3)
        self.heaviness_var = tk.IntVar(value=3)
        self.summary_period_var = tk.StringVar(value="week")
        self.summary_date_var = tk.StringVar(value=date.today().strftime(task_store.DATE_FORMAT))

        self.frame = ttk.Frame(notebook)
        notebook.add(self.frame, text="Tasks")
        self._build()
        self.refresh()

    def refresh(self) -> None:
        """Reload visible tasks using the selected filter and stable sort."""
        for item in self.tree.get_children():
            self.tree.delete(item)
        status = self.status_filter_var.get()
        if status == "open":
            tasks = task_store.list_open_tasks(self.conn, sort_by=self.sort_var.get())
        elif status == "all":
            tasks = task_store.list_tasks(self.conn, sort_by=self.sort_var.get())
        else:
            tasks = task_store.list_tasks(self.conn, status=status, sort_by=self.sort_var.get())
        for task in tasks:
            self.tree.insert(
                "", "end", iid=str(task["id"]),
                values=(
                    task["id"], task["priority"], task["title"], task["status"], task["due_date"],
                    task["urgency"], task["heaviness"], task["created_date"], task["completed_date"],
                ),
            )

    def _build(self) -> None:
        outer = ttk.Frame(self.frame)
        outer.pack(fill="both", expand=True, padx=16, pady=12)
        self._build_editor(outer)
        self._build_list(outer)
        self._build_ai(outer)

    def _build_editor(self, parent: ttk.Frame) -> None:
        editor = ttk.LabelFrame(parent, text="Task details")
        editor.pack(fill="x", pady=(0, 10))
        ttk.Label(editor, text="Title:").grid(row=0, column=0, padx=(10, 4), pady=6, sticky="w")
        ttk.Entry(editor, textvariable=self.title_var, width=42).grid(row=0, column=1, columnspan=3, padx=4, pady=6, sticky="ew")
        ttk.Label(editor, text="Status:").grid(row=0, column=4, padx=(10, 4), pady=6, sticky="w")
        ttk.Combobox(editor, textvariable=self.status_var, values=task_store.VALID_STATUSES, state="readonly", width=10).grid(row=0, column=5, padx=4, pady=6)

        ttk.Label(editor, text="Due date:").grid(row=1, column=0, padx=(10, 4), pady=6, sticky="w")
        due = ttk.Entry(editor, textvariable=self.due_date_var, width=14)
        due.grid(row=1, column=1, padx=4, pady=6, sticky="w")
        add_date_picker_button(editor, self.due_date_var, self.root, title="Task due date").grid(row=1, column=2, padx=2, pady=6)
        ttk.Label(editor, text="Urgency:").grid(row=1, column=3, padx=(10, 4), pady=6, sticky="e")
        ttk.Spinbox(editor, from_=1, to=5, textvariable=self.urgency_var, width=5).grid(row=1, column=4, padx=4, pady=6, sticky="w")
        ttk.Label(editor, text="Heaviness:").grid(row=1, column=5, padx=(10, 4), pady=6, sticky="e")
        ttk.Spinbox(editor, from_=1, to=5, textvariable=self.heaviness_var, width=5).grid(row=1, column=6, padx=4, pady=6, sticky="w")

        ttk.Label(editor, text="Notes:").grid(row=2, column=0, padx=(10, 4), pady=6, sticky="nw")
        self.notes = scrolledtext.ScrolledText(editor, height=3, width=70, wrap=tk.WORD)
        self.notes.grid(row=2, column=1, columnspan=6, padx=4, pady=6, sticky="ew")
        buttons = ttk.Frame(editor)
        buttons.grid(row=3, column=0, columnspan=7, padx=8, pady=(2, 8), sticky="w")
        ttk.Button(buttons, text="Add task", command=self._save_new, style="Accent.TButton").pack(side=tk.LEFT, padx=3)
        ttk.Button(buttons, text="Update selected", command=self._update_selected).pack(side=tk.LEFT, padx=3)
        ttk.Button(buttons, text="Mark done", command=self._mark_done).pack(side=tk.LEFT, padx=3)
        ttk.Button(buttons, text="Delete selected", command=self._delete_selected).pack(side=tk.LEFT, padx=3)
        ttk.Button(buttons, text="Clear", command=self._clear_form).pack(side=tk.LEFT, padx=3)
        editor.columnconfigure(1, weight=1)

    def _build_list(self, parent: ttk.Frame) -> None:
        listing = ttk.LabelFrame(parent, text="Tasks")
        listing.pack(fill="both", expand=True, pady=(0, 10))
        controls = ttk.Frame(listing)
        controls.pack(fill="x", padx=8, pady=6)
        ttk.Label(controls, text="Show:").pack(side=tk.LEFT)
        ttk.Combobox(controls, textvariable=self.status_filter_var, values=("open", "all", "todo", "doing", "done"), state="readonly", width=10).pack(side=tk.LEFT, padx=4)
        ttk.Label(controls, text="Sort:").pack(side=tk.LEFT, padx=(12, 0))
        ttk.Combobox(controls, textvariable=self.sort_var, values=task_store.VALID_SORT_FIELDS, state="readonly", width=12).pack(side=tk.LEFT, padx=4)
        ttk.Button(controls, text="Refresh", command=self.refresh).pack(side=tk.LEFT, padx=4)

        columns = ("id", "priority", "title", "status", "due", "urgency", "heaviness", "created", "completed")
        self.tree = ttk.Treeview(listing, columns=columns, show="headings", height=8)
        labels = ("ID", "Priority", "Title", "Status", "Due", "Urgency", "Heaviness", "Created", "Completed")
        widths = (45, 65, 280, 75, 100, 70, 80, 100, 100)
        for column, label, width in zip(columns, labels, widths):
            self.tree.heading(column, text=label)
            self.tree.column(column, width=width, anchor="w")
        self.tree.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.tree.bind("<<TreeviewSelect>>", self._load_selected)

    def _build_ai(self, parent: ttk.Frame) -> None:
        ai = ttk.LabelFrame(parent, text="AI planning and completed-task summaries")
        ai.pack(fill="both", expand=True)
        buttons = ttk.Frame(ai)
        buttons.pack(fill="x", padx=8, pady=6)
        ttk.Button(buttons, text="Plan open tasks", command=self._plan).pack(side=tk.LEFT, padx=3)
        ttk.Label(buttons, text="Completed:").pack(side=tk.LEFT, padx=(14, 3))
        ttk.Combobox(buttons, textvariable=self.summary_period_var, values=("day", "week", "month"), state="readonly", width=8).pack(side=tk.LEFT, padx=3)
        summary_entry = ttk.Entry(buttons, textvariable=self.summary_date_var, width=12)
        summary_entry.pack(side=tk.LEFT, padx=3)
        add_date_picker_button(buttons, self.summary_date_var, self.root, title="Summary anchor date").pack(side=tk.LEFT, padx=2)
        ttk.Button(buttons, text="Summarize", command=self._summarize).pack(side=tk.LEFT, padx=3)
        self.ai_output = scrolledtext.ScrolledText(ai, height=8, wrap=tk.WORD, state="disabled")
        self.ai_output.pack(fill="both", expand=True, padx=8, pady=(0, 8))

    def _form_values(self) -> dict[str, Any]:
        return {
            "title": self.title_var.get(),
            "notes": self.notes.get("1.0", tk.END).strip(),
            "status": self.status_var.get(),
            "due_date": self.due_date_var.get(),
            "urgency": self.urgency_var.get(),
            "heaviness": self.heaviness_var.get(),
        }

    def _save_new(self) -> None:
        try:
            task_store.create_task(self.conn, **self._form_values())
        except ValueError as exc:
            messagebox.showwarning("Task details", str(exc), parent=self.root)
            return
        self._clear_form()
        self.refresh()

    def _update_selected(self) -> None:
        if self.selected_id is None:
            messagebox.showwarning("Task selection", "Select a task to update.", parent=self.root)
            return
        try:
            task_store.update_task(self.conn, self.selected_id, **self._form_values())
        except ValueError as exc:
            messagebox.showwarning("Task details", str(exc), parent=self.root)
            return
        self.refresh()

    def _mark_done(self) -> None:
        if self.selected_id is None:
            messagebox.showwarning("Task selection", "Select a task to complete.", parent=self.root)
            return
        task_store.update_task(self.conn, self.selected_id, status="done")
        self._clear_form()
        self.refresh()

    def _delete_selected(self) -> None:
        if self.selected_id is None:
            messagebox.showwarning("Task selection", "Select a task to delete.", parent=self.root)
            return
        if messagebox.askyesno("Delete task", "Delete the selected task?", parent=self.root):
            task_store.delete_task(self.conn, self.selected_id)
            self._clear_form()
            self.refresh()

    def _load_selected(self, _event: object) -> None:
        selected = self.tree.selection()
        if not selected:
            return
        task = task_store.get_task(self.conn, int(selected[0]))
        if not task:
            return
        self.selected_id = task["id"]
        self.title_var.set(task["title"])
        self.status_var.set(task["status"])
        self.due_date_var.set(task["due_date"])
        self.urgency_var.set(task["urgency"])
        self.heaviness_var.set(task["heaviness"])
        self.notes.delete("1.0", tk.END)
        self.notes.insert("1.0", task["notes"])

    def _clear_form(self) -> None:
        self.selected_id = None
        self.title_var.set("")
        self.status_var.set("todo")
        self.due_date_var.set("")
        self.urgency_var.set(3)
        self.heaviness_var.set(3)
        self.notes.delete("1.0", tk.END)
        self.tree.selection_remove(self.tree.selection())

    def _plan(self) -> None:
        body, footer = task_ai.plan_tasks({"tasks": task_store.list_open_tasks(self.conn)})
        self._set_ai_output(body, footer)

    def _summarize(self) -> None:
        try:
            anchor = datetime_from_display(self.summary_date_var.get())
        except ValueError as exc:
            messagebox.showwarning("Summary date", str(exc), parent=self.root)
            return
        start, end = _period_bounds(anchor, self.summary_period_var.get())
        tasks = task_store.list_completed_tasks_in_range(
            self.conn, start.strftime(task_store.DATE_FORMAT), end.strftime(task_store.DATE_FORMAT)
        )
        label = f"{self.summary_period_var.get().title()} ending {end.strftime(task_store.DATE_FORMAT)}"
        body, footer = task_ai.summarize_period({"tasks": tasks, "period_label": label})
        self._set_ai_output(body, footer)

    def _set_ai_output(self, body: str, footer: str) -> None:
        self.ai_output.configure(state="normal")
        self.ai_output.delete("1.0", tk.END)
        self.ai_output.insert("1.0", f"{body}\n\n{footer}")
        self.ai_output.configure(state="disabled")


def datetime_from_display(value: str) -> date:
    """Parse a required dd-mm-yyyy UI date."""
    try:
        return date.strptime(value, task_store.DATE_FORMAT)  # type: ignore[attr-defined]
    except AttributeError:
        from datetime import datetime
        try:
            return datetime.strptime(value, task_store.DATE_FORMAT).date()
        except ValueError as exc:
            raise ValueError("Summary date must use dd-mm-yyyy") from exc
    except ValueError as exc:
        raise ValueError("Summary date must use dd-mm-yyyy") from exc


def _period_bounds(anchor: date, period: str) -> tuple[date, date]:
    if period == "day":
        return anchor, anchor
    if period == "week":
        return anchor - timedelta(days=anchor.weekday()), anchor
    if period == "month":
        return anchor.replace(day=1), anchor
    raise ValueError("Summary period must be day, week, or month")
