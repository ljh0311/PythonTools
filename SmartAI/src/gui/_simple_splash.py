"""
Simple fallback splash screen for the Smart Robot System.
Used when the main splash screen cannot be imported.
"""

import tkinter as tk
from tkinter import ttk


class SimpleSplashScreen:
    """A simple fallback splash screen aligned with the app theme."""

    COLORS = {
        "primary": "#4285f4",
        "background": "#fafafa",
        "text": "#1f2937",
        "text_secondary": "#6b7280",
        "border": "#e5e7eb",
    }
    FONTS = {
        "title": ("Segoe UI", 18, "bold"),
        "body": ("Segoe UI", 11),
    }

    def __init__(self, parent, completion_callback=None):
        self.parent = parent
        self.completion_callback = completion_callback

        self.splash = tk.Toplevel(parent)
        self.splash.title("")
        self.splash.geometry("440x220")
        self.splash.resizable(False, False)
        self.splash.configure(background=self.COLORS["background"])
        self.splash.overrideredirect(True)

        self.splash.update_idletasks()
        x = (self.splash.winfo_screenwidth() // 2) - (440 // 2)
        y = (self.splash.winfo_screenheight() // 2) - (220 // 2)
        self.splash.geometry(f"440x220+{x}+{y}")

        border = tk.Frame(self.splash, background=self.COLORS["border"], bd=1, relief=tk.SOLID)
        border.pack(fill=tk.BOTH, expand=True)

        content = tk.Frame(border, background=self.COLORS["background"], padx=32, pady=28)
        content.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        tk.Label(
            content,
            text="Smart Home Robot Assistant",
            font=self.FONTS["title"],
            foreground=self.COLORS["primary"],
            background=self.COLORS["background"],
        ).pack(pady=(4, 8))

        tk.Label(
            content,
            text="Initializing robot system...",
            font=self.FONTS["body"],
            foreground=self.COLORS["text_secondary"],
            background=self.COLORS["background"],
        ).pack(pady=(0, 16))

        self.progress = ttk.Progressbar(content, mode="indeterminate", length=320)
        self.progress.pack(pady=8)
        self.progress.start(12)

        self.splash.after(3000, self._complete_splash)
    
    def _complete_splash(self):
        """Complete the splash screen"""
        try:
            self.splash.destroy()
            if self.completion_callback:
                self.completion_callback()
        except Exception:
            pass
    
    def set_status(self, message):
        """Update the status message"""
        pass  # Simple splash doesn't support status updates 