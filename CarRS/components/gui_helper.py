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
    def create_collapsible(parent, title, start_open=False, pack_kwargs=None):
        """Return (outer_frame, body_frame). Body is packed only when open."""
        pack_kwargs = pack_kwargs or {"fill": tk.X, "expand": False, "padx": 5, "pady": 5}
        outer = ttk.Frame(parent)
        outer.pack(**pack_kwargs)

        open_var = tk.BooleanVar(value=bool(start_open))
        body = ttk.Frame(outer)

        def _toggle():
            if open_var.get():
                toggle_btn.config(text=f"▼ {title}")
                body.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
            else:
                toggle_btn.config(text=f"▶ {title}")
                body.pack_forget()

        toggle_btn = ttk.Checkbutton(
            outer,
            text=f"{'▼' if start_open else '▶'} {title}",
            variable=open_var,
            command=_toggle,
            style="Toolbutton",
        )
        toggle_btn.pack(anchor=tk.W, padx=2, pady=2)
        if start_open:
            body.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))
        outer._collapse_var = open_var  # noqa: SLF001 — allow callers to inspect
        return outer, body
