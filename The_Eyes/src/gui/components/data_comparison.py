"""
Data Comparison Component for the Clinic Data Visualizer.

This component provides functionality to compare the currently loaded
clinic data with a reference dataset from CSV or Excel files.
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import os

from app.utils.logger import get_logger
from app.core.data_loader import DataLoader
from app.core.metrics_calculator import MetricsCalculator
from app.core.statistical_analysis_engine import (
    StatisticalAnalysisEngine,
    StatisticalTestResult,
)
from app.core.data_quality_assessment import (
    DataQualityAssessment,
    QualityAssessmentReport,
)
from app.gui.dialogs.progress_dialog import (
    show_progress,
    close_progress,
    update_progress,
    
)
from app.gui.components.scrollable_panel import (
    create_simple_scrollable_frame,
)

# Configure logging
logger = get_logger(__name__)


class DataComparisonComponent:
    """Component for comparing clinic data with reference datasets."""

    def __init__(self, parent, main_data_loader=None, colors=None):
        """Initialize the data comparison component."""
        self.parent = parent
        self.main_data_loader = main_data_loader
        self.colors = colors or self._default_colors()

        # Initialize reference data components
        self.reference_data_loader = DataLoader()
        self.metrics_calculator = MetricsCalculator()

        # Initialize enhanced analysis engines
        self.statistical_engine = StatisticalAnalysisEngine(alpha=0.05)
        self.quality_assessment = DataQualityAssessment()

        # State variables
        self.reference_file_path = None
        self.comparison_results = None

        # Initialize logger
        self.logger = get_logger(__name__)

        self.logger.info("DataComparisonComponent __init__ started")

        # Setup UI
        self._setup_ui()

        self.logger.info("DataComparisonComponent __init__ completed")

    def _default_colors(self):
        """Default color scheme if none provided."""
        return {
            "primary": "#2563eb",
            "secondary": "#64748b",
            "success": "#059669",
            "warning": "#d97706",
            "error": "#dc2626",
            "background": "#ffffff",
            "card": "#f8fafc",
            "text": "#1e293b",
            "border": "#e2e8f0",
        }

    def _setup_ui(self):
        """Setup the user interface for data comparison."""
        try:
            # Main frame - use basic style to avoid style issues
            self.main_frame = ttk.Frame(self.parent, padding=(20, 15))
            self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # Reference file loading section
            self._setup_reference_loading_section()

            # Comparison controls section
            self._setup_comparison_controls()

            # Results display section
            self._setup_results_display()

            self.logger.info("DataComparisonComponent UI setup completed successfully")

        except Exception as e:
            self.logger.error(f"Error setting up DataComparisonComponent UI: {e}")
            # Create a simple error display
            error_label = ttk.Label(
                self.parent,
                text=f"Error loading Data Comparison Tool: {str(e)}",
                foreground=self.colors["error"],
                font=("Segoe UI", 12),
            )
            error_label.pack(expand=True, pady=50)

    def _setup_reference_loading_section(self):
        """Setup the reference file loading section."""
        # Reference file section
        ref_frame = ttk.LabelFrame(
            self.main_frame, text="Reference Dataset", padding=(15, 10)
        )
        ref_frame.pack(fill=tk.X, pady=(0, 15))

        # File selection row
        file_row = ttk.Frame(ref_frame)
        file_row.pack(fill=tk.X, pady=(0, 10))

        # Load reference file button
        load_ref_btn = ttk.Button(
            file_row, text="Load Reference File", command=self._load_reference_file
        )
        load_ref_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Reference file label
        self.reference_file_label = ttk.Label(
            file_row,
            text="No reference file loaded",
            foreground=self.colors["secondary"],
        )
        self.reference_file_label.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # File info section
        self.ref_info_frame = ttk.Frame(ref_frame)
        self.ref_info_frame.pack(fill=tk.X, pady=(5, 0))

    def _setup_comparison_controls(self):
        """Setup comparison controls and options."""
        controls_frame = ttk.LabelFrame(
            self.main_frame, text="Comparison Options", padding=(15, 10)
        )
        controls_frame.pack(fill=tk.X, pady=(0, 15))

        # Comparison type selection
        type_frame = ttk.Frame(controls_frame)
        type_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(type_frame, text="Comparison Type:").pack(side=tk.LEFT, padx=(0, 10))

        self.comparison_type_var = tk.StringVar(value="basic_metrics")
        comparison_types = [
            ("Basic Metrics", "basic_metrics"),
            ("Service Distribution", "service_distribution"),
            ("Hourly Patterns", "hourly_patterns"),
            ("Patient Behavior", "patient_behavior"),
            ("Monthly Trends", "monthly_trends"),
            ("Service Flow Analysis", "service_flow_analysis"),
            ("Location Performance", "location_performance"),
            ("Action Analysis", "action_analysis"),
        ]

        for text, value in comparison_types:
            rb = ttk.Radiobutton(
                type_frame, text=text, variable=self.comparison_type_var, value=value
            )
            rb.pack(side=tk.LEFT, padx=(0, 15))

        # Action buttons
        action_frame = ttk.Frame(controls_frame)
        action_frame.pack(fill=tk.X, pady=(10, 0))

        # Compare button
        self.compare_btn = ttk.Button(
            action_frame,
            text="Run Comparison",
            command=self._run_comparison,
            state="disabled",
        )
        self.compare_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Export button
        self.export_btn = ttk.Button(
            action_frame,
            text="Export Results",
            command=self._export_comparison,
            state="disabled",
        )
        self.export_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Clear button
        clear_btn = ttk.Button(
            action_frame, text="Clear Results", command=self._clear_results
        )
        clear_btn.pack(side=tk.LEFT)

    def _setup_results_display(self):
        """Setup the results display area."""
        results_frame = ttk.LabelFrame(
            self.main_frame, text="Comparison Results", padding=(10, 10)
        )
        results_frame.pack(fill=tk.BOTH, expand=True)

        # Create notebook for tabbed results
        self.results_notebook = ttk.Notebook(results_frame)
        self.results_notebook.pack(fill=tk.BOTH, expand=True)

        # Create scrollable tabs
        self.summary_frame = create_simple_scrollable_frame(
            self.results_notebook, self.colors
        )
        self.viz_frame = create_simple_scrollable_frame(
            self.results_notebook, self.colors
        )

        # Add tabs to notebook
        self.results_notebook.add(self.summary_frame, text="Summary")
        self.results_notebook.add(self.viz_frame, text="Visualization")

        # Initial placeholder
        self._show_placeholder()

    def _show_placeholder(self):
        """Show placeholder text when no comparison has been run."""
        for frame in [self.summary_frame, self.viz_frame]:
            # Clear existing widgets
            for widget in frame.winfo_children():
                widget.destroy()

            # Create and show placeholder
            placeholder = ttk.Label(
                frame,
                text="📊 No comparison results available\nSelect a reference file and run comparison to see results",
                font=("Segoe UI", 11),
                foreground=self.colors["text_secondary"],
                justify=tk.CENTER,
                anchor=tk.CENTER,
            )
            placeholder.pack(expand=True, fill=tk.BOTH)

    def _load_reference_file(self):
        """Load reference file for comparison."""

        # File dialog for selecting reference file
        file_path = filedialog.askopenfilename(
            title="Select Reference File",
            filetypes=[
                ("Excel files", "*.xlsx *.xls"),
                ("CSV files", "*.csv"),
                ("All supported", "*.xlsx *.xls *.csv"),
            ],
        )

        if not file_path:
            return

        # Fix: Run the data loading in a background thread to keep the progress dialog responsive.
        import threading

        def load_reference_file_bg():
            try:
                # Update progress to show file reading
                update_progress(0.1, "Reading file structure...")

                # Load the reference data
                success, message = self.reference_data_loader.load_data(file_path)

                if success:
                    # Update progress to show data processing
                    update_progress(0.6, "Processing data...")

                    self.reference_file_path = file_path
                    filename = os.path.basename(file_path)

                    # Update progress to show interface updates
                    update_progress(0.8, "Updating interface...")

                    # UI updates must be done in the main thread
                    def update_ui():
                        self.reference_file_label.config(
                            text=f"Loaded: {filename}", foreground=self.colors["success"]
                        )
                        self._display_reference_info()
                        if self.main_data_loader and self.main_data_loader.has_data():
                            self.compare_btn.config(state="normal")
                        update_progress(1.0, "Reference file loaded successfully! ✅")
                        self.logger.info(f"Reference file loaded successfully: {filename}")

                    self.parent.after(0, update_ui)
                else:
                    # Show error in progress dialog
                    update_progress(1.0, f"Error: {message}")
                    def show_error():
                        messagebox.showerror(
                            "Error", f"Failed to load reference file:\n{message}"
                        )
                    self.parent.after(0, show_error)
            except Exception as e:
                self.logger.error(f"Error loading reference file: {e}")
                def show_error():
                    messagebox.showerror("Error", f"Error loading reference file:\n{str(e)}")
                self.parent.after(0, show_error)
            finally:
                # Close progress dialog (in main thread)
                self.parent.after(0, close_progress)

        try:
            # Show progress dialog for loading reference data
            show_progress(
                self.parent,
                title="Loading Reference Data 📊",
                message="Initializing file loading...",
                can_cancel=True,
            )
            # Start the loading in a background thread
            threading.Thread(target=load_reference_file_bg, daemon=True).start()
        except Exception as e:
            self.logger.error(f"Error loading reference file: {e}")
            messagebox.showerror("Error", f"Error loading reference file:\n{str(e)}")

    def _display_reference_info(self):
        """Display information about the loaded reference file."""
        # Clear existing info
        for widget in self.ref_info_frame.winfo_children():
            widget.destroy()

        if not self.reference_data_loader.has_data():
            return

        ref_data = self.reference_data_loader.get_data()

        # Create info display
        info_text = ttk.Label(
            self.ref_info_frame,
            text=f"Records: {len(ref_data):,} | Columns: {len(ref_data.columns)} | "
            f"Date Range: {self._get_date_range(ref_data)}",
            font=("Segoe UI", 9),
            foreground=self.colors["text"],
        )
        info_text.pack(anchor=tk.W)

    def _get_date_range(self, data):
        """Get date range from dataset."""
        try:
            if "Service Date" in data.columns:
                dates = self._parse_dates_flexible(data["Service Date"])
                if dates is not None:
                    dates = dates.dropna()
                    if len(dates) > 0:
                        return f"{dates.min().strftime('%d/%m/%Y')} - {dates.max().strftime('%d/%m/%Y')}"

                # Log the first few date values for debugging
                sample_dates = data["Service Date"].dropna().head(5).tolist()
                self.logger.warning(
                    f"Could not parse dates. Sample values: {sample_dates}"
                )
                return "Unknown (date parsing failed)"
            return "Unknown (no Service Date column)"
        except Exception as e:
            self.logger.error(f"Error getting date range: {e}")
            return "Unknown (error)"

    def _parse_dates_flexible(self, date_series):
        """Parse dates using multiple formats to handle different Excel date formats."""
        try:
            # Try multiple date formats to handle different Excel date formats
            date_formats = [
                "%d/%m/%Y",  # DD/MM/YYYY
                "%Y-%m-%d",  # YYYY-MM-DD
                "%m/%d/%Y",  # MM/DD/YYYY
                "%d-%m-%Y",  # DD-MM-YYYY
                "%Y/%m/%d",  # YYYY/MM/DD
            ]

            for fmt in date_formats:
                try:
                    dates = pd.to_datetime(date_series, format=fmt, errors="coerce")
                    # Check if we got valid dates
                    if dates.notna().sum() > 0:
                        return dates
                except:
                    continue

            # If no specific format worked, try pandas' automatic parsing
            dates = pd.to_datetime(date_series, errors="coerce")
            if dates.notna().sum() > 0:
                return dates

            # If still no success, log sample values for debugging
            sample_dates = date_series.dropna().head(5).tolist()
            self.logger.warning(f"Could not parse dates. Sample values: {sample_dates}")
            return None

        except Exception as e:
            self.logger.error(f"Error parsing dates: {e}")
            return None

    def _run_comparison(self):
        """Run the data comparison based on selected type."""
        if not self.main_data_loader or not self.main_data_loader.has_data():
            messagebox.showwarning("Warning", "No main dataset loaded for comparison")
            return

        if not self.reference_data_loader.has_data():
            messagebox.showwarning(
                "Warning", "No reference dataset loaded for comparison"
            )
            return

        try:
            # Show progress dialog
            show_progress(
                self.parent,
                title="Running Data Comparison 📊",
                message="Initializing comparison...",
                can_cancel=True,
            )

            # Get comparison type
            comparison_type = self.comparison_type_var.get()

            # Load main dataset
            update_progress(0.1, "Loading main dataset...")
            main_data = self.main_data_loader.get_data()

            # Load reference dataset
            update_progress(0.2, "Loading reference dataset...")
            ref_data = self.reference_data_loader.get_data()

            # Generate summaries for comparison
            update_progress(0.3, "Generating main dataset summary...")
            main_summary = self.metrics_calculator.generate_comprehensive_summary(
                main_data
            )

            update_progress(0.4, "Generating reference dataset summary...")
            ref_summary = self.metrics_calculator.generate_comprehensive_summary(
                ref_data
            )

            # Run comparison based on type
            update_progress(0.5, f"Running {comparison_type} comparison...")
            if comparison_type == "basic_metrics":
                self.comparison_results = self._compare_basic_metrics_with_summaries(
                    main_summary, ref_summary
                )
            elif comparison_type == "service_distribution":
                self.comparison_results = self._compare_service_distribution(
                    main_data, ref_data
                )
            elif comparison_type == "hourly_patterns":
                self.comparison_results = self._compare_hourly_patterns(
                    main_data, ref_data
                )
            elif comparison_type == "patient_behavior":
                self.comparison_results = self._compare_patient_behavior(
                    main_data, ref_data
                )
            elif comparison_type == "monthly_trends":
                self.comparison_results = self._compare_monthly_trends(
                    main_data, ref_data
                )
            elif comparison_type == "service_flow_analysis":
                self.comparison_results = self._compare_service_flow(
                    main_data, ref_data
                )
            elif comparison_type == "location_performance":
                self.comparison_results = self._compare_location_performance(
                    main_data, ref_data
                )
            elif comparison_type == "action_analysis":
                self.comparison_results = self._compare_action_analysis(
                    main_data, ref_data
                )

            # Process and display results
            update_progress(0.8, "Processing comparison results...")
            self._display_comparison_results()

            # Enable export button
            self.export_btn.config(state="normal")

            update_progress(1.0, "Comparison completed successfully! ✅")

            self.logger.info(f"Comparison completed: {comparison_type}")

        except Exception as e:
            self.logger.error(f"Error running comparison: {e}")
            # Show error in progress dialog
            update_progress(1.0, f"Error: {str(e)}")
            messagebox.showerror("Error", f"Error running comparison:\n{str(e)}")
        finally:
            # Close progress dialog
            close_progress()

    def _compare_basic_metrics_with_summaries(self, main_summary, ref_summary):
        """Compare basic metrics between datasets using pre-generated summaries with statistical analysis."""
        comparison = {
            "type": "basic_metrics",
            "main_summary": main_summary,
            "ref_summary": ref_summary,
            "differences": {},
            "statistical_tests": {},
            "data_quality": {},
        }

        # Calculate key differences
        if "basic_stats" in main_summary and "basic_stats" in ref_summary:
            main_stats = main_summary["basic_stats"]
            ref_stats = ref_summary["basic_stats"]

            comparison["differences"]["total_records"] = {
                "main": main_stats.get("total_records", 0),
                "reference": ref_stats.get("total_records", 0),
                "diff": main_stats.get("total_records", 0)
                - ref_stats.get("total_records", 0),
                "percent_change": self._calculate_percent_change(
                    ref_stats.get("total_records", 0),
                    main_stats.get("total_records", 0),
                ),
            }

            comparison["differences"]["unique_patients"] = {
                "main": main_stats.get("unique_patients", 0),
                "reference": ref_stats.get("unique_patients", 0),
                "diff": main_stats.get("unique_patients", 0)
                - ref_stats.get("unique_patients", 0),
                "percent_change": self._calculate_percent_change(
                    ref_stats.get("unique_patients", 0),
                    main_stats.get("unique_patients", 0),
                ),
            }

        return comparison

    def _compare_basic_metrics(self, main_data, ref_data):
        """Compare basic metrics between datasets with enhanced statistical analysis."""
        try:
            self.logger.info(
                "Starting enhanced basic metrics comparison with statistical analysis"
            )

            # Generate comprehensive summaries
            main_summary = self.metrics_calculator.generate_comprehensive_summary(
                main_data
            )
            ref_summary = self.metrics_calculator.generate_comprehensive_summary(
                ref_data
            )

            # Initialize comparison structure
            comparison = {
                "type": "basic_metrics",
                "main_summary": main_summary,
                "ref_summary": ref_summary,
                "differences": {},
                "statistical_tests": {},
                "data_quality": {},
                "effect_sizes": {},
                "confidence_intervals": {},
                "recommendations": [],
            }

            # Perform data quality assessment
            self.logger.info("Performing data quality assessment")
            main_quality = self.quality_assessment.assess_data_quality(main_data)
            ref_quality = self.quality_assessment.assess_data_quality(ref_data)

            comparison["data_quality"] = {
                "main_dataset": {
                    "overall_score": main_quality.overall_score,
                    "grade": main_quality.get_quality_grade(),
                    "dimension_scores": {
                        dim.value: score
                        for dim, score in main_quality.dimension_scores.items()
                    },
                    "recommendations": main_quality.recommendations[
                        :5
                    ],  # Top 5 recommendations
                },
                "reference_dataset": {
                    "overall_score": ref_quality.overall_score,
                    "grade": ref_quality.get_quality_grade(),
                    "dimension_scores": {
                        dim.value: score
                        for dim, score in ref_quality.dimension_scores.items()
                    },
                    "recommendations": ref_quality.recommendations[
                        :5
                    ],  # Top 5 recommendations
                },
            }

            # Compare numerical columns with statistical tests
            numerical_columns = main_data.select_dtypes(include=[np.number]).columns
            common_numerical = [
                col for col in numerical_columns if col in ref_data.columns
            ]

            for column in common_numerical:
                try:
                    # Extract column data
                    main_values = main_data[column].dropna()
                    ref_values = ref_data[column].dropna()

                    if len(main_values) > 0 and len(ref_values) > 0:
                        # Perform statistical significance test
                        stat_result = (
                            self.statistical_engine.perform_significance_tests(
                                main_values, ref_values, test_type="auto"
                            )
                        )

                        # Calculate effect size
                        effect_size = self.statistical_engine.calculate_effect_size(
                            main_values, ref_values, method="cohens_d"
                        )

                        # Calculate confidence intervals
                        main_ci = self.statistical_engine.generate_confidence_intervals(
                            main_values
                        )
                        ref_ci = self.statistical_engine.generate_confidence_intervals(
                            ref_values
                        )

                        # Store results
                        comparison["statistical_tests"][column] = {
                            "test_name": stat_result.test_name,
                            "statistic": stat_result.statistic,
                            "p_value": stat_result.p_value,
                            "significant": stat_result.significant,
                            "interpretation": stat_result.interpretation,
                            "sample_sizes": {
                                "main": len(main_values),
                                "reference": len(ref_values),
                            },
                        }

                        comparison["effect_sizes"][column] = {
                            "cohens_d": effect_size,
                            "interpretation": self._interpret_effect_size(effect_size),
                        }

                        comparison["confidence_intervals"][column] = {
                            "main": {"lower": main_ci[0], "upper": main_ci[1]},
                            "reference": {"lower": ref_ci[0], "upper": ref_ci[1]},
                        }

                except Exception as e:
                    self.logger.error(
                        f"Error in statistical analysis for column {column}: {str(e)}"
                    )
                    continue

            # Calculate basic differences (existing logic)
            if "basic_stats" in main_summary and "basic_stats" in ref_summary:
                main_stats = main_summary["basic_stats"]
                ref_stats = ref_summary["basic_stats"]

                comparison["differences"]["total_records"] = {
                    "main": main_stats.get("total_records", 0),
                    "reference": ref_stats.get("total_records", 0),
                    "diff": main_stats.get("total_records", 0)
                    - ref_stats.get("total_records", 0),
                    "percent_change": self._calculate_percent_change(
                        ref_stats.get("total_records", 0),
                        main_stats.get("total_records", 0),
                    ),
                }

                comparison["differences"]["unique_patients"] = {
                    "main": main_stats.get("unique_patients", 0),
                    "reference": ref_stats.get("unique_patients", 0),
                    "diff": main_stats.get("unique_patients", 0)
                    - ref_stats.get("unique_patients", 0),
                    "percent_change": self._calculate_percent_change(
                        ref_stats.get("unique_patients", 0),
                        main_stats.get("unique_patients", 0),
                    ),
                }

            # Generate recommendations based on analysis
            comparison["recommendations"] = self._generate_comparison_recommendations(
                comparison
            )

            self.logger.info("Enhanced basic metrics comparison completed successfully")
            return comparison

        except Exception as e:
            self.logger.error(f"Error in enhanced basic metrics comparison: {str(e)}")
            # Fall back to legacy method
            return self._compare_basic_metrics_with_summaries(main_summary, ref_summary)

    def _compare_service_distribution(self, main_data, ref_data):
        """Compare service type distribution between datasets."""
        comparison = {
            "type": "service_distribution",
            "main_data": {},
            "ref_data": {},
            "differences": {},
        }

        # Analyze service types in main dataset
        if "Service Type" in main_data.columns:
            main_service_counts = main_data["Service Type"].value_counts()
            main_total = len(main_data)
            comparison["main_data"] = {
                "counts": main_service_counts.to_dict(),
                "percentages": (main_service_counts / main_total * 100).to_dict(),
                "total": main_total,
            }

        # Analyze service types in reference dataset
        if "Service Type" in ref_data.columns:
            ref_service_counts = ref_data["Service Type"].value_counts()
            ref_total = len(ref_data)
            comparison["ref_data"] = {
                "counts": ref_service_counts.to_dict(),
                "percentages": (ref_service_counts / ref_total * 100).to_dict(),
                "total": ref_total,
            }

        # Calculate differences
        all_services = set(comparison["main_data"].get("counts", {}).keys()) | set(
            comparison["ref_data"].get("counts", {}).keys()
        )

        for service in all_services:
            main_count = comparison["main_data"].get("counts", {}).get(service, 0)
            ref_count = comparison["ref_data"].get("counts", {}).get(service, 0)
            main_pct = comparison["main_data"].get("percentages", {}).get(service, 0)
            ref_pct = comparison["ref_data"].get("percentages", {}).get(service, 0)

            comparison["differences"][service] = {
                "main_count": main_count,
                "ref_count": ref_count,
                "main_percentage": main_pct,
                "ref_percentage": ref_pct,
                "count_diff": main_count - ref_count,
                "percentage_diff": main_pct - ref_pct,
                "percent_change": self._calculate_percent_change(ref_count, main_count),
            }

        return comparison

    def _compare_hourly_patterns(self, main_data, ref_data):
        """Compare hourly activity patterns between datasets."""
        comparison = {
            "type": "hourly_patterns",
            "main_data": {},
            "ref_data": {},
            "differences": {},
        }

        # Analyze hourly patterns in main dataset
        if "Action Timestamp (HH:MM)" in main_data.columns:
            main_data_copy = main_data.copy()
            main_data_copy["Hour"] = pd.to_datetime(
                main_data_copy["Action Timestamp (HH:MM)"],
                format="%H:%M",
                errors="coerce",
            ).dt.hour
            main_hourly_counts = main_data_copy["Hour"].value_counts().sort_index()
            comparison["main_data"] = {
                "hourly_counts": main_hourly_counts.to_dict(),
                "peak_hour": (
                    main_hourly_counts.idxmax()
                    if not main_hourly_counts.empty
                    else None
                ),
                "peak_count": (
                    main_hourly_counts.max() if not main_hourly_counts.empty else 0
                ),
            }

        # Analyze hourly patterns in reference dataset
        if "Action Timestamp (HH:MM)" in ref_data.columns:
            ref_data_copy = ref_data.copy()
            ref_data_copy["Hour"] = pd.to_datetime(
                ref_data_copy["Action Timestamp (HH:MM)"],
                format="%H:%M",
                errors="coerce",
            ).dt.hour
            ref_hourly_counts = ref_data_copy["Hour"].value_counts().sort_index()
            comparison["ref_data"] = {
                "hourly_counts": ref_hourly_counts.to_dict(),
                "peak_hour": (
                    ref_hourly_counts.idxmax() if not ref_hourly_counts.empty else None
                ),
                "peak_count": (
                    ref_hourly_counts.max() if not ref_hourly_counts.empty else 0
                ),
            }

        # Calculate differences for each hour
        all_hours = set(comparison["main_data"].get("hourly_counts", {}).keys()) | set(
            comparison["ref_data"].get("hourly_counts", {}).keys()
        )

        for hour in sorted(all_hours):
            main_count = comparison["main_data"].get("hourly_counts", {}).get(hour, 0)
            ref_count = comparison["ref_data"].get("hourly_counts", {}).get(hour, 0)

            comparison["differences"][hour] = {
                "main_count": main_count,
                "ref_count": ref_count,
                "count_diff": main_count - ref_count,
                "percent_change": self._calculate_percent_change(ref_count, main_count),
            }

        return comparison

    def _compare_patient_behavior(self, main_data, ref_data):
        """Compare patient behavior patterns between datasets."""
        comparison = {
            "type": "patient_behavior",
            "main_data": {},
            "ref_data": {},
            "differences": {},
        }

        # Analyze patient behavior in main dataset
        if "Queue Number" in main_data.columns:
            main_patient_visits = main_data["Queue Number"].value_counts()
            comparison["main_data"] = {
                "total_patients": len(main_patient_visits),
                "avg_visits_per_patient": main_patient_visits.mean(),
                "max_visits": main_patient_visits.max(),
                "min_visits": main_patient_visits.min(),
                "visit_distribution": {
                    "1 visit": (main_patient_visits == 1).sum(),
                    "2-5 visits": (
                        (main_patient_visits >= 2) & (main_patient_visits <= 5)
                    ).sum(),
                    "6+ visits": (main_patient_visits >= 6).sum(),
                },
            }

        # Analyze patient behavior in reference dataset
        if "Queue Number" in ref_data.columns:
            ref_patient_visits = ref_data["Queue Number"].value_counts()
            comparison["ref_data"] = {
                "total_patients": len(ref_patient_visits),
                "avg_visits_per_patient": ref_patient_visits.mean(),
                "max_visits": ref_patient_visits.max(),
                "min_visits": ref_patient_visits.min(),
                "visit_distribution": {
                    "1 visit": (ref_patient_visits == 1).sum(),
                    "2-5 visits": (
                        (ref_patient_visits >= 2) & (ref_patient_visits <= 5)
                    ).sum(),
                    "6+ visits": (ref_patient_visits >= 6).sum(),
                },
            }

        # Calculate differences
        comparison["differences"] = {
            "total_patients": {
                "main": comparison["main_data"].get("total_patients", 0),
                "reference": comparison["ref_data"].get("total_patients", 0),
                "diff": comparison["main_data"].get("total_patients", 0)
                - comparison["ref_data"].get("total_patients", 0),
                "percent_change": self._calculate_percent_change(
                    comparison["ref_data"].get("total_patients", 0),
                    comparison["main_data"].get("total_patients", 0),
                ),
            },
            "avg_visits_per_patient": {
                "main": comparison["main_data"].get("avg_visits_per_patient", 0),
                "reference": comparison["ref_data"].get("avg_visits_per_patient", 0),
                "diff": comparison["main_data"].get("avg_visits_per_patient", 0)
                - comparison["ref_data"].get("avg_visits_per_patient", 0),
                "percent_change": self._calculate_percent_change(
                    comparison["ref_data"].get("avg_visits_per_patient", 0),
                    comparison["main_data"].get("avg_visits_per_patient", 0),
                ),
            },
        }

        return comparison

    def _compare_monthly_trends(self, main_data, ref_data):
        """Compare monthly trends between datasets."""
        comparison = {
            "type": "monthly_trends",
            "main_data": {},
            "ref_data": {},
            "differences": {},
        }

        # Analyze monthly trends in main dataset
        if "Service Date" in main_data.columns:
            main_data_copy = main_data.copy()
            # Use flexible date parsing
            main_dates = self._parse_dates_flexible(main_data_copy["Service Date"])
            if main_dates is not None:
                main_data_copy["Month"] = main_dates.dt.to_period("M")
                main_monthly_counts = (
                    main_data_copy["Month"].value_counts().sort_index()
                )
                comparison["main_data"] = {
                    "monthly_counts": {
                        str(month): count
                        for month, count in main_monthly_counts.items()
                    },
                    "total_months": len(main_monthly_counts),
                    "avg_monthly_volume": (
                        main_monthly_counts.mean()
                        if not main_monthly_counts.empty
                        else 0
                    ),
                }

        # Analyze monthly trends in reference dataset
        if "Service Date" in ref_data.columns:
            ref_data_copy = ref_data.copy()
            # Use flexible date parsing
            ref_dates = self._parse_dates_flexible(ref_data_copy["Service Date"])
            if ref_dates is not None:
                ref_data_copy["Month"] = ref_dates.dt.to_period("M")
                ref_monthly_counts = ref_data_copy["Month"].value_counts().sort_index()
                comparison["ref_data"] = {
                    "monthly_counts": {
                        str(month): count for month, count in ref_monthly_counts.items()
                    },
                    "total_months": len(ref_monthly_counts),
                    "avg_monthly_volume": (
                        ref_monthly_counts.mean() if not ref_monthly_counts.empty else 0
                    ),
                }

        # Calculate differences for each month
        all_months = set(
            comparison["main_data"].get("monthly_counts", {}).keys()
        ) | set(comparison["ref_data"].get("monthly_counts", {}).keys())

        for month in sorted(all_months):
            main_count = comparison["main_data"].get("monthly_counts", {}).get(month, 0)
            ref_count = comparison["ref_data"].get("monthly_counts", {}).get(month, 0)

            comparison["differences"][month] = {
                "main_count": main_count,
                "ref_count": ref_count,
                "count_diff": main_count - ref_count,
                "percent_change": self._calculate_percent_change(ref_count, main_count),
            }

        return comparison

    def _compare_service_flow(self, main_data, ref_data):
        """Compare service flow patterns between datasets."""
        comparison = {
            "type": "service_flow_analysis",
            "main_data": {},
            "ref_data": {},
            "differences": {},
        }

        # Analyze service flow in main dataset
        if "Service Type" in main_data.columns and "Action" in main_data.columns:
            main_flow = (
                main_data.groupby(["Service Type", "Action"])
                .size()
                .unstack(fill_value=0)
            )
            comparison["main_data"] = {
                "service_flow_matrix": main_flow.to_dict(),
                "total_actions": len(main_data),
                "unique_service_types": main_data["Service Type"].nunique(),
                "unique_actions": main_data["Action"].nunique(),
            }

        # Analyze service flow in reference dataset
        if "Service Type" in ref_data.columns and "Action" in ref_data.columns:
            ref_flow = (
                ref_data.groupby(["Service Type", "Action"])
                .size()
                .unstack(fill_value=0)
            )
            comparison["ref_data"] = {
                "service_flow_matrix": ref_flow.to_dict(),
                "total_actions": len(ref_data),
                "unique_service_types": ref_data["Service Type"].nunique(),
                "unique_actions": ref_data["Action"].nunique(),
            }

        # Calculate differences
        comparison["differences"] = {
            "total_actions": {
                "main": comparison["main_data"].get("total_actions", 0),
                "reference": comparison["ref_data"].get("total_actions", 0),
                "diff": comparison["main_data"].get("total_actions", 0)
                - comparison["ref_data"].get("total_actions", 0),
                "percent_change": self._calculate_percent_change(
                    comparison["ref_data"].get("total_actions", 0),
                    comparison["main_data"].get("total_actions", 0),
                ),
            }
        }

        return comparison

    def _compare_location_performance(self, main_data, ref_data):
        """Compare location performance between datasets."""
        comparison = {
            "type": "location_performance",
            "main_data": {},
            "ref_data": {},
            "differences": {},
        }

        # Analyze location performance in main dataset
        if "Service Location" in main_data.columns:
            main_location_counts = main_data["Service Location"].value_counts()
            comparison["main_data"] = {
                "location_counts": main_location_counts.to_dict(),
                "total_locations": len(main_location_counts),
                "busiest_location": (
                    main_location_counts.index[0]
                    if not main_location_counts.empty
                    else None
                ),
                "busiest_location_count": (
                    main_location_counts.iloc[0]
                    if not main_location_counts.empty
                    else 0
                ),
            }

        # Analyze location performance in reference dataset
        if "Service Location" in ref_data.columns:
            ref_location_counts = ref_data["Service Location"].value_counts()
            comparison["ref_data"] = {
                "location_counts": ref_location_counts.to_dict(),
                "total_locations": len(ref_location_counts),
                "busiest_location": (
                    ref_location_counts.index[0]
                    if not ref_location_counts.empty
                    else None
                ),
                "busiest_location_count": (
                    ref_location_counts.iloc[0] if not ref_location_counts.empty else 0
                ),
            }

        # Calculate differences for each location
        all_locations = set(
            comparison["main_data"].get("location_counts", {}).keys()
        ) | set(comparison["ref_data"].get("location_counts", {}).keys())

        for location in all_locations:
            main_count = (
                comparison["main_data"].get("location_counts", {}).get(location, 0)
            )
            ref_count = (
                comparison["ref_data"].get("location_counts", {}).get(location, 0)
            )

            comparison["differences"][location] = {
                "main_count": main_count,
                "ref_count": ref_count,
                "count_diff": main_count - ref_count,
                "percent_change": self._calculate_percent_change(ref_count, main_count),
            }

        return comparison

    def _compare_action_analysis(self, main_data, ref_data):
        """Compare action patterns between datasets."""
        comparison = {
            "type": "action_analysis",
            "main_data": {},
            "ref_data": {},
            "differences": {},
        }

        # Analyze actions in main dataset
        if "Action" in main_data.columns:
            main_action_counts = main_data["Action"].value_counts()
            comparison["main_data"] = {
                "action_counts": main_action_counts.to_dict(),
                "total_actions": len(main_data),
                "unique_actions": len(main_action_counts),
                "most_common_action": (
                    main_action_counts.index[0]
                    if not main_action_counts.empty
                    else None
                ),
                "most_common_count": (
                    main_action_counts.iloc[0] if not main_action_counts.empty else 0
                ),
            }

        # Analyze actions in reference dataset
        if "Action" in ref_data.columns:
            ref_action_counts = ref_data["Action"].value_counts()
            comparison["ref_data"] = {
                "action_counts": ref_action_counts.to_dict(),
                "total_actions": len(ref_data),
                "unique_actions": len(ref_action_counts),
                "most_common_action": (
                    ref_action_counts.index[0] if not ref_action_counts.empty else None
                ),
                "most_common_count": (
                    ref_action_counts.iloc[0] if not ref_action_counts.empty else 0
                ),
            }

        # Calculate differences for each action
        all_actions = set(
            comparison["main_data"].get("action_counts", {}).keys()
        ) | set(comparison["ref_data"].get("action_counts", {}).keys())

        for action in all_actions:
            main_count = comparison["main_data"].get("action_counts", {}).get(action, 0)
            ref_count = comparison["ref_data"].get("action_counts", {}).get(action, 0)

            comparison["differences"][action] = {
                "main_count": main_count,
                "ref_count": ref_count,
                "count_diff": main_count - ref_count,
                "percent_change": self._calculate_percent_change(ref_count, main_count),
            }

        return comparison

    def _calculate_percent_change(self, old_value, new_value):
        """Calculate percentage change between two values."""
        if old_value == 0:
            return float("inf") if new_value > 0 else 0
        return ((new_value - old_value) / old_value) * 100

    def _interpret_effect_size(self, effect_size):
        """Interpret Cohen's d effect size."""
        if pd.isna(effect_size):
            return "Unable to calculate"

        abs_effect = abs(effect_size)

        if abs_effect < 0.2:
            magnitude = "negligible"
        elif abs_effect < 0.5:
            magnitude = "small"
        elif abs_effect < 0.8:
            magnitude = "medium"
        else:
            magnitude = "large"

        direction = "positive" if effect_size > 0 else "negative"

        return f"{magnitude} {direction} effect"

    def _generate_comparison_recommendations(self, comparison):
        """Generate actionable recommendations based on comparison results."""
        recommendations = []

        # Data quality recommendations
        if "data_quality" in comparison:
            main_score = (
                comparison["data_quality"]
                .get("main_dataset", {})
                .get("overall_score", 100)
            )
            ref_score = (
                comparison["data_quality"]
                .get("reference_dataset", {})
                .get("overall_score", 100)
            )

            if main_score < 70:
                recommendations.append(
                    "🚨 Main dataset has poor data quality - consider data cleaning"
                )
            if ref_score < 70:
                recommendations.append(
                    "🚨 Reference dataset has poor data quality - consider data cleaning"
                )

        # Statistical significance recommendations
        if "statistical_tests" in comparison:
            significant_tests = [
                col
                for col, test in comparison["statistical_tests"].items()
                if test.get("significant", False)
            ]

            if significant_tests:
                recommendations.append(
                    f"📊 Found statistically significant differences in: {', '.join(significant_tests)}"
                )

            # Effect size recommendations
            if "effect_sizes" in comparison:
                large_effects = [
                    col
                    for col, effect in comparison["effect_sizes"].items()
                    if "large" in effect.get("interpretation", "")
                ]

                if large_effects:
                    recommendations.append(
                        f"📈 Large effect sizes found in: {', '.join(large_effects)}"
                    )

        # Sample size recommendations
        if "statistical_tests" in comparison:
            small_samples = [
                col
                for col, test in comparison["statistical_tests"].items()
                if test.get("sample_sizes", {}).get("main", 0) < 30
                or test.get("sample_sizes", {}).get("reference", 0) < 30
            ]

            if small_samples:
                recommendations.append(
                    f"⚠️ Small sample sizes may affect reliability: {', '.join(small_samples)}"
                )

        return recommendations[:10]  # Limit to top 10 recommendations

    def _display_comparison_results(self):
        """Display the comparison results in the UI."""
        if not self.comparison_results:
            return

        # Clear existing results
        for frame in [self.summary_frame, self.viz_frame]:
            for widget in frame.winfo_children():
                widget.destroy()

        # Display based on comparison type
        comparison_type = self.comparison_results["type"]

        if comparison_type == "basic_metrics":
            self._display_basic_metrics_results()
        elif comparison_type == "service_distribution":
            self._display_service_distribution_results()
        elif comparison_type == "hourly_patterns":
            self._display_hourly_patterns_results()
        elif comparison_type == "patient_behavior":
            self._display_patient_behavior_results()
        elif comparison_type == "monthly_trends":
            self._display_monthly_trends_results()
        elif comparison_type == "service_flow_analysis":
            self._display_service_flow_results()
        elif comparison_type == "location_performance":
            self._display_location_performance_results()
        elif comparison_type == "action_analysis":
            self._display_action_analysis_results()
        else:
            # Generic display for unknown types
            self._display_generic_results()

    def _display_basic_metrics_results(self):
        """Display enhanced basic metrics comparison results with statistical analysis."""
        # Summary tab
        summary_text = tk.Text(self.summary_frame, wrap=tk.WORD, height=15)
        summary_scrollbar = ttk.Scrollbar(
            self.summary_frame, orient=tk.VERTICAL, command=summary_text.yview
        )
        summary_text.config(yscrollcommand=summary_scrollbar.set)

        summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Generate enhanced summary text
        summary_content = "ENHANCED BASIC METRICS COMPARISON SUMMARY\n"
        summary_content += "=" * 60 + "\n\n"

        # Basic differences
        differences = self.comparison_results.get("differences", {})
        if differences:
            summary_content += "📊 BASIC METRICS DIFFERENCES\n"
            summary_content += "-" * 30 + "\n"
            for metric, data in differences.items():
                summary_content += f"{metric.replace('_', ' ').title()}:\n"
                summary_content += f"  Main Dataset: {data['main']:,}\n"
                summary_content += f"  Reference Dataset: {data['reference']:,}\n"
                summary_content += f"  Difference: {data['diff']:+,}\n"
                if data["percent_change"] != float("inf"):
                    summary_content += (
                        f"  Percent Change: {data['percent_change']:+.1f}%\n"
                    )
                summary_content += "\n"

        # Data quality assessment
        data_quality = self.comparison_results.get("data_quality", {})
        if data_quality:
            summary_content += "🔍 DATA QUALITY ASSESSMENT\n"
            summary_content += "-" * 30 + "\n"

            main_quality = data_quality.get("main_dataset", {})
            ref_quality = data_quality.get("reference_dataset", {})

            summary_content += f"Main Dataset Quality: {main_quality.get('overall_score', 0):.1f}/100 ({main_quality.get('grade', 'N/A')})\n"
            summary_content += f"Reference Dataset Quality: {ref_quality.get('overall_score', 0):.1f}/100 ({ref_quality.get('grade', 'N/A')})\n\n"

        # Statistical tests
        statistical_tests = self.comparison_results.get("statistical_tests", {})
        if statistical_tests:
            summary_content += "📈 STATISTICAL SIGNIFICANCE TESTS\n"
            summary_content += "-" * 30 + "\n"

            for column, test in statistical_tests.items():
                summary_content += f"{column}:\n"
                summary_content += f"  Test: {test['test_name']}\n"
                summary_content += f"  P-value: {test['p_value']:.6f}\n"
                summary_content += (
                    f"  Significant: {'Yes' if test['significant'] else 'No'}\n"
                )
                summary_content += f"  Interpretation: {test['interpretation']}\n"
                summary_content += f"  Sample sizes: Main={test['sample_sizes']['main']}, Ref={test['sample_sizes']['reference']}\n"
                summary_content += "\n"

        # Effect sizes
        effect_sizes = self.comparison_results.get("effect_sizes", {})
        if effect_sizes:
            summary_content += "📏 EFFECT SIZES (Cohen's d)\n"
            summary_content += "-" * 30 + "\n"

            for column, effect in effect_sizes.items():
                summary_content += f"{column}:\n"
                summary_content += f"  Cohen's d: {effect['cohens_d']:.3f}\n"
                summary_content += f"  Interpretation: {effect['interpretation']}\n"
                summary_content += "\n"

        # Recommendations
        recommendations = self.comparison_results.get("recommendations", [])
        if recommendations:
            summary_content += "💡 RECOMMENDATIONS\n"
            summary_content += "-" * 30 + "\n"

            for i, rec in enumerate(recommendations, 1):
                summary_content += f"{i}. {rec}\n"
            summary_content += "\n"

        summary_text.insert(tk.END, summary_content)
        summary_text.config(state=tk.DISABLED)

        # Visualization tab - enhanced chart
        self._create_basic_metrics_chart()

    def _create_basic_metrics_chart(self):
        """Create a chart for basic metrics comparison using scrollable_panel.py utilities."""
        try:
            # Show progress dialog for chart creation
            show_progress(
                self.parent,
                title="Creating Visualization 📊",
                message="Preparing chart...",
                can_cancel=False,  # Chart creation is usually fast
            )

            try:
                # Create figure
                update_progress(0.2, "Creating chart figure...")
                fig = Figure(figsize=(10, 6))
                ax = fig.add_subplot(111)

                # Prepare data
                update_progress(0.4, "Preparing chart data...")
                differences = self.comparison_results.get("differences", {})
                metrics = list(differences.keys())
                main_values = [differences[m]["main"] for m in metrics]
                ref_values = [differences[m]["reference"] for m in metrics]

                # Create chart
                update_progress(0.6, "Drawing chart...")
                x = np.arange(len(metrics))
                width = 0.35

                bars1 = ax.bar(
                    x - width / 2,
                    main_values,
                    width,
                    label="Main Dataset",
                    color=self.colors["primary"],
                )
                bars2 = ax.bar(
                    x + width / 2,
                    ref_values,
                    width,
                    label="Reference Dataset",
                    color=self.colors["secondary"],
                )

                ax.set_xlabel("Metrics")
                ax.set_ylabel("Count")
                ax.set_title("Basic Metrics Comparison")
                ax.set_xticks(x)
                ax.set_xticklabels([m.replace("_", " ").title() for m in metrics])
                ax.legend()

                fig.tight_layout()

                # Display in viz frame using direct matplotlib embedding
                update_progress(0.8, "Rendering chart...")

                # Clear previous widgets in viz_frame
                for widget in self.viz_frame.winfo_children():
                    widget.destroy()

                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

                # Create a frame for the chart
                chart_frame = ttk.LabelFrame(
                    self.viz_frame, 
                    text="Basic Metrics Comparison", 
                    padding=(10, 5)
                )
                chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

                # Embed the matplotlib figure directly
                canvas_widget = FigureCanvasTkAgg(fig, chart_frame)
                canvas_widget.draw()
                canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)

                update_progress(1.0, "Chart created successfully! ✅")

            finally:
                # Close progress dialog
                close_progress()

        except Exception as e:
            self.logger.error(f"Error creating basic metrics chart: {e}")
            # Show error in progress dialog if it's still open
            try:
                update_progress(1.0, f"Error: {str(e)}")
            except:
                pass
            close_progress()

    def _create_service_distribution_chart(self):
        """Create a chart for service distribution comparison."""
        try:
            show_progress(
                self.parent,
                title="Creating Service Distribution Chart 📊",
                message="Preparing chart...",
                can_cancel=False,
            )

            try:
                update_progress(0.2, "Creating chart figure...")
                fig = Figure(figsize=(12, 8))
                ax = fig.add_subplot(111)

                update_progress(0.4, "Preparing chart data...")
                differences = self.comparison_results.get("differences", {})
                services = list(differences.keys())
                main_counts = [differences[s]["main_count"] for s in services]
                ref_counts = [differences[s]["ref_count"] for s in services]

                update_progress(0.6, "Drawing chart...")
                x = np.arange(len(services))
                width = 0.35

                bars1 = ax.bar(
                    x - width / 2,
                    main_counts,
                    width,
                    label="Main Dataset",
                    color=self.colors["primary"],
                )
                bars2 = ax.bar(
                    x + width / 2,
                    ref_counts,
                    width,
                    label="Reference Dataset",
                    color=self.colors["secondary"],
                )

                ax.set_xlabel("Service Types")
                ax.set_ylabel("Count")
                ax.set_title("Service Distribution Comparison")
                ax.set_xticks(x)
                ax.set_xticklabels(services, rotation=45, ha="right")
                ax.legend()

                fig.tight_layout()

                update_progress(0.8, "Rendering chart...")

                # Clear previous widgets in viz_frame
                for widget in self.viz_frame.winfo_children():
                    widget.destroy()

                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

                # Create a frame for the chart
                chart_frame = ttk.LabelFrame(
                    self.viz_frame, 
                    text="Service Distribution Comparison", 
                    padding=(10, 5)
                )
                chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

                # Embed the matplotlib figure directly
                canvas_widget = FigureCanvasTkAgg(fig, chart_frame)
                canvas_widget.draw()
                canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)

                update_progress(1.0, "Chart created successfully! ✅")

            finally:
                close_progress()

        except Exception as e:
            self.logger.error(f"Error creating service distribution chart: {e}")
            try:
                update_progress(1.0, f"Error: {str(e)}")
            except:
                pass
            close_progress()

    def _create_hourly_patterns_chart(self):
        """Create a chart for hourly patterns comparison."""
        try:
            show_progress(
                self.parent,
                title="Creating Hourly Patterns Chart 📊",
                message="Preparing chart...",
                can_cancel=False,
            )

            try:
                update_progress(0.2, "Creating chart figure...")
                fig = Figure(figsize=(12, 6))
                ax = fig.add_subplot(111)

                update_progress(0.4, "Preparing chart data...")
                differences = self.comparison_results.get("differences", {})
                hours = sorted(differences.keys())
                main_counts = [differences[h]["main_count"] for h in hours]
                ref_counts = [differences[h]["ref_count"] for h in hours]

                update_progress(0.6, "Drawing chart...")
                ax.plot(
                    hours,
                    main_counts,
                    "o-",
                    label="Main Dataset",
                    color=self.colors["primary"],
                    linewidth=2,
                    markersize=6,
                )
                ax.plot(
                    hours,
                    ref_counts,
                    "s-",
                    label="Reference Dataset",
                    color=self.colors["secondary"],
                    linewidth=2,
                    markersize=6,
                )

                ax.set_xlabel("Hour of Day")
                ax.set_ylabel("Number of Actions")
                ax.set_title("Hourly Activity Patterns Comparison")
                ax.set_xticks(hours)
                ax.legend()
                ax.grid(True, alpha=0.3)

                fig.tight_layout()

                update_progress(0.8, "Rendering chart...")

                # Clear previous widgets in viz_frame
                for widget in self.viz_frame.winfo_children():
                    widget.destroy()

                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

                # Create a frame for the chart
                chart_frame = ttk.LabelFrame(
                    self.viz_frame, 
                    text="Hourly Patterns Comparison", 
                    padding=(10, 5)
                )
                chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

                # Embed the matplotlib figure directly
                canvas_widget = FigureCanvasTkAgg(fig, chart_frame)
                canvas_widget.draw()
                canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)

                update_progress(1.0, "Chart created successfully! ✅")

            finally:
                close_progress()

        except Exception as e:
            self.logger.error(f"Error creating hourly patterns chart: {e}")
            try:
                update_progress(1.0, f"Error: {str(e)}")
            except:
                pass
            close_progress()

    def _create_patient_behavior_chart(self):
        """Create a chart for patient behavior comparison."""
        try:
            show_progress(
                self.parent,
                title="Creating Patient Behavior Chart 📊",
                message="Preparing chart...",
                can_cancel=False,
            )

            try:
                update_progress(0.2, "Creating chart figure...")
                import matplotlib.pyplot as plt
                import numpy as np
                from app.visualization.base_visualizer import BaseVisualizer

                fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))

                update_progress(0.4, "Preparing chart data...")
                differences = self.comparison_results.get("differences", {})

                # First subplot: Total patients and average visits
                metrics = ["total_patients", "avg_visits_per_patient"]
                try:
                    main_values = [differences[m]["main"] for m in metrics]
                    ref_values = [differences[m]["reference"] for m in metrics]
                    data_available = True
                except Exception:
                    data_available = False

                update_progress(0.6, "Drawing charts...")
                x = np.arange(len(metrics))
                width = 0.35

                if data_available:
                    ax1.bar(
                        x - width / 2,
                        main_values,
                        width,
                        label="Main Dataset",
                        color=self.colors["primary"],
                    )
                    ax1.bar(
                        x + width / 2,
                        ref_values,
                        width,
                        label="Reference Dataset",
                        color=self.colors["secondary"],
                    )
                    ax1.set_xlabel("Metrics")
                    ax1.set_ylabel("Count")
                    ax1.set_title("Patient Metrics Comparison")
                    ax1.set_xticks(x)
                    ax1.set_xticklabels(["Total Patients", "Avg Visits/Patient"])
                    ax1.legend()
                else:
                    # Use create_error_plot for ax1
                    visualizer = BaseVisualizer(colors=self.colors)
                    visualizer.create_error_plot(
                        fig,
                        "Patient metrics data not available.",
                        ax=ax1,
                        use_tight_layout=False
                    )

                # Second subplot: Visit distribution
                visit_dist_main = self.comparison_results.get("main_data", {}).get("visit_distribution")
                visit_dist_ref = self.comparison_results.get("ref_data", {}).get("visit_distribution")
                if visit_dist_main and visit_dist_ref:
                    categories = list(visit_dist_main.keys())
                    main_counts = [visit_dist_main[cat] for cat in categories]
                    ref_counts = [visit_dist_ref[cat] for cat in categories]
                    x2 = np.arange(len(categories))
                    ax2.bar(
                        x2 - width / 2,
                        main_counts,
                        width,
                        label="Main Dataset",
                        color=self.colors["primary"],
                    )
                    ax2.bar(
                        x2 + width / 2,
                        ref_counts,
                        width,
                        label="Reference Dataset",
                        color=self.colors["secondary"],
                    )
                    ax2.set_xlabel("Visit Count Category")
                    ax2.set_ylabel("Number of Patients")
                    ax2.set_title("Visit Distribution")
                    ax2.set_xticks(x2)
                    ax2.set_xticklabels(categories)
                    ax2.legend()
                else:
                    # Use create_error_plot for ax2
                    visualizer = BaseVisualizer(colors=self.colors)
                    visualizer.create_error_plot(
                        fig,
                        "Visit distribution data not available.",
                        ax=ax2,
                        use_tight_layout=False
                    )

                fig.tight_layout()

                update_progress(0.8, "Rendering chart...")

                # Clear previous widgets in viz_frame
                for widget in self.viz_frame.winfo_children():
                    widget.destroy()

                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

                # Create a frame for the chart
                chart_frame = ttk.LabelFrame(
                    self.viz_frame, 
                    text="Patient Behavior Comparison", 
                    padding=(10, 5)
                )
                chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

                # Embed the matplotlib figure directly
                canvas_widget = FigureCanvasTkAgg(fig, chart_frame)
                canvas_widget.draw()
                canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)

                update_progress(1.0, "Chart created successfully! ✅")

            finally:
                close_progress()

        except Exception as e:
            self.logger.error(f"Error creating patient behavior chart: {e}")
            try:
                update_progress(1.0, f"Error: {str(e)}")
            except:
                pass
            close_progress()

    def _create_monthly_trends_chart(self):
        """Create a chart for monthly trends comparison."""
        try:
            show_progress(
                self.parent,
                title="Creating Monthly Trends Chart 📊",
                message="Preparing chart...",
                can_cancel=False,
            )

            try:
                update_progress(0.2, "Creating chart figure...")
                fig = Figure(figsize=(12, 6))
                ax = fig.add_subplot(111)

                update_progress(0.4, "Preparing chart data...")
                differences = self.comparison_results.get("differences", {})
                months = sorted(differences.keys())
                main_counts = [differences[m]["main_count"] for m in months]
                ref_counts = [differences[m]["ref_count"] for m in months]

                update_progress(0.6, "Drawing chart...")
                x = np.arange(len(months))
                width = 0.35

                bars1 = ax.bar(
                    x - width / 2,
                    main_counts,
                    width,
                    label="Main Dataset",
                    color=self.colors["primary"],
                )
                bars2 = ax.bar(
                    x + width / 2,
                    ref_counts,
                    width,
                    label="Reference Dataset",
                    color=self.colors["secondary"],
                )

                ax.set_xlabel("Month")
                ax.set_ylabel("Number of Records")
                ax.set_title("Monthly Trends Comparison")
                ax.set_xticks(x)
                ax.set_xticklabels(months, rotation=45, ha="right")
                ax.legend()

                fig.tight_layout()

                update_progress(0.8, "Rendering chart...")

                # Clear previous widgets in viz_frame
                for widget in self.viz_frame.winfo_children():
                    widget.destroy()

                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

                # Create a frame for the chart
                chart_frame = ttk.LabelFrame(
                    self.viz_frame, 
                    text="Monthly Trends Comparison", 
                    padding=(10, 5)
                )
                chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

                # Embed the matplotlib figure directly
                canvas_widget = FigureCanvasTkAgg(fig, chart_frame)
                canvas_widget.draw()
                canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)

                update_progress(1.0, "Chart created successfully! ✅")

            finally:
                close_progress()

        except Exception as e:
            self.logger.error(f"Error creating monthly trends chart: {e}")
            try:
                update_progress(1.0, f"Error: {str(e)}")
            except:
                pass
            close_progress()

    def _create_service_flow_chart(self):
        """Create a chart for service flow analysis using PatientFlowAnalysisGenerator."""
        try:
            show_progress(
                self.parent,
                title="Creating Service Flow Chart 📊",
                message="Preparing chart...",
                can_cancel=False,
            )

            try:
                update_progress(0.2, "Preparing chart data...")

                # Retrieve main and reference datasets from comparison_results
                main_data = self.comparison_results.get("main_data")
                ref_data = self.comparison_results.get("ref_data")

                if main_data is None or ref_data is None:
                    raise ValueError("Main and reference datasets are required for service flow analysis.")

                # Import here to avoid circular import at module level
                from app.visualization.chart_generators.flow_charts import PatientFlowAnalysisGenerator

                # Instantiate the generator for both datasets
                main_gen = PatientFlowAnalysisGenerator()
                ref_gen = PatientFlowAnalysisGenerator()

                # Generate the "Process Sequences" chart for both datasets
                update_progress(0.4, "Generating patient flow charts...")
                main_tabbed = main_gen.generate_tabbed_charts(main_data)
                ref_tabbed = ref_gen.generate_tabbed_charts(ref_data)

                # We'll compare the "Process Sequences" chart for both datasets side by side
                main_fig = main_tabbed.get("Process Sequence Analysis")
                ref_fig = ref_tabbed.get("Process Sequence Analysis")

                # Create a new figure to show both charts side by side
                from matplotlib.figure import Figure as MplFigure
                import matplotlib.pyplot as plt

                update_progress(0.6, "Composing comparison chart...")

                # If using matplotlib Figure, we can draw both as subplots
                fig = MplFigure(figsize=(16, 6))
                ax1 = fig.add_subplot(1, 2, 1)
                ax2 = fig.add_subplot(1, 2, 2)

                # Draw the main dataset chart onto ax1
                if main_fig and hasattr(main_fig, "axes") and main_fig.axes:
                    for child_ax in main_fig.axes:
                        for artist in child_ax.get_children():
                            try:
                                artist.remove()  # Remove from old fig
                                ax1.add_artist(artist)
                            except Exception:
                                pass
                    ax1.set_title("Main Dataset - Process Sequence Analysis")
                else:
                    ax1.text(0.5, 0.5, "No data", ha="center", va="center")
                    ax1.set_title("Main Dataset")

                # Draw the reference dataset chart onto ax2
                if ref_fig and hasattr(ref_fig, "axes") and ref_fig.axes:
                    for child_ax in ref_fig.axes:
                        for artist in child_ax.get_children():
                            try:
                                artist.remove()
                                ax2.add_artist(artist)
                            except Exception:
                                pass
                    ax2.set_title("Reference Dataset - Process Sequence Analysis")
                else:
                    ax2.text(0.5, 0.5, "No data", ha="center", va="center")
                    ax2.set_title("Reference Dataset")

                fig.tight_layout()

                update_progress(0.8, "Rendering chart...")

                # Clear previous widgets in viz_frame
                for widget in self.viz_frame.winfo_children():
                    widget.destroy()

                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

                # Create a frame for the chart
                chart_frame = ttk.LabelFrame(
                    self.viz_frame, 
                    text="Service Flow Analysis Comparison", 
                    padding=(10, 5)
                )
                chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

                # Embed the matplotlib figure directly
                canvas_widget = FigureCanvasTkAgg(fig, chart_frame)
                canvas_widget.draw()
                canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)

                update_progress(1.0, "Chart created successfully! ✅")

            finally:
                close_progress()

        except Exception as e:
            self.logger.error(f"Error creating service flow chart: {e}")
            try:
                update_progress(1.0, f"Error: {str(e)}")
            except:
                pass
            close_progress()

    def _create_location_performance_chart(self):
        """Create a chart for location performance comparison."""
        try:
            show_progress(
                self.parent,
                title="Creating Location Performance Chart 📊",
                message="Preparing chart...",
                can_cancel=False,
            )

            try:
                update_progress(0.2, "Creating chart figure...")
                fig = Figure(figsize=(12, 8))
                ax = fig.add_subplot(111)

                update_progress(0.4, "Preparing chart data...")
                differences = self.comparison_results.get("differences", {})

                # Get top 10 locations by absolute difference
                sorted_locations = sorted(
                    differences.items(),
                    key=lambda x: abs(x[1]["count_diff"]),
                    reverse=True,
                )[:10]
                locations = [loc[0] for loc in sorted_locations]
                main_counts = [loc[1]["main_count"] for loc in sorted_locations]
                ref_counts = [loc[1]["ref_count"] for loc in sorted_locations]

                update_progress(0.6, "Drawing chart...")
                x = np.arange(len(locations))
                width = 0.35

                bars1 = ax.bar(
                    x - width / 2,
                    main_counts,
                    width,
                    label="Main Dataset",
                    color=self.colors["primary"],
                )
                bars2 = ax.bar(
                    x + width / 2,
                    ref_counts,
                    width,
                    label="Reference Dataset",
                    color=self.colors["secondary"],
                )

                ax.set_xlabel("Service Locations")
                ax.set_ylabel("Number of Actions")
                ax.set_title("Location Performance Comparison (Top 10)")
                ax.set_xticks(x)
                ax.set_xticklabels(locations, rotation=45, ha="right")
                ax.legend()

                fig.tight_layout()

                update_progress(0.8, "Rendering chart...")

                # Clear previous widgets in viz_frame
                for widget in self.viz_frame.winfo_children():
                    widget.destroy()

                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

                # Create a frame for the chart
                chart_frame = ttk.LabelFrame(
                    self.viz_frame, 
                    text="Location Performance Comparison", 
                    padding=(10, 5)
                )
                chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

                # Embed the matplotlib figure directly
                canvas_widget = FigureCanvasTkAgg(fig, chart_frame)
                canvas_widget.draw()
                canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)

                update_progress(1.0, "Chart created successfully! ✅")

            finally:
                close_progress()

        except Exception as e:
            self.logger.error(f"Error creating location performance chart: {e}")
            try:
                update_progress(1.0, f"Error: {str(e)}")
            except:
                pass
            close_progress()

    def _create_action_analysis_chart(self):
        """Create a chart for action analysis comparison."""
        try:
            show_progress(
                self.parent,
                title="Creating Action Analysis Chart 📊",
                message="Preparing chart...",
                can_cancel=False,
            )

            try:
                update_progress(0.2, "Creating chart figure...")
                fig = Figure(figsize=(12, 8))
                ax = fig.add_subplot(111)

                update_progress(0.4, "Preparing chart data...")
                differences = self.comparison_results.get("differences", {})

                # Get top 10 actions by absolute difference
                sorted_actions = sorted(
                    differences.items(),
                    key=lambda x: abs(x[1]["count_diff"]),
                    reverse=True,
                )[:10]
                actions = [action[0] for action in sorted_actions]
                main_counts = [action[1]["main_count"] for action in sorted_actions]
                ref_counts = [action[1]["ref_count"] for action in sorted_actions]

                update_progress(0.6, "Drawing chart...")
                x = np.arange(len(actions))
                width = 0.35

                bars1 = ax.bar(
                    x - width / 2,
                    main_counts,
                    width,
                    label="Main Dataset",
                    color=self.colors["primary"],
                )
                bars2 = ax.bar(
                    x + width / 2,
                    ref_counts,
                    width,
                    label="Reference Dataset",
                    color=self.colors["secondary"],
                )

                ax.set_xlabel("Actions")
                ax.set_ylabel("Number of Occurrences")
                ax.set_title("Action Analysis Comparison (Top 10)")
                ax.set_xticks(x)
                ax.set_xticklabels(actions, rotation=45, ha="right")
                ax.legend()

                fig.tight_layout()

                update_progress(0.8, "Rendering chart...")

                # Clear previous widgets in viz_frame
                for widget in self.viz_frame.winfo_children():
                    widget.destroy()

                from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

                # Create a frame for the chart
                chart_frame = ttk.LabelFrame(
                    self.viz_frame, 
                    text="Action Analysis Comparison", 
                    padding=(10, 5)
                )
                chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

                # Embed the matplotlib figure directly
                canvas_widget = FigureCanvasTkAgg(fig, chart_frame)
                canvas_widget.draw()
                canvas_widget.get_tk_widget().pack(fill=tk.BOTH, expand=True)

                update_progress(1.0, "Chart created successfully! ✅")

            finally:
                close_progress()

        except Exception as e:
            self.logger.error(f"Error creating action analysis chart: {e}")
            try:
                update_progress(1.0, f"Error: {str(e)}")
            except:
                pass
            close_progress()

    def _display_service_distribution_results(self):
        """Display service distribution comparison results."""
        # Summary tab
        summary_text = tk.Text(self.summary_frame, wrap=tk.WORD, height=15)
        summary_scrollbar = ttk.Scrollbar(
            self.summary_frame, orient=tk.VERTICAL, command=summary_text.yview
        )
        summary_text.config(yscrollcommand=summary_scrollbar.set)

        summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Generate summary text
        summary_content = "SERVICE DISTRIBUTION COMPARISON SUMMARY\n"
        summary_content += "=" * 50 + "\n\n"

        differences = self.comparison_results.get("differences", {})

        for service, data in differences.items():
            summary_content += f"{service}:\n"
            summary_content += f"  Main Dataset: {data['main_count']:,} ({data['main_percentage']:.1f}%)\n"
            summary_content += f"  Reference Dataset: {data['ref_count']:,} ({data['ref_percentage']:.1f}%)\n"
            summary_content += f"  Count Difference: {data['count_diff']:+,}\n"
            summary_content += (
                f"  Percentage Difference: {data['percentage_diff']:+.1f}%\n"
            )
            if data["percent_change"] != float("inf"):
                summary_content += f"  Percent Change: {data['percent_change']:+.1f}%\n"
            summary_content += "\n"

        summary_text.insert(tk.END, summary_content)
        summary_text.config(state=tk.DISABLED)

        # Visualization tab
        self._create_service_distribution_chart()

    def _display_hourly_patterns_results(self):
        """Display hourly patterns comparison results."""
        # Summary tab
        summary_text = tk.Text(self.summary_frame, wrap=tk.WORD, height=15)
        summary_scrollbar = ttk.Scrollbar(
            self.summary_frame, orient=tk.VERTICAL, command=summary_text.yview
        )
        summary_text.config(yscrollcommand=summary_scrollbar.set)

        summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Generate summary text
        summary_content = "HOURLY PATTERNS COMPARISON SUMMARY\n"
        summary_content += "=" * 50 + "\n\n"

        main_data = self.comparison_results.get("main_data", {})
        ref_data = self.comparison_results.get("ref_data", {})

        summary_content += f"Main Dataset Peak Hour: {main_data.get('peak_hour', 'N/A')} ({main_data.get('peak_count', 0):,} actions)\n"
        summary_content += f"Reference Dataset Peak Hour: {ref_data.get('peak_hour', 'N/A')} ({ref_data.get('peak_count', 0):,} actions)\n\n"

        differences = self.comparison_results.get("differences", {})
        summary_content += "Hourly Differences:\n"
        for hour in sorted(differences.keys()):
            data = differences[hour]
            # Calculate percentage difference relative to main and reference counts
            main_count = data['main_count']
            ref_count = data['ref_count']
            count_diff = data['count_diff']
            percent_of_main = (count_diff / main_count * 100) if main_count != 0 else float('inf')
            percent_of_ref = (count_diff / ref_count * 100) if ref_count != 0 else float('inf')
            summary_content += (
                f"  {hour:02d}:00 - Main: {main_count:,}, Ref: {ref_count:,}, "
                f"Diff: {count_diff:+,} "
                f"({percent_of_main:+.1f}% of Main, {percent_of_ref:+.1f}% of Ref)\n"
            )

        summary_text.insert(tk.END, summary_content)
        summary_text.config(state=tk.DISABLED)

        # Visualization tab
        self._create_hourly_patterns_chart()

    def _display_patient_behavior_results(self):
        """Display patient behavior comparison results."""
        # Summary tab
        summary_text = tk.Text(self.summary_frame, wrap=tk.WORD, height=15)
        summary_scrollbar = ttk.Scrollbar(
            self.summary_frame, orient=tk.VERTICAL, command=summary_text.yview
        )
        summary_text.config(yscrollcommand=summary_scrollbar.set)

        summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Generate summary text
        summary_content = "PATIENT BEHAVIOR COMPARISON SUMMARY\n"
        summary_content += "=" * 50 + "\n\n"

        differences = self.comparison_results.get("differences", {})

        for metric, data in differences.items():
            summary_content += f"{metric.replace('_', ' ').title()}:\n"
            summary_content += f"  Main Dataset: {data['main']:,.1f}\n"
            summary_content += f"  Reference Dataset: {data['reference']:,.1f}\n"
            summary_content += f"  Difference: {data['diff']:+,.1f}\n"
            if data["percent_change"] != float("inf"):
                summary_content += f"  Percent Change: {data['percent_change']:+.1f}%\n"
            summary_content += "\n"

        summary_text.insert(tk.END, summary_content)
        summary_text.config(state=tk.DISABLED)

        # Visualization tab
        self._create_patient_behavior_chart()

    def _display_monthly_trends_results(self):
        """Display monthly trends comparison results."""
        # Summary tab
        summary_text = tk.Text(self.summary_frame, wrap=tk.WORD, height=15)
        summary_scrollbar = ttk.Scrollbar(
            self.summary_frame, orient=tk.VERTICAL, command=summary_text.yview
        )
        summary_text.config(yscrollcommand=summary_scrollbar.set)

        summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Generate summary text
        summary_content = "MONTHLY TRENDS COMPARISON SUMMARY\n"
        summary_content += "=" * 50 + "\n\n"

        main_data = self.comparison_results.get("main_data", {})
        ref_data = self.comparison_results.get("ref_data", {})

        summary_content += f"Main Dataset: {main_data.get('total_months', 0)} months, Avg: {main_data.get('avg_monthly_volume', 0):,.0f} records/month\n"
        summary_content += f"Reference Dataset: {ref_data.get('total_months', 0)} months, Avg: {ref_data.get('avg_monthly_volume', 0):,.0f} records/month\n\n"

        differences = self.comparison_results.get("differences", {})
        summary_content += "Monthly Differences:\n"
        for month in sorted(differences.keys()):
            data = differences[month]
            summary_content += f"  {month} - Main: {data['main_count']:,}, Ref: {data['ref_count']:,}, Diff: {data['count_diff']:+,}\n"

        summary_text.insert(tk.END, summary_content)
        summary_text.config(state=tk.DISABLED)

        # Visualization tab
        self._create_monthly_trends_chart()

    def _display_service_flow_results(self):
        """Display service flow analysis results."""
        from app.visualization.chart_generators.flow_charts import PatientFlowAnalysisGenerator

        # Summary tab
        summary_text = tk.Text(self.summary_frame, wrap=tk.WORD, height=15)
        summary_scrollbar = ttk.Scrollbar(
            self.summary_frame, orient=tk.VERTICAL, command=summary_text.yview
        )
        summary_text.config(yscrollcommand=summary_scrollbar.set)

        summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Use PatientFlowAnalysisGenerator config for column names and mappings
        pf_config = PatientFlowAnalysisGenerator.DEFAULT_CONFIG
        columns = pf_config['columns']
        service_mappings = pf_config['service_mappings']

        # Generate summary text
        summary_content = "SERVICE FLOW ANALYSIS SUMMARY\n"
        summary_content += "=" * 50 + "\n\n"

        main_data = self.comparison_results.get("main_data", {})
        ref_data = self.comparison_results.get("ref_data", {})

        # Use config-driven column names for summary
        main_actions = main_data.get('total_actions', 0)
        main_service_types = main_data.get('unique_service_types', 0)
        main_action_types = main_data.get('unique_actions', 0)
        ref_actions = ref_data.get('total_actions', 0)
        ref_service_types = ref_data.get('unique_service_types', 0)
        ref_action_types = ref_data.get('unique_actions', 0)

        summary_content += (
            f"Main Dataset: {main_actions:,} {columns.get('action', 'actions')}, "
            f"{main_service_types} service types, {main_action_types} action types\n"
        )
        summary_content += (
            f"Reference Dataset: {ref_actions:,} {columns.get('action', 'actions')}, "
            f"{ref_service_types} service types, {ref_action_types} action types\n\n"
        )

        differences = self.comparison_results.get("differences", {})
        for metric, data in differences.items():
            # Try to use config-driven label if available
            metric_label = columns.get(metric, metric.replace('_', ' ').title())
            summary_content += f"{metric_label}:\n"
            summary_content += f"  Main Dataset: {data['main']:,}\n"
            summary_content += f"  Reference Dataset: {data['reference']:,}\n"
            summary_content += f"  Difference: {data['diff']:+,}\n"
            if data.get("percent_change", float("inf")) != float("inf"):
                summary_content += f"  Percent Change: {data['percent_change']:+.1f}%\n"
            summary_content += "\n"

        # Optionally, show service mappings summary for context
        summary_content += "Service Type Mappings (from config):\n"
        for service, actions in service_mappings.items():
            summary_content += f"  {service}: {', '.join(actions)}\n"
        summary_content += "\n"

        summary_text.insert(tk.END, summary_content)
        summary_text.config(state=tk.DISABLED)

        # Visualization tab
        self._create_service_flow_chart()

    def _display_location_performance_results(self):
        """Display location performance comparison results."""
        # Summary tab
        summary_text = tk.Text(self.summary_frame, wrap=tk.WORD, height=15)
        summary_scrollbar = ttk.Scrollbar(
            self.summary_frame, orient=tk.VERTICAL, command=summary_text.yview
        )
        summary_text.config(yscrollcommand=summary_scrollbar.set)

        summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Generate summary text
        summary_content = "LOCATION PERFORMANCE COMPARISON SUMMARY\n"
        summary_content += "=" * 50 + "\n\n"

        main_data = self.comparison_results.get("main_data", {})
        ref_data = self.comparison_results.get("ref_data", {})

        summary_content += f"Main Dataset: {main_data.get('total_locations', 0)} locations, Busiest: {main_data.get('busiest_location', 'N/A')} ({main_data.get('busiest_location_count', 0):,} actions)\n"
        summary_content += f"Reference Dataset: {ref_data.get('total_locations', 0)} locations, Busiest: {ref_data.get('busiest_location', 'N/A')} ({ref_data.get('busiest_location_count', 0):,} actions)\n\n"

        differences = self.comparison_results.get("differences", {})
        summary_content += "Top 10 Location Differences:\n"
        sorted_locations = sorted(
            differences.items(), key=lambda x: abs(x[1]["count_diff"]), reverse=True
        )[:10]

        for location, data in sorted_locations:
            summary_content += f"  {location}: Main {data['main_count']:,}, Ref {data['ref_count']:,}, Diff {data['count_diff']:+,}\n"

        summary_text.insert(tk.END, summary_content)
        summary_text.config(state=tk.DISABLED)

        # Visualization tab
        self._create_location_performance_chart()

    def _display_action_analysis_results(self):
        """Display action analysis comparison results."""
        # Summary tab
        summary_text = tk.Text(self.summary_frame, wrap=tk.WORD, height=15)
        summary_scrollbar = ttk.Scrollbar(
            self.summary_frame, orient=tk.VERTICAL, command=summary_text.yview
        )
        summary_text.config(yscrollcommand=summary_scrollbar.set)

        summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Generate summary text
        summary_content = "ACTION ANALYSIS COMPARISON SUMMARY\n"
        summary_content += "=" * 50 + "\n\n"

        main_data = self.comparison_results.get("main_data", {})
        ref_data = self.comparison_results.get("ref_data", {})

        summary_content += f"Main Dataset: {main_data.get('total_actions', 0):,} actions, {main_data.get('unique_actions', 0)} unique actions\n"
        summary_content += f"Most Common: {main_data.get('most_common_action', 'N/A')} ({main_data.get('most_common_count', 0):,} times)\n\n"
        summary_content += f"Reference Dataset: {ref_data.get('total_actions', 0):,} actions, {ref_data.get('unique_actions', 0)} unique actions\n"
        summary_content += f"Most Common: {ref_data.get('most_common_action', 'N/A')} ({ref_data.get('most_common_count', 0):,} times)\n\n"

        differences = self.comparison_results.get("differences", {})
        summary_content += "Top 10 Action Differences:\n"
        sorted_actions = sorted(
            differences.items(), key=lambda x: abs(x[1]["count_diff"]), reverse=True
        )[:10]

        for action, data in sorted_actions:
            summary_content += f"  {action}: Main {data['main_count']:,}, Ref {data['ref_count']:,}, Diff {data['count_diff']:+,}\n"

        summary_text.insert(tk.END, summary_content)
        summary_text.config(state=tk.DISABLED)

        # Visualization tab
        self._create_action_analysis_chart()

    def _display_generic_results(self):
        """Display generic results for unknown comparison types."""
        # Summary tab
        summary_text = tk.Text(self.summary_frame, wrap=tk.WORD, height=15)
        summary_scrollbar = ttk.Scrollbar(
            self.summary_frame, orient=tk.VERTICAL, command=summary_text.yview
        )
        summary_text.config(yscrollcommand=summary_scrollbar.set)

        summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        summary_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Generate summary text
        summary_content = (
            f"COMPARISON RESULTS - {self.comparison_results['type'].upper()}\n"
        )
        summary_content += "=" * 50 + "\n\n"
        summary_content += "Detailed results are available in the export.\n\n"

        differences = self.comparison_results.get("differences", {})
        for key, data in differences.items():
            summary_content += f"{key}:\n"
            if isinstance(data, dict):
                for sub_key, value in data.items():
                    if isinstance(value, float):
                        summary_content += f"  {sub_key}: {value:.2f}\n"
                    else:
                        summary_content += f"  {sub_key}: {value}\n"
            else:
                summary_content += f"  {data}\n"
            summary_content += "\n"

        summary_text.insert(tk.END, summary_content)
        summary_text.config(state=tk.DISABLED)

    def _export_comparison(self):
        """Export comparison results to file."""
        if not self.comparison_results:
            messagebox.showwarning("Warning", "No comparison results to export")
            return

        try:
            # Get save location
            file_path = filedialog.asksaveasfilename(
                title="Export Comparison Results",
                defaultextension=".txt",
                filetypes=[
                    ("Text files", "*.txt"),
                    ("CSV files", "*.csv"),
                    ("All files", "*.*"),
                ],
            )

            if not file_path:
                return

            # Show progress dialog for export
            show_progress(
                self.parent,
                title="Exporting Comparison Results 📊",
                message="Preparing export...",
                can_cancel=True,
            )

            try:
                # Generate export content
                update_progress(0.3, "Generating export content...")
                content = self._generate_export_content()

                # Save to file
                update_progress(0.7, "Writing to file...")
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(content)

                update_progress(1.0, "Export completed successfully! ✅")

                messagebox.showinfo(
                    "Success", f"Comparison results exported to:\n{file_path}"
                )
                self.logger.info(f"Comparison results exported to: {file_path}")

            finally:
                # Close progress dialog
                close_progress()

        except Exception as e:
            self.logger.error(f"Error exporting comparison: {e}")
            messagebox.showerror("Error", f"Error exporting comparison:\n{str(e)}")

    def _generate_export_content(self):
        """Generate content for export."""
        content = "DATA COMPARISON REPORT\n"
        content += "=" * 50 + "\n\n"
        content += f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        content += f"Comparison Type: {self.comparison_results['type'].replace('_', ' ').title()}\n"
        content += f"Main Dataset: {os.path.basename(self.main_data_loader.get_file_path()) if self.main_data_loader.get_file_path() else 'Unknown'}\n"
        content += f"Reference Dataset: {os.path.basename(self.reference_file_path) if self.reference_file_path else 'Unknown'}\n\n"

        differences = self.comparison_results.get("differences", {})

        for key, data in differences.items():
            content += f"{key.replace('_', ' ').title()}:\n"
            for sub_key, value in data.items():
                if isinstance(value, float):
                    content += f"  {sub_key.replace('_', ' ').title()}: {value:.2f}\n"
                else:
                    content += f"  {sub_key.replace('_', ' ').title()}: {value}\n"
            content += "\n"

        return content

    def _clear_results(self):
        """Clear comparison results and reset UI."""
        self.comparison_results = None
        self.export_btn.config(state="disabled")
        self._show_placeholder()
        self.logger.info("Comparison results cleared")

    def set_main_data_loader(self, data_loader):
        """Set the main data loader for comparison."""
        self.main_data_loader = data_loader

        # Enable comparison if reference data is loaded
        if (
            self.reference_data_loader.has_data()
            and self.main_data_loader
            and self.main_data_loader.has_data()
        ):
            self.compare_btn.config(state="normal")

    def get_comparison_results(self):
        """Get the current comparison results."""
        return self.comparison_results
