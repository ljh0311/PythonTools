"""
Progress dialog for long-running operations with cancellation and responsive UI.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import time
from typing import Callable, Optional
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class ProgressDialog:
    """
    Enhanced progress dialog with ETA calculation and detailed progress tracking.
    
    Features:
    - Estimated time to completion
    - Progress percentage display
    - Elapsed time tracking
    - Cancellable operations
    - Detailed status messages
    - Never shows 0% progress (minimum 1%)
    - Immediate visual feedback
    - Throttled updates for better performance
    """
    
    def __init__(self, parent, title: str = "Processing...", 
                 message: str = "Please wait...", 
                 can_cancel: bool = True,
                 cancel_callback: Optional[Callable[[], None]] = None,
                 colors: Optional[dict] = None,
                 file_size_mb: float = None):
        """
        Initialize the progress dialog.
        
        Usage:
            dialog = ProgressDialog(parent_window, "Initializing Camera", "Setting up camera and AI components...")
            dialog.update_progress(0.5, "Halfway done")
            dialog.close()
        
        Args:
            parent: Parent window
            title: Dialog title
            message: Initial status message
            can_cancel: Whether the operation can be cancelled
            cancel_callback: Callback function when cancelled
        """
        self.parent = parent
        self.title = title
        self.message = message
        self.can_cancel = can_cancel
        self.cancel_callback = cancel_callback
        self.file_size_mb = file_size_mb
        
        self._closed = False
        self._cancelled = False  # Ensure this is always defined
        self._start_time = time.time()
        self._last_update_time = self._start_time
        self._progress = 0.01  # Start at 1% instead of 0%
        self._eta_seconds = 0
        self._last_progress_update = time.time()
        
        # Throttling for performance optimization
        self._last_ui_update = 0
        self._ui_update_threshold = 0.1  # Minimum 100ms between UI updates
        self._last_eta_update = 0
        self._eta_update_threshold = 1.0  # Minimum 1 second between ETA updates
        self._last_elapsed_update = 0
        self._elapsed_update_threshold = 0.5  # Minimum 500ms between elapsed time updates
        
        # ETA calculation improvements
        self._progress_history = []  # List of (progress, timestamp) tuples
        self._last_progress_time = self._start_time
        self._min_progress_for_eta = 0.02  # Need at least 2% progress for ETA
        self._eta_sample_size = 5  # Number of recent samples to average
        
        # UI state tracking to prevent unnecessary updates
        self._last_progress_percent = 0
        self._last_status_message = ""
        self._last_eta_text = ""
        self._last_elapsed_text = ""
        
        self.dialog = None
        self.progress_bar = None
        self.status_label = None
        self.eta_label = None
        self.percentage_label = None
        self.elapsed_label = None
        self.cancel_button = None
        
        # Theme colors
        self.colors = colors or {
            "background": "#f0f8ff",
            "text": "#000080",
            "primary": "#4169e1",
            "error": "#dc2626",
            "card": "#ffffff",
        }

        self._create_dialog()
        
        # Show file size warning if provided
        self._show_file_size_warning()
        
        # Immediately show 1% progress to ensure dialog is responsive
        self._show_initial_progress()
        
        # Start watchdog timer to ensure progress never gets stuck (less frequent)
        self._start_watchdog_timer()
    
    def _show_file_size_warning(self):
        """Show warning for large files based on size."""
        try:
            if self.file_size_mb and self.warning_label and self.dialog and self.dialog.winfo_exists():
                if self.file_size_mb > 10:
                    warning_text = f"⚠️ Large file detected ({self.file_size_mb:.1f}MB). Expected loading time: 2-8 minutes."
                elif self.file_size_mb > 5:
                    warning_text = f"⚠️ Medium file detected ({self.file_size_mb:.1f}MB). Expected loading time: 1-3 minutes."
                elif self.file_size_mb > 1:
                    warning_text = f"ℹ️ File size: {self.file_size_mb:.1f}MB. Expected loading time: 30-90 seconds."
                else:
                    warning_text = f"ℹ️ File size: {self.file_size_mb:.1f}MB. Expected loading time: 10-30 seconds."
                
                self.warning_label.config(text=warning_text)
                
        except Exception as e:
            logger.error(f"Error showing file size warning: {e}")

    def _show_initial_progress(self):
        """Show initial progress immediately after dialog creation."""
        try:
            if self.dialog and self.dialog.winfo_exists():
                # Update progress bar to 1%
                if self.progress_bar:
                    self.progress_bar["value"] = 1
                
                # Update percentage label
                if self.percentage_label:
                    self.percentage_label.config(text="1%")
                
                # Update status message
                if self.status_label:
                    self.status_label.config(text=self.message)
                
                # Force update to ensure dialog is visible
                self.dialog.update_idletasks()
                
        except Exception as e:
            logger.error(f"Error showing initial progress: {e}")
    
    def _start_watchdog_timer(self):
        """Start watchdog timer to ensure progress never gets stuck (optimized frequency)."""
        def watchdog_check():
            if self._closed or self._cancelled:
                return
            
            try:
                current_time = time.time()
                time_since_update = current_time - self._last_progress_update
                
                # If no progress update for 10 seconds and progress is still low, show activity
                if time_since_update > 10.0 and self._progress < 0.1:
                    # Show "Still working..." message
                    if self.status_label and self.dialog and self.dialog.winfo_exists():
                        current_text = self.status_label.cget("text")
                        if "Still working" not in current_text:
                            self.status_label.config(text=f"{current_text} (Still working...)")
                
                # Schedule next check (less frequent - every 5 seconds instead of 2)
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.after(5000, watchdog_check)  # Check every 5 seconds
                    
            except Exception as e:
                logger.error(f"Error in watchdog timer: {e}")
        
        # Start the watchdog
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(5000, watchdog_check)  # Start after 5 seconds
    
    def _create_dialog(self):
        """Create the progress dialog window."""
        try:
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.title(self.title)
            self.dialog.resizable(True, True)  # Allow resizing
            self.dialog.transient(self.parent)
            self.dialog.grab_set()
            
            self._create_ui()  # Create UI first to determine size
            self._center_dialog()  # Center after UI is created
            
            self.dialog.focus_set()
            self.dialog.protocol("WM_DELETE_WINDOW", self._on_cancel)
            
            # Ensure dialog is visible immediately
            self.dialog.update_idletasks()
            
        except Exception as e:
            logger.error(f"Error creating progress dialog: {e}")
            raise
    
    def _center_dialog(self):
        """Center the dialog on the screen."""
        try:
            self.dialog.update_idletasks()
            x = (self.dialog.winfo_screenwidth() // 2) - (450 // 2)
            y = (self.dialog.winfo_screenheight() // 2) - (200 // 2)
            self.dialog.geometry(f"450x{self.dialog.winfo_height()}+{x}+{y}")
        except Exception as e:
            logger.error(f"Error centering dialog: {e}")
    
    def _create_ui(self):
        """Create the user interface components."""
        try:
            main_frame = ttk.Frame(self.dialog, padding="20")
            main_frame.pack(fill=tk.BOTH, expand=True)

            # Add file size and estimated time warning
            self.warning_label = ttk.Label(
                main_frame,
                text="",
                font=("Segoe UI", 9),
                foreground="#dc2626",
                wraplength=400,
                justify=tk.CENTER
            )
            self.warning_label.pack(pady=(0, 10))

            self.status_label = ttk.Label(
                main_frame,
                text=self.message,
                font=("Segoe UI", 10),
                wraplength=400,
                justify=tk.CENTER
            )
            self.status_label.pack(pady=(0, 15))
            
            self.progress_bar = ttk.Progressbar(
                main_frame,
                mode="determinate",
                length=400,
                maximum=100
            )
            self.progress_bar.pack(pady=(0, 10))
            
            details_frame = ttk.Frame(main_frame)
            details_frame.pack(fill=tk.X, pady=(0, 15))
            
            self.percentage_label = ttk.Label(
                details_frame,
                text="1%",  # Start at 1% instead of 0%
                font=("Segoe UI", 9, "bold")
            )
            self.percentage_label.pack(side=tk.LEFT)
            
            time_frame = ttk.Frame(details_frame)
            time_frame.pack(side=tk.RIGHT, fill=tk.X, expand=True)
            
            eta_frame = ttk.Frame(time_frame)
            eta_frame.pack(fill=tk.X, pady=(0, 2))
            
            eta_icon = ttk.Label(
                eta_frame,
                text="⏱",
                font=("Segoe UI", 8)
            )
            eta_icon.pack(side=tk.LEFT, padx=(0, 4))
            
            self.eta_label = ttk.Label(
                eta_frame,
                text="ETA: Calculating...",
                font=("Segoe UI", 9)
            )
            self.eta_label.pack(side=tk.LEFT)
            
            elapsed_frame = ttk.Frame(main_frame)
            elapsed_frame.pack(pady=(0, 15))
            
            elapsed_icon = ttk.Label(
                elapsed_frame,
                text="⏰",
                font=("Segoe UI", 8)
            )
            elapsed_icon.pack(side=tk.LEFT, padx=(0, 4))
            
            self.elapsed_label = ttk.Label(
                elapsed_frame,
                text="Elapsed: 0:00",
                font=("Segoe UI", 9)
            )
            self.elapsed_label.pack(side=tk.LEFT)
            
            if self.can_cancel:
                button_frame = ttk.Frame(main_frame)
                button_frame.pack(pady=(5, 0))
                
                self.cancel_button = ttk.Button(
                    button_frame,
                    text="Cancel",
                    command=self._on_cancel,
                    style="Accent.TButton",
                    width=12
                )
                self.cancel_button.pack(pady=5)
                
                self.dialog.bind('<Escape>', lambda e: self._on_cancel())
                
        except Exception as e:
            from gui.dialogs.error_dialog import show_error_dialog
            from utils.error_handler import handle_error
            
            error_result = handle_error(e, {
                'operation': 'progress_dialog_ui_creation',
                'component': 'progress_dialog',
                'dialog_type': 'progress'
            })
            
            show_error_dialog(
                parent=self.parent,
                error=e,
                context={
                    'operation': 'Creating progress dialog UI',
                    'component': 'ProgressDialog',
                    'dialog_type': 'progress'
                }
            )
            raise
    
    def update_progress(self, progress: float, message: str = ""):
        """
        Update progress and status message with throttled updates for better performance.
        
        Usage:
            dialog.update_progress(0.5, "Processing item 50 of 100")
            dialog.update_progress(1.0, "Complete!")
        
        Args:
            progress: Progress value (0.0 to 1.0)
            message: Status message to display
        """
        if self._closed or self._cancelled:
            return
        
        # Clamp progress to valid range and ensure minimum 1% (except for 100%)
        if progress < 0.0:
            progress = 0.0
        elif progress > 1.0:
            progress = 1.0
        elif progress < 0.01 and progress < 1.0:
            # Ensure minimum 1% progress unless it's completion (100%)
            progress = 0.01
        
        target_progress = progress
        
        if hasattr(self, '_current_progress'):
            progress_diff = target_progress - self._current_progress
            if abs(progress_diff) > 0.001:
                self._current_progress += progress_diff * 0.3
            else:
                self._current_progress = target_progress
        else:
            self._current_progress = target_progress
        
        self._progress = self._current_progress
        progress_percent = int(self._progress * 100)
        
        # Update last progress update time
        self._last_progress_update = time.time()
        
        # Only calculate ETA if progress has actually changed and enough time has passed
        current_time = time.time()
        if (not hasattr(self, '_last_progress_value') or 
            abs(self._progress - self._last_progress_value) > 0.001):
            self._last_progress_value = self._progress
            
            # Throttle ETA updates
            if current_time - self._last_eta_update >= self._eta_update_threshold:
                self._calculate_eta()
                self._last_eta_update = current_time
        
        # Schedule UI update with throttling
        if current_time - self._last_ui_update >= self._ui_update_threshold:
            self._last_ui_update = current_time
            self._schedule_ui_update(progress_percent, message)
    
    def _schedule_ui_update(self, progress_percent: int, message: str):
        """Schedule a single UI update with all the necessary changes."""
        def update_ui():
            if self._closed or self._cancelled:
                return
            
            try:
                # Update progress bar only if value changed significantly
                if self.progress_bar:
                    current_value = self.progress_bar["value"]
                    if abs(current_value - progress_percent) > 1:
                        self.progress_bar["value"] = progress_percent
                
                # Update percentage label only if changed
                if self.percentage_label and progress_percent != self._last_progress_percent:
                    self.percentage_label.config(text=f"{progress_percent}%")
                    self._last_progress_percent = progress_percent
                
                # Update status message only if changed
                if message and self.status_label and message != self._last_status_message:
                    self.status_label.config(text=message)
                    self._last_status_message = message
                
                # Update ETA label only if changed
                if self.eta_label:
                    eta_text = self._format_eta()
                    new_eta = f"ETA: {eta_text}"
                    if new_eta != self._last_eta_text:
                        self.eta_label.config(text=new_eta)
                        self._last_eta_text = new_eta
                
                # Update elapsed time label only if enough time has passed
                current_time = time.time()
                if (self.elapsed_label and 
                    current_time - self._last_elapsed_update >= self._elapsed_update_threshold):
                    elapsed_text = self._format_elapsed_time()
                    new_elapsed = f"Elapsed: {elapsed_text}"
                    if new_elapsed != self._last_elapsed_text:
                        self.elapsed_label.config(text=new_elapsed)
                        self._last_elapsed_text = new_elapsed
                        self._last_elapsed_update = current_time
                
                # Single update_idletasks call
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.update_idletasks()
                    
            except Exception as e:
                from gui.dialogs.error_dialog import show_error_dialog
                from utils.error_handler import handle_error
                
                error_result = handle_error(e, {
                    'operation': 'progress_dialog_update_ui',
                    'component': 'progress_dialog',
                    'dialog_type': 'progress'
                })
                
                show_error_dialog(
                    parent=self.parent,
                    error=e,
                    context={
                        'operation': 'Updating progress dialog UI',
                        'component': 'ProgressDialog',
                        'dialog_type': 'progress'
                    }
                )
        
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, update_ui)
    
    def _calculate_eta(self):
        """
        Calculate estimated time to completion based on recent progress samples.
        
        This method tracks progress over time and calculates ETA based on:
        1. Recent progress samples (last N updates)
        2. Time per progress increment
        3. Remaining work based on current progress
        
        The calculation is more accurate than simple rate-based ETA because it:
        - Uses recent samples rather than overall average
        - Accounts for varying processing speeds
        - Provides more stable estimates
        """
        current_time = time.time()
        
        # If completed, ETA is 0
        if self._progress >= 1.0:
            self._eta_seconds = 0
            return
        
        # If no meaningful progress yet, can't calculate ETA
        if self._progress < self._min_progress_for_eta:
            self._eta_seconds = None
            return
        
        # Add current progress to history
        self._progress_history.append((self._progress, current_time))
        
        # Keep only recent samples for calculation
        if len(self._progress_history) > self._eta_sample_size:
            self._progress_history = self._progress_history[-self._eta_sample_size:]
        
        # Need at least 2 samples to calculate rate
        if len(self._progress_history) < 2:
            self._eta_seconds = None
            return
        
        try:
            # Calculate recent progress rate (last N samples)
            recent_samples = self._progress_history[-min(3, len(self._progress_history)):]
            
            if len(recent_samples) >= 2:
                # Calculate time per progress increment for recent samples
                progress_rates = []
                
                for i in range(1, len(recent_samples)):
                    prev_progress, prev_time = recent_samples[i-1]
                    curr_progress, curr_time = recent_samples[i]
                    
                    progress_diff = curr_progress - prev_progress
                    time_diff = curr_time - prev_time
                    
                    if progress_diff > 0 and time_diff > 0:
                        # Time per progress increment (seconds per 1% progress)
                        rate = time_diff / progress_diff
                        progress_rates.append(rate)
                
                if progress_rates:
                    # Use median rate for stability (less affected by outliers)
                    progress_rates.sort()
                    median_rate = progress_rates[len(progress_rates) // 2]
                    
                    # Calculate remaining progress
                    remaining_progress = 1.0 - self._progress
                    
                    # Calculate ETA based on median rate
                    eta_seconds = remaining_progress * median_rate
                    
                    # Apply some smoothing to avoid wild fluctuations
                    if hasattr(self, '_eta_seconds') and self._eta_seconds is not None:
                        # Smooth with previous estimate (70% new, 30% old)
                        eta_seconds = 0.7 * eta_seconds + 0.3 * self._eta_seconds
                    
                    # Only update if ETA is reasonable (not negative, not too large)
                    if eta_seconds >= 0 and eta_seconds < 3600 * 24:  # Max 24 hours
                        self._eta_seconds = eta_seconds
                    else:
                        # Keep previous estimate if new one is unreasonable
                        if not hasattr(self, '_eta_seconds'):
                            self._eta_seconds = None
                else:
                    # No valid rates calculated, keep previous estimate
                    if not hasattr(self, '_eta_seconds'):
                        self._eta_seconds = None
            else:
                # Not enough samples, keep previous estimate
                if not hasattr(self, '_eta_seconds'):
                    self._eta_seconds = None
                    
        except Exception as e:
            logger.error(f"Error calculating ETA: {e}")
            # Keep previous estimate on error
            if not hasattr(self, '_eta_seconds'):
                self._eta_seconds = None
                
    def _format_eta(self) -> str:
        """Format ETA as human-readable string."""
        if self._eta_seconds is None or self._eta_seconds <= 0:
            return "Calculating..."
        
        eta_td = timedelta(seconds=int(self._eta_seconds))
        
        if eta_td.total_seconds() < 60:
            return f"{int(eta_td.total_seconds())}s"
        elif eta_td.total_seconds() < 3600:
            minutes = int(eta_td.total_seconds() // 60)
            seconds = int(eta_td.total_seconds() % 60)
            return f"{minutes}m {seconds}s"
        else:
            hours = int(eta_td.total_seconds() // 3600)
            minutes = int((eta_td.total_seconds() % 3600) // 60)
            return f"{hours}h {minutes}m"
    
    def _format_elapsed_time(self) -> str:
        """Format elapsed time as human-readable string."""
        elapsed = time.time() - self._start_time
        elapsed_td = timedelta(seconds=int(elapsed))
        
        if elapsed < 60:
            return f"{int(elapsed)}s"
        elif elapsed < 3600:
            minutes = int(elapsed // 60)
            seconds = int(elapsed % 60)
            return f"{minutes}:{seconds:02d}"
        else:
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            return f"{hours}:{minutes:02d}:{int(elapsed % 60):02d}"
    
    def set_message(self, message: str):
        """
        Update the status message.
        
        Args:
            message: New status message
        """
        if self._closed or self._cancelled:
            return
        
        def update_message():
            if self.status_label and not self._closed and not self._cancelled:
                self.status_label.config(text=message)
        
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, update_message)
    
    def close(self):
        """Close the progress dialog."""
        if self._closed:
            return
        
        self._closed = True
        
        def close_dialog():
            try:
                if self.dialog and self.dialog.winfo_exists():
                    self.dialog.destroy()
            except Exception as e:
                logger.error(f"Error closing progress dialog: {e}")
        
        if self.dialog and self.dialog.winfo_exists():
            self.dialog.after(0, close_dialog)
    
    def _on_cancel(self):
        """Handle cancel button click."""
        if not self.can_cancel:
            return
        
        result = messagebox.askyesno(
            "Cancel Operation",
            "Are you sure you want to cancel this operation?"
        )
        
        if result:
            self._cancelled = True
            
            # Call cancel callback if provided
            if self.cancel_callback:
                try:
                    self.cancel_callback()
                except Exception as e:
                    logger.error(f"Error in cancel callback: {e}")
            
            # Close dialog
            self.close()
    
    def is_cancelled(self) -> bool:
        """Check if the operation was cancelled."""
        return self._cancelled
    
    def is_closed(self) -> bool:
        """Check if the dialog is closed."""
        return self._closed
    
    def get_elapsed_time(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self._start_time


class ProgressManager:
    """
    Manager for progress dialogs that provides thread-safe progress updates.
    
    This class handles the creation and management of progress dialogs,
    ensuring thread-safe updates from background operations.
    """
    
    def __init__(self):
        """Initialize the progress manager."""
        self._current_dialog: Optional[ProgressDialog] = None
        self._lock = threading.Lock()
    
    def show_progress(self, parent, title: str = "Processing...", 
                     message: str = "Please wait...", 
                     can_cancel: bool = True,
                     cancel_callback: Optional[Callable[[], None]] = None,
                     file_size_mb: float = None) -> ProgressDialog:
        """Show a progress dialog."""
        with self._lock:
            if self._current_dialog and not self._current_dialog.is_closed():
                self._current_dialog.close()
            
            self._current_dialog = ProgressDialog(
                parent, title, message, can_cancel, cancel_callback, file_size_mb=file_size_mb
            )
            return self._current_dialog
    
    def update_progress(self, progress: float, message: str = ""):
        """Update the current progress dialog."""
        with self._lock:
            if self._current_dialog and not self._current_dialog.is_closed():
                self._current_dialog.update_progress(progress, message)
    
    def set_message(self, message: str):
        """Set the message of the current progress dialog."""
        with self._lock:
            if self._current_dialog and not self._current_dialog.is_closed():
                self._current_dialog.set_message(message)
    
    def close_progress(self):
        """Close the current progress dialog."""
        with self._lock:
            if self._current_dialog and not self._current_dialog.is_closed():
                self._current_dialog.close()
                self._current_dialog = None
    
    def is_cancelled(self) -> bool:
        """Check if the current operation was cancelled."""
        with self._lock:
            return (self._current_dialog.is_cancelled() 
                   if self._current_dialog and not self._current_dialog.is_closed() else False)


# Global progress manager instance
_progress_manager = ProgressManager()


def show_progress(parent, title: str = "Processing...", 
                 message: str = "Please wait...", 
                 can_cancel: bool = True,
                 cancel_callback: Optional[Callable[[], None]] = None,
                 colors: Optional[dict] = None,
                 file_size_mb: float = None) -> ProgressDialog:
    """
    Show a progress dialog using the global progress manager.
    
    Args:
        parent: Parent window
        title: Dialog title
        message: Initial message
        can_cancel: Whether to show cancel button
        cancel_callback: Callback when user clicks cancel
        
    Returns:
        ProgressDialog instance
    """
    return _progress_manager.show_progress(parent, title, message, can_cancel, cancel_callback, file_size_mb)


def update_progress(progress: float, message: str = ""):
    """
    Update the current progress dialog using the global progress manager.
    
    Args:
        progress: Progress value between 0.0 and 1.0
        message: New message to display
    """
    _progress_manager.update_progress(progress, message)


def set_progress_message(message: str):
    """
    Set the message of the current progress dialog using the global progress manager.
    
    Args:
        message: New message to display
    """
    _progress_manager.set_message(message)


def close_progress():
    """Close the current progress dialog using the global progress manager."""
    _progress_manager.close_progress()


def is_progress_cancelled() -> bool:
    """Check if the current operation was cancelled using the global progress manager."""
    return _progress_manager.is_cancelled() 