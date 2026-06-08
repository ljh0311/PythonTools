"""
Status Bar Component for the Clinic Data Visualizer application.

This module provides the application status bar with status messages,
progress indicators, and system information.

Extracted from main_window.py as part of Phase 3 component splitting.
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional
import threading
import time

from app.utils.logger import get_logger
from app.core.dependency_injection import injectable


@injectable
class StatusBarComponent:
    """
    Status bar component for the main application window.
    
    Provides status messages, progress indicators, and system information
    in a focused, reusable component.
    """
    
    def __init__(self, parent: tk.Widget):
        """
        Initialize the status bar component.
        
        Args:
            parent: Parent widget to attach the status bar to
        """
        self.parent = parent
        self.logger = get_logger(__name__)
        
        # Status bar frame
        self.status_frame = None
        self.status_label = None
        self.file_label = None
        self.progress_bar = None
        
        # Status management
        self._current_status = "Ready"
        self._current_file = "No file loaded"
        self._status_lock = threading.Lock()
        
        # Create status bar
        self._setup_status_bar()
        
        self.logger.debug("StatusBarComponent initialized")
    
    def _setup_status_bar(self):
        """Create and configure the status bar."""
        # Main status frame
        self.status_frame = ttk.Frame(self.parent)
        self.status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=2)
        
        # Status message label
        self.status_label = ttk.Label(
            self.status_frame,
            text=self._current_status,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2)
        )
        self.status_label.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Separator
        separator = ttk.Separator(self.status_frame, orient=tk.VERTICAL)
        separator.pack(side=tk.LEFT, fill=tk.Y, padx=2)
        
        # File information label
        self.file_label = ttk.Label(
            self.status_frame,
            text=self._current_file,
            relief=tk.SUNKEN,
            anchor=tk.W,
            padding=(5, 2),
            width=30
        )
        self.file_label.pack(side=tk.LEFT, padx=2)
        
        # Progress bar (initially hidden)
        self.progress_bar = ttk.Progressbar(
            self.status_frame,
            mode='determinate',
            length=150
        )
        # Don't pack initially - will be shown when needed
    
    def show_status(self, message: str, message_type: str = "info"):
        """
        Show a status message.
        
        Args:
            message: Status message to display
            message_type: Type of message ("info", "success", "warning", "error")
        """
        with self._status_lock:
            self._current_status = message
            
            # Update label text
            if self.status_label:
                self.status_label.config(text=message)
            
            # Set color based on message type
            color_map = {
                "info": "#1e293b",      # Dark gray
                "success": "#059669",   # Green
                "warning": "#d97706",   # Orange
                "error": "#dc2626"      # Red
            }
            
            color = color_map.get(message_type, color_map["info"])
            if self.status_label:
                self.status_label.config(foreground=color)
            
            self.logger.debug(f"Status updated: {message} ({message_type})")
    
    def update_file_info(self, filename: Optional[str] = None, file_path: Optional[str] = None):
        """
        Update file information in the status bar.
        
        Args:
            filename: Display name of the file
            file_path: Full path to the file (for tooltip)
        """
        with self._status_lock:
            if filename:
                self._current_file = f"File: {filename}"
            else:
                self._current_file = "No file loaded"
            
            if self.file_label:
                self.file_label.config(text=self._current_file)
                
                # Set tooltip with full path if provided
                if file_path:
                    self._create_tooltip(self.file_label, file_path)
            
            self.logger.debug(f"File info updated: {self._current_file}")
    
    def show_progress_statusBar(self, show: bool = True, progress: float = 0.0, message: str = ""):
        """
        Show or hide progress indicator.
        
        Args:
            show: Whether to show the progress bar
            progress: Progress value (0.0 to 1.0)
            message: Optional progress message
        """
        if show:
            # Show progress bar
            if self.progress_bar and not self.progress_bar.winfo_viewable():
                self.progress_bar.pack(side=tk.RIGHT, padx=5)
            
            # Update progress
            if self.progress_bar:
                self.progress_bar['value'] = progress * 100
            
            # Update status message if provided
            if message:
                self.show_status(message, "info")
        else:
            # Hide progress bar
            if self.progress_bar and self.progress_bar.winfo_viewable():
                self.progress_bar.pack_forget()
    
    def show_temporary_status(self, message: str, duration: float = 3.0, message_type: str = "info"):
        """
        Show a temporary status message that reverts after a duration.
        
        Args:
            message: Temporary message to display
            duration: Duration in seconds to show the message
            message_type: Type of message ("info", "success", "warning", "error")
        """
        # Store current status
        original_status = self._current_status
        
        # Show temporary message
        self.show_status(message, message_type)
        
        # Schedule revert to original status using after() instead of threading
        def revert_status():
            with self._status_lock:
                if self._current_status == message:  # Only revert if status hasn't changed
                    self.show_status(original_status, "info")
        
        # Use tkinter's after() method for thread-safe scheduling
        if hasattr(self, 'status_frame') and self.status_frame.winfo_exists():
            self.status_frame.after(int(duration * 1000), revert_status)
    def clear_status(self):
        """Clear the status message."""
        self.show_status("Ready", "info")
    
    def _create_tooltip(self, widget: tk.Widget, text: str):
        """
        Create a tooltip for a widget.
        
        Args:
            widget: Widget to attach tooltip to
            text: Tooltip text
        """
        def enter(event):
            # Create tooltip window
            tooltip = tk.Toplevel()
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{event.x_root + 10}+{event.y_root + 10}")
            
            # Tooltip label
            label = tk.Label(
                tooltip,
                text=text,
                background="#ffffe0",
                relief=tk.SOLID,
                borderwidth=1,
                font=("Arial", 9)
            )
            label.pack()
            
            # Store tooltip reference
            widget.tooltip = tooltip
        
        def leave(event):
            # Remove tooltip
            if hasattr(widget, 'tooltip'):
                widget.tooltip.destroy()
                del widget.tooltip
        
        # Bind events
        widget.bind('<Enter>', enter)
        widget.bind('<Leave>', leave)
    
    def get_status_frame(self) -> ttk.Frame:
        """Get the status bar frame widget."""
        return self.status_frame
    
    def get_current_status(self) -> str:
        """Get the current status message."""
        with self._status_lock:
            return self._current_status
    
    def get_current_file(self) -> str:
        """Get the current file information."""
        with self._status_lock:
            return self._current_file