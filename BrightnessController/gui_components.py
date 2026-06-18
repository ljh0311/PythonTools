"""Reusable tkinter widgets for the BrightnessController GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk
from typing import Callable, Iterable, Optional

from gui_theme import APP_COLORS, APP_FONTS


class ScrollablePanel(ttk.Frame):
    """Vertical scroll container for tab content that can exceed the viewport."""

    def __init__(self, parent: tk.Misc, **kwargs):
        super().__init__(parent, **kwargs)
        self._canvas = tk.Canvas(self, highlightthickness=0, borderwidth=0)
        self._scrollbar = ttk.Scrollbar(self, orient="vertical", command=self._canvas.yview)
        self.content = ttk.Frame(self._canvas)
        self._window_id = self._canvas.create_window((0, 0), window=self.content, anchor="nw")

        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._canvas.pack(side="left", fill="both", expand=True)

        self.content.bind("<Configure>", self._on_content_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._bind_mousewheel(self._canvas)
        self._bind_mousewheel(self.content)

    def _on_content_configure(self, _event=None) -> None:
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))
        self._update_scrollbar_visibility()

    def _on_canvas_configure(self, event) -> None:
        self._canvas.itemconfigure(self._window_id, width=event.width)
        self._update_scrollbar_visibility()

    def _update_scrollbar_visibility(self) -> None:
        self._canvas.update_idletasks()
        content_height = self.content.winfo_reqheight()
        viewport_height = self._canvas.winfo_height()
        if content_height > viewport_height + 2:
            if not self._scrollbar.winfo_ismapped():
                self._scrollbar.pack(side="right", fill="y")
        elif self._scrollbar.winfo_ismapped():
            self._scrollbar.pack_forget()

    def _bind_mousewheel(self, widget: tk.Misc) -> None:
        widget.bind("<Enter>", lambda _e: self._canvas.bind_all("<MouseWheel>", self._on_mousewheel))
        widget.bind("<Leave>", lambda _e: self._canvas.unbind_all("<MouseWheel>"))

    def _on_mousewheel(self, event) -> None:
        if self._scrollbar.winfo_ismapped():
            self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")


class WindowAutoSizer:
    """Grow or shrink the root window to fit content, capped by screen size."""

    def __init__(
        self,
        root: tk.Tk,
        *,
        content_frames: Optional[Iterable[tk.Misc]] = None,
        chrome_height: int = 96,
        min_width: int = 480,
        min_height: int = 520,
        max_screen_ratio: float = 0.92,
        padding: int = 24,
    ):
        self.root = root
        self.content_frames: list[tk.Misc] = list(content_frames or [])
        self.chrome_height = chrome_height
        self.min_width = min_width
        self.min_height = min_height
        self.max_screen_ratio = max_screen_ratio
        self.padding = padding
        self._job: Optional[str] = None

    def register(self, frame: tk.Misc) -> None:
        self.content_frames.append(frame)

    def schedule_fit(self) -> None:
        if self._job is not None:
            self.root.after_cancel(self._job)
        self._job = self.root.after(75, self._fit)

    def _fit(self) -> None:
        self._job = None
        self.root.update_idletasks()

        max_w = int(self.root.winfo_screenwidth() * self.max_screen_ratio)
        max_h = int(self.root.winfo_screenheight() * self.max_screen_ratio)

        content_w = self.min_width
        content_h = 0
        for frame in self.content_frames:
            content_w = max(content_w, frame.winfo_reqwidth())
            content_h = max(content_h, frame.winfo_reqheight())

        target_w = min(max(content_w + self.padding, self.min_width), max_w)
        target_h = min(
            max(content_h + self.chrome_height + self.padding, self.min_height),
            max_h,
        )

        cur_w = max(self.root.winfo_width(), 1)
        cur_h = max(self.root.winfo_height(), 1)

        new_w = cur_w
        new_h = cur_h
        if target_w > cur_w:
            new_w = target_w
        if target_h > cur_h:
            new_h = target_h
        if target_h < cur_h - 48:
            new_h = max(target_h, self.min_height)
        if target_w < cur_w - 48:
            new_w = max(target_w, self.min_width)

        self.root.minsize(self.min_width, self.min_height)
        self.root.maxsize(max_w, max_h)
        if abs(new_w - cur_w) > 4 or abs(new_h - cur_h) > 4:
            self.root.geometry(f"{new_w}x{new_h}")


class StatusBanner(ttk.Frame):
    """Top-of-window runtime status strip (idle / running / error)."""

    _STATES = {
        "idle": ("Ready", APP_COLORS["banner_idle_bg"], APP_COLORS["idle"]),
        "running": ("Running", APP_COLORS["banner_running_bg"], APP_COLORS["running"]),
        "error": ("Attention", APP_COLORS["banner_error_bg"], APP_COLORS["danger"]),
    }

    def __init__(self, parent: tk.Misc, **kwargs):
        super().__init__(parent, style="StatusBanner.TFrame", padding=(12, 10), **kwargs)
        self._dot = tk.Canvas(self, width=12, height=12, highlightthickness=0, bd=0)
        self._dot.pack(side="left", padx=(0, 8))
        self._dot_id = self._dot.create_oval(2, 2, 10, 10, fill=APP_COLORS["idle"], outline="")

        text_col = ttk.Frame(self, style="StatusBanner.TFrame")
        text_col.pack(side="left", fill="x", expand=True)

        self._title = ttk.Label(text_col, text="Ready", style="StatusBannerTitle.TLabel")
        self._title.pack(anchor="w")
        self._detail = ttk.Label(
            text_col,
            text="Choose a mode and press Start.",
            style="StatusBannerDetail.TLabel",
        )
        self._detail.pack(anchor="w", pady=(2, 0))

    def set_state(self, state: str, detail: str = "") -> None:
        label, bg, dot = self._STATES.get(state, self._STATES["idle"])
        self.configure(style="StatusBanner.TFrame")
        for widget in (self, self._title.master):
            try:
                widget.configure(style="StatusBanner.TFrame")
            except tk.TclError:
                pass

        style = ttk.Style(self)
        style.configure("StatusBanner.TFrame", background=bg)
        style.configure("StatusBannerTitle.TLabel", background=bg)
        style.configure("StatusBannerDetail.TLabel", background=bg)

        self._dot.configure(background=bg)
        self._dot.itemconfigure(self._dot_id, fill=dot)
        self._title.configure(text=label)
        self._detail.configure(text=detail or self._default_detail(state))

    @staticmethod
    def _default_detail(state: str) -> str:
        if state == "running":
            return "Brightness control is active."
        if state == "error":
            return "Check camera selection or settings."
        return "Choose a mode and press Start."


class CollapsibleSection(ttk.Frame):
    """Progressive-disclosure panel: primary controls visible, extras behind a toggle."""

    def __init__(
        self,
        parent: tk.Misc,
        title: str,
        *,
        expanded: bool = False,
        on_layout_change: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        super().__init__(parent, **kwargs)
        self._title_text = title
        self._expanded = expanded
        self._on_layout_change = on_layout_change
        self._toggle = ttk.Button(
            self,
            text=self._button_text(),
            command=self._on_toggle,
        )
        self._toggle.pack(anchor="w", fill="x")
        self._body = ttk.Frame(self)
        if expanded:
            self._body.pack(fill="x", pady=(4, 0))

    def _button_text(self) -> str:
        arrow = "▼" if self._expanded else "▶"
        return f"{arrow} {self._title_text}"

    def _on_toggle(self) -> None:
        self._expanded = not self._expanded
        self._toggle.configure(text=self._button_text())
        if self._expanded:
            self._body.pack(fill="x", pady=(4, 0))
        else:
            self._body.pack_forget()
        if self._on_layout_change:
            self._on_layout_change()

    @property
    def body(self) -> ttk.Frame:
        return self._body


class ContextHint(ttk.Label):
    """Muted helper text for empty states and actionable feedback."""

    _LEVEL_COLORS = {
        "info": APP_COLORS["text_muted"],
        "success": APP_COLORS["success"],
        "warning": APP_COLORS["warning"],
        "error": APP_COLORS["danger"],
    }

    def __init__(self, parent: tk.Misc, text: str = "", **kwargs):
        super().__init__(parent, text=text, style="Hint.TLabel", **kwargs)

    def show_hint(self, text: str, level: str = "info") -> None:
        self.configure(text=text, foreground=self._LEVEL_COLORS.get(level, APP_COLORS["text_muted"]))

    def clear(self) -> None:
        self.configure(text="", foreground=APP_COLORS["text_muted"])


class ActionBar(ttk.Frame):
    """Grouped primary actions with consistent spacing."""

    def __init__(self, parent: tk.Misc, **kwargs):
        super().__init__(parent, padding=(10, 6), **kwargs)

    def add_button(
        self,
        text: str,
        command: Callable[[], None],
        *,
        primary: bool = False,
        **kwargs,
    ) -> ttk.Button:
        style = "Primary.TButton" if primary else "TButton"
        button = ttk.Button(self, text=text, command=command, style=style, **kwargs)
        button.pack(side="left", padx=(0, 6))
        return button
