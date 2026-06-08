"""
Error and result dialogs for SmartCam.

- ErrorDialog / show_error_dialog: exceptions, stack trace, recovery hints.
- show_notice_dialog / show_success_dialog: non-exception outcomes (info, warning, success).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import traceback
import sys
from datetime import datetime
from typing import Optional, Dict, Any, Callable, Literal
import os

import logging

logger = logging.getLogger(__name__)


class ErrorDialog:
    """
    A comprehensive error dialog that displays error information in a user-friendly way.
    
    Features:
    - Error summary and details
    - Stack trace (collapsible)
    - Recovery suggestions
    - Copy to clipboard functionality
    - Error reporting options
    """
    
    def __init__(self, parent, error: Exception, context: Dict[str, Any] = None, 
                 recovery_callback: Optional[Callable] = None,
                 colors: Optional[dict] = None):
        """
        Initialize the error dialog.
        
        Args:
            parent: Parent window
            error: The exception that occurred
            context: Additional context about the error
            recovery_callback: Optional callback function for recovery actions
        """
        self.parent = parent
        self.error = error
        self.context = context or {}
        self.recovery_callback = recovery_callback
        self.dialog = None
        
        # Theme colors
        self.colors = colors or {
            "background": "#f0f8ff",
            "text": "#000080",
            "primary": "#4169e1",
            "error": "#dc2626",
            "card": "#ffffff",
        }

        # Error information
        self.error_type = type(error).__name__
        self.error_message = str(error)
        self.timestamp = datetime.now()
        
        # Create the dialog
        self._create_dialog()
    
    def _create_dialog(self):
        """Create the error dialog window."""
        # Handle case where parent is None
        if self.parent is None:
            # Create a root window if parent is None
            self.dialog = tk.Tk()
            self.dialog.title("Application Error")
        else:
            self.dialog = tk.Toplevel(self.parent)
            self.dialog.title("Application Error")
            # Make dialog modal only if parent exists
            self.dialog.transient(self.parent)
            self.dialog.grab_set()
        
        self.dialog.geometry("700x600")
        self.dialog.minsize(600, 500)
        
        # Center the dialog on parent or screen
        self._center_dialog()
        
        # Create main container
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create dialog content
        self._create_header(main_frame)
        self._create_error_details(main_frame)
        self._create_stack_trace(main_frame)
        self._create_recovery_section(main_frame)
        self._create_buttons(main_frame)
        
        # Bind escape key to close
        self.dialog.bind('<Escape>', lambda e: self.dialog.destroy())
        
        # Focus the dialog
        self.dialog.focus_set()
    
    def _center_dialog(self):
        """Center the dialog on the parent window."""
        self.dialog.update_idletasks()
        
        dialog_width = self.dialog.winfo_width()
        dialog_height = self.dialog.winfo_height()
        
        # Check if parent is available and has geometry
        if self.parent is not None:
            try:
                parent_x = self.parent.winfo_x()
                parent_y = self.parent.winfo_y()
                parent_width = self.parent.winfo_width()
                parent_height = self.parent.winfo_height()
                
                x = parent_x + (parent_width - dialog_width) // 2
                y = parent_y + (parent_height - dialog_height) // 2
            except (tk.TclError, AttributeError):
                # Parent window not available or not initialized, center on screen
                screen_width = self.dialog.winfo_screenwidth()
                screen_height = self.dialog.winfo_screenheight()
                x = (screen_width - dialog_width) // 2
                y = (screen_height - dialog_height) // 2
        else:
            # No parent, center on screen
            screen_width = self.dialog.winfo_screenwidth()
            screen_height = self.dialog.winfo_screenheight()
            x = (screen_width - dialog_width) // 2
            y = (screen_height - dialog_height) // 2
        
        self.dialog.geometry(f"+{x}+{y}")
    
    def _create_header(self, parent):
        """Create the error dialog header."""
        header_frame = ttk.Frame(parent)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Error icon and title
        title_frame = ttk.Frame(header_frame)
        title_frame.pack(fill=tk.X)
        
        # Error icon (using text symbol)
        icon_label = ttk.Label(
            title_frame,
            text="\u26a0\ufe0f",
            font=("Segoe UI", 24),
            foreground=self.colors["error"],
            background=self.colors["background"]
        )
        icon_label.pack(side=tk.LEFT, padx=(0, 15))
        
        # Error title
        title_label = ttk.Label(
            title_frame,
            text="An error occurred",
            font=("Segoe UI", 16, "bold"),
            foreground=self.colors["error"],
            background=self.colors["background"]
        )
        title_label.pack(side=tk.LEFT)
        
        # Timestamp
        timestamp_label = ttk.Label(
            header_frame,
            text=f"Time: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}",
            font=("Segoe UI", 9),
            foreground=self.colors["text"],
            background=self.colors["background"]
        )
        timestamp_label.pack(anchor=tk.W, pady=(5, 0))
    
    def _create_error_details(self, parent):
        """Create the error details section."""
        details_frame = ttk.LabelFrame(parent, text="Error Details", padding="15")
        details_frame.pack(fill=tk.X, pady=(0, 15))
        
        # Error type
        type_frame = ttk.Frame(details_frame)
        type_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(
            type_frame,
            text="Error Type:",
            font=("Segoe UI", 10, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(
            type_frame,
            text=self.error_type,
            font=("Segoe UI", 10),
            foreground=self.colors["error"]
        ).pack(side=tk.LEFT)
        
        # Error message
        message_frame = ttk.Frame(details_frame)
        message_frame.pack(fill=tk.X, pady=(0, 8))
        
        ttk.Label(
            message_frame,
            text="Message:",
            font=("Segoe UI", 10, "bold")
        ).pack(anchor=tk.NW, padx=(0, 10))
        
        message_text = tk.Text(
            message_frame,
            height=3,
            wrap=tk.WORD,
            font=("Segoe UI", 9),
            relief="solid",
            borderwidth=1
        )
        message_text.pack(fill=tk.X, pady=(5, 0))
        message_text.insert(tk.END, self.error_message)
        message_text.config(state=tk.DISABLED)
        
        # Context information
        if self.context:
            context_frame = ttk.Frame(details_frame)
            context_frame.pack(fill=tk.X, pady=(10, 0))
            
            ttk.Label(
                context_frame,
                text="Context:",
                font=("Segoe UI", 10, "bold")
            ).pack(anchor=tk.NW, padx=(0, 10))
            
            context_text = tk.Text(
                context_frame,
                height=2,
                wrap=tk.WORD,
                font=("Segoe UI", 9),
                relief="solid",
                borderwidth=1
            )
            context_text.pack(fill=tk.X, pady=(5, 0))
            
            # Format context as key-value pairs
            context_str = "\n".join([f"{k}: {v}" for k, v in self.context.items()])
            context_text.insert(tk.END, context_str)
            context_text.config(state=tk.DISABLED)
    
    def _create_stack_trace(self, parent):
        """Create the stack trace section (collapsible)."""
        # Container frame
        stack_frame = ttk.LabelFrame(parent, text="Technical Details", padding="15")
        stack_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 15))
        
        # Toggle button
        toggle_frame = ttk.Frame(stack_frame)
        toggle_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.stack_visible = tk.BooleanVar(value=False)
        toggle_btn = ttk.Checkbutton(
            toggle_frame,
            text="Show Stack Trace",
            variable=self.stack_visible,
            command=self._toggle_stack_trace
        )
        toggle_btn.pack(side=tk.LEFT)
        
        # Copy button
        copy_btn = ttk.Button(
            toggle_frame,
            text="Copy to Clipboard",
            command=self._copy_to_clipboard
        )
        copy_btn.pack(side=tk.RIGHT)
        
        # Stack trace text widget (initially hidden)
        self.stack_text = tk.Text(
            stack_frame,
            wrap=tk.NONE,
            font=("Consolas", 9),
            relief="solid",
            borderwidth=1,
            state=tk.DISABLED
        )
        
        # Scrollbars for stack trace
        stack_scrollbar_v = ttk.Scrollbar(stack_frame, orient=tk.VERTICAL, command=self.stack_text.yview)
        stack_scrollbar_h = ttk.Scrollbar(stack_frame, orient=tk.HORIZONTAL, command=self.stack_text.xview)
        self.stack_text.configure(yscrollcommand=stack_scrollbar_v.set, xscrollcommand=stack_scrollbar_h.set)
        
        # Pack scrollbars and text widget
        stack_scrollbar_v.pack(side=tk.RIGHT, fill=tk.Y)
        stack_scrollbar_h.pack(side=tk.BOTTOM, fill=tk.X)
        self.stack_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Initially hide the stack trace
        self.stack_text.pack_forget()
        stack_scrollbar_v.pack_forget()
        stack_scrollbar_h.pack_forget()
        
        # Populate stack trace
        self._populate_stack_trace()
    
    def _populate_stack_trace(self):
        """Populate the stack trace text widget."""
        try:
            # Get the full stack trace
            stack_trace = traceback.format_exception(type(self.error), self.error, self.error.__traceback__)
            stack_trace_str = "".join(stack_trace)
            
            # Add additional context
            full_trace = f"""Error: {self.error_type}
