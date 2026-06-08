"""
Data Controls Component for the Clinic Data Visualizer application.

This module provides data loading controls, file information display,
and data summary functionality.

Extracted from main_window.py as part of Phase 3 component splitting.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from typing import Callable, Optional
import os

from app.utils.logger import get_logger
from app.core.dependency_injection import injectable, inject
from app.core.data_loader import DataLoader
from app.core.data_quality import DataQualityAssessment


@injectable
class DataControlsComponent:
    """
    Data controls component for the main application window.
    
    Provides data loading controls, file information display,
    and data summary functionality in a focused, reusable component.
    """
    
    def __init__(self, 
                 parent: tk.Widget,
                 data_loader: DataLoader,
                 data_quality_assessor: DataQualityAssessment,
                 on_data_loaded: Optional[Callable] = None,
                 on_show_summary: Optional[Callable] = None,
                 on_show_quality_report: Optional[Callable] = None):
        """
        Initialize the data controls component.
        
        Args:
            parent: Parent widget
            data_loader: Data loading service
            data_quality_assessor: Data quality assessment service
            on_data_loaded: Callback when data is loaded
            on_show_summary: Callback to show data summary
            on_show_quality_report: Callback to show quality report
        """
        self.parent = parent
        self.data_loader = data_loader
        self.data_quality_assessor = data_quality_assessor
        self.logger = get_logger(__name__)
        
        # Callbacks
        self.on_data_loaded = on_data_loaded
        self.on_show_summary = on_show_summary
        self.on_show_quality_report = on_show_quality_report
        
        # UI components
        self.data_frame = None
        self.file_label = None
        self.load_button = None
        self.summary_button = None
        self.quality_button = None
        
        # State
        self.current_file_path = None
        self.data_loaded = False
        
        # Create data controls
        self._setup_data_controls()
        
        self.logger.debug("DataControlsComponent initialized")
    
    def _setup_data_controls(self):
        """Create and configure the data controls."""
        # Main data controls frame
        self.data_frame = ttk.LabelFrame(
            self.parent,
            text="\U0001F4CA Data Controls",
            padding=10
        )
        self.data_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # File information section
        self._create_file_info_section()
        
        # Data action buttons
        self._create_action_buttons()
    
    def _create_file_info_section(self):
        """Create the file information section."""
        # File info frame
        file_info_frame = ttk.Frame(self.data_frame)
        file_info_frame.pack(fill=tk.X, pady=(0, 10))
        
        # File label
        ttk.Label(
            file_info_frame,
            text="Current File:",
            font=("Segoe UI", 9, "bold")
        ).pack(anchor=tk.W)
        
        # File path display
        self.file_label = ttk.Label(
            file_info_frame,
            text="No file loaded",
            foreground="#64748b",
            font=("Segoe UI", 9),
            wraplength=300
        )
        self.file_label.pack(anchor=tk.W, pady=(2, 0))
        
        # Make file label clickable to show full path
        self.file_label.bind("<Button-1>", self._show_full_file_path)
        self.file_label.bind("<Enter>", lambda e: self.file_label.config(cursor="hand2"))
        self.file_label.bind("<Leave>", lambda e: self.file_label.config(cursor=""))
    
    def _create_action_buttons(self):
        """Create the action buttons."""
        # Buttons frame
        buttons_frame = ttk.Frame(self.data_frame)
        buttons_frame.pack(fill=tk.X)
        
        # Load Data button
        self.load_button = ttk.Button(
            buttons_frame,
            text="📁 Load Data",
            command=self._handle_load_data,
            style="Accent.TButton"
        )
        self.load_button.pack(side=tk.LEFT, padx=(0, 5))
        
        # Data Summary button
        self.summary_button = ttk.Button(
            buttons_frame,
            text="📋 Data Summary",
            command=self._handle_show_summary,
            state=tk.DISABLED
        )
        self.summary_button.pack(side=tk.LEFT, padx=5)
        
        # Quality Report button
        self.quality_button = ttk.Button(
            buttons_frame,
            text="🔍 Quality Report",
            command=self._handle_show_quality_report,
            state=tk.DISABLED
        )
        self.quality_button.pack(side=tk.LEFT, padx=5)
    
    def _handle_load_data(self):
        """Handle load data button click."""
        try:
            # Open file dialog
            file_path = filedialog.askopenfilename(
                title="Select Data File",
                filetypes=[
                    ("CSV files", "*.csv"),
                    ("Excel files", "*.xlsx;*.xls"),
                    ("All files", "*.*")
                ]
            )
            
            if file_path:
                self.load_data_from_file(file_path)
                
        except Exception as e:
            self.logger.error(f"Error in load data handler: {e}")
            messagebox.showerror("Error", f"Failed to load data: {str(e)}")
    
    def load_data_from_file(self, file_path: str):
        """
        Load data from a specific file.
        
        Args:
            file_path: Path to the file to load
        """
        try:
            # Check if file path exists and is valid
            if not file_path or not os.path.exists(file_path):
                messagebox.showerror("Error", "Invalid file path or file does not exist")
                self.logger.error(f"Invalid file path: {file_path}")
                return
            
            # Update UI state
            self.load_button.config(state=tk.DISABLED, text="Loading...")
            
            # Load data using data loader
            success, message = self.data_loader.load_data(file_path)
            print(file_path)
            
            if success:
                # Update state
                self.current_file_path = file_path
                self.data_loaded = True
                
                # Update file label
                filename = os.path.basename(file_path)
                self.update_file_label(filename)
                
                # Enable action buttons
                self.summary_button.config(state=tk.NORMAL)
                self.quality_button.config(state=tk.NORMAL)
                
                # Call callback
                if self.on_data_loaded:
                    self.on_data_loaded()
                
                self.logger.info(f"Data loaded successfully: {filename}")
            else:
                # Show error
                messagebox.showerror("Error", message)
                self.logger.error(f"Failed to load data: {message}")
                
        except Exception as e:
            self.logger.error(f"Error loading data from file: {e}")
            messagebox.showerror("Error", f"Failed to load data: {str(e)}")
            
        finally:
            # Reset button state
            self.load_button.config(state=tk.NORMAL, text="📁 Load Data")
    
    def _handle_show_summary(self):
        """Handle show summary button click."""
        if self.on_show_summary:
            try:
                self.on_show_summary()
            except Exception as e:
                self.logger.error(f"Error in show summary callback: {e}")
                messagebox.showerror("Error", f"Failed to show summary: {str(e)}")
    
    def _handle_show_quality_report(self):
        """Handle show quality report button click."""
        if self.on_show_quality_report:
            try:
                self.on_show_quality_report()
            except Exception as e:
                self.logger.error(f"Error in show quality report callback: {e}")
                messagebox.showerror("Error", f"Failed to show quality report: {str(e)}")
    
    def _show_full_file_path(self, event=None):
        """Show the full file path in a message box."""
        if self.current_file_path:
            messagebox.showinfo(
                "File Path",
                f"Full path:\n{self.current_file_path}"
            )
    
    def update_file_label(self, filename: Optional[str] = None):
        """
        Update the file label display.
        
        Args:
            filename: Name of the file to display
        """
        if filename:
            # Truncate long filenames
            if len(filename) > 40:
                display_name = filename[:37] + "..."
            else:
                display_name = filename
                
            self.file_label.config(
                text=display_name,
                foreground="#1e293b"
            )
        else:
            self.file_label.config(
                text="No file loaded",
                foreground="#64748b"
            )
            
            # Reset state
            self.current_file_path = None
            self.data_loaded = False
            
            # Disable action buttons
            self.summary_button.config(state=tk.DISABLED)
            self.quality_button.config(state=tk.DISABLED)
    
    def get_data_frame(self) -> ttk.LabelFrame:
        """
        Get the data controls frame widget.
        
        Returns:
            The data controls frame widget
        """
        return self.data_frame
    
    def is_data_loaded(self) -> bool:
        """
        Check if data is currently loaded.
        
        Returns:
            True if data is loaded, False otherwise
        """
        return self.data_loaded
    
    def get_current_file_path(self) -> Optional[str]:
        """
        Get the current file path.
        
        Returns:
            Current file path or None if no file loaded
        """
        return self.current_file_path
    
    def get_loaded_data(self):
        """
        Get the currently loaded data.
        
        Returns:
            Loaded data or None if no data loaded
        """
        if self.data_loaded and self.data_loader:
            return self.data_loader.get_data()
        return None
    
    def refresh_data(self):
        """Refresh the currently loaded data."""
        if self.current_file_path:
            self.load_data_from_file(self.current_file_path)
    
    def clear_data(self):
        """Clear the currently loaded data."""
        if self.data_loader:
            self.data_loader.data = None
            self.data_loader.file_path = None
        
        self.update_file_label(None)
        self.logger.info("Data cleared") 