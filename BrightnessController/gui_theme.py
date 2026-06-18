"""Shared colors and ttk styling for the BrightnessController GUI."""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

APP_COLORS = {
    "bg": "#F4F6F8",
    "surface": "#FFFFFF",
    "text": "#1A1A2E",
    "text_muted": "#5C6670",
    "accent": "#1F6F8B",
    "success": "#2E7D4F",
    "warning": "#B86E00",
    "danger": "#AA0000",
    "idle": "#6B7280",
    "running": "#2E7D4F",
    "banner_idle_bg": "#E8ECF0",
    "banner_running_bg": "#E6F4EA",
    "banner_error_bg": "#FDECEC",
}

APP_FONTS = {
    "title": ("Segoe UI", 11, "bold"),
    "body": ("Segoe UI", 9),
    "small": ("Segoe UI", 8),
}


def apply_app_theme(root: tk.Tk) -> ttk.Style:
    """Apply a consistent clam-based theme to the application root."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    root.configure(bg=APP_COLORS["bg"])
    style.configure(".", background=APP_COLORS["bg"], foreground=APP_COLORS["text"])
    style.configure("TFrame", background=APP_COLORS["bg"])
    style.configure("TLabel", background=APP_COLORS["bg"], font=APP_FONTS["body"])
    style.configure("TLabelframe", background=APP_COLORS["bg"], font=APP_FONTS["body"])
    style.configure(
        "TLabelframe.Label",
        background=APP_COLORS["bg"],
        foreground=APP_COLORS["text"],
        font=("Segoe UI", 9, "bold"),
    )
    style.configure("TNotebook", background=APP_COLORS["bg"], borderwidth=0)
    style.configure(
        "TNotebook.Tab",
        padding=(12, 6),
        font=APP_FONTS["body"],
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", APP_COLORS["surface"]), ("!selected", APP_COLORS["bg"])],
    )
    style.configure("Primary.TButton", padding=(10, 6))
    style.configure(
        "StatusBanner.TFrame",
        background=APP_COLORS["banner_idle_bg"],
    )
    style.configure(
        "StatusBannerTitle.TLabel",
        background=APP_COLORS["banner_idle_bg"],
        font=APP_FONTS["title"],
        foreground=APP_COLORS["text"],
    )
    style.configure(
        "StatusBannerDetail.TLabel",
        background=APP_COLORS["banner_idle_bg"],
        font=APP_FONTS["small"],
        foreground=APP_COLORS["text_muted"],
    )
    style.configure(
        "Hint.TLabel",
        background=APP_COLORS["bg"],
        font=APP_FONTS["small"],
        foreground=APP_COLORS["text_muted"],
        wraplength=420,
    )
    return style
