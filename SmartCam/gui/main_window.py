"""
Main window for the Clinic Data Visualizer application.

This module provides the main GUI interface with integrated data loading,
visualization generation, and export functionality.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
from matplotlib.figure import Figure
import pandas as pd
import numpy as np
import os
import sys
import gc
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List, Tuple

from app.utils.timer import Timer
from app.gui.components.scrollable_panel import create_scrollable_text_frame, create_scrollable_tab

# Import configuration
from config.user_config_manager import (
    get_merged_config,
    get_config_section,
    get_config_value,
)
from config.settings import get_settings, get_default_window_sizes

# Import application modules
from app.core.data_loader import DataLoader
from app.core.data_filter import DataFilter
from app.core.data_quality import DataQualityAssessment
from app.core.metrics_calculator import MetricsCalculator
from app.core.data_processor import ClinicDataProcessor
from app.visualization.base_visualizer import VisualizationFactory
from app.visualization import (
    initialize_visualization_system,
    get_visualization_display_name,
)
from app.gui.dialogs.progress_dialog import (
    ProgressDialog,
    show_progress,
    close_progress,
    update_progress,
    set_progress_message,
    is_progress_cancelled,
)

from app.gui.dialogs.splash_screen import SplashScreen
from app.gui.dialogs.error_dialog import show_error_dialog
from app.gui.dialogs.help_dialog import HelpDialog
from app.gui.components.data_comparison import DataComparisonComponent
from app.gui.components.menu_bar import MenuBarComponent
from app.gui.components.viz_controls import VizControls
from app.gui.windows.process_time_table import ProcessTimeTableWindow
from app.utils.logger import get_logger
from app.utils.error_handler import error_handler_decorator, ErrorHandler, handle_error
from app.utils.async_visualization_manager import AsyncVisualizationManager
from app.visualization.export.image_exporter import ImageExporter
from app.gui.components.settings_page import SettingsPage

# Configure logging
logger = get_logger(__name__)

# Get configurations from JSON
CONFIG = get_merged_config()
APP_CONFIG = CONFIG.get("app", {})
VIZ_CONFIG = CONFIG.get("visualization", {})
DATA_CONFIG = CONFIG.get("data", {})
PATH_CONFIG = CONFIG.get("paths", {})
LOG_CONFIG = CONFIG.get("logging", {})
PERF_CONFIG = CONFIG.get("performance", {})


class ClinicDataVisualizer:
    """
    Main application window for the Clinic Data Visualizer.

    This class coordinates all GUI components and handles the overall application
    layout, event handling, and data visualization display.
    """

    def __init__(self, master=None):
        # --- Initialize the Clinic Data Visualizer main window ---

        # Start timer for initialization performance tracking
        timer = Timer()
        timer.start()

        # Create main Tkinter root window (hidden until splash completes)
        self.root = master or tk.Tk()
        self.root.withdraw()  # Hide main window until splash is done

        # Set default theme preference
        self.theme_name = "light"

        # Set up logging and error handling components
        self.logger = get_logger(__name__)
        self.error_handler = ErrorHandler(self.logger)
        self.data_quality_assessor = DataQualityAssessment()
        self.settings = get_settings()

        # Initialize all instance variables and UI state
        self._initialize_variables()

        # Log application startup
        self.logger.info("Application starting up")

        # Show splash screen; will call _complete_initialization when done
        self.logger.info("Showing splash screen...")
        self.splash = SplashScreen(
            self.root, completion_callback=self._complete_initialization
        )

        # Stop timer and display initialization timing
        timer.stop()
        timer.show_timing("Initialisation")

    def _initialize_variables(self):
        """Initialize all instance variables"""
        # Theme and UI state
        self.theme_name = "light"  # Default theme
        self.ui_initialized = False  # Flag to track UI initialization

        # Error state tracking
        self.error_state = False  # Flag to track if an error has occurred
        self.last_error = None  # Store the last error that occurred
        self.error_context = {}  # Store context for the last error
        self.recovery_attempted = False  # Track if recovery has been attempted

        # Core components
        self.data_loader = None
        self.data_filter = None
        self.metrics_calculator = None
        self.processor = None
        self.image_exporter = None
        self.async_viz_manager = None

        # UI components
        self.main_frame = None
        self.left_panel = None
        self.right_panel = None
        self.status_label = None
        self.status_bar_file_label = None
        self.file_label = None
        self.loading_label = None
        self.comparison_component = None
        self.help_dialog = None

        # Initialize tkinter variables early for testing compatibility
        self.selected_service_var = tk.StringVar()
        self.viz_search_var = tk.StringVar()
        self.search_var = tk.StringVar()
        self.patient_id_var = tk.StringVar()
        self.viz_type = tk.StringVar()
        self.selected_patient = tk.StringVar()
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()
        self.start_time_var = tk.StringVar()
        self.end_time_var = tk.StringVar()
        self.service_type_var = tk.StringVar(value="All")
        self.action_var = tk.StringVar(value="All")
        self.patient_search_var = tk.StringVar()
        self.patient_date_var = tk.StringVar()

        # Data storage
        self.all_patient_ids = []
        self.filtered_patient_ids = []
        self.viz_radio_buttons = []

        # Color scheme - Load from theme system with platform detection
        self.colors = self._load_theme_colors()

    def _load_theme_colors(self):
        """
        Load and return the application's color scheme, with platform and config-based theme selection.
        """
        import sys
        from config.settings import get_theme
        from config.app_config import get_feature_config

        feature_config = get_feature_config()
        theme_name = self._choose_theme_name(feature_config)
        theme_config = get_theme(theme_name)
        colors = self._build_color_scheme(theme_name, theme_config)

        self.logger.info(f"Applied theme: {theme_name}")
        return colors

    def _choose_theme_name(self, feature_config):
        """
        Decide which theme to use based on explicit setting, config, and platform.
        """
        theme_name = getattr(self, "theme_name", "light")
        if theme_name == "light":
            if getattr(feature_config, "enable_dark_mode", False):
                return "dark"
            import sys

            if sys.platform == "darwin":
                detected = self._detect_macos_dark_mode()
                if detected == "dark":
                    return "dark"
        return theme_name

    def _detect_macos_dark_mode(self):
        """
        Return 'dark' if macOS system dark mode is enabled, else 'light'.
        """
        try:
            import subprocess

            result = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True,
                text=True,
                timeout=1,
            )
            if result.stdout.strip() == "Dark":
                self.logger.info("Detected macOS dark mode - using dark theme")
                return "dark"
        except Exception:
            pass
        return "light"

    def _build_color_scheme(self, theme_name, theme_config):
        """
        Construct the color scheme dictionary from the theme configuration.
        """
        is_dark = theme_name == "dark"
        return {
            "primary": theme_config.get("accent_color", "#0078d4"),
            "secondary": "#64748b",
            "success": "#059669",
            "warning": "#d97706",
            "error": "#dc2626",
            "foreground": theme_config.get("fg_color", "#000000"),
            "background": theme_config.get("bg_color", "#ffffff"),
            "sidebar": theme_config.get("frame_bg", "#f1f5f9"),
            "card": theme_config.get("entry_bg", "#ffffff"),
            "border": "#404040" if is_dark else "#e2e8f0",
            "text": theme_config.get("fg_color", "#000000"),
            "text_primary": theme_config.get("fg_color", "#000000"),
            "text_secondary": "#a0a0a0" if is_dark else "#64748b",
        }

    def _complete_initialization(self):
        """
        Complete initialization after splash screen is done.

        This method is called by the splash screen when its animation completes,
        ensuring the main GUI only appears after the splash screen is finished.
        """
        # Initialize visualization system
        try:
            initialize_visualization_system()
            self.logger.info("Visualization system initialized")
        except Exception as e:
            self.logger.error(f"Failed to initialize visualization system: {e}")

        # Initialize direct components for better performance and modularity
        self.data_loader = DataLoader()
        self.data_filter = DataFilter()
        self.metrics_calculator = MetricsCalculator()

        # Initialize export functionality
        self.image_exporter = ImageExporter()

        # Initialize async visualization manager
        self.async_viz_manager = AsyncVisualizationManager(max_workers=2)
        self.current_viz_task_id = None

        # Initialize tkinter variables
        self.viz_type = tk.StringVar()
        self.selected_patient = tk.StringVar()
        self.selected_service_var = tk.StringVar()

        # Filter variables
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()
        self.start_time_var = tk.StringVar()
        self.end_time_var = tk.StringVar()
        self.service_type_var = tk.StringVar(value="All")
        self.action_var = tk.StringVar(value="All")
        self.patient_search_var = tk.StringVar()
        self.patient_date_var = tk.StringVar()

        # Additional UI variables that are referenced in the code
        self.search_var = tk.StringVar()
        self.viz_search_var = tk.StringVar()
        self.patient_id_var = tk.StringVar()

        # Data storage
        self.all_patient_ids = []
        self.filtered_patient_ids = []
        self.viz_radio_buttons = []

        # Dataset tracking for export naming
        self.current_dataset_name = None

        # Configure styles and UI
        self._configure_styles_base()
        self._configure_styles()
        self.setup_ui()

        # Mark UI as initialized
        self.ui_initialized = True

        # Show main window and load data
        self.root.deiconify()
        self.try_auto_load()

        self.logger.info("Application initialization complete")

    def try_auto_load(self):
        """Show welcome message and encourage manual data loading"""
        # Skip automatic loading - let users choose their dataset manually
        self.show_status(
            "Welcome to Clinic Data Visualizer! Use Data Source > Load Data to select your dataset.",
            "info",
        )
        return False

    @error_handler_decorator(context={"operation": "data_loading"})
    def load_data_from_file(self, file_path):
        """
        Load data from a file with enhanced error handling, progress feedback, and UI updates.

        This method is organized into clear stages:
        1. Pre-checks (error state, file existence)
        2. Progress dialog setup
        3. Data loading
        4. Data quality assessment
        5. UI updates and finalization

        Key configurations are grouped at the top for easy tweaking.
        """

        # === CONFIGURABLE PARAMETERS ===
        PROGRESS_DIALOG_TITLE = "Loading Data"
        PROGRESS_DIALOG_INIT_MSG = "Preparing to load data..."
        PROGRESS_DIALOG_CAN_CANCEL = True
        PROGRESS_DIALOG_DELAY = 100  # ms
        FILE_LABEL_UPDATE_DELAY = 500  # ms
        QUALITY_REPORT_SHOW_DELAY = 100  # ms
        FINALIZE_LOADING_DELAY = 300  # ms
        LARGE_DATASET_THRESHOLD = 10000  # records

        # === 1. PRE-CHECKS ===
        if self._check_error_state("data_loading"):
            self.show_status(
                "Cannot load data while in error state. Please use recovery option first.",
                "error",
            )
            return False

        if not os.path.exists(file_path):
            error = FileNotFoundError(f"File not found: {file_path}")
            context = {"file_path": file_path, "operation": "file_check"}
            self._set_error_state(error, context)
            return False

        # === 2. PROGRESS DIALOG SETUP ===
        def on_cancel_loading():
            """Handle cancellation of data loading"""
            self.show_status("Data loading cancelled.", "warning")

        from app.gui.dialogs.progress_dialog import (
            show_progress,
            update_progress,
            close_progress,
        )

        # Calculate file size for progress dialog warning
        try:
            file_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        except:
            file_size_mb = None

        progress_dialog = show_progress(
            self.root,
            title=PROGRESS_DIALOG_TITLE,
            message=PROGRESS_DIALOG_INIT_MSG,
            can_cancel=PROGRESS_DIALOG_CAN_CANCEL,
            cancel_callback=on_cancel_loading,
            colors=self.colors,
            file_size_mb=file_size_mb,
        )

        self.root.update()
        self.root.after(PROGRESS_DIALOG_DELAY)  # Ensure dialog is visible

        def on_loading_progress(progress: float, message: str):
            """Update progress dialog with loader progress."""
            if progress_dialog and not progress_dialog.is_closed():
                safe_progress = max(0.01, progress) if progress < 1.0 else progress
                update_progress(safe_progress, message)
                progress_dialog.dialog.update()

        try:
            # === 3. DATA LOADING ===
            self.logger.info(f"Loading data from {file_path}")
            update_progress(0.05, "Starting data loading...")

            success, message = self.data_loader.load_data(
                custom_file=file_path, progress_callback=on_loading_progress
            )

            if not success:
                # --- Data loading failed ---
                error = Exception(f"Data loading failed: {message}")
                context = {
                    "file_path": file_path,
                    "operation": "data_loading",
                    "loader_message": message,
                }
                self._set_error_state(error, context)
                close_progress()
                return False

            # --- Data loaded successfully ---
            update_progress(0.3, "Initializing data processor...")

            # Store the loaded file path for refresh functionality
            self.last_loaded_file = file_path

            # Processor setup
            self.processor = ClinicDataProcessor()
            self.processor.data_loader = self.data_loader
            self.processor.data_filter = self.data_filter
            self.processor.metrics_calculator = self.metrics_calculator

            # Update data filter and dataset name
            self.data_filter.set_data(self.data_loader.get_data())
            self.current_dataset_name = self._extract_dataset_name(file_path)

            # Update file label (immediate and delayed for reliability)
            self.logger.debug(
                f"About to update file label - data_loader has data: {self.data_loader.has_data()}"
            )
            self.update_file_label()
            self.root.after(FILE_LABEL_UPDATE_DELAY, self.update_file_label)

            # === 4. DATA QUALITY ASSESSMENT ===
            self.logger.info("Starting data quality assessment...")
            update_progress(0.5, "Assessing data quality...")

            try:
                quality_report = (
                    self.data_quality_assessor.generate_comprehensive_quality_report(
                        self.data_loader.get_data()
                    )
                )
                self.data_quality_issues = quality_report

                overall_score = quality_report.get("overall_quality_score", 0)
                self.logger.info(
                    f"Data quality assessment complete. Overall score: {overall_score:.1f}%"
                )

                # Quality status mapping
                if overall_score >= 90:
                    quality_status = "Excellent data quality"
                    status_type = "success"
                elif overall_score >= 75:
                    quality_status = "Good data quality"
                    status_type = "info"
                elif overall_score >= 60:
                    quality_status = "Fair data quality - some issues detected"
                    status_type = "warning"
                else:
                    quality_status = "Poor data quality - significant issues detected"
                    status_type = "warning"

                # Show quality report if issues detected
                if overall_score < 85:
                    self.root.after(
                        QUALITY_REPORT_SHOW_DELAY,
                        lambda: self._show_quality_report(quality_report),
                    )

            except Exception as e:
                error_result = self.error_handler.handle_error(
                    e,
                    context={
                        "operation": "quality_assessment",
                        "file_path": file_path,
                    },
                )
                self.data_quality_issues = None
                quality_status = "Quality assessment failed"
                status_type = "error"
                self.logger.error(
                    f"Quality assessment error: {error_result['message']}"
                )

            # === 5. UI UPDATES & FINALIZATION ===
            update_progress(0.7, "Updating UI components...")

            self._update_date_options()
            self._update_time_options()
            self._update_filter_options()
            self._update_simple_patient_dropdown()
            self.data_loaded = True
            self.update_ui_state()
            self.data_loading_complete = True
            self._update_visualization_controls_state(True)

            update_progress(0.9, "Finalizing data loading...")

            # Compose success message
            data_size = len(self.data_loader.get_data())
            success_msg = (
                f"Data loaded successfully from {os.path.basename(file_path)} "
                f"({data_size:,} records). {quality_status}"
            )
            if data_size > LARGE_DATASET_THRESHOLD:
                success_msg += " Select a visualization type and click 'Generate Visualization' to create charts."
            self.show_status(success_msg, status_type)
            self.logger.info(f"Data loaded from {file_path} - {data_size} records")

            # --- Progress bar: show 100% before closing ---
            if progress_dialog and not progress_dialog.is_closed():
                update_progress(1.0, "Loading complete!")
                progress_dialog.dialog.update()
                self.root.after(
                    FINALIZE_LOADING_DELAY,
                    lambda: self._finalize_data_loading(progress_dialog),
                )
            else:
                close_progress()
                self._finalize_data_loading(None)

            return True

        except Exception as e:
            # --- Unexpected error during loading ---
            context = {"file_path": file_path, "operation": "data_loading"}
            self._set_error_state(e, context)
            close_progress()
            return False

    def _finalize_data_loading(self, progress_dialog):
        """Finalize data loading after progress dialog is closed"""
        try:
            # Close progress dialog if it's still open
            if progress_dialog and not progress_dialog.is_closed():
                close_progress()

            # Force update the file label multiple times to ensure it takes
            self.logger.debug("Finalizing data loading - forcing file label updates")
            self.update_file_label()

            # Force UI update
            if hasattr(self, "root"):
                self.root.update()
                self.root.update_idletasks()

                # Schedule additional updates to ensure it takes effect
                self.root.after(100, self.update_file_label)
                self.root.after(1000, self.update_file_label)

            self.logger.info("Data loading finalized - file label updated")

            # Update menu bar after data loading finalized
            if hasattr(self, "menu_bar_component"):
                self.menu_bar_component.update_menu_state(
                    data_loaded=True, visualization_available=False
                )

        except Exception as e:
            self.logger.error(f"Error finalizing data loading: {e}")

    def setup_ui(self, data_loaded=False, visualization_available=False):
        """Set up the main user interface."""
        # Main window configuration from JSON config
        window_title = get_config_value("gui", "window_title", "Clinic Data Visualizer")
        window_size = get_config_value("gui", "window_size", "1920x1080")
        min_window_size = get_config_value("gui", "min_window_size", [1400, 800])

        # Responsive scaling based on screen size
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        if screen_width < 1366:  # Small screens
            scale_factor = 0.7
            # Adjust window size for smaller screens
            if window_size == "1920x1080":
                window_size = "1366x768"
            min_window_size = [int(1000 * scale_factor), int(600 * scale_factor)]
        elif screen_width < 1920:  # Medium screens
            scale_factor = 0.85
            min_window_size = [int(1200 * scale_factor), int(700 * scale_factor)]
        else:  # Large screens
            scale_factor = 1.0

        self.root.title(window_title)
        self.root.geometry(window_size)
        self.root.minsize(min_window_size[0], min_window_size[1])

        # ===== MENU BAR =====
        self._setup_menu_bar_component()
        self.menu_bar_component.update_menu_state(data_loaded, visualization_available)

        # Create main container
        main_container = ttk.Frame(self.root, style="TFrame")
        main_container.pack(fill=tk.BOTH, expand=True)

        # ===== LEFT PANEL (CONTROLS + HEADER) =====
        left_panel = self._setup_left_panel(main_container)

        # ===== RIGHT PANEL (VISUALIZATION) =====
        right_panel = self._setup_right_panel(main_container)

        # ===== STATUS BAR =====
        self._setup_status_bar()

        # Update UI state and file labels now that all components are created
        self.update_ui_state()
        self.update_file_label()  # Ensure file labels are updated after all UI components exist

    def _setup_header(self, parent):
        """Set up the header section with title and version"""
        # Responsive scaling based on screen size
        screen_width = self.root.winfo_screenwidth()
        if screen_width < 1366:  # Small screens
            scale_factor = 0.7
        elif screen_width < 1920:  # Medium screens
            scale_factor = 0.85
        else:  # Large screens
            scale_factor = 1.0

        # Header configuration - responsive scaling
        HEADER_CONFIG = {
            "height": int(50 * scale_factor),  # Scale height
            "title": "Clinic Data Visualizer",
            "version": self._get_dynamic_version(),
            "version": "v2.0.0",
            "title_font": ("Segoe UI", int(12 * scale_factor), "bold"),  # Scale font
            "version_font": ("Segoe UI", int(8 * scale_factor)),  # Scale font
            "title_padding": (
                int(8 * scale_factor),
                int(5 * scale_factor),
            ),  # Scale padding
            "version_padding": (
                0,
                int(8 * scale_factor),
                int(5 * scale_factor),
            ),  # Scale padding
            "show_separator": False,  # Removed separator to save space
            "width": int(380 * scale_factor),  # Scale width
        }

        # Create header frame with fixed width to match left panel
        header = ttk.Frame(
            parent,
            style="Header.TFrame",
            height=HEADER_CONFIG["height"],
            width=HEADER_CONFIG["width"],
        )
        header.pack(fill=tk.X, side=tk.TOP)
        header.pack_propagate(False)  # Prevent frame from shrinking

        # App title
        title_label = ttk.Label(
            header,
            text=HEADER_CONFIG["title"],
            font=HEADER_CONFIG["title_font"],
            foreground=self.colors["primary"],
            background=self.colors["background"],
        )
        title_label.pack(
            side=tk.LEFT,
            padx=HEADER_CONFIG["title_padding"][0],
            pady=HEADER_CONFIG["title_padding"][1],
        )

        # Version label
        version_label = ttk.Label(
            header,
            text=HEADER_CONFIG["version"],
            font=HEADER_CONFIG["version_font"],
            foreground=self.colors["text_secondary"],
            background=self.colors["background"],
        )
        version_label.pack(
            side=tk.LEFT,
            padx=HEADER_CONFIG["version_padding"][:2],
            pady=HEADER_CONFIG["version_padding"][2],
        )

        # Separator below header (optional)
        if HEADER_CONFIG["show_separator"]:
            header_separator = ttk.Separator(parent, orient="horizontal")
            header_separator.pack(fill=tk.X)

        return header

    def _get_dynamic_version(self):
        """Get version text dynamically from git, same as splash screen"""
        try:
            import subprocess

            # Get git commit count as version number
            result = subprocess.run(
                ["git", "rev-list", "--count", "HEAD"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            if result.returncode == 0:
                commit_count = int(result.stdout.strip())
                # After 100 commits, increment minor version
                if commit_count > 100:
                    minor_version = (commit_count // 100) + 1
                    patch_version = commit_count % 100
                    return f"v2.{minor_version}.{patch_version}"
                else:
                    return f"v2.0.{commit_count}"
            else:
                return "v2.0.0"
        except (
            subprocess.TimeoutExpired,
            subprocess.SubprocessError,
            FileNotFoundError,
        ):
            return "v2.0.0"

    def load_data(self):
        """Show data loading dialog with direct component usage"""
        # Get supported formats from config
        supported_formats = get_config_value(
            "data", "supported_formats", [".csv", ".xlsx", ".xls"]
        )

        # Create file types list for dialog
        file_types = []
        if ".csv" in supported_formats:
            file_types.append(("CSV files", "*.csv"))
        if ".xlsx" in supported_formats or ".xls" in supported_formats:
            file_types.append(("Excel files", "*.xlsx *.xls"))
        if supported_formats:
            file_types.append(("All supported", "*.csv *.xlsx *.xls"))
        file_types.append(("All files", "*.*"))

        # Create a simple file dialog instead of using the complex DataLoadingDialog
        file_path = filedialog.askopenfilename(
            title="Select Data File", filetypes=file_types
        )

        if file_path:
            self.load_data_from_file(file_path)

    def get_available_dates(self):
        """Get list of available dates using direct component"""
        if self.data_loader and self.data_loader.has_data():
            self.data_filter.set_data(self.data_loader.get_data())
            return self.data_filter.get_available_dates()
        return []

    def get_service_areas(self):
        """Get list of unique service areas using direct component"""
        if self.data_loader and self.data_loader.has_data():
            self.data_filter.set_data(self.data_loader.get_data())
            return self.data_filter.get_service_areas()
        return []

    def get_service_types(self):
        """Get list of unique service types using direct component"""
        if self.data_loader and self.data_loader.has_data():
            self.data_filter.set_data(self.data_loader.get_data())
            return self.data_filter.get_service_types()
        return []

    def get_actions(self):
        """Get list of unique actions using direct component"""
        if self.data_loader and self.data_loader.has_data():
            self.data_filter.set_data(self.data_loader.get_data())
            return self.data_filter.get_actions()
        return []

    def get_patient_ids(self):
        """Get list of unique patient IDs using direct component"""
        if self.data_loader and self.data_loader.has_data():
            self.data_filter.set_data(self.data_loader.get_data())
            return self.data_filter.get_patient_ids()
        return []

    def get_simple_patient_ids(self):
        """Get list of unique simple patient IDs using direct component"""
        if self.data_loader and self.data_loader.has_data():
            self.data_filter.set_data(self.data_loader.get_data())
            return self.data_filter.get_simple_patient_ids()
        return []

    def apply_filters(self, filters):
        """Apply filters using direct component"""
        if self.data_loader and self.data_loader.has_data():
            self.data_filter.set_data(self.data_loader.get_data())
            return self.data_filter.apply_filters(filters)
        return pd.DataFrame()  # Return empty DataFrame if no data

    def get_data_summary(self):
        """Generate data summary using direct component"""
        if self.data_loader and self.data_loader.has_data():
            return self.metrics_calculator.generate_comprehensive_summary(
                self.data_loader.get_data()
            )
        return {}

    def show_status(self, message, message_type="info"):
        """Show status message in the status bar"""
        if hasattr(self, "status_label"):
            # Color coding for different message types
            colors = {
                "info": self.colors["text"],
                "success": self.colors["success"],
                "warning": self.colors["warning"],
                "error": self.colors["error"],
            }

            color = colors.get(message_type, self.colors["text"])
            self.status_label.config(text=message, foreground=color)

            # Auto-clear non-error messages after 5 seconds
            if message_type != "error":
                self.root.after(5000, lambda: self.status_label.config(text="Ready"))

    def update_file_label(self):
        """Update all file labels to show the current loaded file."""
        # Don't update file labels if we're in an error state
        if self._check_error_state("file_label_update"):
            return

        # Debug logging to understand the issue
        self.logger.debug(
            f"update_file_label called - data_loader exists: {self.data_loader is not None}"
        )
        self.logger.debug(
            f"UI components status - data_controls_file_label exists: {hasattr(self, 'data_controls_file_label') and self.data_controls_file_label is not None}, status_bar_file_label exists: {hasattr(self, 'status_bar_file_label') and self.status_bar_file_label is not None}"
        )

        # Get file information
        file_path = None
        filename = None

        if self.data_loader and self.data_loader.has_data():
            file_path = self.data_loader.get_file_path()
            if file_path:
                import os

                filename = os.path.basename(file_path)
                self.logger.debug(
                    f"update_file_label - has_data: True, file_path: {file_path}"
                )

        # Update file labels using the actual update logic below

        # Handle case where we have a file loaded
        if filename:
            # Truncate long filenames for display
            if len(filename) > 30:
                display_name = filename[:27] + "..."
            else:
                display_name = filename

            # Update data controls file label
            if (
                hasattr(self, "data_controls_file_label")
                and self.data_controls_file_label is not None
            ):
                self.data_controls_file_label.config(
                    text=display_name, foreground=self.colors["text_primary"]
                )
                self.logger.debug("Updated data_controls_file_label")

            # Update status bar file label
            if (
                hasattr(self, "status_bar_file_label")
                and self.status_bar_file_label is not None
            ):
                self.status_bar_file_label.config(
                    text=display_name, foreground=self.colors["text_primary"]
                )
                self.logger.debug("Updated status_bar_file_label")

            # Update status indicator to green (file loaded)
            if (
                hasattr(self, "file_status_indicator")
                and self.file_status_indicator is not None
            ):
                self.file_status_indicator.config(foreground="#059669")  # Green color

            # Update tooltip with full path
            if (
                hasattr(self, "data_controls_file_label")
                and self.data_controls_file_label is not None
            ):
                self._create_tooltip(
                    self.data_controls_file_label,
                    f"Full path: {file_path}\nClick to show full path",
                )

            self.logger.info(f"All file labels updated successfully: {display_name}")

        # Handle case where no file is loaded
        else:
            self.logger.debug("No file loaded, setting 'No file loaded'")
            # Update both file labels to show no file loaded
            if (
                hasattr(self, "data_controls_file_label")
                and self.data_controls_file_label is not None
            ):
                self.data_controls_file_label.config(
                    text="No file loaded", foreground=self.colors["text_secondary"]
                )
            if (
                hasattr(self, "status_bar_file_label")
                and self.status_bar_file_label is not None
            ):
                self.status_bar_file_label.config(
                    text="No file loaded", foreground=self.colors["text_secondary"]
                )
            if (
                hasattr(self, "file_status_indicator")
                and self.file_status_indicator is not None
            ):
                self.file_status_indicator.config(
                    foreground=self.colors["text_secondary"]
                )

    def update_ui_state(self):
        """Update UI state based on data availability using the new data_loader architecture"""
        # Don't update UI if we're in an error state
        if self._check_error_state("ui_update"):
            return

        has_data = self.data_loader is not None and self.data_loader.has_data()

        # Enable/disable quality report button
        if hasattr(self, "quality_btn"):
            self.quality_btn.config(state="normal" if has_data else "disabled")

        # Update data info section visibility
        if hasattr(self, "data_info_frame"):
            if has_data:
                self.data_info_frame.pack(fill=tk.X, pady=(8, 0))
            else:
                self.data_info_frame.pack_forget()

        # Update file label styling based on data status
        if hasattr(self, "file_label") and self.file_label is not None:
            if has_data:
                self.file_label.config(
                    foreground=self.colors["success"], font=("Segoe UI", 9, "bold")
                )
            else:
                self.file_label.config(
                    foreground=self.colors["text_secondary"], font=("Segoe UI", 9)
                )

        self._update_data_control_states()

    def cleanup_and_exit(self):
        """Clean up resources and exit the application gracefully"""
        try:
            # Check if logger exists before using it
            if hasattr(self, "logger") and self.logger:
                self.logger.info("Application shutting down")

            # Set shutdown flag to prevent new operations
            self.shutdown_requested = True

            # Shutdown async visualization manager
            if hasattr(self, "async_viz_manager"):
                self.async_viz_manager.shutdown(wait=False)

            # Close any open progress dialogs
            close_progress()

            # Close any open matplotlib figures
            if hasattr(self, "current_figure") and self.current_figure:
                try:
                    # Check if current_figure is a dictionary (tabbed visualization)
                    if isinstance(self.current_figure, dict):
                        # Close all figures in the dictionary
                        for fig in self.current_figure.values():
                            if fig is not None:
                                plt.close(fig)
                    else:
                        # Close single figure
                        plt.close(self.current_figure)
                except:
                    pass  # Ignore errors during cleanup

            # Close all matplotlib figures
            try:
                plt.close("all")
            except:
                pass  # Ignore errors during cleanup

            # Destroy the root window if it still exists
            if hasattr(self, "root") and self.root is not None:
                try:
                    if self.root.winfo_exists():
                        self.root.quit()  # Exit the mainloop
                        self.root.destroy()
                except:
                    pass  # Ignore errors during cleanup

        except Exception as e:
            # Use print if logger is not available
            if hasattr(self, "logger") and self.logger:
                self.logger.error(f"Error during cleanup: {str(e)}")
            else:
                print(f"Error during cleanup: {str(e)}")
        finally:
            # Only exit if we're not already in the process of shutting down
            if not getattr(self, "_exiting", False):
                self._exiting = True
                import sys

                sys.exit(0)

    def _configure_styles_base(self):
        """Configure base ttk styles"""
        style = ttk.Style()

        # Configure basic styles
        style.configure("TFrame", background=self.colors["background"])
        style.configure(
            "TLabel",
            background=self.colors["background"],
            foreground=self.colors["text"],
        )
        style.configure(
            "TButton",
            padding=(10, 5),
            foreground=self.colors["text"],  # Theme-aware text color
            background=self.colors["card"],
        )  # Theme-aware background

        # Header style
        style.configure(
            "Header.TFrame", background=self.colors["background"], relief="flat"
        )

    def _configure_styles(self):
        """Configure detailed ttk styles for the application"""
        style = ttk.Style()

        # Main frame styles
        style.configure("Main.TFrame", background=self.colors["background"])
        style.configure("Sidebar.TFrame", background=self.colors["sidebar"])
        style.configure("ShadowLeft.TFrame", background=self.colors["background"])
        style.configure("ShadowRight.TFrame", background=self.colors["sidebar"])
        style.configure("Background.TFrame", background=self.colors["background"])
        style.configure("Card.TFrame", background=self.colors["card"])

        # LabelFrame styles
        style.configure(
            "Blue.TLabelframe",
            background=self.colors["sidebar"],
            borderwidth=1,
            relief="solid",
            bordercolor=self.colors["border"],
        )
        style.configure(
            "Blue.TLabelframe.Label",
            background=self.colors["sidebar"],
            foreground=self.colors["primary"],
            font=("Segoe UI", 11, "bold"),
        )

        # Button styles - Theme-aware text colors
        style.configure(
            "Primary.TButton",
            background=self.colors["primary"],
            foreground="white",  # Keep white for primary buttons (high contrast)
            padding=(15, 8),
        )

        style.configure(
            "Accent.TButton",
            font=("Segoe UI", 10, "bold"),
            foreground=self.colors["text"],  # Use theme text color
            background=self.colors["card"],  # Add background for better contrast
        )

        style.configure(
            "Action.TButton",
            font=("Segoe UI", 9),
            foreground=self.colors["text"],  # Use theme text color
            background=self.colors["card"],  # Add background for better contrast
            padding=(8, 4),
        )

        # Custom button color styles for stateful controls - Theme-aware
        style.configure(
            "Red.TButton",
            foreground=self.colors["error"],
            background=self.colors["card"],
        )  # Add background for contrast
        style.configure(
            "Green.TButton",
            foreground=self.colors["success"],
            background=self.colors["card"],
        )  # Add background for contrast
        style.configure(
            "Grey.TButton",
            foreground=self.colors["text_secondary"],
            background=self.colors["card"],
        )  # Add background for contrast

        # Label styles
        style.configure(
            "Title.TLabel",
            font=("Segoe UI", 12, "bold"),
            background=self.colors["background"],
            foreground=self.colors["text"],
        )

        style.configure(
            "Subtitle.TLabel",
            font=("Segoe UI", 10),
            background=self.colors["background"],
            foreground=self.colors["text_secondary"],
        )

        style.configure(
            "SectionTitle.TLabel",
            font=("Segoe UI", 10, "bold"),
            background=self.colors["sidebar"],
            foreground=self.colors["primary"],
        )

        style.configure(
            "Sidebar.TLabel",
            background=self.colors["sidebar"],
            foreground=self.colors["text"],
        )

        # Scrollbar styles
        style.configure("Vertical.TScrollbar", background=self.colors["background"])
        style.configure("Horizontal.TScrollbar", background=self.colors["background"])
        style.configure(
            "Sidebar.Vertical.TScrollbar", background=self.colors["sidebar"]
        )

    def _setup_status_bar(self):
        """Set up the status bar at the bottom of the window"""
        # Create status bar frame
        status_frame = ttk.Frame(self.root, style="TFrame", height=25)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        status_frame.pack_propagate(False)

        # Status label
        self.status_label = ttk.Label(
            status_frame,
            text="Ready",
            font=("Segoe UI", 9),
            background=self.colors["background"],
            foreground=self.colors["text"],
        )
        self.status_label.pack(side=tk.LEFT, padx=10, pady=2)

        # File label in status bar
        self.status_bar_file_label = ttk.Label(
            status_frame,
            text="No file loaded",
            font=("Segoe UI", 9),
            background=self.colors["background"],
            foreground=self.colors["text_secondary"],
        )
        self.status_bar_file_label.pack(side=tk.RIGHT, padx=10, pady=2)

    def _show_quality_report(self, quality_report=None):
        """Show comprehensive data quality report dialog"""
        # If no quality report provided, try to get it from the processor
        if quality_report is None:
            if hasattr(self, "processor") and self.processor:
                try:
                    quality_report = self.processor.get_data_quality_report()
                except Exception as e:
                    self.logger.error(
                        f"Error getting quality report from processor: {str(e)}"
                    )
                    quality_report = None

        # If still no quality report, check if we have stored quality issues
        if (
            not quality_report
            and hasattr(self, "data_quality_issues")
            and self.data_quality_issues
        ):
            quality_report = self.data_quality_issues

        if not quality_report:
            messagebox.showinfo(
                "Quality Report", "No quality assessment data available."
            )
            return

        try:
            # Create quality report window
            quality_window = tk.Toplevel(self.root)
            quality_window.title("Data Quality Assessment Report")
            quality_window.geometry("800x600")
            quality_window.transient(self.root)
            quality_window.grab_set()

            # Create notebook for different quality aspects
            notebook = ttk.Notebook(quality_window)
            notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Overall Summary Tab
            summary_frame, summary_text = create_scrollable_text_frame(notebook)
            notebook.add(summary_frame, text="Overall Summary")

            # Build summary content
            overall_score = quality_report.get("overall_quality_score", 0)
            recommendations = quality_report.get(
                "recommendations", ["No recommendations available"]
            )
            # Ensure all recommendations are strings
            recommendations_text = [f"• {str(rec)}" for rec in recommendations]
            summary_content = f"""Data Quality Assessment Report
