"""Modal loading dialog for blocking user input during async operations."""
import tkinter as tk
from tkinter import ttk


class LoadingDialog:
    """
    Modal loading dialog that blocks user input during async operations.
    Supports context manager usage and manual show/hide.
    """

    def __init__(self, parent, title="Loading", message="Please wait..."):
        self.parent = parent
        self.title = title
        self.message = message
        self.dialog = None
        self.status_label = None
        self.progress_var = None
        self.is_shown = False
        self._cancelled = False
        self.progress_bar = None
        self.cancel_button = None

    def show(self, message=None):
        """Show the loading dialog"""
        if self.is_shown:
            self.update_message(message or self.message)
            return

        self.is_shown = True
        self._cancelled = False

        # Create modal dialog
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title(self.title)
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.dialog.resizable(False, False)

        # Center the dialog
        self.dialog.update_idletasks()
        width = 400
        height = 150
        x = (self.dialog.winfo_screenwidth() // 2) - (width // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (height // 2)
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")

        # Main frame
        main_frame = ttk.Frame(self.dialog, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Status message
        self.status_label = ttk.Label(
            main_frame,
            text=message or self.message,
            font=("Segoe UI", 10),
            wraplength=350
        )
        self.status_label.pack(pady=(0, 15))

        # Progress bar (indeterminate mode)
        self.progress_var = tk.StringVar()
        progress_bar = ttk.Progressbar(
            main_frame,
            mode='indeterminate',
            length=350
        )
        progress_bar.pack(pady=(0, 10))
        progress_bar.start(10)

        self.progress_bar = progress_bar

        # Cancel button (optional, can be hidden)
        self.cancel_button = ttk.Button(
            main_frame,
            text="Cancel",
            command=self._on_cancel
        )
        self.cancel_button.pack()

        # Prevent closing via window manager
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)

        self.dialog.update()

    def update_message(self, message):
        """Update the status message"""
        if self.status_label and message:
            self.status_label.config(text=message)
            self.dialog.update_idletasks()

    def hide_cancel_button(self):
        """Hide the cancel button"""
        if self.cancel_button:
            self.cancel_button.pack_forget()

    def _on_cancel(self):
        """Handle cancel button click"""
        self._cancelled = True
        self.hide()

    def hide(self):
        """Hide the loading dialog"""
        if self.dialog and self.is_shown:
            if self.progress_bar:
                self.progress_bar.stop()
            self.dialog.grab_release()
            self.dialog.destroy()
            self.dialog = None
            self.is_shown = False

    def is_cancelled(self):
        """Check if operation was cancelled"""
        return self._cancelled

    def __enter__(self):
        """Context manager entry"""
        self.show()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.hide()
        return False
