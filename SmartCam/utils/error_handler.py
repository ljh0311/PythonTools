"""
Error handling utilities for SmartCam application.

This module provides centralized error handling functionality that integrates
with the error dialog system and logging.
"""

import logging
import traceback
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import sys

logger = logging.getLogger(__name__)


def handle_error(error: Exception, context: Dict[str, Any] = None, 
                parent=None, recovery_callback: Optional[Callable] = None) -> bool:
    """
    Handle an error with proper logging and error dialog display.
    
    Args:
        error: The exception that occurred
        context: Additional context about the error
        parent: Parent window for error dialog
        recovery_callback: Optional callback function for recovery actions
        
    Returns:
        True if error was handled successfully, False otherwise
    """
    if context is None:
        context = {}
    
    # Add timestamp and error type to context
    context["timestamp"] = datetime.now().isoformat()
    context["error_type"] = type(error).__name__
    
    # Log the error
    logger.error(f"Error occurred: {error}", exc_info=True)
    
    # Try to show error dialog if parent is provided
    if parent is not None:
        try:
            from gui.dialogs.error_dialog import show_error_dialog
            return show_error_dialog(parent, error, context, recovery_callback)
        except Exception as dialog_error:
            logger.error(f"Error showing error dialog: {dialog_error}")
            # Fallback to basic error handling
            return _fallback_error_handling(error, context)
    else:
        # No parent provided, use fallback
        return _fallback_error_handling(error, context)


def _fallback_error_handling(error: Exception, context: Dict[str, Any]) -> bool:
    """
    Fallback error handling when error dialog is not available.
    
    Args:
        error: The exception that occurred
        context: Additional context about the error
        
    Returns:
        True if error was handled successfully, False otherwise
    """
    try:
        # Print error to console
        print(f"Error: {error}")
        print(f"Context: {context}")
        print(f"Traceback:")
        traceback.print_exc()
        
        # Log to file if possible
        logger.error(f"Error details: {error}")
        logger.error(f"Context: {context}")
        
        return True
    except Exception as e:
        logger.error(f"Error in fallback error handling: {e}")
        return False


def setup_global_exception_handler():
    """
    Set up global exception handler for unhandled exceptions.
    """
    def global_exception_handler(exc_type, exc_value, exc_traceback):
        """Global exception handler for unhandled exceptions."""
        if issubclass(exc_type, KeyboardInterrupt):
            # Allow keyboard interrupts to pass through
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return
        
        # Log the unhandled exception
        logger.error("Unhandled exception:", exc_info=(exc_type, exc_value, exc_traceback))
        
        # Create context for the error
        context = {
            "operation": "unhandled_exception",
            "component": "global_handler",
            "timestamp": datetime.now().isoformat()
        }
        
        # Try to show error dialog if we have a root window
        try:
            import tkinter as tk
            root = tk._default_root
            if root and root.winfo_exists():
                from gui.dialogs.error_dialog import show_error_dialog
                show_error_dialog(root, exc_value, context)
        except Exception as e:
            logger.error(f"Error showing error dialog for unhandled exception: {e}")
            # Fallback to console output
            print(f"Unhandled exception: {exc_value}")
            traceback.print_exception(exc_type, exc_value, exc_traceback)
    
    # Set the global exception handler
    sys.excepthook = global_exception_handler


def log_error_with_context(error: Exception, context: Dict[str, Any] = None):
    """
    Log an error with additional context information.
    
    Args:
        error: The exception that occurred
        context: Additional context about the error
    """
    if context is None:
        context = {}
    
    # Add error information to context
    context["error_type"] = type(error).__name__
    context["error_message"] = str(error)
    context["timestamp"] = datetime.now().isoformat()
    
    # Log the error with context
    logger.error(f"Error with context: {error}", extra={"context": context}, exc_info=True) 