"""
Modal date picker for Tkinter + tkcalendar.

Writes dates as dd-mm-yyyy (same as app DATE_FORMAT). Import and attach with
`add_date_picker_button` or call `open_date_picker` directly.
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from datetime import datetime, timedelta, date
from typing import Callable, Optional

from tkcalendar import Calendar

DISPLAY_FMT = "%d-%m-%Y"


def _parse_initial(text: str) -> Optional[date]:
    if not text or not str(text).strip():
        return None
    s = str(text).strip()
    for fmt in (DISPLAY_FMT, "%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def open_date_picker(
    master: tk.Misc,
    string_var: tk.StringVar,
    *,
    title: str = "Select date",
    subtitle: str = "Format: dd-mm-yyyy",
    on_confirm: Optional[Callable[[], None]] = None,
) -> None:
    """
    Open a modal calendar. On Confirm, sets string_var to dd-mm-yyyy and calls on_confirm.
    """
    top = tk.Toplevel(master)
    top.title(title)
    top.geometry("340x400")
    top.resizable(False, False)
    root = master.winfo_toplevel()
    top.transient(root)

    header = ttk.Frame(top)
    header.pack(fill="x", padx=10, pady=(10, 4))
    ttk.Label(header, text=title, font=("Arial", 10, "bold")).pack(side=tk.LEFT)

    sub = ttk.Frame(top)
    sub.pack(fill="x", padx=10, pady=(0, 4))
    ttk.Label(sub, text=subtitle, foreground="#1565C0").pack(side=tk.LEFT)

    cal = Calendar(top, selectmode="day", date_pattern="dd-mm-yyyy")
    cal.pack(padx=10, pady=8, fill="both", expand=True)

    cur = string_var.get()
    initial = _parse_initial(cur)
    if initial:
        try:
            cal.selection_set(initial)
        except (tk.TclError, ValueError):
            pass

    today = datetime.now().date()

    def _month_bounds(d: date) -> tuple[date, date]:
        first = d.replace(day=1)
        if d.month == 12:
            last = d.replace(day=31)
        else:
            nxt = d.replace(month=d.month + 1, day=1)
            last = nxt - timedelta(days=1)
        return first, last

    first_m, last_m = _month_bounds(today)

    quick = ttk.Frame(top)
    quick.pack(fill="x", padx=10, pady=4)
    ttk.Button(quick, text="Today", command=lambda: cal.selection_set(today)).pack(
        side=tk.LEFT, padx=3
    )
    ttk.Button(quick, text="Month start", command=lambda: cal.selection_set(first_m)).pack(
        side=tk.LEFT, padx=3
    )
    ttk.Button(quick, text="Month end", command=lambda: cal.selection_set(last_m)).pack(
        side=tk.LEFT, padx=3
    )

    def confirm() -> None:
        raw = cal.get_date()
        try:
            if isinstance(raw, str):
                d = _parse_initial(raw) or today
            elif isinstance(raw, date):
                d = raw
            else:
                d = today
        except Exception:
            d = today
        string_var.set(d.strftime(DISPLAY_FMT))
        top.destroy()
        if on_confirm:
            on_confirm()

    btns = ttk.Frame(top)
    btns.pack(fill="x", padx=10, pady=(4, 12))
    ttk.Button(btns, text="Cancel", command=top.destroy).pack(side=tk.RIGHT, padx=4)
    ttk.Button(btns, text="OK", command=confirm).pack(side=tk.RIGHT, padx=4)

    top.grab_set()
    top.wait_window(top)


def add_date_picker_button(
    parent: tk.Misc,
    string_var: tk.StringVar,
    modal_master: tk.Misc,
    *,
    title: str = "Select date",
    on_confirm: Optional[Callable[[], None]] = None,
    button_text: str = "\U0001F4C5",
    width: int = 3,
) -> ttk.Button:
    """Pack a compact button that opens open_date_picker for string_var."""

    def _open() -> None:
        open_date_picker(modal_master, string_var, title=title, on_confirm=on_confirm)

    btn = ttk.Button(parent, text=button_text, width=width, command=_open)
    return btn