Generated: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}

OVERALL QUALITY SCORE: {overall_score:.1f}%

{quality_report.get('summary', 'No summary available')}

RECOMMENDATIONS:
{chr(10).join(recommendations_text)}
"""

            # Insert content into the text widget
            summary_text.insert(tk.END, summary_content)
            summary_text.config(state=tk.DISABLED)

            # Completeness Tab
            if "completeness" in quality_report:
                completeness_frame, completeness_text = create_scrollable_text_frame(
                    notebook
                )
                notebook.add(completeness_frame, text="Completeness")

                completeness_data = quality_report["completeness"]
                completeness_content = f"""COMPLETENESS ANALYSIS

{completeness_data.get('missing_data_summary', 'No completeness data available')}

COLUMN-WISE COMPLETENESS:
"""

                # Add column completeness details
                for column, details in completeness_data.get(
                    "column_completeness", {}
                ).items():
                    completeness_percentage = details.get("completeness_percentage", 0)
                    missing_count = details.get("missing_count", 0)
                    completeness_content += (
                        f"\n{column}: {completeness_percentage:.1f}% complete"
                    )
                    if missing_count > 0:
                        completeness_content += f" ({missing_count} missing values)"

                # Insert content into the text widget
                completeness_text.config(state=tk.NORMAL)
                completeness_text.delete("1.0", tk.END)
                completeness_text.insert(tk.END, completeness_content)
                completeness_text.config(state=tk.DISABLED)
                completeness_text.update_idletasks()

            # Consistency Tab
            if "consistency" in quality_report:
                consistency_frame, consistency_text = create_scrollable_text_frame(
                    notebook
                )
                notebook.add(consistency_frame, text="Consistency")

                consistency_data = quality_report["consistency"]
                consistency_content = f"""CONSISTENCY ANALYSIS

