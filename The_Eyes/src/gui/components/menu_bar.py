"""
Menu Bar Component for the Clinic Data Visualizer application.

This module provides the main application menu bar with file operations,
view options, and help functionality.

Extracted from main_window.py as part of Phase 3 component splitting.
"""

import tkinter as tk
from tkinter import messagebox
from typing import Callable, Optional
import webbrowser

from app.utils.logger import get_logger
from app.core.dependency_injection import injectable, inject
from app.core.data_quality import DataQualityAssessment


@injectable
class MenuBarComponent:
    """
    Menu bar component for the main application window.
    
    Provides file operations, view options, and help functionality
    in a focused, reusable component.
    """
    
    def __init__(self, 
                 parent: tk.Tk,
                 data_quality_assessor: DataQualityAssessment,
                 on_load_data: Optional[Callable] = None,
                 on_export_visualization: Optional[Callable] = None,
                 on_show_quality_report: Optional[Callable] = None,
                 on_show_settings: Optional[Callable] = None,
                 on_cleanup_exit: Optional[Callable] = None,
                 on_show_data_summary: Optional[Callable] = None,
                 on_switch_theme: Optional[Callable] = None,
                 on_show_process_time_table: Optional[Callable] = None,
                 on_generate_visualization: Optional[Callable] = None,
                 on_show_journey_config: Optional[Callable] = None,
                 on_quick_export_png: Optional[Callable] = None,
                 on_quick_export_pdf: Optional[Callable] = None,
                 on_show_about: Optional[Callable] = None,
                 on_show_shortcuts: Optional[Callable] = None,
                 on_show_help: Optional[Callable] = None,
                 on_refresh_data: Optional[Callable] = None,
                 on_close_current_tab: Optional[Callable] = None,
                 on_switch_to_tab: Optional[Callable] = None):
        """
        Initialize the menu bar component.
        
        Args:
            parent: Parent window
            data_quality_assessor: Data quality assessment service
            on_load_data: Callback for loading data
            on_export_visualization: Callback for exporting visualization
            on_show_quality_report: Callback for showing quality report
            on_show_settings: Callback for showing settings dialog
            on_cleanup_exit: Callback for cleanup and exit
            on_show_data_summary: Callback for showing data summary
            on_switch_theme: Callback for switching themes
            on_show_process_time_table: Callback for showing process time table
            on_generate_visualization: Callback for generating visualization
            on_show_journey_config: Callback for showing journey configuration
            on_quick_export_png: Callback for quick PNG export
            on_quick_export_pdf: Callback for quick PDF export
            on_show_about: Callback for showing about dialog
            on_show_shortcuts: Callback for showing shortcuts dialog
        """
        self.parent = parent
        self.data_quality_assessor = data_quality_assessor
        self.logger = get_logger(__name__)
        
        # Callbacks
        self.on_load_data = on_load_data
        self.on_export_visualization = on_export_visualization
        self.on_show_quality_report = on_show_quality_report
        self.on_show_settings = on_show_settings
        self.on_cleanup_exit = on_cleanup_exit
        self.on_show_data_summary = on_show_data_summary
        self.on_switch_theme = on_switch_theme
        self.on_show_process_time_table = on_show_process_time_table
        self.on_generate_visualization = on_generate_visualization
        self.on_show_journey_config = on_show_journey_config
        self.on_quick_export_png = on_quick_export_png
        self.on_quick_export_pdf = on_quick_export_pdf
        self.on_show_about = on_show_about
        self.on_show_shortcuts = on_show_shortcuts
        self.on_show_help = on_show_help
        self.on_refresh_data = on_refresh_data
        self.on_close_current_tab = on_close_current_tab
        self.on_switch_to_tab = on_switch_to_tab
        
        # Menu references for state management
        self.menu_items = {}
        
        # Create menu bar
        self.menubar = None
        self._setup_menu_bar()
        
        self.logger.debug("MenuBarComponent initialized")
    
    def _setup_menu_bar(self):
        """Create and configure the menu bar."""
        self.menubar = tk.Menu(self.parent)
        self.parent.config(menu=self.menubar)
        
        # Store menu references
        self.file_menu = None
        self.view_menu = None
        self.tools_menu = None
        self.help_menu = None
        
        # File menu
        self._create_file_menu()
        
        # View menu
        self._create_view_menu()
        
        # Tools menu
        self._create_tools_menu()
        
        # Help menu
        self._create_help_menu()
        
        # Bind keyboard shortcuts
        self._bind_shortcuts()
    
    def _create_file_menu(self):
        """Create the File menu."""
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="📁 File", menu=self.file_menu)
        
        # Load Data
        self.file_menu.add_command(
            label="📂 Load Data...",
            command=self._handle_load_data,
            accelerator="Ctrl+O"
        )
        self.menu_items["load_data"] = self.file_menu
        
        self.file_menu.add_separator()
        
        # Export options
        self.file_menu.add_command(
            label="📤 Export Current Visualization...",
            command=self._handle_export_visualization,
            accelerator="Ctrl+E"
        )
        self.menu_items["export_visualization"] = self.file_menu
        
        self.file_menu.add_separator()
        
        # Settings
        self.file_menu.add_command(
            label="⚙️ Settings...",
            command=self._handle_show_settings
        )
        
        self.file_menu.add_separator()
        
        # Exit
        self.file_menu.add_command(
            label="🚪 Exit",
            command=self._handle_cleanup_exit,
            accelerator="Ctrl+Q"
        )
    
    def _create_view_menu(self):
        """Create the View menu."""
        self.view_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="👁️ View", menu=self.view_menu)
        
        # Data Summary
        self.view_menu.add_command(
            label="📊 Data Summary",
            command=self._handle_show_data_summary,
            accelerator="Ctrl+S"
        )
        self.menu_items["data_summary"] = self.view_menu
        
        # Data Quality Report
        self.view_menu.add_command(
            label="🔍 Data Quality Report",
            command=self._handle_show_quality_report,
            accelerator="Ctrl+Q"
        )
        self.menu_items["quality_report"] = self.view_menu
        
        self.view_menu.add_separator()
        
        # Theme submenu
        theme_menu = tk.Menu(self.view_menu, tearoff=0)
        self.view_menu.add_cascade(label="🎨 Theme", menu=theme_menu)
        theme_menu.add_command(
            label="☀️ Light Theme",
            command=lambda: self._handle_switch_theme("light")
        )
        theme_menu.add_command(
            label="🌙 Dark Theme",
            command=lambda: self._handle_switch_theme("dark")
        )
        
        self.view_menu.add_separator()
        
        # Process Time Table
        self.view_menu.add_command(
            label="⏱️ Process Time Table",
            command=self._handle_show_process_time_table
        )
        
        self.view_menu.add_separator()
        
        # Generate Visualization
        self.view_menu.add_command(
            label="📈 Generate Visualization",
            command=self._handle_generate_visualization,
            accelerator="Ctrl+G"
        )
        self.menu_items["generate_visualization"] = self.view_menu
    
    def _create_tools_menu(self):
        """Create the Tools menu."""
        self.tools_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="🔧 Tools", menu=self.tools_menu)
        
        # Journey Configuration
        self.tools_menu.add_command(
            label="🛤️ Journey Configuration...",
            command=self._handle_show_journey_config
        )
        
        self.tools_menu.add_separator()
        
        # Quick Export options
        self.tools_menu.add_command(
            label="📷 Quick Export PNG",
            command=self._handle_quick_export_png,
            accelerator="Ctrl+P"
        )
        self.menu_items["quick_export_png"] = self.tools_menu
        
        self.tools_menu.add_command(
            label="📄 Quick Export PDF",
            command=self._handle_quick_export_pdf,
            accelerator="Ctrl+F"
        )
        self.menu_items["quick_export_pdf"] = self.tools_menu
        
        self.tools_menu.add_separator()
        
        # Data Quality Assessment
        self.tools_menu.add_command(
            label="🔍 Data Quality Assessment",
            command=self._handle_show_quality_report,
            accelerator="Ctrl+D"
        )
        self.menu_items["quality_assessment"] = self.tools_menu
    
    def _create_help_menu(self):
        """Create the Help menu."""
        self.help_menu = tk.Menu(self.menubar, tearoff=0)
        self.menubar.add_cascade(label="❓ Help", menu=self.help_menu)
        
        # Help Guide
        self.help_menu.add_command(
            label="📚 Help Guide",
            command=self._handle_show_help,
            accelerator="F1"
        )
        
        self.help_menu.add_separator()
        
        # About
        self.help_menu.add_command(
            label="ℹ️ About",
            command=self._handle_show_about
        )
        
        self.help_menu.add_separator()
        
        # Keyboard Shortcuts
        self.help_menu.add_command(
            label="⌨️ Keyboard Shortcuts",
            command=self._handle_show_shortcuts
        )
    
    def _bind_shortcuts(self):
        """Bind keyboard shortcuts."""
        self.parent.bind("<Control-o>", lambda e: self._handle_load_data())
        self.parent.bind("<Control-e>", lambda e: self._handle_export_visualization())
        self.parent.bind("<Control-q>", lambda e: self._handle_cleanup_exit())
        self.parent.bind("<Control-s>", lambda e: self._handle_show_data_summary())
        self.parent.bind("<Control-g>", lambda e: self._handle_generate_visualization())
        self.parent.bind("<Control-p>", lambda e: self._handle_quick_export_png())
        self.parent.bind("<Control-f>", lambda e: self._handle_quick_export_pdf())
        self.parent.bind("<Control-d>", lambda e: self._handle_show_quality_report())
        self.parent.bind("<F1>", lambda e: self._handle_show_help())
        
        # New keyboard shortcuts
        self.parent.bind("<F5>", lambda e: self._handle_refresh_data())
        self.parent.bind("<Control-h>", lambda e: self._handle_show_shortcuts())
        self.parent.bind("<Control-comma>", lambda e: self._handle_show_settings())  # Ctrl+,
        self.parent.bind("<Control-w>", lambda e: self._handle_close_current_tab())
        
        # Tab switching shortcuts (Ctrl+1 through Ctrl+9)
        for i in range(1, 10):
            self.parent.bind(f"<Control-{i}>", lambda e, tab=i-1: self._handle_switch_to_tab(tab))
    
    def _handle_load_data(self):
        """Handle load data menu action."""
        if self.on_load_data:
            try:
                self.on_load_data()
            except Exception as e:
                self.logger.error(f"Error in load data callback: {e}")
                messagebox.showerror("Error", f"Failed to load data: {str(e)}")
    
    def _handle_export_visualization(self):
        """Handle export visualization menu action."""
        if self.on_export_visualization:
            try:
                self.on_export_visualization()
            except Exception as e:
                self.logger.error(f"Error in export visualization callback: {e}")
                messagebox.showerror("Error", f"Failed to export visualization: {str(e)}")
    
    def _handle_show_settings(self):
        """Handle show settings menu action."""
        if self.on_show_settings:
            try:
                self.on_show_settings()
            except Exception as e:
                self.logger.error(f"Error in show settings callback: {e}")
                messagebox.showerror("Error", f"Failed to show settings: {str(e)}")
    
    def _handle_cleanup_exit(self):
        """Handle cleanup and exit menu action."""
        if self.on_cleanup_exit:
            try:
                self.on_cleanup_exit()
            except Exception as e:
                self.logger.error(f"Error in cleanup exit callback: {e}")
                messagebox.showerror("Error", f"Failed to exit: {str(e)}")
    
    def _handle_show_data_summary(self):
        """Handle show data summary menu action."""
        if self.on_show_data_summary:
            try:
                self.on_show_data_summary()
            except Exception as e:
                self.logger.error(f"Error in show data summary callback: {e}")
                messagebox.showerror("Error", f"Failed to show data summary: {str(e)}")
    
    def _handle_show_quality_report(self):
        """Handle show quality report menu action."""
        if self.on_show_quality_report:
            try:
                self.on_show_quality_report()
            except Exception as e:
                self.logger.error(f"Error in show quality report callback: {e}")
                messagebox.showerror("Error", f"Failed to show quality report: {str(e)}")
    
    def _handle_switch_theme(self, theme_name):
        """Handle theme switching."""
        if self.on_switch_theme:
            try:
                self.on_switch_theme(theme_name)
            except Exception as e:
                self.logger.error(f"Error in switch theme callback: {e}")
                messagebox.showerror("Error", f"Failed to switch theme: {str(e)}")
    
    def _handle_show_process_time_table(self):
        """Handle show process time table menu action."""
        if self.on_show_process_time_table:
            try:
                self.on_show_process_time_table()
            except Exception as e:
                self.logger.error(f"Error in show process time table callback: {e}")
                messagebox.showerror("Error", f"Failed to show process time table: {str(e)}")
    
    def _handle_generate_visualization(self):
        """Handle generate visualization menu action."""
        if self.on_generate_visualization:
            try:
                self.on_generate_visualization()
            except Exception as e:
                self.logger.error(f"Error in generate visualization callback: {e}")
                messagebox.showerror("Error", f"Failed to generate visualization: {str(e)}")
    
    def _handle_show_journey_config(self):
        """Handle show journey config menu action."""
        if self.on_show_journey_config:
            try:
                self.on_show_journey_config()
            except Exception as e:
                self.logger.error(f"Error in show journey config callback: {e}")
                messagebox.showerror("Error", f"Failed to show journey config: {str(e)}")
    
    def _handle_quick_export_png(self):
        """Handle quick export PNG menu action."""
        if self.on_quick_export_png:
            try:
                self.on_quick_export_png()
            except Exception as e:
                self.logger.error(f"Error in quick export PNG callback: {e}")
                messagebox.showerror("Error", f"Failed to export PNG: {str(e)}")
    
    def _handle_quick_export_pdf(self):
        """Handle quick export PDF menu action."""
        if self.on_quick_export_pdf:
            try:
                self.on_quick_export_pdf()
            except Exception as e:
                self.logger.error(f"Error in quick export PDF callback: {e}")
                messagebox.showerror("Error", f"Failed to export PDF: {str(e)}")
    
    def _handle_show_about(self):
        """Handle show about menu action."""
        if self.on_show_about:
            try:
                self.on_show_about()
            except Exception as e:
                self.logger.error(f"Error in show about callback: {e}")
                messagebox.showerror("Error", f"Failed to show about dialog: {str(e)}")
    
    def _handle_show_help(self):
        """Handle show help menu action."""
        if self.on_show_help:
            try:
                self.on_show_help()
            except Exception as e:
                self.logger.error(f"Error in show help callback: {e}")
                messagebox.showerror("Error", f"Failed to show help: {str(e)}")

    def _handle_refresh_data(self):
        """Handle refresh data action (F5 shortcut)."""
        if self.on_refresh_data:
            try:
                self.on_refresh_data()
            except Exception as e:
                self.logger.error(f"Error in refresh data callback: {e}")
                messagebox.showerror("Error", f"Failed to refresh data: {str(e)}")

    def _handle_close_current_tab(self):
        """Handle close current tab action (Ctrl+W shortcut)."""
        if self.on_close_current_tab:
            try:
                self.on_close_current_tab()
            except Exception as e:
                self.logger.error(f"Error in close current tab callback: {e}")
                messagebox.showerror("Error", f"Failed to close tab: {str(e)}")

    def _handle_switch_to_tab(self, tab_index):
        """Handle switch to tab action (Ctrl+1-9 shortcuts)."""
        if self.on_switch_to_tab:
            try:
                self.on_switch_to_tab(tab_index)
            except Exception as e:
                self.logger.error(f"Error in switch to tab callback: {e}")
                messagebox.showerror("Error", f"Failed to switch to tab: {str(e)}")
    
    def _handle_show_shortcuts(self):
        """Handle show shortcuts menu action."""
        if self.on_show_shortcuts:
            try:
                self.on_show_shortcuts()
            except Exception as e:
                self.logger.error(f"Error in show shortcuts callback: {e}")
                messagebox.showerror("Error", f"Failed to show shortcuts: {str(e)}")
    
    def update_menu_state(self, data_loaded: bool = False, visualization_available: bool = False):
        """
        Update menu item states based on application state.
        
        Args:
            data_loaded: Whether data is currently loaded
            visualization_available: Whether a visualization is available for export
        """
        try:
            # Update data-dependent menu items
            if data_loaded:
                # Enable data-dependent menu items
                if self.file_menu:
                    self.file_menu.entryconfig(0, state="normal")  # Load Data
                if self.view_menu:
                    self.view_menu.entryconfig(0, state="normal")  # Data Summary
                    self.view_menu.entryconfig(1, state="normal")  # Data Quality Report
                    self.view_menu.entryconfig(8, state="normal")  # Generate Visualization (after separators and theme submenu)
                if self.tools_menu:
                    self.tools_menu.entryconfig(6, state="normal")  # Data Quality Assessment (after separators and quick exports)
            else:
                # Disable data-dependent menu items
                if self.file_menu:
                    self.file_menu.entryconfig(0, state="disabled")  # Load Data
                if self.view_menu:
                    self.view_menu.entryconfig(0, state="disabled")  # Data Summary
                    self.view_menu.entryconfig(1, state="disabled")  # Data Quality Report
                    self.view_menu.entryconfig(8, state="disabled")  # Generate Visualization
                if self.tools_menu:
                    self.tools_menu.entryconfig(6, state="disabled")  # Data Quality Assessment
            
            # Update visualization-dependent menu items
            if visualization_available:
                # Enable export menu items
                if self.file_menu:
                    self.file_menu.entryconfig(2, state="normal")  # Export Current Visualization
                if self.tools_menu:
                    self.tools_menu.entryconfig(2, state="normal")  # Quick Export PNG
                    self.tools_menu.entryconfig(3, state="normal")  # Quick Export PDF
            else:
                # Disable export menu items
                if self.file_menu:
                    self.file_menu.entryconfig(2, state="disabled")  # Export Current Visualization
                if self.tools_menu:
                    self.tools_menu.entryconfig(2, state="disabled")  # Quick Export PNG
                    self.tools_menu.entryconfig(3, state="disabled")  # Quick Export PDF
                    
        except Exception as e:
            self.logger.error(f"Error updating menu state: {e}")
            # Fallback: don't crash the application if menu state update fails
    
    def get_menubar(self) -> tk.Menu:
        """
        Get the menu bar widget.
        
        Returns:
            The menu bar widget
        """
        return self.menubar 