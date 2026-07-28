"""
Reusable tkinter battery monitoring widgets (2D UI assets for the brightness app).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from battery_analytics import relative_charge_percent


class BatteryGauge(tk.Canvas):
    """Battery outline with fill level relative to learned/effective full."""

    FOOTER_H = 18  # reserve space under body so dual labels never clip

    def __init__(self, master, width: int = 220, height: int = 88, **kwargs):
        super().__init__(
            master,
            width=width,
            height=height,
            highlightthickness=0,
            bg=kwargs.pop("bg", "#F4F6F8"),
            **kwargs,
        )
        self._width = width
        self._height = height
        self._os_percent = 0
        self._relative_percent = 0
        self._charging = False
        self._full_percent = 100
        self._draw()

    def update_state(
        self,
        os_percent: int,
        charging: bool = False,
        full_percent: int = 100,
    ) -> None:
        """Update gauge from OS percent and effective/learned full cap."""
        self._os_percent = max(0, min(100, int(os_percent)))
        self._charging = bool(charging)
        self._full_percent = max(65, min(100, int(full_percent)))
        self._relative_percent = relative_charge_percent(
            self._os_percent, self._full_percent
        )
        self._draw()

    def _fill_color(self) -> str:
        rel = self._relative_percent
        if self._charging:
            return "#2E9B57"
        if rel <= 15:
            return "#C0392B"
        if rel <= 35:
            return "#D68910"
        return "#1F6F8B"

    def _draw(self) -> None:
        self.delete("all")
        pad = 8
        show_learned = self._full_percent != 100
        footer = self.FOOTER_H if show_learned else 0
        body_w = self._width - pad * 2 - 12
        body_h = max(28, self._height - pad * 2 - footer)
        x0, y0 = pad, pad
        x1, y1 = x0 + body_w, y0 + body_h

        self.create_rectangle(
            x0, y0, x1, y1, outline="#5A6268", width=2, fill="#FFFFFF"
        )
        cap_w, cap_h = 8, body_h * 0.45
        cap_y0 = y0 + (body_h - cap_h) / 2
        self.create_rectangle(
            x1, cap_y0, x1 + cap_w, cap_y0 + cap_h, outline="#5A6268", fill="#5A6268"
        )

        inner_pad = 4
        fill_max = body_w - inner_pad * 2
        fill_ratio = min(1.0, self._relative_percent / 100.0)
        fill_w = max(2, fill_max * fill_ratio)
        self.create_rectangle(
            x0 + inner_pad,
            y0 + inner_pad,
            x0 + inner_pad + fill_w,
            y1 - inner_pad,
            outline="",
            fill=self._fill_color(),
        )

        cx = (x0 + x1) / 2
        cy = (y0 + y1) / 2
        rel = self._relative_percent

        if not show_learned:
            label = f"{self._os_percent}%"
            if self._charging:
                label += " ⚡"
            self.create_text(
                cx, cy, text=label, fill="#1A1A1A", font=("Segoe UI", 12, "bold")
            )
        elif rel >= 99:
            primary = "Full" if self._charging else "100%"
            self.create_text(
                cx, cy - 10, text=primary, fill="#1A1A1A", font=("Segoe UI", 12, "bold")
            )
            self.create_text(
                cx,
                cy + 4,
                text=f"of {self._full_percent}% learned full",
                fill="#444444",
                font=("Segoe UI", 8),
            )
            self.create_text(
                cx,
                cy + 16,
                text=f"OS {self._os_percent}%",
                fill="#666666",
                font=("Segoe UI", 7),
            )
        else:
            primary = f"{rel}%"
            if self._charging:
                primary += " ⚡"
            self.create_text(
                cx, cy - 6, text=primary, fill="#1A1A1A", font=("Segoe UI", 12, "bold")
            )
            self.create_text(
                cx,
                cy + 10,
                text=f"OS {self._os_percent}% · cap {self._full_percent}%",
                fill="#666666",
                font=("Segoe UI", 8),
            )


class MetricCard(ttk.LabelFrame):
    """Compact metric display card."""

    def __init__(self, master, title: str, initial_value: str = "—", **kwargs):
        super().__init__(master, text=title, padding=6, **kwargs)
        self.value_label = ttk.Label(self, text=initial_value, font=("Segoe UI", 11, "bold"))
        self.value_label.pack(anchor="w")
        self.detail_label = ttk.Label(self, text="", foreground="#666666", font=("Segoe UI", 8))
        self.detail_label.pack(anchor="w")

    def set_value(self, value: str, detail: str = "") -> None:
        self.value_label.config(text=value)
        self.detail_label.config(text=detail)


class CycleHistoryTree(ttk.Frame):
    """Scrollable recent charge/discharge cycle list."""

    COLUMNS = ("when", "kind", "range", "duration", "rate")

    def __init__(self, master, height: int = 8, **kwargs):
        super().__init__(master, **kwargs)
        self.tree = ttk.Treeview(
            self,
            columns=self.COLUMNS,
            show="headings",
            height=height,
        )
        headings = {
            "when": "Ended",
            "kind": "Type",
            "range": "% range",
            "duration": "Duration",
            "rate": "%/hr",
        }
        widths = {"when": 130, "kind": 70, "range": 90, "duration": 80, "rate": 60}
        for col in self.COLUMNS:
            self.tree.heading(col, text=headings[col])
            self.tree.column(col, width=widths[col], anchor="w")

        scroll = ttk.Scrollbar(self, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

    def set_rows(self, rows: list[tuple]) -> None:
        self.tree.delete(*self.tree.get_children())
        for row in rows:
            self.tree.insert("", "end", values=row)


class BatteryMonitorPanel(ttk.Frame):
    """Composite battery dashboard section."""

    def __init__(self, master, **kwargs):
        super().__init__(master, padding=4, **kwargs)

        top = ttk.Frame(self)
        top.pack(fill="x", pady=(0, 8))
        self.gauge = BatteryGauge(top)
        self.gauge.pack(side="left")

        metrics = ttk.Frame(top)
        metrics.pack(side="left", fill="both", expand=True, padx=(12, 0))
        self.time_to_full_card = MetricCard(metrics, "Time to full charge")
        self.time_to_full_card.pack(fill="x", pady=2)
        self.runtime_card = MetricCard(metrics, "Estimated runtime")
        self.runtime_card.pack(fill="x", pady=2)
        self.session_card = MetricCard(metrics, "Current session")
        self.session_card.pack(fill="x", pady=2)

        full_frame = ttk.LabelFrame(self, text="Full battery level", padding=6)
        full_frame.pack(fill="x", pady=4)
        self.full_percent_var = tk.IntVar(value=100)
        self.learned_label = ttk.Label(full_frame, text="Learned: —", foreground="#666666")
        self.learned_label.pack(anchor="w")
        self.auto_apply_label = ttk.Label(
            full_frame,
            text="High-confidence learned values apply automatically.",
            foreground="#666666",
            font=("Segoe UI", 8),
        )
        self.auto_apply_label.pack(anchor="w")
        slider_row = ttk.Frame(full_frame)
        slider_row.pack(fill="x", pady=4)
        ttk.Label(slider_row, text="Treat as 100% at").pack(side="left")
        self.full_slider = ttk.Scale(
            slider_row,
            from_=65,
            to=100,
            orient="horizontal",
            variable=self.full_percent_var,
        )
        self.full_slider.pack(side="left", fill="x", expand=True, padx=6)
        self.full_value_label = ttk.Label(slider_row, text="100%", width=6)
        self.full_value_label.pack(side="left")
        btn_row = ttk.Frame(full_frame)
        btn_row.pack(fill="x")
        self.apply_learned_btn = ttk.Button(
            btn_row, text="Apply learned value", state="disabled"
        )
        self.apply_learned_btn.pack(side="left")

        habit_frame = ttk.LabelFrame(self, text="Charging habits", padding=6)
        habit_frame.pack(fill="x", pady=4)
        self.habit_label = ttk.Label(
            habit_frame,
            text="Collecting data…",
            wraplength=400,
            justify="left",
        )
        self.habit_label.pack(anchor="w")

        history_frame = ttk.LabelFrame(self, text="Recent cycles", padding=6)
        history_frame.pack(fill="both", expand=True, pady=4)
        self.history = CycleHistoryTree(history_frame)
        self.history.pack(fill="both", expand=True)

        self.status_label = ttk.Label(self, text="", foreground="#1F6F8B")
        self.status_label.pack(anchor="w", pady=(4, 0))