{consistency_data.get('summary', 'No consistency data available')}

FORMAT VALIDATION:
"""

                # Add format validation details
                for field, validation in consistency_data.get(
                    "format_validation", {}
                ).items():
                    validity_pct = validation.get("validity_percentage", 0)
                    total_count = validation.get("total_count", 0)
                    valid_count = validation.get("valid_count", 0)
                    consistency_content += (
                        f"\n{field}: {validity_pct:.1f}% valid format"
                    )
                    if validity_pct < 100:
                        invalid_count = total_count - valid_count
                        consistency_content += f" ({invalid_count} invalid entries)"

                # Insert content into the text widget
                consistency_text.config(state=tk.NORMAL)
                consistency_text.delete("1.0", tk.END)
                consistency_text.insert(tk.END, consistency_content)
                consistency_text.config(state=tk.DISABLED)
                consistency_text.update_idletasks()

            # Uniqueness Tab
            if "uniqueness" in quality_report:
                uniqueness_frame, uniqueness_text = create_scrollable_text_frame(
                    notebook
                )
                notebook.add(uniqueness_frame, text="Uniqueness")

                uniqueness_data = quality_report["uniqueness"]
                uniqueness_content = f"""UNIQUENESS ANALYSIS

{uniqueness_data.get('summary', 'No uniqueness data available')}
"""

                # Insert content into the text widget
                uniqueness_text.config(state=tk.NORMAL)
                uniqueness_text.delete("1.0", tk.END)
                uniqueness_text.insert(tk.END, uniqueness_content)
                uniqueness_text.config(state=tk.DISABLED)
                uniqueness_text.update_idletasks()

            # Close button
            button_frame = ttk.Frame(quality_window)
            button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

            close_btn = ttk.Button(
                button_frame, text="Close", command=quality_window.destroy
            )
            close_btn.pack(side=tk.RIGHT)

            # Export button (for future enhancement)
            export_btn = ttk.Button(
                button_frame,
                text="Export Report",
                command=lambda: self._export_quality_report(quality_report),
            )
            export_btn.pack(side=tk.RIGHT, padx=(0, 10))

        except Exception as e:
            from app.gui.dialogs.error_dialog import ErrorDialog

            # Create and show error dialog with recovery options
            error_dialog = ErrorDialog(
                self,
                e,
                context={
                    "operation": "Quality Report Display",
                    "component": "Main Window",
                    "quality_report_available": "quality_report" in locals(),
                },
                recovery_callback=lambda: (
                    self._show_quality_report()
                    if hasattr(self, "_show_quality_report")
                    else None
                ),
            )
            error_dialog.show()

    """ def _create_scrollable_text_frame(self, parent):
        from app.gui.dialogs.error_dialog import show_error_dialog

""" """
        Create a simple text frame without scrollbars.
        Returns the frame and the text widget.
        Uses error_dialog.py to show user-friendly error dialogs on failure.
        """ """
        try:
            frame = ttk.Frame(parent)
            text_widget = tk.Text(
                frame,
                wrap=tk.NONE,
                font=("Consolas", 9),
                padx=16,
                pady=12,
                spacing1=4,
                spacing2=0,
                spacing3=4,
                bg="#f9f9f9",
                relief=tk.FLAT,
                selectbackground="#0078d4",
                selectforeground="white",
                height=20,  # Minimum height for testing
            )
            text_widget.pack(fill=tk.BOTH, expand=True)
            return frame, text_widget

        except Exception as e:
            # Show error dialog for any error in creating the text frame
            show_error_dialog(
                self,
                e,
                context={
                    "operation": "create_scrollable_text_frame",
                    "component": "Main Window"
                }
            )
            return None, None """

    def _export_quality_report(self, quality_report):
        """Export quality report to file."""
        import os
        from tkinter import filedialog, messagebox

        if (
            not quality_report
            or not isinstance(quality_report, str)
            or not quality_report.strip()
        ):
            messagebox.showwarning("Export", "No quality report available to export.")
            return

        # Ask user for file location
        filetypes = [
            ("Text Files", "*.txt"),
            ("Markdown Files", "*.md"),
            ("All Files", "*.*"),
        ]
        default_filename = "quality_report.txt"
        save_path = filedialog.asksaveasfilename(
            title="Export Quality Report",
            defaultextension=".txt",
            filetypes=filetypes,
            initialfile=default_filename,
        )

        if not save_path:
            return  # User cancelled

        try:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(quality_report)
            messagebox.showinfo(
                "Export",
                f"Quality report exported successfully:\n{os.path.basename(save_path)}",
            )
        except Exception as e:
            messagebox.showerror(
                "Export Error", f"Failed to export quality report:\n{e}"
            )

    @error_handler_decorator(context={"operation": "export_visualization"})
    def export_current_visualization(self):
        """Export the current visualization with format selection dialog"""
        from app.gui.dialogs.error_dialog import show_error_dialog

        if not self.current_figure:
            self.show_status("No visualization to export", "warning")
            return

        try:
            # Get default export settings from config
            default_format = get_config_value("export", "default_format", "PNG")
            default_dpi = get_config_value("export", "default_dpi", 300)
            include_timestamp = get_config_value("export", "include_timestamp", True)
            filename_prefix = get_config_value(
                "export", "filename_prefix", "clinic_analysis"
            )

            # Show export dialog
            from app.visualization.export.image_exporter import ExportDialog

            export_dialog = ExportDialog(self.root)
            export_settings = export_dialog.show_export_dialog()

            if not export_settings:
                return  # User cancelled

            # Extract settings with config defaults
            format_type = export_settings.get("format", default_format)
            filename = export_settings.get("filename")
            custom_settings = export_settings.get("settings", {})

            # Apply config defaults to custom settings
            if "dpi" not in custom_settings:
                custom_settings["dpi"] = default_dpi

            # Get current visualization type and dataset name for naming
            viz_type = self.viz_type.get() or "visualization"
            dataset_name = self.current_dataset_name or "dataset"

            # Export the figure
            success, message, filepath = self.image_exporter.export_figure(
                self.current_figure,
                filename,
                format_type,
                viz_type=viz_type,
                dataset_name=dataset_name,
                **custom_settings,
            )

            if success:
                self.show_status(
                    f"Visualization exported successfully to {os.path.basename(filepath)}",
                    "success",
                )
                self.logger.info(f"Visualization exported: {filepath}")
            else:
                # Use error dialog for export errors
                show_error_dialog(
                    self.root,
                    Exception(f"Export failed: {message}"),
                    context={
                        "operation": "export_visualization",
                        "format": format_type,
                        "filename": filename,
                    },
                )
                self.show_status(f"Export failed: {message}", "error")

        except Exception as e:
            # Show error dialog for unexpected exceptions
            show_error_dialog(
                self.root, e, context={"operation": "export_visualization"}
            )
            self.show_status("An unexpected error occurred during export.", "error")

    @error_handler_decorator(context={"operation": "quick_export"})
    def quick_export_visualization(self, format_type):
        """Quick export the current visualization to specified format"""
        if not self.current_figure:
            self.show_status("No visualization to export", "warning")
            return

        # Get export settings from config
        default_dpi = get_config_value("export", "default_dpi", 300)
        include_timestamp = get_config_value("export", "include_timestamp", True)
        filename_prefix = get_config_value(
            "export", "filename_prefix", "clinic_analysis"
        )

        # Generate default filename using visualization-dataset naming convention
        viz_type = self.viz_type.get() or "visualization"
        dataset_name = self.current_dataset_name or "dataset"
        default_filename = f"{viz_type}-{dataset_name}"

        # Export the figure with config settings
        success, message, filepath = self.image_exporter.export_figure(
            self.current_figure,
            default_filename,
            format_type,
            viz_type=viz_type,
            dataset_name=dataset_name,
            dpi=default_dpi,
        )

        if success:
            self.show_status(
                f"Exported as {format_type}: {os.path.basename(filepath)}", "success"
            )
            self.logger.info(f"Quick export successful: {filepath}")
        else:
            error_result = handle_error(
                Exception(f"Quick export failed: {message}"),
                context={"format": format_type, "filename": default_filename},
            )
            self.show_status(error_result["message"], "error")


    def _setup_menu_bar_component(self):
        """Set up the menu bar using the MenuBarComponent"""
        self.menu_bar_component = MenuBarComponent(
            parent=self.root,
            data_quality_assessor=self.data_quality_assessor,
            on_load_data=self.load_data,
            on_export_visualization=self.export_current_visualization,
            on_show_quality_report=self._show_quality_report_menu,
            on_show_settings=self.show_settings_dialog,
            on_cleanup_exit=self.cleanup_and_exit,
            on_show_data_summary=self.show_data_summary,
            on_switch_theme=self._switch_theme,
            on_show_process_time_table=self.show_process_time_table,
            on_generate_visualization=self.generate_visualization,
            on_show_journey_config=self._show_journey_config_dialog,
            on_quick_export_png=lambda: self.quick_export_visualization("PNG"),
            on_quick_export_pdf=lambda: self.quick_export_visualization("PDF"),
            on_show_about=self._show_about_dialog,
            on_show_shortcuts=self._show_shortcuts_dialog,
            on_show_help=self._show_help_dialog,
            on_refresh_data=self.refresh_data,
            on_close_current_tab=self.close_current_tab,
            on_switch_to_tab=self.switch_to_tab,
        )

    def _show_quality_report_menu(self):
        """Show quality report from menu"""
        if not self.processor or not self.processor.has_data():
            messagebox.showwarning(
                "No Data", "Please load data first to generate a quality report."
            )
            return

        # Use the same logic as show_quality_report method
        self.show_quality_report()

    def _show_about_dialog(self):
        """Show about dialog with enhanced information and styling"""
        from config.app_config import get_app_config
        from config.visualization_config import get_viz_config

        app_config = get_app_config()
        viz_config = get_viz_config()

        about_text = f"""🎯 {app_config.app_name} v{app_config.app_version if hasattr(app_config, 'app_version') else '2.0.0'}

{app_config.app_description}

✨ Key Features:
• Advanced data loading and quality assessment
• Multiple visualization types with interactive charts
• Real-time filtering and data exploration
• Export capabilities (PNG, PDF, CSV)
• Customizable themes and styling
• Performance optimized for large datasets

🔧 Technical Highlights:
• Modular architecture for better maintainability
• Configurable visualization settings
• Memory-efficient data processing
• Cross-platform compatibility

Environment: {app_config.environment.title()}
Debug Mode: {'Enabled' if app_config.debug_mode else 'Disabled'}
Chart Engine: {viz_config.chart_engine if hasattr(viz_config, 'chart_engine') else 'Matplotlib'}"""

        messagebox.showinfo("About Clinic Data Visualizer", about_text)

    def _show_help_dialog(self):
        """Show comprehensive help dialog"""
        try:
            # Create help dialog if it doesn't exist or is closed
            if self.help_dialog is None or not self.help_dialog.is_open():
                self.help_dialog = HelpDialog(self.root)

            # Show the help dialog
            self.help_dialog.show()

            self.logger.info("Help dialog opened successfully")

        except Exception as e:
            self.logger.error(f"Error showing help dialog: {e}")
            messagebox.showerror("Error", f"Failed to open help dialog: {str(e)}")

    def _show_shortcuts_dialog(self):
        """Show keyboard shortcuts dialog with enhanced formatting and emojis"""
        shortcuts_text = """Keyboard Shortcuts

File Operations:
   Ctrl+O    Load Data
   Ctrl+E    Export Current Visualization

View Operations:
   Ctrl+S    Show Data Summary
   Ctrl+G    Generate Visualization
   Ctrl+D    Data Quality Assessment
   Ctrl+Q    Exit Application

Export Tools:
   Ctrl+P    Quick Export PNG
   Ctrl+F    Quick Export PDF

Navigation:
   Mouse Wheel    Scroll through controls and visualizations
   Click & Drag   Pan around visualizations (when zoomed)

