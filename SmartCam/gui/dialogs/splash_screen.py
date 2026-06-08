"""
Splash screen dialog

This module provides the splash screen that displays while the application is loading,
with the same appearance and behavior as the original.
"""

import tkinter as tk
from config.settings import get_settings


class SplashScreen:
    """A modern splash screen that displays while the application is loading"""

    # Configuration constants 
    WINDOW_WIDTH = 500
    WINDOW_HEIGHT = 300
    CONTENT_PADDING = (30, 30)  # (padx, pady)
    PROGRESS_BAR_WIDTH = 400
    PROGRESS_BAR_HEIGHT = 12
    
    # Content configuration
    APP_TITLE = "SmartCam AI"
    APP_TAGLINE = "Advanced Camera Intelligence"
    INITIAL_STATUS = "Initializing application..."
    
    # Font configurations
    TITLE_FONT = ("Segoe UI", 22, "bold")
    TAGLINE_FONT = ("Segoe UI", 12)
    STATUS_FONT = ("Segoe UI", 10)
    VERSION_FONT = ("Segoe UI", 8)
    
    # Color scheme
    COLORS = {
        "primary": "#1976D2",  # Primary blue
        "background": "#FFFFFF",  # White background
        "text": "#333333",  # Dark gray for text
        "text_secondary": "#757575",  # Medium gray for secondary text
        "border": "#E0E0E0",  # Light gray for borders
    }
    
    # Progress animation settings
    PROGRESS_STEPS = {
        10: "Loading resources...",
        40: "Preparing user interface...",
        70: "Finalizing setup...",
        100: "Starting application..."
    }

    def __init__(self, parent, completion_callback=None):
        """
        Initialize the splash screen.
        
        Args:
            parent: Parent window
            completion_callback: Function to call when splash screen is complete
        """
        self.parent = parent
        self.completion_callback = completion_callback
        
        # Get settings for splash duration
        settings = get_settings()
        self.splash_duration = settings.get('GUI_CONFIG', {}).get('splash_duration', 3000)  # Default 3 seconds

        # Calculate window position
        x, y = self._calculate_window_position()
        
        # Configure the splash window
        self.splash = tk.Toplevel(parent)
        self.splash.title("")
        self.splash.geometry(f"{self.WINDOW_WIDTH}x{self.WINDOW_HEIGHT}+{x}+{y}")
        self.splash.overrideredirect(True)  # Remove window decorations
        self.splash.configure(background=self.COLORS["background"])

        # Create the UI
        self._create_border_frame()
        self._create_content_frame()
        self._create_title_section()
        self._create_progress_section()
        self._create_status_section()
        self._create_version_section()

        # Center the splash screen
        self.splash.update_idletasks()

        # Start the progress animation
        self.progress_value = 0
        # Calculate delay to match splash duration (splash_duration / 100 steps)
        self.base_delay = max(20, self.splash_duration // 100)  # Minimum 20ms per step
        self.update_progress_bar()

    def _calculate_window_position(self):
        """Calculate center position for the splash window"""
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()
        x = (screen_width - self.WINDOW_WIDTH) // 2
        y = (screen_height - self.WINDOW_HEIGHT) // 2
        return x, y

    def _create_border_frame(self):
        """Create the border frame around the splash window"""
        self.border_frame = tk.Frame(
            self.splash, background=self.COLORS["border"], bd=1, relief=tk.SOLID
        )
        self.border_frame.pack(fill=tk.BOTH, expand=True)

    def _create_content_frame(self):
        """Create the main content frame"""
        self.content = tk.Frame(
            self.border_frame, 
            background=self.COLORS["background"], 
            padx=self.CONTENT_PADDING[0], 
            pady=self.CONTENT_PADDING[1]
        )
        self.content.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

    def _create_title_section(self):
        """Create the title and tagline section"""
        # App title
        title = tk.Label(
            self.content,
            text=self.APP_TITLE,
            font=self.TITLE_FONT,
            foreground=self.COLORS["primary"],
            background=self.COLORS["background"],
        )
        title.pack(pady=(10, 5))

        # Tagline
        tagline = tk.Label(
            self.content,
            text=self.APP_TAGLINE,
            font=self.TAGLINE_FONT,
            foreground=self.COLORS["text_secondary"],
            background=self.COLORS["background"],
        )
        tagline.pack(pady=(0, 25))

    def _create_progress_section(self):
        """Create the progress bar section"""
        # Loading animation (a simulated progress bar)
        self.progress_frame = tk.Frame(
            self.content, 
            width=self.PROGRESS_BAR_WIDTH, 
            height=self.PROGRESS_BAR_HEIGHT, 
            background=self.COLORS["border"], 
            bd=0
        )
        self.progress_frame.pack(pady=10)

        # Actual progress bar that will animate
        self.progress_bar = tk.Frame(
            self.progress_frame, 
            width=0, 
            height=self.PROGRESS_BAR_HEIGHT, 
            background=self.COLORS["primary"], 
            bd=0
        )
        self.progress_bar.place(x=0, y=0)

    def _create_status_section(self):
        """Create the status message section"""
        self.status_message = tk.Label(
            self.content,
            text=self.INITIAL_STATUS,
            font=self.STATUS_FONT,
            foreground=self.COLORS["text_secondary"],
            background=self.COLORS["background"],
        )
        self.status_message.pack(pady=10)

    def _create_version_section(self):
        """Create the version section"""
        version_text = self._get_version_text()
        
        version = tk.Label(
            self.content,
            text=version_text,
            font=self.VERSION_FONT,
            foreground=self.COLORS["text_secondary"],
            background=self.COLORS["background"],
        )
        version.pack(side=tk.RIGHT, anchor=tk.SE, pady=10)

    def _get_version_text(self):
        """Return the static version text."""
        return "🛠️ SmartCam v1.0"

    def update_progress_bar(self):
        """Animate the progress bar and handle completion"""
        if self.progress_value < 100:
            # Update status message based on progress
            if self.progress_value in self.PROGRESS_STEPS:
                self.status_message.config(text=self.PROGRESS_STEPS[self.progress_value])

            # Update progress bar width
            self.progress_value += 1
            width = int(self.PROGRESS_BAR_WIDTH * (self.progress_value / 100))
            self.progress_bar.config(width=width)

            # Schedule next update with calculated timing
            delay = self.base_delay
            if 30 < self.progress_value < 70:
                delay = int(self.base_delay * 1.3)  # slow down in the middle
            self.splash.after(delay, self.update_progress_bar)
        else:
            # Animation complete - schedule completion
            self.status_message.config(text=self.PROGRESS_STEPS[100])
            self.splash.after(500, self._complete_splash)  # Brief pause before completion

    def _complete_splash(self):
        """Complete the splash screen and launch the main GUI"""
        try:
            # Destroy splash screen
            self.splash.destroy()
            
            # Call completion callback to launch main GUI
            if self.completion_callback:
                self.completion_callback()
        except Exception as e:
            # If there's an error, still try to call the callback
            if self.completion_callback:
                self.completion_callback()

    def set_status(self, message):
        """Update the status message on the splash screen"""
        if hasattr(self, 'status_message') and self.status_message.winfo_exists():
            self.status_message.config(text=message)