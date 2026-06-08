"""
Focus navigation for DPAD / keyboard (Raspberry Pi buttons, accessibility).

Maintains an ordered list of focusable widgets. Binds Left/Right (or Up/Down)
to move focus, Space/Return to activate, Escape to clear or go back.
"""

import tkinter as tk
from typing import List, Union, Callable, Optional, Tuple

# Type: each item is (widget, optional_activate_callback). If callback is None, widget.invoke() is used when available.
Focusable = Union[tk.Widget, Tuple[tk.Widget, Optional[Callable[[], None]]]]


def setup_focus_navigation(
    root: tk.Tk,
    focusables: List[Focusable],
    horizontal: bool = True,
    wrap: bool = True,
) -> None:
    """
    Bind DPAD/keyboard navigation on root for the given list of focusable widgets.

    Args:
        root: Root window (or top-level frame) to bind keys on.
        focusables: List of widgets or (widget, activate_callback). For buttons,
            callback can be None and widget.invoke() will be used if available.
        horizontal: If True, use Left/Right to move; if False, use Up/Down.
        wrap: If True, wrap at end/beginning when moving focus.
    """
    # Normalize to (widget, callable)
    items: List[Tuple[tk.Widget, Optional[Callable[[], None]]]] = []
    for item in focusables:
        if isinstance(item, (list, tuple)):
            w, fn = item[0], (item[1] if len(item) > 1 else None)
        else:
            w, fn = item, None
        items.append((w, fn))

    if not items:
        return

    current_index = [0]  # use list so closure can mutate

    def index_of(widget: tk.Widget) -> int:
        for i, (w, _) in enumerate(items):
            if w == widget:
                return i
        return -1

    def set_focus(i: int) -> None:
        i = i % len(items) if wrap else max(0, min(i, len(items) - 1))
        current_index[0] = i
        try:
            items[i][0].focus_set()
        except tk.TclError:
            pass

    def on_focus_in(event: tk.Event) -> None:
        idx = index_of(event.widget)
        if idx >= 0:
            current_index[0] = idx

    def move_prev(_event: Optional[tk.Event] = None) -> str:
        if horizontal:
            set_focus(current_index[0] - 1)
        else:
            set_focus(current_index[0] - 1)
        return "break"

    def move_next(_event: Optional[tk.Event] = None) -> str:
        if horizontal:
            set_focus(current_index[0] + 1)
        else:
            set_focus(current_index[0] + 1)
        return "break"

    def activate(_event: Optional[tk.Event] = None) -> str:
        w, fn = items[current_index[0]]
        try:
            if fn is not None:
                fn()
            elif hasattr(w, 'invoke'):
                w.invoke()
        except Exception:
            pass
        return "break"

    def on_escape(_event: Optional[tk.Event] = None) -> str:
        try:
            root.focus_set()
        except tk.TclError:
            pass
        return "break"

    for w, _ in items:
        try:
            w.bind("<FocusIn>", on_focus_in)
        except tk.TclError:
            pass

    if horizontal:
        root.bind("<Left>", move_prev)
        root.bind("<Right>", move_next)
    else:
        root.bind("<Up>", move_prev)
        root.bind("<Down>", move_next)
    root.bind("<space>", activate)
    root.bind("<Return>", activate)
    root.bind("<Escape>", on_escape)

    # Initial focus on first widget (optional; can leave to user)
    # root.after(100, lambda: set_focus(0))