Tips:
   • Use Tab to navigate between controls
   • Right-click on visualizations for context menus
   • Double-click to reset zoom levels"""

        messagebox.showinfo("Keyboard Shortcuts", shortcuts_text)

    def refresh_data(self):
        """Refresh/reload the current data file (F5 shortcut)"""
        if hasattr(self, 'last_loaded_file') and self.last_loaded_file:
            try:
                self.logger.info(f"Refreshing data from {self.last_loaded_file}")
                self.load_data_from_file(self.last_loaded_file)
                self.show_status("Data refreshed successfully", "success")
            except Exception as e:
                self.logger.error(f"Error refreshing data: {e}")
                self.show_status(f"Error refreshing data: {str(e)}", "error")
        else:
            # No file loaded yet, just open file dialog
            self.load_data()

    def close_current_tab(self):
        """Close the currently selected tab (Ctrl+W shortcut)"""
        try:
            if hasattr(self, 'vis_notebook') and self.vis_notebook:
                current_tab = self.vis_notebook.select()
                if current_tab:
                    # Don't close the welcome tab
                    tab_text = self.vis_notebook.tab(current_tab, "text")
                    if tab_text.lower() != "welcome":
                        self.vis_notebook.forget(current_tab)
                        self.logger.info(f"Closed tab: {tab_text}")
                        self.show_status(f"Closed tab: {tab_text}", "info")
                        
                        # If no tabs left, show welcome tab
                        if len(self.vis_notebook.tabs()) == 0:
                            self._show_welcome_placeholder()
        except Exception as e:
            self.logger.error(f"Error closing tab: {e}")

    def switch_to_tab(self, tab_index):
        """Switch to tab by index (Ctrl+1, Ctrl+2, etc. shortcuts)"""
        try:
            if hasattr(self, 'vis_notebook') and self.vis_notebook:
                tabs = self.vis_notebook.tabs()
                if 0 <= tab_index < len(tabs):
                    self.vis_notebook.select(tabs[tab_index])
                    tab_text = self.vis_notebook.tab(tabs[tab_index], "text")
                    self.logger.info(f"Switched to tab {tab_index + 1}: {tab_text}")
        except Exception as e:
            self.logger.error(f"Error switching to tab {tab_index}: {e}")

    def show_settings_shortcut(self):
        """Open settings dialog (Ctrl+, shortcut)"""
        self.show_settings_dialog()

    def show_shortcuts_shortcut(self):
        """Show shortcuts dialog (Ctrl+H shortcut)"""
        self._show_shortcuts_dialog()

    def _switch_theme(self, theme_name):
        """
        Switch to a different theme and refresh the UI.

        Args:
            theme_name (str): Name of the theme to switch to ('light', 'dark')
        """
        try:
            # Only allow 'light' and 'dark'
            if theme_name not in ("light", "dark"):
                theme_name = "light"

            # Update theme name and reload colors
            self.theme_name = theme_name
            self.colors = self._load_theme_colors()

            # Reconfigure all styles with new colors
            self._configure_styles_base()
            self._configure_styles()

            # Update the root window background
            if hasattr(self, "root") and self.root is not None:
                self.root.configure(bg=self.colors["background"])

            # Only refresh UI colors if the UI has been initialized
            if self._is_ui_ready():
                # Refresh all UI elements with new colors
                self._refresh_ui_colors()
                # Schedule an additional refresh after a short delay to ensure all widgets are updated
                self.root.after(100, self._refresh_ui_colors)
            else:
                self.logger.info(
                    "UI not ready yet - theme colors will be applied when UI initializes"
                )

            # Show success message
            self.show_status(f"Theme switched to {theme_name.title()}", "success")
            self.logger.info(f"Theme switched to: {theme_name}")

        except Exception as e:
            self.logger.error(f"Error switching theme: {e}")
            self.show_status("Error switching theme", "error")

    def _refresh_ui_colors(self):
        """Refresh all UI elements with the current theme colors."""
        try:
            # Update status bar
            if hasattr(self, "status_label") and self.status_label is not None:
                self.status_label.configure(
                    background=self.colors["background"], foreground=self.colors["text"]
                )

            if (
                hasattr(self, "status_bar_file_label")
                and self.status_bar_file_label is not None
            ):
                self.status_bar_file_label.configure(
                    background=self.colors["background"],
                    foreground=self.colors["text_secondary"],
                )

            # Update file label if it exists
            if hasattr(self, "file_label") and self.file_label is not None:
                self.file_label.configure(
                    background=self.colors["background"], foreground=self.colors["text"]
                )

            # Update loading label if it exists
            if hasattr(self, "loading_label") and self.loading_label is not None:
                self.loading_label.configure(
                    background=self.colors["background"], foreground=self.colors["text"]
                )

            # Update comparison component if it exists
            if (
                hasattr(self, "comparison_component")
                and self.comparison_component is not None
            ):
                self.comparison_component.configure(
                    background=self.colors["background"]
                )

            # Update main panels
            if hasattr(self, "main_frame") and self.main_frame is not None:
                self.main_frame.configure(background=self.colors["background"])

            if hasattr(self, "left_panel") and self.left_panel is not None:
                self.left_panel.configure(background=self.colors["sidebar"])

            if hasattr(self, "right_panel") and self.right_panel is not None:
                self.right_panel.configure(background=self.colors["background"])

            # Update visualization controls frame
            if (
                hasattr(self, "viz_options_frame")
                and self.viz_options_frame is not None
            ):
                self.viz_options_frame.configure(background=self.colors["sidebar"])

            # Update all radio buttons in visualization controls
            if (
                hasattr(self, "viz_radio_buttons")
                and self.viz_radio_buttons is not None
            ):
                for rb_info in self.viz_radio_buttons:
                    if "widget" in rb_info and rb_info["widget"] is not None:
                        rb_info["widget"].configure(background=self.colors["sidebar"])

            # Update data controls file label
            if (
                hasattr(self, "data_controls_file_label")
                and self.data_controls_file_label is not None
            ):
                self.data_controls_file_label.configure(
                    background=self.colors["sidebar"]
                )

            # Update file status indicator
            if (
                hasattr(self, "file_status_indicator")
                and self.file_status_indicator is not None
            ):
                self.file_status_indicator.configure(background=self.colors["sidebar"])

            # Update title label
            if hasattr(self, "title_label") and self.title_label is not None:
                self.title_label.configure(
                    background=self.colors["card"], foreground=self.colors["primary"]
                )

            # Update placeholder label
            if (
                hasattr(self, "placeholder_label")
                and self.placeholder_label is not None
            ):
                self.placeholder_label.configure(
                    background=self.colors["card"],
                    foreground=self.colors["text_secondary"],
                )

            # Only recursively update widgets if the root exists and UI is initialized
            if hasattr(self, "root") and self.root is not None:
                self._update_widget_colors_recursive(self.root)

            # Force update of all widgets
            if hasattr(self, "root") and self.root is not None:
                self.root.update_idletasks()
                self.root.update()  # Force immediate update

            # Log the theme change
            self.logger.info(f"UI colors refreshed for theme: {self.theme_name}")

        except Exception as e:
            self.logger.error(f"Error refreshing UI colors: {e}")

    def _update_widget_colors_recursive(self, widget):
        """Recursively update colors for all child widgets."""
        try:
            # Check if widget exists and has configure method
            if widget is None or not hasattr(widget, "configure"):
                return

            widget_type = widget.winfo_class()

            # Update based on widget type
            if widget_type in ["TFrame", "Frame"]:
                widget.configure(background=self.colors["background"])
            elif widget_type in ["TLabel", "Label"]:
                widget.configure(
                    background=self.colors["background"], foreground=self.colors["text"]
                )
            elif widget_type in ["TButton", "Button"]:
                widget.configure(
                    background=self.colors["card"], foreground=self.colors["text"]
                )
            elif widget_type in ["TEntry", "Entry"]:
                widget.configure(
                    background=self.colors["card"], foreground=self.colors["text"]
                )
            elif widget_type in ["TCombobox", "Combobox"]:
                widget.configure(
                    background=self.colors["card"], foreground=self.colors["text"]
                )
            elif widget_type in ["TRadiobutton", "Radiobutton"]:
                widget.configure(
                    background=self.colors["sidebar"], foreground=self.colors["text"]
                )
            elif widget_type in ["TCheckbutton", "Checkbutton"]:
                widget.configure(
                    background=self.colors["sidebar"], foreground=self.colors["text"]
                )
            elif widget_type in ["TSeparator", "Separator"]:
                # Separators don't need color updates
                pass
            elif widget_type in ["TNotebook", "Notebook"]:
                widget.configure(background=self.colors["background"])
            elif widget_type in ["TScrollbar", "Scrollbar"]:
                widget.configure(background=self.colors["background"])

            # Recursively update all children
            for child in widget.winfo_children():
                self._update_widget_colors_recursive(child)

        except Exception as e:
            # Silently ignore errors for individual widgets
            pass

    def _show_journey_config_dialog(self):
        """Show journey configuration in the settings page (Journey tab)."""
        self.show_settings_dialog(tab_name="Journey")

    def _on_journey_config_changed(self, config):
        """Handle journey configuration changes."""
        try:
            self.logger.info(f"Journey configuration changed: {config}")

            # Update journey configuration status display
            self._update_journey_config_status()

            # If data is loaded, ask user if they want to reload
            if self.data_loader and self.data_loader.has_data():
                result = messagebox.askyesno(
                    "Reload Data",
                    "Journey configuration has been updated.\n\n"
                    "To apply the new settings to your current data, you need to reload the file.\n\n"
                    "Would you like to reload the current data file now?",
                )

                if result and self.data_loader.get_file_path():
                    # Reload the current file with new configuration
                    self.load_data_from_file(self.data_loader.get_file_path())
                else:
                    self.show_status(
                        "Journey configuration updated. Reload data to apply changes.",
                        "info",
                    )
            else:
                self.show_status("Journey configuration updated.", "success")

        except Exception as e:
            self.logger.error(f"Error handling journey config change: {e}")
            self.show_status("Error applying journey configuration.", "error")

    def _on_settings_config_changed(self, config):
        """Handle settings configuration changes."""
        try:
            self.logger.info(f"Settings configuration changed: {list(config.keys())}")

            # Check if data-related configuration changed
            data_sections = [
                "data",
                "data_quality",
                "journey",
                "consultation",
                "columns",
                "processing",
            ]
            data_changed = any(section in config for section in data_sections)

            if data_changed:
                # Update journey configuration status display
                self._update_journey_config_status()

                # If data is loaded, ask user if they want to reload
                if self.data_loader and self.data_loader.has_data():
                    result = messagebox.askyesno(
                        "Reload Data",
                        "Data configuration has been updated.\n\n"
                        "To apply the new settings to your current data, you need to reload the file.\n\n"
                        "Would you like to reload the current data file now?",
                    )

                    if result and self.data_loader.get_file_path():
                        # Reload the current file with new configuration
                        self.load_data_from_file(self.data_loader.get_file_path())
                    else:
                        self.show_status(
                            "Data configuration updated. Reload data to apply changes.",
                            "info",
                        )
                else:
                    self.show_status("Data configuration updated.", "success")

        except Exception as e:
            self.logger.error(f"Error handling settings config change: {e}")
            self.show_status("Error applying configuration changes.", "error")



    def _on_viz_controls_change(self, event_type, value):
        """Handle changes from VizControls component"""
        if event_type == 'viz_type_selected':
            self.viz_type.set(value)
            self.on_viz_type_selected()
        elif event_type == 'patient_selected':
            # Auto-generate visualization when patient is selected
            self.root.after(100, self.generate_visualization)

    def show_patient_journey_controls(self):
        """Show patient journey controls and hide filter controls"""
        if hasattr(self, "viz_controls") and self.viz_controls is not None:
            self.viz_controls.show_patient_controls(True)
        if hasattr(self, "filter_frame") and self.filter_frame is not None:
            self.filter_frame.pack_forget()

    def show_filter_controls(self):
        """Show filter controls and hide patient journey controls"""
        if hasattr(self, "filter_frame") and self.filter_frame is not None:
            self.filter_frame.pack(fill=tk.X, pady=(0, 15), padx=0)
        if hasattr(self, "viz_controls") and self.viz_controls is not None:
            self.viz_controls.show_patient_controls(False)

    def on_viz_type_selected(self):
        """Handle visualization type selection"""
        current_viz = self.viz_type.get()

        # Show/hide patient selection based on visualization type
        if current_viz in ["patient_journey"]:
            self.show_patient_journey_controls()
        else:
            self.show_filter_controls()

        # Show/hide service selector for transition analysis
        if current_viz == "service_transitions":
            self.service_selector_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
            # Update service options if data is available
            if (
                self.processor
                and hasattr(self.processor, "data_loader")
                and self.processor.data_loader.get_data() is not None
            ):
                data = self.processor.data_loader.get_data()
                if "Service Type" in data.columns:
                    service_types = sorted(data["Service Type"].dropna().unique())
                    self.service_selector["values"] = service_types
        else:
            self.service_selector_frame.pack_forget()

        # Handle data comparison visualization type
        if current_viz == "data_comparison":
            self._show_data_comparison_interface()
        else:
            # Only auto-generate visualization if explicitly requested (not during initial data loading)
            # This prevents hanging when loading large datasets
            if (
                self.processor
                and hasattr(self.processor, "data_loader")
                and self.processor.data_loader.get_data() is not None
                and getattr(self, "data_loading_complete", False)
            ):
                # Small delay to ensure UI updates are complete
                self.root.after(100, self.generate_visualization)

    def _filter_visualizations(self, *args):
        """Filter visualization options based on search text and rearrange results neatly"""
        search_text = self.viz_search_var.get().lower()

        # Track which categories have visible items
        visible_categories = set()

        # First pass: determine visibility and collect visible categories
        for rb_info in self.viz_radio_buttons:
            widget = rb_info["widget"]
            text = rb_info["text"]
            value = rb_info["value"]
            category_frame = rb_info["category_frame"]

            # Check if this item matches the search
            matches_search = (
                not search_text
                or search_text in text.lower()
                or search_text in value.lower()
            )

            if matches_search:
                widget.pack(side=tk.LEFT, anchor=tk.W, fill=tk.X, padx=(0, 10))
                visible_categories.add(category_frame)
            else:
                widget.pack_forget()

        # Second pass: show/hide category frames and arrange visible items neatly
        for rb_info in self.viz_radio_buttons:
            category_frame = rb_info["category_frame"]

            if category_frame in visible_categories:
                # Show category frame with proper spacing
                category_frame.pack(fill=tk.X, anchor=tk.W, padx=(10, 0), pady=(5, 0))

                # Rearrange visible children within the category for better layout
                visible_children = [
                    child
                    for child in category_frame.winfo_children()
                    if child.winfo_viewable()
                ]

                # Clear and repack visible children with consistent spacing
                for child in visible_children:
                    child.pack_forget()

                for i, child in enumerate(visible_children):
                    child.pack(
                        side=tk.LEFT,
                        anchor=tk.W,
                        fill=tk.X,
                        padx=(0, 15 if i < len(visible_children) - 1 else 0),
                    )
            else:
                # Hide category frame if no visible children
                category_frame.pack_forget()

        # Update the scrollable frame to ensure proper scrolling
        if hasattr(self, "viz_scrollable_frame"):
            self.viz_scrollable_frame.update_idletasks()

        # Force a complete redraw of the visualization panel when search is cleared
        if not search_text:
            # Schedule a complete refresh of the visualization panel
            self.root.after(50, self._refresh_visualization_panel)

    def _refresh_visualization_panel(self):
        """Force a complete redraw of the visualization panel"""
        if hasattr(self, "viz_scrollable_frame"):
            self.viz_scrollable_frame.update_idletasks()
            self.viz_scrollable_frame.update()

    def _setup_data_controls(self, parent):
        """Set up the Data Controls section of the UI with a modern card layout."""
        # Main frame with card style
        control_frame = self._create_section_frame(parent, "Data Controls", (16, 12))
        control_frame.pack(fill=tk.X, pady=(0, 15), padx=0)

        # File info section
        self._setup_file_info_section(control_frame)

        # Action buttons section
        self._setup_action_buttons_section(control_frame)

        # Call to update button states/colors initially
        self._update_data_control_states()
        self.update_file_label()

    def _create_section_frame(self, parent, title, padding):
        """Create a consistent section frame with blue styling."""
        return ttk.LabelFrame(
            parent, text=title, padding=padding, style="Blue.TLabelframe"
        )

    def _setup_file_info_section(self, parent):
        """Set up the file information display section."""
        # File info row
        file_info_row = ttk.Frame(parent)
        file_info_row.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(
            file_info_row,
            text="Current File:",
            font=("Segoe UI", 10, "bold"),
            foreground=self.colors["primary"],
            background=self.colors["sidebar"],
        ).pack(side=tk.LEFT, padx=(0, 8))

        # Create a frame to hold the file label and status indicator
        file_display_frame = ttk.Frame(file_info_row)
        file_display_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # File label with improved styling and functionality
        self.data_controls_file_label = ttk.Label(
            file_display_frame,
            text="No file loaded",
            background=self.colors["sidebar"],
            foreground=self.colors["text_secondary"],
            font=("Segoe UI", 10),
            wraplength=220,
            justify=tk.LEFT,
            cursor="hand2",
        )
        self.data_controls_file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Status indicator (small colored dot)
        self.file_status_indicator = ttk.Label(
            file_display_frame,
            text="●",
            font=("Segoe UI", 12),
            foreground=self.colors["text_secondary"],
            background=self.colors["sidebar"],
        )
        self.file_status_indicator.pack(side=tk.RIGHT, padx=(5, 0))

        # Enhanced tooltip with more information
        self._create_tooltip(
            self.data_controls_file_label, "Click to show full file path"
        )
        self.data_controls_file_label.bind("<Button-1>", self._show_full_file_path)

        # Add a small refresh button next to the file label for debugging
        refresh_btn = ttk.Button(
            file_display_frame, text="🔄", command=self.update_file_label, width=3
        )
        refresh_btn.pack(side=tk.RIGHT, padx=(5, 0))
        self._create_tooltip(refresh_btn, "Refresh file label display")

    def _setup_action_buttons_section(self, parent):
        """Set up the action buttons section with consistent styling."""
        # Action buttons row - Fixed sizing
        btn_row = ttk.Frame(parent)
        btn_row.pack(fill=tk.X, pady=(0, 5))

        # Configure grid weights for equal button distribution
        for i in range(3):
            btn_row.columnconfigure(i, weight=1)

        # Define button configurations
        button_configs = [
            {
                "text": "Load Data",
                "command": self.load_data,
                "style": "Primary.TButton",
                "tooltip": "Load a CSV or Excel file",
                "state": "normal"
            },
            {
                "text": "Summary",
                "command": self.show_data_summary,
                "style": "Grey.TButton",
                "tooltip": "Show data summary",
                "state": "disabled"
            },
            {
                "text": "Quality",
                "command": self.show_quality_report,
                "style": "Grey.TButton",
                "tooltip": "Show data quality report",
                "state": "disabled"
            }
        ]

        # Create buttons
        for i, config in enumerate(button_configs):
            button = ttk.Button(
                btn_row,
                text=config["text"],
                command=config["command"],
                style=config["style"],
                cursor="hand2",
                state=config["state"]
            )
            
            # Grid positioning with consistent spacing
            padx = (0, 4) if i == 0 else (2, 4) if i == 1 else (4, 0)
            button.grid(row=0, column=i, sticky="ew", padx=padx, pady=4)
            self._create_tooltip(button, config["tooltip"])
            
            # Store button references
            if i == 0:
                self.load_btn = button
            elif i == 1:
                self.summary_btn = button
            elif i == 2:
                self.quality_btn = button

    def _update_data_control_states(self):
        """Update the color and state of Load Data, Summary, and Quality buttons based on data status and quality."""
        has_data = self.data_loader is not None and self.data_loader.has_data()
        # Data quality issues: if present and overall_quality_score < 85, mark as issues
        data_issues = False
        if (
            has_data
            and hasattr(self, "data_quality_issues")
            and self.data_quality_issues
        ):
            score = self.data_quality_issues.get("overall_quality_score", 100)
            data_issues = score < 85
        # Load Data button color
        if has_data:
            self.load_btn.config(style="Green.TButton")  # dark green
        else:
            self.load_btn.config(style="Red.TButton")  # red
        # Summary and Quality buttons
        if has_data:
            if data_issues:
                self.summary_btn.config(state="normal", style="Red.TButton")  # red
                self.quality_btn.config(state="normal", style="Red.TButton")  # red
            else:
                self.summary_btn.config(
                    state="normal", style="Green.TButton"
                )  # dark green
                self.quality_btn.config(
                    state="normal", style="Green.TButton"
                )  # dark green
        else:
            self.summary_btn.config(state="disabled", style="Grey.TButton")  # grey
            self.quality_btn.config(state="disabled", style="Grey.TButton")  # grey

        # Update visualization controls state
        self._update_visualization_controls_state(has_data)

        # Always update file label with current file
        self.logger.debug("_update_data_control_states called - updating file label")
        self.update_file_label()

        # Update journey configuration status
        self._update_journey_config_status()

    def _update_visualization_controls_state(self, has_data):
        """Update the state of visualization controls based on data availability."""
        try:
            self.logger.debug(f"Updating visualization controls state - has_data: {has_data}")
            
            # Update VizControls component if it exists
            if hasattr(self, "viz_controls") and self.viz_controls is not None:
                self.viz_controls.set_enabled(has_data)
                self.logger.debug(f"Updated VizControls enabled state: {has_data}")
            else:
                self.logger.warning("VizControls component not found or not initialized")
            
            # Also update the old viz_radio_buttons for backward compatibility
            if hasattr(self, "viz_radio_buttons") and self.viz_radio_buttons:
                self.logger.debug(f"Found {len(self.viz_radio_buttons)} old viz_radio_buttons")
                for rb_info in self.viz_radio_buttons:
                    if "widget" in rb_info and rb_info["widget"] is not None:
                        widget = rb_info["widget"]
                        if has_data:
                            widget.config(state="normal")
                        else:
                            widget.config(state="disabled")
            else:
                self.logger.debug("No old viz_radio_buttons found")

            # Update search entry (old method - kept for backward compatibility)
            if hasattr(self, "viz_search_var"):
                search_entry = None
                # Find the search entry widget
                if hasattr(self, "viz_options_frame") and self.viz_options_frame:
                    for child in self.viz_options_frame.winfo_children():
                        if hasattr(child, "winfo_children"):
                            for grandchild in child.winfo_children():
                                if hasattr(grandchild, "winfo_children"):
                                    for great_grandchild in grandchild.winfo_children():
                                        if isinstance(great_grandchild, ttk.Entry):
                                            search_entry = great_grandchild
                                            break
                                    if search_entry:
                                        break
                                if search_entry:
                                    break
                        if search_entry:
                            break

                if search_entry:
                    if has_data:
                        search_entry.config(state="normal")
                    else:
                        search_entry.config(state="disabled")

        except Exception as e:
            self.logger.error(f"Error updating visualization controls state: {e}")

    def _update_journey_config_status(self):
        """Update the journey configuration status display."""
        if not self.data_loader:
            return

        try:
            config = self.data_loader.get_journey_config()
            enabled = config.get("enabled", True)

            # Update status indicator color based on configuration
            if hasattr(self, "file_status_indicator"):
                if enabled:
                    self.file_status_indicator.config(
                        text="●", foreground=self.colors["success"]
                    )
                else:
                    self.file_status_indicator.config(
                        text="●", foreground=self.colors["text_secondary"]
                    )

        except Exception as e:
            self.logger.error(f"Error updating journey config status: {e}")

    def _show_full_file_path(self, event=None):
        """Show a popup with the full file path when the file label is clicked"""
        # Check if we have a data_loader and there's data loaded
        if not self.data_loader or not self.data_loader.get_file_path():
            messagebox.showinfo("File Information", "No file currently loaded.")
            return

        # Show a messagebox with the full file path
        file_path = self.data_loader.get_file_path()
        messagebox.showinfo("File Information", f"Full path: {file_path}")

    def _extract_dataset_name(self, file_path):
        """Extract dataset name from file path for export naming"""
        if not file_path:
            return "dataset"

        # Get filename without extension
        filename = os.path.basename(file_path)
        dataset_name = os.path.splitext(filename)[0]

        # Remove common suffixes like "_ANONYMISED"
        dataset_name = dataset_name.replace("_ANONYMISED", "")
        dataset_name = dataset_name.replace("_anonymised", "")

        return dataset_name

    def _setup_filter_controls(self, parent):
        """Set up the Filters section of the UI with grouped, grid-aligned layout, fitting within left_panel."""
        self.filter_frame = self._create_section_frame(parent, "🔎 Analysis Filters", (12, 8))
        self.filter_frame.pack(fill=tk.X, pady=(0, 12), padx=0)
        
        if hasattr(self, "patient_frame") and self.patient_frame is not None:
            self.patient_frame.pack_forget()

        # Use a frame for grid layout with proper constraints
        grid_frame = ttk.Frame(self.filter_frame)
        grid_frame.pack(fill=tk.X, padx=2)  # Slightly reduced padding for compactness

        # Configure responsive grid columns
        self._configure_filter_grid_columns(grid_frame)

        # Define filter controls configuration
        filter_configs = [
            {
                "label": "Date Range:",
                "start_var": self.start_date_var,
                "end_var": self.end_date_var,
                "start_width": 10,
                "end_width": 10,
                "start_combo": "start_date_combo",
                "end_combo": "end_date_combo"
            },
            {
                "label": "Time Range:",
                "start_var": self.start_time_var,
                "end_var": self.end_time_var,
                "start_width": 7,
                "end_width": 7,
                "start_combo": "start_time_combo",
                "end_combo": "end_time_combo"
            },
            {
                "label": "Service Type:",
                "start_var": self.service_type_var,
                "end_var": None,
                "start_width": 18,
                "end_width": None,
                "start_combo": "service_type_combo",
                "end_combo": None,
                "span_columns": True
            },
            {
                "label": "Action:",
                "start_var": self.action_var,
                "end_var": None,
                "start_width": 18,
                "end_width": None,
                "start_combo": "action_combo",
                "end_combo": None,
                "span_columns": True
            }
        ]

        # Create filter controls
        row = 0
        for config in filter_configs:
            row = self._create_filter_row(grid_frame, config, row)

        # Reset Filters button
        reset_btn = ttk.Button(
            grid_frame,
            text="Reset Filters",
            style="Accent.TButton",
            command=self.reset_filters,
        )
        reset_btn.grid(row=row, column=0, columnspan=4, pady=(8, 0), sticky="ew")
        self._create_tooltip(reset_btn, "Clear all filters and show all data")

        # After setting up, update options if data is loaded
        self._update_date_options()
        self._update_time_options()
        self._update_filter_options()

    def _configure_filter_grid_columns(self, grid_frame):
        """Configure responsive grid columns for filter controls."""
        # Dynamically set minsize based on left_panel width if possible
        min_col_width = 80
        if hasattr(self, "left_panel") and self.left_panel is not None:
            try:
                self.left_panel.update_idletasks()
                left_panel_width = self.left_panel.winfo_width()
                # If left_panel width is not yet set, fallback to a reasonable default
                if left_panel_width < 200:
                    left_panel_width = 240
                # Calculate minsize for columns to fit nicely
                min_col_width = max(80, int(left_panel_width * 0.22))
            except Exception:
                min_col_width = 80

        # Configure grid columns to be responsive and fit within left_panel
        grid_frame.columnconfigure(0, weight=0, minsize=min_col_width)
        grid_frame.columnconfigure(1, weight=1, minsize=min_col_width)
        grid_frame.columnconfigure(2, weight=0, minsize=24)
        grid_frame.columnconfigure(3, weight=1, minsize=min_col_width)

    def _create_filter_row(self, grid_frame, config, row):
        """Create a filter row with consistent styling and behavior."""
        # Label
        ttk.Label(grid_frame, text=config["label"], font=("Segoe UI", 10, "bold")).grid(
            row=row, column=0, sticky="e", padx=2, pady=3
        )

        # Start combobox
        start_combo = ttk.Combobox(
            grid_frame, 
            textvariable=config["start_var"], 
            state="readonly", 
            width=config["start_width"]
        )
        
        if config.get("span_columns", False):
            start_combo.grid(row=row, column=1, columnspan=3, sticky="ew", padx=1, pady=3)
        else:
            start_combo.grid(row=row, column=1, padx=1, pady=3, sticky="ew")
            ttk.Label(grid_frame, text="to").grid(row=row, column=2, padx=1)
            
            # End combobox
            end_combo = ttk.Combobox(
                grid_frame, 
                textvariable=config["end_var"], 
                state="readonly", 
                width=config["end_width"]
            )
            end_combo.grid(row=row, column=3, padx=1, pady=3, sticky="ew")
            end_combo.bind("<<ComboboxSelected>>", self.on_filter_changed)
            setattr(self, config["end_combo"], end_combo)

        start_combo.bind("<<ComboboxSelected>>", self.on_filter_changed)
        setattr(self, config["start_combo"], start_combo)

        return row + 1



    def on_filter_changed(self, event=None):
        """Handle filter changes (date, time, service type, action) and auto-generate visualization"""
        # Auto-generate visualization if data is loaded
        if (
            self.processor
            and hasattr(self.processor, "data_loader")
            and self.processor.data_loader.get_data() is not None
        ):
            self.root.after(100, self.generate_visualization)

    def on_start_date_changed(self, event=None):
        """Handle start date change - now redirects to combined filter handler"""
        self.on_filter_changed(event)

    def on_start_time_changed(self, event=None):
        """Handle start time change - now redirects to combined filter handler"""
        self.on_filter_changed(event)



    def _create_tooltip(self, widget, text):
        """Create a tooltip for a widget"""

        def enter(event):
            # Get widget position
            x = widget.winfo_rootx() + 25
            y = widget.winfo_rooty() + widget.winfo_height() + 5

            # Create tooltip window
            tooltip = tk.Toplevel(widget)
            tooltip.wm_overrideredirect(True)
            tooltip.wm_geometry(f"+{x}+{y}")

            # Create tooltip label
            label = tk.Label(
                tooltip,
                text=text,
                background="#FFFFDD",
                foreground="#000000",
                relief="solid",
                borderwidth=1,
                font=("Segoe UI", 9),
                wraplength=200,
            )
            label.pack()

            # Store tooltip reference
            widget.tooltip = tooltip

        def leave(event):
            # Remove tooltip when mouse leaves
            if hasattr(widget, "tooltip"):
                widget.tooltip.destroy()
                del widget.tooltip

        # Bind events
        widget.bind("<Enter>", enter)
        widget.bind("<Leave>", leave)

    def _setup_right_panel(self, parent):
        """Set up the right panel with visualization display using a tabbed notebook for multi-graph visualizations."""
        self.right_panel = ttk.Frame(parent, style="ShadowLeft.TFrame")
        self.right_panel.pack(fill=tk.BOTH, side=tk.RIGHT, expand=True)

        # Create the main content frame directly (no scrollbars)
        self.right_content_frame = ttk.Frame(self.right_panel, style="Card.TFrame")
        self.right_content_frame.pack(fill=tk.BOTH, expand=True)

        # Create visualization frame with proper padding
        vis_frame = ttk.Frame(
            self.right_content_frame, style="Card.TFrame", padding=(20, 15)
        )
        vis_frame.pack(fill=tk.BOTH, expand=True, padx=(10, 20), pady=20)

        self.vis_frame = vis_frame  # <-- Expose the visualization frame for testing

        self._add_title_bar(vis_frame)

        # Use a notebook for tabbed visualizations
        self.vis_notebook = ttk.Notebook(vis_frame)
        self.vis_notebook.pack(fill=tk.BOTH, expand=True)

        # Placeholder tab
        self.placeholder_tab = ttk.Frame(self.vis_notebook, style="Card.TFrame")
        self.placeholder_label = ttk.Label(
            self.placeholder_tab,
            text="Load data and select a visualization type to begin",
            font=("Segoe UI", 12),
            foreground=self.colors["text_secondary"],
            background=self.colors["card"],
        )
        self.placeholder_label.pack(expand=True, pady=50)
        self.vis_notebook.add(self.placeholder_tab, text="Welcome")

        # No scrollbar configuration needed since we removed scrollbars

        return self.right_panel

    def _clear_vis_notebook_tabs(self):
        """Remove all tabs from the visualization notebook except the placeholder."""
        for tab_id in self.vis_notebook.tabs():
            self.vis_notebook.forget(tab_id)

    def update_figure_display(self, fig=None):
        """
        Simple update of the visualization display with a new figure or figures.
        """
        self._clear_vis_notebook_tabs()

        if self.viz_type.get() == "data_comparison":
            self._show_data_comparison_interface()
            self._disable_export_buttons()
            return

        if fig is None:
            self._show_welcome_placeholder()
            self._disable_export_buttons()
            if hasattr(self, "menu_bar_component"):
                self.menu_bar_component.update_menu_state(
                    data_loaded=True, visualization_available=False
                )
            return

        if isinstance(fig, dict):
            self._show_multiple_figures(fig)
            self._enable_export_buttons()
            return

        self._show_single_figure(fig)
        self._enable_export_buttons()

    def _show_welcome_placeholder(self):
        """Display the welcome placeholder when no visualization is selected."""
        self.vis_notebook.add(self.placeholder_tab, text="Welcome")
        self.vis_notebook.select(self.placeholder_tab)

    def _show_multiple_figures(self, figures_dict):
        """
        Display multiple figures in separate tabs.

        Args:
            figures_dict: Dictionary mapping tab names to matplotlib figures
        """

        for tab_name, figure in figures_dict.items():
            tab = create_scrollable_tab(
                figure,
                tab_name,
                self.root,
                right_panel=self.right_panel,
                vis_notebook=self.vis_notebook,
                colors=self.colors,
                logger=self.logger,
            )
            self.vis_notebook.add(tab, text=tab_name)

        # Select the first tab
        if self.vis_notebook.tabs():
            self.vis_notebook.select(self.vis_notebook.tabs()[0])

    def _show_single_figure(self, figure):
        """
        Display a single figure in one tab.

        Args:
            figure: Matplotlib figure to display
        """
        tab = create_scrollable_tab(
            figure,
            "Visualization",
            self.root,
            right_panel=self.right_panel,
            vis_notebook=self.vis_notebook,
            colors=self.colors,
            logger=self.logger,
        )
        self.vis_notebook.add(tab, text="Visualization")
        self.vis_notebook.select(tab)

    def _show_error_placeholder(self, error_message):
        """Display error message when visualization fails."""
        self._clear_vis_notebook_tabs()

        error_tab = ttk.Frame(self.vis_notebook, style="Card.TFrame")
        error_label = ttk.Label(
            error_tab,
            text=f"Error displaying visualization: {error_message}",
            font=("Segoe UI", 12),
            foreground=self.colors["error"],
            background=self.colors["card"],
        )
        error_label.pack(expand=True, pady=50)

        self.vis_notebook.add(error_tab, text="Error")
        self.vis_notebook.select(error_tab)

    def _enable_export_buttons(self):
        """Enable all export buttons when visualization is available."""
        export_buttons = ["export_button", "png_export_button", "pdf_export_button"]
        for button_name in export_buttons:
            if hasattr(self, button_name):
                getattr(self, button_name).config(state="normal")

    def _disable_export_buttons(self):
        """Disable all export buttons when no visualization is available."""
        export_buttons = ["export_button", "png_export_button", "pdf_export_button"]
        for button_name in export_buttons:
            if hasattr(self, button_name):
                getattr(self, button_name).config(state="disabled")

    """  def _create_scrollable_tab(self, figure, tab_name):