Message: {self.error_message}
Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

Context:
{chr(10).join([f"  {k}: {v}" for k, v in self.context.items()])}

Stack Trace:
{stack_trace_str}"""
            
            self.stack_text.config(state=tk.NORMAL)
            self.stack_text.delete(1.0, tk.END)
            self.stack_text.insert(tk.END, full_trace)
            self.stack_text.config(state=tk.DISABLED)
            
        except Exception as e:
            logger.error(f"Error populating stack trace: {e}")
            self.stack_text.config(state=tk.NORMAL)
            self.stack_text.delete(1.0, tk.END)
            self.stack_text.insert(tk.END, f"Error displaying stack trace: {e}")
            self.stack_text.config(state=tk.DISABLED)
    
    def _toggle_stack_trace(self):
        """Toggle the visibility of the stack trace."""
        if self.stack_visible.get():
            # Show stack trace
            self.stack_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            self.stack_text.master.winfo_children()[-2].pack(side=tk.RIGHT, fill=tk.Y)  # Vertical scrollbar
            self.stack_text.master.winfo_children()[-1].pack(side=tk.BOTTOM, fill=tk.X)  # Horizontal scrollbar
        else:
            # Hide stack trace
            self.stack_text.pack_forget()
            for child in self.stack_text.master.winfo_children():
                if isinstance(child, ttk.Scrollbar):
                    child.pack_forget()
    
    def _copy_to_clipboard(self):
        """Copy error details to clipboard."""
        try:
            # Get the full error information
            error_info = f"""Error Report
