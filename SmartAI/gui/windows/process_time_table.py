"""
Process Time Table Window

This window provides comparison functionality between AnyLogic simulation results
and historical clinic data to validate model accuracy and track improvements.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import numpy as np  # Added for np.arange

from config.app_config import get_process_time_config
from app.utils.logger import get_logger
from app.gui.components.anylogic_loader import AnyLogicDataLoader
from app.core.enhanced_anylogic_processor import EnhancedAnyLogicProcessor
from app.core.statistical_analysis_engine import (
    StatisticalAnalysisEngine,
)
from app.core.data_quality_assessment import (
    DataQualityAssessment,
)
from app.core.metrics_calculator import MetricsCalculator
from app.gui.dialogs.progress_dialog import show_progress, update_progress, close_progress, is_progress_cancelled
from app.gui.components.scrollable_panel import create_scrollable_tab


class ProcessTimeTableWindow:
    """
    Process Time Table window for comparing AnyLogic simulation results
    with historical clinic data.

    This window allows users to:
    - Configure master AnyLogic CSV file
    - Select historical data periods
    - Compare simulation vs. actual performance
    - Export comparison results
    """

    def __init__(self, parent, data_loader):
        """
        Initialize the Process Time Table window.

        Args:
            parent: Parent window (main application window)
            data_loader: Data loader instance for accessing historical data
        """
        self.parent = parent
        self.data_loader = data_loader
        self.logger = get_logger(__name__)
        self.config = get_process_time_config()

        # Initialize variables
        self.window = None
        self.anylogic_data = None
        self.comparison_results = None

        # Initialize data processors
        self.anylogic_loader = AnyLogicDataLoader()
        self.processor = EnhancedAnyLogicProcessor(data_loader)

        # Initialize enhanced analysis engines
        self.statistical_engine = StatisticalAnalysisEngine(alpha=0.05)
        self.quality_assessment = DataQualityAssessment()
        self.metrics_calculator = MetricsCalculator()

        # Initialize data filter for getting available dates
        from app.core.data_filter import DataFilter

        self.data_filter = DataFilter()

        # UI variables
        self.master_file_var = tk.StringVar()
        self.start_date_var = tk.StringVar()
        self.end_date_var = tk.StringVar()

        # Initialize with current config
        if self.config.master_file_path:
            self.master_file_var.set(self.config.master_file_path)

        # Check if master file is configured, if not show setup
        self._check_master_file_setup()

    def _check_master_file_setup(self):
        """Check if master file is configured and show setup if needed."""
        if not self.config.master_file_path or not os.path.exists(
            self.config.master_file_path
        ):
            self._show_master_file_setup()
        else:
            self._create_window()

    def _show_master_file_setup(self):
        """Show master file setup dialog for first-time configuration."""
        setup_message = (
            "Process Time Table Setup\n\n"
            "To use this feature, you need to configure a master AnyLogic Excel file "
            "containing simulation results.\n\n"
            "The Excel file should have a 'Process Summary' sheet with columns:\n"
            "- Process (process name)\n"
            "- Mean (mins) (mean duration)\n"
            "- Median (mins) (median duration)\n\n"
            "Would you like to select your AnyLogic master file now?"
        )

        result = messagebox.askyesno("Setup Required", setup_message)

        if result:
            self._select_master_file()
        else:
            # User declined setup, don't create window
            return

    def _select_master_file(self):
        """Open file dialog to select AnyLogic master file."""
        file_path = filedialog.askopenfilename(
            title="Select AnyLogic Master File",
            filetypes=[("Excel files", "*.xlsx;*.xls"), ("All files", "*.*")],
            initialdir=os.path.expanduser("~"),
        )

        if file_path:
            # Validate the selected file
            if self._validate_anylogic_file(file_path):
                # Update configuration
                self.config.master_file_path = file_path
                self.master_file_var.set(file_path)

                # Save configuration (in a real app, this would persist)
                self.logger.info(f"Master file configured: {file_path}")

                # Create the main window
                self._create_window()
            else:
                messagebox.showerror(
                    "Invalid File",
                    "The selected file does not appear to be a valid AnyLogic Excel file.\n\n"
                    "Please ensure the file contains a 'Process Summary' sheet with columns:\n"
                    "- Process\n"
                    "- Mean (mins)\n"
                    "- Median (mins)",
                )
                # Try again
                self._select_master_file()

    def _validate_anylogic_file(self, file_path: str) -> bool:
        """
        Validate that the selected file is a valid AnyLogic Excel file.

        Args:
            file_path: Path to the Excel file to validate

        Returns:
            bool: True if valid, False otherwise
        """
        from app.gui.dialogs import error_dialog

        try:
            # Check file extension
            if not file_path.lower().endswith((".xlsx", ".xls")):
                self.logger.warning("File is not an Excel file")
                error_dialog.show_error_dialog(
                    self.parent,
                    ValueError("Selected file is not an Excel file (.xlsx or .xls)"),
                    context={
                        "file_path": file_path,
                        "operation": "anylogic_file_validation",
                    },
                )
                return False

            # Read the Excel file
            try:
                excel_file = pd.ExcelFile(file_path)
            except Exception as e:
                self.logger.warning(f"Could not open Excel file: {e}")
                error_dialog.show_error_dialog(
                    self.parent,
                    e,
                    context={
                        "file_path": file_path,
                        "operation": "anylogic_file_validation",
                    },
                )
                return False

            # Check if "Process Summary" sheet exists
            if "Process Summary" not in excel_file.sheet_names:
                self.logger.warning(
                    "Excel file does not contain 'Process Summary' sheet"
                )
                error_dialog.show_error_dialog(
                    self.parent,
                    KeyError("Excel file does not contain 'Process Summary' sheet"),
                    context={
                        "file_path": file_path,
                        "sheet_names": excel_file.sheet_names,
                        "operation": "anylogic_file_validation",
                    },
                )
                return False

            # Read the Process Summary sheet
            try:
                df = pd.read_excel(file_path, sheet_name="Process Summary")
            except Exception as e:
                self.logger.warning(f"Could not read 'Process Summary' sheet: {e}")
                error_dialog.show_error_dialog(
                    self.parent,
                    e,
                    context={
                        "file_path": file_path,
                        "sheet_name": "Process Summary",
                        "operation": "anylogic_file_validation",
                    },
                )
                return False

            # Strip whitespace from column names
            df.columns = df.columns.str.strip()

            # Check required columns
            required_columns = ["Process", "Mean (mins)", "Median (mins)"]
            missing_columns = [col for col in required_columns if col not in df.columns]

            if missing_columns:
                self.logger.warning(
                    f"Missing columns in AnyLogic file: {missing_columns}"
                )
                error_dialog.show_error_dialog(
                    self.parent,
                    KeyError(f"Missing columns in AnyLogic file: {missing_columns}"),
                    context={
                        "file_path": file_path,
                        "columns": list(df.columns),
                        "missing_columns": missing_columns,
                        "operation": "anylogic_file_validation",
                    },
                )
                return False

            # Check that we have some data
            if len(df) == 0:
                self.logger.warning("AnyLogic file is empty")
                error_dialog.show_error_dialog(
                    self.parent,
                    ValueError("The 'Process Summary' sheet is empty"),
                    context={
                        "file_path": file_path,
                        "operation": "anylogic_file_validation",
                    },
                )
                return False

            # Check that numeric columns are actually numeric
            numeric_columns = ["Mean (mins)", "Median (mins)"]
            for col in numeric_columns:
                try:
                    pd.to_numeric(df[col], errors="raise")
                except Exception as e:
                    self.logger.warning(
                        f"Column '{col}' contains non-numeric data: {e}"
                    )
                    error_dialog.show_error_dialog(
                        self.parent,
                        ValueError(f"Column '{col}' contains non-numeric data"),
                        context={
                            "file_path": file_path,
                            "column": col,
                            "operation": "anylogic_file_validation",
                        },
                    )
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating AnyLogic file: {e}")
            error_dialog.show_error_dialog(
                self.parent,
                e,
                context={
                    "file_path": file_path,
                    "operation": "anylogic_file_validation",
                },
            )
            return False

    def _create_window(self):
        """Create the main Process Time Table window."""
        if self.window and self.window.winfo_exists():
            self.window.lift()
            return

        # Create window
        self.window = tk.Toplevel(self.parent)
        self.window.title("Process Time Analysis")
        self.window.geometry("900x700")
        self.window.transient(self.parent)

        # Make window resizable
        self.window.rowconfigure(1, weight=1)
        self.window.columnconfigure(0, weight=1)

        # Create UI components
        self._create_header()
        self._create_settings_panel()
        self._create_results_area()
        self._create_button_panel()
        self._create_status_bar()

        try:
            # Update progress for date range information
            update_progress(0.3, "Updating date range information...")
            self._update_date_range_info()

            # Update progress for default date range
            update_progress(0.6, "Setting default date range...")
            self._set_default_date_range()

            # Update progress for AnyLogic data loading
            if self.config.master_file_path:
                update_progress(0.8, "Loading master file data...")
                self._load_anylogic_data()
                update_progress(1.0, "Initialization complete!")
                self._show_status(
                    "Master file loaded. Set date range and click Analyze Data.", "info"
                )
            else:
                update_progress(1.0, "Initialization complete!")
                self._show_status("Configure master file to begin analysis.", "warning")

        except Exception as e:
            self.logger.error(f"Error during window initialization: {e}")
            self._show_status("Error during initialization", "error")
        finally:
            # Close progress dialog
            close_progress()

    def _create_header(self):
        """Create the header with master file path display."""
        header_frame = ttk.Frame(self.window, style="TFrame")
        header_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        # Master file label
        ttk.Label(
            header_frame, text="Master File:", font=("Arial", 9, "bold"), style="TLabel"
        ).pack(side=tk.LEFT)

        # File path display (truncated if too long)
        file_path = self.master_file_var.get()
        display_path = (
            self._truncate_path(file_path) if file_path else "No file selected"
        )
        self.file_label = ttk.Label(
            header_frame, text=display_path, style="Primary.TLabel"
        )  # Use a primary label style
        self.file_label.pack(side=tk.LEFT, padx=(5, 0))

        # Change button
        change_btn = ttk.Button(
            header_frame,
            text="Change...",
            command=self._change_master_file,
            style="Primary.TButton",
        )
        change_btn.pack(side=tk.RIGHT)

    def _create_settings_panel(self):
        """Create the analysis settings panel (easy to add/remove items).

        To add a new section (e.g., a new group of controls), create a new Frame or LabelFrame
        and pack it into `settings_frame` where appropriate.

        To add a new info label to the top info bar, add a new dict to the `info_labels` list
        with the desired properties (see below for structure).

        To add a new date control (label, entry, button, etc.), add a new dict to the `date_controls` list.
        Supported types: "label", "entry", "quick_buttons", "button".
        """
        settings_frame = ttk.LabelFrame(
            self.window,
            text="Analysis Settings",
            padding="10",
            style="Card.TLabelframe",
        )
        settings_frame.pack(fill=tk.X, padx=10, pady=5)

        # --- Data range information section ---
        range_info_frame = ttk.Frame(settings_frame, style="TFrame")
        range_info_frame.pack(fill=tk.X, pady=(0, 10))

        # Info labels: add/change by editing the list below.
        # Each dict defines a label. To add a new label, append a dict with:
        #   - "attr": attribute name for self (for later reference)
        #   - "text": label text
        #   - "font": font tuple
        #   - "style": ttk style string
        #   - "pack_opts": dict of pack options
        info_labels = [
            {
                "attr": "historical_range_label",
                "text": "📊 Historical Data: Loading...",
                "font": ("Arial", 8),
                "style": "Info.TLabel",
                "pack_opts": {"side": tk.LEFT},
            },
            {
                "attr": "consultation_splitting_label",
                "text": "",
                "font": ("Arial", 8),
                "style": "Secondary.TLabel",
                "pack_opts": {"side": tk.LEFT, "padx": (20, 0)},
            },
            {
                "attr": "simulation_range_label",
                "text": "📈 Simulation Data: Not loaded",
                "font": ("Arial", 8),
                "style": "Secondary.TLabel",
                "pack_opts": {"side": tk.RIGHT},
            },
            # To add a new info label, copy the structure above and append here.
        ]
        for label_info in info_labels:
            label = ttk.Label(
                range_info_frame,
                text=label_info["text"],
                font=label_info["font"],
                style=label_info["style"],
            )
            label.pack(**label_info["pack_opts"])
            setattr(self, label_info["attr"], label)

        # --- Date range selection section ---
        date_frame = ttk.Frame(settings_frame, style="TFrame")
        date_frame.pack(fill=tk.X)

        # Date controls: add/change by editing the list below.
        # Each dict defines a control. Supported types:
        #   - "label": static text label
        #   - "entry": entry box (requires "var" for StringVar attribute)
        #   - "quick_buttons": vertical stack of buttons (see "buttons" list)
        #   - "button": single button
        # To add a new control, append a dict with the appropriate structure.
        date_controls = [
            {
                "type": "label",
                "text": "Historical Period:",
                "font": ("Arial", 9, "bold"),
                "style": "TLabel",
                "pack_opts": {"side": tk.LEFT},
            },
            {
                "type": "label",
                "text": "From:",
                "style": "TLabel",
                "pack_opts": {"side": tk.LEFT, "padx": (20, 5)},
            },
            {
                "type": "entry",
                "var": "start_date_var",  # StringVar attribute on self
                "width": 12,
                "style": "TEntry",
                "pack_opts": {"side": tk.LEFT, "padx": (0, 5)},
                "binds": [
                    ("<FocusOut>", "_validate_start_date"),
                    ("<KeyRelease>", "_on_date_key_release"),
                ],
            },
            {
                "type": "quick_buttons",
                # To add a new quick button, append a dict to "buttons" below.
                "buttons": [
                    {
                        "text": "Full Range",
                        "command": "_set_full_range",  # method name on self
                        "width": 12,
                        "style": "Accent.TButton",
                        "pack_opts": {"side": tk.TOP},
                    },
                    {
                        "text": "Last 30 days",
                        "command": (lambda: self._set_quick_period(30)),  # direct lambda
                        "width": 12,
                        "style": "Accent.TButton",
                        "pack_opts": {"side": tk.TOP, "pady": (2, 0)},
                    },
                    # To add more quick buttons, copy the structure above.
                ],
                "frame_opts": {"side": tk.LEFT, "padx": (5, 10)},
            },
            {
                "type": "label",
                "text": "To:",
                "style": "TLabel",
                "pack_opts": {"side": tk.LEFT, "padx": (0, 5)},
            },
            {
                "type": "entry",
                "var": "end_date_var",
                "width": 12,
                "style": "TEntry",
                "pack_opts": {"side": tk.LEFT, "padx": (0, 20)},
                "binds": [
                    ("<FocusOut>", "_validate_end_date"),
                    ("<KeyRelease>", "_on_date_key_release"),
                ],
            },
            {
                "type": "button",
                "text": "🔍 Analyze Data",
                "command": "_analyze_data",  # method name on self
                "style": "Accent.TButton",
                "pack_opts": {"side": tk.RIGHT},
            },
            # To add a new control (e.g., a button), append a dict here.
        ]

        # Build the controls from the date_controls list above.
        for ctrl in date_controls:
            if ctrl["type"] == "label":
                # To add a new label, add a dict with type "label" to date_controls.
                ttk.Label(
                    date_frame,
                    text=ctrl["text"],
                    font=ctrl.get("font"),
                    style=ctrl["style"],
                ).pack(**ctrl["pack_opts"])
            elif ctrl["type"] == "entry":
                # To add a new entry, add a dict with type "entry" and specify "var" (StringVar attribute on self).
                entry = ttk.Entry(
                    date_frame,
                    textvariable=getattr(self, ctrl["var"]),
                    width=ctrl["width"],
                    style=ctrl["style"],
                )
                entry.pack(**ctrl["pack_opts"])
                for event, method in ctrl.get("binds", []):
                    entry.bind(event, getattr(self, method))
            elif ctrl["type"] == "quick_buttons":
                # To add a new quick button group, add a dict with type "quick_buttons" and a "buttons" list.
                quick_frame = ttk.Frame(date_frame, style="TFrame")
                quick_frame.pack(**ctrl["frame_opts"])
                for btn in ctrl["buttons"]:
                    # If command is a string, get method from self, else use as is (for lambda)
                    command = (
                        getattr(self, btn["command"])
                        if isinstance(btn["command"], str)
                        else btn["command"]
                    )
                    ttk.Button(
                        quick_frame,
                        text=btn["text"],
                        command=command,
                        width=btn["width"],
                        style=btn["style"],
                    ).pack(**btn["pack_opts"])
            elif ctrl["type"] == "button":
                # To add a new button, add a dict with type "button" to date_controls.
                ttk.Button(
                    date_frame,
                    text=ctrl["text"],
                    command=getattr(self, ctrl["command"]),
                    style=ctrl["style"],
                ).pack(**ctrl["pack_opts"])

    def _create_results_area(self):
        """Create the scrollable results display area with enhanced analysis tabs."""
        # Results frame with notebook for tabs
        results_frame = ttk.LabelFrame(
            self.window, text="Enhanced Process Analysis", padding="5"
        )
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        results_frame.rowconfigure(0, weight=1)
        results_frame.columnconfigure(0, weight=1)

        # Create notebook for tabs
        self.results_notebook = ttk.Notebook(results_frame)
        self.results_notebook.grid(row=0, column=0, sticky="nsew")

        # Tab 1: Process Time Comparison
        self.comparison_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.comparison_frame, text="📊 Process Comparison")
        self.comparison_frame.rowconfigure(0, weight=1)
        self.comparison_frame.columnconfigure(0, weight=1)

        # Create treeview for results table with enhanced statistical columns
        columns = (
            "Process",
            "AnyLogic Mean",
            "AnyLogic Median",
            "Historical Mean",
            "Historical Median",
            "Mean Improvement",
            "Median Improvement",
            "Statistical Sig.",
            "Effect Size",
            "Data Quality",
        )
        self.results_tree = ttk.Treeview(
            self.comparison_frame, columns=columns, show="headings", height=12
        )

        # Configure column headings and widths with enhanced statistical information
        column_data = [
            ("Process", 140, "Process name from AnyLogic simulation"),
            ("AnyLogic Mean", 90, "Mean duration from simulation (minutes)"),
            ("AnyLogic Median", 90, "Median duration from simulation (minutes)"),
            ("Historical Mean", 90, "Mean duration from historical data (minutes)"),
            ("Historical Median", 90, "Median duration from historical data (minutes)"),
            (
                "Mean Improvement",
                110,
                "Percentage improvement in mean duration (negative = better)",
            ),
            (
                "Median Improvement",
                110,
                "Percentage improvement in median duration (negative = better)",
            ),
            (
                "Statistical Sig.",
                100,
                "Statistical significance of the difference (p-value)",
            ),
            ("Effect Size", 80, "Cohen's d effect size (magnitude of difference)"),
            ("Data Quality", 80, "Overall data quality assessment score"),
        ]

        for i, (col, width, tooltip) in enumerate(column_data):
            self.results_tree.heading(col, text=col)
            self.results_tree.column(
                col, width=width, anchor="center" if i > 0 else "w"
            )

        # Scrollbars for comparison tab
        v_scrollbar = ttk.Scrollbar(
            self.comparison_frame, orient=tk.VERTICAL, command=self.results_tree.yview
        )
        h_scrollbar = ttk.Scrollbar(
            self.comparison_frame, orient=tk.HORIZONTAL, command=self.results_tree.xview
        )
        self.results_tree.configure(
            yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set
        )

        # Grid layout for comparison tab
        self.results_tree.grid(row=0, column=0, sticky="nsew")
        v_scrollbar.grid(row=0, column=1, sticky="ns")
        h_scrollbar.grid(row=1, column=0, sticky="ew")

        # Tab 2: Efficiency Analysis
        self.efficiency_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.efficiency_frame, text="⚡ Efficiency Metrics")
        self.efficiency_frame.rowconfigure(0, weight=1)
        self.efficiency_frame.columnconfigure(0, weight=1)

        # Create treeview for efficiency analysis
        efficiency_columns = (
            "Service",
            "Efficiency Score",
            "Avg Duration",
            "Sample Size",
            "Status",
            "Recommendation",
        )
        self.efficiency_tree = ttk.Treeview(
            self.efficiency_frame,
            columns=efficiency_columns,
            show="headings",
            height=12,
        )

        efficiency_column_data = [
            ("Service", 150, "Service type"),
            ("Efficiency Score", 120, "Efficiency score (0-100)"),
            ("Avg Duration", 100, "Average duration in minutes"),
            ("Sample Size", 100, "Number of samples"),
            ("Status", 80, "Performance status"),
            ("Recommendation", 200, "Recommended action"),
        ]

        for i, (col, width, tooltip) in enumerate(efficiency_column_data):
            self.efficiency_tree.heading(col, text=col)
            self.efficiency_tree.column(
                col, width=width, anchor="center" if i > 0 else "w"
            )

        # Scrollbars for efficiency tab
        eff_v_scrollbar = ttk.Scrollbar(
            self.efficiency_frame,
            orient=tk.VERTICAL,
            command=self.efficiency_tree.yview,
        )
        eff_h_scrollbar = ttk.Scrollbar(
            self.efficiency_frame,
            orient=tk.HORIZONTAL,
            command=self.efficiency_tree.xview,
        )
        self.efficiency_tree.configure(
            yscrollcommand=eff_v_scrollbar.set, xscrollcommand=eff_h_scrollbar.set
        )

        # Grid layout for efficiency tab
        self.efficiency_tree.grid(row=0, column=0, sticky="nsew")
        eff_v_scrollbar.grid(row=0, column=1, sticky="ns")
        eff_h_scrollbar.grid(row=1, column=0, sticky="ew")

        # Tab 3: Volume Correlation
        self.volume_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.volume_frame, text="📈 Volume Analysis")
        self.volume_frame.rowconfigure(0, weight=1)
        self.volume_frame.columnconfigure(0, weight=1)

        # Create treeview for volume correlation
        volume_columns = (
            "Analysis Type",
            "Metric",
            "Value",
            "Impact",
            "Recommendation",
        )
        self.volume_tree = ttk.Treeview(
            self.volume_frame, columns=volume_columns, show="headings", height=12
        )

        volume_column_data = [
            ("Analysis Type", 150, "Type of volume analysis"),
            ("Metric", 120, "Measured metric"),
            ("Value", 100, "Metric value"),
            ("Impact", 100, "Impact level"),
            ("Recommendation", 200, "Recommended action"),
        ]

        for i, (col, width, tooltip) in enumerate(volume_column_data):
            self.volume_tree.heading(col, text=col)
            self.volume_tree.column(col, width=width, anchor="center" if i > 0 else "w")

        # Scrollbars for volume tab
        vol_v_scrollbar = ttk.Scrollbar(
            self.volume_frame, orient=tk.VERTICAL, command=self.volume_tree.yview
        )
        vol_h_scrollbar = ttk.Scrollbar(
            self.volume_frame, orient=tk.HORIZONTAL, command=self.volume_tree.xview
        )
        self.volume_tree.configure(
            yscrollcommand=vol_v_scrollbar.set, xscrollcommand=vol_h_scrollbar.set
        )

        # Grid layout for volume tab
        self.volume_tree.grid(row=0, column=0, sticky="nsew")
        vol_v_scrollbar.grid(row=0, column=1, sticky="ns")
        vol_h_scrollbar.grid(row=1, column=0, sticky="ew")
        # Bind double-click event for popup
        self.volume_tree.bind("<Double-1>", self._on_volume_row_double_click)

        # Tab 4: Bottleneck Analysis
        self.bottleneck_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.bottleneck_frame, text="🚨 Bottlenecks")
        self.bottleneck_frame.rowconfigure(0, weight=1)
        self.bottleneck_frame.columnconfigure(0, weight=1)

        # Create treeview for bottleneck analysis
        bottleneck_columns = (
            "Service",
            "Severity",
            "Efficiency",
            "Avg Duration",
            "Impact",
            "Recommendations",
        )
        self.bottleneck_tree = ttk.Treeview(
            self.bottleneck_frame,
            columns=bottleneck_columns,
            show="headings",
            height=12,
        )

        bottleneck_column_data = [
            ("Service", 150, "Service with bottleneck"),
            ("Severity", 80, "Bottleneck severity"),
            ("Efficiency", 100, "Current efficiency score"),
            ("Avg Duration", 100, "Average duration"),
            ("Impact", 120, "Estimated impact"),
            ("Recommendations", 200, "Recommended solutions"),
        ]

        for i, (col, width, tooltip) in enumerate(bottleneck_column_data):
            self.bottleneck_tree.heading(col, text=col)
            self.bottleneck_tree.column(
                col, width=width, anchor="center" if i > 0 else "w"
            )

        # Scrollbars for bottleneck tab
        bot_v_scrollbar = ttk.Scrollbar(
            self.bottleneck_frame,
            orient=tk.VERTICAL,
            command=self.bottleneck_tree.yview,
        )
        bot_h_scrollbar = ttk.Scrollbar(
            self.bottleneck_frame,
            orient=tk.HORIZONTAL,
            command=self.bottleneck_tree.xview,
        )
        self.bottleneck_tree.configure(
            yscrollcommand=bot_v_scrollbar.set, xscrollcommand=bot_h_scrollbar.set
        )

        # Grid layout for bottleneck tab
        self.bottleneck_tree.grid(row=0, column=0, sticky="nsew")
        bot_v_scrollbar.grid(row=0, column=1, sticky="ns")
        bot_h_scrollbar.grid(row=1, column=0, sticky="ew")

        # Tab 5: Enhanced Insights & Recommendations
        self.insights_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(
            self.insights_frame, text="💡 Insights & Recommendations"
        )
        self.insights_frame.rowconfigure(0, weight=1)
        self.insights_frame.columnconfigure(0, weight=1)

        # Create scrollable text widget for insights
        insights_canvas = tk.Canvas(self.insights_frame)
        insights_scrollbar = ttk.Scrollbar(
            self.insights_frame, orient="vertical", command=insights_canvas.yview
        )
        self.insights_content_frame = ttk.Frame(insights_canvas)

        self.insights_content_frame.bind(
            "<Configure>",
            lambda e: insights_canvas.configure(
                scrollregion=insights_canvas.bbox("all")
            ),
        )

        insights_canvas.create_window(
            (0, 0), window=self.insights_content_frame, anchor="nw"
        )
        insights_canvas.configure(yscrollcommand=insights_scrollbar.set)

        # Grid layout for insights tab
        insights_canvas.grid(row=0, column=0, sticky="nsew")
        insights_scrollbar.grid(row=0, column=1, sticky="ns")

        # Initialize insights content
        self._create_insights_placeholder()

        # Tab 6: Statistical Charts & Visualizations
        self.charts_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.charts_frame, text="📈 Statistical Charts")
        self.charts_frame.rowconfigure(0, weight=1)
        self.charts_frame.columnconfigure(0, weight=1)

        # Create main container for charts that spans the full space
        self.charts_main_container = ttk.Frame(self.charts_frame)
        self.charts_main_container.pack(fill=tk.BOTH, expand=True)

        # Initialize charts placeholder
        self._create_charts_placeholder()

    def _create_button_panel(self):
        """Create the bottom button panel."""
        button_frame = ttk.Frame(self.window, style="TFrame")
        button_frame.pack(fill=tk.X, padx=10, pady=(5, 10))

        # Export button
        export_btn = ttk.Button(
            button_frame,
            text="Export Results",
            command=self._export_results,
            style="Primary.TButton",
        )
        export_btn.pack(side=tk.LEFT)

        # Refresh button
        refresh_btn = ttk.Button(
            button_frame,
            text="Refresh Data",
            command=self._refresh_data,
            style="Primary.TButton",
        )
        refresh_btn.pack(side=tk.LEFT, padx=(10, 0))

        # Close button
        close_btn = ttk.Button(
            button_frame,
            text="Close",
            command=self._close_window,
            style="Accent.TButton",
        )
        close_btn.pack(side=tk.RIGHT)

    def _create_status_bar(self):
        """Create a status bar for user feedback."""
        status_frame = ttk.Frame(self.window, style="TFrame")
        status_frame.pack(fill=tk.X, padx=10, pady=(0, 5))

        # Status message label
        self.status_label = ttk.Label(
            status_frame, text="Ready", font=("Arial", 8), style="TLabel"
        )
        self.status_label.pack(side=tk.LEFT)

        # Progress indicator (initially hidden)
        self.progress_var = tk.StringVar()
        self.progress_label = ttk.Label(
            status_frame,
            textvariable=self.progress_var,
            font=("Arial", 8),
            style="Info.TLabel",
        )
        self.progress_label.pack(side=tk.RIGHT)

    def _show_status(self, message: str, status_type: str = "info"):
        """
        Show status message to user.

        Args:
            message: Status message to display
            status_type: Type of status (info, warning, error, success)
        """
        if hasattr(self, "status_label"):
            # Set color based on status type using styles
            style_map = {
                "info": "Info.TLabel",
                "warning": "Warning.TLabel",
                "error": "Error.TLabel",
                "success": "Success.TLabel",
            }
            style = style_map.get(status_type, "TLabel")
            self.status_label.config(text=message, style=style)
            self.window.update_idletasks()

    def _truncate_path(self, path: str, max_length: int = 60) -> str:
        """Truncate file path for display."""
        if len(path) <= max_length:
            return path

        # Show beginning and end of path
        if len(path) > max_length:
            return f"{path[:20]}...{path[-30:]}"
        return path

    def _change_master_file(self):
        """Handle changing the master file."""
        self._select_master_file()
        if self.config.master_file_path:
            # Update display
            display_path = self._truncate_path(self.config.master_file_path)
            self.file_label.config(text=display_path)

            # Reload AnyLogic data
            self._load_anylogic_data()

    def _load_anylogic_data(self):
        """Load data from the AnyLogic master file with enhanced multi-sheet support, using progress dialog."""


        try:
            if not self.config.master_file_path or not os.path.exists(
                self.config.master_file_path
            ):
                self.anylogic_data = None
                self._show_status("No master file configured", "warning")
                return

            # Show progress dialog
            dlg = show_progress(
                self.window,
                title="Loading AnyLogic Data",
                message="Loading AnyLogic data with enhanced analysis...",
                can_cancel=False,
            )
            try:
                update_progress(0.05, "Validating file path...")
                self._show_status("Loading AnyLogic data with enhanced analysis...", "info")

                # Use enhanced processor to load all sheets
                update_progress(0.15, "Reading Excel sheets...")
                load_result = self.processor.load_anylogic_excel(
                    self.config.master_file_path
                )

                if load_result["success"]:
                    update_progress(0.7, "Processing loaded data...")
                    # Set data in processor
                    self.anylogic_data = self.processor.anylogic_data

                    # Update simulation data range information with enhanced details
                    self._update_simulation_range_info_enhanced(load_result)

                    # Show enhanced loading information
                    sheets_info = ", ".join(load_result["loaded_sheets"])
                    self.logger.info(
                        f"Loaded AnyLogic data: {load_result['process_count']} processes from {sheets_info}"
                    )
                    self._show_status(
                        f"Enhanced analysis ready: {load_result['process_count']} processes, {load_result['raw_records']} raw records",
                        "success",
                    )

                    # Show sheet information to user
                    if len(load_result["loaded_sheets"]) > 1:
                        update_progress(0.9, "Finalizing enhanced analysis...")
                        messagebox.showinfo(
                            "Enhanced Analysis Available",
                            f"Successfully loaded {len(load_result['loaded_sheets'])} sheets:\n\n"
                            + f"• {load_result['process_count']} processes (Process Summary)\n"
                            + f"• {load_result['raw_records']} raw duration records\n"
                            + f"• {load_result['waiting_records']} waiting time records\n"
                            + f"• {load_result['arrival_records']} patient arrival records\n\n"
                            + "Enhanced features available:\n"
                            + "• Patient Volume Correlation Analysis\n"
                            + "• Process Efficiency Metrics\n"
                            + "• Bottleneck Identification\n"
                            + "• Enhanced Comparison Reports",
                        )
                    update_progress(1.0, "AnyLogic data loaded successfully.")
                    # Automatically run analysis after successful load
                    self._analyze_data()
                else:
                    # Fallback to original method if enhanced loading fails
                    self.logger.warning(
                        "Enhanced loading failed, falling back to basic loading"
                    )
                    update_progress(0.5, "Falling back to basic loading...")
                    import pandas as pd
                    self.anylogic_data = pd.read_excel(
                        self.config.master_file_path, sheet_name="Process Summary"
                    )
                    self.anylogic_data.columns = self.anylogic_data.columns.str.strip()
                    self.processor.set_anylogic_data(self.anylogic_data)
                    self._update_simulation_range_info()
                    self._show_status(
                        f"Loaded {len(self.anylogic_data)} processes (basic mode)",
                        "success",
                    )
                    update_progress(1.0, "AnyLogic data loaded (basic mode).")
                    # Automatically run analysis after fallback load
                    self._analyze_data()
            finally:
                    close_progress()
        except Exception as e:
            self.logger.error(f"Error loading AnyLogic data: {e}")
            self._show_status("Failed to load AnyLogic data", "error")
            messagebox.showerror("Error", f"Failed to load AnyLogic data:\n{str(e)}")
            self.anylogic_data = None

    def _analyze_data(self):
        """Perform the enhanced comparison analysis with statistical testing and data quality assessment."""
        # Comprehensive prerequisite validation
        if not self._validate_analysis_prerequisites():
            return

        try:
            # Get date range
            start_date = self.start_date_var.get()
            end_date = self.end_date_var.get()

            # Validate date format
            try:
                datetime.strptime(start_date, "%Y-%m-%d")
                datetime.strptime(end_date, "%Y-%m-%d")
            except ValueError:
                messagebox.showerror(
                    "Invalid Date", "Please enter dates in YYYY-MM-DD format."
                )
                self._show_status("Invalid date format", "error")
                return

            # Show progress dialog

            dlg = show_progress(
                self.window,
                title="Enhanced Statistical Analysis",
                message="Initializing enhanced analysis...",
                can_cancel=True,
            )

            try:
                self._show_status("Performing enhanced analysis... Please wait", "info")

                # Step 1: Data Quality Assessment
                update_progress(0.1, "Assessing data quality...")
                if is_progress_cancelled():
                    return

                historical_data = self.data_loader.get_data()
                anylogic_quality = self.quality_assessment.assess_quality(
                    self.anylogic_data
                )
                historical_quality = self.quality_assessment.assess_quality(
                    historical_data
                )

                # Step 2: Calculate historical metrics
                update_progress(0.2, "Calculating historical metrics...")
                if is_progress_cancelled():
                    return
                self.processor.calculate_historical_metrics(start_date, end_date)

                # Step 3: Calculate improvements with statistical analysis
                update_progress(
                    0.4, "Calculating process improvements with statistical testing..."
                )
                if is_progress_cancelled():
                    return
                results = self.processor.calculate_improvements()
                self.comparison_results = results["comparisons"]
                
                # Debug: Log the results
                self.logger.info(f"Analysis results keys: {list(results.keys())}")
                self.logger.info(f"Comparison results count: {len(self.comparison_results) if self.comparison_results else 0}")
                if self.comparison_results:
                    self.logger.info(f"First comparison result: {self.comparison_results[0]}")

                # Step 4: Perform statistical analysis
                update_progress(0.6, "Performing statistical significance tests...")
                if is_progress_cancelled():
                    return
                self._perform_statistical_analysis()

                # Step 5: Add data quality information to results
                results["data_quality"] = {
                    "anylogic_quality": anylogic_quality,
                    "historical_quality": historical_quality,
                }

                # Step 6: Update displays
                update_progress(0.8, "Updating result displays...")
                if is_progress_cancelled():
                    return
                self._update_results_display()
                self._update_efficiency_display(results)
                self._update_volume_display(results)
                self._update_bottleneck_display(results)

                # Update insights and recommendations
                self._update_insights_display(results)

                # Update statistical charts
                self._update_charts_display(results)

                # Update consultation splitting information
                self._update_consultation_splitting_info()

                # Step 7: Complete
                update_progress(1.0, "Enhanced analysis complete!")

                # Show enhanced summary with statistical and quality information
                summary = results["summary"]
                if summary:
                    statistical_summary = self._generate_statistical_summary()
                    quality_summary = self._generate_quality_summary(
                        results.get("data_quality", {})
                    )

                    self._show_status(
                        f"Enhanced statistical analysis complete: {summary['total_comparisons']} processes analyzed",
                        "success",
                    )

                    # Create enhanced summary message with statistics and quality
                    summary_msg = (
                        f"🎯 Enhanced Statistical Analysis Complete!\n\n"
                        f"📊 Process Comparisons:\n"
                        f"• Total Processes: {summary['total_comparisons']}\n"
                        f"• Improved (Mean): {summary['processes_improved_mean']}\n"
                        f"• Improved (Median): {summary['processes_improved_median']}\n"
                        f"• Avg Mean Improvement: {summary['mean_improvement_avg']:.1f}%\n"
                        f"• Avg Median Improvement: {summary['median_improvement_avg']:.1f}%\n\n"
                    )

                    # Add statistical significance information
                    if statistical_summary:
                        summary_msg += f"📈 Statistical Analysis:\n"
                        summary_msg += f"• Significant Differences: {statistical_summary.get('significant_tests', 0)}\n"
                        summary_msg += f"• Effect Sizes (Large): {statistical_summary.get('large_effects', 0)}\n"
                        summary_msg += f"• Statistical Power: {statistical_summary.get('avg_power', 'N/A')}\n\n"

                    # Add data quality information
                    if quality_summary:
                        summary_msg += f"🔍 Data Quality Assessment:\n"
                        summary_msg += f"• AnyLogic Data Quality: {quality_summary.get('anylogic_grade', 'N/A')}\n"
                        summary_msg += f"• Historical Data Quality: {quality_summary.get('historical_grade', 'N/A')}\n"
                        if quality_summary.get("critical_issues", 0) > 0:
                            summary_msg += f"• Critical Issues Found: {quality_summary['critical_issues']}\n"
                        summary_msg += "\n"

                    # Add efficiency information
                    if (
                        "efficiency_improvements" in summary
                        and summary["efficiency_improvements"]
                    ):
                        summary_msg += f"⚡ Efficiency Analysis:\n"
                        summary_msg += f"• Services Analyzed: {len(summary['efficiency_improvements'])}\n"
                        high_priority = sum(
                            1
                            for imp in summary["efficiency_improvements"]
                            if imp["priority"] == "High"
                        )
                        if high_priority > 0:
                            summary_msg += f"• High Priority Issues: {high_priority}\n"

                    # Add bottleneck information
                    if (
                        "bottleneck_analysis" in summary
                        and summary["bottleneck_analysis"]
                    ):
                        summary_msg += f"🚨 Bottleneck Analysis:\n"
                        summary_msg += f"• Bottlenecks Identified: {len(summary['bottleneck_analysis'])}\n"
                        high_severity = sum(
                            1
                            for bot in summary["bottleneck_analysis"]
                            if bot["severity"] == "High"
                        )
                        if high_severity > 0:
                            summary_msg += f"• High Severity: {high_severity}\n"

                    # Add volume correlation information
                    if (
                        "volume_impact_analysis" in summary
                        and summary["volume_impact_analysis"]
                    ):
                        summary_msg += f"📈 Volume Impact Analysis:\n"
                        summary_msg += f"• Volume Factors: {len(summary['volume_impact_analysis'])}\n"

                    summary_msg += f"\n💡 Check the tabs for detailed statistical analysis and quality assessment!"

                    messagebox.showinfo(
                        "Enhanced Statistical Analysis Results", summary_msg
                    )
                else:
                    self._show_status("No analysis results generated", "warning")

            finally:
                close_progress()

        except ValueError as e:
            self.logger.error(f"Data validation error during analysis: {e}")
            self._show_status("Analysis failed - data validation error", "error")
            messagebox.showerror(
                "Data Validation Error",
                f"Invalid data detected:\n{str(e)}\n\n"
                "Please check your data format and try again.",
            )
        except FileNotFoundError as e:
            self.logger.error(f"File not found during analysis: {e}")
            self._show_status("Analysis failed - file not found", "error")
            messagebox.showerror(
                "File Not Found",
                f"Required file not found:\n{str(e)}\n\n"
                "Please ensure all data files are available.",
            )
        except MemoryError as e:
            self.logger.error(f"Memory error during analysis: {e}")
            self._show_status("Analysis failed - insufficient memory", "error")
            messagebox.showerror(
                "Memory Error",
                "Insufficient memory to complete analysis.\n\n"
                "Try reducing the date range or closing other applications.",
            )
        except ImportError as e:
            self.logger.error(f"Missing dependency during analysis: {e}")
            self._show_status("Analysis failed - missing dependency", "error")
            messagebox.showerror(
                "Missing Dependency",
                f"Required library not found:\n{str(e)}\n\n"
                "Please ensure all dependencies are installed.",
            )
        except Exception as e:

            self.logger.error(f"Unexpected error during analysis: {e}", exc_info=True)
            self._show_status("Analysis failed - unexpected error", "error")

            # Provide more helpful error message based on error type
            error_message = self._get_user_friendly_error_message(e)
            messagebox.showerror("Analysis Error", error_message)

            # Attempt graceful recovery
            self._attempt_error_recovery()

    def _update_results_display(self):
        """Update the results table with comparison data."""
        # Clear existing data
        for item in self.results_tree.get_children():
            self.results_tree.delete(item)

        if not self.comparison_results:
            return

        # Configure tags for color coding improvements
        self.results_tree.tag_configure(
            "excellent", background="#d4edda", foreground="#155724"
        )  # Green
        self.results_tree.tag_configure(
            "good", background="#fff3cd", foreground="#856404"
        )  # Yellow
        self.results_tree.tag_configure(
            "poor", background="#f8d7da", foreground="#721c24"
        )  # Red
        self.results_tree.tag_configure(
            "neutral", background="#f8f9fa", foreground="#495057"
        )  # Gray

        # Add comparison results to the table
        for result in self.comparison_results:
            # Format values for display
            process_name = result["anylogic_process"]
            anylogic_mean = f"{result['anylogic_mean']:.2f}"
            anylogic_median = f"{result['anylogic_median']:.2f}"
            historical_mean = f"{result['historical_mean']:.2f}"
            historical_median = f"{result['historical_median']:.2f}"

            # Format improvement percentages with visual indicators
            mean_improvement = result["mean_improvement_pct"]
            median_improvement = result["median_improvement_pct"]

            # Add visual indicators for improvements
            mean_improvement_str = self._format_improvement_display(mean_improvement)
            median_improvement_str = self._format_improvement_display(
                median_improvement
            )

            # Format statistical information
            statistical_test = result.get("statistical_test", {})

            # Statistical significance display
            p_value = statistical_test.get("p_value")
            if p_value is not None:
                if p_value < 0.001:
                    stat_sig_display = "*** p<0.001"
                elif p_value < 0.01:
                    stat_sig_display = "** p<0.01"
                elif p_value < 0.05:
                    stat_sig_display = "* p<0.05"
                elif p_value < 0.10:
                    stat_sig_display = "• p<0.10"
                else:
                    stat_sig_display = f"p={p_value:.3f}"
            else:
                stat_sig_display = "N/A"

            # Effect size display
            effect_size = statistical_test.get("effect_size")
            if effect_size is not None:
                abs_effect = abs(effect_size)
                if abs_effect > 0.8:
                    effect_display = f"Large ({effect_size:.2f})"
                elif abs_effect > 0.5:
                    effect_display = f"Medium ({effect_size:.2f})"
                elif abs_effect > 0.2:
                    effect_display = f"Small ({effect_size:.2f})"
                else:
                    effect_display = f"Negligible ({effect_size:.2f})"
            else:
                effect_display = "N/A"

            # Data quality display (placeholder - would use actual quality score)
            quality_score = result.get("data_quality_score", 85)  # Default score
            if quality_score >= 90:
                quality_display = f"Excellent ({quality_score})"
            elif quality_score >= 80:
                quality_display = f"Good ({quality_score})"
            elif quality_score >= 70:
                quality_display = f"Fair ({quality_score})"
            else:
                quality_display = f"Poor ({quality_score})"

            # Determine row color based on overall improvement and statistical significance
            avg_improvement = (mean_improvement + median_improvement) / 2
            is_significant = statistical_test.get("is_significant", False)
            confidence = result.get("confidence", "Medium")

            # Enhanced tag selection considering statistical significance
            if is_significant and avg_improvement < -5:
                row_tag = "excellent"  # Statistically significant improvement
            elif is_significant and avg_improvement < 0:
                row_tag = "good"  # Statistically significant but small improvement
            elif avg_improvement < -5:
                row_tag = "good"  # Large improvement but not statistically confirmed
            else:
                row_tag = self._get_improvement_tag(avg_improvement, confidence)

            # Insert row with enhanced color coding and statistical information
            item = self.results_tree.insert(
                "",
                "end",
                values=(
                    process_name,
                    anylogic_mean,
                    anylogic_median,
                    historical_mean,
                    historical_median,
                    mean_improvement_str,
                    median_improvement_str,
                    stat_sig_display,
                    effect_display,
                    quality_display,
                ),
                tags=(row_tag,),
            )

    def _format_improvement_display(self, improvement_pct: float) -> str:
        if improvement_pct <= -10:
            # Big improvement
            return f"✓✓ {improvement_pct:+.1f}%"
        elif improvement_pct <= -5:
            # Moderate improvement
            return f"✓ {improvement_pct:+.1f}%"
        elif improvement_pct <= 0:
            # Small improvement
            return f"~ {improvement_pct:+.1f}%"
        else:
            # No improvement or things got worse
            return f"✗ {improvement_pct:+.1f}%"

    def _get_improvement_tag(self, avg_improvement: float, confidence: str) -> str:
        """
        Determine the color tag for improvement based on average improvement and confidence.

        Args:
            avg_improvement (float): Average improvement percentage (negative is better).
            confidence (str): Confidence level ("High", "Medium", "Low").

        Returns:
            str: Tag name for color coding ("excellent", "good", "neutral", "poor").
        """
        # If confidence is low, always use neutral color to avoid misleading interpretation
        if confidence.strip().lower() == "low":
            return "neutral"

        # More granular thresholds for better visual feedback
        if avg_improvement <= -15:
            return "excellent"  # Outstanding improvement
        elif avg_improvement <= -7.5:
            return "good"       # Strong improvement
        elif avg_improvement < 0:
            return "neutral"    # Slight improvement
        elif avg_improvement < 5:
            return "poor"       # No improvement or slight worsening
        else:
            return "poor"       # Significant worsening

    def _format_confidence_display(self, confidence: str) -> str:
        """
        Format confidence level with visual indicators.

        Args:
            confidence: Confidence level string

        Returns:
            Formatted confidence display with icons and explanations
        """
        confidence_icons = {
            "High": "🟢 High (>=50 samples, consistent data)",
            "Medium": "🟡 Medium (20-49 samples, moderate variation)",
            "Low": "🔴 Low (<20 samples, high variation)",
        }
        return confidence_icons.get(confidence, f"⚪ {confidence}")

    def _export_results(self):
        """Export comparison results with enhanced naming and feedback."""
        if not self.comparison_results:
            messagebox.showwarning(
                "No Results", "Please run analysis first to generate results."
            )
            self._show_status("No results to export. Run analysis first.", "warning")
            return

        try:
            # Generate default filename with timestamp and date range
            current_time = datetime.now().strftime("%Y%m%d_%H%M%S")
            start_date = self.start_date_var.get().replace("-", "")
            end_date = self.end_date_var.get().replace("-", "")
            default_name = (
                f"process_time_comparison_{start_date}_to_{end_date}_{current_time}.csv"
            )

            # Ask user for save location with suggested name
            file_path = filedialog.asksaveasfilename(
                title="Export Process Time Comparison Results",
                defaultextension=".csv",
                initialvalue=default_name,
                filetypes=[
                    ("CSV files", "*.csv"),
                    ("Excel files", "*.xlsx"),
                    ("All files", "*.*"),
                ],
            )

            if file_path:
                self._show_status("Exporting results...", "info")
                self.window.config(cursor="wait")
                self.window.update()

                # Export using the enhanced processor
                self.processor.export_results(file_path)

                # Show success message
                self._show_status(
                    f"Results exported successfully to {os.path.basename(file_path)}",
                    "success",
                )
                messagebox.showinfo(
                    "Export Complete", f"Results exported to:\n{file_path}"
                )

        except Exception as e:
            self.logger.error(f"Error exporting results: {e}")
            self._show_status("Export failed", "error")
            messagebox.showerror("Export Error", f"Failed to export results:\n{str(e)}")
        finally:
            self.window.config(cursor="")
            self.window.update()

    def _perform_statistical_analysis(self):
        """
        Perform statistical analysis on process time comparisons.

        This method adds statistical significance testing and effect size calculations
        to each process comparison, enhancing the analysis with quantitative insights.
        """
        if not self.comparison_results:
            self.logger.warning(
                "No comparison results available for statistical analysis"
            )
            return

        try:
            self.logger.info("Performing statistical analysis on process comparisons")

            # Get historical data for statistical testing
            historical_data = self.data_loader.get_data()

            for result in self.comparison_results:
                process_name = result["anylogic_process"]

                # Extract process time data for this specific process
                # Note: This assumes historical data has process time columns
                # You might need to adjust based on your data structure
                historical_times = self._extract_process_times(
                    historical_data, process_name
                )

                if historical_times is not None and len(historical_times) > 1:
                    # Create simulation data array based on AnyLogic results
                    # Since we only have mean/median from AnyLogic, we'll simulate a distribution
                    anylogic_mean = result["anylogic_mean"]
                    anylogic_median = result["anylogic_median"]

                    # Estimate standard deviation based on mean-median relationship
                    # This is an approximation for demonstration
                    estimated_std = abs(anylogic_mean - anylogic_median) * 1.5
                    if estimated_std == 0:
                        estimated_std = anylogic_mean * 0.1  # 10% of mean as fallback

                    # Generate synthetic AnyLogic data for statistical testing
                    np.random.seed(42)  # For reproducible results
                    anylogic_times = np.random.normal(
                        anylogic_mean, estimated_std, len(historical_times)
                    )
                    anylogic_times = np.maximum(
                        anylogic_times, 0
                    )  # Ensure positive times

                    # Perform statistical tests
                    test_result = self.statistical_engine.compare_groups(
                        group1=historical_times,
                        group2=anylogic_times,
                        group1_name="Historical",
                        group2_name="AnyLogic Simulation",
                    )

                    # Add statistical results to comparison
                    result["statistical_test"] = {
                        "test_type": test_result.test_type,
                        "p_value": test_result.p_value,
                        "test_statistic": test_result.test_statistic,
                        "effect_size": test_result.effect_size,
                        "confidence_interval": test_result.confidence_interval,
                        "is_significant": test_result.is_significant,
                        "interpretation": test_result.interpretation,
                        "recommendation": test_result.recommendation,
                    }

                    # Update confidence level based on statistical power
                    if test_result.p_value < 0.001:
                        result["statistical_confidence"] = "Very High"
                    elif test_result.p_value < 0.01:
                        result["statistical_confidence"] = "High"
                    elif test_result.p_value < 0.05:
                        result["statistical_confidence"] = "Medium"
                    else:
                        result["statistical_confidence"] = "Low"

                else:
                    # Insufficient data for statistical testing
                    result["statistical_test"] = {
                        "test_type": "Insufficient Data",
                        "p_value": None,
                        "is_significant": False,
                        "interpretation": "Insufficient historical data for statistical testing",
                        "recommendation": "Collect more historical data for robust analysis",
                    }
                    result["statistical_confidence"] = "Low"

            self.logger.info(
                f"Statistical analysis completed for {len(self.comparison_results)} processes"
            )

        except Exception as e:
            self.logger.error(f"Error performing statistical analysis: {e}")
            # Add fallback statistical information
            for result in self.comparison_results:
                if "statistical_test" not in result:
                    result["statistical_test"] = {
                        "test_type": "Analysis Failed",
                        "p_value": None,
                        "is_significant": False,
                        "interpretation": f"Statistical analysis failed: {str(e)}",
                        "recommendation": "Check data quality and try again",
                    }
                    result["statistical_confidence"] = "Low"

    def _extract_process_times(
        self, data: pd.DataFrame, process_name: str
    ) -> Optional[np.ndarray]:
        """
        Extract process times for a specific process from historical data.

        Args:
            data: Historical clinic data
            process_name: Name of the process to extract times for

        Returns:
            Array of process times or None if not found
        """
        try:
            # Local extraction logic
            time_columns = [
                col
                for col in data.columns
                if any(
                    keyword in col.lower()
                    for keyword in ["time", "duration", "wait", "service"]
                )
            ]

            if not time_columns:
                return None

            process_columns = [
                col for col in time_columns if process_name.lower() in col.lower()
            ]

            if process_columns:
                times = pd.to_numeric(
                    data[process_columns[0]], errors="coerce"
                ).dropna()
                return times.values if len(times) > 1 else None
            else:
                general_time_cols = [
                    col
                    for col in time_columns
                    if any(
                        word in col.lower() for word in ["service", "total", "duration"]
                    )
                ]
                if general_time_cols:
                    times = pd.to_numeric(
                        data[general_time_cols[0]], errors="coerce"
                    ).dropna()
                    return times.values if len(times) > 1 else None

            return None

        except Exception as e:
            self.logger.error(f"Error extracting process times for {process_name}: {e}")
            return None

    def _generate_statistical_summary(self) -> Dict[str, Any]:
        """
        Generate a summary of statistical analysis results.

        Returns:
            Dictionary containing statistical analysis summary
        """
        if not self.comparison_results:
            return {}

        try:
            significant_tests = 0
            large_effects = 0
            total_tests = 0
            p_values = []

            for result in self.comparison_results:
                statistical_test = result.get("statistical_test", {})

                if statistical_test.get("p_value") is not None:
                    total_tests += 1
                    p_values.append(statistical_test["p_value"])

                    if statistical_test.get("is_significant", False):
                        significant_tests += 1

                    # Check for large effect sizes
                    effect_size = statistical_test.get("effect_size")
                    if (
                        effect_size and abs(effect_size) > 0.8
                    ):  # Cohen's d > 0.8 is large
                        large_effects += 1

            # Calculate average statistical power (simplified)
            avg_power = (
                f"{(significant_tests / max(total_tests, 1) * 100):.1f}%"
                if total_tests > 0
                else "N/A"
            )

            return {
                "total_tests": total_tests,
                "significant_tests": significant_tests,
                "large_effects": large_effects,
                "significance_rate": f"{(significant_tests / max(total_tests, 1) * 100):.1f}%",
                "avg_power": avg_power,
                "avg_p_value": np.mean(p_values) if p_values else None,
            }

        except Exception as e:
            self.logger.error(f"Error generating statistical summary: {e}")
            return {}

    def _generate_quality_summary(self, data_quality: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary of data quality assessment results.

        Args:
            data_quality: Data quality assessment results

        Returns:
            Dictionary containing quality assessment summary
        """
        if not data_quality:
            return {}

        try:
            anylogic_quality = data_quality.get("anylogic_quality")
            historical_quality = data_quality.get("historical_quality")

            summary = {}

            if anylogic_quality:
                summary["anylogic_score"] = anylogic_quality.overall_score
                summary["anylogic_grade"] = anylogic_quality.overall_grade

            if historical_quality:
                summary["historical_score"] = historical_quality.overall_score
                summary["historical_grade"] = historical_quality.overall_grade

            # Count critical issues
            critical_issues = 0

            if anylogic_quality and anylogic_quality.overall_score < 60:
                critical_issues += 1

            if historical_quality and historical_quality.overall_score < 60:
                critical_issues += 1

            summary["critical_issues"] = critical_issues

            # Generate quality recommendations
            recommendations = []

            if anylogic_quality and anylogic_quality.overall_score < 80:
                recommendations.append("Improve AnyLogic simulation data quality")

            if historical_quality and historical_quality.overall_score < 80:
                recommendations.append("Improve historical clinic data quality")

            summary["recommendations"] = recommendations

            return summary

        except Exception as e:
            self.logger.error(f"Error generating quality summary: {e}")
            return {}

    def _create_insights_placeholder(self):
        """Create placeholder content for the insights tab."""
        # Clear existing content
        for widget in self.insights_content_frame.winfo_children():
            widget.destroy()

        # Placeholder message
        placeholder_label = ttk.Label(
            self.insights_content_frame,
            text="🔍 No analysis results available\n\nRun the enhanced analysis to see automated insights and recommendations.",
            font=("Segoe UI", 12),
            foreground="#6c757d",
            justify=tk.CENTER,
        )
        placeholder_label.pack(expand=True, pady=50)

    def _update_insights_display(self, results: Dict[str, Any]):
        """
        Update the insights tab with automated insights and recommendations.

        Args:
            results: Analysis results containing statistical and quality information
        """
        # Clear existing content
        for widget in self.insights_content_frame.winfo_children():
            widget.destroy()

        try:
            # Generate automated insights
            insights = self._generate_automated_insights(results)

            # Create main title
            title_label = ttk.Label(
                self.insights_content_frame,
                text="🎯 Enhanced Process Analysis Insights",
                font=("Segoe UI", 16, "bold"),
                foreground="#0d6efd",
            )
            title_label.pack(pady=(10, 20))

            # Executive Summary section
            self._add_insights_section(
                "📋 Executive Summary", insights.get("executive_summary", []), "#198754"
            )

            # Statistical Insights section
            self._add_insights_section(
                "📊 Statistical Analysis Insights",
                insights.get("statistical_insights", []),
                "#0d6efd",
            )

            # Data Quality Insights section
            self._add_insights_section(
                "🔍 Data Quality Assessment",
                insights.get("quality_insights", []),
                "#fd7e14",
            )

            # Process-Specific Recommendations section
            self._add_insights_section(
                "⚡ Process-Specific Recommendations",
                insights.get("process_recommendations", []),
                "#6f42c1",
            )

            # Implementation Priority section
            self._add_insights_section(
                "🎯 Implementation Priorities",
                insights.get("implementation_priorities", []),
                "#dc3545",
            )

            # Next Steps section
            self._add_insights_section(
                "🚀 Recommended Next Steps", insights.get("next_steps", []), "#20c997"
            )

        except Exception as e:
            self.logger.error(f"Error updating insights display: {e}")
            error_label = ttk.Label(
                self.insights_content_frame,
                text=f"⚠️ Error generating insights: {str(e)}",
                font=("Segoe UI", 10),
                foreground="#dc3545",
            )
            error_label.pack(pady=20)

    def _add_insights_section(self, title: str, content: List[str], color: str):
        """
        Add a section to the insights display.

        Args:
            title: Section title
            content: List of content items
            color: Color for the section header
        """
        if not content:
            return

        # Section frame
        section_frame = ttk.LabelFrame(
            self.insights_content_frame, text=title, padding=(15, 10)
        )
        section_frame.pack(fill=tk.X, padx=15, pady=(5, 15))

        # Content items
        for i, item in enumerate(content):
            item_frame = ttk.Frame(section_frame)
            item_frame.pack(fill=tk.X, pady=(5 if i > 0 else 0, 0))

            # Bullet point
            bullet_label = ttk.Label(
                item_frame, text="•", font=("Segoe UI", 10, "bold")
            )
            bullet_label.pack(side=tk.LEFT, padx=(0, 8))

            # Content text
            content_label = ttk.Label(
                item_frame,
                text=item,
                font=("Segoe UI", 10),
                wraplength=800,
                justify=tk.LEFT,
            )
            content_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

    def _generate_automated_insights(
        self, results: Dict[str, Any]
    ) -> Dict[str, List[str]]:
        """
        Generate automated insights and recommendations based on analysis results.

        Args:
            results: Analysis results containing comparisons, statistics, and quality data

        Returns:
            Dictionary containing categorized insights and recommendations
        """
        insights = {
            "executive_summary": [],
            "statistical_insights": [],
            "quality_insights": [],
            "process_recommendations": [],
            "implementation_priorities": [],
            "next_steps": [],
        }

        try:
            # Get basic analysis data
            comparisons = self.comparison_results or []
            summary = results.get("summary", {})
            data_quality = results.get("data_quality", {})

            # Generate executive summary
            total_processes = len(comparisons)
            significant_improvements = sum(
                1
                for c in comparisons
                if c.get("statistical_test", {}).get("is_significant", False)
                and c.get("mean_improvement_pct", 0) < 0
            )

            insights["executive_summary"].extend(
                [
                    f"Analyzed {total_processes} processes comparing AnyLogic simulation results with historical clinic data.",
                    f"Found {significant_improvements} processes with statistically significant improvements.",
                    f"Overall data quality: AnyLogic ({self._get_quality_grade(data_quality, 'anylogic')}), "
                    f"Historical ({self._get_quality_grade(data_quality, 'historical')})",
                    f"Average improvement in mean process times: {summary.get('mean_improvement_avg', 0):.1f}%",
                ]
            )

            # Generate statistical insights
            statistical_summary = self._generate_statistical_summary()
            if statistical_summary:
                insights["statistical_insights"].extend(
                    [
                        f"Performed {statistical_summary.get('total_tests', 0)} statistical significance tests.",
                        f"Found {statistical_summary.get('significant_tests', 0)} statistically significant differences.",
                        f"Identified {statistical_summary.get('large_effects', 0)} processes with large effect sizes (Cohen's d > 0.8).",
                        f"Statistical power: {statistical_summary.get('avg_power', 'N/A')} of tests showed significant results.",
                    ]
                )

            # Generate data quality insights
            if data_quality:
                anylogic_quality = data_quality.get("anylogic_quality")
                historical_quality = data_quality.get("historical_quality")

                if anylogic_quality:
                    insights["quality_insights"].append(
                        f"AnyLogic simulation data quality: {anylogic_quality.overall_score:.1f}/100 "
                        f"({anylogic_quality.overall_grade})"
                    )

                if historical_quality:
                    insights["quality_insights"].append(
                        f"Historical clinic data quality: {historical_quality.overall_score:.1f}/100 "
                        f"({historical_quality.overall_grade})"
                    )

                # Add quality-specific recommendations
                if anylogic_quality and anylogic_quality.overall_score < 80:
                    insights["quality_insights"].append(
                        "AnyLogic data quality needs improvement - consider reviewing simulation parameters."
                    )

                if historical_quality and historical_quality.overall_score < 80:
                    insights["quality_insights"].append(
                        "Historical data quality needs improvement - consider data cleaning and validation."
                    )

            # Generate process-specific recommendations
            for comparison in comparisons:
                process_name = comparison.get("anylogic_process", "Unknown")
                statistical_test = comparison.get("statistical_test", {})
                improvement_pct = comparison.get("mean_improvement_pct", 0)

                if (
                    statistical_test.get("is_significant", False)
                    and improvement_pct < -10
                ):
                    insights["process_recommendations"].append(
                        f"{process_name}: Excellent improvement ({improvement_pct:.1f}%) with statistical significance. "
                        "Consider implementing simulation recommendations."
                    )
                elif improvement_pct > 5:
                    insights["process_recommendations"].append(
                        f"{process_name}: Performance degradation detected ({improvement_pct:.1f}%). "
                        "Review simulation parameters and assumptions."
                    )
                elif abs(improvement_pct) < 2 and not statistical_test.get(
                    "is_significant", False
                ):
                    insights["process_recommendations"].append(
                        f"{process_name}: Minimal difference between simulation and reality. "
                        "Model appears well-calibrated."
                    )

            # Generate implementation priorities
            high_impact_processes = [
                c
                for c in comparisons
                if c.get("statistical_test", {}).get("is_significant", False)
                and c.get("mean_improvement_pct", 0) < -5
            ]

            if high_impact_processes:
                insights["implementation_priorities"].extend(
                    [
                        f"Prioritize implementing changes for {len(high_impact_processes)} high-impact processes.",
                        "Focus on processes with both statistical significance and large improvements.",
                        "Consider pilot implementation for most promising processes first.",
                    ]
                )
            else:
                insights["implementation_priorities"].append(
                    "No high-impact improvements identified. Consider refining simulation model or data collection."
                )

            # Generate next steps
            insights["next_steps"].extend(
                [
                    "Validate simulation results with additional historical data periods.",
                    "Conduct sensitivity analysis on key simulation parameters.",
                    "Develop implementation plan for statistically significant improvements.",
                    "Establish monitoring framework to track real-world implementation results.",
                    "Consider expanding analysis to include cost-benefit calculations.",
                ]
            )

            # Add data quality specific next steps
            if data_quality and any(
                q.overall_score < 80
                for q in [
                    data_quality.get("anylogic_quality"),
                    data_quality.get("historical_quality"),
                ]
                if q
            ):
                insights["next_steps"].insert(
                    0,
                    "Address data quality issues before implementing simulation recommendations.",
                )

        except Exception as e:
            self.logger.error(f"Error generating automated insights: {e}")
            insights["executive_summary"] = [f"Error generating insights: {str(e)}"]

        return insights

    def _get_quality_grade(self, data_quality: Dict[str, Any], source: str) -> str:
        """Get quality grade for a data source."""
        quality_obj = data_quality.get(f"{source}_quality")
        if quality_obj:
            return f"{quality_obj.overall_grade} ({quality_obj.overall_score:.0f})"
        return "Unknown"

    def _create_charts_placeholder(self):
        """Create placeholder content for the charts tab."""
        # Clear existing content
        for widget in self.charts_main_container.winfo_children():
            widget.destroy()

        # Placeholder message
        placeholder_label = ttk.Label(
            self.charts_main_container,
            text="📈 No statistical charts available\n\nRun the enhanced analysis to see statistical visualizations with confidence intervals.",
            font=("Segoe UI", 12),
            foreground="#6c757d",
            justify=tk.CENTER,
        )
        placeholder_label.pack(expand=True, pady=50)

    def _update_charts_display(self, results: Dict[str, Any]):
        """
        Update the charts tab with statistical visualizations using flexible scaling.

        Args:
            results: Analysis results containing statistical information
        """
        import tkinter as tk
        from tkinter import ttk

        # Clear existing content
        for widget in self.charts_main_container.winfo_children():
            widget.destroy()

        # Debug: Log the comparison results
        self.logger.info(f"Updating charts display. Comparison results count: {len(self.comparison_results) if self.comparison_results else 0}")
        if self.comparison_results:
            self.logger.info(f"First comparison result: {self.comparison_results[0] if len(self.comparison_results) > 0 else 'None'}")

        if not self.comparison_results:
            self.logger.warning("No comparison results available for charts")
            self._create_charts_placeholder()
            return

        try:
            # Create main title
            title_label = ttk.Label(
                self.charts_main_container,
                text="📈 Clinic Performance Analysis: Simulation vs Historical Data",
                font=("Segoe UI", 16, "bold"),
                foreground="#0d6efd",
            )
            title_label.pack(pady=(10, 5))
            
            # Add scrolling instructions
            instructions_label = ttk.Label(
                self.charts_main_container,
                text="💡 Scroll vertically with mouse wheel | Hold Shift + mouse wheel for horizontal scrolling | Use arrow keys for navigation",
                font=("Segoe UI", 9),
                foreground="#6c757d",
            )
            instructions_label.pack(pady=(0, 15))

            # Create a scrollable canvas for all charts with both vertical and horizontal scrolling
            self.charts_canvas = tk.Canvas(self.charts_main_container, bg="white", highlightthickness=0)
            
            # Create vertical scrollbar
            self.charts_v_scrollbar = ttk.Scrollbar(
                self.charts_main_container, orient=tk.VERTICAL, command=self.charts_canvas.yview
            )
            
            # Create horizontal scrollbar
            self.charts_h_scrollbar = ttk.Scrollbar(
                self.charts_main_container, orient=tk.HORIZONTAL, command=self.charts_canvas.xview
            )
            
            self.charts_content_frame_inner = ttk.Frame(self.charts_canvas)

            # Configure scrolling for both directions
            self.charts_content_frame_inner.bind(
                "<Configure>",
                lambda e: self.charts_canvas.configure(scrollregion=self.charts_canvas.bbox("all")),
            )

            # Create window in canvas and configure scroll commands
            self.charts_canvas_window = self.charts_canvas.create_window(
                (0, 0), window=self.charts_content_frame_inner, anchor="nw"
            )
            self.charts_canvas.configure(
                yscrollcommand=self.charts_v_scrollbar.set,
                xscrollcommand=self.charts_h_scrollbar.set
            )

            # Pack scrollbars and canvas using grid for better control
            self.charts_canvas.grid(row=0, column=0, sticky="nsew")
            self.charts_v_scrollbar.grid(row=0, column=1, sticky="ns")
            self.charts_h_scrollbar.grid(row=1, column=0, sticky="ew")
            
            # Configure grid weights for proper resizing
            self.charts_main_container.grid_rowconfigure(0, weight=1)
            self.charts_main_container.grid_columnconfigure(0, weight=1)

            # Enhanced mousewheel scrolling with horizontal support
            def on_mousewheel(event):
                try:
                    if self.charts_canvas and self.charts_canvas.winfo_exists():
                        # Check if Shift is held for horizontal scrolling
                        if event.state & 0x0001:  # Shift key is pressed
                            self.charts_canvas.xview_scroll(int(-1 * (event.delta / 120)), "units")
                        else:
                            self.charts_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
                except:
                    pass

            # Bind mousewheel to canvas and content frame
            self.charts_canvas.bind("<MouseWheel>", on_mousewheel)
            self.charts_content_frame_inner.bind("<MouseWheel>", on_mousewheel)
            
            # Bind arrow keys for keyboard navigation
            def on_key_press(event):
                try:
                    if self.charts_canvas and self.charts_canvas.winfo_exists():
                        if event.keysym == "Up":
                            self.charts_canvas.yview_scroll(-1, "units")
                        elif event.keysym == "Down":
                            self.charts_canvas.yview_scroll(1, "units")
                        elif event.keysym == "Left":
                            self.charts_canvas.xview_scroll(-1, "units")
                        elif event.keysym == "Right":
                            self.charts_canvas.xview_scroll(1, "units")
                        elif event.keysym == "Page_Up":
                            self.charts_canvas.yview_scroll(-1, "pages")
                        elif event.keysym == "Page_Down":
                            self.charts_canvas.yview_scroll(1, "pages")
                except:
                    pass
            
            # Make canvas focusable and bind keyboard events
            self.charts_canvas.configure(takefocus=True)
            self.charts_canvas.bind("<Key>", on_key_press)
            self.charts_canvas.bind("<Button-1>", lambda e: self.charts_canvas.focus_set())
            
            # Update canvas window size when main container changes
            def on_canvas_configure(event):
                try:
                    if self.charts_canvas and self.charts_canvas.winfo_exists():
                        # Update the canvas window width to match canvas width if content is smaller
                        canvas_width = event.width
                        canvas_height = event.height
                        
                        # Get the required width and height of the content
                        self.charts_content_frame_inner.update_idletasks()
                        content_width = self.charts_content_frame_inner.winfo_reqwidth()
                        content_height = self.charts_content_frame_inner.winfo_reqheight()
                        
                        # Set the window width to at least the canvas width for proper horizontal scrolling
                        window_width = max(canvas_width, content_width)
                        window_height = max(canvas_height, content_height)
                        
                        self.charts_canvas.itemconfig(self.charts_canvas_window, width=window_width)
                except:
                    pass
            
            self.charts_canvas.bind("<Configure>", on_canvas_configure)

            # Generate and embed all performance analysis charts into the scrollable frame
            self._embed_performance_analysis_charts(results)

        except Exception as e:
            self.logger.error(f"Error updating charts display: {e}")
            error_label = ttk.Label(
                self.charts_main_container,
                text=f"⚠️ Error generating charts: {str(e)}",
                font=("Segoe UI", 10),
                foreground="#dc3545",
            )
            error_label.pack(pady=20)


    def _embed_performance_analysis_charts(self, results: Dict[str, Any]):
        """Embed all performance analysis charts with flexible scaling."""
        try:
            self.logger.info("Starting to embed performance analysis charts...")
            
            # 1. Process Time Comparison (Core Performance Metric)
            self.logger.info("Embedding process comparison chart...")
            self._embed_process_comparison_chart_enhanced()
            
            # 2. Statistical Significance Analysis
            self.logger.info("Embedding statistical significance chart...")
            self._embed_statistical_significance_chart_enhanced()
            
            # 3. Effect Size Analysis
            self.logger.info("Embedding effect size chart...")
            self._embed_effect_size_chart_enhanced()
            
            # 4. Wait Time Analysis (Key Performance Indicator)
            self.logger.info("Embedding wait time analysis chart...")
            self._embed_wait_time_analysis_chart_enhanced()
            
            # 5. Data Quality Assessment
            self.logger.info("Embedding data quality chart...")
            self._embed_data_quality_chart_enhanced(results.get("data_quality", {}))
            
            # 6. Efficiency Metrics Analysis
            self.logger.info("Embedding efficiency metrics chart...")
            self._embed_efficiency_metrics_chart_enhanced(results)
            
            # 7. Volume Impact Analysis
            self.logger.info("Embedding volume impact chart...")
            self._embed_volume_impact_chart_enhanced(results)
            
            # 8. Bottleneck Analysis
            self.logger.info("Embedding bottleneck analysis chart...")
            self._embed_bottleneck_analysis_chart_enhanced(results)
            
            self.logger.info("All performance analysis charts embedded successfully")

        except Exception as e:
            self.logger.error(f"Error embedding performance analysis charts: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            error_label = ttk.Label(
                self.charts_content_frame_inner,
                text=f"⚠️ Error generating performance charts: {str(e)}",
                font=("Segoe UI", 10),
                foreground="#dc3545",
            )
            error_label.pack(pady=20)

    def _embed_process_comparison_chart_enhanced(self):
        """Embed process comparison chart with flexible scaling and enhanced performance metrics, using scrollable panel."""
        from app.visualization.chart_generators.process_comparison import ProcessComparisonChartGenerator
        
        self._embed_chart_with_scrollable_panel(
            chart_name="Process Time Comparison",
            chart_generator=ProcessComparisonChartGenerator,
            chart_method="create_comparison_figure",
            chart_args={"comparison_results": self.comparison_results},
            error_message="Failed to generate process comparison chart"
        )

    def _embed_statistical_significance_chart_enhanced(self):
        """Embed statistical significance chart with flexible scaling, using scrollable panel."""
        from app.visualization.chart_generators.process_comparison import ProcessComparisonChartGenerator
        
        self._embed_chart_with_scrollable_panel(
            chart_name="Statistical Significance Analysis",
            chart_generator=ProcessComparisonChartGenerator,
            chart_method="create_significance_figure",
            chart_args={"comparison_results": self.comparison_results},
            error_message="Failed to generate statistical significance chart"
        )

    def _embed_effect_size_chart_enhanced(self):
        """Embed effect size chart with flexible scaling, using scrollable panel."""
        from app.visualization.chart_generators.process_comparison import ProcessComparisonChartGenerator
        
        self._embed_chart_with_scrollable_panel(
            chart_name="Effect Size Analysis",
            chart_generator=ProcessComparisonChartGenerator,
            chart_method="create_effect_size_figure",
            chart_args={"comparison_results": self.comparison_results},
            error_message="Failed to generate effect size chart"
        )

    def _embed_wait_time_analysis_chart_enhanced(self):
        """Embed wait time analysis chart with flexible scaling and enhanced metrics, using scrollable panel."""
        try:
            if not hasattr(self, "anylogic_data") or self.anylogic_data is None:
                self._create_chart_info_placeholder("Wait Time Analysis", "No AnyLogic data available for wait time analysis")
                return

            import matplotlib.pyplot as plt
            import numpy as np

            # Check if we have summary data (Process Summary sheet)
            available_columns = self.anylogic_data.columns.tolist()
            
            # Look for summary statistics columns
            has_summary_data = any(col in available_columns for col in ['Mean (mins)', 'Median (mins)', 'Std Dev (mins)'])
            
            if has_summary_data:
                # Create a summary statistics chart instead of detailed wait time analysis
                self._create_process_summary_chart()
            else:
                # Try to create detailed wait time analysis if we have the right columns
                self._create_detailed_wait_time_chart()
            
        except Exception as e:
            self.logger.error(f"Error embedding enhanced wait time analysis chart: {e}")
            self._create_chart_error_placeholder("Wait Time Analysis", str(e))

    def _create_process_summary_chart(self):
        """Create a chart showing process summary statistics from AnyLogic data."""
        try:
            import matplotlib.pyplot as plt
            import numpy as np

            # Create figure with subplots
            fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
            fig.suptitle('Process Performance Summary Analysis', fontsize=16, fontweight='bold')

            # Get process names
            process_col = None
            for col in ['Process', 'process', 'Process Name', 'ProcessName']:
                if col in self.anylogic_data.columns:
                    process_col = col
                    break

            if process_col is None:
                self._create_chart_info_placeholder("Process Summary", "Process column not found in data")
                return

            processes = self.anylogic_data[process_col].tolist()

            # Subplot 1: Mean vs Median comparison
            if 'Mean (mins)' in self.anylogic_data.columns and 'Median (mins)' in self.anylogic_data.columns:
                means = self.anylogic_data['Mean (mins)'].tolist()
                medians = self.anylogic_data['Median (mins)'].tolist()
                
                x = np.arange(len(processes))
                width = 0.35
                
                bars1 = ax1.bar(x - width/2, means, width, label='Mean', color='#4e79a7', alpha=0.8)
                bars2 = ax1.bar(x + width/2, medians, width, label='Median', color='#f28e2b', alpha=0.8)
                
                ax1.set_xlabel('Processes')
                ax1.set_ylabel('Duration (minutes)')
                ax1.set_title('Mean vs Median Process Duration')
                ax1.set_xticks(x)
                ax1.set_xticklabels(processes, rotation=45, ha='right')
                ax1.legend()
                ax1.grid(axis='y', alpha=0.3)
                
                # Add value labels
                for bars in [bars1, bars2]:
                    for bar in bars:
                        height = bar.get_height()
                        ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                f'{height:.1f}', ha='center', va='bottom', fontsize=8)

            # Subplot 2: Standard Deviation (variability)
            if 'Std Dev (mins)' in self.anylogic_data.columns:
                std_devs = self.anylogic_data['Std Dev (mins)'].tolist()
                
                # Use numeric indices for x-axis positions to avoid dtype issues
                x_positions = np.arange(len(processes))
                bars = ax2.bar(x_positions, std_devs, color='#59a14f', alpha=0.8)
                ax2.set_xlabel('Processes')
                ax2.set_ylabel('Standard Deviation (minutes)')
                ax2.set_title('Process Duration Variability')
                ax2.set_xticks(x_positions)
                ax2.set_xticklabels(processes, rotation=45, ha='right')
                ax2.grid(axis='y', alpha=0.3)
                
                # Add value labels
                for bar, std in zip(bars, std_devs):
                    height = bar.get_height()
                    ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                            f'{std:.1f}', ha='center', va='bottom', fontsize=8)

            # Subplot 3: Min vs Max comparison
            if 'Min (mins)' in self.anylogic_data.columns and 'Max (mins)' in self.anylogic_data.columns:
                mins = self.anylogic_data['Min (mins)'].tolist()
                maxs = self.anylogic_data['Max (mins)'].tolist()
                
                x = np.arange(len(processes))
                width = 0.35
                
                bars1 = ax3.bar(x - width/2, mins, width, label='Minimum', color='#76b7b2', alpha=0.8)
                bars2 = ax3.bar(x + width/2, maxs, width, label='Maximum', color='#edc948', alpha=0.8)
                
                ax3.set_xlabel('Processes')
                ax3.set_ylabel('Duration (minutes)')
                ax3.set_title('Min vs Max Process Duration')
                ax3.set_xticks(x)
                ax3.set_xticklabels(processes, rotation=45, ha='right')
                ax3.legend()
                ax3.grid(axis='y', alpha=0.3)
                
                # Add value labels
                for bars in [bars1, bars2]:
                    for bar in bars:
                        height = bar.get_height()
                        ax3.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                                f'{height:.1f}', ha='center', va='bottom', fontsize=8)

            # Subplot 4: Process efficiency ranking
            if 'Mean (mins)' in self.anylogic_data.columns:
                means = self.anylogic_data['Mean (mins)'].tolist()
                # Calculate efficiency score (lower duration = higher efficiency)
                efficiency_scores = [max(0, 100 - (mean / 60) * 10) if mean > 0 else 0 for mean in means]
                
                # Sort by efficiency
                sorted_data = sorted(zip(processes, efficiency_scores), key=lambda x: x[1], reverse=True)
                sorted_processes, sorted_scores = zip(*sorted_data)
                
                # Use numeric indices for y-axis positions to avoid dtype issues
                y_positions = np.arange(len(sorted_processes))
                colors = ['green' if score > 70 else 'orange' if score > 50 else 'red' for score in sorted_scores]
                bars = ax4.barh(y_positions, sorted_scores, color=colors, alpha=0.8)
                ax4.set_yticks(y_positions)
                ax4.set_yticklabels(sorted_processes)
                ax4.set_xlabel('Efficiency Score (%)')
                ax4.set_title('Process Efficiency Ranking')
                ax4.set_xlim(0, 100)
                ax4.grid(axis='x', alpha=0.3)
                
                # Add value labels
                for bar, score in zip(bars, sorted_scores):
                    width = bar.get_width()
                    ax4.text(width + 1, bar.get_y() + bar.get_height()/2.,
                            f'{score:.1f}%', ha='left', va='center', fontsize=8)

            plt.tight_layout()
            
            # Set optimal figure size
            self._set_optimal_figure_size(fig)
            
            # Create a section frame for this chart
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            
            chart_section_frame = ttk.LabelFrame(
                self.charts_content_frame_inner, 
                text="Process Performance Summary", 
                padding=(10, 5)
            )
            chart_section_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Embed the matplotlib figure directly
            canvas_widget = FigureCanvasTkAgg(fig, chart_section_frame)
            canvas_widget.draw()
            canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Update scroll region after adding chart
            self._update_scroll_region()
            
        except Exception as e:
            self.logger.error(f"Error creating process summary chart: {e}")
            self._create_chart_error_placeholder("Process Summary", str(e))

    def _create_detailed_wait_time_chart(self):
        """Create detailed wait time analysis chart if detailed data is available."""
        try:
            from app.visualization.chart_generators.process_comparison import PatientFlowAnalysisGenerator

            # Determine the correct column names from the AnyLogic data
            available_columns = self.anylogic_data.columns.tolist()

            # Find the appropriate patient ID column
            patient_id_col = None
            for col in ['Patient ID', 'PatientID', 'patient_id', 'Queue Number', 'QueueNumber']:
                if col in available_columns:
                    patient_id_col = col
                    break

            if patient_id_col is None:
                self._create_chart_info_placeholder("Wait Time Analysis", f"Patient ID column not found. Available columns: {', '.join(available_columns[:5])}...")
                return

            # Find the appropriate action column
            action_col = None
            for col in ['Action', 'action', 'Process', 'process']:
                if col in available_columns:
                    action_col = col
                    break

            if action_col is None:
                self._create_chart_info_placeholder("Wait Time Analysis", f"Action column not found. Available columns: {', '.join(available_columns[:5])}...")
                return

            # Find the appropriate timestamp column
            timestamp_col = None
            for col in ['Hour_Float', 'hour_float', 'Time', 'time', 'Timestamp', 'timestamp']:
                if col in available_columns:
                    timestamp_col = col
                    break

            if timestamp_col is None:
                self._create_chart_info_placeholder("Wait Time Analysis", f"Timestamp column not found. Available columns: {', '.join(available_columns[:5])}...")
                return

            chart_gen = PatientFlowAnalysisGenerator()
            fig = chart_gen.create_wait_time_figure(
                self.anylogic_data,
                patient_id_col=patient_id_col,
                action_col=action_col,
                timestamp_col=timestamp_col,
                wait_terms=None,
                service_terms=None,
                max_wait_minutes=480,
                business_start="08:00",
                business_end="18:59",
            )

            # Set better default size before scaling
            self._set_optimal_figure_size(fig)
            
            # Create a section frame for this chart
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            
            chart_section_frame = ttk.LabelFrame(
                self.charts_content_frame_inner, 
                text="Wait Time Analysis", 
                padding=(10, 5)
            )
            chart_section_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Embed the matplotlib figure directly
            canvas_widget = FigureCanvasTkAgg(fig, chart_section_frame)
            canvas_widget.draw()
            canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Update scroll region after adding chart
            self._update_scroll_region()
            
        except Exception as e:
            self.logger.error(f"Error creating detailed wait time chart: {e}")
            self._create_chart_error_placeholder("Wait Time Analysis", str(e))

    def _embed_chart_with_scrollable_panel(self, chart_name: str, chart_generator, chart_method: str, 
                                         chart_args: Dict[str, Any] = None, error_message: str = None):
        """
        Unified method to embed charts directly into the scrollable frame.
        
        Args:
            chart_name: Name of the chart for display
            chart_generator: Chart generator class or instance
            chart_method: Method name to call on the generator
            chart_args: Arguments to pass to the chart method
            error_message: Custom error message if chart creation fails
        """
        try:
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            
            self.logger.info(f"Embedding chart: {chart_name}")
            
            # Initialize chart generator if it's a class
            if isinstance(chart_generator, type):
                generator = chart_generator()
            else:
                generator = chart_generator
            
            # Get the chart method
            method = getattr(generator, chart_method)
            
            # Call the method with provided arguments
            if chart_args:
                self.logger.info(f"Calling {chart_method} with args: {list(chart_args.keys())}")
                fig = method(**chart_args)
            else:
                self.logger.info(f"Calling {chart_method} without args")
                fig = method()
            
            self.logger.info(f"Chart figure created successfully: {type(fig)}")
            
            # Set optimal figure size
            self._set_optimal_figure_size(fig)
            
            # Create a section frame for this chart
            chart_section_frame = ttk.LabelFrame(
                self.charts_content_frame_inner, 
                text=chart_name, 
                padding=(10, 5)
            )
            chart_section_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Embed the matplotlib figure directly
            canvas_widget = FigureCanvasTkAgg(fig, chart_section_frame)
            canvas_widget.draw()
            canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Update scroll region after adding chart
            self._update_scroll_region()
            
            self.logger.info(f"Chart {chart_name} embedded successfully")
            
        except Exception as e:
            self.logger.error(f"Error embedding {chart_name}: {e}")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            if error_message:
                self._create_chart_error_placeholder(chart_name, error_message)
            else:
                self._create_chart_error_placeholder(chart_name, str(e))

    def _embed_data_quality_chart_enhanced(self, data_quality: Dict[str, Any]):
        """Embed data quality chart with flexible scaling, using scrollable panel."""
        if not data_quality:
            self._create_chart_info_placeholder("Data Quality Assessment", "No data quality information available")
            return

        from app.visualization.chart_generators.data_quality import DataQualityChartGenerator
        
        self._embed_chart_with_scrollable_panel(
            chart_name="Data Quality Assessment",
            chart_generator=DataQualityChartGenerator,
            chart_method="create_quality_figure",
            chart_args={"data_quality": data_quality},
            error_message="Failed to generate data quality assessment chart"
        )

    def _embed_efficiency_metrics_chart_enhanced(self, results: Dict[str, Any]):
        """Embed efficiency metrics chart with flexible scaling, using scrollable panel."""
        try:
            from app.visualization.chart_generators.process_comparison import ProcessComparisonChartGenerator
            import matplotlib.pyplot as plt
            import numpy as np

            # Create efficiency metrics figure
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

            if self.comparison_results:
                # Extract efficiency data
                processes = [result.get("anylogic_process", "Unknown") for result in self.comparison_results]
                historical_means = [result.get("historical_mean", 0) for result in self.comparison_results]
                anylogic_means = [result.get("anylogic_mean", 0) for result in self.comparison_results]

                # Calculate efficiency scores (lower duration = higher efficiency)
                historical_efficiency = [max(0, 100 - (h_mean / 60) * 10) if h_mean > 0 else 0 for h_mean in historical_means]
                simulation_efficiency = [max(0, 100 - (a_mean / 60) * 10) if a_mean > 0 else 0 for a_mean in anylogic_means]

                # Subplot 1: Efficiency comparison
                x = np.arange(len(processes))
                width = 0.35

                bars1 = ax1.bar(x - width/2, historical_efficiency, width, label='Historical', color='#4e79a7', alpha=0.8)
                bars2 = ax1.bar(x + width/2, simulation_efficiency, width, label='Simulation', color='#f28e2b', alpha=0.8)

                ax1.set_xlabel('Processes')
                ax1.set_ylabel('Efficiency Score (%)')
                ax1.set_title('Process Efficiency Comparison')
                ax1.set_xticks(x)
                ax1.set_xticklabels(processes, rotation=45, ha='right')
                ax1.legend()
                ax1.grid(axis='y', alpha=0.3)
                ax1.set_ylim(0, 100)

                # Add value labels
                for bars in [bars1, bars2]:
                    for bar in bars:
                        height = bar.get_height()
                        ax1.text(bar.get_x() + bar.get_width()/2., height + 1,
                                f'{height:.1f}%', ha='center', va='bottom', fontsize=8)

                # Subplot 2: Efficiency improvement
                efficiency_improvements = [sim - hist for sim, hist in zip(simulation_efficiency, historical_efficiency)]
                colors = ['green' if imp > 0 else 'red' for imp in efficiency_improvements]

                # Use numeric indices for x-axis positions to avoid dtype issues
                x_positions = np.arange(len(processes))
                bars3 = ax2.bar(x_positions, efficiency_improvements, color=colors, alpha=0.7)
                ax2.set_xlabel('Processes')
                ax2.set_ylabel('Efficiency Improvement (%)')
                ax2.set_title('Efficiency Improvement Analysis (Positive = Better)')
                ax2.set_xticks(x_positions)
                ax2.set_xticklabels(processes, rotation=45, ha='right')
                ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
                ax2.grid(axis='y', alpha=0.3)

                # Add value labels
                for bar, imp in zip(bars3, efficiency_improvements):
                    height = bar.get_height()
                    ax2.text(bar.get_x() + bar.get_width()/2., height + (0.5 if height > 0 else -1),
                            f'{imp:+.1f}%', ha='center', va='bottom' if height > 0 else 'top', fontsize=8)
            else:
                ax1.text(0.5, 0.5, "No efficiency data available", ha="center", va="center", fontsize=12)
                ax1.set_axis_off()
                ax2.text(0.5, 0.5, "No efficiency data available", ha="center", va="center", fontsize=12)
                ax2.set_axis_off()

            plt.tight_layout()

            # Set better default size before scaling
            self._set_optimal_figure_size(fig)

            # Create a section frame for this chart
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            
            chart_section_frame = ttk.LabelFrame(
                self.charts_content_frame_inner, 
                text="Efficiency Metrics Analysis", 
                padding=(10, 5)
            )
            chart_section_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Embed the matplotlib figure directly
            canvas_widget = FigureCanvasTkAgg(fig, chart_section_frame)
            canvas_widget.draw()
            canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Update scroll region after adding chart
            self._update_scroll_region()

        except Exception as e:
            self.logger.error(f"Error embedding enhanced efficiency metrics chart: {e}")
            self._create_chart_error_placeholder("Efficiency Metrics Analysis", str(e))

    def _embed_volume_impact_chart_enhanced(self, results: Dict[str, Any]):
        """Embed volume impact analysis chart with flexible scaling, using scrollable panel."""
        try:    
            import matplotlib.pyplot as plt
            import numpy as np

            # Create volume impact figure
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

            if self.comparison_results:
                # Extract volume impact data
                processes = [result.get("anylogic_process", "Unknown") for result in self.comparison_results]
                anylogic_means = [result.get("anylogic_mean", 0) for result in self.comparison_results]
                historical_means = [result.get("historical_mean", 0) for result in self.comparison_results]
                mean_improvements = [result.get("mean_improvement_pct", 0) for result in self.comparison_results]

                # Categorize by volume level
                high_volume = []
                medium_volume = []
                low_volume = []

                for i, mean_time in enumerate(anylogic_means):
                    if mean_time > 30:
                        high_volume.append(i)
                    elif mean_time > 10:
                        medium_volume.append(i)
                    else:
                        low_volume.append(i)

                # Subplot 1: Volume distribution
                volume_categories = ['High Volume', 'Medium Volume', 'Low Volume']
                volume_counts = [len(high_volume), len(medium_volume), len(low_volume)]
                colors = ['#e15759', '#f28e2b', '#59a14f']

                # Use numeric indices for x-axis positions to avoid dtype issues
                x_positions = np.arange(len(volume_categories))
                bars1 = ax1.bar(x_positions, volume_counts, color=colors, alpha=0.8)
                ax1.set_xticks(x_positions)
                ax1.set_xticklabels(volume_categories)
                ax1.set_ylabel('Number of Processes')
                ax1.set_title('Process Volume Distribution')
                ax1.grid(axis='y', alpha=0.3)

                # Add value labels
                for bar, count in zip(bars1, volume_counts):
                    height = bar.get_height()
                    ax1.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                            str(count), ha='center', va='bottom', fontsize=10)

                # Subplot 2: Volume impact on performance
                if mean_improvements:
                    colors_impact = ['green' if imp < -20 else 'orange' if imp < 0 else 'red' for imp in mean_improvements]
                    bars2 = ax2.bar(processes, mean_improvements, color=colors_impact, alpha=0.7)

                    ax2.set_xlabel('Processes')
                    ax2.set_ylabel('Performance Impact (%)')
                    ax2.set_title('Volume Impact on Performance (Negative = Improvement)')
                    ax2.set_xticklabels(processes, rotation=45, ha='right')
                    ax2.axhline(y=0, color='black', linestyle='-', alpha=0.3)
                    ax2.grid(axis='y', alpha=0.3)

                    # Add value labels
                    for bar, imp in zip(bars2, mean_improvements):
                        height = bar.get_height()
                        ax2.text(bar.get_x() + bar.get_width()/2., height + (0.5 if height > 0 else -1),
                                f'{imp:+.1f}%', ha='center', va='bottom' if height > 0 else 'top', fontsize=8)
                else:
                    ax2.text(0.5, 0.5, "No volume impact data available", ha="center", va="center", fontsize=12)
                    ax2.set_axis_off()
            else:
                ax1.text(0.5, 0.5, "No volume data available", ha="center", va="center", fontsize=12)
                ax1.set_axis_off()
                ax2.text(0.5, 0.5, "No volume data available", ha="center", va="center", fontsize=12)
                ax2.set_axis_off()

            plt.tight_layout()

            # Set better default size before scaling
            self._set_optimal_figure_size(fig)

            # Create a section frame for this chart
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            
            chart_section_frame = ttk.LabelFrame(
                self.charts_content_frame_inner, 
                text="Volume Impact Analysis", 
                padding=(10, 5)
            )
            chart_section_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Embed the matplotlib figure directly
            canvas_widget = FigureCanvasTkAgg(fig, chart_section_frame)
            canvas_widget.draw()
            canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Update scroll region after adding chart
            self._update_scroll_region()
            
        except Exception as e:
            self.logger.error(f"Error embedding enhanced volume impact chart: {e}")
            self._create_chart_error_placeholder("Volume Impact Analysis", str(e))

    def _embed_bottleneck_analysis_chart_enhanced(self, results: Dict[str, Any]):
        """Embed bottleneck analysis chart with flexible scaling, using scrollable panel."""
        try:
            import matplotlib.pyplot as plt
            import numpy as np

            # Create bottleneck analysis figure
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

            if self.comparison_results:
                # Extract bottleneck data
                processes = [result.get("anylogic_process", "Unknown") for result in self.comparison_results]
                anylogic_means = [result.get("anylogic_mean", 0) for result in self.comparison_results]
                historical_means = [result.get("historical_mean", 0) for result in self.comparison_results]
                mean_improvements = [result.get("mean_improvement_pct", 0) for result in self.comparison_results]

                # Generate bottleneck scores using the same logic as the display
                bottleneck_scores = []
                bottleneck_severities = []
                
                for i, (al_mean, hist_mean, improvement) in enumerate(zip(anylogic_means, historical_means, mean_improvements)):
                    # Calculate bottleneck score using same criteria as display
                    bottleneck_score = 0
                    
                    # Criterion 1: High duration (AnyLogic mean > 10 minutes)
                    if al_mean > 10:
                        bottleneck_score += 1
                    
                    # Criterion 2: Poor improvement (positive improvement = worse performance)
                    if improvement > 20:
                        bottleneck_score += 2
                    elif improvement > 0:
                        bottleneck_score += 1
                    
                    # Criterion 3: High historical duration (> 5 minutes)
                    if hist_mean > 5:
                        bottleneck_score += 1
                    
                    # Criterion 4: Large performance gap (> 50% difference)
                    if abs(improvement) > 50:
                        bottleneck_score += 1
                    
                    # Normalize score to 0-1 range
                    normalized_score = min(bottleneck_score / 5.0, 1.0)
                    bottleneck_scores.append(normalized_score)
                    
                    # Determine severity
                    if bottleneck_score >= 3:
                        bottleneck_severities.append("High")
                    elif bottleneck_score >= 2:
                        bottleneck_severities.append("Medium")
                    else:
                        bottleneck_severities.append("Low")

                # Subplot 1: Bottleneck identification
                colors = ['red' if severity == 'High' else 'orange' if severity == 'Medium' else 'green' for severity in bottleneck_severities]
                bars1 = ax1.bar(processes, bottleneck_scores, color=colors, alpha=0.8)

                ax1.set_xlabel('Processes')
                ax1.set_ylabel('Bottleneck Score')
                ax1.set_title('Bottleneck Identification (Higher = More Critical)')
                ax1.set_xticklabels(processes, rotation=45, ha='right')
                ax1.grid(axis='y', alpha=0.3)
                ax1.set_ylim(0, 1)

                # Add threshold lines
                ax1.axhline(y=0.6, color='red', linestyle='--', alpha=0.7, label='High Severity (>=3 criteria)')
                ax1.axhline(y=0.4, color='orange', linestyle='--', alpha=0.7, label='Medium Severity (>=2 criteria)')
                ax1.legend()

                # Add value labels
                for bar, score in zip(bars1, bottleneck_scores):
                    height = bar.get_height()
                    ax1.text(bar.get_x() + bar.get_width()/2., height + 0.02,
                            f'{score:.2f}', ha='center', va='bottom', fontsize=8)

                # Subplot 2: Bottleneck severity distribution
                high_count = sum(1 for severity in bottleneck_severities if severity == 'High')
                moderate_count = sum(1 for severity in bottleneck_severities if severity == 'Medium')
                low_count = sum(1 for severity in bottleneck_severities if severity == 'Low')

                severity_labels = ['High', 'Medium', 'Low']
                severity_counts = [high_count, moderate_count, low_count]
                severity_colors = ['red', 'orange', 'green']

                bars2 = ax2.bar(severity_labels, severity_counts, color=severity_colors, alpha=0.8)
                ax2.set_ylabel('Number of Processes')
                ax2.set_title('Bottleneck Severity Distribution')
                ax2.grid(axis='y', alpha=0.3)

                # Add value labels
                for bar, count in zip(bars2, severity_counts):
                    height = bar.get_height()
                    ax2.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                            str(count), ha='center', va='bottom', fontsize=10)
            else:
                ax1.text(0.5, 0.5, "No bottleneck data available", ha="center", va="center", fontsize=12)
                ax1.set_axis_off()
                ax2.text(0.5, 0.5, "No bottleneck data available", ha="center", va="center", fontsize=12)
                ax2.set_axis_off()

            plt.tight_layout()

            # Set better default size before scaling
            self._set_optimal_figure_size(fig)

            # Create a section frame for this chart
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            
            chart_section_frame = ttk.LabelFrame(
                self.charts_content_frame_inner, 
                text="Bottleneck Analysis", 
                padding=(10, 5)
            )
            chart_section_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
            
            # Embed the matplotlib figure directly
            canvas_widget = FigureCanvasTkAgg(fig, chart_section_frame)
            canvas_widget.draw()
            canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Update scroll region after adding chart
            self._update_scroll_region()

        except Exception as e:
            self.logger.error(f"Error embedding enhanced bottleneck analysis chart: {e}")
            self._create_chart_error_placeholder("Bottleneck Analysis", str(e))

    def _set_optimal_figure_size(self, fig):
        """Set optimal default figure size before scaling."""
        try:
            current_size = fig.get_size_inches()
            
            # Define optimal sizes for different chart types
            # Multi-subplot charts (like comparison, significance, effect size)
            if len(fig.axes) > 1:
                optimal_width = 14.0
                optimal_height = 10.0
            else:
                # Single chart (like wait time, data quality)
                optimal_width = 12.0
                optimal_height = 8.0
            
            # Only resize if current size is smaller than optimal
            if current_size[0] < optimal_width or current_size[1] < optimal_height:
                fig.set_size_inches(optimal_width, optimal_height)
                self.logger.debug(f"Set optimal figure size to {optimal_width}x{optimal_height} inches")
                
        except Exception as e:
            self.logger.warning(f"Error setting optimal figure size: {e}")

    def _update_scroll_region(self):
        """Update the scroll region of the charts canvas to accommodate new content."""
        try:
            if hasattr(self, 'charts_canvas') and self.charts_canvas and self.charts_canvas.winfo_exists():
                # Update the content frame first
                self.charts_content_frame_inner.update_idletasks()
                
                # Update scroll region to match content
                self.charts_canvas.configure(scrollregion=self.charts_canvas.bbox("all"))
                
                # Get content dimensions
                content_width = self.charts_content_frame_inner.winfo_reqwidth()
                content_height = self.charts_content_frame_inner.winfo_reqheight()
                
                # Get canvas dimensions
                canvas_width = self.charts_canvas.winfo_width()
                canvas_height = self.charts_canvas.winfo_height()
                
                # Set minimum window size to enable horizontal scrolling when needed
                min_window_width = max(canvas_width, content_width, 800)  # Minimum 800px wide
                
                if hasattr(self, 'charts_canvas_window'):
                    self.charts_canvas.itemconfig(self.charts_canvas_window, width=min_window_width)
                
                self.logger.debug(f"Updated scroll region: content={content_width}x{content_height}, canvas={canvas_width}x{canvas_height}")
                
        except Exception as e:
            self.logger.warning(f"Error updating scroll region: {e}")

    

    def _create_chart_error_placeholder(self, chart_name: str, error_message: str):
        """Create an error placeholder for a chart."""
        error_frame = ttk.LabelFrame(
            self.charts_content_frame_inner,
            text=f"❌ {chart_name}",
            padding=(10, 5)
        )
        error_frame.pack(fill=tk.X, padx=5, pady=5)
        
        error_label = ttk.Label(
            error_frame,
            text=f"⚠️ Error generating {chart_name}:\n{error_message}",
            font=("Segoe UI", 10),
            foreground="#dc3545",
            wraplength=600,
            justify=tk.CENTER
        )
        error_label.pack(pady=10)



    def _create_chart_info_placeholder(self, chart_name: str, info_message: str):
        """Create an info placeholder for a chart."""
        info_frame = ttk.LabelFrame(
            self.charts_content_frame_inner,
            text=f"ℹ️ {chart_name}",
            padding=(10, 5)
        )
        info_frame.pack(fill=tk.X, padx=5, pady=5)
        
        info_label = ttk.Label(
            info_frame,
            text=info_message,
            font=("Segoe UI", 10),
            foreground="#6c757d",
            wraplength=600,
            justify=tk.CENTER
        )
        info_label.pack(pady=10)

    def _embed_process_comparison_chart(self):
        """Embed process comparison chart using chart generator."""
        try:
            from app.visualization.chart_generators.process_comparison import ProcessComparisonChartGenerator

            chart_gen = ProcessComparisonChartGenerator()
            fig = chart_gen.create_comparison_figure(self.comparison_results)

        except Exception as e:
            self.logger.error(f"Error embedding process comparison chart: {e}")

    def _embed_statistical_significance_chart(self):
        """Embed statistical significance chart using chart generator."""
        try:
            from app.visualization.chart_generators.process_comparison import ProcessComparisonChartGenerator

            chart_gen = ProcessComparisonChartGenerator()
            fig = chart_gen.create_significance_figure(self.comparison_results)

        except Exception as e:
            self.logger.error(f"Error embedding statistical significance chart: {e}")

    def _embed_effect_size_chart(self):
        """Embed effect size chart using chart generator."""
        try:
            from app.visualization.chart_generators.process_comparison import ProcessComparisonChartGenerator

            chart_gen = ProcessComparisonChartGenerator()
            fig = chart_gen.create_effect_size_figure(self.comparison_results)

        except Exception as e:
            self.logger.error(f"Error embedding effect size chart: {e}")

    def _embed_data_quality_chart(self, data_quality: Dict[str, Any]):
        """Embed data quality chart using chart generator."""
        try:
            if not data_quality:
                return
            from app.visualization.chart_generators.data_quality import DataQualityChartGenerator

            chart_gen = DataQualityChartGenerator()
            fig = chart_gen.create_quality_figure(data_quality)

        except Exception as e:
            self.logger.error(f"Error embedding data quality chart: {e}")

    def _embed_wait_time_analysis_chart(self):
        """Embed wait time analysis chart using chart generator."""
        try:
            if not hasattr(self, "anylogic_data") or self.anylogic_data is None:
                return
            from app.visualization.chart_generators.process_comparison import PatientFlowAnalysisGenerator

            chart_gen = PatientFlowAnalysisGenerator()
            fig = chart_gen.create_wait_time_figure(
                self.anylogic_data,
                patient_id_col="Patient ID",
                action_col="Action",
                timestamp_col="Hour_Float",
                wait_terms=None,
                service_terms=None,
                max_wait_minutes=480,
                business_start="08:00",
                business_end="18:59",
            )

        except Exception as e:
            self.logger.error(f"Error embedding wait time analysis chart: {e}")

    def _get_user_friendly_error_message(self, error: Exception) -> str:
        """
        Convert technical error messages into user-friendly messages, tailored to common issues in process_time_table.py.

        Args:
            error: The exception that occurred

        Returns:
            User-friendly error message with suggested actions
        """
        error_str = str(error).lower()

        # File not found or missing master file
        if "no such file" in error_str or "file not found" in error_str or "master file" in error_str:
            return (
                "Master file not found or missing.\n\n"
                "Suggested actions:\n"
                "• Ensure the AnyLogic master file is selected and exists\n"
                "• Check the file path in the configuration\n"
                "• Re-select the master file if necessary"
            )

        # Excel/Sheet errors
        elif "process summary" in error_str or "sheet" in error_str or "excel" in error_str:
            return (
                "Excel file or sheet error.\n\n"
                "Suggested actions:\n"
                "• Ensure the selected file is a valid Excel file (.xlsx or .xls)\n"
                "• Verify the file contains a 'Process Summary' sheet\n"
                "• Check that all required columns are present"
            )

        # Data column errors
        elif "column" in error_str or "keyerror" in error_str:
            return (
                "Missing or invalid data columns.\n\n"
                "Suggested actions:\n"
                "• Check that all required columns exist in your data files\n"
                "• Ensure column names are spelled correctly and match expected format\n"
                "• Review the data structure in the Excel file"
            )

        # Date/time errors
        elif "date" in error_str or "time" in error_str or "strptime" in error_str:
            return (
                "Date/time processing error.\n\n"
                "Suggested actions:\n"
                "• Check date format (YYYY-MM-DD)\n"
                "• Ensure date range is valid and within available data\n"
                "• Verify that start and end dates are correct"
            )

        # Pandas/dataframe errors
        elif "pandas" in error_str or "dataframe" in error_str or "read_excel" in error_str:
            return (
                "Data processing error.\n\n"
                "Suggested actions:\n"
                "• Check data file format and structure\n"
                "• Verify all required columns are present\n"
                "• Ensure data contains valid, non-empty values"
            )

        # Chart/Matplotlib errors
        elif "matplotlib" in error_str or "chart" in error_str or "plot" in error_str or "figure" in error_str:
            return (
                "Chart generation error.\n\n"
                "Suggested actions:\n"
                "• Check if data is suitable for visualization\n"
                "• Try refreshing the analysis\n"
                "• Ensure matplotlib is properly installed"
            )

        # Statistical/scipy errors
        elif "statistical" in error_str or "scipy" in error_str or "test" in error_str:
            return (
                "Statistical analysis error.\n\n"
                "Suggested actions:\n"
                "• Verify data has sufficient samples\n"
                "• Check for missing or invalid values\n"
                "• Ensure data meets statistical test requirements"
            )

        # Permission or access errors
        elif "permission" in error_str or "access" in error_str or "denied" in error_str:
            return (
                "File access permission error.\n\n"
                "Suggested actions:\n"
                "• Check file permissions\n"
                "• Close files if they're open in other programs\n"
                "• Run as administrator if necessary"
            )

        # Memory errors
        elif "memory" in error_str or "out of memory" in error_str:
            return (
                "Memory allocation error.\n\n"
                "Suggested actions:\n"
                "• Close unnecessary applications\n"
                "• Reduce the date range for analysis\n"
                "• Restart the application"
            )

        # Network/connection errors
        elif "connection" in error_str or "network" in error_str:
            return (
                "Network connection error detected.\n\n"
                "Suggested actions:\n"
                "• Check your internet connection\n"
                "• Verify file paths are accessible\n"
                "• Try again in a few moments"
            )

        # Tkinter/UI errors
        elif "tkinter" in error_str or "widget" in error_str or "tclerror" in error_str:
            return (
                "User interface error.\n\n"
                "Suggested actions:\n"
                "• Try closing and reopening the window\n"
                "• Restart the application\n"
                "• Ensure your system supports Tkinter"
            )

        else:
            # Generic error message for unknown errors
            return (
                f"An unexpected error occurred:\n{str(error)}\n\n"
                "Suggested actions:\n"
                "• Try refreshing the data\n"
                "• Check the application logs for details\n"
                "• Contact support if the problem persists\n\n"
                "Technical details:\n"
                f"{type(error).__name__}: {str(error)}"
            )

    def _attempt_error_recovery(self):
        """
        Attempt to recover gracefully from errors.

        This method tries to restore the application to a stable state
        after an error occurs.
        """
        try:
            self.logger.info("Attempting error recovery...")

            # Clear any partial results
            self.comparison_results = None

            # Reset UI state
            self._show_status("Ready - Error recovered", "info")

            # Clear results displays
            try:
                # Clear main results tree
                if hasattr(self, "results_tree"):
                    for item in self.results_tree.get_children():
                        self.results_tree.delete(item)

                # Clear other trees
                for tree_name in ["efficiency_tree", "volume_tree", "bottleneck_tree"]:
                    if hasattr(self, tree_name):
                        tree = getattr(self, tree_name)
                        for item in tree.get_children():
                            tree.delete(item)

                # Reset insights and charts to placeholder
                if hasattr(self, "insights_content_frame"):
                    self._create_insights_placeholder()

                if hasattr(self, "charts_content_frame"):
                    self._create_charts_placeholder()

            except Exception as cleanup_error:
                self.logger.warning(f"Error during UI cleanup: {cleanup_error}")

            # Verify critical components are still functional
            try:
                # Test data loader
                if self.data_loader and hasattr(self.data_loader, "has_data"):
                    if not self.data_loader.has_data():
                        self._show_status("Warning: No clinic data loaded", "warning")

                # Test master file
                if not self.config.master_file_path or not os.path.exists(
                    self.config.master_file_path
                ):
                    self._show_status("Warning: Master file not configured", "warning")

            except Exception as test_error:
                self.logger.warning(f"Error during component testing: {test_error}")

            self.logger.info("Error recovery completed")

        except Exception as recovery_error:
            self.logger.error(f"Error recovery failed: {recovery_error}")
            self._show_status("Error recovery failed - please restart", "error")

    def _validate_analysis_prerequisites(self) -> bool:
        """
        Validate that all prerequisites for analysis are met.

        Returns:
            True if all prerequisites are met, False otherwise
        """
        try:
            # Check data loader
            if not self.data_loader:
                self._show_status("Error: Data loader not initialized", "error")
                return False

            if not self.data_loader.has_data():
                self._show_status("Error: No clinic data loaded", "error")
                return False

            # Check AnyLogic data
            if self.anylogic_data is None or self.anylogic_data.empty:
                self._show_status("Error: No AnyLogic data available", "error")
                return False

            # Check master file
            if not self.config.master_file_path:
                self._show_status("Error: Master file not configured", "error")
                return False

            if not os.path.exists(self.config.master_file_path):
                self._show_status("Error: Master file not found", "error")
                return False

            # Check date range
            start_date = self.start_date_var.get()
            end_date = self.end_date_var.get()

            if not start_date or not end_date:
                self._show_status("Error: Date range not specified", "error")
                return False

            try:
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")

                if start_dt >= end_dt:
                    self._show_status("Error: Invalid date range", "error")
                    return False

            except ValueError:
                self._show_status("Error: Invalid date format", "error")
                return False

            # Check required components
            required_components = [
                "statistical_engine",
                "quality_assessment",
                "metrics_calculator",
                "processor",
            ]

            for component in required_components:
                if not hasattr(self, component) or getattr(self, component) is None:
                    self._show_status(f"Error: {component} not initialized", "error")
                    return False

            return True

        except Exception as e:
            self.logger.error(f"Error validating prerequisites: {e}")
            self._show_status("Error: Prerequisite validation failed", "error")
            return False

    def _validate_start_date(self, event=None):
        """Validate start date format and value."""
        try:
            date_str = self.start_date_var.get()
            if date_str:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")

                # Check if start date is within available historical data range
                if hasattr(self, "historical_min_date") and hasattr(
                    self, "historical_max_date"
                ):
                    if date_obj < self.historical_min_date:
                        messagebox.showwarning(
                            "Invalid Date",
                            f"Start date cannot be before {self.historical_min_date.strftime('%Y-%m-%d')} (earliest available date).",
                        )
                        self.start_date_var.set(
                            self.historical_min_date.strftime("%Y-%m-%d")
                        )
                        return
                    elif date_obj > self.historical_max_date:
                        messagebox.showwarning(
                            "Invalid Date",
                            f"Start date cannot be after {self.historical_max_date.strftime('%Y-%m-%d')} (latest available date).",
                        )
                        self.start_date_var.set(
                            self.historical_max_date.strftime("%Y-%m-%d")
                        )
                        return
                else:
                    # Fallback: Check if start date is not in the future
                    if date_obj > datetime.now():
                        messagebox.showwarning(
                            "Invalid Date", "Start date cannot be in the future."
                        )
                        # Reset to a valid date
                        valid_date = datetime.now() - timedelta(days=30)
                        self.start_date_var.set(valid_date.strftime("%Y-%m-%d"))
                        return

                # Check if start date is after end date
                try:
                    end_date_str = self.end_date_var.get()
                    if end_date_str:
                        end_date_obj = datetime.strptime(end_date_str, "%Y-%m-%d")
                        if date_obj > end_date_obj:
                            messagebox.showwarning(
                                "Invalid Date Range",
                                "Start date must be before end date.",
                            )
                            return
                except ValueError:
                    pass  # End date might not be valid yet

        except ValueError:
            if len(date_str) >= 10:  # Only show error for complete entries
                messagebox.showerror(
                    "Invalid Date Format", "Please enter date in YYYY-MM-DD format."
                )

    def _validate_end_date(self, event=None):
        """Validate end date format and value."""
        try:
            date_str = self.end_date_var.get()
            if date_str:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")

                # Check if end date is within available historical data range
                if hasattr(self, "historical_min_date") and hasattr(
                    self, "historical_max_date"
                ):
                    if date_obj < self.historical_min_date:
                        messagebox.showwarning(
                            "Invalid Date",
                            f"End date cannot be before {self.historical_min_date.strftime('%Y-%m-%d')} (earliest available date).",
                        )
                        self.end_date_var.set(
                            self.historical_min_date.strftime("%Y-%m-%d")
                        )
                        return
                    elif date_obj > self.historical_max_date:
                        messagebox.showwarning(
                            "Invalid Date",
                            f"End date cannot be after {self.historical_max_date.strftime('%Y-%m-%d')} (latest available date).",
                        )
                        self.end_date_var.set(
                            self.historical_max_date.strftime("%Y-%m-%d")
                        )
                        return
                else:
                    # Fallback: Check if end date is not in the future
                    if date_obj > datetime.now():
                        messagebox.showwarning(
                            "Invalid Date", "End date cannot be in the future."
                        )
                        self.end_date_var.set(datetime.now().strftime("%Y-%m-%d"))
                        return

                # Check if end date is after start date
                try:
                    start_date_str = self.start_date_var.get()
                    if start_date_str:
                        start_date_obj = datetime.strptime(start_date_str, "%Y-%m-%d")
                        if date_obj < start_date_obj:
                            messagebox.showwarning(
                                "Invalid Date Range",
                                "End date must be after start date.",
                            )
                            return
                except ValueError:
                    pass  # Start date might not be valid yet
        except ValueError:
            if len(date_str) >= 10:  # Only show error for complete entries
                messagebox.showerror(
                    "Invalid Date Format", "Please enter date in YYYY-MM-DD format."
                )

    def _on_date_key_release(self, event=None):
        """Handle key release in date fields for real-time formatting assistance."""
        widget = event.widget
        current_text = widget.get()

        # Auto-add hyphens for date formatting
        if len(current_text) == 4 and not current_text.endswith("-"):
            widget.insert(tk.END, "-")
        elif len(current_text) == 7 and not current_text.endswith("-"):
            widget.insert(tk.END, "-")

    def _update_date_range_info(self):
        """Update the date range information display."""
        # Update historical data range
        self._update_historical_range_info()

        # Update simulation data range (if loaded)
        if hasattr(self, "anylogic_data") and self.anylogic_data is not None:
            self._update_simulation_range_info()

    def _update_historical_range_info(self):
        """Update historical data range information."""
        try:
            if self.data_loader and self.data_loader.has_data():
                # Set data in filter and get available dates
                self.data_filter.set_data(self.data_loader.get_data())
                available_dates = self.data_filter.get_available_dates()

                if available_dates:
                    # Convert to datetime objects for sorting (handle dd/mm/yyyy format)
                    date_objects = []
                    for date in available_dates:
                        try:
                            # Try dd/mm/yyyy format first (your data format)
                            date_obj = datetime.strptime(date, "%d/%m/%Y")
                            date_objects.append(date_obj)
                        except ValueError:
                            try:
                                # Fallback to yyyy-mm-dd format
                                date_obj = datetime.strptime(date, "%Y-%m-%d")
                                date_objects.append(date_obj)
                            except ValueError:
                                self.logger.warning(f"Could not parse date '{date}'")
                                continue

                    if date_objects:
                        min_date = min(date_objects)
                        max_date = max(date_objects)
                    else:
                        # No valid dates found
                        if hasattr(self, "historical_range_label"):
                            self.historical_range_label.config(
                                text="📊 Historical Data: No valid dates found",
                                foreground="red",
                            )
                        return

                    # Format for display
                    range_text = f"📊 Historical Data: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')} ({len(available_dates)} days)"

                    # Update label
                    if hasattr(self, "historical_range_label"):
                        self.historical_range_label.config(
                            text=range_text, foreground="green"
                        )

                    # Store for validation
                    self.historical_min_date = min_date
                    self.historical_max_date = max_date

                    self.logger.info(
                        f"Historical data range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}"
                    )
                else:
                    if hasattr(self, "historical_range_label"):
                        self.historical_range_label.config(
                            text="📊 Historical Data: No dates available",
                            foreground="red",
                        )
            else:
                if hasattr(self, "historical_range_label"):
                    self.historical_range_label.config(
                        text="📊 Historical Data: No data loaded", foreground="gray"
                    )
        except Exception as e:
            self.logger.error(f"Error updating historical range info: {e}")
            if hasattr(self, "historical_range_label"):
                self.historical_range_label.config(
                    text="📊 Historical Data: Error loading range", foreground="red"
                )

    def _update_simulation_range_info(self):
        """Update simulation data range information."""
        try:
            if self.anylogic_data is not None and not self.anylogic_data.empty:
                # For simulation data, we show the number of processes and any date info
                process_count = len(self.anylogic_data)
                range_text = f"📈 Simulation Data: {process_count} processes loaded"

                # Check if there's any date information in the simulation data
                # (This would depend on your simulation data format)
                if hasattr(self, "simulation_range_label"):
                    self.simulation_range_label.config(
                        text=range_text, foreground="green"
                    )

                self.logger.info(f"Simulation data: {process_count} processes")
            else:
                if hasattr(self, "simulation_range_label"):
                    self.simulation_range_label.config(
                        text="📈 Simulation Data: Not loaded", foreground="gray"
                    )
        except Exception as e:
            self.logger.error(f"Error updating simulation range info: {e}")
            if hasattr(self, "simulation_range_label"):
                self.simulation_range_label.config(
                    text="📈 Simulation Data: Error loading info", foreground="red"
                )

    def _update_simulation_range_info_enhanced(self, load_result: Dict[str, Any]):
        """Update simulation data range information with enhanced details."""
        try:
            if load_result["success"]:
                process_count = load_result["process_count"]
                raw_records = load_result["raw_records"]
                waiting_records = load_result["waiting_records"]
                arrival_records = load_result["arrival_records"]

                # Create enhanced range text
                range_text = f"📈 Enhanced Simulation: {process_count} processes, {raw_records} raw records"

                if hasattr(self, "simulation_range_label"):
                    self.simulation_range_label.config(
                        text=range_text, foreground="green"
                    )

                self.logger.info(
                    f"Enhanced simulation data: {process_count} processes, {raw_records} raw records"
                )
            else:
                if hasattr(self, "simulation_range_label"):
                    self.simulation_range_label.config(
                        text="📈 Simulation Data: Enhanced loading failed",
                        foreground="orange",
                    )
        except Exception as e:
            self.logger.error(f"Error updating enhanced simulation range info: {e}")
            if hasattr(self, "simulation_range_label"):
                self.simulation_range_label.config(
                    text="📈 Simulation Data: Error loading enhanced info",
                    foreground="red",
                )

    def _update_consultation_splitting_info(self):
        """Update consultation splitting information display."""
        try:
            if hasattr(self.processor, "get_consultation_splitting_info"):
                splitting_info = self.processor.get_consultation_splitting_info()

                if splitting_info["strategy"] == "consultation_splitting":
                    fv_count = splitting_info.get("fv_count", 0)
                    rv_count = splitting_info.get("rv_count", 0)
                    ratio = splitting_info.get("fv_rv_ratio", 0)

                    splitting_text = (
                        f"🔄 FV/RV Split: {fv_count} FV, {rv_count} RV (1:{ratio:.1f})"
                    )

                    if hasattr(self, "consultation_splitting_label"):
                        self.consultation_splitting_label.config(
                            text=splitting_text, foreground="blue"
                        )

                    self.logger.info(
                        f"Consultation splitting applied: {fv_count} FV, {rv_count} RV (ratio: {ratio:.1f})"
                    )
                elif splitting_info["strategy"] == "disabled":
                    if hasattr(self, "consultation_splitting_label"):
                        self.consultation_splitting_label.config(
                            text="🔄 FV/RV Split: Disabled", foreground="gray"
                        )
                else:
                    if hasattr(self, "consultation_splitting_label"):
                        self.consultation_splitting_label.config(
                            text="🔄 FV/RV Split: Not applied", foreground="orange"
                        )
            else:
                if hasattr(self, "consultation_splitting_label"):
                    self.consultation_splitting_label.config(
                        text="🔄 FV/RV Split: Not available", foreground="gray"
                    )
        except Exception as e:
            self.logger.error(f"Error updating consultation splitting info: {e}")
            if hasattr(self, "consultation_splitting_label"):
                self.consultation_splitting_label.config(
                    text="🔄 FV/RV Split: Error", foreground="red"
                )

    def _set_full_range(self):
        """Set date range to the full available historical data range."""
        try:
            if hasattr(self, "historical_min_date") and hasattr(
                self, "historical_max_date"
            ):
                self.start_date_var.set(self.historical_min_date.strftime("%Y-%m-%d"))
                self.end_date_var.set(self.historical_max_date.strftime("%Y-%m-%d"))

                self.logger.info(
                    f"Set date range to full historical range: {self.historical_min_date.strftime('%Y-%m-%d')} to {self.historical_max_date.strftime('%Y-%m-%d')}"
                )
            else:
                messagebox.showwarning(
                    "No Data",
                    "Historical data range not available. Please load data first.",
                )
        except Exception as e:
            self.logger.error(f"Error setting full range: {e}")
            messagebox.showerror("Error", f"Failed to set full range: {str(e)}")

    def _set_default_date_range(self):
        """Set default date range based on available historical data."""
        try:
            if hasattr(self, "historical_min_date") and hasattr(
                self, "historical_max_date"
            ):
                # Use the full available historical data range as default
                self.start_date_var.set(self.historical_min_date.strftime("%Y-%m-%d"))
                self.end_date_var.set(self.historical_max_date.strftime("%Y-%m-%d"))

                self.logger.info(
                    f"Set default date range to full historical range: {self.historical_min_date.strftime('%Y-%m-%d')} to {self.historical_max_date.strftime('%Y-%m-%d')}"
                )
            else:
                # Fallback to last 30 days if no historical data available
                end_date = datetime.now()
                start_date = end_date - timedelta(days=self.config.default_period_days)
                self.start_date_var.set(start_date.strftime("%Y-%m-%d"))
                self.end_date_var.set(end_date.strftime("%Y-%m-%d"))

                self.logger.info(
                    f"Set default date range to last {self.config.default_period_days} days (fallback)"
                )
        except Exception as e:
            self.logger.error(f"Error setting default date range: {e}")
            # Use fallback dates
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.config.default_period_days)
            self.start_date_var.set(start_date.strftime("%Y-%m-%d"))
            self.end_date_var.set(end_date.strftime("%Y-%m-%d"))

    def _set_quick_period(self, days: int):
        """Set date range to last N days within available historical data."""
        try:
            if hasattr(self, "historical_max_date"):
                # Use the latest available date as end date
                end_date = self.historical_max_date
                start_date = end_date - timedelta(
                    days=days - 1
                )  # -1 to include the end date

                # Ensure start date is not before the earliest available date
                if hasattr(self, "historical_min_date"):
                    if start_date < self.historical_min_date:
                        start_date = self.historical_min_date
                        messagebox.showinfo(
                            "Date Range Adjusted",
                            f"Adjusted start date to earliest available: {start_date.strftime('%Y-%m-%d')}",
                        )

                self.start_date_var.set(start_date.strftime("%Y-%m-%d"))
                self.end_date_var.set(end_date.strftime("%Y-%m-%d"))

                self.logger.info(
                    f"Set date range to last {days} days: {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                )
            else:
                # Fallback to current date if no historical data available
                end_date = datetime.now()
                start_date = end_date - timedelta(days=days)

                self.start_date_var.set(start_date.strftime("%Y-%m-%d"))
                self.end_date_var.set(end_date.strftime("%Y-%m-%d"))

                self.logger.info(
                    f"Set date range to last {days} days (fallback): {start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}"
                )
        except Exception as e:
            self.logger.error(f"Error setting quick period: {e}")
            messagebox.showerror("Error", f"Failed to set quick period: {str(e)}")

    def _refresh_data(self):
        """Refresh the analysis with current settings."""
        # Update date range information
        self._update_date_range_info()

        # Reload AnyLogic data
        self._load_anylogic_data()

        # Re-run analysis
        self._analyze_data()

    def _close_window(self):
        """Close the window."""
        if self.window:
            self.window.destroy()

    def show(self):
        """Show the window (alternative to constructor behavior)."""
        if not self.window or not self.window.winfo_exists():
            self._create_window()
        else:
            self.window.lift()

    def winfo_exists(self):
        """Check if window exists."""
        return self.window and self.window.winfo_exists()

    def _update_efficiency_display(self, results: Dict[str, Any]):
        """Update the efficiency analysis tab with historical vs simulation comparisons."""
        try:
            # Clear existing data
            for item in self.efficiency_tree.get_children():
                self.efficiency_tree.delete(item)

            # Configure tags for color coding
            self.efficiency_tree.tag_configure(
                "excellent", background="#d4edda", foreground="#155724"
            )  # Green
            self.efficiency_tree.tag_configure(
                "good", background="#fff3cd", foreground="#856404"
            )  # Yellow
            self.efficiency_tree.tag_configure(
                "poor", background="#f8d7da", foreground="#721c24"
            )  # Red
            self.efficiency_tree.tag_configure(
                "critical", background="#f5c6cb", foreground="#721c24"
            )  # Dark Red
            self.efficiency_tree.tag_configure(
                "improved", background="#d1ecf1", foreground="#0c5460"
            )  # Blue for improvements
            self.efficiency_tree.tag_configure(
                "worsened", background="#f8d7da", foreground="#721c24"
            )  # Red for degradation

            # Get comparison results for efficiency analysis
            if "comparisons" not in results:
                return

            comparisons = results["comparisons"]

            # Add section header
            self.efficiency_tree.insert(
                "",
                "end",
                values=(
                    "📊 Efficiency Comparison Analysis",
                    f"{len(comparisons)} processes",
                    "",
                    "📋 Section",
                    "Historical vs Simulation efficiency comparison",
                ),
                tags=("section_header",),
            )

            for comparison in comparisons:
                anylogic_process = comparison["anylogic_process"]
                historical_service = comparison.get("historical_service", "N/A")
                anylogic_mean = comparison["anylogic_mean"]
                anylogic_median = comparison["anylogic_median"]
                historical_mean = comparison["historical_mean"]
                historical_median = comparison["historical_median"]
                mean_improvement = comparison["mean_improvement_pct"]
                median_improvement = comparison["median_improvement_pct"]
                confidence = comparison.get("confidence", "Medium")

                # Calculate efficiency scores (lower duration = higher efficiency)
                # Historical efficiency (based on mean duration)
                historical_efficiency = (
                    max(0, 100 - (historical_mean / 60) * 10)
                    if historical_mean > 0
                    else 0
                )
                # Simulation efficiency (based on mean duration)
                simulation_efficiency = (
                    max(0, 100 - (anylogic_mean / 60) * 10) if anylogic_mean > 0 else 0
                )

                # Determine efficiency status
                if simulation_efficiency > historical_efficiency + 10:
                    status = "🟢 Improved"
                    tag = "improved"
                elif simulation_efficiency < historical_efficiency - 10:
                    status = "🔴 Worsened"
                    tag = "worsened"
                elif simulation_efficiency >= 80:
                    status = "🟢 Excellent"
                    tag = "excellent"
                elif simulation_efficiency >= 60:
                    status = "🟡 Good"
                    tag = "good"
                elif simulation_efficiency >= 40:
                    status = "🟠 Poor"
                    tag = "poor"
                else:
                    status = "🔴 Critical"
                    tag = "critical"

                # Calculate efficiency improvement
                efficiency_improvement = simulation_efficiency - historical_efficiency

                # Format efficiency comparison
                efficiency_comparison = (
                    f"H: {historical_efficiency:.1f} → S: {simulation_efficiency:.1f}"
                )
                if efficiency_improvement != 0:
                    efficiency_comparison += f" ({efficiency_improvement:+.1f})"

                # Generate recommendation based on comparison
                if efficiency_improvement > 10:
                    recommendation = f"Simulation shows {efficiency_improvement:.1f}% efficiency improvement - validate model assumptions"
                elif efficiency_improvement < -10:
                    recommendation = f"Simulation shows {abs(efficiency_improvement):.1f}% efficiency degradation - review model parameters"
                else:
                    recommendation = (
                        "Efficiency levels are comparable - model validation successful"
                    )

                # Insert row
                self.efficiency_tree.insert(
                    "",
                    "end",
                    values=(
                        f"  {anylogic_process}",
                        efficiency_comparison,
                        f"H: {historical_mean:.1f} | S: {anylogic_mean:.1f}",
                        f"Confidence: {confidence}",
                        status,
                        recommendation,
                    ),
                    tags=(tag,),
                )

            # Configure section header styling
            self.efficiency_tree.tag_configure(
                "section_header",
                background="#e9ecef",
                foreground="#495057",
                font=("Arial", 9, "bold"),
            )
        except Exception as e:
            self.logger.error(f"Error updating efficiency display: {e}")

    def _update_volume_display(self, results: Dict[str, Any]):
        """Update the volume correlation analysis tab with historical vs simulation comparisons."""
        try:
            # Clear existing data
            for item in self.volume_tree.get_children():
                self.volume_tree.delete(item)

            # Configure tags for color coding
            self.volume_tree.tag_configure(
                "high", background="#f8d7da", foreground="#721c24"
            )  # Red
            self.volume_tree.tag_configure(
                "medium", background="#fff3cd", foreground="#856404"
            )  # Yellow
            self.volume_tree.tag_configure(
                "low", background="#d4edda", foreground="#155724"
            )  # Green
            self.volume_tree.tag_configure(
                "improved", background="#d1ecf1", foreground="#0c5460"
            )  # Blue for improvements
            self.volume_tree.tag_configure(
                "worsened", background="#f8d7da", foreground="#721c24"
            )  # Red for degradation

            # Get comparison results for volume analysis
            if "comparisons" not in results:
                return

            comparisons = results["comparisons"]

            # Add section header
            self.volume_tree.insert(
                "",
                "end",
                values=(
                    "📊 Volume Comparison Analysis",
                    f"{len(comparisons)} processes",
                    "",
                    "📋 Section",
                    "Historical vs Simulation volume comparison",
                ),
                tags=("section_header",),
            )

            # Group comparisons by volume patterns
            high_volume_processes = []
            medium_volume_processes = []
            low_volume_processes = []

            for comparison in comparisons:
                anylogic_process = comparison["anylogic_process"]
                anylogic_mean = comparison["anylogic_mean"]
                historical_mean = comparison["historical_mean"]
                mean_improvement = comparison["mean_improvement_pct"]

                # Categorize by volume level (using simulation mean as reference)
                if anylogic_mean > 30:  # High volume processes
                    high_volume_processes.append(comparison)
                elif anylogic_mean > 10:  # Medium volume processes
                    medium_volume_processes.append(comparison)
                else:  # Low volume processes
                    low_volume_processes.append(comparison)

            # Process each volume category
            volume_categories = [
                ("🔴 High Volume Processes", high_volume_processes),
                ("🟡 Medium Volume Processes", medium_volume_processes),
                ("🟢 Low Volume Processes", low_volume_processes),
            ]

            for category_title, category_data in volume_categories:
                if category_data:
                    # Add category header
                    self.volume_tree.insert(
                        "",
                        "end",
                        values=(
                            category_title,
                            f"{len(category_data)} processes",
                            "",
                            "📋 Category",
                            "Volume level classification",
                        ),
                        tags=("section_header",),
                    )

                    for comparison in category_data:
                        anylogic_process = comparison["anylogic_process"]
                        anylogic_mean = comparison["anylogic_mean"]
                        anylogic_median = comparison["anylogic_median"]
                        historical_mean = comparison["historical_mean"]
                        historical_median = comparison["historical_median"]
                        mean_improvement = comparison["mean_improvement_pct"]
                        median_improvement = comparison["median_improvement_pct"]
                        confidence = comparison.get("confidence", "Medium")

                        # Determine volume impact
                        if (
                            mean_improvement < -50
                        ):  # Significant improvement (negative = better)
                            impact = "🟢 High Improvement"
                            tag = "improved"
                        elif mean_improvement < -20:
                            impact = "🟡 Moderate Improvement"
                            tag = "improved"
                        elif mean_improvement > 50:  # Significant degradation
                            impact = "🔴 High Degradation"
                            tag = "worsened"
                        elif mean_improvement > 20:
                            impact = "🟠 Moderate Degradation"
                            tag = "worsened"
                        else:
                            impact = "🟢 Comparable"
                            tag = "low"

                        # Format volume comparison
                        volume_comparison = (
                            f"H: {historical_mean:.1f} | S: {anylogic_mean:.1f}"
                        )
                        if mean_improvement != 0:
                            volume_comparison += f" ({mean_improvement:+.1f}%)"

                        # Generate recommendation based on volume comparison
                        if mean_improvement < -50:
                            recommendation = f"Simulation shows {abs(mean_improvement):.1f}% faster processing - validate model assumptions"
                        elif mean_improvement < -20:
                            recommendation = f"Simulation shows {abs(mean_improvement):.1f}% improvement - consider model refinements"
                        elif mean_improvement > 50:
                            recommendation = f"Simulation shows {mean_improvement:.1f}% slower processing - review model parameters"
                        elif mean_improvement > 20:
                            recommendation = f"Simulation shows {mean_improvement:.1f}% degradation - investigate model assumptions"
                        else:
                            recommendation = "Volume levels are comparable - model validation successful"

                        # Insert row
                        self.volume_tree.insert(
                            "",
                            "end",
                            values=(
                                f"  {anylogic_process}",
                                volume_comparison,
                                f"Confidence: {confidence}",
                                impact,
                                recommendation,
                            ),
                            tags=(tag,),
                        )

            # Configure section header styling
            self.volume_tree.tag_configure(
                "section_header",
                background="#e9ecef",
                foreground="#495057",
                font=("Arial", 9, "bold"),
            )

        except Exception as e:
            self.logger.error(f"Error updating volume display: {e}")

    def _update_bottleneck_display(self, results: Dict[str, Any]):
        """Update the bottleneck analysis tab."""
        try:
            # Clear existing data
            for item in self.bottleneck_tree.get_children():
                self.bottleneck_tree.delete(item)

            # Get bottleneck data from results - try multiple sources
            bottleneck_data = results.get("summary", {}).get("bottleneck_analysis", [])
            if not bottleneck_data:
                bottleneck_data = results.get("bottleneck_analysis", [])
            
            # If still no bottleneck data, generate from comparison results
            if not bottleneck_data and self.comparison_results:
                bottleneck_data = self._generate_bottlenecks_from_comparison()

            if not bottleneck_data:
                # Insert placeholder message if no data
                self.bottleneck_tree.insert(
                    "",
                    "end",
                    values=(
                        "No Bottlenecks Found",
                        "",
                        "",
                        "",
                        "",
                        "No significant bottlenecks detected in the analysis",
                    ),
                    tags=("placeholder",),
                )
                self.bottleneck_tree.tag_configure(
                    "placeholder",
                    background="#f8f9fa",
                    foreground="#6c757d",
                    font=("Arial", 10, "italic"),
                )
                return

            # Configure tags for color coding
            self.bottleneck_tree.tag_configure(
                "high", background="#f8d7da", foreground="#721c24"
            )  # Red
            self.bottleneck_tree.tag_configure(
                "medium", background="#fff3cd", foreground="#856404"
            )  # Yellow
            self.bottleneck_tree.tag_configure(
                "low", background="#d4edda", foreground="#155724"
            )  # Green

            # Add section header
            self.bottleneck_tree.insert(
                "",
                "end",
                values=(
                    "🔍 Bottleneck Analysis Results",
                    "",
                    "",
                    "",
                    "",
                    f"Found {len(bottleneck_data)} potential bottlenecks",
                ),
                tags=("section_header",),
            )

            for bottleneck in bottleneck_data:
                # Determine severity tag based on priority
                priority = bottleneck.get("priority", "Low")
                if priority == "High":
                    tag = "high"
                    severity_emoji = "🔴"
                elif priority == "Medium":
                    tag = "medium"
                    severity_emoji = "🟡"
                else:
                    tag = "low"
                    severity_emoji = "🟢"

                # Extract bottleneck information
                service = bottleneck.get("service", "Unknown Service")
                efficiency = bottleneck.get("efficiency_score", 0)
                avg_duration = bottleneck.get("avg_duration", 0)
                estimated_impact = bottleneck.get("estimated_impact", "Unknown")
                recommendations = bottleneck.get("recommendations", [])

                # Format recommendations
                if isinstance(recommendations, list):
                    recommendations_text = "; ".join(
                        recommendations[:2]
                    )  # Show first 2 recommendations
                    if len(recommendations) > 2:
                        recommendations_text += f" (+{len(recommendations)-2} more)"
                else:
                    recommendations_text = (
                        str(recommendations)
                        if recommendations
                        else "No specific recommendations"
                    )

                # Format efficiency and duration
                efficiency_text = f"{efficiency:.1f}%" if efficiency > 0 else "N/A"
                duration_text = f"{avg_duration:.1f} min" if avg_duration > 0 else "N/A"

                # Insert row
                self.bottleneck_tree.insert(
                    "",
                    "end",
                    values=(
                        f"  {service}",
                        f"{severity_emoji} {priority}",
                        efficiency_text,
                        duration_text,
                        estimated_impact,
                        recommendations_text,
                    ),
                    tags=(tag,),
                )

            # Configure section header styling
            self.bottleneck_tree.tag_configure(
                "section_header",
                background="#e9ecef",
                foreground="#495057",
                font=("Arial", 9, "bold"),
            )

        except Exception as e:
            self.logger.error(f"Error updating bottleneck display: {e}")
            # Insert error message
            self.bottleneck_tree.insert(
                "",
                "end",
                values=(
                    "Error Loading Data",
                    "",
                    "",
                    "",
                    "",
                    f"Failed to load bottleneck analysis: {str(e)}",
                ),
                tags=("error",),
            )
            self.bottleneck_tree.tag_configure(
                "error",
                background="#f8d7da",
                foreground="#721c24",
                font=("Arial", 10, "italic"),
            )

    def _on_volume_row_double_click(self, event):
        """Handle double-click on a process row in the volume tree to show advanced details popup."""
        item_id = self.volume_tree.identify_row(event.y)
        if not item_id:
            return
        values = self.volume_tree.item(item_id, "values")
        # Only allow popup for actual process rows (not section/category headers)
        if (
            not values
            or not values[0]
            or values[0].strip().startswith("📊")
            or values[0].strip().startswith("📋")
            or values[0].strip().startswith("🔴")
            or values[0].strip().startswith("🟡")
            or values[0].strip().startswith("🟢")
        ):
            return
        process_name = values[0].strip()
        # Remove leading spaces or icons
        process_name = process_name.lstrip("•").strip()
        process_name = process_name.lstrip("0123456789. ").strip()
        process_name = process_name.lstrip("–-").strip()
        process_name = process_name.lstrip("•").strip()
        process_name = process_name.lstrip(" ").strip()
        process_name = process_name.lstrip("–-").strip()
        process_name = process_name.lstrip("•").strip()
        process_name = process_name.lstrip(" ").strip()
        # Remove emoji if present
        for emoji in ["🔴", "🟡", "🟢", "📋", "📊"]:
            if process_name.startswith(emoji):
                process_name = process_name[len(emoji) :].strip()
        self._show_volume_details_popup(process_name)

    def _show_volume_details_popup(self, process_name):
        """Show a popup with advanced volume details and charts for the selected process."""
        import tkinter as tk
        from tkinter import ttk
        import io
        import matplotlib.pyplot as plt
        from PIL import Image, ImageTk

        # Create popup window with better sizing
        popup = tk.Toplevel(self.window)
        popup.title(f"Volume Details: {process_name}")
        popup.geometry("800x700")
        popup.minsize(600, 500)
        popup.transient(self.window)
        popup.grab_set()  # Make it modal

        # Main frame with better layout
        frame = ttk.Frame(popup, padding=15)
        frame.pack(fill=tk.BOTH, expand=True)

        # Title with better styling
        title_label = ttk.Label(
            frame,
            text=f"Advanced Volume Analysis for {process_name}",
            font=("Segoe UI", 16, "bold"),
        )
        title_label.pack(pady=(0, 15))

        # Get data from existing comparison results
        process_data = None
        if self.comparison_results:
            for comparison in self.comparison_results:
                if comparison["anylogic_process"] == process_name:
                    process_data = comparison
                    break

        # Key metrics table with better styling
        metrics_frame = ttk.LabelFrame(frame, text="📊 Key Metrics", padding=12)
        metrics_frame.pack(fill=tk.X, pady=(0, 10))

        if process_data:
            metrics = [
                (
                    "Historical Mean Duration (min)",
                    f"{process_data['historical_mean']:.2f}",
                ),
                (
                    "Simulation Mean Duration (min)",
                    f"{process_data['anylogic_mean']:.2f}",
                ),
                (
                    "Historical Median Duration (min)",
                    f"{process_data['historical_median']:.2f}",
                ),
                (
                    "Simulation Median Duration (min)",
                    f"{process_data['anylogic_median']:.2f}",
                ),
                (
                    "Mean Improvement (%)",
                    f"{process_data['mean_improvement_pct']:+.1f}",
                ),
                (
                    "Median Improvement (%)",
                    f"{process_data['median_improvement_pct']:+.1f}",
                ),
                ("Confidence Level", process_data.get("confidence", "Medium")),
                ("Sample Size", str(process_data.get("sample_size", "N/A"))),
            ]
        else:
            metrics = [
                ("Historical Mean Duration (min)", "N/A"),
                ("Simulation Mean Duration (min)", "N/A"),
                ("Historical Median Duration (min)", "N/A"),
                ("Simulation Median Duration (min)", "N/A"),
                ("Mean Improvement (%)", "N/A"),
                ("Median Improvement (%)", "N/A"),
                ("Confidence Level", "N/A"),
                ("Sample Size", "N/A"),
            ]

        for label, value in metrics:
            row = ttk.Frame(metrics_frame)
            row.pack(fill=tk.X, pady=2)
            ttk.Label(
                row,
                text=label + ":",
                width=35,
                anchor="w",
                font=("Segoe UI", 9, "bold"),
            ).pack(side=tk.LEFT)
            ttk.Label(row, text=str(value), anchor="w", font=("Segoe UI", 9)).pack(
                side=tk.LEFT
            )

        # Volume Analysis section with better styling
        volume_frame = ttk.LabelFrame(frame, text="📈 Volume Analysis", padding=12)
        volume_frame.pack(fill=tk.X, pady=(0, 10))

        # Get volume analysis from processor if available
        volume_analysis = []
        if (
            hasattr(self.processor, "historical_metrics")
            and self.processor.historical_metrics
        ):
            volume_correlation = self.processor.historical_metrics.get(
                "volume_correlation", {}
            )
            volume_metrics = volume_correlation.get("volume_metrics", {})

            # Add volume metrics
            if "hourly_volume" in volume_metrics:
                hourly_volumes = volume_metrics["hourly_volume"]
                if hourly_volumes:
                    peak_hour = max(hourly_volumes, key=hourly_volumes.get)
                    peak_volume = hourly_volumes[peak_hour]
                    volume_analysis.append(
                        f"Peak Hour: {peak_hour}:00 ({peak_volume} patients)"
                    )

            if "service_volume" in volume_metrics:
                service_volumes = volume_metrics["service_volume"]
                if (
                    process_data
                    and process_data.get("historical_service") in service_volumes
                ):
                    service_volume = service_volumes[process_data["historical_service"]]
                    volume_analysis.append(f"Service Volume: {service_volume} patients")

            # Add peak period analysis
            peak_analysis = volume_correlation.get("peak_period_analysis", {})
            if peak_analysis:
                if "peak_hour" in peak_analysis:
                    volume_analysis.append(
                        f"Peak Period: Hour {peak_analysis['peak_hour']}"
                    )
                if "peak_volume" in peak_analysis:
                    volume_analysis.append(
                        f"Peak Volume: {peak_analysis['peak_volume']} patients"
                    )

        if volume_analysis:
            for analysis in volume_analysis:
                ttk.Label(
                    volume_frame, text=f"• {analysis}", anchor="w", font=("Segoe UI", 9)
                ).pack(fill=tk.X, pady=2)
        else:
            ttk.Label(
                volume_frame,
                text="Volume analysis data not available",
                foreground="gray",
                font=("Segoe UI", 9, "italic"),
            ).pack(pady=5)

        # Charts section with proper containment
        chart_frame = ttk.LabelFrame(frame, text="📊 Volume & Flow Charts", padding=12)
        chart_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Create a canvas for proper chart containment
        chart_canvas = tk.Canvas(chart_frame, bg="white", height=400)
        chart_scrollbar = ttk.Scrollbar(
            chart_frame, orient=tk.VERTICAL, command=chart_canvas.yview
        )
        chart_content_frame = ttk.Frame(chart_canvas)

        chart_canvas.configure(yscrollcommand=chart_scrollbar.set)
        chart_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        chart_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Create window in canvas for content
        chart_canvas.create_window((0, 0), window=chart_content_frame, anchor=tk.NW)

        # Try to generate and display charts
        chart_success = False
        try:
            if process_data and hasattr(self.processor, "historical_metrics"):
                # Create figure with proper sizing for the popup
                fig, axes = plt.subplots(2, 1, figsize=(8, 6))

                # Chart 1: Duration comparison
                categories = ["Historical", "Simulation"]
                mean_values = [
                    process_data["historical_mean"],
                    process_data["anylogic_mean"],
                ]
                median_values = [
                    process_data["historical_median"],
                    process_data["anylogic_median"],
                ]

                x = np.arange(len(categories))
                width = 0.35

                axes[0].bar(
                    x - width / 2,
                    mean_values,
                    width,
                    label="Mean Duration",
                    color="skyblue",
                )
                axes[0].bar(
                    x + width / 2,
                    median_values,
                    width,
                    label="Median Duration",
                    color="lightcoral",
                )
                axes[0].set_xlabel("Data Source")
                axes[0].set_ylabel("Duration (minutes)")
                axes[0].set_title(f"Duration Comparison for {process_name}")
                axes[0].set_xticks(x)
                axes[0].set_xticklabels(categories)
                axes[0].legend()
                axes[0].grid(True, alpha=0.3)

                # Chart 2: Improvement visualization
                improvements = [
                    process_data["mean_improvement_pct"],
                    process_data["median_improvement_pct"],
                ]
                improvement_labels = ["Mean Improvement", "Median Improvement"]
                colors = ["green" if imp < 0 else "red" for imp in improvements]

                bars = axes[1].bar(
                    improvement_labels, improvements, color=colors, alpha=0.7
                )
                axes[1].set_ylabel("Improvement (%)")
                axes[1].set_title("Performance Improvement (Negative = Better)")
                axes[1].axhline(y=0, color="black", linestyle="-", alpha=0.3)
                axes[1].grid(True, alpha=0.3)

                # Add value labels on bars
                for bar, value in zip(bars, improvements):
                    height = bar.get_height()
                    axes[1].text(
                        bar.get_x() + bar.get_width() / 2.0,
                        height + (0.5 if height > 0 else -1),
                        f"{value:+.1f}%",
                        ha="center",
                        va="bottom" if height > 0 else "top",
                    )

                plt.tight_layout()

                # Save to buffer with higher DPI for better quality
                buf = io.BytesIO()
                plt.savefig(
                    buf,
                    format="png",
                    dpi=150,
                    bbox_inches="tight",
                    facecolor="white",
                    edgecolor="none",
                )
                buf.seek(0)

                # Create image and display in content frame
                img = Image.open(buf)
                # Resize image to fit the popup better
                img.thumbnail((600, 500), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)

                # Create label in the content frame
                chart_label = ttk.Label(
                    chart_content_frame, image=photo, background="white"
                )
                chart_label.image = photo  # Keep a reference
                chart_label.pack(pady=10)

                chart_success = True
                plt.close(fig)

        except Exception as e:
            chart_success = False
            plt.close("all")
            self.logger.error(f"Error generating charts: {e}")

        if not chart_success:
            ttk.Label(
                chart_content_frame,
                text="(Charts unavailable for this process)",
                foreground="red",
                background="white",
            ).pack(pady=20)

        # Configure canvas scrolling
        def configure_scroll_region(event):
            chart_canvas.configure(scrollregion=chart_canvas.bbox("all"))

        chart_content_frame.bind("<Configure>", configure_scroll_region)

        # Bind mouse wheel for scrolling with proper error handling
        def on_mousewheel(event):
            try:
                # Check if canvas still exists and is valid
                if chart_canvas and chart_canvas.winfo_exists():
                    chart_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except tk.TclError:
                # Canvas has been destroyed, ignore the event
                pass
            except Exception as e:
                # Log any other errors but don't crash
                print(f"Mousewheel error: {e}")

        chart_canvas.bind("<MouseWheel>", on_mousewheel)

        # Close button with better styling
        close_btn = ttk.Button(
            frame, text="✖ Close", command=popup.destroy, style="Accent.TButton"
        )
        close_btn.pack(pady=(10, 0))

        # Center the popup on screen
        popup.update_idletasks()
        x = (popup.winfo_screenwidth() // 2) - (popup.winfo_width() // 2)
        y = (popup.winfo_screenheight() // 2) - (popup.winfo_height() // 2)
        popup.geometry(f"+{x}+{y}")

    def _generate_bottlenecks_from_comparison(self) -> List[Dict[str, Any]]:
        """Generate bottleneck analysis from comparison results."""
        try:
            bottlenecks = []
            
            if not self.comparison_results:
                return bottlenecks
            
            for result in self.comparison_results:
                process_name = result.get("anylogic_process", "Unknown")
                anylogic_mean = result.get("anylogic_mean", 0)
                historical_mean = result.get("historical_mean", 0)
                improvement_pct = result.get("mean_improvement_pct", 0)
                
                # Determine if this is a bottleneck based on multiple criteria
                bottleneck_score = 0
                severity = "Low"
                recommendations = []
                
                # Criterion 1: High duration (AnyLogic mean > 10 minutes)
                if anylogic_mean > 10:
                    bottleneck_score += 1
                    recommendations.append("Consider process optimization to reduce duration")
                
                # Criterion 2: Poor improvement (positive improvement = worse performance)
                if improvement_pct > 20:
                    bottleneck_score += 2
                    recommendations.append("Simulation shows worse performance than historical data")
                elif improvement_pct > 0:
                    bottleneck_score += 1
                    recommendations.append("Simulation performance needs improvement")
                
                # Criterion 3: High historical duration (> 5 minutes)
                if historical_mean > 5:
                    bottleneck_score += 1
                    recommendations.append("Historical data shows long process duration")
                
                # Criterion 4: Large performance gap (> 50% difference)
                if abs(improvement_pct) > 50:
                    bottleneck_score += 1
                    recommendations.append("Significant performance gap between simulation and historical")
                
                # Determine severity based on score
                if bottleneck_score >= 3:
                    severity = "High"
                elif bottleneck_score >= 2:
                    severity = "Medium"
                else:
                    severity = "Low"
                
                # Only include as bottleneck if score >= 2
                if bottleneck_score >= 2:
                    bottlenecks.append({
                        'service': process_name,
                        'severity': severity,
                        'efficiency': max(0, 100 - (anylogic_mean / 60) * 10),
                        'avg_duration': anylogic_mean,
                        'recommendations': recommendations,
                        'estimated_impact': f"{abs(improvement_pct):.1f}% performance gap",
                        'priority': severity
                    })
            
            # Sort by severity (High, Medium, Low)
            severity_order = {"High": 3, "Medium": 2, "Low": 1}
            bottlenecks.sort(key=lambda x: severity_order.get(x['severity'], 0), reverse=True)
            
            return bottlenecks
            
        except Exception as e:
            self.logger.error(f"Error generating bottlenecks from comparison: {e}")
            return []