""" """
        Create a scrollable tab that supports both vertical and horizontal scrolling,
        and fills the entire space of the right_panel.

        Args:
            figure: Matplotlib figure to display
            tab_name: Name of the tab

        Returns:
            ttk.Frame: The scrollable tab frame
        """ """
        # Responsive scaling based on screen size
        screen_width = self.root.winfo_screenwidth()
        if screen_width < 1366:
            scale_factor = 0.7
        elif screen_width < 1920:
            scale_factor = 0.85
        else:
            scale_factor = 1.0

        RENDERING_CONFIG = {
            "min_width": int(800 * scale_factor),
            "min_height": int(600 * scale_factor),
            "background_color": self.colors.get("card", "#ffffff"),
            "scroll_delay_ms": 100,
            "auto_resize_canvas": True,
            "enable_horizontal_scroll": True,
            "enable_vertical_scroll": True,
            "figure_dpi": None,
            "figure_scale": scale_factor,
        }

        # The tab frame should fill the right_panel
        tab = ttk.Frame(self.vis_notebook, style="Card.TFrame")
        tab.pack_propagate(False)
        if self.right_panel is not None:
            # Make the tab fill the right_panel
            tab.configure(
                width=self.right_panel.winfo_width(),
                height=self.right_panel.winfo_height(),
            )
        tab.grid_propagate(False)

        # Canvas fills the tab
        canvas = tk.Canvas(
            tab, bg=RENDERING_CONFIG["background_color"], highlightthickness=0
        )
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Configure scrollbars
        if RENDERING_CONFIG["enable_vertical_scroll"]:
            v_scrollbar = ttk.Scrollbar(tab, orient=tk.VERTICAL, command=canvas.yview)
            canvas.configure(yscrollcommand=v_scrollbar.set)
            v_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        if RENDERING_CONFIG["enable_horizontal_scroll"]:
            h_scrollbar = ttk.Scrollbar(tab, orient=tk.HORIZONTAL, command=canvas.xview)
            canvas.configure(xscrollcommand=h_scrollbar.set)
            h_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

        # Set content frame size based on figure dimensions with responsive scaling
        fig_width, fig_height = figure.get_size_inches()
        dpi = figure.get_dpi()
        pixel_width = int(fig_width * dpi * RENDERING_CONFIG["figure_scale"])
        pixel_height = int(fig_height * dpi * RENDERING_CONFIG["figure_scale"])

        content_frame = ttk.Frame(canvas, style="Card.TFrame")
        content_frame.config(
            width=max(pixel_width, RENDERING_CONFIG["min_width"]),
            height=max(pixel_height, RENDERING_CONFIG["min_height"]),
        )

        canvas_window = canvas.create_window((0, 0), window=content_frame, anchor=tk.NW)

        try:
            # Apply figure scaling if configured
            if RENDERING_CONFIG["figure_scale"] != 1.0:
                figure.set_size_inches(
                    figure.get_size_inches() * RENDERING_CONFIG["figure_scale"]
                )
            if RENDERING_CONFIG["figure_dpi"]:
                figure.set_dpi(RENDERING_CONFIG["figure_dpi"])

            fig_canvas = FigureCanvasTkAgg(figure, content_frame)
            fig_canvas.draw()
            fig_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        except Exception as e:
            self.logger.error(f"Error creating matplotlib canvas: {e}")
            ttk.Label(
                content_frame, text=f"Error displaying {tab_name}: {str(e)}"
            ).pack(pady=20)

        def _configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            if RENDERING_CONFIG["auto_resize_canvas"]:
                canvas.itemconfig(
                    canvas_window,
                    width=canvas.winfo_width(),
                    height=canvas.winfo_height(),
                )

        def _on_canvas_configure(event):
            if RENDERING_CONFIG["auto_resize_canvas"]:
                # Always fill the right_panel (tab) area
                new_width = max(event.width, content_frame.winfo_reqwidth())
                new_height = max(event.height, content_frame.winfo_reqheight())
                canvas.itemconfig(canvas_window, width=new_width, height=new_height)

        content_frame.bind("<Configure>", _configure_scroll_region)
        canvas.bind("<Configure>", _on_canvas_configure)

        tab.after(
            RENDERING_CONFIG["scroll_delay_ms"],
            lambda: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        return tab """

    def show_data_summary(self):
        """Show data summary dialog using the new data_loader architecture"""
        # Check if we're in an error state
        if self._check_error_state("data_summary"):
            self.show_status(
                "Cannot show data summary while in error state. Please use recovery option first.",
                "error",
            )
            return

        if not self.data_loader or not self.data_loader.has_data():
            messagebox.showwarning("No Data", "Please load data first.")
            return

        try:
            # Get data summary with error handling and validation
            summary = self.get_data_summary()
            if not summary:
                messagebox.showwarning("No Data", "No data available for summary.")
                return

            # Validate summary data
            if not isinstance(summary, dict):
                messagebox.showerror("Data Error", "Invalid summary data format.")
                return

            # Format summary with enhanced styling
            pretty_summary = self._format_data_summary(summary)

            # Validate formatted summary
            if not pretty_summary or len(pretty_summary.strip()) == 0:
                messagebox.showerror("Format Error", "Failed to format data summary.")
                return

            # Create and configure summary window with improved layout
            summary_window = tk.Toplevel(self.root)
            summary_window.title("Data Summary")
            summary_window.transient(self.root)
            summary_window.grab_set()
            summary_window.minsize(800, 600)
            summary_window.geometry("1000x700")

            # Set window icon if available
            try:
                summary_window.iconbitmap("assets/logo.png")
            except:
                pass

            # Center window on screen
            self._center_window(summary_window)

            # Create main content frame with better padding
            main_frame = ttk.Frame(summary_window)
            main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)

            # Create scrollable text frame with enhanced styling
            frame, text_widget = create_scrollable_text_frame(main_frame)
            frame.pack(fill=tk.BOTH, expand=True)

            if text_widget:
                # Insert formatted summary
                text_widget.insert(tk.END, pretty_summary)
                text_widget.config(state=tk.DISABLED)

                # Configure text widget styling with improved fonts and colors
                text_widget.tag_configure(
                    "header", font=("Segoe UI", 14, "bold"), foreground="#1e40af"
                )
                text_widget.tag_configure(
                    "section", font=("Segoe UI", 12, "bold"), foreground="#059669"
                )
                text_widget.tag_configure(
                    "highlight", background="#f0f8ff", foreground="#374151"
                )

                # Apply styling to text
                self._apply_summary_styling(text_widget, pretty_summary)

                # Smart window sizing with improved calculations
                def adjust_window_size():
                    try:
                        # Calculate optimal size based on content
                        line_count = int(text_widget.index("end-1c").split(".")[0])
                        lines = pretty_summary.split("\n")
                        max_line_length = (
                            max(len(line) for line in lines) if lines else 80
                        )

                        # Improved size calculations with better defaults
                        line_height = 18  # Slightly smaller for better fit
                        char_width = 9  # Better character width estimation
                        padding = 200  # More padding for better appearance
                        # Set min/max width and height to maintain a 4:3 aspect ratio
                        min_width, max_width = 800, 1400
                        min_height, max_height = 600, 1050

                        estimated_height = min(
                            max(min_height, line_count * line_height + padding),
                            max_height,
                        )
                        estimated_width = min(
                            max(min_width, max_line_length * char_width + 150),
                            max_width,
                        )

                        # Apply calculated size
                        summary_window.geometry(f"{estimated_width}x{estimated_height}")
                        summary_window.update_idletasks()

                        # Re-center window
                        self._center_window(summary_window)

                    except Exception as e:
                        self.logger.warning(
                            f"Could not calculate optimal window size: {e}"
                        )

                # Schedule size adjustment with longer delay for better accuracy
                # summary_window.after(500, adjust_window_size)

            # Create button frame with enhanced styling and better layout
            button_frame = ttk.Frame(main_frame)
            button_frame.pack(fill=tk.X, pady=(20, 0))

            # Add export button with better styling
            export_btn = ttk.Button(
                button_frame,
                text="Export Summary",
                command=lambda: self._export_summary(pretty_summary, summary_window),
                style="Accent.TButton",
            )
            export_btn.pack(side=tk.LEFT, padx=(0, 10))

            # Add close button with better styling
            close_btn = ttk.Button(
                button_frame,
                text="Close",
                command=summary_window.destroy,
                style="Primary.TButton",
            )
            close_btn.pack(side=tk.RIGHT, padx=(10, 0))

            # Add keyboard shortcuts
            summary_window.bind("<Escape>", lambda e: summary_window.destroy())
            summary_window.bind(
                "<Control-s>",
                lambda e: self._export_summary(pretty_summary, summary_window),
            )

            # Set focus to window
            summary_window.focus_set()

        except Exception as e:
            from app.gui.dialogs.error_dialog import ErrorDialog

            # Create and show error dialog with recovery options
            error_dialog = ErrorDialog(
                self,
                e,
                context={
                    "operation": "Data Summary Generation",
                    "component": "Main Window",
                    "summary_data_available": "summary" in locals(),
                },
                recovery_callback=lambda: self.show_data_summary(),
            )
            error_dialog.show()

    def _format_data_summary(self, summary):
        """Format data summary for display with enhanced information"""
        from datetime import datetime
        import os

        lines = []

        # Header
        lines.append("=" * 60)
        lines.append("CLINIC DATA SUMMARY REPORT")
        lines.append("=" * 60)
        lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("")

        # Basic Statistics
        lines.append("BASIC STATISTICS")
        lines.append("-" * 30)
        total_records = summary.get("total_records", "N/A")
        patients = summary.get("patients", "N/A")
        if isinstance(total_records, (int, float)):
            lines.append(f"Total Records: {total_records:,}")
        else:
            lines.append(f"Total Records: {total_records}")
        if isinstance(patients, (int, float)):
            lines.append(f"Unique Patients: {patients:,}")
        else:
            lines.append(f"Unique Patients: {patients}")

        # Date and Time Information
        if summary.get("date_range") and summary["date_range"] != "Unknown":
            lines.append(f"Date Range: {summary['date_range']}")
        if summary.get("time_range") and summary["time_range"] != "Unknown":
            lines.append(f"Time Range: {summary['time_range']}")

        # Data Dimensions
        lines.append("")
        lines.append("SERVICE INFORMATION")
        lines.append("-" * 30)
        if summary.get("service_areas", 0) > 0:
            lines.append(f"Service Areas: {summary['service_areas']}")
        if summary.get("service_types", 0) > 0:
            lines.append(f"Service Types: {summary['service_types']}")
        if summary.get("actions", 0) > 0:
            lines.append(f"Actions: {summary['actions']}")
        if summary.get("locations", 0) > 0:
            lines.append(f"Locations: {summary['locations']}")

        # Most Common Values
        lines.append("")
        lines.append("MOST COMMON VALUES")
        lines.append("-" * 30)
        if summary.get("most_common_service_area"):
            lines.append(f"Service Area: {summary['most_common_service_area']}")
        if summary.get("most_common_service_type"):
            lines.append(f"Service Type: {summary['most_common_service_type']}")
        if summary.get("most_common_action"):
            lines.append(f"Action: {summary['most_common_action']}")
        if summary.get("most_common_location"):
            lines.append(f"Location: {summary['most_common_location']}")

        # Data Quality Information
        lines.append("")
        lines.append("DATA QUALITY")
        lines.append("-" * 30)
        if "missing_data_percentage" in summary:
            # Fix: Don't multiply by 100 again - it's already a percentage
            missing_pct = summary["missing_data_percentage"]
            if isinstance(missing_pct, (int, float)):
                # Ensure the value is reasonable (0-100%)
                if missing_pct > 100:
                    missing_pct = 100.0
                elif missing_pct < 0:
                    missing_pct = 0.0
                lines.append(f"Missing Data: {missing_pct:.1f}%")
            else:
                lines.append(f"Missing Data: {missing_pct}")
        if "memory_usage_mb" in summary:
            lines.append(f"Memory Usage: {summary['memory_usage_mb']:.2f} MB")
        if "data_quality_score" in summary:
            lines.append(f"Quality Score: {summary['data_quality_score']:.1f}/10")

        # Journey Information (if available)
        if self.data_loader and hasattr(self.data_loader, "journey_config"):
            journey_config = self.data_loader.get_journey_config()
            if journey_config.get("enabled", False):
                lines.append("")
                lines.append("PATIENT JOURNEY CONFIGURATION")
                lines.append("-" * 30)
                lines.append(f"Journey Identification: Enabled")
                lines.append(
                    f"Max Gap: {journey_config.get('max_gap_minutes', 'N/A')} minutes"
                )
                lines.append(
                    f"Same Day Only: {journey_config.get('same_day_only', 'N/A')}"
                )
                lines.append(
                    f"Include Service Type: {journey_config.get('include_service_type', 'N/A')}"
                )

        # File Information
        if self.data_loader and self.data_loader.get_file_path():
            lines.append("")
            lines.append("FILE INFORMATION")
            lines.append("-" * 30)
            file_path = self.data_loader.get_file_path()
            lines.append(f"File: {os.path.basename(file_path)}")
            lines.append(f"Path: {file_path}")

            # File size
            try:
                file_size = os.path.getsize(file_path)
                if file_size > 1024 * 1024:
                    size_str = f"{file_size / (1024 * 1024):.1f} MB"
                else:
                    size_str = f"{file_size / 1024:.1f} KB"
                lines.append(f"Size: {size_str}")
            except:
                lines.append("Size: Unknown")

        lines.append("")
        lines.append("=" * 60)

        return "\n".join(lines)

    def _apply_summary_styling(self, text_widget, content):
        """Apply styling to the data summary text widget."""
        try:
            # Apply styling to different sections
            lines = content.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("="):
                    # Header lines
                    text_widget.tag_add("header", f"{i+1}.0", f"{i+1}.end")
                elif (
                    line.startswith("BASIC STATISTICS")
                    or line.startswith("SERVICE INFORMATION")
                    or line.startswith("MOST COMMON VALUES")
                    or line.startswith("DATA QUALITY")
                    or line.startswith("PATIENT JOURNEY CONFIGURATION")
                    or line.startswith("FILE INFORMATION")
                ):
                    # Section headers
                    text_widget.tag_add("section", f"{i+1}.0", f"{i+1}.end")
                elif line.startswith("-"):
                    # Separator lines
                    text_widget.tag_add("highlight", f"{i+1}.0", f"{i+1}.end")
        except Exception as e:
            self.logger.debug(f"Error applying summary styling: {e}")

    def _export_summary(self, summary_content, parent_window):
        """Export data summary to a text file."""
        try:
            from tkinter import filedialog
            import os

            # Get default filename
            default_filename = (
                f"clinic_data_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            )

            # Show save dialog
            file_path = filedialog.asksaveasfilename(
                parent=parent_window,
                title="Export Data Summary",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialvalue=default_filename,
            )

            if file_path:
                # Write summary to file
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(summary_content)

                self.show_status(
                    f"Data summary exported to {os.path.basename(file_path)}", "success"
                )
                self.logger.info(f"Data summary exported: {file_path}")

        except Exception as e:
            self.logger.error(f"Error exporting summary: {e}")
            messagebox.showerror("Export Error", f"Failed to export summary: {str(e)}")

    def _center_window(self, window):
        """Center a window on the screen."""
        try:
            window.update_idletasks()
            x = (window.winfo_screenwidth() // 2) - (window.winfo_width() // 2)
            y = (window.winfo_screenheight() // 2) - (window.winfo_height() // 2)
            window.geometry(f"+{x}+{y}")
        except Exception as e:
            self.logger.debug(f"Error centering window: {e}")

    def show_quality_report(self):
        """Show data quality report using the new data_loader architecture"""
        # Check if we're in an error state
        if self._check_error_state("quality_report"):
            self.show_status(
                "Cannot show quality report while in error state. Please use recovery option first.",
                "error",
            )
            return

        if not self.data_loader or not self.data_loader.has_data():
            messagebox.showwarning("No Data", "Please load data first.")
            return

        try:
            # Use our new DataQualityAssessment component
            if self.data_quality_issues:
                # Use cached quality report if available
                self._show_quality_report(self.data_quality_issues)
            else:
                # Generate new quality report
                self.logger.info("Generating fresh data quality report...")
                data = self.data_loader.get_data()
                quality_report = (
                    self.data_quality_assessor.generate_comprehensive_quality_report(
                        data
                    )
                )
                self.data_quality_issues = quality_report
                self._show_quality_report(quality_report)

        except Exception as e:
            self.logger.error(f"Error generating quality report: {str(e)}")
            messagebox.showerror(
                "Error", f"Failed to generate quality report: {str(e)}"
            )

    def _get_current_filters(self):
        """Get current filter settings"""
        filters = {}

        # Date filters
        if self.start_date_var.get() and self.end_date_var.get():
            filters["start_date"] = self.start_date_var.get()
            filters["end_date"] = self.end_date_var.get()

        # Time filters
        if self.start_time_var.get() and self.end_time_var.get():
            filters["start_time"] = self.start_time_var.get()
            filters["end_time"] = self.end_time_var.get()

        # Service type filter
        if self.service_type_var.get() and self.service_type_var.get() != "All":
            filters["service_type"] = self.service_type_var.get()

        # Action filter
        if self.action_var.get() and self.action_var.get() != "All":
            filters["action"] = self.action_var.get()

        return filters

    def _handle_mousewheel(self, event, canvas, frame, orientation="vertical"):
        """Handle mousewheel scrolling for canvas widgets with proper error handling"""
        try:
            # Check if canvas still exists and is valid
            if not canvas or not canvas.winfo_exists():
                return

            # Only process if event is from this canvas or its children
            if (
                event.widget != canvas
                and hasattr(event.widget, "master")
                and event.widget.master != frame
            ):
                return

            # Determine scroll direction
            scroll_direction = -1 if (event.num == 4 or event.delta > 0) else 1

            # Apply scrolling
            if orientation == "vertical":
                canvas.yview_scroll(scroll_direction, "units")
            else:  # horizontal
                canvas.xview_scroll(scroll_direction, "units")
        except tk.TclError:
            # Canvas has been destroyed, ignore the event
            pass
        except Exception as e:
            # Log any other errors but don't crash
            print(f"Mousewheel error: {e}")

    def _update_date_options(self):
        """Update date filter options using the new data_loader architecture"""
        if self.data_loader and self.data_loader.get_data() is not None:
            try:
                data = self.data_loader.get_data()
                # Use the parsed datetime column, never the original
                if "Service Date" in data.columns:
                    # Parse all dates with dayfirst=True
                    dates = pd.to_datetime(
                        data["Service Date"].astype(str).str.strip(),
                        dayfirst=True,
                        errors="coerce",
                    )
                    dates = dates.dropna().unique()
                    dates = sorted(dates)
                    date_strings = [d.strftime("%d/%m/%Y") for d in dates]
                else:
                    date_strings = []
                if not date_strings:
                    self.logger.info("No valid dates found in Service Date.")
                # Update date comboboxes directly
                if hasattr(self, "start_date_combo"):
                    self.start_date_combo["values"] = date_strings
                    if date_strings:
                        self.start_date_var.set(date_strings[0])
                if hasattr(self, "end_date_combo"):
                    self.end_date_combo["values"] = date_strings
                    if date_strings:
                        self.end_date_var.set(date_strings[-1])
                # Update VizControls if available
                if hasattr(self, "viz_controls") and self.viz_controls is not None:
                    self.viz_controls.update_patient_dates(date_strings)
                
                # Fallback: Update patient date combo directly (for backward compatibility)
                if hasattr(self, "patient_date_combo"):
                    self.patient_date_combo["values"] = date_strings
            except Exception as e:
                self.logger.error(f"Error updating date options: {e}")

    def _update_filter_options(self):
        """Update filter options using the new data_loader architecture"""
        if self.data_loader and self.data_loader.get_data() is not None:
            try:
                data = self.data_loader.get_data()
                # Update service types
                if "Service Type" in data.columns:
                    service_types = ["All"] + sorted(
                        data["Service Type"].dropna().unique()
                    )
                    if hasattr(self, "service_type_combo"):
                        self.service_type_combo["values"] = service_types

                # Update actions
                if "Action" in data.columns:
                    actions = ["All"] + sorted(data["Action"].dropna().unique())
                    if hasattr(self, "action_combo"):
                        self.action_combo["values"] = actions

            except Exception as e:
                self.logger.error(f"Error updating filter options: {e}")

    def _update_simple_patient_dropdown(self):
        """Update patient dropdown with full journey IDs for patient journey visualizations"""
        if self.data_loader and self.data_loader.get_data() is not None:
            try:
                # Set the data in the filter component
                self.data_filter.set_data(self.data_loader.get_data())

                # Get full journey IDs (Patient IDs) from the enhanced journey identification
                data = self.data_loader.get_data()
                if 'Patient ID' in data.columns:
                    full_journey_ids = sorted(data['Patient ID'].unique())
                    
                    # Store for filtering
                    self.all_patient_ids = full_journey_ids

                    # Update VizControls if available
                    if hasattr(self, "viz_controls") and self.viz_controls is not None:
                        # Don't override patient list if user has actively filtered by date
                        if (hasattr(self.viz_controls, 'patient_date_var') and 
                            self.viz_controls.patient_date_var.get() and 
                            getattr(self.viz_controls, 'date_filter_active', False)):
                            # Skip updating if user has actively filtered by date
                            pass
                        else:
                            self.viz_controls.update_patients(full_journey_ids)
                    
                    # Fallback: Update patient combo directly (for backward compatibility)
                    if hasattr(self, "patient_combo"):
                        self.patient_combo["values"] = full_journey_ids
                        
                    self.logger.info(f"Updated patient dropdown with {len(full_journey_ids)} journey IDs")
                else:
                    self.logger.warning("Patient ID column not found in data")
            except Exception as e:
                self.logger.error(f"Error updating patient dropdown: {e}")


    def generate_visualization(self):
        """Generate and display the selected visualization asynchronously with progress reporting"""
        timer = Timer()
        timer.start()
        # Check if shutdown was requested
        if getattr(self, "shutdown_requested", False):
            return

        # Check if we're in an error state
        if self._check_error_state("visualization_generation"):
            self.show_status(
                "Cannot generate visualization while in error state. Please use recovery option first.",
                "error",
            )
            return

        # Check if data is loaded
        if not self.data_loader or not self.data_loader.has_data():
            self.show_status("Please load data first.", "warning")
            return

        # Get selected visualization type
        viz_type = self.viz_type.get()
        if not viz_type:
            self.show_status("Please select a visualization type.", "warning")
            return

        # Handle data comparison type (no async generation needed)
        if viz_type == "data_comparison":
            self._show_data_comparison_interface()
            return

        # Cancel any existing visualization task
        if self.current_viz_task_id:
            self.async_viz_manager.cancel_task(self.current_viz_task_id)
            self.current_viz_task_id = None

        try:
            # Get current filters
            filters = self._get_current_filters()

            # Apply filters to get the data
            filtered_data = self.apply_filters(filters)

            if filtered_data.empty:
                self.show_status("No data matches the current filters.", "warning")
                return

            # Check again if shutdown was requested during filtering
            if getattr(self, "shutdown_requested", False):
                return

            # Get patient ID for patient-specific visualizations
            patient_id = None
            journey_start_time = None
            if viz_type in ["patient_journey"]:
                # Get patient data from VizControls
                if hasattr(self, "viz_controls") and self.viz_controls is not None:
                    selection = self.viz_controls.get_current_selection()
                    patient_id = selection.get('patient_id')
                    patient_date = selection.get('patient_date')
                else:
                    # Fallback to old method if VizControls not available
                    patient_id = self.patient_id_var.get()
                    patient_date = self.patient_date_var.get()
                
                if not patient_id:
                    self.show_status(
                        "Please select a patient for this visualization.", "warning"
                    )
                    return

            # Show progress dialog
            def on_cancel():
                """Handle cancellation from progress dialog"""
                # Capture self reference to avoid scope issues in async context
                main_window = self
                if main_window.current_viz_task_id:
                    main_window.async_viz_manager.cancel_task(main_window.current_viz_task_id)
                    main_window.current_viz_task_id = None
                main_window.show_status("Visualization generation cancelled.", "warning")

            # Create progress dialog
            progress_dialog = show_progress(
                self.root,
                title="Generating Visualization",
                message=f"Preparing {get_visualization_display_name(viz_type)}...",
                can_cancel=True,
                cancel_callback=on_cancel,
                colors=self.colors,
            )

            # Progress callback for updates
            def on_progress(progress: float, message: str):
                """Handle progress updates from async manager"""
                # Capture progress_dialog reference to avoid scope issues in async context
                dialog = progress_dialog
                if dialog and not dialog.is_closed():
                    # Ensure progress is never 0.0 (minimum 0.01)
                    safe_progress = max(0.01, progress) if progress < 1.0 else progress
                    dialog.update_progress(safe_progress, message)

            # Completion callback - capture self reference properly
            def on_completion(figure):
                """Handle successful completion"""
                # Capture self reference to avoid scope issues in async context
                main_window = self
                try:
                    # Close progress dialog
                    close_progress()

                    # Check if shutdown was requested
                    if getattr(main_window, "shutdown_requested", False):
                        if figure:
                            plt.close(figure)
                        return

                    if figure is None:
                        main_window.show_status(
                            "Visualization generation failed - no result returned.",
                            "error",
                        )
                        return

                    # Special handling for tabbed visualizations
                    if viz_type in [
                        "patient_journey",
                        "patient_flow_analysis",
                        "service_transitions",
                        "kpi_dashboard",
                        "hourly_unique_kiosk_queue",
                    ]:
                        # If the generator returns a dictionary of figures (tabbed charts)
                        if isinstance(figure, dict):
                            display_name = get_visualization_display_name(viz_type)
                            main_window.update_figure_display(figure)
                            # Use clean title without emojis
                            clean_title = display_name
                            main_window.title_label.config(text=clean_title)
                            # Store current figure reference safely - for dict, store None to avoid closing issues
                            if (
                                hasattr(main_window, "current_figure")
                                and main_window.current_figure
                                and not isinstance(main_window.current_figure, dict)
                            ):
                                plt.close(main_window.current_figure)
                            main_window.current_figure = (
                                None  # Don't store dict as current_figure
                            )
                            main_window.show_status(
                                f"Generated {display_name} (Tabbed) successfully. (Processed {len(filtered_data)} records)",
                                "success",
                            )
                            main_window.current_viz_task_id = None
                            timer.stop()
                            timer.show_timing(
                                f"Visualization Generation: {display_name}"
                            )
                            # Update menu bar after visualization generated
                            if hasattr(main_window, "menu_bar_component"):
                                main_window.menu_bar_component.update_menu_state(
                                    data_loaded=True, visualization_available=True
                                )
                            return

                    # Display the figure (single-figure fallback)
                    display_name = get_visualization_display_name(viz_type)
                    if viz_type in ["patient_journey"]:
                        display_name += f" - Patient {patient_id}"

                    main_window.update_figure_display(figure)
                    # Use clean title without emojis
                    clean_title = display_name
                    main_window.title_label.config(text=clean_title)

                    # Store current figure reference safely
                    if hasattr(main_window, "current_figure") and main_window.current_figure:
                        # Check if current_figure is a dictionary (tabbed visualization)
                        if isinstance(main_window.current_figure, dict):
                            # Close all figures in the dictionary
                            for fig in main_window.current_figure.values():
                                if fig is not None:
                                    plt.close(fig)
                        else:
                            # Close single figure
                            plt.close(main_window.current_figure)
                    main_window.current_figure = figure

                    success_msg = f"Generated {display_name} successfully."
                    if viz_type in ["patient_journey"]:
                        success_msg += f" Note: Using Patient ID {patient_id} for journey analysis."
                    success_msg += f" (Processed {len(filtered_data)} records)"

                    timer.stop()
                    timer.show_timing(f"Visualization Generation: {display_name}")
                    main_window.show_status(success_msg, "success")

                    # Clear task ID
                    main_window.current_viz_task_id = None

                except Exception as e:
                    main_window.logger.error(f"Error in completion callback: {e}")
                    main_window.show_status(
                        f"Error displaying visualization: {str(e)}", "error"
                    )

            # Error callback - capture self reference properly
            def on_error(error):
                """Handle errors during generation"""
                # Capture self reference to avoid scope issues in async context
                main_window = self
                try:
                    # Close progress dialog
                    close_progress()

                    # Handle the error
                    error_result = main_window.error_handler.handle_error(
                        error,
                        context={
                            "viz_type": viz_type,
                            "data_loaded": main_window.data_loader is not None,
                            "operation": "async_visualization_generation",
                        },
                    )
                    main_window.show_status(error_result["message"], "error")

                    # Clear task ID
                    main_window.current_viz_task_id = None

                except Exception as e:
                    main_window.logger.error(f"Error in error callback: {e}")
                    main_window.show_status(
                        f"Visualization generation failed: {str(error)}", "error"
                    )

            # Start async visualization generation
            self.logger.debug(
                f"Starting async generation of {viz_type} visualization with {len(filtered_data)} records"
            )

            # Get container and window dimensions for responsive sizing
            container_width, container_height, window_width, window_height = (
                self._get_visualization_container_dimensions()
            )

            # Prepare kwargs with container and window dimensions
            viz_kwargs = {
                "container_width": container_width,
                "container_height": container_height,
                "window_width": window_width,
                "window_height": window_height,
            }

            # Add patient ID and journey start time for patient-specific visualizations
            if patient_id:
                viz_kwargs["patient_id"] = patient_id
            if journey_start_time:
                viz_kwargs["journey_start_time"] = journey_start_time
            # Pass the selected date for patient journey matching
            if viz_type == "patient_journey" and patient_date:
                viz_kwargs["patient_date"] = patient_date

            # For patient_journey, patient_flow_analysis, service_transitions, and kpi_dashboard, use tabbed charts
            if viz_type in [
                "patient_journey",
                "patient_flow_analysis",
                "service_transitions",
                "kpi_dashboard",
            ]:
                if viz_type == "patient_journey":
                    from app.visualization.chart_generators.flow_charts import (
                        PatientJourneyGenerator,
                    )

                    generator = PatientJourneyGenerator()
                elif viz_type == "patient_flow_analysis":
                    from app.visualization.chart_generators.flow_charts import (
                        PatientFlowAnalysisGenerator,
                    )

                    generator = PatientFlowAnalysisGenerator()
                elif viz_type == "service_transitions":
                    from app.visualization.chart_generators.flow_charts import (
                        ServiceTransitionsGenerator,
                    )

                    generator = ServiceTransitionsGenerator()
                else:  # kpi_dashboard
                    from app.visualization.chart_generators.dashboard_charts import (
                        KPIDashboardGenerator,
                    )

                    generator = KPIDashboardGenerator()

                def run_tabbed():
                    return generator.generate_tabbed_charts(
                        filtered_data, progress_callback=on_progress, **viz_kwargs
                    )

                import threading

                def thread_target():
                    result = run_tabbed()
                    on_completion(result)

                t = threading.Thread(target=thread_target)
                t.start()
                return

            self.current_viz_task_id = self.async_viz_manager.generate_async(
                viz_type=viz_type,
                data=filtered_data,
                progress_callback=on_progress,
                completion_callback=on_completion,
                error_callback=on_error,
                **viz_kwargs,
            )

            self.show_status(
                f"Generating {get_visualization_display_name(viz_type)}...", "info"
            )

        except Exception as e:
            # Close progress dialog if it was created
            close_progress()

            error_result = self.error_handler.handle_error(
                e,
                context={
                    "viz_type": viz_type,
                    "data_loaded": self.data_loader is not None,
                    "operation": "visualization_setup",
                },
            )
            self.show_status(error_result["message"], "error")

    def _get_visualization_container_dimensions(self):
        """Get the dimensions of the visualization container and window for responsive sizing."""
        try:
            # Get container dimensions
            if hasattr(self, "vis_notebook") and self.vis_notebook.winfo_exists():
                container_width = self.vis_notebook.winfo_width()
                container_height = self.vis_notebook.winfo_height()
                # Use reasonable defaults if dimensions are not available
                if container_width <= 1:
                    container_width = 800
                if container_height <= 1:
                    container_height = 600
            else:
                # Default container dimensions
                container_width, container_height = 800, 600
            
            # Get window dimensions
            if hasattr(self, "root") and self.root.winfo_exists():
                window_width = self.root.winfo_width()
                window_height = self.root.winfo_height()
                # Use reasonable defaults if dimensions are not available
                if window_width <= 1:
                    window_width = 1200
                if window_height <= 1:
                    window_height = 800
            else:
                # Default window dimensions
                window_width, window_height = 1200, 800
            
            return container_width, container_height, window_width, window_height
        except Exception as e:
            self.logger.debug(f"Error getting dimensions: {e}")
            return 800, 600, 1200, 800


    def _setup_left_panel(self, parent):
        """Set up the left panel with header and controls using VizControls component"""
        from app.gui.components.viz_controls import VizControls  # Ensure import at top of file

        # Panel configuration - easily tweakable
        PANEL_CONFIG = {
            "width": 380,  # Total panel width
            "canvas_width": 365,  # Canvas width (increased for better fit)
            "controls_width": 345,  # Controls frame width (increased for better fit)
            "padding": (12, 12),  # Controls frame padding (increased for better spacing)
            "section_spacing": 12,  # Spacing between sections (increased for better separation)
            "font_family": "Segoe UI",  # Font family for labels
            "label_font_size": 11,  # Font size for section labels
            "control_font_size": 10,  # Font size for controls
        }

        # Create the left panel frame
        left_panel = ttk.Frame(
            parent, style="ShadowRight.TFrame", width=PANEL_CONFIG["width"]
        )
        left_panel.pack(fill=tk.Y, side=tk.LEFT)
        left_panel.pack_propagate(False)

        # Add header at the top of the left panel
        self._setup_header(left_panel)

        # Create scrollable controls container
        controls_frame = self._create_scrollable_controls_container(left_panel, PANEL_CONFIG)

        # Add service transition controls if needed
        self._setup_service_selector(controls_frame, PANEL_CONFIG)

        # Add data controls and filter controls
        self._setup_data_controls(controls_frame)
        self._setup_filter_controls(controls_frame)

        # Use VizControls for all visualization and patient controls
        self.viz_controls = VizControls(controls_frame, self.colors, self._on_viz_controls_change)

        return left_panel

    def _create_scrollable_controls_container(self, parent, config):
        """Create a scrollable container for controls with consistent styling."""
        # Canvas and scrollbar setup for scrollable controls
        left_canvas = tk.Canvas(
            parent,
            background=self.colors["sidebar"],
            highlightthickness=0,
            width=config["canvas_width"],
        )
        left_scrollbar = ttk.Scrollbar(
            parent,
            orient="vertical",
            command=left_canvas.yview,
            style="Sidebar.Vertical.TScrollbar",
        )
        left_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        left_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        left_canvas.configure(yscrollcommand=left_scrollbar.set)

        # Controls frame inside the canvas
        controls_frame = ttk.Frame(
            left_canvas, style="Sidebar.TFrame", padding=config["padding"]
        )
        left_canvas.create_window(
            (0, 0),
            window=controls_frame,
            anchor="nw",
            width=config["controls_width"],
        )

        # Scrolling configuration
        controls_frame.bind(
            "<Configure>",
            lambda e: left_canvas.configure(scrollregion=left_canvas.bbox("all")),
        )
        left_canvas.bind(
            "<MouseWheel>",
            lambda e: self._handle_mousewheel(e, left_canvas, controls_frame),
        )

        return controls_frame

    def _setup_service_selector(self, parent, config):
        """Set up service selector controls with consistent styling."""
        self.service_selector_frame = ttk.Frame(parent, style="Sidebar.TFrame")
        self.service_selector_frame.pack(
            fill=tk.X,
            padx=config["section_spacing"],
            pady=(0, config["section_spacing"]),
        )
        self.service_selector_frame.pack_forget()  # Hide initially

        self.service_selector_label = ttk.Label(
            self.service_selector_frame,
            text="Select Source Service:",
            style="Sidebar.TLabel",
            font=(config["font_family"], config["label_font_size"], "bold"),
        )
        self.service_selector_label.pack(fill=tk.X, pady=(6, 3))

        self.service_selector = ttk.Combobox(
            self.service_selector_frame,
            textvariable=self.selected_service_var,
            state="readonly",
            font=(config["font_family"], config["control_font_size"]),
        )
        self.service_selector.pack(fill=tk.X, pady=(0, 6))
        self.service_selector.bind("<<ComboboxSelected>>", self._on_service_selected)

    def _on_service_selected(self, event=None):
        """Handle service selection change"""
        if self.viz_type.get() == "service_transitions":
            self.generate_visualization()

    def _add_title_bar(self, parent):
        """Add title bar with export controls to the visualization area"""
        title_frame = ttk.Frame(parent, style="Card.TFrame")
        title_frame.pack(fill=tk.X, pady=(0, 8))  # Reduced from 15 to 8 for more space

        # Title label (left side)
        self.title_label = ttk.Label(
            title_frame,
            text="Visualization",
            font=("Segoe UI", 14, "bold"),
            foreground=self.colors["primary"],
            background=self.colors["card"],
        )
        self.title_label.pack(side=tk.LEFT)

        # Export controls (right side)
        export_frame = ttk.Frame(title_frame, style="Card.TFrame")
        export_frame.pack(side=tk.RIGHT)

        # --- Button configuration for easy add/remove ---
        # Each dict: { 'name': str, 'text': str, 'style': str, 'command': callable, 'state': str, 'width': int, 'parent': str }
        # 'parent' can be 'export_frame' or 'quick_export_frame'
        export_buttons_config = [
            {
                "name": "export_button",
                "text": "Export",
                "style": "Action.TButton",
                "command": self.export_current_visualization,
                "state": "disabled",
                "width": None,
                "parent": "export_frame",
                "pack_opts": {"side": tk.RIGHT, "padx": (5, 0)},
            },
        ]
        quick_export_buttons_config = [
            {
                "name": "png_export_button",
                "text": "PNG",
                "style": "Action.TButton",
                "command": lambda: self.quick_export_visualization("PNG"),
                "state": "disabled",
                "width": 5,
                "parent": "quick_export_frame",
                "pack_opts": {"side": tk.RIGHT, "padx": (0, 2)},
            },
            {
                "name": "pdf_export_button",
                "text": "PDF",
                "style": "Action.TButton",
                "command": lambda: self.quick_export_visualization("PDF"),
                "state": "disabled",
                "width": 5,
                "parent": "quick_export_frame",
                "pack_opts": {"side": tk.RIGHT, "padx": (0, 2)},
            },
        ]
        # ------------------------------------------------

        # Quick export buttons for common formats
        quick_export_frame = ttk.Frame(export_frame, style="Card.TFrame")
        quick_export_frame.pack(side=tk.RIGHT, padx=(0, 10))

        # Store button references for later access if needed
        self.export_buttons = {}

        # Create quick export buttons
        for btn_cfg in quick_export_buttons_config:
            btn = ttk.Button(
                quick_export_frame,
                text=btn_cfg["text"],
                style=btn_cfg["style"],
                command=btn_cfg["command"],
                state=btn_cfg["state"],
                width=btn_cfg["width"],
            )
            btn.pack(**btn_cfg["pack_opts"])
            setattr(self, btn_cfg["name"], btn)
            self.export_buttons[btn_cfg["name"]] = btn

        # Create main export buttons
        for btn_cfg in export_buttons_config:
            btn = ttk.Button(
                export_frame,
                text=btn_cfg["text"],
                style=btn_cfg["style"],
                command=btn_cfg["command"],
                state=btn_cfg["state"],
                width=btn_cfg["width"] if btn_cfg["width"] else None,
            )
            btn.pack(**btn_cfg["pack_opts"])
            setattr(self, btn_cfg["name"], btn)
            self.export_buttons[btn_cfg["name"]] = btn

    def show_process_time_table(self):
        """Show the Process Time Table for comparing AnyLogic simulation with historical data."""
        if not self.data_loader:
            messagebox.showwarning("No Data Loader", "Please load clinic data first.")
            return

        try:
            # Check if window already exists
            if (
                not hasattr(self, "process_time_window")
                or not self.process_time_window.winfo_exists()
            ):
                # Create new window
                self.process_time_window = ProcessTimeTableWindow(
                    self.root, self.data_loader
                )
            else:
                # Bring existing window to front
                self.process_time_window.show()

        except Exception as e:
            self.logger.error(f"Error opening Process Time Table: {e}")
            messagebox.showerror(
                "Error", f"Failed to open Process Time Table:\n{str(e)}"
            )

    def _update_time_options(self):
        """
        Update time filter options to only allow earliest and latest hour in the dataset, rounded as needed.
        Key configurations are defined as class-level or method-level variables for easy tweaking.
        """
        # --- Configurable parameters ---
        TIME_COLUMN = "Action Timestamp (HH:MM)"
        TIME_FORMAT = "%H:%M"
        ROUND_TO_HOUR = True  # If False, disables rounding logic
        TIME_FREQ = "h"  # Pandas date_range frequency string
        TIME_DISPLAY_FORMAT = "%H:00"
        # -------------------------------

        if (
            self.processor
            and hasattr(self.processor, "data_loader")
            and self.processor.data_loader.get_data() is not None
        ):
            try:
                data = self.processor.data_loader.get_data()
                if TIME_COLUMN in data.columns:
                    times = pd.to_datetime(
                        data[TIME_COLUMN].astype(str).str.strip(),
                        format=TIME_FORMAT,
                        errors="coerce",
                    )
                    times = times.dropna()
                    if not times.empty:
                        min_time = times.min()
                        max_time = times.max()
                        if ROUND_TO_HOUR:
                            # Round min down to hour, max up to next hour
                            min_hour = min_time.replace(minute=0, second=0)
                            max_hour = max_time.replace(minute=0, second=0)
                            if max_time.minute > 0:
                                from datetime import timedelta

                                max_hour = max_hour + timedelta(hours=1)
                        else:
                            min_hour = min_time
                            max_hour = max_time
                        # Build list of hour strings
                        hour_range = pd.date_range(min_hour, max_hour, freq=TIME_FREQ)
                        time_values = [
                            t.strftime(TIME_DISPLAY_FORMAT) for t in hour_range
                        ]
                        if hasattr(self, "start_time_combo"):
                            self.start_time_combo["values"] = time_values
                            self.start_time_var.set(time_values[0])
                        if hasattr(self, "end_time_combo"):
                            self.end_time_combo["values"] = time_values
                            self.end_time_var.set(time_values[-1])
            except Exception as e:
                self.logger.error(f"Error updating time options: {e}")

    def reset_filters(self):
        """Reset all filter controls to default values."""
        combos = [
            ("start_date_combo", "start_date_var", 0),
            ("end_date_combo", "end_date_var", -1),
            ("start_time_combo", "start_time_var", 0),
            ("end_time_combo", "end_time_var", -1),
            ("service_type_combo", "service_type_var", 0),
            ("action_combo", "action_var", 0),
        ]
        for combo_name, var_name, idx in combos:
            combo = getattr(self, combo_name, None)
            var = getattr(self, var_name, None)
            if combo and combo["values"]:
                var.set(combo["values"][idx])
        if hasattr(self, "search_var"):
            self.search_var.set("")
        if hasattr(self, "patient_id_var"):
            self.patient_id_var.set("")
        self._update_filter_options()
        self._update_date_options()
        self._update_time_options()
        if getattr(self, "processor", None) and self.processor.has_data():
            self.root.after(100, self.generate_visualization)

    def _is_ui_ready(self):
        """Check if the UI is fully initialized and ready for theme switching."""
        return (
            hasattr(self, "main_frame")
            and self.main_frame is not None
            and hasattr(self, "root")
            and self.root is not None
            and self.root.winfo_exists()
            and self.ui_initialized
            and hasattr(self, "left_panel")
            and self.left_panel is not None
            and hasattr(self, "right_panel")
            and self.right_panel is not None
        )

    def _check_error_state(self, operation: str = None) -> bool:
        """
        Check if the application is in an error state.

        Args:
            operation: Optional operation name for logging

        Returns:
            bool: True if in error state, False otherwise
        """
        if self.error_state:
            if operation:
                self.logger.warning(
                    f"Operation '{operation}' blocked due to error state"
                )
            return True
        return False

    def _clear_error_state(self):
        """Clear the error state and allow normal operation to resume."""
        self.error_state = False
        self.last_error = None
        self.error_context = {}
        self.recovery_attempted = False

        self.logger.info("Application error state cleared")

    def _reset_filter_controls(self):
        """Reset all filter controls to default state."""
        try:
            # Reset date variables
            if hasattr(self, "start_date_var"):
                self.start_date_var.set("")
            if hasattr(self, "end_date_var"):
                self.end_date_var.set("")

            # Reset time variables
            if hasattr(self, "start_time_var"):
                self.start_time_var.set("")
            if hasattr(self, "end_time_var"):
                self.end_time_var.set("")

            # Reset service and action variables
            if hasattr(self, "service_type_var"):
                self.service_type_var.set("All")
            if hasattr(self, "action_var"):
                self.action_var.set("All")

            # Reset patient variables (fallback for backward compatibility)
            if hasattr(self, "patient_id_var"):
                self.patient_id_var.set("")
            if hasattr(self, "patient_date_var"):
                self.patient_date_var.set("")
            if hasattr(self, "search_var"):
                self.search_var.set("")

            # Reset VizControls if available
            if hasattr(self, "viz_controls") and self.viz_controls is not None:
                self.viz_controls.reset_selection()

            # Clear combobox values
            if hasattr(self, "start_date_combo"):
                self.start_date_combo["values"] = []
            if hasattr(self, "end_date_combo"):
                self.end_date_combo["values"] = []
            if hasattr(self, "start_time_combo"):
                self.start_time_combo["values"] = []
            if hasattr(self, "end_time_combo"):
                self.end_time_combo["values"] = []
            if hasattr(self, "service_type_combo"):
                self.service_type_combo["values"] = []
            if hasattr(self, "action_combo"):
                self.action_combo["values"] = []
            # Fallback: Clear patient combos directly (for backward compatibility)
            if hasattr(self, "patient_combo"):
                self.patient_combo["values"] = []
            if hasattr(self, "patient_date_combo"):
                self.patient_date_combo["values"] = []

        except Exception as e:
            self.logger.error(f"Error resetting filter controls: {e}")

    def _reset_ui_to_safe_state(self):
        """Reset the UI to a safe state after an error."""
        try:
            # Clear any loaded data
            if self.data_loader:
                self.data_loader.data = None
                self.data_loader.file_path = None

            # Reset processor
            self.processor = None

            # Clear quality issues
            self.data_quality_issues = None

            # Reset data flags
            self.data_loaded = False
            self.data_loading_complete = False

            # Update UI state
            self.update_ui_state()
            self.update_file_label()

            # Clear visualization
            self.update_figure_display(None)

            # Reset filter controls
            self._reset_filter_controls()

            # Disable visualization controls
            self._update_visualization_controls_state(False)

            self.logger.info("UI reset to safe state")

            # Update menu bar after UI reset
            if hasattr(self, "menu_bar_component"):
                self.menu_bar_component.update_menu_state(
                    data_loaded=False, visualization_available=False
                )

        except Exception as e:
            self.logger.error(f"Error resetting UI to safe state: {e}")

    def _set_error_state(self, error: Exception, context: Dict[str, Any] = None):
        """
        Set the application to error state and prevent UI updates.

        Args:
            error: The exception that occurred
            context: Additional context about the error
        """
        self.error_state = True
        self.last_error = error
        self.error_context = context or {}
        self.recovery_attempted = False

        self.logger.error(f"Application entered error state: {error}")
        self.logger.error(f"Error context: {context}")

        # Show error dialog
        self._show_error_dialog(error, context)

    def _show_error_dialog(self, error: Exception, context: Dict[str, Any] = None):
        """
        Show the error dialog with recovery options.

        Args:
            error: The exception that occurred
            context: Additional context about the error
        """
        try:
            # Define recovery callback
            def recovery_callback():
                """Attempt to recover from the error."""
                self.logger.info("Attempting error recovery...")
                self.recovery_attempted = True

                # Clear error state
                self._clear_error_state()

                # Reset UI to safe state
                self._reset_ui_to_safe_state()

                # Show success message
                self.show_status(
                    "Error recovery completed. You can now try your operation again.",
                    "success",
                )

            # Show error dialog
            show_error_dialog(
                parent=self.root,
                error=error,
                context=context,
                recovery_callback=recovery_callback,
                colors=self.colors,
            )

        except Exception as e:
            self.logger.error(f"Error showing error dialog: {e}")
            # Fallback to simple message box
            messagebox.showerror(
                "Error", f"An error occurred: {error}\n\nContext: {context}"
            )

    def _show_data_comparison_interface(self):
        """Show the data comparison interface in the main visualization area."""
        try:
            self.logger.info("Starting to show data comparison interface...")

            # Clear existing visualization
            self._clear_vis_notebook_tabs()

            # Create a new tab for data comparison
            comparison_tab = ttk.Frame(self.vis_notebook)
            self.vis_notebook.add(comparison_tab, text="Data Comparison")
            self.vis_notebook.select(comparison_tab)

            self.logger.info(
                "Created comparison tab, initializing DataComparisonComponent..."
            )

            # Always create a new comparison component for the new tab
            # This ensures proper initialization and avoids reparenting issues
            self.comparison_component = DataComparisonComponent(
                parent=comparison_tab,
                main_data_loader=self.data_loader,
                colors=self.colors,
            )

            self.logger.info("DataComparisonComponent created successfully")

            # Update title
            self.title_label.config(text="Data Comparison Tool")

            # Enable export buttons (they will be handled by the comparison component)
            if hasattr(self, "export_button"):
                self.export_button.config(state="normal")
            if hasattr(self, "png_export_button"):
                self.png_export_button.config(state="normal")
            if hasattr(self, "pdf_export_button"):
                self.pdf_export_button.config(state="normal")

            self.show_status(
                "Data Comparison interface loaded. Load a reference file to begin comparison.",
                "info",
            )

        except Exception as e:
            self.logger.error(f"Error showing data comparison interface: {e}")
            self.show_status(
                f"Error loading data comparison interface: {str(e)}", "error"
            )

    def show_settings_dialog(self, tab_name=None):
        """Open the settings dialog window, optionally selecting a tab by name."""
        win = tk.Toplevel(self.root)
        win.title("Settings")

        # Create settings page with callback for configuration changes
        page = SettingsPage(win, on_config_change=self._on_settings_config_changed)
        page.pack(fill=tk.BOTH, expand=True)
        win.transient(self.root)
        win.grab_set()
        win.geometry("500x600")

        # Select the requested tab if provided
        if tab_name:
            try:
                page.select_tab(tab_name)
            except Exception as e:
                self.logger.warning(f"Could not select tab '{tab_name}': {e}")

        def on_closing():
            try:
                page.cleanup()
            except:
                pass
            win.destroy()

        win.protocol("WM_DELETE_WINDOW", on_closing)

    def figure_to_widget(self, fig, parent):
        canvas = FigureCanvasTkAgg(fig, master=parent)
        widget = canvas.get_tk_widget()
        canvas.draw()
        return widget

    def refresh_data(self):
        """Refresh/reload the current data file (F5 shortcut)"""
        if hasattr(self, 'last_loaded_file') and self.last_loaded_file:
            try:
                self.logger.info(f"Refreshing data from {self.last_loaded_file}")
                self.load_data_from_file(self.last_loaded_file)
                self.show_status("Data refreshed successfully", "success")
            except Exception as e:
                self.logger.error(f"Error refreshing data: {e}")
                self.show_status(f"Error refreshing data: {str(e)}", "error")
        else:
            # No file loaded yet, just open file dialog
            self.load_data()

    def close_current_tab(self):
        """Close the currently selected tab (Ctrl+W shortcut)"""
        try:
            if hasattr(self, 'vis_notebook') and self.vis_notebook:
                current_tab = self.vis_notebook.select()
                if current_tab:
                    # Don't close the welcome tab
                    tab_text = self.vis_notebook.tab(current_tab, "text")
                    if tab_text.lower() != "welcome":
                        self.vis_notebook.forget(current_tab)
                        self.logger.info(f"Closed tab: {tab_text}")
                        self.show_status(f"Closed tab: {tab_text}", "info")
                        
                        # If no tabs left, show welcome tab
                        if len(self.vis_notebook.tabs()) == 0:
                            self._show_welcome_placeholder()
        except Exception as e:
            self.logger.error(f"Error closing tab: {e}")

    def switch_to_tab(self, tab_index):
        """Switch to tab by index (Ctrl+1, Ctrl+2, etc. shortcuts)"""
        try:
            if hasattr(self, 'vis_notebook') and self.vis_notebook:
                tabs = self.vis_notebook.tabs()
                if 0 <= tab_index < len(tabs):
                    self.vis_notebook.select(tabs[tab_index])
                    tab_text = self.vis_notebook.tab(tabs[tab_index], "text")
                    self.logger.info(f"Switched to tab {tab_index + 1}: {tab_text}")
        except Exception as e:
            self.logger.error(f"Error switching to tab {tab_index}: {e}")

    def show_settings_shortcut(self):
        """Open settings dialog (Ctrl+, shortcut)"""
        self.show_settings_dialog()

    def show_shortcuts_shortcut(self):
        """Show shortcuts dialog (Ctrl+H shortcut)"""
        self._show_shortcuts_dialog()
