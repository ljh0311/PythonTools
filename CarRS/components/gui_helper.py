"""Reusable GUI widget helpers (ttk/tkinter)."""
import tkinter as tk
from tkinter import ttk


class GUIHelper:
    """Static helpers for creating common ttk widgets with consistent layout."""

    @staticmethod
    def create_checkbutton(parent, text, variable, **kwargs):
        cb = ttk.Checkbutton(parent, text=text, variable=variable, **kwargs)
        cb.pack(side=tk.LEFT, padx=(0, 10))
        return cb

    @staticmethod
    def create_label(parent, text, **kwargs):
        lbl = ttk.Label(parent, text=text, **kwargs)
        lbl.pack(side=tk.LEFT, padx=(10, 2))
        return lbl

    @staticmethod
    def create_combobox(parent, textvariable, values, width, **kwargs):
        layout_options = ['row', 'column', 'rowspan', 'columnspan', 'sticky', 'padx', 'pady', 'bind_event']
        widget_kwargs = {k: v for k, v in kwargs.items() if k not in layout_options}

        cb = ttk.Combobox(
            parent,
            textvariable=textvariable,
            values=values,
            width=width,
            state="readonly",
            **widget_kwargs,
        )

        if any(opt in kwargs for opt in ['row', 'column', 'rowspan', 'columnspan', 'sticky']):
            grid_kwargs = {k: v for k, v in kwargs.items() if k in ['row', 'column', 'rowspan', 'columnspan', 'sticky', 'padx', 'pady']}
            cb.grid(**grid_kwargs)
        else:
            cb.pack(side=tk.LEFT, padx=(0, 5))

        if 'bind_event' in kwargs:
            event, handler = kwargs['bind_event']
            cb.bind(event, handler)

        return cb

    @staticmethod
    def create_collapsible(parent, title, collapsed=False):
        """Return (frame, body) where frame toggles body visibility."""
        frame = CollapsibleFrame(parent, title, collapsed=collapsed)
        return frame, frame.body


class CollapsibleFrame(ttk.Frame):
    """Simple show/hide section with toggle header."""

    def __init__(self, parent, title, collapsed=False):
        super().__init__(parent)
        self._collapsed = collapsed
        self._title = title
        header = ttk.Frame(self)
        header.pack(fill=tk.X)
        self._toggle_btn = ttk.Button(
            header,
            text=("▸ " if collapsed else "▾ ") + title,
            command=self.toggle,
        )
        self._toggle_btn.pack(anchor=tk.W, padx=2, pady=2)
        self.body = ttk.Frame(self)
        if not collapsed:
            self.body.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))

    def toggle(self):
        self._collapsed = not self._collapsed
        prefix = "▸ " if self._collapsed else "▾ "
        self._toggle_btn.config(text=prefix + self._title)
        if self._collapsed:
            self.body.pack_forget()
        else:
            self.body.pack(fill=tk.BOTH, expand=True, padx=4, pady=(0, 4))
