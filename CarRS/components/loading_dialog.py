"""Modal loading dialog for blocking user input during async operations.

Tkinter widgets must be created/destroyed on the main thread. Creating a
LoadingDialog from a worker thread makes it flash and vanish — that was the bug.
Use ``run_with_loading`` (preferred) or call ``show``/``hide`` only on the UI thread.
"""
from __future__ import annotations

import threading
import time
import tkinter as tk
from tkinter import ttk
from typing import Any, Callable, Optional


class LoadingDialog:
    """Modal loading dialog. show/hide must run on the Tk main thread."""

    def __init__(self, parent, title="Loading", message="Please wait..."):
        self.parent = parent
        self.title = title
        self.message = message
        self.dialog = None
        self.status_label = None
        self.is_shown = False
        self._cancelled = False
        self.progress_bar = None
        self.cancel_button = None
        self._shown_at = 0.0

    def show(self, message=None):
        """Show the loading dialog (main thread only)."""
        if threading.current_thread() is not threading.main_thread():
            raise RuntimeError(
                "LoadingDialog.show() must be called on the Tk main thread. "
                "Use run_with_loading() instead."
            )

        if self.is_shown:
            self.update_message(message or self.message)
            return

        self.is_shown = True
        self._cancelled = False
        self._shown_at = time.monotonic()

        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.title)
        self.dialog.transient(self.parent)
        self.dialog.resizable(False, False)

        width, height = 400, 150
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        self.status_label = ttk.Label(
            main_frame,
            text=message or self.message,
            font=("Segoe UI", 10),
            wraplength=350,
        )
        self.status_label.pack(pady=(0, 15))

        self.progress_bar = ttk.Progressbar(main_frame, mode="indeterminate", length=350)
        self.progress_bar.pack(pady=(0, 10))
        self.progress_bar.start(10)

        self.cancel_button = ttk.Button(main_frame, text="Cancel", command=self._on_cancel)
        self.cancel_button.pack()

        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
        self.dialog.lift()
        self.dialog.focus_force()
        self.dialog.grab_set()
        self.dialog.update_idletasks()
        self.dialog.update()

    def update_message(self, message):
        """Update the status message (main thread)."""
        if not message:
            return

        def _apply():
            if self.status_label and self.dialog:
                self.status_label.config(text=message)
                self.dialog.update_idletasks()

        if threading.current_thread() is threading.main_thread():
            _apply()
        else:
            self.parent.after(0, _apply)

    def hide_cancel_button(self):
        if self.cancel_button:
            self.cancel_button.pack_forget()

    def _on_cancel(self):
        self._cancelled = True
        self.hide()

    def hide(self, min_visible_ms: int = 0):
        """Hide the dialog on the main thread; optional minimum visible time."""
        def _hide():
            if not self.is_shown:
                return
            if min_visible_ms > 0 and self._shown_at:
                elapsed_ms = (time.monotonic() - self._shown_at) * 1000
                remaining = int(min_visible_ms - elapsed_ms)
                if remaining > 0:
                    self.parent.after(remaining, lambda: self.hide(min_visible_ms=0))
                    return
            if self.progress_bar:
                try:
                    self.progress_bar.stop()
                except tk.TclError:
                    pass
            if self.dialog:
                try:
                    self.dialog.grab_release()
                except tk.TclError:
                    pass
                try:
                    self.dialog.destroy()
                except tk.TclError:
                    pass
            self.dialog = None
            self.is_shown = False

        if threading.current_thread() is threading.main_thread():
            _hide()
        else:
            self.parent.after(0, _hide)

    def is_cancelled(self):
        return self._cancelled

    def __enter__(self):
        self.show()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.hide()
        return False


def run_with_loading(
    parent: tk.Misc,
    work: Callable[[], Any],
    on_success: Callable[[Any], None],
    on_error: Optional[Callable[[BaseException], None]] = None,
    title: str = "Loading",
    message: str = "Please wait...",
    min_visible_ms: int = 450,
) -> LoadingDialog:
    """
    Show loading on the main thread, run ``work`` in a daemon thread, then
    hide and call ``on_success``/``on_error`` on the main thread.
    """
    loading = LoadingDialog(parent, title=title, message=message)
    loading.show()

    def _finish_ok(result: Any) -> None:
        elapsed_ms = (time.monotonic() - loading._shown_at) * 1000
        delay = max(0, int(min_visible_ms - elapsed_ms))

        def _close_and_success():
            loading.hide(min_visible_ms=0)
            on_success(result)

        parent.after(delay, _close_and_success)

    def _finish_err(exc: BaseException) -> None:
        elapsed_ms = (time.monotonic() - loading._shown_at) * 1000
        delay = max(0, int(min_visible_ms - elapsed_ms))

        def _close_and_fail():
            loading.hide(min_visible_ms=0)
            if on_error:
                on_error(exc)

        parent.after(delay, _close_and_fail)

    def _worker():
        try:
            result = work()
        except BaseException as exc:  # noqa: BLE001 - surface to UI callback
            parent.after(0, lambda err=exc: _finish_err(err))
            return
        parent.after(0, lambda res=result: _finish_ok(res))

    threading.Thread(target=_worker, daemon=True).start()
    return loading
