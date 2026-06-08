"""
Simple fallback splash screen for the Smart Robot System.
Used when the main splash screen cannot be imported.
"""

import tkinter as tk
from tkinter import ttk


class SimpleSplashScreen:
    """A simple fallback splash screen"""
    
    def __init__(self, parent, completion_callback=None):
        """
        Initialize the simple splash screen.
        
        Args:
            parent: Parent window
            completion_callback: Function to call when splash screen is complete
        """
        self.parent = parent
        self.completion_callback = completion_callback
        
        # Create splash window
        self.splash = tk.Toplevel(parent)
        self.splash.title("Loading...")
        self.splash.geometry("400x200")
        self.splash.resizable(False, False)
        
        # Center the window
        self.splash.update_idletasks()
        x = (self.splash.winfo_screenwidth() // 2) - (400 // 2)
        y = (self.splash.winfo_screenheight() // 2) - (200 // 2)
        self.splash.geometry(f"400x200+{x}+{y}")
        
        # Create content
        title_label = tk.Label(
            self.splash, 
            text="Smart Robot Control System", 
            font=("Arial", 16, "bold")
        )
        title_label.pack(pady=(30, 10))
        
        status_label = tk.Label(
            self.splash, 
            text="Initializing robot system...", 
            font=("Arial", 10)
        )
        status_label.pack(pady=10)
        
        # Progress bar
        self.progress = ttk.Progressbar(
            self.splash, 
            mode='indeterminate', 
            length=300
        )
        self.progress.pack(pady=20)
        self.progress.start()
        
        # Start completion timer
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