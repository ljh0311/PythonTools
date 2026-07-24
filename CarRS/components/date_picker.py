"""Calendar date picker dialog for Tkinter (tkcalendar or built-in grid)."""

from __future__ import annotations

import calendar
from datetime import date, datetime
from typing import Optional

import tkinter as tk
from tkinter import messagebox, ttk


def _parse_initial(value: str) -> date:
    text = (value or "").strip()
    if not text:
        return date.today()
    try:
        return datetime.strptime(text, "%Y-%m-%d").date()
    except ValueError:
        try:
            return datetime.fromisoformat(text).date()
        except ValueError:
            return date.today()


def pick_date(parent: tk.Misc, initial: str = "") -> Optional[str]:
    """
    Modal calendar picker. Returns YYYY-MM-DD or None if cancelled.
    Prefers tkcalendar; falls back to a built-in month grid (no text-only dialog).
    """
    result: dict[str, Optional[str]] = {"value": None}
    current = _parse_initial(initial)

    dialog = tk.Toplevel(parent)
    dialog.title("Select Date")
    dialog.transient(parent)
    dialog.resizable(False, False)
    dialog.grab_set()

    def finish(selected: Optional[date]) -> None:
        if selected is not None:
            result["value"] = selected.strftime("%Y-%m-%d")
        dialog.destroy()

    try:
        from tkcalendar import Calendar

        cal = Calendar(
            dialog,
            selectmode="day",
            year=current.year,
            month=current.month,
            day=current.day,
            date_pattern="y-mm-dd",
        )
        cal.pack(padx=12, pady=12)

        def use_selection() -> None:
            sel = cal.selection_get()
            finish(sel if isinstance(sel, date) else date(sel.year, sel.month, sel.day))

        btn_row = ttk.Frame(dialog)
        btn_row.pack(fill=tk.X, padx=12, pady=(0, 12))
        ttk.Button(btn_row, text="Cancel", command=lambda: finish(None)).pack(side=tk.RIGHT)
        ttk.Button(btn_row, text="OK", command=use_selection).pack(side=tk.RIGHT, padx=(0, 8))
        cal.bind("<<CalendarSelected>>", lambda _e: None)
    except ImportError:
        _build_builtin_calendar(dialog, current, finish)

    dialog.update_idletasks()
    dialog.geometry(f"+{parent.winfo_rootx() + 40}+{parent.winfo_rooty() + 40}")
    parent.wait_window(dialog)
    return result["value"]


def _build_builtin_calendar(dialog: tk.Toplevel, current: date, finish) -> None:
    """Simple month grid when tkcalendar is not installed."""
    state = {"year": current.year, "month": current.month, "selected": current}

    header = ttk.Frame(dialog)
    header.pack(fill=tk.X, padx=12, pady=(12, 4))
    title_var = tk.StringVar()

    def refresh_title() -> None:
        title_var.set(f"{calendar.month_name[state['month']]} {state['year']}")

    def shift(delta: int) -> None:
        month = state["month"] + delta
        year = state["year"]
        while month < 1:
            month += 12
            year -= 1
        while month > 12:
            month -= 12
            year += 1
        state["year"], state["month"] = year, month
        refresh_title()
        draw_days()

    ttk.Button(header, text="<", width=3, command=lambda: shift(-1)).pack(side=tk.LEFT)
    ttk.Label(header, textvariable=title_var, font=("Segoe UI", 11, "bold")).pack(
        side=tk.LEFT, expand=True
    )
    ttk.Button(header, text=">", width=3, command=lambda: shift(1)).pack(side=tk.RIGHT)
    refresh_title()

    weekdays = ttk.Frame(dialog)
    weekdays.pack(padx=12)
    for i, name in enumerate(["Mo", "Tu", "We", "Th", "Fr", "Sa", "Su"]):
        ttk.Label(weekdays, text=name, width=4, anchor="center").grid(row=0, column=i, padx=1)

    days_frame = ttk.Frame(dialog)
    days_frame.pack(padx=12, pady=4)

    def choose(day_num: int) -> None:
        state["selected"] = date(state["year"], state["month"], day_num)
        finish(state["selected"])

    def draw_days() -> None:
        for child in days_frame.winfo_children():
            child.destroy()
        weeks = calendar.Calendar(firstweekday=0).monthdayscalendar(state["year"], state["month"])
        for r, week in enumerate(weeks):
            for c, day_num in enumerate(week):
                if day_num == 0:
                    ttk.Label(days_frame, text="", width=4).grid(row=r, column=c, padx=1, pady=1)
                    continue
                is_sel = (
                    day_num == state["selected"].day
                    and state["month"] == state["selected"].month
                    and state["year"] == state["selected"].year
                )
                style = "Accent.TButton" if is_sel else "TButton"
                try:
                    btn = ttk.Button(
                        days_frame,
                        text=str(day_num),
                        width=4,
                        style=style,
                        command=lambda d=day_num: choose(d),
                    )
                except tk.TclError:
                    btn = ttk.Button(
                        days_frame,
                        text=str(day_num),
                        width=4,
                        command=lambda d=day_num: choose(d),
                    )
                btn.grid(row=r, column=c, padx=1, pady=1)

    draw_days()

    btn_row = ttk.Frame(dialog)
    btn_row.pack(fill=tk.X, padx=12, pady=(4, 12))
    ttk.Button(btn_row, text="Today", command=lambda: finish(date.today())).pack(side=tk.LEFT)
    ttk.Button(btn_row, text="Cancel", command=lambda: finish(None)).pack(side=tk.RIGHT)


def apply_picked_date(parent: tk.Misc, date_var: tk.Variable) -> None:
    """Open picker and write YYYY-MM-DD into date_var when confirmed."""
    try:
        chosen = pick_date(parent, date_var.get() if hasattr(date_var, "get") else "")
        if chosen:
            date_var.set(chosen)
    except Exception as exc:
        messagebox.showerror("Error", f"Date selection error: {exc}")