============

Error Type: {self.error_type}
Message: {self.error_message}
Timestamp: {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}

Context:
{chr(10).join([f"  {k}: {v}" for k, v in self.context.items()])}

Stack Trace:
{traceback.format_exc()}"""
            
            # Copy to clipboard
            self.dialog.clipboard_clear()
            self.dialog.clipboard_append(error_info)
            
            # Show confirmation
            messagebox.showinfo("Copied", "Error details copied to clipboard.")
            
        except Exception as e:
            logger.error(f"Error copying to clipboard: {e}")
            messagebox.showerror("Error", f"Failed to copy to clipboard: {e}")
    
    def _create_recovery_section(self, parent):
        """Create the recovery suggestions section."""
        try:
            recovery_frame = ttk.LabelFrame(parent, text="Recovery Suggestions", padding="15")
            recovery_frame.pack(fill=tk.X, pady=(0, 15))
            
            # Get recovery suggestions based on error type
            suggestions = self._get_recovery_suggestions(self.error, self.context)
            
            if not suggestions:
                # Fallback if no suggestions are generated
                suggestions = [
                    "Check that all required data files are accessible and not corrupted.",
                    "Ensure you have sufficient disk space and memory available.",
                    "Try restarting the application if the error persists."
                ]
            
            # Create a scrollable frame for suggestions if there are many
            if len(suggestions) > 4:
                # Create a canvas with scrollbar for many suggestions
                canvas = tk.Canvas(recovery_frame, height=120)
                scrollbar = ttk.Scrollbar(recovery_frame, orient="vertical", command=canvas.yview)
                scrollable_frame = ttk.Frame(canvas)
                
                scrollable_frame.bind(
                    "<Configure>",
                    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
                )
                
                canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
                canvas.configure(yscrollcommand=scrollbar.set)
                
                # Add suggestions to scrollable frame
                for i, suggestion in enumerate(suggestions, 1):
                    suggestion_label = ttk.Label(
                        scrollable_frame,
                        text=f"{i}. {suggestion}",
                        font=("Segoe UI", 9),
                        wraplength=550
                    )
                    suggestion_label.pack(anchor=tk.W, pady=(0, 5))
                
                canvas.pack(side="left", fill="both", expand=True)
                scrollbar.pack(side="right", fill="y")
            else:
                # Simple layout for few suggestions
                for i, suggestion in enumerate(suggestions, 1):
                    suggestion_label = ttk.Label(
                        recovery_frame,
                        text=f"{i}. {suggestion}",
                        font=("Segoe UI", 9),
                        wraplength=600
                    )
                    suggestion_label.pack(anchor=tk.W, pady=(0, 5))
                    
        except Exception as e:
            logger.error(f"Error creating recovery section: {e}")
            # Fallback: create a simple error message
            recovery_frame = ttk.LabelFrame(parent, text="Recovery Suggestions", padding="15")
            recovery_frame.pack(fill=tk.X, pady=(0, 15))
            
            fallback_label = ttk.Label(
                recovery_frame,
                text="Unable to generate specific recovery suggestions. Please try restarting the application.",
                font=("Segoe UI", 9),
                wraplength=600
            )
            fallback_label.pack(anchor=tk.W)
    
    def _get_recovery_suggestions(self, error: Exception, context: Dict[str, Any] = None):
        """Get recovery suggestions based on the error type and context."""
        try:
            suggestions = []
            context = context or {}
            
            # General suggestions
            suggestions.append("Check that all required data files are accessible and not corrupted.")
            suggestions.append("Ensure you have sufficient disk space and memory available.")
            suggestions.append("Try restarting the application if the error persists.")
            
            # Specific suggestions based on error type
            error_type = type(error)
            
            if isinstance(error, (FileNotFoundError, PermissionError)):
                suggestions.append("Verify that the file path is correct and the file exists.")
                suggestions.append("Check file permissions and ensure the file is not locked by another application.")
            elif isinstance(error, MemoryError):
                suggestions.append("Close other applications to free up memory.")
                suggestions.append("Try processing a smaller dataset.")
            elif isinstance(error, UnicodeDecodeError):
                suggestions.append("The file encoding may not be supported.")
                suggestions.append("Try saving the file as UTF-8 encoding and reload it.")
            elif isinstance(error, tk.TclError):
                suggestions.append("There may be an issue with the graphical user interface or widget options.")
                suggestions.append("Check that all widget options are valid for the widget type.")
                suggestions.append("If you recently updated the application, try reverting UI changes.")
            elif isinstance(error, ValueError):
                suggestions.append("Check that the data format is correct and complete.")
                suggestions.append("Verify that all required columns are present in the data file.")
            elif isinstance(error, KeyError):
                suggestions.append("Ensure all required data columns are present in your file.")
                suggestions.append("Check that column names match the expected format.")
            elif isinstance(error, AttributeError):
                suggestions.append("This appears to be an internal application error.")
                suggestions.append("Try restarting the application to reset the internal state.")
                suggestions.append("If the error persists, check for application updates.")
            elif isinstance(error, TypeError):
                suggestions.append("Check that the data types in your file match the expected format.")
                suggestions.append("Ensure numeric columns contain only numbers and date columns are properly formatted.")
            elif isinstance(error, IndexError):
                suggestions.append("The data file may be empty or have an unexpected structure.")
                suggestions.append("Verify that the file contains the expected number of rows and columns.")
            elif isinstance(error, (ImportError, ModuleNotFoundError)):
                suggestions.append("Required application components may be missing.")
                suggestions.append("Try reinstalling the application or updating dependencies.")
            elif isinstance(error, (ConnectionError, TimeoutError)):
                suggestions.append("Check your internet connection if the application requires online features.")
                suggestions.append("Try again when the connection is more stable.")
            elif isinstance(error, OSError):
                suggestions.append("There may be an issue with your operating system or file system.")
                suggestions.append("Try running the application as administrator or check disk health.")
            
            # Check for pandas-related errors by error message
            error_message = str(error).lower()
            if "pandas" in error_message or "pd." in error_message:
                suggestions.append("The data file format may be corrupted or incompatible.")
                suggestions.append("Try opening and resaving the file in a different format (e.g., CSV instead of Excel).")
            
            # Context-specific suggestions
            operation = context.get("operation", "")
            if "data_loading" in operation:
                suggestions.append("Try loading a different data file to isolate the issue.")
                suggestions.append("Check that the file format is supported (.csv, .xlsx, .xls).")
                suggestions.append("Ensure the file is not open in another application.")
            elif "visualization" in operation:
                suggestions.append("Try generating a different type of visualization.")
                suggestions.append("Check that the selected filters are compatible with the visualization type.")
            elif "export" in operation:
                suggestions.append("Check that you have write permissions in the export directory.")
                suggestions.append("Try exporting to a different location or format.")
            elif "filter" in operation:
                suggestions.append("Try clearing all filters and applying them one by one.")
                suggestions.append("Check that the filter values match the data in your file.")
            
            # File path specific suggestions
            if "file_path" in context:
                file_path = context["file_path"]
                if file_path:
                    suggestions.append(f"Verify the file path: {file_path}")
                    if len(file_path) > 100:
                        suggestions.append("The file path is very long - try moving the file to a shorter path.")
            
            # Memory and performance suggestions for large datasets
            context_str = str(context).lower()
            if "large" in context_str or "memory" in context_str:
                suggestions.append("For large datasets, try enabling data sampling in settings.")
                suggestions.append("Close other applications to free up system resources.")
            
            # Remove duplicates while preserving order
            seen = set()
            unique_suggestions = []
            for suggestion in suggestions:
                if suggestion not in seen:
                    seen.add(suggestion)
                    unique_suggestions.append(suggestion)
            
            return unique_suggestions[:6]  # Limit to 6 suggestions for better readability
            
        except Exception as e:
            logger.error(f"Error generating recovery suggestions: {e}")
            # Return basic suggestions if there's an error
            return [
                "Check that all required data files are accessible and not corrupted.",
                "Ensure you have sufficient disk space and memory available.",
                "Try restarting the application if the error persists."
            ]
    
    def _create_buttons(self, parent):
        """Create the dialog buttons."""
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        # Recovery button (if callback provided)
        if self.recovery_callback:
            recovery_btn = ttk.Button(
                button_frame,
                text="Try Recovery",
                command=self._execute_recovery,
                style="Accent.TButton"
            )
            recovery_btn.pack(side=tk.LEFT)
        
        # Spacer
        ttk.Frame(button_frame).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Close button
        close_btn = ttk.Button(
            button_frame,
            text="Close",
            command=self.dialog.destroy
        )
        close_btn.pack(side=tk.RIGHT)
        
        # Focus the close button
        close_btn.focus_set()
    
    def _execute_recovery(self):
        """Execute the recovery callback if provided."""
        if self.recovery_callback:
            try:
                self.recovery_callback()
                self.dialog.destroy()
            except Exception as e:
                logger.error(f"Error in recovery callback: {e}")
                messagebox.showerror("Recovery Failed", f"Recovery attempt failed: {e}")
    
    def show(self):
        """Show the error dialog and return the result."""
        if self.dialog:
            self.dialog.wait_window()
        return True


def show_error_dialog(parent, error: Exception, context: Dict[str, Any] = None, 
                     recovery_callback: Optional[Callable] = None,
                     colors: Optional[dict] = None):
    """
    Show an error dialog for the given error.
    
    Args:
        parent: Parent window
        error: The exception that occurred
        context: Additional context about the error
        recovery_callback: Optional callback function for recovery actions
        
    Returns:
        bool: True if dialog was shown successfully
    """
    try:
        dialog = ErrorDialog(parent, error, context, recovery_callback, colors=colors)
        return dialog.show()
    except Exception as e:
        logger.error(f"Error creating error dialog: {e}")
        # Fallback to simple message box
        messagebox.showerror("Error", f"An error occurred: {error}\n\nContext: {context}")
        return False


NoticeLevel = Literal["success", "info", "warning"]


def show_notice_dialog(
    parent,
    title: str,
    message: str,
    level: NoticeLevel = "info",
    details: Optional[str] = None,
    colors: Optional[dict] = None,
) -> bool:
    """
    Modal notice for success, informational, or warning outcomes (non-exception flows).

    Use show_error_dialog for exceptions and stack traces.
    """
    accent = {
        "success": "#15803d",
        "info": "#1d4ed8",
        "warning": "#c2410c",
    }.get(level, "#1d4ed8")

    palette = colors or {
        "background": "#f8fafc",
        "text": "#0f172a",
        "primary": accent,
        "card": "#ffffff",
    }

    try:
        if parent is None:
            dlg = tk.Tk()
            dlg.title(title)
        else:
            dlg = tk.Toplevel(parent)
            dlg.title(title)
            dlg.transient(parent)
            dlg.grab_set()

        dlg.geometry("520x400")
        dlg.minsize(440, 280)
        dlg.resizable(True, True)

        main = ttk.Frame(dlg, padding="20")
        main.pack(fill=tk.BOTH, expand=True)

        header = ttk.Frame(main)
        header.pack(fill=tk.X, pady=(0, 12))

        icon = {"success": "✓", "info": "ℹ", "warning": "⚠"}.get(level, "ℹ")
        ttk.Label(
            header,
            text=icon,
            font=("Segoe UI", 22),
            foreground=palette["primary"],
        ).pack(side=tk.LEFT, padx=(0, 12))

        ttk.Label(
            header,
            text=title,
            font=("Segoe UI", 14, "bold"),
            foreground=palette["text"],
        ).pack(side=tk.LEFT)

        body = ttk.Frame(main)
        body.pack(fill=tk.BOTH, expand=True)

        msg_wrap = ttk.Label(
            body,
            text=message,
            font=("Segoe UI", 10),
            foreground=palette["text"],
            wraplength=460,
            justify=tk.LEFT,
        )
        msg_wrap.pack(anchor=tk.W, fill=tk.X, pady=(0, 8))

        if details:
            detail_frame = ttk.LabelFrame(body, text="Details", padding="8")
            detail_frame.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
            txt = tk.Text(
                detail_frame,
                height=10,
                wrap=tk.WORD,
                font=("Consolas", 9),
                relief="solid",
                borderwidth=1,
            )
            scroll = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=txt.yview)
            txt.configure(yscrollcommand=scroll.set)
            txt.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scroll.pack(side=tk.RIGHT, fill=tk.Y)
            txt.insert(tk.END, details)
            txt.config(state=tk.DISABLED)

        btn_row = ttk.Frame(main)
        btn_row.pack(fill=tk.X, pady=(16, 0))
        ttk.Button(btn_row, text="OK", command=dlg.destroy).pack(side=tk.RIGHT)

        dlg.bind("<Escape>", lambda e: dlg.destroy())
        dlg.focus_set()
        dlg.wait_window()
        return True
    except Exception as e:
        logger.error(f"Error creating notice dialog: {e}")
        fn = messagebox.showwarning if level == "warning" else messagebox.showinfo
        fn(title, message if not details else f"{message}\n\n{details}")
        return False


def show_success_dialog(
    parent,
    title: str,
    message: str,
    details: Optional[str] = None,
    colors: Optional[dict] = None,
) -> bool:
    """Shorthand for a success-style notice."""
    return show_notice_dialog(parent, title, message, level="success", details=details, colors=colors)