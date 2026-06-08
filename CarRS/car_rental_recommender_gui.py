import os
import sys
import pandas as pd
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
import numpy as np
from datetime import datetime
import json
import threading
import queue
import time
import socket
import requests

# Import core logic
from car_rental_recommender_core import (
    load_data,
    enhance_dataframe,
    run_cleaning_pipeline,
    create_complete_cost_analysis,
    calculate_estimated_cost,
    get_recommendations,
    get_providers_for_region,
    VALID_REGIONS,
    analyze_rental_costs,
    calculate_required_mileage,
    calculate_required_duration,
    generate_booking_scenarios,
    calculate_cost_breakdown,
    get_enhanced_recommendations,
    get_ollama_enhanced_recommendations,
    get_calculator_pricing_recommendations,
    calculate_provider_prices,
    create_ml_budget_prediction,
    calculate_spending_trend,
    assess_budget_risk,
    calculate_confidence_score,
    calculate_cost_requirements,
    create_trip_record,
    # User preference functions
    analyze_user_preferences,
    prepare_user_data_summary,
    get_preference_based_recommendations,
    prepare_context_for_ollama,
    get_enhanced_preference_recommendations,
    # Range-based analysis functions
    get_distance_range,
    get_duration_range,
    get_range_specific_statistics,
    analyze_provider_performance_by_ranges,
    # Prediction functions
    predict_rental_patterns,
    analyze_historical_patterns,
    predict_rental_possibility,
    # LLM parsing functions
    parse_rental_description_with_llm,
    estimate_missing_fields_with_llm,
    call_ollama_api,
    # Form validation (core logic, no UI)
    validate_numeric_input,
    validate_date_input,
    validate_date_range,
)
from components import LoadingDialog, GUIHelper, OllamaHelper


def set_modern_theme(root):
    """Set a modern theme for the application"""
    style = ttk.Style()
    style.theme_use("clam")  # Use clam as base theme

    # Configure colors
    style.configure(
        ".", background="#f0f0f0", foreground="#333333", font=("Segoe UI", 10)
    )

    # Configure specific widgets
    style.configure("TFrame", background="#f0f0f0")
    style.configure("TLabel", background="#f0f0f0", font=("Segoe UI", 10))
    style.configure(
        "TButton",
        background="#0078d7",
        foreground="white",
        font=("Segoe UI", 10, "bold"),
        padding=5,
    )
    style.configure("TEntry", fieldbackground="white", font=("Segoe UI", 10), padding=5)
    style.configure(
        "Treeview", background="white", fieldbackground="white", font=("Segoe UI", 10)
    )
    style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    # Configure hover effects
    style.map(
        "TButton", background=[("active", "#005fa3")], foreground=[("active", "white")]
    )

class CarRentalRecommenderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Car Rental Recommender")

        # Helper to create StringVars in bulk
        def create_stringvars(names, default=None):
            d = {}
            for name in names:
                if isinstance(default, dict) and name in default:
                    d[name] = tk.StringVar(value=default[name])
                elif isinstance(default, str):
                    d[name] = tk.StringVar(value=default)
                else:
                    d[name] = tk.StringVar()
            return d

        # Initialize variables
        self.df = None
        self.cost_analysis = None
        self._last_quality_report = None  # Data cleaning pipeline quality report
        self.settings = {}
        self.selected_record = None
        self._updating_fields = False  # Flag to prevent recursive calls in auto_update_fields
        self._updating_fuel_economy = False  # Flag to prevent recursive calls in update_fuel_economy_comparison
        
        # Initialize user profile attributes with defaults (will be loaded from settings if available)
        self.user_age = 25
        self.user_experience_years = 5

        # StringVars used across multiple tabs
        shared_vars = {
            "cost_per_kwh_var": "0.45",
            "fuel_price_var": "2.51",
            "fuel_cost_var": "20",
            "tank_distance_var": "110",
            "getgo_mileage_var": "0.39",
            "carclub_mileage_var": "0.33",
        }
        self.__dict__.update(create_stringvars(shared_vars.keys(), shared_vars))

        # Esso Singapore fuel discount: 23% off when enabled and region is Singapore only
        self.apply_esso_sg_discount_var = tk.BooleanVar(value=True)

        # StringVars for records management tab (no default unless specified)
        record_vars = [
            "record_date_var",
            "record_region_var",
            "record_car_model_var",
            "record_provider_var",
            "record_distance_var",
            "record_hours_var",
            "record_fuel_pumped_var",
            "record_fuel_usage_var",
            "record_weekend_var",
            "record_total_cost_var",
            "record_pumped_cost_var",
            "record_cost_per_km_var",
            "record_duration_cost_var",
            "record_kwh_used_var",
            "record_electricity_cost_var",
            "search_var",
            "record_consumption_var",
            "record_fuel_savings_var",
            "record_cost_per_hr_var",
            "record_mileage_cost_var",
            "record_deposit_rm_var",
            "record_rental_fee_rm_var",
            "record_additional_fee_rm_var",
        ]
        # Remove duplicates (record_kwh_used_var, record_electricity_cost_var appear twice)
        record_vars = list(dict.fromkeys(record_vars))
        self.__dict__.update(create_stringvars(record_vars))

        # Initialize style
        self.style = ttk.Style()

        # Create main container
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        tab_names = [
            ("recommendation_tab", "Recommendations"),
            ("data_analysis_tab", "Data Analysis"),
            ("records_management_tab", "Records Management"),
            ("cost_planning_tab", "Budget Planner"),
            ("predictions_tab", "Predictions"),
            ("calculator_tab", "Calculator"),
            ("user_preference_tab", "User Preferences"),
            ("settings_tab", "Settings"),
        ]
        for attr, label in tab_names:
            setattr(self, attr, ttk.Frame(self.notebook))
            self.notebook.add(getattr(self, attr), text=label)

        # Set up each tab
        self.setup_recommendation_tab()
        self.setup_data_analysis_tab()
        self.setup_records_management_tab()
        self.setup_cost_planning_tab()
        self.setup_predictions_tab()
        self.setup_calculator_tab()
        self.setup_user_preference_tab()
        self.setup_settings_tab()

        # Set modern theme
        set_modern_theme(root)

        # Load settings
        self.load_settings()

        # Set up status bar
        self.status_var = tk.StringVar()
        self.status_bar = ttk.Label(
            root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Initialize with default data file if it exists (async)
        default_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "22 - Sheet1.csv"
        )
        if os.path.exists(default_file):
            # Load data asynchronously without showing dialog on startup
            self.root.after(100, lambda: self.load_data_file(default_file, show_dialog=False))
        
        # Detect Ollama models asynchronously on startup
        self.root.after(200, self.refresh_ollama_models)

        # Ensure input fields are properly initialized after a short delay
        self.root.after(100, self.ensure_input_fields_ready)
        
        # Track form dirty state for unsaved changes warning
        self._form_dirty = False

    # ========== Helper Methods for Validation and Error Handling ==========
    
    def _check_data_loaded(self, show_error=True):
        """
        Check if data is loaded and not empty.
        Returns True if data is available, False otherwise.
        If show_error is True, displays a user-friendly error message.
        """
        if self.df is None:
            if show_error:
                self._show_user_friendly_error(
                    "No Data Loaded",
                    "Please load a rental data file first.\n\nYou can load data using the 'Browse...' button in the Recommendations tab."
                )
            return False
        if self.df.empty:
            if show_error:
                self._show_user_friendly_error(
                    "Empty Dataset",
                    "The loaded data file contains no records.\n\nPlease load a valid data file with rental records."
                )
            return False
        return True
    
    def _check_column_exists(self, column_name, show_error=True):
        """
        Check if a required column exists in the dataframe.
        Returns True if column exists, False otherwise.
        """
        if not self._check_data_loaded(show_error=False):
            return False
        if column_name not in self.df.columns:
            if show_error:
                self._show_user_friendly_error(
                    "Missing Data Column",
                    f"The required column '{column_name}' is missing from your data.\n\n"
                    f"Available columns: {', '.join(self.df.columns[:10])}{'...' if len(self.df.columns) > 10 else ''}\n\n"
                    "Please ensure your data file contains all required columns."
                )
            return False
        return True
    
    def _show_user_friendly_error(self, title, message, field_name=None):
        """
        Display a user-friendly error message with helpful context.
        
        Args:
            title: Short error title
            message: Detailed error message
            field_name: Optional name of the field that caused the error
        """
        if field_name:
            full_message = f"{message}\n\nField: {field_name}"
        else:
            full_message = message
        
        messagebox.showerror(title, full_message)
        self.status_var.set(f"Error: {title}")
    
    def setup_recommendation_tab(self):
        # Main container
        container = ttk.Frame(self.recommendation_tab)
        container.pack(fill=tk.BOTH, expand=True)

        # --- Left: Chat Assistant ---
        left_panel = ttk.LabelFrame(container, text="Car Rental Assistant", padding=(10, 5))
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5), pady=5)

        # Chat display
        chat_frame = ttk.Frame(left_panel)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.chat_display = tk.Text(
            chat_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Segoe UI", 10),
            bg="white", relief=tk.SUNKEN, borderwidth=1
        )
        chat_scrollbar = ttk.Scrollbar(chat_frame, orient=tk.VERTICAL, command=self.chat_display.yview)
        self.chat_display.configure(yscrollcommand=chat_scrollbar.set)
        self.chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Chat input
        input_frame = ttk.Frame(left_panel)
        input_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        self.message_var = tk.StringVar()
        self.message_entry = ttk.Entry(
            input_frame, textvariable=self.message_var, font=("Segoe UI", 10), state="normal"
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        send_button = ttk.Button(
            input_frame, text="Send", command=self.send_message, style="Accent.TButton"
        )
        send_button.pack(side=tk.RIGHT)
        self.message_entry.bind("<Return>", lambda e: self.send_message())

        # Settings (left, below chat) - Enhanced with better organization
        settings_frame = ttk.LabelFrame(left_panel, text="Settings", padding=(5, 5))
        settings_frame.pack(fill=tk.X, padx=5, pady=(5, 0))
        
        # Trip Settings Section
        trip_frame = ttk.Frame(settings_frame)
        trip_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(trip_frame, text="Trip Settings:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        trip_settings_inner = ttk.Frame(trip_frame)
        trip_settings_inner.pack(fill=tk.X, padx=(10, 0), pady=(2, 0))
        
        self.is_weekend_var = tk.BooleanVar()
        GUIHelper.create_checkbutton(trip_settings_inner, "Weekend Trip", self.is_weekend_var)
        
        ttk.Label(trip_settings_inner, text="Passengers:").pack(side=tk.LEFT, padx=(10, 2))
        self.passenger_count_var = tk.StringVar()
        passenger_spinbox = ttk.Spinbox(
            trip_settings_inner, from_=1, to=10, textvariable=self.passenger_count_var,
            width=5, state="readonly"
        )
        passenger_spinbox.pack(side=tk.LEFT, padx=(0, 5))
        self.passenger_count_var.set("2")
        
        ttk.Label(trip_settings_inner, text="Space:").pack(side=tk.LEFT, padx=(5, 2))
        self.space_requirements_var = tk.StringVar()
        space_combobox = ttk.Combobox(trip_settings_inner, textvariable=self.space_requirements_var, width=12, values=["little", "medium", "alot"], state="readonly")
        space_combobox.pack(side=tk.LEFT, padx=(0, 5))
        self.space_requirements_var.set("little")
        
        # AI Settings Section
        ai_frame = ttk.Frame(settings_frame)
        ai_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(ai_frame, text="AI Settings:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        ai_settings_inner = ttk.Frame(ai_frame)
        ai_settings_inner.pack(fill=tk.X, padx=(10, 0), pady=(2, 0))
        
        self.use_ml_var = tk.BooleanVar(value=True)
        GUIHelper.create_checkbutton(ai_settings_inner, "Use Machine Learning", self.use_ml_var)
        
        self.use_ollama_var = tk.BooleanVar(value=False)
        GUIHelper.create_checkbutton(ai_settings_inner, "Use Ollama LLM", self.use_ollama_var)
        
        # Ollama model selection with refresh button
        ollama_model_frame = ttk.Frame(ai_settings_inner)
        ollama_model_frame.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(ollama_model_frame, text="Model:").pack(side=tk.LEFT, padx=(10, 2))
        self.ollama_model_var = tk.StringVar(value="llama3.1:3b")
        self.ollama_model_combobox = GUIHelper.create_combobox(
            ollama_model_frame, self.ollama_model_var,
            ["llama3.1:3b", "llama2", "llama2:7b", "llama2:13b", "mistral", "codellama", "neural-chat"],
            width=15,
        )
        self.ollama_model_combobox.pack(side=tk.LEFT, padx=(0, 5))
        
        refresh_model_btn = ttk.Button(
            ollama_model_frame, text="🔄", width=3,
            command=self.refresh_ollama_models
        )
        refresh_model_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Ollama connection status indicator
        self.ollama_status_label = ttk.Label(
            ollama_model_frame, text="●", foreground="gray", font=("Segoe UI", 12)
        )
        self.ollama_status_label.pack(side=tk.LEFT, padx=(5, 0))
        self.ollama_status_tooltip = "Ollama status: Unknown"
        
        # Filter Settings Section (region-aware: Singapore vs Malaysia)
        filter_frame = ttk.Frame(settings_frame)
        filter_frame.pack(fill=tk.X)
        ttk.Label(filter_frame, text="Filter Settings:", font=("Segoe UI", 9, "bold")).pack(anchor=tk.W)
        filter_settings_inner = ttk.Frame(filter_frame)
        filter_settings_inner.pack(fill=tk.X, padx=(10, 0), pady=(2, 0))

        ttk.Label(filter_settings_inner, text="Region:").pack(side=tk.LEFT, padx=(0, 2))
        self.current_region_var = tk.StringVar(value="Singapore")
        GUIHelper.create_combobox(
            filter_settings_inner, self.current_region_var,
            list(VALID_REGIONS), width=12,
        )
        self.current_region_var.trace_add("write", lambda *a: self._on_region_filter_changed())

        ttk.Label(filter_settings_inner, text="Category:").pack(side=tk.LEFT, padx=(0, 2))
        self.car_cat_var = tk.StringVar(value="All")
        self.car_cat_combo = GUIHelper.create_combobox(
            filter_settings_inner, self.car_cat_var,
            ["All"] + get_providers_for_region("Singapore"), width=12,
        )
        self.recommendation_region_label = ttk.Label(
            filter_frame, text="Showing recommendations for: Singapore",
            font=("Segoe UI", 9)
        )
        self.recommendation_region_label.pack(anchor=tk.W, padx=(10, 0), pady=(2, 0))

        # Initialize Ollama model list (will be populated asynchronously)
        self.available_ollama_models = ["llama3.1:3b", "llama2", "llama2:7b", "llama2:13b", "mistral", "codellama", "neural-chat"]
        self.ollama_available = False

        # Chat state
        self.chat_state = {
            "waiting_for_timing": False,
            "waiting_for_distance": False,
            "waiting_for_duration": False,
            "waiting_for_passengers": False,
            "waiting_for_space": False,
            "rental_date": None,
            "rental_time": None,
            "rental_timing": None,
            "distance": None,
            "duration": None,
            "passenger_count": 2,  # Default: 2 passengers (including driver)
            "space_requirements": "little",  # Default: little space
            "conversation_started": False,
            "conversation_history": [],
            "last_recommendations": None,
            "user_preferences": {},
            "trip_context": {},
        }
        self.start_chat()

        # --- Right: Recommendations, Error Log, Results, Chart, Data Source ---
        right_panel = ttk.LabelFrame(container, text="Recommendations", padding=(10, 5))
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)

        # Error log
        error_frame = ttk.LabelFrame(right_panel, text="Error Log", padding=(5, 5))
        error_frame.pack(fill=tk.X, padx=5, pady=(0, 5))
        error_display_frame = ttk.Frame(error_frame)
        error_display_frame.pack(fill=tk.BOTH, expand=True)
        self.error_display = tk.Text(
            error_display_frame, wrap=tk.WORD, state=tk.DISABLED, font=("Segoe UI", 9),
            bg="#fff5f5", fg="#d73a49", relief=tk.SUNKEN, borderwidth=1, height=3
        )
        error_scrollbar = ttk.Scrollbar(error_display_frame, orient=tk.VERTICAL, command=self.error_display.yview)
        self.error_display.configure(yscrollcommand=error_scrollbar.set)
        clear_error_button = ttk.Button(
            error_display_frame, text="Clear", command=self.clear_error_display, style="Accent.TButton"
        )
        self.error_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        error_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        clear_error_button.pack(side=tk.RIGHT, padx=(5, 0))

        # Results treeview
        self.results_tree = ttk.Treeview(
            right_panel,
            columns=("provider", "car_model", "cost", "method", "confidence", "reasoning", "full_reasoning"),
            show="headings",
        )
        headings = [
            ("provider", "Provider"),
            ("car_model", "Car Model"),
            ("cost", "Est. Cost ($)"),
            ("method", "Method"),
            ("confidence", "Confidence"),
            ("reasoning", "Reasoning"),
            ("full_reasoning", ""),
        ]
        for col, text in headings:
            self.results_tree.heading(col, text=text)
        columns_config = [
            ("provider", 80, None),
            ("car_model", 120, None),
            ("cost", 80, tk.E),
            ("method", 100, None),
            ("confidence", 80, tk.CENTER),
            ("reasoning", 300, None),
            ("full_reasoning", 0, None),
        ]
        for col, width, anchor in columns_config:
            if anchor is not None:
                self.results_tree.column(col, width=width, anchor=anchor, stretch=(col != "full_reasoning"))
            else:
                self.results_tree.column(col, width=width, stretch=(col != "full_reasoning"))
        self.results_tree.column("full_reasoning", stretch=False)
        results_scroll = ttk.Scrollbar(right_panel, orient=tk.VERTICAL, command=self.results_tree.yview)
        self.results_tree.configure(yscrollcommand=results_scroll.set)
        self.results_tree.bind("<Double-1>", self.show_recommendation_details)
        results_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Chart
        self.chart_frame = ttk.LabelFrame(right_panel, text="Cost Comparison", padding=(10, 5))
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Data file selection frame
        file_frame = ttk.LabelFrame(right_panel, text="Data Source", padding=5)
        file_frame.pack(fill=tk.X, padx=5, pady=5)

        # Variables
        self.data_file_var = tk.StringVar()
        self.file_path_var = tk.StringVar()

        # "Loaded File:" label
        file_label = GUIHelper.create_label(file_frame, "Loaded File:")
        file_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 2), pady=2)
        file_name_entry = ttk.Entry(
            file_frame, textvariable=self.data_file_var, state="readonly", width=24, font=("Segoe UI", 9)
        )
        file_name_entry.grid(row=0, column=1, sticky=tk.W + tk.E, padx=(0, 5), pady=2)
        file_path_entry = ttk.Entry(
            file_frame, textvariable=self.file_path_var, state="readonly", width=28
        )
        file_path_entry.grid(row=1, column=1, sticky=tk.W + tk.E, padx=(0, 5), pady=(0, 2))
        browse_button = ttk.Button(file_frame, text="Browse...", command=self.browse_file)
        browse_button.grid(row=0, column=2, rowspan=2, sticky=tk.NS + tk.E, padx=(5, 0), pady=2)
        file_frame.columnconfigure(1, weight=1)
        
    def check_ollama_port(self, host="localhost", port=11434, timeout=2):
        """
        Check if Ollama service port is accessible.
        Returns (is_accessible, error_message) tuple.
        """
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                return (True, None)
            else:
                return (False, f"Port {port} is not accessible")
        except socket.timeout:
            return (False, f"Connection to {host}:{port} timed out")
        except socket.gaierror:
            return (False, f"Cannot resolve hostname: {host}")
        except Exception as e:
            return (False, f"Port check error: {str(e)}")
    
    def check_ollama_health(self, host="localhost", port=11434, timeout=10):
        """
        Comprehensive health check for Ollama service.
        Returns dict with status, reason, and suggestion.
        """
        result = {
            "available": False,
            "reason": "Unknown",
            "suggestion": "Ensure Ollama is installed and running",
            "models": None
        }
        
        # Check if ollama package is installed
        try:
            import ollama
            result["package_installed"] = True
        except ImportError:
            result["package_installed"] = False
            result["reason"] = "Ollama Python package not installed"
            result["suggestion"] = "Install ollama package: pip install ollama"
            return result
        
        # Check if port is accessible
        port_accessible, port_error = self.check_ollama_port(host, port, timeout=2)
        if not port_accessible:
            result["reason"] = f"Ollama service not running: {port_error}"
            result["suggestion"] = "Start Ollama service: ollama serve"
            return result
        
        # Try to get models with retry logic
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                # Try using ollama.list() if available
                try:
                    models = ollama.list()
                    if models and 'models' in models:
                        model_names = [model.get('name', '') for model in models['models']]
                        filtered_models = [m for m in model_names if m]
                        if filtered_models:
                            result["available"] = True
                            result["models"] = filtered_models
                            result["reason"] = "Connected successfully"
                            result["suggestion"] = None
                            return result
                except Exception as e:
                    if attempt == max_retries - 1:
                        print(f"Ollama.list() failed: {str(e)}")
                
                # Fallback: Try HTTP API
                try:
                    response = requests.get(f"http://{host}:{port}/api/tags", timeout=timeout)
                    if response.status_code == 200:
                        data = response.json()
                        if 'models' in data:
                            model_names = [model.get('name', '') for model in data['models']]
                            filtered_models = [m for m in model_names if m]
                            if filtered_models:
                                result["available"] = True
                                result["models"] = filtered_models
                                result["reason"] = "Connected successfully"
                                result["suggestion"] = None
                                return result
                except requests.exceptions.ConnectionError:
                    if attempt == max_retries - 1:
                        result["reason"] = "Connection refused - Ollama service may not be running"
                        result["suggestion"] = "Start Ollama service: ollama serve"
                except requests.exceptions.Timeout:
                    if attempt == max_retries - 1:
                        result["reason"] = f"Request timed out after {timeout} seconds"
                        result["suggestion"] = "Ollama service may be slow or overloaded. Try again later."
                except requests.exceptions.HTTPError as e:
                    if attempt == max_retries - 1:
                        result["reason"] = f"HTTP error: {e.response.status_code}"
                        result["suggestion"] = "Check Ollama service status"
                except Exception as e:
                    if attempt == max_retries - 1:
                        result["reason"] = f"API error: {str(e)}"
                        result["suggestion"] = "Check Ollama installation and configuration"
                
                # Wait before retry (exponential backoff)
                if attempt < max_retries - 1:
                    time.sleep(retry_delay * (2 ** attempt))
                    
            except Exception as e:
                if attempt == max_retries - 1:
                    result["reason"] = f"Unexpected error: {str(e)}"
                    result["suggestion"] = "Check Ollama installation and logs"
        
        # If we get here, no models were found
        if result["reason"] == "Unknown":
            result["reason"] = "No models found or service not responding"
            result["suggestion"] = "Ensure Ollama is running and has models installed: ollama pull llama3"
        
        return result
    
    def detect_available_ollama_models(self):
        """
        Detect available Ollama models asynchronously.
        Returns tuple: (models_list, error_info_dict) where error_info_dict contains
        diagnostic information if models is None.
        """
        health_check = self.check_ollama_health()
        
        if health_check["available"] and health_check["models"]:
            return (health_check["models"], None)
        else:
            return (None, {
                "reason": health_check["reason"],
                "suggestion": health_check["suggestion"],
                "package_installed": health_check.get("package_installed", False)
            })
    
    def refresh_ollama_models(self):
        """Refresh the list of available Ollama models"""
        def _refresh_in_thread():
            loading = LoadingDialog(self.root, "Checking Ollama", "Detecting available models...")
            loading.show()
            
            try:
                models, error_info = self.detect_available_ollama_models()
                
                def _update_ui():
                    loading.hide()
                    if models:
                        self.available_ollama_models = models
                        current_value = self.ollama_model_var.get()
                        self.ollama_model_combobox['values'] = models
                        # Keep current selection if still available, otherwise use first
                        if current_value in models:
                            self.ollama_model_var.set(current_value)
                        else:
                            self.ollama_model_var.set(models[0] if models else "llama3.1:3b")
                        self.ollama_available = True
                        self.ollama_status_label.config(foreground="green")
                        self.ollama_status_tooltip = "Ollama status: Connected"
                        self.add_success_message(f"Found {len(models)} Ollama model(s)")
                    else:
                        self.ollama_available = False
                        self.ollama_status_label.config(foreground="red")
                        self.ollama_status_tooltip = "Ollama status: Not available"
                        
                        # Provide diagnostic and actionable error message
                        if error_info:
                            reason = error_info.get("reason", "Unknown error")
                            suggestion = error_info.get("suggestion", "")
                            package_installed = error_info.get("package_installed", False)
                            
                            if not package_installed:
                                error_msg = f"Ollama Python package not installed. {suggestion}"
                            else:
                                error_msg = f"Ollama not available: {reason}"
                                if suggestion:
                                    error_msg += f" | {suggestion}"
                            
                            self.add_error_message(error_msg)
                        else:
                            self.add_error_message("Ollama not available. Using default model list.")
                
                self.root.after(0, _update_ui)
            except Exception as e:
                def _update_ui_error():
                    loading.hide()
                    self.ollama_available = False
                    self.ollama_status_label.config(foreground="red")
                    self.ollama_status_tooltip = "Ollama status: Error"
                    error_msg = f"Error detecting Ollama models: {str(e)}"
                    self.add_error_message(error_msg)
                    print(f"Ollama detection error: {str(e)}")  # Log for debugging
                self.root.after(0, _update_ui_error)
        
        thread = threading.Thread(target=_refresh_in_thread, daemon=True)
        thread.start()
    
    def _prepare_dataset_context_for_llm(self):
        """
        Prepare dataset context summary for LLM system messages.
        Returns a formatted string with available providers, models, and statistics.
        """
        if self.df is None or self.df.empty:
            return ""
        
        try:
            # Use prepare_context_for_ollama to get structured data
            # We'll use dummy values for distance/duration since we just want the dataset summary
            context_data = prepare_context_for_ollama(
                distance=50,  # Dummy value
                duration=2,   # Dummy value
                df=self.df,
                is_weekend=False
            )
            
            historical_data = context_data.get("historical_data", {})
            if not historical_data:
                return ""
            
            # Format the dataset context
            context_lines = [
                "\n=== Available Dataset Information ===",
                "The following providers and car models are available in the dataset:",
                ""
            ]
            
            # Add provider information
            for provider, data in historical_data.items():
                context_lines.append(f"Provider: {provider}")
                if data.get("avg_cost_per_km"):
                    context_lines.append(f"  - Average cost per km: ${data['avg_cost_per_km']}")
                if data.get("avg_cost_per_hour"):
                    context_lines.append(f"  - Average cost per hour: ${data['avg_cost_per_hour']}")
                if data.get("avg_consumption_km_l"):
                    context_lines.append(f"  - Average fuel consumption: {data['avg_consumption_km_l']} km/L")
                context_lines.append(f"  - Total rentals: {data.get('total_rentals', 0)}")
                context_lines.append(f"  - Weekend rentals: {data.get('weekend_rentals', 0)}")
                
                # Add popular models
                popular_models = data.get("popular_models", {})
                if popular_models:
                    models_list = ", ".join([f"{model} ({count})" for model, count in list(popular_models.items())[:5]])
                    context_lines.append(f"  - Popular models: {models_list}")
                context_lines.append("")
            
            context_lines.append(
                "IMPORTANT: Only ask about or mention providers and car models that exist in the dataset above. "
                "When asking questions, reference the available options from this dataset."
            )
            
            return "\n".join(context_lines)
        except Exception as e:
            print(f"Error preparing dataset context: {e}")
            return ""
    
    def _call_ollama_async(self, messages, model="llama3", callback=None, fallback_message=None, show_loading=False):
        """Helper method to call Ollama asynchronously"""
        loading_positions = {"start": None, "end": None}
        
        def _show_loading():
            """Show loading indicator in chat"""
            if show_loading:
                self.chat_display.config(state=tk.NORMAL)
                loading_positions["start"] = self.chat_display.index(tk.END)
                self.chat_display.insert(tk.END, "🤖 Assistant: ", "bot_name")
                self.chat_display.insert(tk.END, "Thinking...\n\n", "bot_message")
                loading_positions["end"] = self.chat_display.index(tk.END)
                self.chat_display.config(state=tk.DISABLED)
                self.chat_display.see(tk.END)
        
        def _remove_loading():
            """Remove loading indicator from chat"""
            if show_loading and loading_positions["start"] and loading_positions["end"]:
                try:
                    self.chat_display.config(state=tk.NORMAL)
                    self.chat_display.delete(loading_positions["start"], loading_positions["end"])
                    self.chat_display.config(state=tk.DISABLED)
                except Exception as e:
                    print(f"Error removing loading indicator: {e}")
        
        def _call_in_thread():
            if show_loading:
                self.root.after(0, _show_loading)
                # Wait a bit to ensure UI updates
                time.sleep(0.1)
            
            try:
                import ollama
                response = ollama.chat(model=model, messages=messages)
                result = response["message"]["content"]
                if callback:
                    def _callback_with_cleanup(result):
                        if show_loading:
                            _remove_loading()
                        callback(result)
                    self.root.after(0, lambda: _callback_with_cleanup(result))
            except Exception as e:
                print(f"Ollama call failed: {str(e)}")
                if show_loading:
                    self.root.after(0, _remove_loading)
                if callback and fallback_message:
                    self.root.after(0, lambda: callback(fallback_message))
        
        thread = threading.Thread(target=_call_in_thread, daemon=True)
        thread.start()
    
    def _get_current_region(self):
        """Return current region for recommendations/filter (Singapore or Malaysia)."""
        if not hasattr(self, "current_region_var"):
            return "Singapore"
        r = self.current_region_var.get() or "Singapore"
        return r if r in VALID_REGIONS else "Singapore"

    def _on_region_filter_changed(self):
        """Update category dropdown and region label for the selected region."""
        region = self._get_current_region()
        providers = get_providers_for_region(region)
        self.car_cat_combo["values"] = ["All"] + providers
        self.car_cat_var.set("All")
        self._update_recommendation_region_label()

    def _update_recommendation_region_label(self):
        """Update the 'Showing recommendations for: ...' label."""
        if hasattr(self, "recommendation_region_label"):
            region = self._get_current_region()
            self.recommendation_region_label.config(text=f"Showing recommendations for: {region}")

    def _update_pref_region_label(self):
        """Update the User Preference tab region label."""
        if hasattr(self, "pref_region_label"):
            region = self.pref_region_var.get() or "Singapore"
            if region not in VALID_REGIONS:
                region = "Singapore"
            self.pref_region_label.config(text=f"Analysis and recommendations for region: {region}")

    def start_chat(self):
        """Initialize the chat conversation using Ollama for the welcome message (async)"""
        fallback_welcome = (
            "🤖 Hello! I'm your Car Rental Assistant. I can help you find the best car for your trip.\n"
            "To get started, I need to know a few details about your journey:\n\n"
            "1. When will you need the car? (e.g., 'tomorrow', 'Jan 15', 'next Monday')\n"
            "2. How far will you be traveling? (in kilometers)\n"
            "3. How long will you need the car? (in hours)\n"
            "4. How many passengers? (number of people)\n"
            "5. Any special space requirements? (e.g., 'luggage', 'cargo', 'comfortable')\n\n"
            "Let's start with when you need the car!"
        )
        
        def _on_welcome_received(welcome_message):
            self.add_bot_message(welcome_message, use_ollama=False)
            self.chat_state["waiting_for_timing"] = True
            self.chat_state["conversation_started"] = True
        
        # Try Ollama first, fallback to default message
        try:
            import ollama
            # Get dataset context
            dataset_context = self._prepare_dataset_context_for_llm()
            
            system_content = (
                "You are a helpful car rental assistant. Greet the user and ask for their rental date and time first, "
                "then distance, duration, number of passengers, and space requirements."
            )
            if dataset_context:
                system_content += "\n\n" + dataset_context
            
            self._call_ollama_async(
                messages=[{
                    "role": "system",
                    "content": system_content,
                }],
                model="llama3",
                callback=_on_welcome_received,
                fallback_message=fallback_welcome,
                show_loading=True
            )
        except:
            # If Ollama not available, use fallback immediately
            _on_welcome_received(fallback_welcome)

    def add_bot_message(self, message, use_ollama=True):
        """
        Add a bot message to the chat display and update conversation history.
        If Ollama is available and enabled, use it to generate the reply based on conversation history.
        """
        def _display_message(bot_reply):
            """Display the bot message in chat"""
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.insert(tk.END, "🤖 Assistant: ", "bot_name")
            self.chat_display.insert(tk.END, bot_reply + "\n\n", "bot_message")
            self.chat_display.config(state=tk.DISABLED)
            self.chat_display.see(tk.END)
            
            # Add to conversation history
            self.chat_state.setdefault("conversation_history", []).append(
                {"type": "bot", "message": bot_reply, "timestamp": self.get_current_time()}
            )
        
        if use_ollama:
            try:
                import ollama
                
                # Get dataset context
                dataset_context = self._prepare_dataset_context_for_llm()

                # Build conversation context for Ollama
                history = self.chat_state.get("conversation_history", [])
                system_content = (
                    "You are a helpful car rental assistant. Respond concisely and clearly. "
                    "If the user provides trip details, confirm and ask for missing info. "
                    "If the user asks for recommendations, explain that you will analyze the data. "
                    "If the user asks for help, provide a short help message."
                )
                if dataset_context:
                    system_content += "\n\n" + dataset_context
                
                ollama_messages = [
                    {
                        "role": "system",
                        "content": system_content,
                    }
                ]
                for h in history:
                    if h["type"] == "user":
                        ollama_messages.append(
                            {"role": "user", "content": h["message"]}
                        )
                    elif h["type"] == "bot":
                        ollama_messages.append(
                            {"role": "assistant", "content": h["message"]}
                        )
                # Add the new user message if not already in history
                if not history or (history and history[-1]["type"] != "user"):
                    ollama_messages.append({"role": "user", "content": message})
                
                # Use async call with loading indicator
                self._call_ollama_async(
                    messages=ollama_messages,
                    model="llama3",
                    callback=_display_message,
                    fallback_message=message,
                    show_loading=True
                )
                return  # Exit early, message will be displayed via callback
            except Exception:
                # Fallback to synchronous display
                _display_message(message)
        else:
            # Display immediately without LLM
            _display_message(message)
    
    def get_current_time(self):
        """Get current timestamp for conversation history"""
        import datetime

        return datetime.datetime.now().strftime("%H:%M:%S")

    def add_error_message(self, error_message):
        """Add an error message to the error display area"""
        if hasattr(self, "error_display"):
            self.error_display.config(state=tk.NORMAL)
            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")
            self.error_display.insert(
                tk.END, f"[{timestamp}] ❌ {error_message}\n", "error"
            )
            self.error_display.config(state=tk.DISABLED)
            self.error_display.see(tk.END)

    def clear_error_display(self):
        """Clear the error display area"""
        if hasattr(self, "error_display"):
            self.error_display.config(state=tk.NORMAL)
            self.error_display.delete(1.0, tk.END)
            self.error_display.config(state=tk.DISABLED)

    def add_success_message(self, success_message):
        """Add a success message to the error display area (in green)"""
        if hasattr(self, "error_display"):
            self.error_display.config(state=tk.NORMAL)
            from datetime import datetime

            timestamp = datetime.now().strftime("%H:%M:%S")
            original_fg = self.error_display.cget("fg")
            self.error_display.config(fg="#28a745")
            self.error_display.insert(
                tk.END, f"[{timestamp}] ✅ {success_message}\n", "success"
            )
            self.error_display.config(fg=original_fg)
            self.error_display.config(state=tk.DISABLED)
            self.error_display.see(tk.END)
        self.chat_display.see(tk.END)

    def add_user_message(self, message):
        """Add a user message to the chat display and update conversation history"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "👤 You: ", "user_name")
        self.chat_display.insert(tk.END, message + "\n\n", "user_message")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
        
        self.chat_state.setdefault("conversation_history", []).append(
            {"type": "user", "message": message, "timestamp": self.get_current_time()}
        )

    def send_message(self):
        """Handle sending a message in the chat"""
        message = self.message_var.get().strip()
        if not message:
            return

        self.add_user_message(message)
        self.message_var.set("")
        self.process_message(message)

    def process_message(self, message):
        """Process user message based on current chat state and input"""
        msg_lower = message.lower().strip()

        # Check for restart or reset commands first, regardless of state
        if any(word in msg_lower for word in ["restart", "new", "again", "reset"]):
            self.restart_conversation()
            return

        # Handle expected input states
        if self.chat_state.get("waiting_for_timing", False):
            self.handle_rental_timing_input(message)
        elif self.chat_state.get("waiting_for_distance", False):
            self.handle_distance_input(message)
        elif self.chat_state.get("waiting_for_duration", False):
            self.handle_duration_input(message)
        elif self.chat_state.get("waiting_for_passengers", False):
            self.handle_passenger_input(message)
        elif self.chat_state.get("waiting_for_space", False):
            self.handle_space_input(message)
        else:
            self.handle_contextual_response(message)

    def handle_rental_timing_input(self, message):
        """Parse rental date/time input and determine weekday/weekend"""
        from car_rental_recommender_core import determine_rental_timing
        
        # Try to parse date/time from message
        timing_result = determine_rental_timing(date_str=message)
        
        if timing_result.get("rental_date"):
            self.chat_state["rental_date"] = timing_result["rental_date"]
            self.chat_state["rental_timing"] = timing_result
            self.chat_state["waiting_for_timing"] = False
            self.chat_state["waiting_for_distance"] = True
            
            # Update weekend checkbox based on detected day
            is_weekend = timing_result.get("is_weekend", False)
            self.is_weekend_var.set(is_weekend)
            
            day_name = timing_result.get("day_name", "N/A")
            date_str = timing_result["rental_date"].strftime("%d/%m/%Y")
            
            fallback_response = (
                f"Perfect! I've noted your rental date: {date_str} ({day_name}). "
                f"{'This is a weekend, so rates may be slightly higher.' if is_weekend else 'This is a weekday.'}\n\n"
                "Now, how far will you be traveling? (in kilometers)"
            )
            
            def _on_response_received(response):
                self.add_bot_message(response, use_ollama=False)
            
            try:
                import ollama
                history = self.chat_state.get("conversation_history", [])
                ollama_messages = [{
                    "role": "system",
                    "content": (
                        "You are a helpful car rental assistant. The user just provided their rental date. "
                        "Acknowledge the date and day of week, and ask for the trip distance in kilometers."
                    ),
                }]
                for h in history:
                    if h["type"] == "user":
                        ollama_messages.append({"role": "user", "content": h["message"]})
                    elif h["type"] == "bot":
                        ollama_messages.append({"role": "assistant", "content": h["message"]})
                ollama_messages.append({"role": "user", "content": message})
                self._call_ollama_async(
                    messages=ollama_messages,
                    model="llama3",
                    callback=_on_response_received,
                    fallback_message=fallback_response
                )
            except Exception:
                _on_response_received(fallback_response)
        else:
            self.add_bot_message(
                "I couldn't understand the date. Please tell me when you need the car "
                "(e.g., 'tomorrow', 'Jan 15', 'next Monday', or '2024-01-15')."
            )

    def handle_passenger_input(self, message):
        """Parse passenger count input"""
        import re
        
        # Try to extract number from message
        patterns = [
            r"(\d+)\s*(?:passengers?|people|pax|persons?)",
            r"(\d+)\s*(?:adults?|guests?)",
            r"^(\d+)\s*$",
        ]
        
        passenger_count = None
        for pattern in patterns:
            match = re.search(pattern, message.lower())
            if match:
                passenger_count = int(match.group(1))
                break
        
        if passenger_count and passenger_count > 0:
            if passenger_count > 10:
                self.add_bot_message(
                    f"That's a large group ({passenger_count} people)! You'll likely need a van or multiple vehicles. "
                    "Please confirm this number or let me know if you meant something else."
                )
                return
            
            self.chat_state["passenger_count"] = passenger_count
            self.chat_state["waiting_for_passengers"] = False
            self.chat_state["waiting_for_space"] = True
            
            fallback_response = (
                f"Got it! {passenger_count} passenger{'s' if passenger_count > 1 else ''}. "
                "Do you have any special space requirements? "
                "(e.g., 'luggage', 'cargo', 'comfortable', 'minimal', or just say 'no' if not needed)"
            )
            
            def _on_response_received(response):
                self.add_bot_message(response, use_ollama=False)
            
            try:
                import ollama
                history = self.chat_state.get("conversation_history", [])
                ollama_messages = [{
                    "role": "system",
                    "content": (
                        "You are a helpful car rental assistant. The user just provided the number of passengers. "
                        "Acknowledge it and ask about space requirements (luggage, cargo, etc.)."
                    ),
                }]
                for h in history:
                    if h["type"] == "user":
                        ollama_messages.append({"role": "user", "content": h["message"]})
                    elif h["type"] == "bot":
                        ollama_messages.append({"role": "assistant", "content": h["message"]})
                ollama_messages.append({"role": "user", "content": message})
                self._call_ollama_async(
                    messages=ollama_messages,
                    model="llama3",
                    callback=_on_response_received,
                    fallback_message=fallback_response
                )
            except Exception:
                _on_response_received(fallback_response)
        else:
            self.add_bot_message(
                "I couldn't find the number of passengers. Please tell me how many people will be traveling "
                "(e.g., '2 passengers', '4 people', or just '3')."
            )

    def handle_space_input(self, message):
        """Parse space requirements input"""
        msg_lower = message.lower().strip()
        
        # Check if user says no space needed
        if any(word in msg_lower for word in ["no", "none", "nothing", "minimal", "not needed"]):
            space_requirements = "minimal"
        else:
            space_requirements = message.strip()
        
        self.chat_state["space_requirements"] = space_requirements
        self.chat_state["waiting_for_space"] = False
        
        fallback_response = (
            f"Perfect! I've noted your space requirements: {space_requirements}. "
            "Let me find the best car rental options for you based on all your requirements..."
        )
        
        def _on_response_received(response):
            self.add_bot_message(response, use_ollama=False)
            self.get_chat_recommendations()
        
        # All information collected, get recommendations
        try:
            import ollama
            history = self.chat_state.get("conversation_history", [])
            ollama_messages = [{
                "role": "system",
                "content": (
                    "You are a helpful car rental assistant. The user has provided all trip details. "
                    "Acknowledge the space requirements and let them know you'll find the best car options."
                ),
            }]
            for h in history:
                if h["type"] == "user":
                    ollama_messages.append({"role": "user", "content": h["message"]})
                elif h["type"] == "bot":
                    ollama_messages.append({"role": "assistant", "content": h["message"]})
            ollama_messages.append({"role": "user", "content": message})
            self._call_ollama_async(
                messages=ollama_messages,
                model="llama3",
                callback=_on_response_received,
                fallback_message=fallback_response
            )
        except Exception:
            _on_response_received(fallback_response)

    def handle_distance_input(self, message):
        """Parse user distance input, confirm, and prompt for duration."""
        import re

        patterns = [
            (r"(\d+(?:\.\d+)?)\s*(?:km|kilometers?|kms?)", "km", 1),
            (r"(\d+(?:\.\d+)?)\s*(?:miles?|mi)", "miles", 1.60934),
            (r"(\d+(?:\.\d+)?)\s*(?:minutes?|mins?)", "minutes", 1),
            (r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)", "hours", 30),
            (r"(\d+(?:\.\d+)?)", "km", 1),
        ]
        distance = value = None
        unit_type = "km"

        msg = message.lower()
        for pat, utype, factor in patterns:
            m = re.search(pat, msg)
            if m:
                value = float(m.group(1))
                if utype == "miles":
                    distance = value * factor
                elif utype == "hours":
                    distance = value * factor
                else:
                    distance = value
                unit_type = utype
                break

        if distance is not None and distance > 0:
            if distance > 1000:
                self.add_bot_message(
                    f"That's quite a long distance ({distance:.1f} km)! Are you sure? "
                    "For very long trips, you might want to consider different transportation options. "
                    "Please confirm or provide a different distance."
                )
                return
            if distance < 1:
                self.add_bot_message(
                    "That's a very short distance! For trips under 1 km, walking or cycling might be more practical. "
                    "Please provide a distance of at least 1 km, or let me know if you meant something else."
                )
                return

            self.chat_state["distance"] = distance
            self.chat_state["waiting_for_distance"] = False
            self.chat_state["waiting_for_duration"] = True

            # Build fallback response
            if unit_type != "km":
                fallback_response = f"Got it! {distance:.1f} km (from {value} {unit_type}). Now, how many hours will you need the car for?"
            else:
                fallback_response = f"Perfect! {distance} km. Now, how many hours will you need the car for?"
            if distance <= 10:
                fallback_response += "\n💡 **Short trip tip:** Perfect for local errands and quick outings!"
            elif distance <= 50:
                fallback_response += "\n🚗 **Medium trip tip:** Great for shopping, appointments, or city exploration!"
            else:
                fallback_response += "\n🌅 **Long trip tip:** Ideal for day trips, sightseeing, or visiting nearby areas!"
            
            def _on_response_received(response):
                self.add_bot_message(response, use_ollama=False)
            
            # Try Ollama for confirmation and prompt
            try:
                import ollama
                history = self.chat_state.get("conversation_history", [])
                ollama_messages = [
                    {
                        "role": "system",
                        "content": (
                            "You are a helpful car rental assistant. The user just provided their trip distance. "
                            "Acknowledge the distance, convert units if needed, and ask for the trip duration in hours."
                        ),
                    }
                ]
                for h in history:
                    if h["type"] == "user":
                        ollama_messages.append({"role": "user", "content": h["message"]})
                    elif h["type"] == "bot":
                        ollama_messages.append({"role": "assistant", "content": h["message"]})
                ollama_messages.append({"role": "user", "content": message})
                self._call_ollama_async(
                    messages=ollama_messages,
                    model="llama3",
                    callback=_on_response_received,
                    fallback_message=fallback_response
                )
            except Exception:
                _on_response_received(fallback_response)
        else:
            self.add_bot_message(
                "I couldn't find a valid distance in your message. Please tell me the distance in kilometers (e.g., '50 km', '25 miles', or just '50')."
            )
    def handle_duration_input(self, message):
        """Parse and handle duration input, confirm with Ollama or fallback, then proceed."""
        import re

        patterns = [
            (r"(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)", lambda v: (v, "hours")),
            (r"(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|m)", lambda v: (v / 60, "minutes")),
            (r"(\d+(?:\.\d+)?)\s*(?:days?|d)", lambda v: (v * 24, "days")),
            (r"^(\d+(?:\.\d+)?)\s*$", lambda v: (v, "hours")),
        ]

        duration = value = None
        unit_type = "hours"
        msg = message.lower()

        for pat, conv in patterns:
            m = re.search(pat, msg)
            if m:
                value = float(m.group(1))
                duration, unit_type = conv(value)
                break

        if duration and duration > 0:
            if duration > 72:
                self.add_bot_message(
                    f"That's a very long rental period ({duration:.1f} hours = {duration/24:.1f} days)! "
                    "For rentals longer than 3 days, you might want to consider weekly rates or different providers. "
                    "Please confirm this duration or provide a different one."
                )
                return
            if duration < 0.5:
                self.add_bot_message(
                    "That's a very short rental period! Most car rental services have minimum rental periods. "
                    "Please provide a duration of at least 30 minutes (0.5 hours), or let me know if you meant something else."
                )
                return

            self.chat_state["duration"] = duration
            self.chat_state["waiting_for_duration"] = False
            self.chat_state["waiting_for_passengers"] = True

            # Build fallback response
            if unit_type != "hours":
                fallback_response = f"Perfect! {duration:.1f} hours (from {value} {unit_type}). "
            else:
                fallback_response = f"Great! {duration} hours. "
            fallback_response += "How many passengers will be traveling?"
            if duration <= 2:
                fallback_response += "\n⏰ **Quick rental tip:** Perfect for short errands and quick trips!"
            elif duration <= 8:
                fallback_response += "\n🚗 **Half-day rental tip:** Great for shopping, appointments, or leisure activities!"
            else:
                fallback_response += "\n🌅 **Full-day rental tip:** Ideal for sightseeing, long-distance travel, or multiple stops!"
            
            def _on_response_received(response):
                self.add_bot_message(response, use_ollama=False)
            
            try:
                import ollama
                history = self.chat_state.get("conversation_history", [])
                ollama_msgs = [{
                    "role": "system",
                    "content": (
                        "You are a helpful car rental assistant. The user just provided their trip duration. "
                        "Acknowledge the duration, convert units if needed, and ask for the number of passengers."
                    ),
                }]
                for h in history:
                    role = "user" if h["type"] == "user" else "assistant"
                    ollama_msgs.append({"role": role, "content": h["message"]})
                ollama_msgs.append({"role": "user", "content": message})
                self._call_ollama_async(
                    messages=ollama_msgs,
                    model="llama3",
                    callback=_on_response_received,
                    fallback_message=fallback_response
                )
            except Exception:
                _on_response_received(fallback_response)
        else:
            self.add_bot_message(
                "I couldn't find a valid duration in your message. Please tell me the duration in hours (e.g., '2 hours', '90 minutes', or just '2')."
            )
    def handle_contextual_response(self, message):
        """
        Handle contextual responses and follow-up questions using Ollama if available.
        Fallback to manual responses if Ollama is unavailable.
        """
        msg = message.lower().strip()

        # Restart command
        if any(cmd in msg for cmd in ["restart", "new", "again", "reset"]):
            self.restart_conversation()
            return
        
        # Try Ollama for context-aware response (async)
        def _on_ollama_response(response):
            self.add_bot_message(response, use_ollama=False)
        
        def _on_fallback():
            # Fallback: manual context handling
            if self.chat_state.get("last_recommendations"):
                msg_lower = message.lower()
                if any(word in msg_lower for word in [
                    "more", "details", "compare", "comparison", "explain", "why",
                    "best", "cheaper", "expensive", "difference"
                ]):
                    self.add_bot_message(
                        "If you'd like more details or a comparison of the recommended cars, please specify which car or aspect you're interested in (e.g., 'Compare the top 2', 'Why is Car A best?', or 'Show me more details about Car B')."
                    )
                elif any(word in msg_lower for word in ["help", "how", "what can you do", "instructions"]):
                    self.add_bot_message(
                        "You can ask for car recommendations, cost comparisons, or details about specific cars. For example: 'Show me the cheapest option', 'Compare electric vs. hybrid', or 'Tell me more about Car X'."
                    )
                elif any(word in msg_lower for word in ["change", "edit", "update", "modify", "different trip"]):
                    self.add_bot_message(
                        "To update your trip details, just tell me the new distance or duration, and I'll refresh the recommendations."
                    )
                else:
                    self.add_bot_message(
                        "Let me know if you want more info, a comparison, or to change your trip details!"
                    )
            else:
                self.add_bot_message(
                    "I'm here to help! You can ask me about car rental recommendations, or start by telling me about your trip (date, distance, duration, passengers, space needs)."
                )
        
        try:
            import ollama
            # Get dataset context
            dataset_context = self._prepare_dataset_context_for_llm()
            
            # Compose conversation history for LLM
            history = self.chat_state.get("conversation_history", [])
            system_content = (
                "You are a helpful car rental assistant. "
                "The user may ask about recommendations, cost, details, comparison, help, or trip modification. "
                "Respond concisely and clearly, and refer to the recommendations panel if needed."
            )
            if dataset_context:
                system_content += "\n\n" + dataset_context
            
            ollama_msgs = [{
                "role": "system",
                "content": system_content,
            }]
            for h in history:
                if h["type"] == "user":
                    ollama_msgs.append({"role": "user", "content": h["message"]})
                elif h["type"] == "bot":
                    ollama_msgs.append({"role": "assistant", "content": h["message"]})
            ollama_msgs.append({"role": "user", "content": message})
            self._call_ollama_async(
                messages=ollama_msgs,
                model="llama3",
                callback=_on_ollama_response,
                fallback_message=None,
                show_loading=True
            )
            # Set a flag to use fallback if Ollama fails
            self.root.after(3000, _on_fallback)  # Fallback after 3 seconds if no response
            return
        except Exception:
            _on_fallback()
            return
            msg_lower = message.lower()
            if any(word in msg_lower for word in [
                "more", "details", "compare", "comparison", "explain", "why",
                "best", "cheaper", "expensive", "difference"
            ]):
                self.add_bot_message(
                    "If you'd like more details or a comparison of the recommended cars, please specify which car or aspect you're interested in (e.g., 'Compare the top 2', 'Why is Car A best?', or 'Show me more details about Car B')."
                )
            elif any(word in msg_lower for word in ["help", "how", "what can you do", "instructions"]):
                self.add_bot_message(
                    "You can ask for car recommendations, cost comparisons, or details about specific cars. For example: 'Show me the cheapest option', 'Compare electric vs. hybrid', or 'Tell me more about Car X'."
                )
            elif any(word in msg_lower for word in ["change", "edit", "update", "modify", "different trip"]):
                self.add_bot_message(
                    "To update your trip details, just tell me the new distance or duration, and I'll refresh the recommendations."
                )
            else:
                self.add_bot_message(
                    "Let me know if you want more info, a comparison, or to change your trip details!"
                )
    def get_chat_recommendations(self):
        """Get recommendations based on chat inputs asynchronously"""
        distance = self.chat_state.get("distance")
        duration = self.chat_state.get("duration")

        if distance is None or duration is None:
            self.add_bot_message(
                "❌ I need distance and duration to provide recommendations. Please provide these details first."
            )
            return

        if self.df is None or self.df.empty:
            self.add_bot_message(
                "❌ I need rental data to provide recommendations. Please load a data file first using the 'Browse...' button."
            )
            return

        def _get_recommendations_in_thread():
            loading = LoadingDialog(self.root, "Generating Recommendations", "Analyzing data and generating recommendations...")
            loading.show()
            
            try:
                # Determine weekend from rental timing or checkbox
                is_weekend = False
                if self.chat_state.get("rental_timing"):
                    is_weekend = self.chat_state["rental_timing"].get("is_weekend", False)
                else:
                    is_weekend = self.is_weekend_var.get()
                
                selected_cat = self.car_cat_var.get()
                use_ml = self.use_ml_var.get() if hasattr(self, "use_ml_var") else True
                use_ollama = (
                    self.use_ollama_var.get() if hasattr(self, "use_ollama_var") else False
                )
                ollama_model = (
                    self.ollama_model_var.get()
                    if hasattr(self, "use_ollama_var")
                    else "llama3.1:3b"
                )
                
                # Get passenger count and space requirements from settings if set, otherwise from chat state, with defaults
                passenger_count = None
                if hasattr(self, "passenger_count_var") and self.passenger_count_var.get():
                    try:
                        passenger_count = int(self.passenger_count_var.get())
                    except:
                        passenger_count = self.chat_state.get("passenger_count", 2)
                else:
                    passenger_count = self.chat_state.get("passenger_count", 2)
                
                space_requirements = None
                if hasattr(self, "space_requirements_var") and self.space_requirements_var.get().strip():
                    space_requirements = self.space_requirements_var.get().strip()
                else:
                    space_requirements = self.chat_state.get("space_requirements", "little")

                # Get enhanced recommendations (region-aware)
                region = self.current_region_var.get() if hasattr(self, "current_region_var") else "Singapore"
                if region not in VALID_REGIONS:
                    region = "Singapore"
                cost_analysis = self.cost_analysis
                if cost_analysis is None:
                    loading.update_message("Creating cost analysis...")
                    cost_analysis = create_complete_cost_analysis(self.df, region=region)

                # Load pricing config
                try:
                    with open("pricing_config.json", "r") as f:
                        pricing_config = json.load(f)
                except:
                    pricing_config = None

                loading.update_message("Generating recommendations...")
                try:
                    from car_rental_recommender_core import get_ollama_enhanced_recommendations
                    recommendations = get_ollama_enhanced_recommendations(
                        distance,
                        duration,
                        self.df,
                        cost_analysis,
                        is_weekend,
                        top_n=10,
                        use_ollama=use_ollama,
                        ollama_model=ollama_model,
                        use_ml=use_ml,
                        passenger_count=passenger_count,
                        space_requirements=space_requirements,
                        rental_timing=self.chat_state.get("rental_timing"),
                        pricing_config=pricing_config
                    )
                    print(f"Generated {len(recommendations)} recommendations")
                except Exception as e:
                    error_msg = f"Ollama LLM is not available: {str(e)}"
                    print(f"Recommendation error: {error_msg}")
                    if use_ollama:
                        # Fallback without Ollama
                        recommendations = get_ollama_enhanced_recommendations(
                            distance,
                            duration,
                            self.df,
                            cost_analysis,
                            is_weekend,
                            top_n=10,
                            use_ollama=False,
                            ollama_model=ollama_model,
                            use_ml=use_ml,
                            passenger_count=passenger_count,
                            space_requirements=space_requirements,
                            rental_timing=self.chat_state.get("rental_timing"),
                            pricing_config=pricing_config
                        )
                    else:
                        raise e

                # Filter recommendations by selected category if not "All"
                if selected_cat != "All":
                    recommendations = [
                        rec for rec in recommendations if rec["provider"] == selected_cat
                    ]

                def _update_ui():
                    loading.hide()
                    # Update cost_analysis if it was created
                    if self.cost_analysis is None:
                        self.cost_analysis = cost_analysis
                    
                    # Display recommendations in chat
                    self.display_chat_recommendations(recommendations, distance, duration)

                    # Update the results treeview
                    self.update_results_tree(recommendations)

                    # Show comparison chart
                    self.show_recommendation_chart(recommendations)

                    # Show success message
                    success_msg = f"Generated {len(recommendations)} recommendations for {distance} km, {duration} hours"
                    self.add_success_message(success_msg)
                
                self.root.after(0, _update_ui)

            except Exception as e:
                def _update_ui_error():
                    loading.hide()
                    error_msg = f"An error occurred while getting recommendations: {str(e)}"
                    self.add_error_message(error_msg)
                    self.add_bot_message(f"❌ {error_msg}")
                self.root.after(0, _update_ui_error)
        
        thread = threading.Thread(target=_get_recommendations_in_thread, daemon=True)
        thread.start()

    def display_chat_recommendations(self, recommendations, distance, duration):
        """Display recommendations in the chat interface, using Ollama for summary if available."""
        if not recommendations:
            self.add_bot_message(
                "❌ Sorry, I couldn't find any suitable car rental options for your trip details."
            )
            return

        best = recommendations[0]
        model = best.get("model", "Unknown Model")
        provider = best.get("provider", "Unknown Provider")
        total_cost = best.get("total_cost", 0.0)
        method = best.get("method", "Standard")
        confidence = best.get("confidence", None)
        reasoning = best.get("reasoning", "")
        size_suitability = best.get("size_suitability")
        pricing_comparison = best.get("pricing_comparison", {})

        cost_per_km = total_cost / distance if distance > 0 else 0
        cost_per_hour = total_cost / duration if duration > 0 else 0

        # Try Ollama summary
        summary = None
        try:
            import ollama
            ollama_helper = OllamaHelper(ollama_model="llama3", use_ml=False)
            # Compose prompt
            prompt = (
                f"You are a helpful car rental assistant. "
                f"Summarize the following best car rental recommendation for a user in a concise, friendly, and informative way. "
                f"Highlight the car model, provider, total cost, cost per km and per hour, analysis method, confidence, and a short reason. "
                f"Add a tip based on duration and a cost context. "
                f"User trip: {distance} km, {duration} hours.\n"
                f"Best Recommendation:\n"
                f"Model: {model}\n"
                f"Provider: {provider}\n"
                f"Total Cost: ${total_cost:.2f}\n"
                f"Cost per km: ${cost_per_km:.2f}\n"
                f"Cost per hour: ${cost_per_hour:.2f}\n"
                f"Method: {method}\n"
                f"Confidence: {confidence if confidence is not None else 'N/A'}\n"
                f"Reasoning: {reasoning}\n"
                f"Number of options: {len(recommendations)}"
            )
            # Optionally add chat history for context
            history = self.chat_state.get("conversation_history", [])
            ollama_msgs = [{"role": "system", "content": "You are a helpful car rental assistant."}]
            for h in history:
                if h["type"] == "user":
                    ollama_msgs.append({"role": "user", "content": h["message"]})
                elif h["type"] == "bot":
                    ollama_msgs.append({"role": "assistant", "content": h["message"]})
            ollama_msgs.append({"role": "user", "content": prompt})
            summary = ollama.chat(model="llama3", messages=ollama_msgs)["message"]["content"]
        except Exception:
            pass

        # Initialize lines - either from Ollama summary or build from scratch
        if summary:
            # Use Ollama summary as base, convert to list for appending
            lines = [summary]
        else:
            # Fallback summary
            lines = [
                f"🎯 **Best Recommendation for {distance} km, {duration} hours:**\n",
                f"🚗 **{model}** ({provider})",
                f"💰 **Total Cost:** ${total_cost:.2f}",
                f"📊 **Cost Breakdown:** ${cost_per_km:.2f}/km, ${cost_per_hour:.2f}/hour",
                f"🔬 **Analysis Method:** {method}",
            ]
            if confidence is not None:
                emoji = "🟢" if confidence >= 0.8 else "🟡" if confidence >= 0.6 else "🔴"
                lines.append(f"{emoji} **Confidence:** {confidence:.1%}")
        
        # Add passenger and space info if available
        if self.chat_state.get("passenger_count"):
            lines.append(f"👥 **Passengers:** {self.chat_state['passenger_count']}")
        if self.chat_state.get("space_requirements"):
            lines.append(f"📦 **Space needs:** {self.chat_state['space_requirements']}")
        
        # Add size suitability if available
        if size_suitability is not None:
            size_emoji = "🟢" if size_suitability >= 0.8 else "🟡" if size_suitability >= 0.6 else "🔴"
            lines.append(f"{size_emoji} **Size suitability:** {size_suitability:.0%}")
        
        # Add pricing model recommendation
        if pricing_comparison:
            recommended_model = pricing_comparison.get("recommended_model", "")
            if recommended_model:
                model_text = "Mileage-included" if recommended_model == "mileage_included" else "Pay-per-km"
                lines.append(f"💳 **Pricing model:** {model_text} recommended for this trip")
        
        if reasoning:
            display_reasoning = (reasoning[:150] + "...") if len(reasoning) > 150 else reasoning
            lines.append(f"💡 **Why this car:** {display_reasoning}")
        if duration <= 2:
            lines.append("⏰ **Quick trip tip:** Perfect for short errands or quick outings!")
        elif duration <= 6:
            lines.append("🚗 **Half-day trip:** Great for shopping, appointments, or leisure activities!")
        else:
            lines.append("🌅 **Full-day adventure:** Ideal for sightseeing, long-distance travel, or multiple stops!")
        if total_cost < 25:
            lines.append("💵 **Budget-friendly:** Excellent value for money!")
        elif total_cost < 40:
            lines.append("⚖️ **Balanced option:** Good mix of cost and convenience!")
        else:
            lines.append("⭐ **Premium choice:** Higher cost but maximum comfort and features!")
        lines.append(f"\n📋 I found {len(recommendations)} total options. Check the recommendations panel on the right for the full list!")
        lines.append("💬 You can say 'restart' to get recommendations for a different trip, or ask me anything else!")
        final_summary = "\n".join(lines)

        self.add_bot_message(final_summary)
        # Store recommendations for context
        self.chat_state["last_recommendations"] = recommendations
        self.chat_state["trip_context"] = {
            "distance": distance,
            "duration": duration,
            "timestamp": self.get_current_time(),
        }
    def update_results_tree(self, recommendations):
        """Update the results treeview with new recommendations"""
        # Clear previous results
        for i in self.results_tree.get_children():
            self.results_tree.delete(i)

        # Display recommendations in treeview
        for i, rec in enumerate(recommendations):
            provider = rec["provider"]
            car_model = rec["model"]
            cost = f"${rec['total_cost']:.2f}"
            method = rec.get("method", "Standard")
            confidence = f"{rec.get('confidence', 0.8):.1%}"
            size_info = rec.get("inferred_size", "N/A")
            if rec.get("size_suitability"):
                size_info += f" ({rec['size_suitability']:.0%})"
            pricing_model = rec.get("pricing_model", "N/A")
            reasoning = rec.get("reasoning", "")

            # Truncate reasoning for display
            if method == "Ollama Analysis":
                display_reasoning = (
                    reasoning[:100] + "..." if len(reasoning) > 100 else reasoning
                )
            else:
                display_reasoning = (
                    reasoning[:50] + "..." if len(reasoning) > 50 else reasoning
                )

            # Add to treeview with tags for coloring
            tag = "best" if i == 0 else ""
            if method == "Ollama Analysis":
                tag = "ollama" if tag == "" else "ollama_best"
            elif method == "ML Prediction":
                tag = "ml" if tag == "" else "ml_best"
            elif method == "Historical Analysis":
                tag = "historical" if tag == "" else "historical_best"

            # Store the full reasoning in the item for later retrieval
            item_id = self.results_tree.insert(
                "",
                tk.END,
                values=(
                    provider,
                    car_model,
                    cost,
                    method,
                    confidence,
                    size_info,
                    pricing_model,
                    display_reasoning,
                    reasoning,
                ),
                tags=(tag,),
            )

        # Configure tags for different recommendation types
        self.results_tree.tag_configure("best", background="#e6ffe6")
        self.results_tree.tag_configure("ollama", background="#e6ffe6")
        self.results_tree.tag_configure("ollama_best", background="#b3ffb3")
        self.results_tree.tag_configure("ml", background="#e6f3ff")
        self.results_tree.tag_configure("ml_best", background="#b3d9ff")
        self.results_tree.tag_configure("historical", background="#fff2e6")
        self.results_tree.tag_configure("historical_best", background="#ffd9b3")

        # Update status
        distance = self.chat_state["distance"]
        duration = self.chat_state["duration"]
        ollama_count = sum(
            1 for rec in recommendations if rec.get("method") == "Ollama Analysis"
        )
        ml_count = sum(
            1 for rec in recommendations if rec.get("method") == "ML Prediction"
        )
        historical_count = sum(
            1 for rec in recommendations if rec.get("method") == "Historical Analysis"
        )
        fallback_count = sum(
            1 for r in recommendations if "Fallback" in r.get("method", "")
        )

        if fallback_count > 0:
            status_msg = f"Found {len(recommendations)} recommendations for {distance} km and {duration} hours ({fallback_count} intelligent fallback, {ml_count} ML, {historical_count} historical)"
        elif ollama_count > 0 or ml_count > 0:
            status_msg = f"Found {len(recommendations)} recommendations for {distance} km and {duration} hours ({ollama_count} personalized AI, {ml_count} ML, {historical_count} historical)"
        else:
            status_msg = f"Found {len(recommendations)} recommendations for {distance} km and {duration} hours"
        self.status_var.set(status_msg)

    def restart_conversation(self):
        """Restart the chat conversation"""
        # Clear conversation history but keep the structure
        self.chat_state = {
            "waiting_for_distance": False,
            "waiting_for_duration": False,
            "distance": None,
            "duration": None,
            "conversation_started": False,
            "conversation_history": [],
            "last_recommendations": None,
            "user_preferences": {},
            "trip_context": {},
        }

        self.add_bot_message(
            "🔄 Starting fresh! Let's get your new trip details.\n\nHow far will you be traveling? (in kilometers)"
        )
        self.chat_state["waiting_for_distance"] = True
        self.chat_state["conversation_started"] = True

    def setup_data_analysis_tab(self):
        """Set up the data analysis tab with useful visualizations"""

        def add_radiobuttons(parent, items, variable, command, padx=20, pady=2):
            """Helper to add a group of radiobuttons to a parent frame."""
            for text, value in items:
                ttk.Radiobutton(
                    parent,
                    text=text,
                    value=value,
                    variable=variable,
                    command=command,
                ).pack(anchor=tk.W, padx=padx, pady=pady)

        def add_button(parent, text, command, style=None, padx=5, pady=5):
            """Helper to add a button to a parent frame."""
            kwargs = {"text": text, "command": command}
            if style:
                kwargs["style"] = style
            ttk.Button(parent, **kwargs).pack(padx=padx, pady=pady)

        # Main container
        main_frame = ttk.Frame(self.data_analysis_tab)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left panel for options
        left_panel = ttk.LabelFrame(
            main_frame, text="Analysis Options", padding=(10, 5)
        )
        left_panel.pack(side=tk.LEFT, fill=tk.Y, expand=False, padx=(0, 5), pady=5)

        # Analysis type selection
        ttk.Label(left_panel, text="Select Analysis:").pack(anchor=tk.W, padx=5, pady=5)

        self.analysis_var = tk.StringVar(value="provider_comparison")
        self.analyses = [
            ("Provider Comparison", "provider_comparison"),
            ("Cost Trends", "cost_trends"),
            ("Car Models", "car_models"),
            ("Car Categories", "car_categories"),
            ("Monthly Summary", "monthly_summary"),
            ("Fuel Efficiency", "fuel_efficiency"),
            ("Weekend vs Weekday", "weekend_weekday"),
            ("Distance vs Cost", "distance_cost"),
            ("Electric vs Traditional", "electric_vs_traditional"),
            ("Cost Efficiency", "cost_efficiency"),
            ("Seasonal Patterns", "seasonal_patterns"),
            ("Usage Patterns", "usage_patterns"),
        ]
        add_radiobuttons(
            left_panel, self.analyses, self.analysis_var, self.update_analysis_chart
        )

        # Region indicator (data filtered by region from Recommendations filter)
        ttk.Separator(left_panel, orient="horizontal").pack(fill=tk.X, padx=5, pady=10)
        self.analysis_region_label = ttk.Label(
            left_panel,
            text="Data for region: " + (self._get_current_region() if hasattr(self, "current_region_var") else "Singapore"),
            font=("Segoe UI", 9),
        )
        self.analysis_region_label.pack(anchor=tk.W, padx=5, pady=2)

        # Period selection
        ttk.Separator(left_panel, orient="horizontal").pack(fill=tk.X, padx=5, pady=10)
        ttk.Label(left_panel, text="Time Period:").pack(anchor=tk.W, padx=5, pady=5)

        self.period_var = tk.StringVar(value="all")
        self.periods = [
            ("All Data", "all"),
            ("This Year", "this_year"),
            ("Last 6 Months", "last_6_months"),
            ("Last 3 Months", "last_3_months"),
            ("Last Month", "last_month"),
            ("This Month", "this_month"),
        ]
        add_radiobuttons(
            left_panel, self.periods, self.period_var, self.update_analysis_chart
        )

        # Run analysis button
        add_button(
            left_panel,
            text="Run Analysis",
            command=self.update_analysis_chart,
            style="Accent.TButton",
            pady=15,
        )

        # Refresh button
        add_button(
            left_panel,
            text="🔄 Refresh Data",
            command=self.refresh_analysis_data,
        )

        # Export data button
        add_button(
            left_panel,
            text="Export Results",
            command=self.export_analysis_results,
        )

        # Right panel for results and charts
        right_panel = ttk.Frame(main_frame)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

        # Stats summary frame
        self.stats_frame = ttk.LabelFrame(
            right_panel, text="Key Statistics", padding=(10, 5)
        )
        self.stats_frame.pack(fill=tk.X, expand=False, padx=5, pady=5)

        # Create grid for statistics (single column layout for rows)
        self.stats_grid = ttk.Frame(self.stats_frame)
        self.stats_grid.pack(fill=tk.X, expand=True, padx=5, pady=5)
        self.stats_grid.columnconfigure(0, weight=1)  # Allow the column to expand

        # Initialize stats labels (will be populated when analysis runs)
        self.stats_labels = []

        # Chart frame
        self.analysis_chart_frame = ttk.LabelFrame(
            right_panel, text="Analysis Chart", padding=(10, 5)
        )
        self.analysis_chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create a figure and canvas for the chart
        self.analysis_fig, self.analysis_ax = plt.subplots(figsize=(10, 6), dpi=100)
        self.analysis_canvas = FigureCanvasTkAgg(
            self.analysis_fig, master=self.analysis_chart_frame
        )
        self.analysis_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Add navigation toolbar for better chart interaction
        self.analysis_toolbar = NavigationToolbar2Tk(
            self.analysis_canvas, self.analysis_chart_frame
        )
        self.analysis_toolbar.update()
        self.analysis_toolbar.pack(fill=tk.X)

    def update_analysis_chart(self):
        """Update the analysis chart based on selected options"""
        if not self._check_data_loaded():
            return

        # Update region label (data is filtered by this region)
        if hasattr(self, "analysis_region_label"):
            self.analysis_region_label.config(text="Data for region: " + self._get_current_region())

        # Clear previous stats and chart
        self.analysis_fig.clear()  # Clear the entire figure
        self.analysis_ax = self.analysis_fig.add_subplot(111)  # Recreate the main axis
        for label in self.stats_labels:
            label.destroy()
        self.stats_labels = []

        # Get selected options
        analysis_type = self.analysis_var.get()
        period = self.period_var.get()

        # Filter data by time period
        filtered_df = self.filter_data_by_period(period)
        # Restrict to current region so Singapore and Malaysia are not mixed
        if not filtered_df.empty and "Region" in filtered_df.columns:
            filtered_df = filtered_df[filtered_df["Region"] == self._get_current_region()].copy()

        if filtered_df.empty:
            # Show empty state on chart
            self.analysis_ax.text(
                0.5, 0.5,
                "No data available\nfor the selected period",
                ha="center", va="center",
                transform=self.analysis_ax.transAxes,
                fontsize=14,
                color="gray",
            )
            self.analysis_fig.tight_layout()
            self.analysis_canvas.draw()
            self.status_var.set("No data available for selected period")
            return

        try:
            # Perform the selected analysis
            if analysis_type == "provider_comparison":
                self.show_provider_comparison(filtered_df)
            elif analysis_type == "cost_trends":
                self.show_cost_trends(filtered_df)
            elif analysis_type == "car_models":
                self.show_car_models_analysis(filtered_df)
            elif analysis_type == "car_categories":
                self.show_car_categories_analysis(filtered_df)
            elif analysis_type == "monthly_summary":
                self.show_monthly_summary(filtered_df)
            elif analysis_type == "fuel_efficiency":
                self.show_fuel_efficiency_analysis(filtered_df)
            elif analysis_type == "weekend_weekday":
                self.show_weekend_weekday_analysis(filtered_df)
            elif analysis_type == "distance_cost":
                self.show_distance_cost_analysis(filtered_df)
            elif analysis_type == "electric_vs_traditional":
                self.show_electric_vs_traditional_analysis(filtered_df)
            elif analysis_type == "cost_efficiency":
                self.show_cost_efficiency_analysis(filtered_df)
            elif analysis_type == "seasonal_patterns":
                self.show_seasonal_patterns_analysis(filtered_df)
            elif analysis_type == "usage_patterns":
                self.show_usage_patterns_analysis(filtered_df)

            # Convert analysis type and period to their display names
            analysis_name = {v: k for k, v in self.analyses}[analysis_type]
            period_name = {v: k for k, v in self.periods}[period]

            # Update status
            self.status_var.set(
                f"Analysis completed: {analysis_name} for {period_name}"
            )
        except Exception as e:
            messagebox.showerror(
                "Analysis Error", f"An error occurred during analysis: {str(e)}"
            )
            self.status_var.set("Analysis failed. See error message.")
            # Clear the chart on error
            self.analysis_fig.clear()
            self.analysis_ax = self.analysis_fig.add_subplot(111)
            self.analysis_ax.text(
                0.5,
                0.5,
                "Analysis failed\nPlease check your data",
                ha="center",
                va="center",
                transform=self.analysis_ax.transAxes,
                fontsize=12,
                color="red",
            )
            self.analysis_fig.tight_layout()
            self.analysis_canvas.draw()

    def filter_data_by_period(self, period):
        """Filter dataframe by time period"""
        if period == "all" or "Date" not in self.df.columns:
            return self.df.copy()

        # Ensure Date column is datetime
        df_copy = self.df.copy()
        if not pd.api.types.is_datetime64_dtype(df_copy["Date"]):
            try:
                df_copy["Date"] = pd.to_datetime(df_copy["Date"])
            except:
                return df_copy  # Return unfiltered if conversion fails

        now = pd.Timestamp.now()

        if period == "last_3_months":
            start_date = now - pd.DateOffset(months=3)
            return df_copy[df_copy["Date"] >= start_date]

        elif period == "last_6_months":
            start_date = now - pd.DateOffset(months=6)
            return df_copy[df_copy["Date"] >= start_date]

        elif period == "this_year":
            start_date = pd.Timestamp(now.year, 1, 1)
            return df_copy[df_copy["Date"] >= start_date]

        elif period == "last_month":
            start_date = now - pd.DateOffset(months=1)
            return df_copy[df_copy["Date"] >= start_date]

        elif period == "this_month":
            start_date = pd.Timestamp(now.year, now.month, 1)
            return df_copy[df_copy["Date"] >= start_date]
        return df_copy

    def show_provider_comparison(self, df):
        """Show comparison between different providers"""
        # Check if provider column exists
        if "Car Cat" not in df.columns:
            messagebox.showwarning("Missing Data", "Provider information is missing")
            return

        # Group by provider
        provider_stats = (
            df.groupby("Car Cat")
            .agg(
                {
                    "Total": ["mean", "count", "sum"],
                    "Distance (KM)": ["sum", "mean"],
                    "Rental hour": ["sum", "mean"],
                    "Cost per KM": ["mean"],
                    "Cost/HR": ["mean"],
                }
            )
            .reset_index()
        )

        # Flatten multi-index columns
        provider_stats.columns = [
            "_".join(col).strip("_") for col in provider_stats.columns.values
        ]

        # Display key statistics
        self.add_stat("Total Trips", f"{len(df)}")
        self.add_stat("Total Spending", f"${df['Total'].sum():.2f}")
        self.add_stat("Average Cost per Trip", f"${df['Total'].mean():.2f}")
        self.add_stat("Total Distance", f"{df['Distance (KM)'].sum():.1f} km")
        self.add_stat("Total Rental Hours", f"{df['Rental hour'].sum():.1f} hrs")

        # Create bar chart comparing providers
        providers = provider_stats["Car Cat"].tolist()
        avg_costs = provider_stats["Total_mean"].tolist()
        trip_counts = provider_stats["Total_count"].tolist()

        # Clear the axis and plot average cost by provider
        self.analysis_ax.clear()
        bars = self.analysis_ax.bar(
            providers, avg_costs, width=0.6, color="#4a6984", alpha=0.7
        )

        # Add trip count as text
        for i, (bar, count) in enumerate(zip(bars, trip_counts)):
            height = bar.get_height()
            self.analysis_ax.text(
                bar.get_x() + bar.get_width() / 2,
                height + 0.5,
                f"{count} trips",
                ha="center",
                va="bottom",
                color="black",
                fontsize=9,
            )

        # Add data labels
        for bar in bars:
            height = bar.get_height()
            self.analysis_ax.text(
                bar.get_x() + bar.get_width() / 2,
                height / 2,
                f"${height:.2f}",
                ha="center",
                va="center",
                color="white",
                fontsize=9,
                fontweight="bold",
            )

        # Set chart properties
        self.analysis_ax.set_title("Average Cost by Provider", fontsize=12)
        self.analysis_ax.set_ylabel("Average Cost ($)", fontsize=10)
        self.analysis_ax.set_ylim(0, max(avg_costs) * 1.2 if len(avg_costs) > 0 else 10)
        self.analysis_ax.grid(axis="y", linestyle="--", alpha=0.3)

        # Update chart
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def show_cost_trends(self, df):
        """Show cost trends over time"""
        if "Date" not in df.columns or "Total" not in df.columns:
            messagebox.showwarning(
                "Missing Data", "Date or cost information is missing"
            )
            return

        # Ensure we have datetime data
        df_copy = df.copy()
        if not pd.api.types.is_datetime64_dtype(df_copy["Date"]):
            try:
                df_copy["Date"] = pd.to_datetime(df_copy["Date"])
            except:
                messagebox.showwarning("Data Error", "Could not parse dates correctly")
                return

        # Add month and year columns if not already present
        if "Month" not in df_copy.columns:
            df_copy["Month"] = df_copy["Date"].dt.month
        if "Year" not in df_copy.columns:
            df_copy["Year"] = df_copy["Date"].dt.year

        # Create Month-Year column for grouping
        df_copy["Month-Year"] = df_copy["Date"].dt.strftime("%b %Y")

        # Group by month and calculate average costs
        monthly_avg = (
            df_copy.groupby("Month-Year")
            .agg(
                {
                    "Total": "mean",
                    "Cost per KM": "mean",
                    "Cost/HR": "mean",
                    "Distance (KM)": "mean",
                    "Date": "first",  # Keep one date per month for sorting
                }
            )
            .reset_index()
        )

        # Sort by date
        monthly_avg = monthly_avg.sort_values("Date")

        # Display key statistics
        if not monthly_avg.empty:
            min_month = monthly_avg.loc[monthly_avg["Total"].idxmin(), "Month-Year"]
            max_month = monthly_avg.loc[monthly_avg["Total"].idxmax(), "Month-Year"]

            min_cost = monthly_avg["Total"].min()
            max_cost = monthly_avg["Total"].max()
            avg_cost = df_copy["Total"].mean()

            self.add_stat("Average Trip Cost", f"${avg_cost:.2f}")
            self.add_stat("Lowest Month", f"{min_month} (${min_cost:.2f})")
            self.add_stat("Highest Month", f"{max_month} (${max_cost:.2f})")

            first_month = monthly_avg["Month-Year"].iloc[0]
            last_month = monthly_avg["Month-Year"].iloc[-1]
            self.add_stat("Period", f"{first_month} to {last_month}")

        # Plot the trend
        months = monthly_avg["Month-Year"].tolist()
        avg_total = monthly_avg["Total"].tolist()
        avg_per_km = (
            monthly_avg["Cost per KM"].tolist()
            if "Cost per KM" in monthly_avg.columns
            else []
        )
        avg_per_hour = (
            monthly_avg["Cost/HR"].tolist() if "Cost/HR" in monthly_avg.columns else []
        )

        # Clear the axis and plot primary axis: Average total cost
        self.analysis_ax.clear()
        self.analysis_ax.plot(
            months,
            avg_total,
            marker="o",
            linestyle="-",
            color="#4a6984",
            linewidth=2,
            markersize=6,
            label="Avg Total Cost",
        )

        # Plot on the same axis if we have per km and per hour costs
        if avg_per_km and not all(pd.isna(avg_per_km)):
            self.analysis_ax.plot(
                months,
                avg_per_km,
                marker="s",
                linestyle="--",
                color="#e67e22",
                linewidth=2,
                markersize=5,
                label="Avg Cost per KM",
            )

        if avg_per_hour and not all(pd.isna(avg_per_hour)):
            self.analysis_ax.plot(
                months,
                avg_per_hour,
                marker="^",
                linestyle="-.",
                color="#27ae60",
                linewidth=2,
                markersize=5,
                label="Avg Cost per Hour",
            )

        # Set chart properties
        self.analysis_ax.set_title("Average Rental Costs Over Time", fontsize=12)
        self.analysis_ax.set_ylabel("Cost ($)", fontsize=10)
        self.analysis_ax.set_xticks(range(len(months)))
        self.analysis_ax.set_xticklabels(months, rotation=45, ha="right", fontsize=9)
        self.analysis_ax.grid(True, linestyle="--", alpha=0.3)

        # Add legend
        self.analysis_ax.legend()

        # Add data labels for total cost
        for i, (x, y) in enumerate(zip(range(len(months)), avg_total)):
            self.analysis_ax.annotate(
                f"${y:.2f}",
                (x, y),
                xytext=(0, 5),
                textcoords="offset points",
                ha="center",
                fontsize=8,
            )

        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def add_stat(self, label, value):
        """Add a statistic to the stats grid (displayed in rows)"""
        row = len(self.stats_labels) // 2  # Each stat uses 2 widgets (label and value)

        # Create a frame for this statistic (horizontal layout)
        frame = ttk.Frame(self.stats_grid)
        frame.grid(row=row, column=0, padx=10, pady=3, sticky=tk.W + tk.E)
        frame.columnconfigure(1, weight=1)  # Allow value column to expand

        # Add label and value side by side
        label_widget = ttk.Label(frame, text=f"{label}:", font=("Segoe UI", 9))
        label_widget.grid(row=0, column=0, padx=(0, 10), sticky=tk.W)

        value_widget = ttk.Label(frame, text=value, font=("Segoe UI", 10, "bold"))
        value_widget.grid(row=0, column=1, sticky=tk.W)

        # Store references to labels for later cleanup
        self.stats_labels.extend([frame, label_widget, value_widget])

    def export_analysis_results(self):
        """Export analysis results to CSV"""
        if not self._check_data_loaded():
            return

        # Ask for file location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx"),
                ("All files", "*.*"),
            ],
            title="Export Analysis Results",
        )

        if not file_path:
            return  # User cancelled

        try:
            # Get current analysis settings
            analysis_type = self.analysis_var.get()
            period = self.period_var.get()

            # Filter data
            filtered_df = self.filter_data_by_period(period)

            # Create a summary DataFrame
            if analysis_type == "provider_comparison":
                # Group by provider
                result_df = (
                    filtered_df.groupby("Car Cat")
                    .agg(
                        {
                            "Total": ["mean", "count", "sum"],
                            "Distance (KM)": ["sum", "mean"],
                            "Rental hour": ["sum", "mean"],
                            "Cost per KM": ["mean"],
                            "Cost/HR": ["mean"],
                        }
                    )
                    .reset_index()
                )

                # Flatten multi-index columns
                result_df.columns = [
                    "_".join(col).strip("_") for col in result_df.columns.values
                ]

            elif analysis_type == "cost_trends":
                # Ensure Date column is datetime
                df_copy = filtered_df.copy()
                df_copy["Date"] = pd.to_datetime(df_copy["Date"])

                # Extract month-year for grouping
                df_copy["Month"] = df_copy["Date"].dt.to_period("M")

                # Group by month
                result_df = (
                    df_copy.groupby("Month")
                    .agg(
                        {
                            "Total": ["mean", "sum", "count"],
                            "Distance (KM)": ["sum"],
                            "Rental hour": ["sum"],
                        }
                    )
                    .reset_index()
                )

                # Flatten multi-index columns
                result_df.columns = [
                    "_".join(col).strip("_") for col in result_df.columns.values
                ]

            elif analysis_type == "car_categories":
                # Group by car category
                result_df = (
                    filtered_df.groupby("Car Cat")
                    .agg(
                        {
                            "Total": ["mean", "count", "sum"],
                            "Distance (KM)": ["sum", "mean"],
                            "Rental hour": ["sum", "mean"],
                            "Cost per KM": ["mean"],
                            "Cost/HR": ["mean"],
                            "Consumption (KM/L)": ["mean"],
                        }
                    )
                    .reset_index()
                )

                # Flatten multi-index columns
                result_df.columns = [
                    "_".join(col).strip("_") for col in result_df.columns.values
                ]

            else:
                # For other analyses, just export the filtered data
                result_df = filtered_df

            # Save to file
            if file_path.endswith(".xlsx"):
                result_df.to_excel(file_path, index=False)
            else:
                result_df.to_csv(file_path, index=False)

            messagebox.showinfo(
                "Export Complete", f"Data exported successfully to {file_path}"
            )

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export data: {str(e)}")

    def setup_settings_tab(self):
        def add_labeled_entry(
            parent,
            label_text,
            var,
            row,
            col,
            width=10,
            entry_kwargs=None,
            label_kwargs=None,
            **grid_kwargs,
        ):
            """Helper to add a label and entry to a grid row/col."""
            if label_kwargs is None:
                label_kwargs = {}
            if entry_kwargs is None:
                entry_kwargs = {}
            ttk.Label(parent, text=label_text, **label_kwargs).grid(
                row=row, column=col, padx=5, pady=5, sticky="w", **grid_kwargs
            )
            entry = ttk.Entry(parent, textvariable=var, width=width, **entry_kwargs)
            entry.grid(
                row=row, column=col + 1, padx=5, pady=5, sticky="w", **grid_kwargs
            )
            return entry

        def add_button(parent, text, command, row, col, style=None, **grid_kwargs):
            kwargs = {"text": text, "command": command}
            if style:
                kwargs["style"] = style
            btn = ttk.Button(parent, **kwargs)
            btn.grid(row=row, column=col, padx=5, pady=5, sticky="w", **grid_kwargs)
            return btn

        # Combined Data Settings and Upload frame
        data_frame = ttk.LabelFrame(self.settings_tab, text="Data Settings & Upload")
        data_frame.pack(fill="x", expand=False, padx=10, pady=10, ipadx=10, ipady=10)

        # Data file row
        ttk.Label(data_frame, text="Data File:").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self.data_file_var = tk.StringVar(value="22 - Sheet1.csv")
        ttk.Entry(data_frame, textvariable=self.data_file_var, width=40).grid(
            row=0, column=1, padx=5, pady=5, sticky="w"
        )
        add_button(data_frame, "Browse", self.browse_file, row=0, col=2)
        add_button(data_frame, "Load Data", self.load_data_action, row=0, col=3)
        add_button(data_frame, "Data quality report", self.show_data_quality_report, row=0, col=4)

        # Divider
        ttk.Separator(data_frame, orient="horizontal").grid(
            row=1, column=0, columnspan=4, sticky="ew", pady=(5, 5)
        )

        # Upload file selection
        ttk.Label(data_frame, text="📄 Select File:").grid(
            row=2, column=0, padx=5, pady=5, sticky="w"
        )
        self.upload_file_var = tk.StringVar()
        ttk.Entry(
            data_frame, textvariable=self.upload_file_var, width=40, state="readonly"
        ).grid(row=2, column=1, padx=5, pady=5, sticky="w")
        add_button(data_frame, "Browse", self.browse_upload_file, row=2, col=2)

        # Upload mode selection
        ttk.Label(data_frame, text="📋 Upload Mode:").grid(
            row=3, column=0, padx=5, pady=5, sticky="w"
        )
        self.upload_mode_var = tk.StringVar(value="replace")
        upload_mode_combo = ttk.Combobox(
            data_frame,
            textvariable=self.upload_mode_var,
            values=["Replace Current Data", "Add to Current Data"],
            width=25,
            state="readonly",
        )
        upload_mode_combo.grid(row=3, column=1, padx=5, pady=5, sticky="w")
        add_button(
            data_frame,
            "📤 Upload File",
            self.upload_file_action,
            row=3,
            col=2,
            style="Accent.TButton",
        )
        add_button(
            data_frame,
            "👁️ Preview",
            self.preview_upload_file,
            row=4,
            col=2,
        )

        # Upload status
        self.upload_status_var = tk.StringVar(value="No file selected")
        ttk.Label(
            data_frame, textvariable=self.upload_status_var, foreground="gray"
        ).grid(row=5, column=0, columnspan=3, padx=5, pady=2, sticky="w")

        # Fuel cost settings
        fuel_frame = ttk.LabelFrame(self.settings_tab, text="Fuel Cost Settings")
        fuel_frame.pack(fill="x", expand=False, padx=10, pady=10, ipadx=10, ipady=10)

        # Fuel price per liter, cost for full tank, expected distance per tank
        add_labeled_entry(
            fuel_frame, "Fuel Price (SGD/L):", self.fuel_price_var, row=0, col=0
        )
        add_labeled_entry(
            fuel_frame, "Cost for full tank (SGD):", self.fuel_cost_var, row=0, col=2
        )
        add_labeled_entry(
            fuel_frame,
            "Expected distance per tank (km):",
            self.tank_distance_var,
            row=0,
            col=4,
        )

        # Mileage charge settings
        mileage_frame = ttk.LabelFrame(
            self.settings_tab, text="Mileage Charge Settings"
        )
        mileage_frame.pack(fill="x", expand=False, padx=10, pady=10, ipadx=10, ipady=10)

        add_labeled_entry(
            mileage_frame, "Getgo (SGD/km):", self.getgo_mileage_var, row=0, col=0
        )
        add_labeled_entry(
            mileage_frame, "Car Club (SGD/km):", self.carclub_mileage_var, row=0, col=2
        )

        # Cost per kWh for EVs (will be shown/hidden based on provider selection)
        self.cost_per_kwh_label = ttk.Label(fuel_frame, text="Cost per kWh (SGD):")
        self.cost_per_kwh_entry = ttk.Entry(
            fuel_frame, textvariable=self.cost_per_kwh_var, width=10
        )
        self.cost_per_kwh_label.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.cost_per_kwh_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Initially hide the cost per kWh field (will be shown when EV provider is selected)
        self.cost_per_kwh_label.grid_remove()
        self.cost_per_kwh_entry.grid_remove()

        # Esso Singapore fuel discount (23%) - applies only when region is Singapore
        self.esso_discount_cb = ttk.Checkbutton(
            fuel_frame,
            text="Apply Esso Singapore fuel discount (23%)",
            variable=self.apply_esso_sg_discount_var,
            command=self._on_esso_discount_toggled,
        )
        self.esso_discount_cb.grid(row=2, column=0, columnspan=2, padx=5, pady=5, sticky="w")

        # Car Model Tank Capacities section
        tank_capacity_frame = ttk.LabelFrame(
            self.settings_tab, text="Car Model Tank Capacities"
        )
        tank_capacity_frame.pack(fill="both", expand=True, padx=10, pady=10, ipadx=10, ipady=10)

        # Treeview for displaying car models and tank capacities
        tree_frame = ttk.Frame(tank_capacity_frame)
        tree_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Create Treeview with scrollbar
        tree_scroll = ttk.Scrollbar(tree_frame)
        tree_scroll.pack(side="right", fill="y")

        self.tank_capacity_tree = ttk.Treeview(
            tree_frame,
            columns=("car_model", "capacity"),
            show="headings",
            yscrollcommand=tree_scroll.set,
            height=8,
        )
        self.tank_capacity_tree.heading("car_model", text="Car Model")
        self.tank_capacity_tree.heading("capacity", text="Tank Capacity (L)")
        self.tank_capacity_tree.column("car_model", width=300)
        self.tank_capacity_tree.column("capacity", width=150)
        self.tank_capacity_tree.pack(side="left", fill="both", expand=True)
        tree_scroll.config(command=self.tank_capacity_tree.yview)

        # Bind selection event
        self.tank_capacity_tree.bind(
            "<<TreeviewSelect>>", self.on_tank_capacity_select
        )

        # Input fields frame
        input_frame = ttk.Frame(tank_capacity_frame)
        input_frame.pack(fill="x", padx=5, pady=5)

        ttk.Label(input_frame, text="Car Model:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.tank_capacity_model_var = tk.StringVar()
        self.tank_capacity_model_combo = ttk.Combobox(
            input_frame, textvariable=self.tank_capacity_model_var, width=30
        )
        self.tank_capacity_model_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(input_frame, text="Tank Capacity (L):").grid(
            row=0, column=2, padx=5, pady=5, sticky="w"
        )
        self.tank_capacity_value_var = tk.StringVar()
        self.tank_capacity_value_entry = ttk.Entry(
            input_frame, textvariable=self.tank_capacity_value_var, width=15
        )
        self.tank_capacity_value_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # Buttons frame
        button_frame = ttk.Frame(tank_capacity_frame)
        button_frame.pack(fill="x", padx=5, pady=5)

        ttk.Button(button_frame, text="Add", command=self.add_tank_capacity_entry).pack(
            side="left", padx=5
        )
        ttk.Button(button_frame, text="Edit", command=self.edit_tank_capacity_entry).pack(
            side="left", padx=5
        )
        ttk.Button(button_frame, text="Delete", command=self.delete_tank_capacity_entry).pack(
            side="left", padx=5
        )
        ttk.Button(
            button_frame, text="Load from CSV", command=self.load_car_models_from_csv
        ).pack(side="left", padx=5)
        ttk.Button(
            button_frame, text="Set Defaults", command=self.set_default_tank_capacities
        ).pack(side="left", padx=5)

        # Refresh the treeview with existing data
        self.refresh_tank_capacity_tree()

        # Save settings button
        save_button = ttk.Button(
            self.settings_tab, text="Save Settings", command=self.save_settings
        )
        save_button.pack(anchor="w", padx=10, pady=20)

    def get_default_tank_capacity(self, category: str) -> float:
        """Get default tank capacity based on car category"""
        defaults = {
            "Econ": 40.0,
            "Stand": 40.0,
            "Getgo": 45.0,
            "Car Club": 45.0,
            "Getgo(EV)": 50.0,
        }
        return defaults.get(category, 45.0)

    def refresh_tank_capacity_tree(self):
        """Refresh the tank capacity treeview with current settings"""
        # Clear existing items
        for item in self.tank_capacity_tree.get_children():
            self.tank_capacity_tree.delete(item)
        
        # Add items from settings
        capacities = self.settings.get("car_model_tank_capacities", {})
        for car_model, capacity in sorted(capacities.items()):
            self.tank_capacity_tree.insert(
                "", "end", values=(car_model, f"{capacity:.1f}")
            )

    def on_tank_capacity_select(self, event):
        """Handle selection in tank capacity treeview"""
        selected = self.tank_capacity_tree.selection()
        if selected:
            item = self.tank_capacity_tree.item(selected[0])
            values = item["values"]
            if len(values) >= 2:
                self.tank_capacity_model_var.set(values[0])
                self.tank_capacity_value_var.set(values[1])

    def add_tank_capacity_entry(self):
        """Add a new car model tank capacity entry"""
        car_model = self.tank_capacity_model_var.get().strip()
        capacity_str = self.tank_capacity_value_var.get().strip()
        
        # Validation
        if not car_model:
            messagebox.showerror("Error", "Car model name cannot be empty.")
            return
        
        if not capacity_str:
            messagebox.showerror("Error", "Tank capacity cannot be empty.")
            return
        
        try:
            capacity = float(capacity_str)
            if capacity <= 0:
                messagebox.showerror("Error", "Tank capacity must be a positive number.")
                return
        except ValueError:
            messagebox.showerror("Error", "Tank capacity must be a valid number.")
            return
        
        # Check for duplicates
        capacities = self.settings.get("car_model_tank_capacities", {})
        if car_model in capacities:
            messagebox.showerror("Error", f"Car model '{car_model}' already exists. Use Edit to modify.")
            return
        
        # Add entry
        if "car_model_tank_capacities" not in self.settings:
            self.settings["car_model_tank_capacities"] = {}
        self.settings["car_model_tank_capacities"][car_model] = capacity
        
        # Refresh treeview
        self.refresh_tank_capacity_tree()
        
        # Clear input fields
        self.tank_capacity_model_var.set("")
        self.tank_capacity_value_var.set("")
        
        messagebox.showinfo("Success", f"Added tank capacity for {car_model}: {capacity}L")

    def edit_tank_capacity_entry(self):
        """Edit an existing car model tank capacity entry"""
        selected = self.tank_capacity_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a car model to edit.")
            return
        
        item = self.tank_capacity_tree.item(selected[0])
        values = item["values"]
        if len(values) < 1:
            return
        
        old_car_model = values[0]
        car_model = self.tank_capacity_model_var.get().strip()
        capacity_str = self.tank_capacity_value_var.get().strip()
        
        # Validation
        if not car_model:
            messagebox.showerror("Error", "Car model name cannot be empty.")
            return
        
        if not capacity_str:
            messagebox.showerror("Error", "Tank capacity cannot be empty.")
            return
        
        try:
            capacity = float(capacity_str)
            if capacity <= 0:
                messagebox.showerror("Error", "Tank capacity must be a positive number.")
                return
        except ValueError:
            messagebox.showerror("Error", "Tank capacity must be a valid number.")
            return
        
        # Check for duplicates if name changed
        capacities = self.settings.get("car_model_tank_capacities", {})
        if car_model != old_car_model and car_model in capacities:
            messagebox.showerror("Error", f"Car model '{car_model}' already exists.")
            return
        
        # Update entry
        if "car_model_tank_capacities" not in self.settings:
            self.settings["car_model_tank_capacities"] = {}
        
        # Remove old entry if name changed
        if car_model != old_car_model and old_car_model in capacities:
            del self.settings["car_model_tank_capacities"][old_car_model]
        
        # Add/update new entry
        self.settings["car_model_tank_capacities"][car_model] = capacity
        
        # Refresh treeview
        self.refresh_tank_capacity_tree()
        
        # Clear input fields
        self.tank_capacity_model_var.set("")
        self.tank_capacity_value_var.set("")
        
        messagebox.showinfo("Success", f"Updated tank capacity for {car_model}: {capacity}L")

    def delete_tank_capacity_entry(self):
        """Delete a car model tank capacity entry"""
        selected = self.tank_capacity_tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a car model to delete.")
            return
        
        item = self.tank_capacity_tree.item(selected[0])
        values = item["values"]
        if len(values) < 1:
            return
        
        car_model = values[0]
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm", f"Delete tank capacity for '{car_model}'?"):
            return
        
        # Delete entry
        capacities = self.settings.get("car_model_tank_capacities", {})
        if car_model in capacities:
            del capacities[car_model]
        
        # Refresh treeview
        self.refresh_tank_capacity_tree()
        
        # Clear input fields
        self.tank_capacity_model_var.set("")
        self.tank_capacity_value_var.set("")
        
        messagebox.showinfo("Success", f"Deleted tank capacity for {car_model}")

    def load_car_models_from_csv(self):
        """Load unique car models from CSV data and populate treeview"""
        if not self._check_data_loaded():
            return
        
        if not self._check_column_exists("Car model"):
            return
        
        # Get unique car models (excluding "Calculator Generated")
        unique_models = self.df[
            (self.df["Car model"].notna()) & 
            (self.df["Car model"] != "Calculator Generated")
        ]["Car model"].unique()
        
        if len(unique_models) == 0:
            messagebox.showinfo("Info", "No car models found in the loaded data.")
            return
        
        # Update combobox values
        self.tank_capacity_model_combo["values"] = sorted(unique_models)
        
        # Get car categories for default values
        if "Car Cat" in self.df.columns:
            model_categories = {}
            for model in unique_models:
                model_data = self.df[self.df["Car model"] == model]
                if not model_data.empty:
                    # Get most common category for this model
                    categories = model_data["Car Cat"].dropna().unique()
                    if len(categories) > 0:
                        model_categories[model] = categories[0]
        else:
            model_categories = {}
        
        # Add models with default capacities if not already configured
        if "car_model_tank_capacities" not in self.settings:
            self.settings["car_model_tank_capacities"] = {}
        
        capacities = self.settings["car_model_tank_capacities"]
        added_count = 0
        
        for model in unique_models:
            if model not in capacities:
                # Use default based on category
                category = model_categories.get(model, "")
                default_capacity = self.get_default_tank_capacity(category)
                capacities[model] = default_capacity
                added_count += 1
        
        # Refresh treeview
        self.refresh_tank_capacity_tree()
        
        messagebox.showinfo(
            "Success", 
            f"Loaded {len(unique_models)} car models from CSV.\n"
            f"Added {added_count} new entries with default capacities."
        )

    def set_default_tank_capacities(self):
        """Set default tank capacities for all car models based on their categories"""
        if self.df is None or self.df.empty:
            messagebox.showwarning("Warning", "No data loaded. Please load data first.")
            return
        
        if "Car model" not in self.df.columns or "Car Cat" not in self.df.columns:
            messagebox.showerror("Error", "CSV data must contain 'Car model' and 'Car Cat' columns.")
            return
        
        # Get all car models from settings
        capacities = self.settings.get("car_model_tank_capacities", {})
        if not capacities:
            messagebox.showinfo("Info", "No car models configured. Use 'Load from CSV' first.")
            return
        
        # Confirm action
        if not messagebox.askyesno(
            "Confirm", 
            f"Set default tank capacities for {len(capacities)} car models based on their categories?"
        ):
            return
        
        updated_count = 0
        
        # Update capacities based on categories
        for car_model in capacities.keys():
            model_data = self.df[
                (self.df["Car model"] == car_model) & 
                (self.df["Car Cat"].notna())
            ]
            
            if not model_data.empty:
                # Get most common category for this model
                categories = model_data["Car Cat"].dropna().unique()
                if len(categories) > 0:
                    category = categories[0]
                    default_capacity = self.get_default_tank_capacity(category)
                    capacities[car_model] = default_capacity
                    updated_count += 1
        
        # Refresh treeview
        self.refresh_tank_capacity_tree()
        
        messagebox.showinfo(
            "Success", 
            f"Updated {updated_count} car models with default tank capacities based on categories."
        )

    def setup_records_management_tab(self):
        """Set up the records management tab for CRUD operations with enhanced Excel formula integration"""
        # Main frame with improved layout
        main_frame = ttk.Frame(self.records_management_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Split into left and right panes with better proportions
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5), pady=5)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0), pady=5)

        # Records list on the left with enhanced columns
        records_frame = ttk.LabelFrame(left_frame, text="Rental Records")
        records_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Create treeview for records with comprehensive columns
        columns = (
            "Date",
            "Car Model",
            "Provider",
            "Distance",
            "Duration",
            "Total Cost",
            "Fuel Used",
            "Consumption",
        )
        self.records_tree = ttk.Treeview(
            records_frame, columns=columns, show="headings", height=15
        )

        # Set column headings and widths
        column_widths = {
            "Date": 80,
            "Car Model": 120,
            "Provider": 80,
            "Distance": 70,
            "Duration": 70,
            "Total Cost": 80,
            "Fuel Used": 70,
            "Consumption": 80,
        }

        for col in columns:
            self.records_tree.heading(col, text=col)
            self.records_tree.column(
                col, width=column_widths.get(col, 100), anchor="center", stretch=False
            )

        # Add scrollbars
        y_scrollbar = ttk.Scrollbar(
            records_frame, orient="vertical", command=self.records_tree.yview
        )
        x_scrollbar = ttk.Scrollbar(
            records_frame, orient="horizontal", command=self.records_tree.xview
        )
        self.records_tree.configure(
            yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set
        )

        # Improved packing order for better layout and resizing
        self.records_tree.pack(
            side="left", fill="both", expand=True, padx=(0, 0), pady=(0, 0)
        )
        y_scrollbar.pack(side="right", fill="y")
        x_scrollbar.pack(side="bottom", fill="x")

        # Add select event
        self.records_tree.bind("<<TreeviewSelect>>", self.on_record_select)

        # Enhanced buttons for record operations
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill="x", expand=False, padx=5, pady=5)

        # Left side buttons
        left_buttons = ttk.Frame(button_frame)
        left_buttons.pack(side="left", fill="x", expand=True)

        ttk.Button(left_buttons, text="🆕 Add New Record", command=self.add_record, style="Accent.TButton").pack(
            side="left", padx=2
        )
        ttk.Button(left_buttons, text="💾 Update Record", command=self.update_record, style="Accent.TButton").pack(
            side="left", padx=2
        )
        ttk.Button(left_buttons, text="🔄 Refresh", command=self.refresh_records).pack(
            side="left", padx=2
        )
        ttk.Button(left_buttons, text="🗑️ Delete", command=self.delete_record).pack(
            side="left", padx=2
        )

        # Right side buttons
        right_buttons = ttk.Frame(button_frame)
        right_buttons.pack(side="right", fill="x", expand=True)

        ttk.Button(
            right_buttons, text="📤 Export", command=self.export_records_data
        ).pack(side="right", padx=2)

        # Enhanced search field
        search_frame = ttk.Frame(button_frame)
        search_frame.pack(side="right", padx=10)

        ttk.Label(search_frame, text="🔍 Search:").pack(side="left", padx=2)
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var, width=20)
        search_entry.pack(side="left", padx=2)
        search_entry.bind("<KeyRelease>", self.filter_records)

        # LLM Assistant Frame for natural language input
        llm_assistant_frame = ttk.LabelFrame(right_frame, text="🤖 LLM Assistant - Describe Your Rental")
        llm_assistant_frame.pack(fill="x", padx=5, pady=5)
        
        # Text input area for natural language description
        llm_input_frame = ttk.Frame(llm_assistant_frame)
        llm_input_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        ttk.Label(llm_input_frame, text="💬 Describe your rental in natural language:").pack(anchor="w", padx=5, pady=2)
        
        # Text widget for input with scrollbar
        llm_text_frame = ttk.Frame(llm_input_frame)
        llm_text_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.llm_input_text = tk.Text(llm_text_frame, height=4, width=60, wrap=tk.WORD)
        llm_input_scrollbar = ttk.Scrollbar(llm_text_frame, orient="vertical", command=self.llm_input_text.yview)
        self.llm_input_text.configure(yscrollcommand=llm_input_scrollbar.set)
        self.llm_input_text.pack(side="left", fill="both", expand=True)
        llm_input_scrollbar.pack(side="right", fill="y")
        
        # Example text
        example_text = "Example: 'Rented a Getgo car on Saturday, drove 50km in 3 hours, pumped 4L of fuel'"
        ttk.Label(llm_input_frame, text=example_text, font=("TkDefaultFont", 8), foreground="gray").pack(anchor="w", padx=5, pady=2)
        
        # Buttons frame
        llm_buttons_frame = ttk.Frame(llm_assistant_frame)
        llm_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(
            llm_buttons_frame,
            text="🤖 Rephrase to standard format",
            command=self.rephrase_to_standard_format,
            style="Accent.TButton"
        ).pack(side="left", padx=5)
        
        ttk.Button(
            llm_buttons_frame,
            text="🤖 Process with LLM",
            command=self.process_natural_language_input,
            style="Accent.TButton"
        ).pack(side="left", padx=5)
        
        ttk.Button(
            llm_buttons_frame,
            text="📋 Fill Form from LLM",
            command=self.fill_form_from_llm,
        ).pack(side="left", padx=5)
        
        ttk.Button(
            llm_buttons_frame,
            text="🧹 Clear",
            command=lambda: self.llm_input_text.delete("1.0", tk.END),
        ).pack(side="left", padx=5)
        
        # Display area for LLM response
        llm_response_frame = ttk.LabelFrame(llm_assistant_frame, text="📊 LLM Extracted Data")
        llm_response_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.llm_response_text = tk.Text(
            llm_response_frame,
            height=6,
            width=60,
            state="disabled",
            background="#f8f9fa",
            font=("Consolas", 9),
            wrap=tk.WORD
        )
        llm_response_scrollbar = ttk.Scrollbar(
            llm_response_frame,
            orient="vertical",
            command=self.llm_response_text.yview
        )
        self.llm_response_text.configure(yscrollcommand=llm_response_scrollbar.set)
        self.llm_response_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        llm_response_scrollbar.pack(side="right", fill="y")
        
        # Store LLM extracted data
        self.llm_extracted_data = None

        # Enhanced Record Form on the right
        form_frame = ttk.LabelFrame(right_frame, text="📝 Record Details")
        form_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Create scrollable frame for the form with proper configuration
        # Remove scrolling: just use a direct frame in the form_frame
        scrollable_frame = ttk.Frame(form_frame)
        scrollable_frame.pack(fill="both", expand=True)

        # Create two frames for better organization
        left_form_frame = ttk.Frame(scrollable_frame)
        left_form_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)

        right_form_frame = ttk.Frame(scrollable_frame)
        right_form_frame.pack(side="right", fill="both", expand=True, padx=10, pady=5)

        # Left form fields - Basic Information
        basic_info_frame = ttk.LabelFrame(left_form_frame, text="📋 Basic Information")
        basic_info_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Region (Singapore / Malaysia) - determines which providers are shown
        ttk.Label(basic_info_frame, text="🌏 Region:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(basic_info_frame, text="*", foreground="red").grid(row=0, column=0, padx=(55, 0), pady=5, sticky="w")
        self.record_region_var.set("Singapore")
        GUIHelper.create_combobox(
            parent=basic_info_frame,
            textvariable=self.record_region_var,
            values=list(VALID_REGIONS),
            width=15,
            row=0,
            column=1,
            padx=5,
            pady=5,
            sticky="w",
            bind_event=("<<ComboboxSelected>>", self._on_record_region_changed),
        )

        # Date and Car Model with better layout
        date_label_frame = ttk.Frame(basic_info_frame)
        date_label_frame.grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(date_label_frame, text="📅 Date (DD/MM/YYYY):").pack(side="left")
        ttk.Label(date_label_frame, text="*", foreground="red").pack(side="left", padx=(2, 0))
        date_entry = ttk.Entry(
            basic_info_frame, textvariable=self.record_date_var, width=15
        )
        date_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        date_entry.bind("<KeyRelease>", lambda e: setattr(self, '_form_dirty', True))
        ttk.Button(
            basic_info_frame, text="Today", command=self.set_today_date, width=8
        ).grid(row=1, column=2, padx=2, pady=5, sticky="w")

        car_model_label_frame = ttk.Frame(basic_info_frame)
        car_model_label_frame.grid(row=2, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(car_model_label_frame, text="🚗 Car Model:").pack(side="left")
        ttk.Label(car_model_label_frame, text="*", foreground="red").pack(side="left", padx=(2, 0))
        car_model_entry = ttk.Entry(
            basic_info_frame, textvariable=self.record_car_model_var, width=25
        )
        car_model_entry.grid(row=2, column=1, columnspan=2, padx=5, pady=5, sticky="w")
        car_model_entry.bind("<KeyRelease>", lambda e: setattr(self, '_form_dirty', True))

        # Provider (Car Cat) - list depends on Region
        provider_label_frame = ttk.Frame(basic_info_frame)
        provider_label_frame.grid(row=3, column=0, padx=5, pady=5, sticky="w")
        ttk.Label(provider_label_frame, text="🏢 Provider:").pack(side="left")
        ttk.Label(provider_label_frame, text="*", foreground="red").pack(side="left", padx=(2, 0))
        self.record_provider_combo = GUIHelper.create_combobox(
            parent=basic_info_frame,
            textvariable=self.record_provider_var,
            values=get_providers_for_region(self.record_region_var.get() or "Singapore"),
            width=15,
            row=3,
            column=1,
            padx=5,
            pady=5,
            sticky="w",
            bind_event=("<<ComboboxSelected>>", self.on_provider_changed),
        )

        ttk.Label(basic_info_frame, text="📅 Day Type:").grid(
            row=4, column=0, padx=5, pady=5, sticky="w"
        )
        daytype_combo = GUIHelper.create_combobox(
            parent=basic_info_frame,
            textvariable=self.record_weekend_var,
            values=["weekday", "weekend"],
            width=15,
            row=4,
            column=1,
            padx=5,
            pady=5,
            sticky="w",
        )

        # Right form fields - Rental Details
        rental_details_frame = ttk.LabelFrame(right_form_frame, text="⏱️ Rental Details")
        rental_details_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Distance and Duration with auto-calculation hints
        ttk.Label(rental_details_frame, text="📏 Distance (KM):").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        distance_entry = ttk.Entry(
            rental_details_frame, textvariable=self.record_distance_var, width=15
        )
        distance_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(rental_details_frame, text="*Required", foreground="red").grid(
            row=0, column=2, padx=2, pady=5, sticky="w"
        )

        ttk.Label(rental_details_frame, text="⏰ Rental Hours:").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        hours_entry = ttk.Entry(
            rental_details_frame, textvariable=self.record_hours_var, width=15
        )
        hours_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(rental_details_frame, text="*Required", foreground="red").grid(
            row=1, column=2, padx=2, pady=5, sticky="w"
        )

        # Enhanced Fuel Information with better organization
        fuel_frame = ttk.LabelFrame(left_form_frame, text="⛽ Fuel Information")
        fuel_frame.pack(fill="both", expand=True, padx=5, pady=5)

        ttk.Label(fuel_frame, text="⛽ Fuel Pumped (L):").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(fuel_frame, textvariable=self.record_fuel_pumped_var, width=15).grid(
            row=0, column=1, padx=5, pady=5, sticky="w"
        )

        ttk.Label(fuel_frame, text="📊 Est. Fuel Usage (L):").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(fuel_frame, textvariable=self.record_fuel_usage_var, width=15).grid(
            row=1, column=1, padx=5, pady=5, sticky="w"
        )

        ttk.Label(fuel_frame, text="📈 Consumption (KM/L):").grid(
            row=2, column=0, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(fuel_frame, textvariable=self.record_consumption_var, width=15).grid(
            row=2, column=1, padx=5, pady=5, sticky="w"
        )

        # Auto-calculate fuel usage button
        ttk.Button(
            fuel_frame,
            text="Auto-calc Usage",
            command=self.auto_calculate_fuel_usage,
            width=12,
        ).grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="ew")

        # Enhanced Cost Information with Excel integration
        cost_frame = ttk.LabelFrame(right_form_frame, text="💰 Cost Information")
        cost_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # First column of costs
        ttk.Label(cost_frame, text="💵 Total Cost ($):").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(cost_frame, textvariable=self.record_total_cost_var, width=15).grid(
            row=0, column=1, padx=5, pady=5, sticky="w"
        )

        ttk.Label(cost_frame, text="⛽ Pumped Fuel Cost ($):").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(
            cost_frame,
            textvariable=self.record_pumped_cost_var,
            width=15,
            state="readonly",
            background="#f0f0f0",
            foreground="black",
        ).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Second column of costs
        ttk.Label(cost_frame, text="📏 Cost per KM ($):").grid(
            row=0, column=2, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(
            cost_frame,
            textvariable=self.record_cost_per_km_var,
            width=15,
            state="readonly",
            background="#f0f0f0",
            foreground="black",
        ).grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(cost_frame, text="⏰ Duration Cost ($):").grid(
            row=1, column=2, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(
            cost_frame, textvariable=self.record_duration_cost_var, width=15
        ).grid(row=1, column=3, padx=5, pady=5, sticky="w")

        # Additional cost fields
        ttk.Label(cost_frame, text="💰 Cost per Hour ($):").grid(
            row=2, column=0, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(
            cost_frame,
            textvariable=self.record_cost_per_hr_var,
            width=15,
            state="readonly",
            background="#f0f0f0",
            foreground="black",
        ).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(cost_frame, text="💸 Fuel Savings ($):").grid(
            row=2, column=2, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(
            cost_frame,
            textvariable=self.record_fuel_savings_var,
            width=15,
            state="readonly",
            background="#f0f0f0",
            foreground="black",
        ).grid(row=2, column=3, padx=5, pady=5, sticky="w")

        # Improved layout: align buttons horizontally, add spacers for clarity

        # Create a frame to hold the action buttons for better layout
        button_row = ttk.Frame(cost_frame)
        button_row.grid(row=3, column=0, columnspan=4, padx=0, pady=5, sticky="ew")

        # Auto-calc button (left)
        auto_calc_btn = ttk.Button(
            button_row,
            text="Auto-calc Total",
            command=self.auto_calculate_total_cost,
            width=14,
        )
        auto_calc_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # Smart calculation button (middle)
        smart_calc_btn = ttk.Button(
            button_row,
            text="Get smart calculation",
            command=self.smart_auto_calc,
            width=16,
        )
        smart_calc_btn.pack(side="left", fill="x", expand=True, padx=(0, 5))

        # LLM Assistance button (right, robot emoji)
        llm_btn = ttk.Button(
            button_row,
            text="🤖 Get LLM Assistance",
            command=self.llm_assisted_form_fill,
            width=18,
        )
        llm_btn.pack(side="left", fill="x", expand=True)


        # Malaysia NormalRental breakdown (shown when Provider = NormalRental)
        self.normal_rental_frame = ttk.LabelFrame(left_form_frame, text="🇲🇾 NormalRental (RM)")
        # Pack later only when provider is NormalRental
        ttk.Label(self.normal_rental_frame, text="Deposit (RM):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(self.normal_rental_frame, textvariable=self.record_deposit_rm_var, width=12).grid(row=0, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(self.normal_rental_frame, text="Rental fee (RM):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(self.normal_rental_frame, textvariable=self.record_rental_fee_rm_var, width=12).grid(row=1, column=1, padx=5, pady=5, sticky="w")
        ttk.Label(self.normal_rental_frame, text="Additional fee (RM):").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        ttk.Entry(self.normal_rental_frame, textvariable=self.record_additional_fee_rm_var, width=12).grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # EV Information (will be shown/hidden based on provider selection)
        self.ev_frame = ttk.LabelFrame(left_form_frame, text="⚡ EV Information")
        self.ev_frame.pack(fill="both", expand=True, padx=5, pady=5)

        ttk.Label(self.ev_frame, text="⚡ kWh Used (EV):").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(self.ev_frame, textvariable=self.record_kwh_used_var, width=10).grid(
            row=0, column=1, padx=5, pady=5, sticky="w"
        )

        ttk.Label(self.ev_frame, text="💰 Electricity Cost ($):").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(
            self.ev_frame,
            textvariable=self.record_electricity_cost_var,
            width=15,
            state="readonly",
            background="#f0f0f0",
            foreground="black",
        ).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Initially hide the EV frame (will be shown when EV provider is selected)
        self.ev_frame.pack_forget()

        # Enhanced Fuel Economy Comparison Frame
        fuel_economy_frame = ttk.LabelFrame(
            right_form_frame, text="📈 Fuel Economy Comparison"
        )
        fuel_economy_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Create text widget for fuel economy comparison
        self.fuel_economy_comparison_text = tk.Text(
            fuel_economy_frame,
            height=8,
            width=60,
            state="disabled",
            background="#f8f9fa",
            font=("Consolas", 9),
        )
        fuel_economy_scrollbar = ttk.Scrollbar(
            fuel_economy_frame,
            orient="vertical",
            command=self.fuel_economy_comparison_text.yview,
        )
        self.fuel_economy_comparison_text.configure(
            yscrollcommand=fuel_economy_scrollbar.set
        )

        self.fuel_economy_comparison_text.pack(
            side="left", fill="both", expand=True, padx=5, pady=5
        )
        fuel_economy_scrollbar.pack(side="right", fill="y")

        # Enhanced Button frame for CRUD operations
        crud_frame = ttk.Frame(scrollable_frame)
        crud_frame.pack(fill="x", padx=5, pady=10)

        # Primary action buttons
        primary_buttons = ttk.Frame(crud_frame)
        primary_buttons.pack(fill="x", pady=5)

        add_btn = ttk.Button(
            primary_buttons,
            text="🆕 Add New Record",
            command=self.add_record,
            style="Accent.TButton",
        )
        add_btn.pack(side="left", padx=5, fill="x", expand=True)
        # Bind Enter key to add record when form is focused
        self.root.bind_all("<Return>", lambda e: self.add_record() if self.records_management_tab == self.notebook.select() else None)
        
        update_btn = ttk.Button(
            primary_buttons,
            text="💾 Update Record",
            command=self.update_record,
            style="Accent.TButton",
        )
        update_btn.pack(side="left", padx=5, fill="x", expand=True)

        # Secondary action buttons
        secondary_buttons = ttk.Frame(crud_frame)
        secondary_buttons.pack(fill="x", pady=2)

        ttk.Button(
            secondary_buttons, text="🧹 Clear Form", command=self.clear_record_form
        ).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(
            secondary_buttons,
            text="📊 Calculate All",
            command=self.calculate_all_formulas,
        ).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(
            secondary_buttons,
            text="📝 Edit Selected",
            command=self.edit_selected_record,
        ).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(
            secondary_buttons, text="🆕 Quick Add", command=self.add_new_record_quick
        ).pack(side="left", padx=5, fill="x", expand=True)

        # Add status bar to show form state
        self.records_status_bar = ttk.Label(
            right_frame,
            text="Form ready - All fields visible",
            relief="sunken",
            anchor="w",
        )
        self.records_status_bar.pack(side="bottom", fill="x", padx=5, pady=2)

        # Update status after a short delay to ensure all widgets are visible
        self.root.after(
            200,
            lambda: self.update_records_status(
                "Form loaded - All fields visible and accessible"
            ),
        )

        # Record ID variable (hidden) for tracking which record is being edited
        self.current_record_index = None

        # Enhanced trace callbacks to trigger auto-calculation with better performance
        self.record_provider_var.trace_add(
            "write", lambda *args: self.auto_update_fields()
        )
        self.record_distance_var.trace_add(
            "write", lambda *args: self.auto_update_fields()
        )
        self.record_fuel_pumped_var.trace_add(
            "write", lambda *args: self.auto_update_fields()
        )
        self.record_fuel_usage_var.trace_add(
            "write", lambda *args: self.auto_update_fields()
        )
        self.record_total_cost_var.trace_add(
            "write", lambda *args: self.auto_update_fields()
        )
        self.record_hours_var.trace_add(
            "write", lambda *args: self.auto_update_fields()
        )
        self.record_kwh_used_var.trace_add(
            "write", lambda *args: self.auto_update_fields()
        )
        self.record_duration_cost_var.trace_add(
            "write", lambda *args: self.auto_update_fields()
        )
        self.fuel_price_var.trace_add("write", lambda *args: self.auto_update_fields())

    def update_records_status(self, message):
        """Update the status bar in records management tab"""
        if hasattr(self, "records_status_bar"):
            self.records_status_bar.config(text=message)

    def set_today_date(self):
        """Set today's date in the date field"""
        from datetime import datetime

        today = datetime.now().strftime("%d/%m/%Y")
        self.record_date_var.set(today)

    def add_new_record_quick(self):
        """Quick add new record with default values"""
        self.clear_record_form()
        self.set_today_date()
        self.record_provider_var.set("Getgo")
        self.record_weekend_var.set("weekday")
        # Focus on the first field
        self.root.focus_set()
        # Update status
        self.update_records_status("New record form ready - All fields visible")

    def edit_selected_record(self):
        """Edit the currently selected record"""
        selection = self.records_tree.selection()
        if selection:
            # Create a dummy event object to pass to on_record_select
            class DummyEvent:
                pass

            event = DummyEvent()
            self.on_record_select(event)
        else:
            messagebox.showwarning("No Selection", "Please select a record to edit.")

    def auto_calculate_fuel_usage(self):
        """Auto-calculate fuel usage based on distance and consumption"""
        try:
            distance = (
                float(self.record_distance_var.get())
                if self.record_distance_var.get()
                else 0
            )
            consumption = (
                float(self.record_consumption_var.get())
                if self.record_consumption_var.get()
                else 12.0
            )

            if distance > 0 and consumption > 0:
                fuel_usage = distance / consumption
                self.record_fuel_usage_var.set(f"{fuel_usage:.2f}")
                messagebox.showinfo(
                    "Auto-calculation", f"Fuel usage calculated: {fuel_usage:.2f}L"
                )
            else:
                messagebox.showwarning(
                    "Auto-calculation",
                    "Please enter distance and consumption values first.",
                )
        except ValueError:
            messagebox.showerror("Error", "Invalid values for calculation.")

    def auto_calculate_total_cost(self):
        """Auto-calculate total cost based on available data"""
        try:
            # Get values
            distance = (
                float(self.record_distance_var.get())
                if self.record_distance_var.get()
                else 0
            )
            hours = (
                float(self.record_hours_var.get()) if self.record_hours_var.get() else 0
            )
            provider = self.record_provider_var.get()
            fuel_pumped = (
                float(self.record_fuel_pumped_var.get())
                if self.record_fuel_pumped_var.get()
                else 0
            )
            fuel_price = (
                float(self.fuel_price_var.get()) if self.fuel_price_var.get() else 2.76
            )

            total_cost = 0

            if provider == "Getgo(EV)":
                # EV calculation
                # Mileage cost at $0.29/km (no charging cost as it's provided free)
                mileage_cost = distance * 0.29

                # Duration cost (use user input or estimate)
                user_duration_cost = (
                    float(self.record_duration_cost_var.get())
                    if self.record_duration_cost_var.get()
                    else 0
                )
                if user_duration_cost > 0:
                    duration_cost = user_duration_cost
                else:
                    duration_cost = hours * 8.0  # Fallback estimate of $8/hour

                total_cost = mileage_cost + duration_cost
            else:
                # Regular car calculation
                # Mileage cost
                mileage_cost = 0
                if provider == "Getgo":
                    mileage_cost = distance * 0.39
                elif provider == "Car Club":
                    mileage_cost = distance * 0.33

                # Duration cost (use user input or estimate)
                user_duration_cost = (
                    float(self.record_duration_cost_var.get())
                    if self.record_duration_cost_var.get()
                    else 0
                )
                if user_duration_cost > 0:
                    duration_cost = user_duration_cost
                else:
                    duration_cost = hours * 8.0  # Fallback estimate of $8/hour

                # Fuel cost (Esso Singapore 23% discount applied only when toggle on and region Singapore)
                region = (self.record_region_var.get() or "Singapore").strip()
                factor = self._get_fuel_discount_factor(region)
                fuel_cost = fuel_pumped * fuel_price * factor

                total_cost = mileage_cost + duration_cost + fuel_cost

            self.record_total_cost_var.set(f"{total_cost:.2f}")
            messagebox.showinfo(
                "Auto-calculation", f"Total cost calculated: ${total_cost:.2f}"
            )

        except ValueError:
            messagebox.showerror("Error", "Invalid values for calculation.")

    def _get_fuel_discount_factor(self, region=None):
        """Return multiplier for pumped fuel cost: 0.77 (23% off) if Esso SG discount on and region Singapore, else 1.0 (no discount)."""
        if region is None:
            region = getattr(self, "record_region_var", None)
            region = (region.get() or "Singapore").strip() if region else "Singapore"
        if getattr(self, "apply_esso_sg_discount_var", None) and self.apply_esso_sg_discount_var.get():
            if (region or "Singapore").strip() == "Singapore":
                return 0.77  # 23% discount for Esso in Singapore only
        return 1.0

    def _get_historical_statistics(self, provider):
        """Get historical statistics for a given provider from past rental data"""
        stats = {
            'data_points': 0,
            'avg_cost_per_km': None,
            'avg_cost_per_hour': None,
            'avg_consumption': None,
            'avg_fuel_price': None,
            'avg_total_cost': None,
        }
        
        if self.df is None or self.df.empty or not provider:
            return stats
        
        try:
            # Filter data by provider
            provider_data = self.df[self.df["Car Cat"] == provider]
            
            if provider_data.empty:
                return stats
            
            stats['data_points'] = len(provider_data)
            
            # Calculate averages
            if "Cost per KM" in provider_data.columns:
                stats['avg_cost_per_km'] = provider_data["Cost per KM"].mean()
            
            if "Cost/HR" in provider_data.columns:
                stats['avg_cost_per_hour'] = provider_data["Cost/HR"].mean()
            
            if "Consumption (KM/L)" in provider_data.columns:
                consumption_data = provider_data["Consumption (KM/L)"].dropna()
                if not consumption_data.empty:
                    stats['avg_consumption'] = consumption_data.mean()
            
            if "Total" in provider_data.columns:
                stats['avg_total_cost'] = provider_data["Total"].mean()
            
            # Estimate fuel price from historical data
            if "Pumped fuel cost" in provider_data.columns and "Fuel pumped" in provider_data.columns:
                fuel_cost = provider_data["Pumped fuel cost"].dropna()
                fuel_pumped = provider_data["Fuel pumped"].dropna()
                if not fuel_cost.empty and not fuel_pumped.empty:
                    # Reverse discount: fuel_price = (stored_cost / fuel_pumped) / discount_factor
                    factor = self._get_fuel_discount_factor(self._get_current_region())
                    fuel_price_series = (fuel_cost / fuel_pumped) / factor
                    fuel_price_series = fuel_price_series[fuel_price_series > 0]  # Remove invalid values
                    if not fuel_price_series.empty:
                        stats['avg_fuel_price'] = fuel_price_series.mean()
        
        except Exception as e:
            # Silently fail and return empty stats
            pass
        
        return stats

    def _calculate_cost_from_historical_data(self, distance, hours, provider, fuel_pumped, fuel_price, duration_cost, historical_stats):
        """Calculate total cost using historical data as fallback"""
        try:
            distance_val = float(distance) if distance else 0
            hours_val = float(hours) if hours else 0
            fuel_pumped_val = float(fuel_pumped) if fuel_pumped else 0
            fuel_price_val = float(fuel_price) if fuel_price else 2.51
            
            total_cost = 0
            
            if provider == "Getgo(EV)":
                # EV calculation
                mileage_cost = distance_val * 0.29
                
                if duration_cost:
                    duration_cost_val = float(duration_cost)
                elif historical_stats.get('avg_cost_per_hour'):
                    duration_cost_val = hours_val * historical_stats['avg_cost_per_hour']
                else:
                    duration_cost_val = hours_val * 8.0
                
                total_cost = mileage_cost + duration_cost_val
            else:
                # Regular car calculation
                mileage_cost = 0
                if provider == "Getgo":
                    mileage_cost = distance_val * 0.39
                elif provider == "Car Club":
                    mileage_cost = distance_val * 0.33
                
                if duration_cost:
                    duration_cost_val = float(duration_cost)
                elif historical_stats.get('avg_cost_per_hour'):
                    duration_cost_val = hours_val * historical_stats['avg_cost_per_hour']
                else:
                    duration_cost_val = hours_val * 8.0

                region = getattr(self, "record_region_var", None)
                region = (region.get() or "Singapore").strip() if region else "Singapore"
                factor = self._get_fuel_discount_factor(region)
                fuel_cost = fuel_pumped_val * fuel_price_val * factor

                total_cost = mileage_cost + duration_cost_val + fuel_cost

            return total_cost
        except Exception:
            return None

    def calculate_excel_formulas_for_current_record(self):
        """Calculate Excel formulas for the current record - wrapper for auto_update_fields"""
        try:
            self.auto_update_fields()
        except Exception as e:
            # Silently handle errors as this is called from multiple places
            pass

    def _estimate_missing_values_with_llm(self, distance, hours, provider, fuel_pumped, fuel_usage, consumption, fuel_price, duration_cost, historical_stats):
        """Use LLM to estimate missing fuel and cost values"""
        import requests
        import json
        
        # Identify what's missing
        missing = []
        if not consumption and distance and fuel_usage:
            missing.append("consumption")
        if not fuel_usage and distance and consumption:
            missing.append("fuel_usage")
        if not fuel_price or fuel_price == "":
            missing.append("fuel_price")
        if not duration_cost and hours:
            missing.append("duration_cost")
        
        if not missing:
            return {}  # Nothing to estimate
        
        # Build context for LLM
        available_data = {
            "Distance (km)": distance if distance else "unknown",
            "Hours": hours if hours else "unknown",
            "Provider": provider,
            "Fuel Pumped (L)": fuel_pumped if fuel_pumped else "unknown",
            "Fuel Usage (L)": fuel_usage if fuel_usage else "unknown",
            "Consumption (km/L)": consumption if consumption else "unknown",
            "Fuel Price ($/L)": fuel_price if fuel_price else "unknown",
            "Duration Cost ($)": duration_cost if duration_cost else "unknown",
        }
        
        historical_context = ""
        if historical_stats and historical_stats.get('data_points', 0) > 0:
            historical_context = f"\n\nHistorical Data (from {historical_stats['data_points']} past rentals for {provider}):\n"
            if historical_stats.get('avg_consumption'):
                historical_context += f"- Average consumption: {historical_stats['avg_consumption']:.2f} km/L\n"
            if historical_stats.get('avg_cost_per_hour'):
                historical_context += f"- Average cost per hour: ${historical_stats['avg_cost_per_hour']:.2f}\n"
            if historical_stats.get('avg_fuel_price'):
                historical_context += f"- Average fuel price: ${historical_stats['avg_fuel_price']:.2f}/L\n"
        
        prompt = (
            f"You are a car rental cost expert. I need help estimating missing values for a rental record.\n\n"
            f"Available data:\n{json.dumps(available_data, indent=2)}\n"
            f"{historical_context}\n"
            f"Please estimate the following missing values: {', '.join(missing)}.\n\n"
            f"Rules:\n"
            f"- If distance and consumption are known, fuel_usage = distance / consumption\n"
            f"- If distance and fuel_usage are known, consumption = distance / fuel_usage\n"
            f"- Use historical data averages if available\n"
            f"- For fuel_price, use historical average or typical Singapore price (~$2.50-2.80/L)\n"
            f"- For duration_cost, estimate based on hours and provider rates\n\n"
            f"Return ONLY a JSON object with the estimated values, like:\n"
            f'{{"consumption": 14.5, "fuel_usage": 7.2, "fuel_price": 2.55, "duration_cost": 24.0}}\n'
            f"Only include the values that were requested in the missing list."
        )
        
        try:
            ollama_url = "http://localhost:11434/api/generate"
            if hasattr(self, 'ollama_model_var'):
                model = self.ollama_model_var.get()
            else:
                model = "llama3.1:3b"
            
            payload = {"model": model, "prompt": prompt, "stream": False}
            response = requests.post(ollama_url, json=payload, timeout=30)
            response.raise_for_status()
            resp_json = response.json()
            
            if "response" in resp_json:
                llm_output = resp_json["response"].strip()
                # Try to extract JSON from response (handle nested JSON)
                import re
                # Find JSON object - look for opening brace and try to match closing brace
                start_idx = llm_output.find('{')
                if start_idx != -1:
                    # Count braces to find matching closing brace
                    brace_count = 0
                    for i in range(start_idx, len(llm_output)):
                        if llm_output[i] == '{':
                            brace_count += 1
                        elif llm_output[i] == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                json_str = llm_output[start_idx:i+1]
                                try:
                                    estimates = json.loads(json_str)
                                    return estimates
                                except json.JSONDecodeError:
                                    pass
                                break
        except Exception as e:
            # Silently fail - will use historical data fallback
            pass
        
        return {}

    def smart_auto_calc(self):
        """Smart auto-calculate: use LLM to estimate missing fuel/cost values, then use standard calculation for total cost"""
        # Get current form values
        distance = self.record_distance_var.get()
        hours = self.record_hours_var.get()
        provider = self.record_provider_var.get()
        
        # Validate required fields
        if not provider:
            messagebox.showerror("Error", "Please select a provider first.")
            return
        
        fuel_pumped = self.record_fuel_pumped_var.get()
        fuel_usage = self.record_fuel_usage_var.get()
        consumption = self.record_consumption_var.get()
        fuel_price = self.fuel_price_var.get() if hasattr(self, 'fuel_price_var') and self.fuel_price_var.get() else ""
        duration_cost = self.record_duration_cost_var.get()
        
        # Step 1: Use simple math to calculate derived values if possible
        estimated_values = {}
        estimated_sources = {}
        
        # Calculate consumption if distance and fuel_usage are known
        if not consumption and distance and fuel_usage:
            try:
                distance_val = float(distance)
                fuel_usage_val = float(fuel_usage)
                if fuel_usage_val > 0:
                    calculated_consumption = distance_val / fuel_usage_val
                    self.record_consumption_var.set(f"{calculated_consumption:.2f}")
                    estimated_values['Consumption'] = f"{calculated_consumption:.2f} km/L"
                    estimated_sources['Consumption'] = "calculated from distance and fuel usage"
            except (ValueError, ZeroDivisionError):
                pass
        
        # Calculate fuel_usage if distance and consumption are known
        if not fuel_usage and distance and consumption:
            try:
                distance_val = float(distance)
                consumption_val = float(consumption)
                if consumption_val > 0:
                    calculated_fuel_usage = distance_val / consumption_val
                    self.record_fuel_usage_var.set(f"{calculated_fuel_usage:.2f}")
                    estimated_values['Fuel Usage'] = f"{calculated_fuel_usage:.2f} L"
                    estimated_sources['Fuel Usage'] = "calculated from distance and consumption"
            except (ValueError, ZeroDivisionError):
                pass
        
        # Step 2: Get historical statistics
        historical_stats = self._get_historical_statistics(provider)
        
        # Step 3: Use historical data to estimate missing values
        # Update consumption from historical data if still missing
        if not consumption and historical_stats.get('avg_consumption'):
            estimated_consumption = historical_stats['avg_consumption']
            self.record_consumption_var.set(f"{estimated_consumption:.2f}")
            estimated_values['Consumption'] = f"{estimated_consumption:.2f} km/L"
            estimated_sources['Consumption'] = f"estimated from {historical_stats['data_points']} past rentals"
        
        # Update fuel price from historical data if missing
        if not fuel_price or fuel_price == "":
            if historical_stats.get('avg_fuel_price'):
                fuel_price = str(historical_stats['avg_fuel_price'])
                estimated_values['Fuel Price'] = f"${fuel_price}/L"
                estimated_sources['Fuel Price'] = f"estimated from {historical_stats['data_points']} past rentals"
            else:
                fuel_price = "2.51"  # Default
                estimated_values['Fuel Price'] = "$2.51/L"
                estimated_sources['Fuel Price'] = "default value"
        
        # Update duration cost from historical data if missing
        if not duration_cost and hours:
            try:
                hours_val = float(hours)
                if historical_stats.get('avg_cost_per_hour'):
                    estimated_duration_cost = hours_val * historical_stats['avg_cost_per_hour']
                    self.record_duration_cost_var.set(f"{estimated_duration_cost:.2f}")
                    estimated_values['Duration Cost'] = f"${estimated_duration_cost:.2f}"
                    estimated_sources['Duration Cost'] = f"estimated from {historical_stats['data_points']} past rentals"
                else:
                    estimated_duration_cost = hours_val * 8.0
                    self.record_duration_cost_var.set(f"{estimated_duration_cost:.2f}")
                    estimated_values['Duration Cost'] = f"${estimated_duration_cost:.2f}"
                    estimated_sources['Duration Cost'] = "default estimate ($8/hr)"
            except ValueError:
                pass
        
        # Step 4: Use LLM for complex estimates or when multiple fields are missing
        # Re-read variables after updates to get current values
        consumption = self.record_consumption_var.get()
        fuel_usage = self.record_fuel_usage_var.get()
        duration_cost = self.record_duration_cost_var.get()
        fuel_price = self.fuel_price_var.get() if hasattr(self, 'fuel_price_var') and self.fuel_price_var.get() else ""
        
        # Check if we still need LLM help
        needs_llm = False
        missing_count = sum([
            bool(not consumption and not (distance and fuel_usage)),
            bool(not fuel_usage and not (distance and consumption)),
            bool(not duration_cost and hours),
            bool(not fuel_price or fuel_price == "")
        ])
        
        # Use LLM if we have multiple missing fields or complex scenarios
        if missing_count >= 2:
            needs_llm = True
        elif not consumption and not (distance and fuel_usage):
            needs_llm = True
        elif not fuel_usage and not (distance and consumption):
            needs_llm = True
        
        llm_estimates = {}
        if needs_llm:
            try:
                # Get updated values after historical data estimates
                fuel_usage = self.record_fuel_usage_var.get()
                consumption = self.record_consumption_var.get()
                
                # Prepare form data for new LLM function
                form_data = {
                    "provider": provider,
                    "distance": float(distance) if distance else None,
                    "duration": float(hours) if hours else None,
                    "fuel_pumped": float(fuel_pumped) if fuel_pumped else None,
                    "fuel_usage": float(fuel_usage) if fuel_usage else None,
                    "consumption": float(consumption) if consumption else None,
                    "duration_cost": float(duration_cost) if duration_cost else None,
                    "is_weekend": self.record_weekend_var.get() == "weekend" if self.record_weekend_var.get() else None,
                }
                
                # Get model name
                model_name = getattr(self, "ollama_model_var", None)
                if model_name:
                    model_name = model_name.get() if hasattr(model_name, "get") else "llama2"
                else:
                    model_name = "llama2"
                
                # Use new comprehensive LLM function
                llm_estimates = estimate_missing_fields_with_llm(
                    form_data,
                    df=self.df,
                    model_name=model_name
                )
                
                # Apply LLM estimates (map field names)
                if 'consumption' in llm_estimates and llm_estimates['consumption'] is not None:
                    self.record_consumption_var.set(f"{llm_estimates['consumption']:.2f}")
                    estimated_values['Consumption'] = f"{llm_estimates['consumption']:.2f} km/L"
                    estimated_sources['Consumption'] = "estimated by LLM"
                if 'fuel_usage' in llm_estimates and llm_estimates['fuel_usage'] is not None:
                    self.record_fuel_usage_var.set(f"{llm_estimates['fuel_usage']:.2f}")
                    estimated_values['Fuel Usage'] = f"{llm_estimates['fuel_usage']:.2f} L"
                    estimated_sources['Fuel Usage'] = "estimated by LLM"
                if 'fuel_price' in llm_estimates and llm_estimates['fuel_price'] is not None:
                    fuel_price = str(llm_estimates['fuel_price'])
                    if hasattr(self, 'fuel_price_var'):
                        self.fuel_price_var.set(fuel_price)
                    estimated_values['Fuel Price'] = f"${fuel_price}/L"
                    estimated_sources['Fuel Price'] = "estimated by LLM"
                if 'duration_cost' in llm_estimates and llm_estimates['duration_cost'] is not None:
                    self.record_duration_cost_var.set(f"{llm_estimates['duration_cost']:.2f}")
                    estimated_values['Duration Cost'] = f"${llm_estimates['duration_cost']:.2f}"
                    estimated_sources['Duration Cost'] = "estimated by LLM"
                if 'distance' in llm_estimates and llm_estimates['distance'] is not None and not distance:
                    self.record_distance_var.set(f"{llm_estimates['distance']:.2f}")
                    estimated_values['Distance'] = f"{llm_estimates['distance']:.2f} km"
                    estimated_sources['Distance'] = "estimated by LLM"
                if 'duration' in llm_estimates and llm_estimates['duration'] is not None and not hours:
                    self.record_hours_var.set(f"{llm_estimates['duration']:.2f}")
                    estimated_values['Duration'] = f"{llm_estimates['duration']:.2f} hours"
                    estimated_sources['Duration'] = "estimated by LLM"
                
                # Add LLM reasoning to success message if available
                if 'reasoning' in llm_estimates:
                    estimated_sources['_llm_reasoning'] = llm_estimates['reasoning']
                    
            except Exception as e:
                # Fallback to old method if new one fails
                fuel_usage = self.record_fuel_usage_var.get()
                consumption = self.record_consumption_var.get()
                
                llm_estimates = self._estimate_missing_values_with_llm(
                    distance, hours, provider, fuel_pumped, fuel_usage, consumption,
                    fuel_price, duration_cost, historical_stats
                )
                
                # Apply LLM estimates
                if 'consumption' in llm_estimates:
                    self.record_consumption_var.set(f"{llm_estimates['consumption']:.2f}")
                    estimated_values['Consumption'] = f"{llm_estimates['consumption']:.2f} km/L"
                    estimated_sources['Consumption'] = "estimated by LLM (fallback)"
                if 'fuel_usage' in llm_estimates:
                    self.record_fuel_usage_var.set(f"{llm_estimates['fuel_usage']:.2f}")
                    estimated_values['Fuel Usage'] = f"{llm_estimates['fuel_usage']:.2f} L"
                    estimated_sources['Fuel Usage'] = "estimated by LLM (fallback)"
                if 'fuel_price' in llm_estimates:
                    fuel_price = str(llm_estimates['fuel_price'])
                    estimated_values['Fuel Price'] = f"${fuel_price}/L"
                    estimated_sources['Fuel Price'] = "estimated by LLM (fallback)"
                if 'duration_cost' in llm_estimates:
                    self.record_duration_cost_var.set(f"{llm_estimates['duration_cost']:.2f}")
                    estimated_values['Duration Cost'] = f"${llm_estimates['duration_cost']:.2f}"
                    estimated_sources['Duration Cost'] = "estimated by LLM (fallback)"
        
        # Step 5: Use standard calculation logic for total cost
        try:
            # Update auto_update_fields to recalculate with new values
            self.auto_update_fields()
            
            # Build success message
            success_msg = "Smart calculation complete!\n\n"
            if estimated_values:
                success_msg += "Estimated/calculated values:\n"
                for key, value in estimated_values.items():
                    if key != '_llm_reasoning':  # Skip internal reasoning key
                        source = estimated_sources.get(key, "calculated")
                        success_msg += f"- {key}: {value} ({source})\n"
                
                # Add LLM reasoning if available
                if '_llm_reasoning' in estimated_sources:
                    success_msg += f"\nLLM Reasoning: {estimated_sources['_llm_reasoning']}\n"
                
                success_msg += "\n"
            
            # Get the calculated total cost
            total_cost = self.record_total_cost_var.get()
            if total_cost:
                success_msg += f"Total cost: ${total_cost}"
            
            messagebox.showinfo("Smart Calculation Complete", success_msg)
            
        except Exception as e:
            messagebox.showerror(
                "Calculation Error",
                f"Error during calculation: {str(e)}"
            )

        # Update other calculated fields
        try:
            self.calculate_excel_formulas_for_current_record()
            self.update_fuel_economy_comparison()
        except Exception as e:
            # Don't block, just log
            pass

    def calculate_all_formulas(self):
        """Calculate all Excel formulas for the current record"""
        try:
            self.auto_update_fields()
            self.calculate_excel_formulas_for_current_record()
            self.update_fuel_economy_comparison()
            messagebox.showinfo(
                "Calculation Complete",
                "All formulas have been calculated successfully!",
            )
        except Exception as e:
            messagebox.showerror(
                "Calculation Error", f"Error calculating formulas: {str(e)}"
            )

    def rephrase_to_standard_format(self):
        """Rephrase the natural language input to a standard format using LLM"""
        try:
            # Get the description from the text widget
            description = self.llm_input_text.get("1.0", tk.END).strip()
            
            if not description:
                messagebox.showwarning("No Input", "Please enter a description of your rental.")
                return

            # Show loading message
            self.llm_response_text.config(state="normal")
            self.llm_response_text.delete("1.0", tk.END)
            self.llm_response_text.insert("1.0", "Rephrasing to standard format... Please wait...")
            self.llm_response_text.config(state="disabled")
            self.root.update()

            # Get model name (use the one from settings if available)
            model_name = getattr(self, "ollama_model_var", None)
            if model_name:
                model_name = model_name.get() if hasattr(model_name, "get") else "llama2"
            else:
                model_name = "llama2"

            # Define the prompt for rephrasing
            prompt = (
                "Please rephrase the following car rental description into a standard, structured format suitable "
                "for data entry, preferring fields like car model, category, provider, date, start/end time, duration, "
                "distance (km), fuel/charging info, and any cost breakdowns (if present). Use concise, consistently-labeled lines.\n\n"
                f"Description:\n{description}\n\nStandard Format:"
            )

            # Call LLM via core Ollama API
            try:
                llm_response = call_ollama_api(prompt, model_name=model_name)
            except Exception as llm_exc:
                raise RuntimeError(f"LLM Rephrase call failed: {llm_exc}")

            # Display the rephrased result to the user
            self.llm_response_text.config(state="normal")
            self.llm_response_text.delete("1.0", tk.END)
            self.llm_response_text.insert("1.0", llm_response.strip() if llm_response else "No response from LLM.")
            self.llm_response_text.config(state="disabled")

        except Exception as e:
            self.llm_response_text.config(state="normal")
            self.llm_response_text.delete("1.0", tk.END)
            self.llm_response_text.insert("1.0", f"❌ Error: {str(e)}\n\nPlease ensure Ollama is running and try again.")
            self.llm_response_text.config(state="disabled")
            messagebox.showerror("LLM Processing Error", f"Failed to rephrase description: {str(e)}")

    def process_natural_language_input(self):
        """Process natural language rental description using LLM"""
        try:
            # Get the description from the text widget
            description = self.llm_input_text.get("1.0", tk.END).strip()
            
            if not description:
                messagebox.showwarning("No Input", "Please enter a description of your rental.")
                return
            
            # Show loading message
            self.llm_response_text.config(state="normal")
            self.llm_response_text.delete("1.0", tk.END)
            self.llm_response_text.insert("1.0", "Processing with LLM... Please wait...")
            self.llm_response_text.config(state="disabled")
            self.root.update()
            
            # Get model name (use the one from settings if available)
            model_name = getattr(self, "ollama_model_var", None)
            if model_name:
                model_name = model_name.get() if hasattr(model_name, "get") else "llama2"
            else:
                model_name = "llama2"
            
            # Call LLM parser
            extracted_data = parse_rental_description_with_llm(
                description,
                df=self.df,
                model_name=model_name
            )
            
            self.llm_extracted_data = extracted_data  # Save LLM extraction

            # Compose the standard format
            car_model = extracted_data.get('car_model') or "N/A"
            car_category = extracted_data.get('car_category') or "N/A"
            start_time = extracted_data.get('start_time') or "N/A"
            end_time = extracted_data.get('end_time') or "N/A"
            duration = extracted_data.get('duration')
            date = extracted_data.get('date') or "N/A"
            distance = extracted_data.get('distance')
            duration_cost = extracted_data.get('duration_cost')
            additional_details = extracted_data.get('additional_details', "")

            # Attempt fallback for missing keys from other fields
            if not duration:
                duration = extracted_data.get('duration_hours') or extracted_data.get('duration_text') or "N/A"
            if not distance:
                distance = extracted_data.get('distance_travelled') or extracted_data.get('distance_km') or "N/A"
            if not duration_cost:
                duration_cost = extracted_data.get('duration_cost') or extracted_data.get('cost_duration') or "N/A"
            if not additional_details:
                details_parts = []
                fuel = extracted_data.get('fuel_pumped') or extracted_data.get('fuel_usage')
                if fuel:
                    details_parts.append(f"Fuel pumped/used: {fuel} L")
                total_cost = extracted_data.get('total_cost')
                if total_cost:
                    details_parts.append(f"Total cost: ${total_cost}")
                provider = extracted_data.get('provider')
                if provider:
                    details_parts.append(f"Provider: {provider}")
                notes = extracted_data.get('notes') or extracted_data.get('reasoning')
                if notes:
                    details_parts.append(f"Notes: {notes}")
                additional_details = "; ".join(details_parts) if details_parts else "N/A"

            # Try to format hours for duration
            duration_str = str(duration)
            try:
                # If duration is numeric and float, format to one decimal if needed
                duration_val = float(duration)
                duration_str = f"{duration_val:.1f}" if duration_val % 1 else f"{int(duration_val)}"
            except Exception:
                duration_str = str(duration)
            
            standard_sentence = (
                f"Rented a {car_model} under {car_category} from {start_time} to {end_time} "
                f"({duration_str} hours) on {date}. "
                f"Travelled {distance}. "
                f"Duration cost was {duration_cost}. "
                f"Additional cost and details are as follow: {additional_details}"
            )

            # Display standardized output
            self.llm_response_text.config(state="normal")
            self.llm_response_text.delete("1.0", tk.END)
            self.llm_response_text.insert("1.0", f"{standard_sentence}\n")
            self.llm_response_text.config(state="disabled")

        except Exception as e:
            self.llm_response_text.config(state="normal")
            self.llm_response_text.delete("1.0", tk.END)
            self.llm_response_text.insert(
                "1.0",
                f"❌ Error: {str(e)}\n\nPlease ensure Ollama is running and try again."
            )
            self.llm_response_text.config(state="disabled")
            messagebox.showerror("LLM Processing Error", f"Failed to process description: {str(e)}")

    def fill_form_from_llm(self):
        """Fill the form with data extracted by LLM"""
        if not self.llm_extracted_data:
            messagebox.showwarning("No Data", "Please process a description with LLM first.")
            return
        
        # Use populate_form_from_llm_data to fill the form
        self.populate_form_from_llm_data(self.llm_extracted_data)

    def populate_form_from_llm_data(self, llm_data):
        """Populate form fields from LLM-extracted data"""
        try:
            # Ask for confirmation
            if llm_data.get("confidence", 0) < 0.5:
                response = messagebox.askyesno(
                    "Low Confidence",
                    f"The LLM extraction has low confidence ({llm_data.get('confidence', 0):.1%}).\n"
                    "Do you still want to fill the form with these values?\n\n"
                    f"Reasoning: {llm_data.get('reasoning', 'N/A')}"
                )
                if not response:
                    return
            
            # Map LLM data to form fields
            if llm_data.get("date"):
                try:
                    date_str = llm_data["date"]
                    if isinstance(date_str, pd.Timestamp):
                        date_str = date_str.strftime("%d/%m/%Y")
                    elif isinstance(date_str, str):
                        # Try to parse and reformat
                        try:
                            date_obj = pd.to_datetime(date_str)
                            date_str = date_obj.strftime("%d/%m/%Y")
                        except:
                            pass
                    self.record_date_var.set(date_str)
                except:
                    pass
            
            if llm_data.get("provider"):
                provider = llm_data["provider"]
                # Map common variations
                provider_map = {
                    "Getgo": "Getgo",
                    "GetGo": "Getgo",
                    "getgo": "Getgo",
                    "Getgo(EV)": "Getgo(EV)",
                    "Getgo EV": "Getgo(EV)",
                    "Car Club": "Car Club",
                    "car club": "Car Club",
                    "Econ": "Econ",
                    "Stand": "Stand",
                    "Tribecar": "Tribecar"
                }
                provider = provider_map.get(provider, provider)
                if provider in ["Getgo", "Car Club", "Econ", "Stand", "Getgo(EV)", "Tribecar"]:
                    self.record_provider_var.set(provider)
            
            if llm_data.get("car_model"):
                self.record_car_model_var.set(str(llm_data["car_model"]))
            
            if llm_data.get("distance"):
                self.record_distance_var.set(str(llm_data["distance"]))
            
            if llm_data.get("duration"):
                self.record_hours_var.set(str(llm_data["duration"]))
            
            if llm_data.get("fuel_pumped"):
                self.record_fuel_pumped_var.set(str(llm_data["fuel_pumped"]))
            
            if llm_data.get("total_cost"):
                self.record_total_cost_var.set(str(llm_data["total_cost"]))
            
            if llm_data.get("is_weekend") is not None:
                self.record_weekend_var.set("weekend" if llm_data["is_weekend"] else "weekday")
            
            if llm_data.get("consumption"):
                self.record_consumption_var.set(str(llm_data["consumption"]))
            
            if llm_data.get("fuel_usage"):
                self.record_fuel_usage_var.set(str(llm_data["fuel_usage"]))
            
            # Map additional cost fields if extracted
            if llm_data.get("fuel_cost"):
                # fuel_cost maps to pumped_cost_var (Pumped fuel cost)
                self.record_pumped_cost_var.set(str(llm_data["fuel_cost"]))
            
            if llm_data.get("mileage_cost"):
                self.record_mileage_cost_var.set(str(llm_data["mileage_cost"]))
            
            if llm_data.get("duration_cost"):
                self.record_duration_cost_var.set(str(llm_data["duration_cost"]))
            
            if llm_data.get("kwh_used"):
                self.record_kwh_used_var.set(str(llm_data["kwh_used"]))
            
            if llm_data.get("electricity_cost"):
                self.record_electricity_cost_var.set(str(llm_data["electricity_cost"]))
            
            # Track which fields were successfully extracted
            extracted_fields = []
            missing_fields = []
            
            field_mapping = {
                "date": "Date",
                "provider": "Provider (Car Cat)",
                "car_model": "Car Model",
                "distance": "Distance (KM)",
                "duration": "Rental Hour",
                "fuel_pumped": "Fuel Pumped",
                "fuel_usage": "Fuel Usage",
                "consumption": "Consumption (KM/L)",
                "total_cost": "Total Cost",
                "is_weekend": "Weekday/Weekend",
                "fuel_cost": "Fuel Cost",
                "mileage_cost": "Mileage Cost",
                "duration_cost": "Duration Cost",
                "kwh_used": "kWh Used",
                "electricity_cost": "Electricity Cost"
            }
            
            for field_key, field_name in field_mapping.items():
                if llm_data.get(field_key) is not None and llm_data.get(field_key) != "":
                    extracted_fields.append(field_name)
                else:
                    missing_fields.append(field_name)
            
            # Trigger auto-update to calculate derived fields
            self.auto_update_fields()
            
            # Build feedback message
            feedback_msg = f"Form has been populated with LLM-extracted data.\n\n"
            feedback_msg += f"Confidence: {llm_data.get('confidence', 0):.1%}\n\n"
            
            if extracted_fields:
                feedback_msg += f"Extracted Fields ({len(extracted_fields)}):\n"
                feedback_msg += "• " + "\n• ".join(extracted_fields[:10])  # Show first 10
                if len(extracted_fields) > 10:
                    feedback_msg += f"\n... and {len(extracted_fields) - 10} more"
                feedback_msg += "\n\n"
            
            if missing_fields and len(missing_fields) < len(field_mapping):
                feedback_msg += f"Fields not found in description ({len(missing_fields)}):\n"
                feedback_msg += "• " + "\n• ".join(missing_fields[:5])  # Show first 5
                if len(missing_fields) > 5:
                    feedback_msg += f"\n... and {len(missing_fields) - 5} more"
                feedback_msg += "\n\n"
            
            if llm_data.get("reasoning"):
                feedback_msg += f"Reasoning: {llm_data.get('reasoning')}\n\n"
            
            feedback_msg += "Please review and adjust any fields as needed before saving."
            
            messagebox.showinfo("Form Filled", feedback_msg)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to populate form: {str(e)}")

    def llm_assisted_form_fill(self):
        """Use LLM to intelligently fill missing form fields based on current input and historical data"""
        try:
            # Get current form state
            current_form_data = {
                "date": self.record_date_var.get(),
                "provider": self.record_provider_var.get(),
                "car_model": self.record_car_model_var.get(),
                "distance": self.record_distance_var.get(),
                "duration": self.record_hours_var.get(),
                "fuel_pumped": self.record_fuel_pumped_var.get(),
                "fuel_usage": self.record_fuel_usage_var.get(),
                "consumption": self.record_consumption_var.get(),
                "total_cost": self.record_total_cost_var.get(),
                "duration_cost": self.record_duration_cost_var.get(),
                "is_weekend": self.record_weekend_var.get(),
            }
            
            # Convert empty strings to None
            for key, value in current_form_data.items():
                if value == "":
                    current_form_data[key] = None
            
            # Check if we have minimum required fields
            if not current_form_data.get("provider"):
                messagebox.showwarning("Missing Provider", "Please select a provider first.")
                return
            
            if not current_form_data.get("distance") and not current_form_data.get("duration"):
                messagebox.showwarning(
                    "Insufficient Data",
                    "Please provide at least distance or duration to enable LLM assistance."
                )
                return
            
            # Show loading
            loading_window = tk.Toplevel(self.root)
            loading_window.title("LLM Processing")
            loading_window.geometry("300x100")
            loading_label = ttk.Label(loading_window, text="Processing with LLM... Please wait...")
            loading_label.pack(pady=20)
            self.root.update()
            
            # Get model name
            model_name = getattr(self, "ollama_model_var", None)
            if model_name:
                model_name = model_name.get() if hasattr(model_name, "get") else "llama2"
            else:
                model_name = "llama2"
            
            # Call LLM to estimate missing fields
            estimates = estimate_missing_fields_with_llm(
                current_form_data,
                df=self.df,
                model_name=model_name
            )
            
            loading_window.destroy()
            
            # Apply estimates to form
            applied_fields = []
            confidence = estimates.get("confidence", 0.5)
            
            # Map estimates to form fields (handle various field name formats)
            field_mapping = {
                "distance": ("record_distance_var", "Distance"),
                "duration": ("record_hours_var", "Duration"),
                "fuel_pumped": ("record_fuel_pumped_var", "Fuel Pumped"),
                "fuel_usage": ("record_fuel_usage_var", "Fuel Usage"),
                "consumption": ("record_consumption_var", "Consumption"),
                "total_cost": ("record_total_cost_var", "Total Cost"),
                "duration_cost": ("record_duration_cost_var", "Duration Cost"),
            }
            
            for field_key, (var_name, display_name) in field_mapping.items():
                if field_key in estimates and estimates[field_key] is not None:
                    # Only fill if field is currently empty
                    current_value = getattr(self, var_name).get()
                    if not current_value or current_value == "":
                        try:
                            value = estimates[field_key]
                            if isinstance(value, (int, float)):
                                getattr(self, var_name).set(f"{value:.2f}")
                            else:
                                getattr(self, var_name).set(str(value))
                            applied_fields.append(f"{display_name}: {value}")
                        except:
                            pass
            
            # Trigger auto-update
            self.auto_update_fields()
            
            # Show results
            if applied_fields:
                message = f"LLM Assistance Complete!\n\n"
                message += f"Confidence: {confidence:.1%}\n\n"
                message += f"Reasoning: {estimates.get('reasoning', 'N/A')}\n\n"
                message += "Fields filled:\n"
                for field in applied_fields:
                    message += f"- {field}\n"
                messagebox.showinfo("LLM Form Fill", message)
            else:
                messagebox.showinfo(
                    "LLM Form Fill",
                    f"No fields were filled. All required fields may already have values.\n\n"
                    f"Reasoning: {estimates.get('reasoning', 'N/A')}"
                )
            
        except Exception as e:
            messagebox.showerror("LLM Error", f"Failed to get LLM assistance: {str(e)}")

    def browse_file(self):
        """Open file browser to select data file"""
        filename = filedialog.askopenfilename(
            initialdir="./",
            title="Select CSV File",
            filetypes=(("CSV files", "*.csv"), ("All files", "*.*")),
        )
        if filename:
            self.data_file_var.set(filename)
            # Update file path display
            self.file_path_var.set(filename)
            # Auto-load the selected file
            self.load_data_file(filename)

    def load_data_action(self):
        """Load data from the selected file"""
        file_path = self.data_file_var.get()
        if not file_path:
            error_msg = "No file selected. Please browse and select a file first."
            self.add_error_message(error_msg)
            messagebox.showwarning("No File", error_msg)
            return
        self.load_data_file(file_path)

    def show_data_quality_report(self):
        """Show the last data cleaning pipeline quality report in a dialog."""
        report = getattr(self, "_last_quality_report", None)
        if report is None:
            messagebox.showinfo(
                "Data quality report",
                "No report available. Load a data file first to run the cleaning pipeline.",
            )
            return
        lines = [
            "Data cleaning pipeline — last run",
            "",
            f"Rows in:  {report.get('rows_in', '—')}",
            f"Rows out: {report.get('rows_out', '—')}",
            f"Duplicates removed: {report.get('duplicates_removed', 0)}",
            f"Outliers capped: {report.get('outliers_capped', 0)}",
            f"Schema valid: {report.get('schema_valid', True)}",
        ]
        errors = report.get("schema_errors", [])
        if errors:
            lines.append("")
            lines.append("Schema messages:")
            for e in errors:
                lines.append(f"  • {e}")
        messagebox.showinfo("Data quality report", "\n".join(lines))

    def load_data_file(self, file_path, show_dialog=True):
        """Load and process data from file asynchronously"""
        if not file_path or not os.path.exists(file_path):
            error_msg = f"File not found: {file_path}"
            self.add_error_message(error_msg)
            messagebox.showerror("Error", error_msg)
            return
        
        def _load_in_thread():
            loading = None
            if show_dialog:
                loading = LoadingDialog(self.root, "Loading Data", f"Loading and processing {os.path.basename(file_path)}...")
                loading.show()
            
            try:
                # Run automated data cleaning pipeline (schema -> load -> enhance -> deduplicate)
                df, quality_report = run_cleaning_pipeline(file_path)
                cost_analysis = create_complete_cost_analysis(df, region=self._get_current_region())
                self._last_quality_report = quality_report
                # Log pipeline report for data management visibility
                print("[Data cleaning pipeline]", quality_report)
                
                def _update_ui():
                    if loading:
                        loading.hide()
                    self.df = df
                    self.cost_analysis = cost_analysis
                    
                    # Update file path display
                    self.data_file_var.set(os.path.basename(file_path))
                    self.file_path_var.set(file_path)
                    
                    success_msg = f"Data loaded successfully from {os.path.basename(file_path)}"
                    # Append pipeline summary (rows, duplicates removed, schema)
                    r_in = quality_report.get("rows_in", 0)
                    r_out = quality_report.get("rows_out", 0)
                    dup = quality_report.get("duplicates_removed", 0)
                    if dup > 0 or r_in != r_out:
                        success_msg += f" — {r_out} rows"
                        if dup > 0:
                            success_msg += f", {dup} duplicate(s) removed"
                    if not quality_report.get("schema_valid", True):
                        success_msg += " (schema warnings — some columns missing)"
                    self.add_success_message(success_msg)
                    if show_dialog:
                        messagebox.showinfo("Success", success_msg)

                    # Remove message labels once data is loaded
                    if hasattr(self, "message_label"):
                        self.message_label.place_forget()
                    if hasattr(self, "analysis_label"):
                        self.analysis_label.place_forget()

                    # Refresh records if tab exists
                    if hasattr(self, "records_tree"):
                        self.refresh_records()
                
                self.root.after(0, _update_ui)
                
            except Exception as e:
                def _update_ui_error():
                    if loading:
                        loading.hide()
                    error_msg = f"Failed to load data: {str(e)}"
                    self.add_error_message(error_msg)
                    messagebox.showerror("Error", error_msg)
                self.root.after(0, _update_ui_error)
        
        thread = threading.Thread(target=_load_in_thread, daemon=True)
        thread.start()

    def browse_upload_file(self):
        """Open file browser to select file for upload"""
        filename = filedialog.askopenfilename(
            initialdir="./",
            title="Select File to Upload",
            filetypes=(
                ("Excel files", "*.xlsx"),
                ("CSV files", "*.csv"),
                ("All files", "*.*"),
            ),
        )
        if filename:
            self.upload_file_var.set(filename)
            self.upload_status_var.set(f"File selected: {os.path.basename(filename)}")

    def preview_upload_file(self):
        """Preview the file contents before uploading"""
        file_path = self.upload_file_var.get()
        if not file_path:
            messagebox.showwarning("No File", "Please select a file to preview first.")
            return

        try:
            # Load the file for preview
            preview_df = load_data(file_path)

            # Create preview window
            preview_window = tk.Toplevel(self.root)
            preview_window.title(f"File Preview - {os.path.basename(file_path)}")
            preview_window.geometry("800x600")
            preview_window.resizable(True, True)

            # Create frame for preview content
            preview_frame = ttk.Frame(preview_window)
            preview_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

            # File info
            info_frame = ttk.LabelFrame(preview_frame, text="File Information")
            info_frame.pack(fill=tk.X, pady=(0, 10))

            ttk.Label(info_frame, text=f"File: {os.path.basename(file_path)}").pack(
                anchor=tk.W, padx=5, pady=2
            )
            ttk.Label(info_frame, text=f"Records: {len(preview_df)}").pack(
                anchor=tk.W, padx=5, pady=2
            )
            ttk.Label(info_frame, text=f"Columns: {len(preview_df.columns)}").pack(
                anchor=tk.W, padx=5, pady=2
            )

            # Show column names
            columns_text = ", ".join(preview_df.columns.tolist())
            ttk.Label(info_frame, text=f"Columns: {columns_text}").pack(
                anchor=tk.W, padx=5, pady=2
            )

            # Data preview
            data_frame = ttk.LabelFrame(
                preview_frame, text="Data Preview (First 10 rows)"
            )
            data_frame.pack(fill=tk.BOTH, expand=True)

            # Create treeview for data preview
            columns = list(preview_df.columns)
            preview_tree = ttk.Treeview(
                data_frame, columns=columns, show="headings", height=10
            )

            # Set column headings
            for col in columns:
                preview_tree.heading(col, text=col)
                preview_tree.column(col, width=100, anchor="center")

            # Add scrollbars
            y_scrollbar = ttk.Scrollbar(
                data_frame, orient="vertical", command=preview_tree.yview
            )
            x_scrollbar = ttk.Scrollbar(
                data_frame, orient="horizontal", command=preview_tree.xview
            )
            preview_tree.configure(
                yscrollcommand=y_scrollbar.set, xscrollcommand=x_scrollbar.set
            )

            # Pack treeview and scrollbars
            preview_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            x_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)

            # Add data to treeview (first 10 rows)
            for idx, row in preview_df.head(10).iterrows():
                values = []
                for col in columns:
                    value = row[col]
                    if pd.isna(value):
                        values.append("")
                    elif isinstance(value, (int, float)):
                        values.append(
                            f"{value:.2f}" if isinstance(value, float) else str(value)
                        )
                    else:
                        values.append(str(value))
                preview_tree.insert("", tk.END, values=values)

            # Close button
            ttk.Button(
                preview_frame, text="Close", command=preview_window.destroy
            ).pack(pady=10)

        except Exception as e:
            error_msg = f"Failed to preview file: {str(e)}"
            messagebox.showerror("Preview Error", error_msg)

    def upload_file_action(self):
        """Handle file upload based on selected mode"""
        file_path = self.upload_file_var.get()
        if not file_path:
            messagebox.showwarning("No File", "Please select a file to upload first.")
            return

        upload_mode = self.upload_mode_var.get()

        try:
            # Run cleaning pipeline on the new file
            new_df, _ = run_cleaning_pipeline(file_path)

            if upload_mode == "Replace Current Data":
                # Replace current data
                self.df = new_df
                self.cost_analysis = create_complete_cost_analysis(self.df, region=self._get_current_region())

                # Update the main data file path
                self.data_file_var.set(file_path)
                if hasattr(self, "file_path_var"):
                    self.file_path_var.set(file_path)

                success_msg = (
                    f"Data replaced successfully with {os.path.basename(file_path)}"
                )
                self.upload_status_var.set(success_msg)
                messagebox.showinfo("Success", success_msg)

            else:  # Add to Current Data
                if self.df is None or self.df.empty:
                    # If no current data, just load the new file
                    self.df = new_df
                    self.cost_analysis = create_complete_cost_analysis(self.df, region=self._get_current_region())
                    self.data_file_var.set(file_path)
                    if hasattr(self, "file_path_var"):
                        self.file_path_var.set(file_path)

                    success_msg = (
                        f"Data loaded successfully from {os.path.basename(file_path)}"
                    )
                    self.upload_status_var.set(success_msg)
                    messagebox.showinfo("Success", success_msg)
                else:
                    # Combine current and new data
                    combined_df = pd.concat([self.df, new_df], ignore_index=True)

                    # Remove duplicates based on key columns if they exist
                    key_columns = [
                        "Date",
                        "Car model",
                        "Car Cat",
                        "Distance (KM)",
                        "Rental hour",
                    ]
                    existing_columns = [
                        col for col in key_columns if col in combined_df.columns
                    ]

                    if existing_columns:
                        # Remove exact duplicates
                        initial_count = len(combined_df)
                        combined_df = combined_df.drop_duplicates(
                            subset=existing_columns, keep="first"
                        )
                        final_count = len(combined_df)
                        duplicates_removed = initial_count - final_count
                    else:
                        duplicates_removed = 0

                    self.df = combined_df
                    self.cost_analysis = create_complete_cost_analysis(self.df, region=self._get_current_region())

                    # Update status
                    new_records = len(new_df)
                    total_records = len(self.df)
                    success_msg = f"Added {new_records} new records. Total: {total_records} records"
                    if duplicates_removed > 0:
                        success_msg += f" ({duplicates_removed} duplicates removed)"

                    self.upload_status_var.set(success_msg)
                    messagebox.showinfo("Success", success_msg)

                    # Ask user if they want to save the combined data
                    if messagebox.askyesno(
                        "Save Data",
                        f"Would you like to save the combined data ({total_records} records) to a new file?",
                    ):
                        self.save_combined_data()

            # Refresh all relevant displays
            if hasattr(self, "records_tree"):
                self.refresh_records()

            # Clear upload file selection
            self.upload_file_var.set("")
            self.upload_status_var.set("Upload completed successfully")

        except Exception as e:
            error_msg = f"Failed to upload file: {str(e)}"
            self.upload_status_var.set(f"Error: {str(e)}")
            messagebox.showerror("Upload Error", error_msg)

    def save_combined_data(self):
        """Save the combined data to a new file"""
        try:
            # Ask for save location
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[
                    ("CSV files", "*.csv"),
                    ("Excel files", "*.xlsx"),
                    ("All files", "*.*"),
                ],
                title="Save Combined Data",
                initialname="combined_rental_data.csv",
            )

            if file_path:
                # Save the data
                if file_path.endswith(".xlsx"):
                    self.df.to_excel(file_path, index=False)
                else:
                    self.df.to_csv(file_path, index=False)

                # Update the main data file path to the new saved file
                self.data_file_var.set(file_path)
                if hasattr(self, "file_path_var"):
                    self.file_path_var.set(file_path)

                success_msg = (
                    f"Combined data saved successfully to {os.path.basename(file_path)}"
                )
                self.upload_status_var.set(success_msg)
                messagebox.showinfo("Save Success", success_msg)

        except Exception as e:
            error_msg = f"Failed to save combined data: {str(e)}"
            self.upload_status_var.set(f"Save Error: {str(e)}")
            messagebox.showerror("Save Error", error_msg)

    def on_tab_changed(self, event):
        """Handle tab change events to ensure input fields are properly configured"""
        current_tab = self.notebook.select()
        tab_name = self.notebook.tab(current_tab, "text")

        if tab_name == "Recommendations":
            # Ensure input fields are clickable when recommendations tab is selected
            self.initialize_input_fields()
        elif tab_name == "Records Management":
            self.refresh_records()
        elif tab_name == "Data Analysis":
            # Only analyze if data is available
            if self.df is not None and not self.df.empty:
                self.update_analysis_chart()
        elif tab_name == "Cost Planning":
            # Clear previous results when switching to cost planning tab
            if hasattr(self, "results_text"):
                self.results_text.delete(1.0, tk.END)
            if hasattr(self, "scenarios_tree"):
                for item in self.scenarios_tree.get_children():
                    self.scenarios_tree.delete(item)
        elif tab_name == "Excel Formulas":
            # Clear previous results when switching to Excel formulas tab
            if hasattr(self, "comparison_text"):
                self.comparison_text.delete(1.0, tk.END)

    def ensure_input_fields_ready(self):
        """Ensure input fields are ready for interaction after application startup"""
        try:
            # Focus on the message entry for chat input
            if hasattr(self, "message_entry"):
                self.message_entry.focus_set()

            # Force update the display
            self.root.update_idletasks()

            # print("Chat interface initialized and ready for interaction")
        except Exception as e:
            print(f"Warning: Could not initialize chat interface: {e}")

    def show_ml_help(self, event=None):
        """Show help information about machine learning recommendations"""
        help_text = """
Machine Learning Recommendations:

The system uses machine learning to provide more accurate cost predictions based on your historical rental data.

Features:
• Analyzes patterns in your past rentals
• Considers distance, duration, provider, and weekend factors
• Provides confidence scores for predictions
• Falls back to traditional methods when ML data is insufficient

Requirements:
• At least 10 historical rental records for ML predictions
• More data = higher confidence scores
• Works best with diverse rental patterns

The ML model uses Random Forest regression to predict costs based on your actual usage patterns, making recommendations more personalized to your rental behavior.
        """
        messagebox.showinfo("Machine Learning Help", help_text)

    def show_ollama_help(self, event=None):
        """Show help information about Ollama LLM recommendations"""
        help_text = """
Ollama LLM Recommendations:

The system uses Ollama (Local Large Language Model) to provide intelligent, personalized car rental recommendations based on your historical data.

USER PROFILE:
The AI considers you as a 24-year-old male with 3 years of driving experience who is:
• Value-conscious and cost-effective
• Wants to maximize time and money spent
• Plans to make full use of rentals (errands, leisure, sightseeing)
• Decently confident in driving

Features:
• AI-powered analysis tailored to your profile
• Personalized reasoning for recommendations
• Considers value for money, reliability, and versatility
• Detailed explanations for each recommendation
• Works with various Ollama models (llama2, mistral, etc.)

Requirements:
• Ollama must be installed and running locally
• At least one Ollama model downloaded (e.g., llama2)
• Historical rental data for context
• Internet connection for initial model download

Setup Instructions:
1. Install Ollama from https://ollama.ai
2. Download a model: ollama pull llama2
3. Start Ollama service: ollama serve
4. Select your preferred model in the dropdown

The LLM analyzes your historical data with your specific profile in mind, providing recommendations that match your value-conscious approach and desire to maximize rental benefits.
        """
        messagebox.showinfo("Ollama LLM Help", help_text)

    def show_recommendation_details(self, event=None):
        """Show detailed explanation for a selected recommendation"""
        selection = self.results_tree.selection()
        if not selection:
            return

        # Get the selected item
        item = selection[0]
        values = self.results_tree.item(item, "values")

        if len(values) < 6:
            return

        provider, car_model, cost, method, confidence, display_reasoning = values[:6]

        # Try to get the full reasoning from the stored data
        full_reasoning = self.results_tree.set(item, "full_reasoning")
        if not full_reasoning:
            # Fallback to display reasoning if full reasoning not available
            full_reasoning = display_reasoning
            if display_reasoning.endswith("..."):
                # If it was truncated, try to reconstruct a more detailed explanation
                if method == "Ollama Analysis":
                    full_reasoning = f"AI-powered recommendation for {provider}: {display_reasoning[:-3]}...\n\nThis recommendation is based on your profile as a {self.user_age}-year-old value-conscious driver with {self.user_experience_years} years of experience who wants to maximize rental value for errands, leisure, and sightseeing. The AI analyzed your historical rental patterns and current trip requirements to provide this personalized suggestion."
                elif method == "ML Prediction":
                    full_reasoning = f"Machine learning prediction for {provider}: {display_reasoning[:-3]}...\n\nThis recommendation is based on statistical analysis of your historical rental data, considering patterns in distance, duration, provider preferences, and cost efficiency."
                else:
                    full_reasoning = f"Historical analysis for {provider}: {display_reasoning[:-3]}...\n\nThis recommendation is based on traditional cost analysis using your historical rental data and current pricing patterns."

        # Create detailed explanation
        details = f"""
Recommendation Details:

Provider: {provider}
Car Model: {car_model}
Estimated Cost: {cost}
Method: {method}
Confidence: {confidence}

Explanation:
{full_reasoning if full_reasoning else "No detailed explanation available for this recommendation."}

Profile Context:
This recommendation considers your profile as a {self.user_age}-year-old value-conscious driver with {self.user_experience_years} years of experience who wants to maximize rental value for errands, leisure, and sightseeing.

Tip: Ollama recommendations are personalized based on your user profile and historical rental patterns to help you make the most cost-effective decision.
        """

        # Show in a new window
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"Recommendation Details - {provider}")
        detail_window.resizable(True, True)

        # Add text widget with scrollbar
        text_frame = ttk.Frame(detail_window)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        text_widget = tk.Text(text_frame, wrap=tk.WORD, padx=10, pady=10)
        scrollbar = ttk.Scrollbar(
            text_frame, orient=tk.VERTICAL, command=text_widget.yview
        )
        text_widget.configure(yscrollcommand=scrollbar.set)

        text_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Insert the details
        text_widget.insert(tk.END, details)
        text_widget.config(state=tk.DISABLED)  # Make read-only

        # Add close button
        close_button = ttk.Button(
            detail_window, text="Close", command=detail_window.destroy
        )
        close_button.pack(pady=10)

    def show_recommendation_chart(self, recommendations=None):
        """Display a horizontal bar chart comparing recommendation costs, optimized for clarity and mobile-friendly layout."""
        self.ax.clear()
        if not recommendations:
            self.canvas.draw()
            return

        # Extract and limit data for readability
        top_n = 5
        data = [
            (
                rec["provider"],
                rec["model"],
                rec["total_cost"],
                rec.get("method", "Standard"),
            )
            for rec in recommendations
        ][:top_n]

        labels = [
            f"{provider} - {model}" if model != "Average" else provider
            for provider, model, _, _ in data
        ]
        costs = [cost for _, _, cost, _ in data]
        methods = [method for _, _, _, method in data]

        # Color mapping for methods
        method_colors = {
            "Ollama Analysis": "#28a745",
            "ML Prediction": "#4a90e2",
            "Historical Analysis": "#f39c12",
        }
        colors = [method_colors.get(m, "#95a5a6") for m in methods]

        # Plot horizontal bar chart
        bars = self.ax.barh(labels, costs, color=colors, height=0.45)

        # Add value labels to bars
        for bar in bars:
            width = bar.get_width()
            self.ax.text(
                width + max(costs) * 0.01,
                bar.get_y() + bar.get_height() / 2,
                f"${width:.2f}",
                ha="left",
                va="center",
                fontsize=10,
            )

        # Improve chart aesthetics for mobile/small screens
        self.ax.set_title("Cost Comparison", fontsize=13, pad=8)
        self.ax.set_xlabel("Estimated Cost ($)", fontsize=10)
        self.ax.tick_params(axis="y", labelsize=10)
        self.ax.tick_params(axis="x", labelsize=9)
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["top"].set_visible(False)
        self.ax.grid(axis="x", linestyle="--", alpha=0.5)

        # Custom legend
        from matplotlib.patches import Patch
        legend_labels = [
            ("Ollama Analysis", "#28a745"),
            ("ML Prediction", "#4a90e2"),
            ("Historical Analysis", "#f39c12"),
            ("Default Pricing", "#95a5a6"),
        ]
        legend_elements = [Patch(facecolor=color, label=label) for label, color in legend_labels]
        self.ax.legend(handles=legend_elements, loc="upper right", fontsize=9, frameon=False)

        plt.tight_layout()
        self.canvas.draw()
    def save_settings(self):
        """Save current settings to a JSON file"""
        settings_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "settings.json"
        )
        try:
            # Update user profile in settings before saving
            self.settings["user_age"] = self.user_age
            self.settings["user_experience_years"] = self.user_experience_years
            self.settings["apply_esso_sg_discount"] = self.apply_esso_sg_discount_var.get()
            with open(settings_file, "w") as f:
                json.dump(self.settings, f)
            print(f"Settings saved to {settings_file}")
        except Exception as e:
            print(f"Error saving settings: {str(e)}")

    def load_settings(self):
        """Load settings from JSON file"""
        settings_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "settings.json"
        )
        try:
            if os.path.exists(settings_file):
                with open(settings_file, "r") as f:
                    self.settings = json.load(f)
                print(f"Settings loaded from {settings_file}")
            else:
                # Set default settings if file doesn't exist
                self.settings = {
                    "fuel_cost_per_liter": 2.51,
                    "full_tank_cost": 20.0,
                    "default_provider": "Getgo",
                    "default_car_model": "Generic",
                    "car_model_tank_capacities": {},
                    "user_age": 25,
                    "user_experience_years": 5,
                }
                print("Using default settings")
        except Exception as e:
            print(f"Error loading settings: {str(e)}")
            # Set default settings if there's an error
            self.settings = {
                "fuel_cost_per_liter": 2.51,
                "full_tank_cost": 20.0,
                "default_provider": "Getgo",
                "default_car_model": "Generic",
                "car_model_tank_capacities": {},
                "user_age": 25,
                "user_experience_years": 5,
            }
            # Ensure car_model_tank_capacities exists even if loaded from file
        if "car_model_tank_capacities" not in self.settings:
            self.settings["car_model_tank_capacities"] = {}
        
        # Load user profile from settings
        if "user_age" in self.settings:
            self.user_age = int(self.settings["user_age"])
        if "user_experience_years" in self.settings:
            self.user_experience_years = int(self.settings["user_experience_years"])
        if "apply_esso_sg_discount" in self.settings:
            self.apply_esso_sg_discount_var.set(bool(self.settings["apply_esso_sg_discount"]))

    def _on_esso_discount_toggled(self):
        """When Esso Singapore discount checkbox is toggled, refresh record form calculations."""
        if hasattr(self, "auto_update_fields"):
            self.auto_update_fields()

    def refresh_records(self):
        """Refresh the records list in the treeview"""
        if self.df is None:
            # Clear and show empty state
            for item in self.records_tree.get_children():
                self.records_tree.delete(item)
            self.records_tree.insert("", "end", values=("No data loaded", "", "", "", "", "", "", ""))
            return

        # Clear existing records
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)

        # Check if dataframe is empty
        if self.df.empty:
            self.records_tree.insert("", "end", values=("No records available", "", "", "", "", "", "", ""))
            return

        # Add records from dataframe
        for idx, row in self.df.iterrows():
            try:
                # Format date for display
                date_str = (
                    row["Date"].strftime("%d/%m/%Y") if pd.notna(row["Date"]) else ""
                )

                # Add record to tree with index as ID
                self.records_tree.insert(
                    "",
                    "end",
                    iid=str(idx),
                    values=(
                        date_str,
                        row["Car model"] if pd.notna(row["Car model"]) else "",
                        row["Car Cat"] if pd.notna(row["Car Cat"]) else "",
                        (
                            f"{row['Distance (KM)']:.2f}"
                            if pd.notna(row["Distance (KM)"])
                            else ""
                        ),
                        (
                            f"{row['Rental hour']:.2f}"
                            if pd.notna(row["Rental hour"])
                            else ""
                        ),
                        f"${row['Total']:.2f}" if pd.notna(row["Total"]) else "",
                        (
                            f"{row['Estimated fuel usage']:.2f}"
                            if pd.notna(row["Estimated fuel usage"])
                            else ""
                        ),
                        (
                            f"{row['Consumption (KM/L)']:.2f}"
                            if pd.notna(row["Consumption (KM/L)"])
                            else ""
                        ),
                    ),
                )
            except Exception as e:
                # Skip problematic records
                print(f"Error adding record {idx}: {e}")
                continue

    def on_record_select(self, event):
        """Handle record selection in the treeview"""
        selected_items = self.records_tree.selection()
        if not selected_items:
            return

        # Get the selected record's index
        idx = int(selected_items[0])
        self.current_record_index = idx

        # Get the record data
        row = self.df.iloc[idx]

        # Region and provider (region determines provider list)
        region = row.get("Region", "Singapore")
        if pd.notna(region) and str(region).strip() in VALID_REGIONS:
            self.record_region_var.set(str(region).strip())
        else:
            self.record_region_var.set("Singapore")
        if hasattr(self, "record_provider_combo") and self.record_provider_combo is not None:
            self.record_provider_combo["values"] = get_providers_for_region(self.record_region_var.get())
        self.record_provider_var.set(row["Car Cat"] if pd.notna(row["Car Cat"]) else "")

        # Populate the form fields
        self.record_date_var.set(
            row["Date"].strftime("%d/%m/%Y") if pd.notna(row["Date"]) else ""
        )
        self.record_car_model_var.set(
            row["Car model"] if pd.notna(row["Car model"]) else ""
        )
        self.record_distance_var.set(
            f"{row['Distance (KM)']}" if pd.notna(row["Distance (KM)"]) else ""
        )
        self.record_hours_var.set(
            f"{row['Rental hour']}" if pd.notna(row["Rental hour"]) else ""
        )
        self.record_fuel_pumped_var.set(
            f"{row['Fuel pumped']}".replace(" L", "")
            if pd.notna(row["Fuel pumped"])
            else ""
        )
        self.record_fuel_usage_var.set(
            f"{row['Estimated fuel usage']}"
            if pd.notna(row["Estimated fuel usage"])
            else ""
        )
        self.record_weekend_var.set(
            row["Weekday/weekend"] if pd.notna(row["Weekday/weekend"]) else ""
        )
        self.record_total_cost_var.set(
            f"{row['Total']}" if pd.notna(row["Total"]) else ""
        )
        self.record_pumped_cost_var.set(
            f"{row['Pumped fuel cost']}".replace("$", "")
            if pd.notna(row["Pumped fuel cost"])
            else ""
        )
        self.record_cost_per_km_var.set(
            f"{row['Cost per KM']}".replace("$", "")
            if pd.notna(row["Cost per KM"])
            else ""
        )
        self.record_duration_cost_var.set(
            f"{row['Duration cost']}".replace("$", "")
            if pd.notna(row["Duration cost"])
            else ""
        )
        self.record_consumption_var.set(
            f"{row['Consumption (KM/L)']}"
            if pd.notna(row["Consumption (KM/L)"])
            else ""
        )
        self.record_fuel_savings_var.set(
            f"{row['Est original fuel savings']}".replace("$", "")
            if pd.notna(row["Est original fuel savings"])
            else ""
        )
        self.record_cost_per_hr_var.set(
            f"{row['Cost/HR']}".replace("$", "") if pd.notna(row["Cost/HR"]) else ""
        )
        # NormalRental (Malaysia) optional fields
        for col, var in (
            ("Deposit (RM)", self.record_deposit_rm_var),
            ("Rental fee (RM)", self.record_rental_fee_rm_var),
            ("Additional fee (RM)", self.record_additional_fee_rm_var),
        ):
            if col in row.index and pd.notna(row.get(col)):
                try:
                    var.set(f"{row[col]}")
                except Exception:
                    var.set("")
            else:
                var.set("")

        # Handle EV-specific fields
        if row["Car Cat"] == "Getgo(EV)":
            # For EV records, populate kWh and electricity cost fields
            # These might not exist in the original data, so we'll calculate them
            kwh_used = row.get("kWh Used", 0) if pd.notna(row.get("kWh Used", 0)) else 0
            electricity_cost = (
                row.get("Electricity Cost", 0)
                if pd.notna(row.get("Electricity Cost", 0))
                else 0
            )
            self.record_kwh_used_var.set(f"{kwh_used}" if kwh_used else "")
            self.record_electricity_cost_var.set(
                f"{electricity_cost}" if electricity_cost else ""
            )
        else:
            self.record_kwh_used_var.set("")
            self.record_electricity_cost_var.set("")
        self.on_provider_changed()

    def clear_record_form(self):
        """Clear all form fields and prepare for new record entry"""
        # Check if form has unsaved changes
        if self._form_dirty:
            if not messagebox.askyesno(
                "Unsaved Changes",
                "You have unsaved changes in the form.\n\nDo you want to clear the form and lose these changes?"
            ):
                return
        
        self.current_record_index = None
        self._form_dirty = False

        # Clear all form fields; default region Singapore and first provider
        self.record_region_var.set("Singapore")
        if hasattr(self, "record_provider_combo") and self.record_provider_combo is not None:
            self.record_provider_combo["values"] = get_providers_for_region("Singapore")
        self.record_provider_var.set("Getgo")
        self.record_date_var.set("")
        self.record_car_model_var.set("")
        self.record_distance_var.set("")
        self.record_hours_var.set("")
        self.record_fuel_pumped_var.set("")
        self.record_fuel_usage_var.set("")
        self.record_weekend_var.set("")
        self.record_total_cost_var.set("")
        self.record_pumped_cost_var.set("")
        self.record_cost_per_km_var.set("")
        self.record_duration_cost_var.set("")
        self.record_consumption_var.set("")
        self.record_fuel_savings_var.set("")
        self.record_cost_per_hr_var.set("")
        self.record_kwh_used_var.set("")
        self.record_electricity_cost_var.set("")
        self.record_deposit_rm_var.set("")
        self.record_rental_fee_rm_var.set("")
        self.record_additional_fee_rm_var.set("")

        # Clear fuel economy comparison
        if hasattr(self, "fuel_economy_comparison_text"):
            self.fuel_economy_comparison_text.config(state="normal")
            self.fuel_economy_comparison_text.delete(1.0, tk.END)
            self.fuel_economy_comparison_text.config(state="disabled")

        # Hide EV and NormalRental frames when clearing form
        if hasattr(self, "ev_frame"):
            self.ev_frame.pack_forget()
        if hasattr(self, "normal_rental_frame"):
            self.normal_rental_frame.pack_forget()

        # Update status bar
        self.status_var.set("Form cleared - Ready for new record entry")

        # Focus on the first field for better UX
        self.root.focus_set()

    def _check_form_completeness(self):
        """
        Check if required form fields are present and valid (no dialogs).
        Returns (is_complete, list_of_missing_or_invalid_field_names).
        """
        missing = []
        region = (self.record_region_var.get() or "").strip()
        if region not in VALID_REGIONS:
            region = "Singapore"
        allowed_providers = get_providers_for_region(region)
        provider = (self.record_provider_var.get() or "").strip()
        if not provider:
            missing.append("Provider")
        elif provider not in allowed_providers:
            missing.append("Provider (invalid for region)")
        date_str = self.record_date_var.get() or ""
        date_valid, _, _ = validate_date_input(
            date_str, "Date", allow_future=False, min_year=2000, required=True
        )
        if not date_valid:
            missing.append("Date")
        car_model = (self.record_car_model_var.get() or "").strip()
        if not car_model:
            missing.append("Car model")
        distance_valid, _, _ = validate_numeric_input(
            self.record_distance_var.get(), "Distance",
            min_value=1, max_value=1000, allow_zero=False, allow_negative=False, required=True
        )
        if not distance_valid:
            missing.append("Distance")
        rental_hour_valid, _, _ = validate_numeric_input(
            self.record_hours_var.get(), "Rental Hours",
            min_value=0.1, max_value=24, allow_zero=False, allow_negative=False, required=True
        )
        if not rental_hour_valid:
            missing.append("Rental hours")
        return (len(missing) == 0, missing)

    def get_form_data(self):
        """Get data from the form fields and validate it"""
        try:
            # Region (Singapore / Malaysia)
            region = (self.record_region_var.get() or "").strip()
            if region not in VALID_REGIONS:
                region = "Singapore"
            allowed_providers = get_providers_for_region(region)
            provider = self.record_provider_var.get()
            if not provider:
                self._show_user_friendly_error("Required Field", "Provider is required.", "Provider")
                return None
            if provider not in allowed_providers:
                self._show_user_friendly_error(
                    "Invalid Provider",
                    f"Provider must be one of {allowed_providers} for region {region}.",
                    "Provider",
                )
                return None

            # Validate date
            date_str = self.record_date_var.get()
            date_valid, date, date_error = validate_date_input(
                date_str, "Date", allow_future=False, min_year=2000, required=True
            )
            if not date_valid:
                self._show_user_friendly_error("Invalid Date", date_error, "Date")
                return None

            # Validate required text fields
            car_model = self.record_car_model_var.get().strip()
            if not car_model:
                self._show_user_friendly_error("Required Field", "Car model is required.", "Car Model")
                return None

            # Validate numeric fields with appropriate constraints
            # Distance: required, positive, reasonable range (1-1000 km)
            distance_valid, distance, distance_error = validate_numeric_input(
                self.record_distance_var.get(), "Distance", 
                min_value=1, max_value=1000, allow_zero=False, allow_negative=False, required=True
            )
            if not distance_valid:
                self._show_user_friendly_error("Invalid Distance", distance_error, "Distance")
                return None

            # Rental hours: required, positive, reasonable range (0.1-24 hours)
            rental_hour_valid, rental_hour, hour_error = validate_numeric_input(
                self.record_hours_var.get(), "Rental Hours",
                min_value=0.1, max_value=24, allow_zero=False, allow_negative=False, required=True
            )
            if not rental_hour_valid:
                self._show_user_friendly_error("Invalid Duration", hour_error, "Rental Hours")
                return None

            # Optional numeric fields
            fuel_pumped_valid, fuel_pumped, _ = validate_numeric_input(
                self.record_fuel_pumped_var.get(), "Fuel Pumped",
                min_value=0, allow_zero=True, allow_negative=False, required=False
            )
            if not fuel_pumped_valid:
                self._show_user_friendly_error("Invalid Fuel Pumped", 
                    "Fuel pumped must be a valid number (0 or positive).", "Fuel Pumped")
                return None

            fuel_usage_valid, fuel_usage, _ = validate_numeric_input(
                self.record_fuel_usage_var.get(), "Fuel Usage",
                min_value=0, allow_zero=True, allow_negative=False, required=False
            )
            if not fuel_usage_valid:
                self._show_user_friendly_error("Invalid Fuel Usage",
                    "Fuel usage must be a valid number (0 or positive).", "Fuel Usage")
                return None

            total_valid, total, _ = validate_numeric_input(
                self.record_total_cost_var.get(), "Total Cost",
                min_value=0, allow_zero=True, allow_negative=False, required=False
            )
            if not total_valid:
                self._show_user_friendly_error("Invalid Total Cost",
                    "Total cost must be a valid number (0 or positive).", "Total Cost")
                return None

            pumped_cost_valid, pumped_cost, _ = validate_numeric_input(
                self.record_pumped_cost_var.get(), "Pumped Fuel Cost",
                min_value=0, allow_zero=True, allow_negative=False, required=False
            )
            if not pumped_cost_valid:
                self._show_user_friendly_error("Invalid Pumped Fuel Cost",
                    "Pumped fuel cost must be a valid number (0 or positive).", "Pumped Fuel Cost")
                return None

            cost_per_km_valid, cost_per_km, _ = validate_numeric_input(
                self.record_cost_per_km_var.get(), "Cost per KM",
                min_value=0, allow_zero=True, allow_negative=False, required=False
            )
            if not cost_per_km_valid:
                self._show_user_friendly_error("Invalid Cost per KM",
                    "Cost per KM must be a valid number (0 or positive).", "Cost per KM")
                return None

            duration_cost_valid, duration_cost, _ = validate_numeric_input(
                self.record_duration_cost_var.get(), "Duration Cost",
                min_value=0, allow_zero=True, allow_negative=False, required=False
            )
            if not duration_cost_valid:
                self._show_user_friendly_error("Invalid Duration Cost",
                    "Duration cost must be a valid number (0 or positive).", "Duration Cost")
                return None

            consumption_valid, consumption, _ = validate_numeric_input(
                self.record_consumption_var.get(), "Consumption",
                min_value=0, allow_zero=True, allow_negative=False, required=False
            )
            if not consumption_valid:
                self._show_user_friendly_error("Invalid Consumption",
                    "Consumption must be a valid number (0 or positive).", "Consumption")
                return None

            fuel_savings_valid, fuel_savings, _ = validate_numeric_input(
                self.record_fuel_savings_var.get(), "Fuel Savings",
                min_value=0, allow_zero=True, allow_negative=False, required=False
            )
            if not fuel_savings_valid:
                self._show_user_friendly_error("Invalid Fuel Savings",
                    "Fuel savings must be a valid number (0 or positive).", "Fuel Savings")
                return None

            cost_per_hr_valid, cost_per_hr, _ = validate_numeric_input(
                self.record_cost_per_hr_var.get(), "Cost per Hour",
                min_value=0, allow_zero=True, allow_negative=False, required=False
            )
            if not cost_per_hr_valid:
                self._show_user_friendly_error("Invalid Cost per Hour",
                    "Cost per hour must be a valid number (0 or positive).", "Cost per Hour")
                return None

            # Validate EV-specific fields
            kwh_used_valid, kwh_used, _ = validate_numeric_input(
                self.record_kwh_used_var.get(), "kWh Used",
                min_value=0, allow_zero=True, allow_negative=False, required=False
            )
            if not kwh_used_valid:
                self._show_user_friendly_error("Invalid kWh Used",
                    "kWh used must be a valid number (0 or positive).", "kWh Used")
                return None

            electricity_cost_valid, electricity_cost, _ = validate_numeric_input(
                self.record_electricity_cost_var.get(), "Electricity Cost",
                min_value=0, allow_zero=True, allow_negative=False, required=False
            )
            if not electricity_cost_valid:
                self._show_user_friendly_error("Invalid Electricity Cost",
                    "Electricity cost must be a valid number (0 or positive).", "Electricity Cost")
                return None

            # Optional NormalRental (Malaysia) breakdown fields
            deposit_rm_val = None
            rental_fee_rm_val = None
            additional_fee_rm_val = None
            if provider == "NormalRental":
                _, deposit_rm_val, _ = validate_numeric_input(
                    self.record_deposit_rm_var.get(), "Deposit (RM)",
                    min_value=0, allow_zero=True, allow_negative=False, required=False
                )
                _, rental_fee_rm_val, _ = validate_numeric_input(
                    self.record_rental_fee_rm_var.get(), "Rental fee (RM)",
                    min_value=0, allow_zero=True, allow_negative=False, required=False
                )
                _, additional_fee_rm_val, _ = validate_numeric_input(
                    self.record_additional_fee_rm_var.get(), "Additional fee (RM)",
                    min_value=0, allow_zero=True, allow_negative=False, required=False
                )
                # Auto-sum Total from breakdown if all are filled and Total not set
                if total is None and (deposit_rm_val is not None or rental_fee_rm_val is not None or additional_fee_rm_val is not None or pumped_cost is not None):
                    total = (deposit_rm_val or 0) + (rental_fee_rm_val or 0) + (additional_fee_rm_val or 0) + (pumped_cost or 0)

            weekend = self.record_weekend_var.get()

            # Create record dict
            record = {
                "Region": region,
                "Date": date,
                "Car model": car_model,
                "Car Cat": provider,
                "Distance (KM)": distance,
                "Rental hour": rental_hour,
                "Fuel pumped": f"{fuel_pumped} L" if fuel_pumped is not None else None,
                "Estimated fuel usage": fuel_usage,
                "Consumption (KM/L)": consumption,
                "Pumped fuel cost": (
                    f"${pumped_cost}" if pumped_cost is not None else None
                ),
                "Cost per KM": cost_per_km,
                "Duration cost": duration_cost,
                "Total": total,
                "Est original fuel savings": fuel_savings,
                "Weekday/weekend": weekend,
                "Cost/HR": cost_per_hr,
                "kWh Used": kwh_used,
                "Electricity Cost": electricity_cost,
            }
            if provider == "NormalRental":
                record["Deposit (RM)"] = deposit_rm_val
                record["Rental fee (RM)"] = rental_fee_rm_val
                record["Additional fee (RM)"] = additional_fee_rm_val

            return record
        except Exception as e:
            self._show_user_friendly_error(
                "Validation Error",
                f"An unexpected error occurred while validating form data: {str(e)}\n\nPlease check all fields and try again."
            )
            return None

    def add_record(self):
        """Add a new record from form data with enhanced validation and feedback"""
        if not self._check_data_loaded():
            return

        is_complete, missing = self._check_form_completeness()
        if not is_complete:
            msg = (
                "The form is incomplete. Missing or invalid:\n\n• "
                + "\n• ".join(missing)
                + "\n\nWould you like to use LLM to help fill missing fields?"
            )
            if messagebox.askyesno("Form incomplete", msg, icon="question"):
                self.llm_assisted_form_fill()
            else:
                # Show first validation error so user knows what to fix
                self.get_form_data()
            return

        record = self.get_form_data()
        if record is None:
            return

        try:
            # Add record to dataframe
            self.df = pd.concat([self.df, pd.DataFrame([record])], ignore_index=True)

            # Refresh the cost analysis
            self.cost_analysis = create_complete_cost_analysis(self.df, region=self._get_current_region())

            # Refresh the records list
            self.refresh_records()

            # Clear the form (no confirmation needed after successful save)
            self._form_dirty = False
            self.clear_record_form()

            # Show success message with record details
            car_model = record.get("Car model", "Unknown")
            distance = record.get("Distance (KM)", 0)
            total_cost = record.get("Total", 0)
            messagebox.showinfo(
                "Success",
                f"Record added successfully!\n\nCar: {car_model}\nDistance: {distance}km\nTotal Cost: ${total_cost:.2f}",
            )

            # Update status bar
            self.status_var.set(
                f"Record added - {car_model} ({distance}km, ${total_cost:.2f})"
            )

            # Save the changes
            self.save_data()
            self.auto_update_fields()
            self.refresh_records()

        except Exception as e:
            messagebox.showerror("Error", f"Failed to add record: {str(e)}")
            self.status_var.set("Error adding record")

    def update_record(self):
        """Update an existing record with form data"""
        if not self._check_data_loaded():
            return

        if self.current_record_index is None:
            self._show_user_friendly_error(
                "No Selection",
                "Please select a record to update.\n\nClick on a record in the list to select it."
            )
            return

        is_complete, missing = self._check_form_completeness()
        if not is_complete:
            msg = (
                "The form is incomplete. Missing or invalid:\n\n• "
                + "\n• ".join(missing)
                + "\n\nWould you like to use LLM to help fill missing fields?"
            )
            if messagebox.askyesno("Form incomplete", msg, icon="question"):
                self.llm_assisted_form_fill()
            else:
                self.get_form_data()
            return

        record = self.get_form_data()
        if record is None:
            return

        # Update record in dataframe
        for key, value in record.items():
            if key in self.df.columns:
                self.df.at[self.current_record_index, key] = value

        # Refresh the cost analysis
        self.cost_analysis = create_complete_cost_analysis(self.df, region=self._get_current_region())

        # Refresh the records list
        self.refresh_records()

        # Show success message
        messagebox.showinfo("Success", "Record updated successfully")

        # Save the changes
        self.save_data()
        self.auto_update_fields()

    def delete_record(self):
        """Delete the selected record"""
        if not self._check_data_loaded():
            return

        selected_items = self.records_tree.selection()
        if not selected_items:
            self._show_user_friendly_error(
                "No Selection",
                "Please select a record to delete.\n\nClick on a record in the list to select it."
            )
            return

        # Confirm deletion
        if not messagebox.askyesno(
            "Confirm", "Are you sure you want to delete the selected record?"
        ):
            return

        # Get the selected record's index
        idx = int(selected_items[0])

        # Delete record from dataframe
        self.df = self.df.drop(idx).reset_index(drop=True)

        # Refresh the cost analysis
        self.cost_analysis = create_complete_cost_analysis(self.df, region=self._get_current_region())

        # Refresh the records list
        self.refresh_records()

        # Clear the form
        self.clear_record_form()

        # Show success message
        messagebox.showinfo("Success", "Record deleted successfully")

        # Save the changes
        self.save_data()

    def save_data(self):
        """Save the data to the CSV file"""
        try:
            file_path = self.data_file_var.get()
            self.df.to_csv(file_path, index=False)
            print(f"Data saved to {file_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save data: {str(e)}")

    def export_records_data(self):
        """Export records data to CSV or Excel"""
        if not self._check_data_loaded():
            return

        # Ask for file location
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[
                ("CSV files", "*.csv"),
                ("Excel files", "*.xlsx"),
                ("All files", "*.*"),
            ],
            title="Export Rental Records",
        )

        if not file_path:
            return  # User cancelled

        try:
            # Save to file
            if file_path.endswith(".xlsx"):
                self.df.to_excel(file_path, index=False)
            else:
                self.df.to_csv(file_path, index=False)

            messagebox.showinfo(
                "Export Complete", f"Records exported successfully to {file_path}"
            )

        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export records: {str(e)}")

    def filter_records(self, event=None):
        """Filter records based on search text"""
        if self.df is None or self.df.empty:
            # Clear and show empty state
            for item in self.records_tree.get_children():
                self.records_tree.delete(item)
            if self.df is None:
                self.records_tree.insert("", "end", values=("No data loaded", "", "", "", "", "", "", ""))
            else:
                self.records_tree.insert("", "end", values=("No records available", "", "", "", "", "", "", ""))
            return

        search_text = self.search_var.get().lower()

        # Clear existing records
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)

        # If search text is empty, show all records
        if not search_text:
            self.refresh_records()
            return

        # Add matching records
        match_count = 0
        for idx, row in self.df.iterrows():
            # Check if search text appears in any of the displayed columns
            date_str = row["Date"].strftime("%d/%m/%Y") if pd.notna(row["Date"]) else ""
            car_model = str(row["Car model"]) if pd.notna(row["Car model"]) else ""
            provider = str(row["Car Cat"]) if pd.notna(row["Car Cat"]) else ""

            if (
                search_text in date_str.lower()
                or search_text in car_model.lower()
                or search_text in provider.lower()
            ):
                self.records_tree.insert(
                    "",
                    "end",
                    iid=str(idx),
                    values=(
                        date_str,
                        car_model,
                        provider,
                        (
                            f"{row['Distance (KM)']:.2f}"
                            if pd.notna(row["Distance (KM)"])
                            else ""
                        ),
                        (
                            f"{row['Rental hour']:.2f}"
                            if pd.notna(row["Rental hour"])
                            else ""
                        ),
                        f"${row['Total']:.2f}" if pd.notna(row["Total"]) else "",
                        (
                            f"{row['Estimated fuel usage']:.2f}"
                            if pd.notna(row["Estimated fuel usage"])
                            else ""
                        ),
                        (
                            f"{row['Consumption (KM/L)']:.2f}"
                            if pd.notna(row["Consumption (KM/L)"])
                            else ""
                        ),
                    ),
                )
                match_count += 1

        # Show empty state if no matches found
        if match_count == 0:
            self.records_tree.insert("", "end", values=(f"No records found matching '{search_text}'", "", "", "", "", "", "", ""))

        # Update status
        self.status_var.set(f"Found {match_count} matching record{'s' if match_count != 1 else ''} for '{search_text}'")

    def setup_cost_planning_tab(self):
        """Set up the budget planner tab with ML-based spending predictions"""
        # Main container
        main_frame = ttk.Frame(self.cost_planning_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Split into left and right panes
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=False, padx=5, pady=5)

        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=5, pady=5)

        # Left panel - Budget Input and Controls
        budget_input_frame = ttk.LabelFrame(left_frame, text="💰 Budget Settings")
        budget_input_frame.pack(fill="x", expand=False, padx=5, pady=5)

        # Monthly budget input
        ttk.Label(budget_input_frame, text="Monthly Budget ($):").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        self.monthly_budget_var = tk.StringVar(value="1500")
        budget_entry = ttk.Entry(
            budget_input_frame, textvariable=self.monthly_budget_var, width=15
        )
        budget_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        # Prediction period
        ttk.Label(budget_input_frame, text="Prediction Period:").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        self.prediction_period_var = tk.StringVar(value="next_month")
        period_combo = ttk.Combobox(
            budget_input_frame,
            textvariable=self.prediction_period_var,
            values=["next_month", "next_3_months", "next_6_months", "next_year"],
            width=15,
            state="readonly",
        )
        period_combo.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        # Confidence level
        ttk.Label(budget_input_frame, text="Prediction Confidence:").grid(
            row=2, column=0, padx=5, pady=5, sticky="w"
        )
        self.confidence_level_var = tk.StringVar(value="medium")
        confidence_combo = ttk.Combobox(
            budget_input_frame,
            textvariable=self.confidence_level_var,
            values=["conservative", "medium", "optimistic"],
            width=15,
            state="readonly",
        )
        confidence_combo.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        # Generate prediction button
        ttk.Button(
            budget_input_frame,
            text="🔮 Generate Prediction",
            command=self.generate_budget_prediction,
            style="Accent.TButton",
        ).grid(row=3, column=0, columnspan=2, pady=10)

        # Budget Status Frame
        status_frame = ttk.LabelFrame(left_frame, text="📊 Budget Status")
        status_frame.pack(fill="x", expand=False, padx=5, pady=5)

        # Create status labels
        self.budget_status_labels = {}
        status_fields = [
            ("Budget Set", "budget_set"),
            ("Predicted Spending", "predicted_spending"),
            ("Budget Remaining", "budget_remaining"),
            ("Risk Level", "risk_level"),
            ("Confidence", "confidence"),
        ]

        for i, (label_text, key) in enumerate(status_fields):
            ttk.Label(status_frame, text=f"{label_text}:").grid(
                row=i, column=0, padx=5, pady=2, sticky="w"
            )
            label = ttk.Label(status_frame, text="--", font=("Arial", 9, "bold"))
            label.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            self.budget_status_labels[key] = label

        # Recommendations Frame
        recommendations_frame = ttk.LabelFrame(
            left_frame, text="💡 Smart Recommendations"
        )
        recommendations_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Create text widget for recommendations
        self.recommendations_text = tk.Text(
            recommendations_frame, wrap=tk.WORD, height=12, width=45
        )
        recommendations_scroll = ttk.Scrollbar(
            recommendations_frame,
            orient="vertical",
            command=self.recommendations_text.yview,
        )
        self.recommendations_text.configure(yscrollcommand=recommendations_scroll.set)

        self.recommendations_text.pack(side="left", fill="both", expand=True)
        recommendations_scroll.pack(side="right", fill="y")

        # Right panel - Visualizations
        # Top right - Prediction Summary
        summary_frame = ttk.LabelFrame(right_frame, text="📈 Prediction Summary")
        summary_frame.pack(fill="x", expand=False, padx=5, pady=5)

        # Create summary labels
        self.prediction_summary_labels = {}
        summary_fields = [
            ("ML Model Used", "model_used"),
            ("Data Points", "data_points"),
            ("Accuracy", "accuracy"),
            ("Trend", "trend"),
        ]

        for i, (label_text, key) in enumerate(summary_fields):
            ttk.Label(summary_frame, text=f"{label_text}:").grid(
                row=i // 2, column=(i % 2) * 2, padx=5, pady=2, sticky="w"
            )
            label = ttk.Label(summary_frame, text="--", font=("Arial", 9))
            label.grid(row=i // 2, column=(i % 2) * 2 + 1, padx=5, pady=2, sticky="w")
            self.prediction_summary_labels[key] = label

        # Bottom right - Charts
        charts_frame = ttk.LabelFrame(right_frame, text="📊 Budget Analysis Charts")
        charts_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Chart type selector
        chart_selector_frame = ttk.Frame(charts_frame)
        chart_selector_frame.pack(fill="x", expand=False, padx=5, pady=5)

        ttk.Label(chart_selector_frame, text="Chart Type:").pack(side="left", padx=5)
        self.budget_chart_type_var = tk.StringVar(value="Budget vs Prediction")
        budget_chart_combo = ttk.Combobox(
            chart_selector_frame,
            textvariable=self.budget_chart_type_var,
            values=[
                "Budget vs Prediction",
                "Spending Trends",
                "Monthly Breakdown",
                "Provider Analysis",
                "Risk Assessment",
                "Historical vs Predicted",
            ],
            width=20,
            state="readonly",
        )
        budget_chart_combo.pack(side="left", padx=5)

        # Update chart button
        ttk.Button(
            chart_selector_frame,
            text="Update Chart",
            command=self.update_budget_chart,
        ).pack(side="left", padx=5)

        # Bind chart type change
        budget_chart_combo.bind(
            "<<ComboboxSelected>>", self.on_budget_chart_type_changed
        )

        # Create matplotlib figure for budget charts
        self.budget_fig, self.budget_ax = plt.subplots(figsize=(12, 8))
        self.budget_canvas = FigureCanvasTkAgg(self.budget_fig, charts_frame)
        self.budget_canvas.get_tk_widget().pack(fill="both", expand=True)

        # Add navigation toolbar
        self.budget_toolbar = NavigationToolbar2Tk(self.budget_canvas, charts_frame)
        self.budget_toolbar.update()
        self.budget_toolbar.pack(fill="x")

        # Saved Trip Data Section
        saved_data_frame = ttk.LabelFrame(
            self.settings_tab, text="Saved Trip Data (Calculator)", padding=10
        )
        saved_data_frame.pack(fill="both", expand=True, pady=(10, 0))

        # Instructions
        ttk.Label(
            saved_data_frame,
            text="Trip data saved from Calculator tab, sorted by rental duration:",
            font=("Arial", 10),
        ).pack(anchor="w", pady=(0, 10))

        # Create saved data treeview
        saved_columns = (
            "Date",
            "Provider",
            "Distance (km)",
            "Duration (hrs)",
            "Day Type",
            "Total Cost",
            "Cost/km",
            "Cost/hr",
        )
        self.saved_data_tree = ttk.Treeview(
            saved_data_frame, columns=saved_columns, show="headings", height=8
        )

        # Configure columns
        for col in saved_columns:
            self.saved_data_tree.heading(col, text=col)
            if col == "Date":
                self.saved_data_tree.column(col, width=100, anchor="center")
            elif col == "Provider":
                self.saved_data_tree.column(col, width=120, anchor="center")
            elif col in ["Distance (km)", "Duration (hrs)"]:
                self.saved_data_tree.column(col, width=80, anchor="center")
            elif col == "Day Type":
                self.saved_data_tree.column(col, width=80, anchor="center")
            else:
                self.saved_data_tree.column(col, width=90, anchor="center")

        # Add scrollbar for saved data
        saved_scrollbar = ttk.Scrollbar(
            saved_data_frame, orient="vertical", command=self.saved_data_tree.yview
        )
        self.saved_data_tree.configure(yscrollcommand=saved_scrollbar.set)

        # Pack saved data treeview and scrollbar
        self.saved_data_tree.pack(side="left", fill="both", expand=True)
        saved_scrollbar.pack(side="right", fill="y")

        # Buttons for saved data management
        saved_buttons_frame = ttk.Frame(saved_data_frame)
        saved_buttons_frame.pack(fill="x", pady=(10, 0))

        ttk.Button(
            saved_buttons_frame, text="Refresh Data", command=self.refresh_saved_data
        ).pack(side="left", padx=5)
        ttk.Button(
            saved_buttons_frame,
            text="Clear All Saved Data",
            command=self.clear_saved_data,
        ).pack(side="left", padx=5)
        ttk.Button(
            saved_buttons_frame,
            text="Export Saved Data",
            command=self.export_saved_data,
        ).pack(side="left", padx=5)

        # Initialize saved data display
        self.refresh_saved_data()

        # Initialize prediction data
        self.budget_prediction_data = None
        self.ml_model = None

    def setup_predictions_tab(self):
        """Set up the predictions tab with pattern and possibility prediction"""
        # Main container with horizontal split
        main_frame = ttk.Frame(self.predictions_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Title
        ttk.Label(
            main_frame, text="Rental Predictions", font=("Arial", 16, "bold")
        ).pack(pady=(0, 10))
        
        # Create paned window for resizable split
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill="both", expand=True)
        
        # Left pane - Pattern Prediction
        pattern_frame = ttk.Frame(paned)
        paned.add(pattern_frame, weight=1)
        
        # Right pane - Possibility Prediction
        possibility_frame = ttk.Frame(paned)
        paned.add(possibility_frame, weight=1)
        
        # ========== Pattern Prediction Section ==========
        pattern_title = ttk.LabelFrame(pattern_frame, text="📊 Rental Pattern Prediction")
        pattern_title.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Input section
        pattern_input_frame = ttk.Frame(pattern_title)
        pattern_input_frame.pack(fill="x", padx=10, pady=10)
        
        # Date range inputs side by side (Start left, End right)
        self.pattern_start_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        self.pattern_end_date_var = tk.StringVar(value=(datetime.now() + pd.Timedelta(days=30)).strftime("%Y-%m-%d"))

        # Create a frame for row layout
        date_row_frame = ttk.Frame(pattern_input_frame)
        date_row_frame.grid(row=0, column=0, columnspan=3, padx=0, pady=5, sticky="ew")

        # Start Date (left)
        ttk.Label(date_row_frame, text="Start Date:").pack(side="left", padx=5)
        pattern_start_entry = ttk.Entry(date_row_frame, textvariable=self.pattern_start_date_var, width=15)
        pattern_start_entry.pack(side="left", padx=5)
        ttk.Button(date_row_frame, text="📅", command=lambda: self.select_date(self.pattern_start_date_var)).pack(side="left", padx=2)

        # Spacer between
        ttk.Label(date_row_frame, text=" " * 3).pack(side="left")  # Optional: provides spacing

        # End Date (right)
        ttk.Label(date_row_frame, text="End Date:").pack(side="left", padx=5)
        pattern_end_entry = ttk.Entry(date_row_frame, textvariable=self.pattern_end_date_var, width=15)
        pattern_end_entry.pack(side="left", padx=5)
        ttk.Button(date_row_frame, text="📅", command=lambda: self.select_date(self.pattern_end_date_var)).pack(side="left", padx=2)
        # Granularity selector
        ttk.Label(pattern_input_frame, text="Granularity:").grid(row=2, column=0, padx=5, pady=5, sticky="w")
        self.pattern_granularity_var = tk.StringVar(value="weekly")
        granularity_combo = ttk.Combobox(
            pattern_input_frame,
            textvariable=self.pattern_granularity_var,
            values=["daily", "weekly", "monthly"],
            width=12,
            state="readonly"
        )
        granularity_combo.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        
        # Ollama reasoning option
        self.pattern_use_ollama_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            pattern_input_frame,
            text="Use AI Reasoning (Ollama)",
            variable=self.pattern_use_ollama_var
        ).grid(row=3, column=0, columnspan=2, padx=5, pady=5, sticky="w")
        
        # Generate button
        ttk.Button(
            pattern_input_frame,
            text="🔮 Predict Patterns",
            command=self.generate_pattern_prediction
        ).grid(row=4, column=0, columnspan=3, pady=10)
        
        # Results section
        pattern_results_frame = ttk.LabelFrame(pattern_title, text="Prediction Results")
        pattern_results_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Summary statistics
        self.pattern_summary_frame = ttk.Frame(pattern_results_frame)
        self.pattern_summary_frame.pack(fill="x", padx=5, pady=5)
        
        self.pattern_summary_labels = {}
        summary_fields = [
            ("Total Predicted Rentals", "total_rentals"),
            ("Total Predicted Spending", "total_spending"),
            ("Avg Distance per Rental", "avg_distance"),
            ("Most Likely Provider", "top_provider"),
            ("Confidence", "confidence")
        ]
        
        for i, (label_text, key) in enumerate(summary_fields):
            ttk.Label(self.pattern_summary_frame, text=f"{label_text}:").grid(
                row=i, column=0, padx=5, pady=2, sticky="w"
            )
            label = ttk.Label(self.pattern_summary_frame, text="--", font=("Arial", 9))
            label.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            self.pattern_summary_labels[key] = label
        
        # AI Reasoning section
        self.pattern_reasoning_frame = ttk.LabelFrame(pattern_results_frame, text="🤖 AI Reasoning & Insights")
        self.pattern_reasoning_frame.pack(fill="both", expand=False, padx=5, pady=5)
        
        self.pattern_reasoning_text = tk.Text(
            self.pattern_reasoning_frame,
            height=4,
            wrap=tk.WORD,
            font=("Arial", 9),
            state=tk.DISABLED,
            relief=tk.FLAT,
            bg=self.root.cget("bg")
        )
        reasoning_scroll = ttk.Scrollbar(self.pattern_reasoning_frame, orient="vertical", command=self.pattern_reasoning_text.yview)
        self.pattern_reasoning_text.configure(yscrollcommand=reasoning_scroll.set)
        self.pattern_reasoning_text.pack(side="left", fill="both", expand=True, padx=5, pady=5)
        reasoning_scroll.pack(side="right", fill="y")
        
        # Chart frame
        self.pattern_chart_frame = ttk.Frame(pattern_results_frame)
        self.pattern_chart_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Table for detailed breakdown
        pattern_table_frame = ttk.Frame(pattern_results_frame)
        pattern_table_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        pattern_table_scroll = ttk.Scrollbar(pattern_table_frame)
        pattern_table_scroll.pack(side="right", fill="y")
        
        self.pattern_table = ttk.Treeview(
            pattern_table_frame,
            columns=("date", "day", "will_rent", "duration", "distance", "cost"),
            show="headings",
            height=12,
            yscrollcommand=pattern_table_scroll.set
        )
        pattern_table_scroll.config(command=self.pattern_table.yview)
        
        self.pattern_table.heading("date", text="Date")
        self.pattern_table.heading("day", text="Day")
        self.pattern_table.heading("will_rent", text="Will Rent?")
        self.pattern_table.heading("duration", text="Duration (hrs)")
        self.pattern_table.heading("distance", text="Distance (km)")
        self.pattern_table.heading("cost", text="Est. Cost")
        
        self.pattern_table.column("date", width=110)
        self.pattern_table.column("day", width=80)
        self.pattern_table.column("will_rent", width=80)
        self.pattern_table.column("duration", width=100)
        self.pattern_table.column("distance", width=100)
        self.pattern_table.column("cost", width=90)
        
        self.pattern_table.pack(side="left", fill="both", expand=True)
        
        # ========== Possibility Prediction Section ==========
        possibility_title = ttk.LabelFrame(possibility_frame, text="🎯 Date-Specific Rental Possibility")
        possibility_title.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Input section
        possibility_input_frame = ttk.Frame(possibility_title)
        possibility_input_frame.pack(fill="x", padx=10, pady=10)
        
        # Target date
        ttk.Label(possibility_input_frame, text="Target Date:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.possibility_date_var = tk.StringVar(value=datetime.now().strftime("%Y-%m-%d"))
        possibility_date_entry = ttk.Entry(possibility_input_frame, textvariable=self.possibility_date_var, width=15)
        possibility_date_entry.grid(row=0, column=1, padx=5, pady=5)
        ttk.Button(possibility_input_frame, text="📅", command=lambda: self.select_date(self.possibility_date_var)).grid(row=0, column=2, padx=2)
        
        # Combine "Trip Details" (left) and "Contextual Factors" (right) in a single horizontal frame
        details_context_outer = ttk.Frame(possibility_input_frame)
        details_context_outer.grid(row=1, column=0, columnspan=3, sticky="ew", padx=5, pady=5)
        details_context_outer.columnconfigure(0, weight=1)
        details_context_outer.columnconfigure(1, weight=1)

        # Trip details frame (left)
        trip_details_frame = ttk.LabelFrame(details_context_outer, text="Trip Details (Optional)")
        trip_details_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5), pady=0)

        ttk.Label(trip_details_frame, text="Distance (km):").grid(row=0, column=0, padx=5, pady=2, sticky="w")
        self.possibility_distance_var = tk.StringVar()
        ttk.Entry(trip_details_frame, textvariable=self.possibility_distance_var, width=12).grid(row=0, column=1, padx=5, pady=2)

        ttk.Label(trip_details_frame, text="Duration (hours):").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.possibility_duration_var = tk.StringVar()
        ttk.Entry(trip_details_frame, textvariable=self.possibility_duration_var, width=12).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(trip_details_frame, text="Weekend:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.possibility_weekend_var = tk.BooleanVar()
        ttk.Checkbutton(trip_details_frame, variable=self.possibility_weekend_var).grid(row=2, column=1, padx=5, pady=2, sticky="w")

        # Contextual factors frame (right)
        context_frame = ttk.LabelFrame(details_context_outer, text="Contextual Factors (Optional)")
        context_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0), pady=0)

        self.possibility_holiday_var = tk.BooleanVar()
        ttk.Checkbutton(context_frame, text="Holiday", variable=self.possibility_holiday_var).grid(row=0, column=0, padx=5, pady=2, sticky="w")

        ttk.Label(context_frame, text="Special Event:").grid(row=1, column=0, padx=5, pady=2, sticky="w")
        self.possibility_event_var = tk.StringVar()
        ttk.Entry(context_frame, textvariable=self.possibility_event_var, width=20).grid(row=1, column=1, padx=5, pady=2)

        ttk.Label(context_frame, text="Weather:").grid(row=2, column=0, padx=5, pady=2, sticky="w")
        self.possibility_weather_var = tk.StringVar()
        weather_combo = ttk.Combobox(
            context_frame,
            textvariable=self.possibility_weather_var,
            values=["", "sunny", "rainy", "cloudy", "stormy"],
            width=15,
            state="readonly"
        )
        weather_combo.grid(row=2, column=1, padx=5, pady=2)

        ttk.Label(context_frame, text="Personal Schedule:").grid(row=3, column=0, padx=5, pady=2, sticky="w")
        self.possibility_schedule_var = tk.StringVar(value="Maybe")
        schedule_combo = ttk.Combobox(
            context_frame,
            textvariable=self.possibility_schedule_var,
            values=["Free", "Maybe", "Busy"],
            width=15,
            state="readonly"
        )
        schedule_combo.grid(row=3, column=1, padx=5, pady=2)
        # Generate button
        ttk.Button(
            possibility_input_frame,
            text="🔮 Predict Possibility",
            command=self.generate_possibility_prediction
        ).grid(row=3, column=0, columnspan=3, pady=10)
        
        # Results section
        possibility_results_frame = ttk.LabelFrame(possibility_title, text="Prediction Results")
        possibility_results_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Possibility score display (large)
        self.possibility_score_frame = ttk.Frame(possibility_results_frame)
        self.possibility_score_frame.pack(fill="x", padx=10, pady=10)
        
        self.possibility_score_label = ttk.Label(
            self.possibility_score_frame,
            text="--",
            font=("Arial", 32, "bold"),
            foreground="#0078d7"
        )
        self.possibility_score_label.pack()
        
        # Details frame
        self.possibility_details_frame = ttk.Frame(possibility_results_frame)
        self.possibility_details_frame.pack(fill="x", padx=5, pady=5)
        
        self.possibility_details_labels = {}
        details_fields = [
            ("Confidence", "confidence"),
            ("Expected Cost Range", "cost_range"),
            ("Recommended Provider", "provider"),
            ("Method", "method")
        ]
        
        for i, (label_text, key) in enumerate(details_fields):
            ttk.Label(self.possibility_details_frame, text=f"{label_text}:").grid(
                row=i, column=0, padx=5, pady=2, sticky="w"
            )
            label = ttk.Label(self.possibility_details_frame, text="--", font=("Arial", 9))
            label.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            self.possibility_details_labels[key] = label
        
        # Reasoning text
        reasoning_frame = ttk.LabelFrame(possibility_results_frame, text="Reasoning")
        reasoning_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.possibility_reasoning_text = tk.Text(
            reasoning_frame, wrap=tk.WORD, height=6, width=40
        )
        reasoning_scroll = ttk.Scrollbar(reasoning_frame, command=self.possibility_reasoning_text.yview)
        self.possibility_reasoning_text.config(yscrollcommand=reasoning_scroll.set)
        
        self.possibility_reasoning_text.pack(side="left", fill="both", expand=True)
        reasoning_scroll.pack(side="right", fill="y")
        
        # Historical comparison
        historical_frame = ttk.LabelFrame(possibility_results_frame, text="Historical Comparison")
        historical_frame.pack(fill="x", padx=5, pady=5)
        
        self.possibility_historical_text = tk.Text(
            historical_frame, wrap=tk.WORD, height=4, width=40
        )
        self.possibility_historical_text.pack(fill="x", padx=5, pady=5)

    def setup_calculator_tab(self):
        """Set up the calculator tab for price comparison between providers"""
        # Main container
        main_frame = ttk.Frame(self.calculator_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        ttk.Label(
            main_frame, text="Car Rental Price Calculator", font=("Arial", 16, "bold")
        ).pack(pady=(0, 20))

        # Create notebook for different sections
        calc_notebook = ttk.Notebook(main_frame)
        calc_notebook.pack(fill="both", expand=True)

        # Trip Details Tab
        trip_frame = ttk.Frame(calc_notebook)
        calc_notebook.add(trip_frame, text="Trip Details")

        # Pricing Configuration Tab
        pricing_frame = ttk.Frame(calc_notebook)
        calc_notebook.add(pricing_frame, text="Pricing Configuration")

        # Setup trip details tab
        self.setup_trip_details_tab(trip_frame)
        # Setup pricing configuration tab
        self.setup_pricing_config_tab(pricing_frame)

    def setup_user_preference_tab(self):
        """Set up the user preference analysis tab"""
        # Main container
        main_frame = ttk.Frame(self.user_preference_tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Title
        ttk.Label(
            main_frame, text="User Preference Analysis", font=("Arial", 16, "bold")
        ).pack(pady=(0, 20))

        # Create notebook for different sections
        pref_notebook = ttk.Notebook(main_frame)
        pref_notebook.pack(fill="both", expand=True)

        # User Profile Analysis Tab
        profile_frame = ttk.Frame(pref_notebook)
        pref_notebook.add(profile_frame, text="User Profile")

        # Preference-based Recommendations Tab
        rec_frame = ttk.Frame(pref_notebook)
        pref_notebook.add(rec_frame, text="Personalized Recommendations")

        # Setup profile analysis section
        self.setup_user_profile_section(profile_frame)
        # Setup preference recommendations section
        self.setup_preference_recommendations_section(rec_frame)

    def setup_user_profile_section(self, parent):
        """Set up the user profile analysis section"""
        # Region selector: analysis and recommendations apply to this region only
        region_frame = ttk.Frame(parent)
        region_frame.pack(fill="x", padx=10, pady=(0, 5))
        ttk.Label(region_frame, text="Analysis for region:").pack(side="left", padx=(0, 5))
        self.pref_region_var = tk.StringVar(value="Singapore")
        ttk.Combobox(
            region_frame,
            textvariable=self.pref_region_var,
            values=list(VALID_REGIONS),
            width=12,
            state="readonly",
        ).pack(side="left", padx=(0, 10))
        self.pref_region_label = ttk.Label(
            region_frame,
            text="Analysis and recommendations for region: Singapore",
            font=("Segoe UI", 9),
        )
        self.pref_region_label.pack(side="left", padx=(10, 0))
        self.pref_region_var.trace_add("write", lambda *a: self._update_pref_region_label())

        # Profile editing section
        edit_profile_frame = ttk.LabelFrame(parent, text="Edit Profile", padding=10)
        edit_profile_frame.pack(fill="x", padx=10, pady=10)
        
        # Age input
        age_frame = ttk.Frame(edit_profile_frame)
        age_frame.pack(fill="x", pady=5)
        ttk.Label(age_frame, text="Age:").pack(side="left", padx=(0, 10))
        self.user_age_var = tk.StringVar(value=str(self.user_age))
        age_spinbox = ttk.Spinbox(
            age_frame, 
            from_=18, 
            to=100, 
            textvariable=self.user_age_var, 
            width=10
        )
        age_spinbox.pack(side="left", padx=(0, 20))
        
        # Experience years input
        ttk.Label(age_frame, text="Driving Experience (years):").pack(side="left", padx=(0, 10))
        self.user_experience_years_var = tk.StringVar(value=str(self.user_experience_years))
        experience_spinbox = ttk.Spinbox(
            age_frame, 
            from_=0, 
            to=50, 
            textvariable=self.user_experience_years_var, 
            width=10
        )
        experience_spinbox.pack(side="left", padx=(0, 20))
        
        # Update profile button
        update_btn = ttk.Button(
            edit_profile_frame,
            text="Update Profile",
            command=self.update_user_profile
        )
        update_btn.pack(pady=10)
        
        # Analysis controls
        controls_frame = ttk.LabelFrame(parent, text="Analysis Controls", padding=10)
        controls_frame.pack(fill="x", padx=10, pady=10)

        # Analyze button
        analyze_btn = ttk.Button(
            controls_frame,
            text="Analyze User Preferences",
            command=self.analyze_user_preferences
        )
        analyze_btn.pack(pady=10)

        # Results display
        results_frame = ttk.LabelFrame(parent, text="User Profile Analysis", padding=10)
        results_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create text widget for displaying results
        self.user_profile_text = tk.Text(
            results_frame, 
            height=20, 
            wrap=tk.WORD,
            font=("Consolas", 10)
        )
        scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.user_profile_text.yview)
        self.user_profile_text.configure(yscrollcommand=scrollbar.set)
        
        self.user_profile_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def update_user_profile(self):
        """Update user profile (age and experience years) and save to settings"""
        try:
            # Validate age
            age_str = self.user_age_var.get().strip()
            age_valid, age, age_error = validate_numeric_input(
                age_str, "Age",
                min_value=18, max_value=100, allow_zero=False, allow_negative=False, required=True
            )
            if not age_valid:
                self._show_user_friendly_error("Invalid Age", age_error, "Age")
                return
            
            # Validate experience years
            experience_str = self.user_experience_years_var.get().strip()
            exp_valid, experience, exp_error = validate_numeric_input(
                experience_str, "Driving Experience",
                min_value=0, max_value=50, allow_zero=True, allow_negative=False, required=True
            )
            if not exp_valid:
                self._show_user_friendly_error("Invalid Experience", exp_error, "Driving Experience")
                return
            
            # Convert to int for storage
            age = int(age)
            experience = int(experience)
            
            # Update profile attributes
            self.user_age = age
            self.user_experience_years = experience
            
            # Save to settings
            self.save_settings()
            
            # Show confirmation
            messagebox.showinfo("Success", f"Profile updated successfully!\n\nAge: {age} years\nDriving Experience: {experience} years")
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to update profile: {str(e)}")

    def setup_preference_recommendations_section(self, parent):
        """Set up the preference-based recommendations section"""
        # Input controls
        input_frame = ttk.LabelFrame(parent, text="Trip Details", padding=10)
        input_frame.pack(fill="x", padx=10, pady=10)

        # Distance input
        dist_frame = ttk.Frame(input_frame)
        dist_frame.pack(fill="x", pady=5)
        ttk.Label(dist_frame, text="Distance (km):").pack(side="left")
        self.pref_distance_var = tk.StringVar()
        ttk.Entry(dist_frame, textvariable=self.pref_distance_var, width=10).pack(side="left", padx=(10, 0))

        # Duration input
        dur_frame = ttk.Frame(input_frame)
        dur_frame.pack(fill="x", pady=5)
        ttk.Label(dur_frame, text="Duration (hours):").pack(side="left")
        self.pref_duration_var = tk.StringVar()
        ttk.Entry(dur_frame, textvariable=self.pref_duration_var, width=10).pack(side="left", padx=(10, 0))

        # Weekend checkbox
        self.pref_weekend_var = tk.BooleanVar()
        ttk.Checkbutton(input_frame, text="Weekend trip", variable=self.pref_weekend_var).pack(pady=5)

        # Get recommendations button
        get_recs_btn = ttk.Button(
            input_frame,
            text="Get Personalized Recommendations",
            command=self.get_preference_recommendations
        )
        get_recs_btn.pack(pady=10)

        # Range information display
        range_frame = ttk.LabelFrame(parent, text="Trip Range Category", padding=10)
        range_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.range_info_text = tk.Text(range_frame, height=3, wrap=tk.WORD, state=tk.DISABLED)
        self.range_info_text.pack(fill="x")
        
        # Range insights display
        insights_frame = ttk.LabelFrame(parent, text="Range-Specific Insights", padding=10)
        insights_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        self.range_insights_text = tk.Text(insights_frame, height=4, wrap=tk.WORD, state=tk.DISABLED)
        self.range_insights_text.pack(fill="x")

        # Results display
        results_frame = ttk.LabelFrame(parent, text="Personalized Recommendations", padding=10)
        results_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Create treeview for recommendations
        columns = ("Provider", "Model", "Cost", "Confidence", "Reasoning", "Range Insights")
        self.pref_recs_tree = ttk.Treeview(results_frame, columns=columns, show="headings", height=10)
        
        # Configure columns
        for col in columns:
            self.pref_recs_tree.heading(col, text=col)
            if col == "Range Insights":
                self.pref_recs_tree.column(col, width=200)
            elif col == "Reasoning":
                self.pref_recs_tree.column(col, width=200)
            else:
                self.pref_recs_tree.column(col, width=120)

        # Scrollbar for treeview
        pref_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.pref_recs_tree.yview)
        self.pref_recs_tree.configure(yscrollcommand=pref_scrollbar.set)
        
        self.pref_recs_tree.pack(side="left", fill="both", expand=True)
        pref_scrollbar.pack(side="right", fill="y")

    def analyze_user_preferences(self):
        """Analyze user preferences using Ollama"""
        if not self._check_data_loaded():
            return

        # Show loading indicator
        loading = LoadingDialog(self.root, "Analyzing Preferences", "Analyzing your rental history and preferences...")
        loading.show()

        try:
            # Clear previous results
            self.user_profile_text.delete(1.0, tk.END)
            self.user_profile_text.insert(tk.END, "Analyzing user preferences...\n")
            self.root.update()

            # Get Ollama model (use shared variable from Recommendations tab, or default)
            if hasattr(self, 'ollama_model_var'):
                ollama_model = self.ollama_model_var.get()
            else:
                ollama_model = "llama3.1:3b"  # Default fallback

            # Filter by selected region so analysis is for one region only (Singapore or Malaysia)
            region = self.pref_region_var.get() if hasattr(self, "pref_region_var") else "Singapore"
            if region not in VALID_REGIONS:
                region = "Singapore"
            df_for_analysis = self.df
            if "Region" in self.df.columns:
                df_for_analysis = self.df[self.df["Region"] == region].copy()

            # Analyze user preferences
            # Note: analyze_user_preferences will use fallback if Ollama is not available
            user_preferences = analyze_user_preferences(df_for_analysis, ollama_model)
            
            # Store preferences for later use
            self.user_preferences = user_preferences

            # Display results
            self.display_user_preferences(user_preferences)

        except AttributeError as e:
            # Handle case where ollama_model_var doesn't exist
            error_msg = f"Configuration error: {str(e)}\n\nPlease ensure the application is properly initialized."
            messagebox.showerror("Error", error_msg)
            self.user_profile_text.delete(1.0, tk.END)
            self.user_profile_text.insert(tk.END, f"Error: {error_msg}")
        except Exception as e:
            error_msg = str(e)
            # Check if it's an ollama-related error
            if "ollama" in error_msg.lower() or "cannot connect" in error_msg.lower():
                # Try to continue with fallback preferences
                try:
                    self.user_profile_text.insert(tk.END, f"\nNote: {error_msg}\n")
                    self.user_profile_text.insert(tk.END, "Using fallback analysis method...\n")
                    self.root.update()
                    # The analyze_user_preferences function should have already used fallback
                    # But if it didn't, we'll show the error
                    if hasattr(self, 'user_preferences') and self.user_preferences:
                        self.display_user_preferences(self.user_preferences)
                    else:
                        raise
                except:
                    messagebox.showwarning("Ollama Not Available", 
                        f"Ollama is not available: {error_msg}\n\n"
                        "The analysis will use fallback methods based on your data patterns.")
                    self.user_profile_text.delete(1.0, tk.END)
                    self.user_profile_text.insert(tk.END, f"Error: {error_msg}\n\n")
                    self.user_profile_text.insert(tk.END, "Please ensure Ollama is installed and running if you want to use AI-powered analysis.")
            else:
                self._show_user_friendly_error("Error", f"Failed to analyze user preferences: {error_msg}")
                self.user_profile_text.delete(1.0, tk.END)
                self.user_profile_text.insert(tk.END, f"Error: {error_msg}")
        finally:
            loading.hide()

    def display_user_preferences(self, preferences):
        """Display user preferences in the text widget with clear, readable format"""
        self.user_profile_text.delete(1.0, tk.END)
        
        # Check for errors
        if isinstance(preferences, dict) and "error" in preferences:
            self.user_profile_text.insert(tk.END, "⚠️ ERROR\n")
            self.user_profile_text.insert(tk.END, "=" * 60 + "\n\n")
            self.user_profile_text.insert(tk.END, f"{preferences['error']}\n\n")
            self.user_profile_text.insert(tk.END, "Please ensure:\n")
            self.user_profile_text.insert(tk.END, "• Your CSV file is loaded in the 'Data Analysis' tab\n")
            self.user_profile_text.insert(tk.END, "• The file contains rental data with records\n")
            self.user_profile_text.insert(tk.END, "• Required columns are present (Date, Car Cat, Distance (KM), etc.)\n")
            self.user_profile_text.insert(tk.END, "• The data file is not empty\n\n")
            self.user_profile_text.insert(tk.END, "If you have data loaded, try:\n")
            self.user_profile_text.insert(tk.END, "• Reloading the CSV file\n")
            self.user_profile_text.insert(tk.END, "• Checking that the file format is correct\n")
            self.user_profile_text.insert(tk.END, "• Verifying the data contains rental records\n")
            return
        
        # Helper function to convert values to readable descriptions
        def format_frequency(freq):
            if freq == "low":
                return "occasional renter (few rentals)"
            elif freq == "medium":
                return "regular renter (moderate rentals)"
            else:
                return "frequent renter (many rentals)"
        
        def format_budget(budget):
            if budget == "high":
                return "very budget-conscious (prioritizes cost savings)"
            elif budget == "medium":
                return "moderately budget-conscious (balances cost and quality)"
            else:
                return "less budget-focused (prioritizes convenience/quality)"
        
        def format_distance(dist):
            if dist == "short":
                return "short trips (typically under 30km)"
            elif dist == "medium":
                return "medium trips (typically 30-80km)"
            else:
                return "long trips (typically over 80km)"
        
        def format_duration(dur):
            if dur == "short":
                return "short rentals (typically under 2 hours)"
            elif dur == "medium":
                return "medium rentals (typically 2-6 hours)"
            else:
                return "long rentals (typically over 6 hours)"
        
        def format_weekend_pref(pref):
            if pref == "weekend_preference":
                return "prefer weekends"
            elif pref == "weekday_preference":
                return "prefer weekdays"
            else:
                return "no strong preference (balanced)"
        
        def format_cost_range(cost):
            if cost == "budget":
                return "budget-friendly options (typically under $30)"
            elif cost == "mid-range":
                return "mid-range options (typically $30-$60)"
            else:
                return "premium options (typically over $60)"
        
        def format_usage_type(usage):
            usage_map = {
                "errands": "primarily for errands and daily tasks",
                "leisure": "primarily for leisure and recreation",
                "business": "primarily for business purposes",
                "mixed": "mixed usage (errands, leisure, and business)"
            }
            return usage_map.get(usage, usage)
        
        # Extract data
        profile = preferences.get("user_profile", {})
        preferred_providers = preferences.get("preferred_providers", [])
        preferred_models = preferences.get("preferred_car_models", [])
        patterns = preferences.get("rental_patterns", {})
        recommendations = preferences.get("recommendations", [])
        insights = preferences.get("insights", [])
        
        # Build user type summary
        frequency = profile.get('rental_frequency', 'medium')
        budget = profile.get('budget_consciousness', 'medium')
        distance = profile.get('distance_preference', 'medium')
        duration = profile.get('duration_preference', 'medium')
        weekend_pref = profile.get('weekend_vs_weekday', 'balanced')
        
        # 1. USER PROFILE SUMMARY
        self.user_profile_text.insert(tk.END, "📊 YOUR RENTAL PROFILE\n")
        self.user_profile_text.insert(tk.END, "=" * 60 + "\n\n")
        
        user_summary = f"You are a {format_frequency(frequency)} who is {format_budget(budget)}. "
        user_summary += f"You typically take {format_distance(distance)} and prefer {format_duration(duration)}. "
        user_summary += f"You {format_weekend_pref(weekend_pref)} for rentals.\n\n"
        self.user_profile_text.insert(tk.END, user_summary)
        
        # 2. PREFERRED CAR MODEL
        if preferred_models:
            self.user_profile_text.insert(tk.END, "🚗 YOUR PREFERRED CAR MODEL\n")
            self.user_profile_text.insert(tk.END, "=" * 60 + "\n\n")
            for model in preferred_models[:1]:  # Show top model
                model_name = model.get('model', 'N/A')
                model_reason = model.get('reason', 'No reason provided')
                self.user_profile_text.insert(tk.END, f"Model: {model_name}\n")
                self.user_profile_text.insert(tk.END, f"Reason: {model_reason}\n\n")
        
        # 3. RENTAL PATTERNS
        self.user_profile_text.insert(tk.END, "📈 YOUR RENTAL PATTERNS\n")
        self.user_profile_text.insert(tk.END, "=" * 60 + "\n\n")
        
        typical_distance = patterns.get('typical_distance', 'medium')
        typical_duration = patterns.get('typical_duration', 'medium')
        typical_cost = patterns.get('typical_cost_range', 'mid-range')
        usage_type = patterns.get('usage_type', 'mixed')
        
        self.user_profile_text.insert(tk.END, f"• Typical trip distance: {format_distance(typical_distance)}\n")
        self.user_profile_text.insert(tk.END, f"• Typical rental duration: {format_duration(typical_duration)}\n")
        self.user_profile_text.insert(tk.END, f"• Cost preference: {format_cost_range(typical_cost)}\n")
        self.user_profile_text.insert(tk.END, f"• Usage type: {format_usage_type(usage_type)}\n\n")
        
        # 4. PROVIDER RECOMMENDATION
        if preferred_providers:
            self.user_profile_text.insert(tk.END, "💡 PROVIDER RECOMMENDATION\n")
            self.user_profile_text.insert(tk.END, "=" * 60 + "\n\n")
            
            top_provider = preferred_providers[0]
            provider_name = top_provider.get('provider', 'N/A')
            provider_reason = top_provider.get('reason', 'No reason provided')
            
            self.user_profile_text.insert(tk.END, f"Recommended Provider: {provider_name}\n\n")
            self.user_profile_text.insert(tk.END, f"Reasoning:\n{provider_reason}\n\n")
        
        # 5. ADDITIONAL RECOMMENDATIONS
        if recommendations:
            self.user_profile_text.insert(tk.END, "✨ ADDITIONAL RECOMMENDATIONS\n")
            self.user_profile_text.insert(tk.END, "=" * 60 + "\n\n")
            for rec in recommendations:
                rec_type = rec.get('type', 'general')
                suggestion = rec.get('suggestion', 'N/A')
                reasoning = rec.get('reasoning', 'No reasoning provided')
                
                self.user_profile_text.insert(tk.END, f"• {suggestion}\n")
                self.user_profile_text.insert(tk.END, f"  {reasoning}\n\n")
        
        # 6. KEY INSIGHTS
        if insights:
            self.user_profile_text.insert(tk.END, "🔍 KEY INSIGHTS\n")
            self.user_profile_text.insert(tk.END, "=" * 60 + "\n\n")
            for insight in insights:
                self.user_profile_text.insert(tk.END, f"• {insight}\n")
            self.user_profile_text.insert(tk.END, "\n")

    def get_preference_recommendations(self):
        """Get personalized recommendations based on user preferences with range analysis"""
        if not hasattr(self, 'user_preferences') or self.user_preferences is None:
            messagebox.showerror("Error", "Please analyze user preferences first")
            return

        try:
            # Get input values
            distance = float(self.pref_distance_var.get())
            duration = float(self.pref_duration_var.get())
            is_weekend = self.pref_weekend_var.get()

            # Clear previous results
            for item in self.pref_recs_tree.get_children():
                self.pref_recs_tree.delete(item)
            
            # Clear range displays
            self.range_info_text.config(state=tk.NORMAL)
            self.range_info_text.delete(1.0, tk.END)
            self.range_insights_text.config(state=tk.NORMAL)
            self.range_insights_text.delete(1.0, tk.END)

            # Filter by selected region so recommendations use one region's data only
            region = self.pref_region_var.get() if hasattr(self, "pref_region_var") else "Singapore"
            if region not in VALID_REGIONS:
                region = "Singapore"
            df_for_pref = self.df
            if "Region" in self.df.columns:
                df_for_pref = self.df[self.df["Region"] == region].copy()

            # Get range categories
            distance_range = get_distance_range(distance)
            duration_range = get_duration_range(duration)
            
            # Display range information
            range_info = f"Distance Range: {distance_range} | Duration Range: {duration_range}"
            self.range_info_text.insert(tk.END, range_info)
            self.range_info_text.config(state=tk.DISABLED)
            
            # Get range-specific statistics (region-filtered)
            range_stats = get_range_specific_statistics(df_for_pref, distance_range, duration_range)
            if range_stats:
                insights_text = f"Found {range_stats.get('total_rentals', 0)} historical rentals in this range.\n"
                insights_text += f"Average cost in this range: ${range_stats.get('avg_cost', 0):.2f}\n"
                if range_stats.get('providers'):
                    insights_text += "\nProvider performance in this range:\n"
                    for provider, stats in list(range_stats['providers'].items())[:3]:
                        insights_text += f"  • {provider}: ${stats.get('avg_cost', 0):.2f} avg ({stats.get('rental_count', 0)} rentals)\n"
            else:
                insights_text = "No historical data available for this specific range combination."
            
            self.range_insights_text.insert(tk.END, insights_text)
            self.range_insights_text.config(state=tk.DISABLED)

            # Get personalized recommendations (region-filtered df)
            recommendations = get_preference_based_recommendations(
                distance, duration, self.user_preferences, df_for_pref, is_weekend, top_n=5
            )

            # Display recommendations with range insights
            for rec in recommendations:
                range_insights = rec.get("range_insights", {})
                range_insight_text = ""
                if range_insights.get("range_specific_reasoning"):
                    range_insight_text = range_insights["range_specific_reasoning"]
                elif range_insights.get("range_rental_count", 0) > 0:
                    range_insight_text = f"Avg: ${range_insights.get('range_average_cost', 0):.2f} ({range_insights.get('range_rental_count', 0)} rentals)"
                
                self.pref_recs_tree.insert("", "end", values=(
                    rec.get("provider", "N/A"),
                    rec.get("model", "N/A"),
                    f"${rec.get('total_cost', 0):.2f}",
                    f"{rec.get('confidence', 0):.1%}",
                    rec.get("reasoning", "N/A"),
                    range_insight_text or "N/A"
                ))

        except ValueError:
            messagebox.showerror("Error", "Please enter valid distance and duration values")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get recommendations: {str(e)}")
            import traceback
            traceback.print_exc()

    def setup_trip_details_tab(self, parent):
        """Set up the trip details input section"""

        def create_labeled_entry(frame, label_text, var, width=10, default=None):
            row = ttk.Frame(frame)
            row.pack(fill="x", pady=5)
            ttk.Label(row, text=label_text, width=15).pack(side="left")
            entry = ttk.Entry(row, textvariable=var, width=width, state="normal")
            entry.pack(side="left", padx=(10, 0))
            if default is not None:
                var.set(default)
            return entry

        # Input section
        input_frame = ttk.LabelFrame(parent, text="Trip Details", padding=10)
        input_frame.pack(fill="x", pady=(0, 20))

        # Region (Singapore / Malaysia) - determines which providers are calculated
        region_frame = ttk.Frame(input_frame)
        region_frame.pack(fill="x", pady=5)
        ttk.Label(region_frame, text="Region:", width=15).pack(side="left")
        self.calc_region_var = tk.StringVar(value="Singapore")
        ttk.Combobox(
            region_frame,
            textvariable=self.calc_region_var,
            values=list(VALID_REGIONS),
            width=12,
            state="readonly",
        ).pack(side="left", padx=(10, 0))

        # Distance input
        self.calc_distance_var = tk.StringVar(value="10")
        create_labeled_entry(input_frame, "Distance (km):", self.calc_distance_var)

        # Duration input
        self.calc_duration_var = tk.StringVar(value="2")
        create_labeled_entry(input_frame, "Duration (hours):", self.calc_duration_var)

        # Day type selection
        day_frame = ttk.Frame(input_frame)
        day_frame.pack(fill="x", pady=5)
        ttk.Label(day_frame, text="Day Type:", width=15).pack(side="left")
        self.calc_day_type_var = tk.StringVar(value="weekday")
        ttk.Combobox(
            day_frame,
            textvariable=self.calc_day_type_var,
            values=["weekday", "weekend"],
            width=10,
            state="readonly",
        ).pack(side="left", padx=(10, 0))

        # Calculate button
        ttk.Button(
            input_frame, text="Calculate Prices", command=self.calculate_provider_prices
        ).pack(pady=10)
        # Save trip button
        ttk.Button(
            input_frame, text="Save Trip Data", command=self.save_trip_data
        ).pack(pady=5)

        # Results section
        results_frame = ttk.LabelFrame(
            parent, text="Price Comparison Results", padding=10
        )
        results_frame.pack(fill="both", expand=True)

        # Create results treeview
        columns = (
            "Provider",
            "Base Cost",
            "Distance/Fuel Cost",
            "Duration Cost",
            "Weekend Surcharge",
            "Total Cost",
        )
        self.calc_results_tree = ttk.Treeview(
            results_frame, columns=columns, show="headings", height=6
        )
        for col in columns:
            self.calc_results_tree.heading(col, text=col)
            self.calc_results_tree.column(col, width=120, anchor="center")

        # Add scrollbar
        calc_scrollbar = ttk.Scrollbar(
            results_frame, orient="vertical", command=self.calc_results_tree.yview
        )
        self.calc_results_tree.configure(yscrollcommand=calc_scrollbar.set)
        self.calc_results_tree.pack(side="left", fill="both", expand=True)
        calc_scrollbar.pack(side="right", fill="y")

        # Summary section
        summary_frame = ttk.Frame(parent)
        summary_frame.pack(fill="x", pady=(10, 0))
        self.calc_summary_var = tk.StringVar(
            value="Enter trip details and click 'Calculate Prices' to see comparison"
        )
        ttk.Label(
            summary_frame,
            textvariable=self.calc_summary_var,
            font=("Arial", 10, "bold"),
            foreground="#2E8B57",
        ).pack()

    def setup_pricing_config_tab(self, parent):
        """Set up the simplified pricing configuration section"""
        # Initialize simplified pricing data: Singapore providers + Malaysia SoCar
        self.pricing_data = {
            "Getgo": {
                "mileage_rate": 0.39,
                "hour_rate": 8.0,
                "pricing_type": "mileage",
            },
            "Getgo EV": {
                "mileage_rate": 0.35,
                "hour_rate": 9.0,
                "pricing_type": "mileage",
            },
            "Tribecar": {
                "usual_fuel_amount": 20,
                "hour_rate": 8.5,
                "pricing_type": "fuel",
            },
            "Car Club": {
                "mileage_rate": 0.30,
                "hour_rate": 9.5,
                "pricing_type": "mileage",
            },
            "Econ": {"usual_fuel_amount": 15, "hour_rate": 7.5, "pricing_type": "fuel"},
            "Stand": {
                "usual_fuel_amount": 25,
                "hour_rate": 10.0,
                "pricing_type": "fuel",
            },
            "SoCar": {
                "pricing_type": "socar",
                "hour_rate": 8.0,
                "mileage_packages": [
                    {"km": 10, "price": 2.5},
                    {"km": 50, "price": 11},
                    {"km": 100, "price": 15},
                ],
                "excess_km_rate": 0.25,
            },
            "NormalRental": {"pricing_type": "traditional"},
        }

        # Load saved pricing data
        self.load_pricing_data()

        # Instructions
        instructions_frame = ttk.Frame(parent)
        instructions_frame.pack(fill="x", pady=(0, 10))
        instructions_text = (
            "Configure pricing rates for each provider. Tribecar uses fuel cost, others use mileage cost. "
            "Weekend trips will have 20% surcharge applied."
        )
        ttk.Label(instructions_frame, text=instructions_text, font=("Arial", 10)).pack()

        # Create pricing input frames for each provider
        providers = ["Getgo", "Getgo EV", "Tribecar", "Car Club", "Econ", "Stand"]

        def create_pricing_fields(provider, parent_frame):
            def add_labeled_entry(
                frame, label_text, var, width=10, label_width=15, padx=(10, 20)
            ):
                ttk.Label(frame, text=label_text, width=label_width).pack(side="left")
                entry = ttk.Entry(frame, textvariable=var, width=width, state="normal")
                entry.pack(side="left", padx=padx)
                return entry

            provider_key = provider.lower().replace(" ", "_")
            pricing = self.pricing_data[provider]
            pricing_type = pricing["pricing_type"]
            rates_frame = ttk.Frame(parent_frame)
            rates_frame.pack(fill="x", pady=2)

            if pricing_type == "mileage":
                mileage_var = tk.StringVar(value=str(pricing["mileage_rate"]))
                add_labeled_entry(rates_frame, "Mileage cost ($/km):", mileage_var)
                setattr(self, f"{provider_key}_mileage_var", mileage_var)
            else:
                fuel_val = str(
                    pricing.get("fuel_rate", pricing.get("usual_fuel_amount", 0))
                )
                fuel_var = tk.StringVar(value=fuel_val)
                add_labeled_entry(rates_frame, "Fuel top-up ($):", fuel_var)
                setattr(self, f"{provider_key}_fuel_var", fuel_var)

            duration_var = tk.StringVar(value=str(pricing["hour_rate"]))
            # Use smaller left padding for the last entry
            ttk.Label(rates_frame, text="Total duration cost ($):", width=18).pack(
                side="left"
            )
            ttk.Entry(
                rates_frame, textvariable=duration_var, width=10, state="normal"
            ).pack(side="left", padx=(10, 0))
            setattr(self, f"{provider_key}_duration_var", duration_var)

        for provider in providers:
            provider_frame = ttk.LabelFrame(parent, text=provider, padding=10)
            provider_frame.pack(fill="x", pady=5)
            create_pricing_fields(provider, provider_frame)

        # Malaysia (SoCar) section - hour rate and excess km rate in RM
        socar_frame = ttk.LabelFrame(parent, text="Malaysia - SoCar (RM)", padding=10)
        socar_frame.pack(fill="x", pady=5)
        socar_inner = ttk.Frame(socar_frame)
        socar_inner.pack(fill="x", pady=2)
        ttk.Label(socar_inner, text="Hour rate (RM/h):", width=18).pack(side="left")
        self.socar_hour_var = tk.StringVar(value=str(self.pricing_data.get("SoCar", {}).get("hour_rate", 8.0)))
        ttk.Entry(socar_inner, textvariable=self.socar_hour_var, width=10).pack(side="left", padx=(10, 20))
        ttk.Label(socar_inner, text="Excess km rate (RM/km):", width=22).pack(side="left", padx=(10, 0))
        self.socar_excess_var = tk.StringVar(value=str(self.pricing_data.get("SoCar", {}).get("excess_km_rate", 0.25)))
        ttk.Entry(socar_inner, textvariable=self.socar_excess_var, width=10).pack(side="left", padx=(10, 0))
        ttk.Label(socar_frame, text="Mileage packages: 10km=RM2.50, 50km=RM11, 100km=RM15 (fixed).", font=("Arial", 9)).pack(anchor="w")

        # Save/Load buttons
        button_frame = ttk.Frame(parent)
        button_frame.pack(fill="x", pady=10)
        ttk.Button(
            button_frame, text="Save Pricing Data", command=self.save_pricing_data
        ).pack(side="left", padx=5)
        ttk.Button(
            button_frame, text="Load Default Pricing", command=self.load_default_pricing
        ).pack(side="left", padx=5)
        ttk.Button(
            button_frame, text="Reset to Defaults", command=self.reset_pricing_defaults
        ).pack(side="left", padx=5)

        # Ensure proper focus handling
        self.setup_pricing_focus_handling()

    def setup_pricing_focus_handling(self):
        """Set up proper focus handling for pricing entry fields"""

        def on_entry_click(event):
            event.widget.focus_set()
            event.widget.icursor(0)

        def bind_entry_focus(widget):
            if isinstance(widget, ttk.Entry):
                widget.bind("<Button-1>", on_entry_click)
                widget.bind("<FocusIn>", lambda e: e.widget.focus_set())
            for child in widget.winfo_children():
                bind_entry_focus(child)

        bind_entry_focus(self.calculator_tab)

    def calculate_provider_prices(self):
        """Calculate and display prices for all providers using simplified pricing data"""

        currency = "RM" if (self.calc_region_var.get() or "Singapore") == "Malaysia" else "$"
        def insert_result_row(result, is_best):
            tags = ("best",) if is_best else ()
            distance_fuel_cost = (
                result["distance_cost"]
                if result["distance_cost"] > 0
                else result["fuel_cost"]
            )
            self.calc_results_tree.insert(
                "",
                "end",
                values=(
                    result["provider"],
                    f"{currency}{result['base_cost']:.2f}",
                    f"{currency}{distance_fuel_cost:.2f}",
                    f"{currency}{result['duration_cost']:.2f}",
                    f"{currency}{result['weekend_surcharge']:.2f}",
                    f"{currency}{result['total_cost']:.2f}",
                ),
                tags=tags,
            )

        try:
            distance = float(self.calc_distance_var.get())
            duration = float(self.calc_duration_var.get())
            day_type = self.calc_day_type_var.get()

            # Clear previous results
            for item in self.calc_results_tree.get_children():
                self.calc_results_tree.delete(item)

            # Update pricing data from current inputs (including SoCar)
            self.update_pricing_data_from_inputs()

            # Build pricing data for selected region only (Singapore vs Malaysia)
            region = self.calc_region_var.get() or "Singapore"
            if region not in VALID_REGIONS:
                region = "Singapore"
            region_providers = get_providers_for_region(region)
            pricing_data_for_calc = {
                k: v for k, v in self.pricing_data.items()
                if k in region_providers
            }

            # Use core function to calculate prices
            results = calculate_provider_prices(
                distance, duration, pricing_data_for_calc, day_type
            )

            for i, result in enumerate(results):
                insert_result_row(result, i == 0)

            self.calc_results_tree.tag_configure(
                "best", background="#E8F5E8", foreground="#2E8B57"
            )

            best_provider = results[0]["provider"]
            best_cost = results[0]["total_cost"]
            worst_cost = results[-1]["total_cost"]
            savings = worst_cost - best_cost
            currency = "RM" if (self.calc_region_var.get() or "Singapore") == "Malaysia" else "$"
            summary_text = (
                f"Best Option: {best_provider} ({currency}{best_cost:.2f}) | "
                f"Savings vs most expensive: {currency}{savings:.2f} | "
                f"Distance: {distance}km, Duration: {duration}h, {day_type.title()}"
            )
            self.calc_summary_var.set(summary_text)

        except ValueError:
            messagebox.showerror(
                "Invalid Input", "Please enter valid numbers for distance and duration"
            )
        except Exception as e:
            messagebox.showerror("Calculation Error", f"An error occurred: {str(e)}")

    def update_pricing_data_from_inputs(self):
        """Update pricing data from current input fields (Singapore providers + SoCar)"""
        providers = ["Getgo", "Getgo EV", "Tribecar", "Car Club", "Econ", "Stand"]
        for provider in providers:
            if provider not in self.pricing_data:
                continue
            provider_key = provider.lower().replace(" ", "_")
            pricing_type = self.pricing_data[provider]["pricing_type"]
            try:
                self.pricing_data[provider]["hour_rate"] = float(
                    getattr(self, f"{provider_key}_duration_var").get()
                )
                if pricing_type == "mileage":
                    self.pricing_data[provider]["mileage_rate"] = float(
                        getattr(self, f"{provider_key}_mileage_var").get()
                    )
                else:
                    fuel_value = float(getattr(self, f"{provider_key}_fuel_var").get())
                    self.pricing_data[provider]["usual_fuel_amount"] = fuel_value
            except (ValueError, AttributeError):
                pass
        # SoCar (Malaysia)
        if "SoCar" in self.pricing_data and hasattr(self, "socar_hour_var"):
            try:
                self.pricing_data["SoCar"]["hour_rate"] = float(self.socar_hour_var.get())
                self.pricing_data["SoCar"]["excess_km_rate"] = float(self.socar_excess_var.get())
            except (ValueError, AttributeError):
                pass

    def save_trip_data(self):
        """Save all trip calculation results to the main dataset"""
        try:
            distance = float(self.calc_distance_var.get())
            duration = float(self.calc_duration_var.get())
            day_type = self.calc_day_type_var.get()

            new_records = []
            for item in self.calc_results_tree.get_children():
                values = self.calc_results_tree.item(item)["values"]
                if not values:
                    continue
                provider = values[0]
                total_cost = float(str(values[5]).replace("$", "").replace("RM", ""))

                # Use calculator region so saved record matches calculated region (Singapore/Malaysia)
                calc_region = self.calc_region_var.get() if hasattr(self, "calc_region_var") else "Singapore"
                if calc_region not in VALID_REGIONS:
                    calc_region = "Singapore"
                new_record = create_trip_record(
                    distance, duration, provider, total_cost, day_type,
                    region=calc_region,
                )
                new_records.append(new_record)

            if new_records:
                self.df = (
                    pd.DataFrame(new_records)
                    if self.df is None
                    else pd.concat(
                        [self.df, pd.DataFrame(new_records)], ignore_index=True
                    )
                )
                if hasattr(self, "records_tree"):
                    self.refresh_records()
                messagebox.showinfo(
                    "Success",
                    f"All trip data saved successfully!\nSaved {len(new_records)} records.",
                )
            else:
                messagebox.showwarning(
                    "No Results",
                    "Please calculate prices first before saving trip data.",
                )
        except ValueError:
            messagebox.showerror(
                "Invalid Input", "Please enter valid numbers for distance and duration"
            )
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save trip data: {str(e)}")

    def save_pricing_data(self):
        """Save current pricing configuration to file"""
        try:
            self.update_pricing_data_from_inputs()
            pricing_file = "pricing_config.json"
            with open(pricing_file, "w") as f:
                json.dump(self.pricing_data, f, indent=2)
            messagebox.showinfo("Success", f"Pricing data saved to {pricing_file}")
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save pricing data: {str(e)}")

    # --- Refactored to remove repeated code ---

    default_pricing = {
        "Getgo": {"mileage_rate": 0.39, "hour_rate": 8.0, "pricing_type": "mileage"},
        "Getgo EV": {"mileage_rate": 0.35, "hour_rate": 9.0, "pricing_type": "mileage"},
        "Tribecar": {"usual_fuel_amount": 20, "hour_rate": 8.5, "pricing_type": "fuel"},
        "Car Club": {"mileage_rate": 0.30, "hour_rate": 9.5, "pricing_type": "mileage"},
        "Econ": {"usual_fuel_amount": 15, "hour_rate": 7.5, "pricing_type": "fuel"},
        "Stand": {"usual_fuel_amount": 25, "hour_rate": 10.0, "pricing_type": "fuel"},
        "SoCar": {
            "pricing_type": "socar",
            "hour_rate": 8.0,
            "mileage_packages": [{"km": 10, "price": 2.5}, {"km": 50, "price": 11}, {"km": 100, "price": 15}],
            "excess_km_rate": 0.25,
        },
        "NormalRental": {"pricing_type": "traditional"},
    }

    def load_pricing_data(self):
        """Load pricing configuration from file"""
        try:
            pricing_file = "pricing_config.json"
            if os.path.exists(pricing_file):
                with open(pricing_file, "r") as f:
                    loaded_data = json.load(f)
                self.pricing_data = self.migrate_pricing_data(loaded_data)
            else:
                self.pricing_data = self.default_pricing.copy()
        except Exception as e:
            print(f"Could not load pricing data: {e}")
            self.pricing_data = self.default_pricing.copy()

    def migrate_pricing_data(self, loaded_data):
        """Migrate old pricing data structure to new structure"""
        migrated_data = {}
        for provider, default_config in self.default_pricing.items():
            if provider in loaded_data:
                migrated_data[provider] = loaded_data[provider].copy()
                for key, value in default_config.items():
                    if key not in migrated_data[provider]:
                        migrated_data[provider][key] = value
                if "pricing_type" not in migrated_data[provider]:
                    if provider in ["Tribecar", "Econ", "Stand"]:
                        # Fuel-based providers
                        if "mileage_rate" in migrated_data[provider]:
                            migrated_data[provider]["usual_fuel_amount"] = (
                                migrated_data[provider]["mileage_rate"]
                            )
                            del migrated_data[provider]["mileage_rate"]
                        elif "fuel_rate" in migrated_data[provider]:
                            migrated_data[provider]["usual_fuel_amount"] = (
                                migrated_data[provider]["fuel_rate"]
                            )
                            del migrated_data[provider]["fuel_rate"]
                        migrated_data[provider]["pricing_type"] = "fuel"
                    else:
                        # Mileage-based providers
                        if "fuel_rate" in migrated_data[provider]:
                            migrated_data[provider]["mileage_rate"] = migrated_data[
                                provider
                            ]["fuel_rate"]
                            del migrated_data[provider]["fuel_rate"]
                        migrated_data[provider]["pricing_type"] = "mileage"
            else:
                migrated_data[provider] = default_config.copy()
        # Merge SoCar and NormalRental (Malaysia) from loaded or default
        for provider in ["SoCar", "NormalRental"]:
            if provider not in migrated_data:
                def_cfg = self.default_pricing.get(provider, {})
                if provider in loaded_data:
                    merged = def_cfg.copy()
                    for k, v in loaded_data[provider].items():
                        merged[k] = v
                    migrated_data[provider] = merged
                else:
                    migrated_data[provider] = def_cfg.copy()
        return migrated_data

    def load_default_pricing(self):
        """Load default pricing configuration"""
        self.pricing_data = self.default_pricing.copy()
        self.update_pricing_input_fields()
        messagebox.showinfo("Success", "Default pricing loaded successfully")

    def reset_pricing_defaults(self):
        """Reset all pricing fields to default values"""
        self.load_default_pricing()

    def update_pricing_input_fields(self):
        """Update all pricing input fields with current pricing data"""
        for provider in self.default_pricing:
            if provider in ("SoCar", "NormalRental"):
                continue  # SoCar has its own section below
            provider_key = provider.lower().replace(" ", "_")
            if provider not in self.pricing_data:
                continue
            pricing_type = self.pricing_data[provider]["pricing_type"]
            try:
                getattr(self, f"{provider_key}_duration_var").set(
                    str(self.pricing_data[provider]["hour_rate"])
                )
                if pricing_type == "mileage":
                    getattr(self, f"{provider_key}_mileage_var").set(
                        str(self.pricing_data[provider]["mileage_rate"])
                    )
                else:
                    fuel_value = self.pricing_data[provider].get(
                        "fuel_rate",
                        self.pricing_data[provider].get("usual_fuel_amount", 0),
                    )
                    getattr(self, f"{provider_key}_fuel_var").set(str(fuel_value))
            except AttributeError:
                pass
        if "SoCar" in self.pricing_data and hasattr(self, "socar_hour_var"):
            try:
                self.socar_hour_var.set(str(self.pricing_data["SoCar"].get("hour_rate", 8.0)))
                self.socar_excess_var.set(str(self.pricing_data["SoCar"].get("excess_km_rate", 0.25)))
            except AttributeError:
                pass

    def refresh_saved_data(self):
        """Refresh the saved data table with calculator-generated trips"""
        try:
            for item in self.saved_data_tree.get_children():
                self.saved_data_tree.delete(item)
            if self.df is not None and not self.df.empty:
                calculator_trips = self.df[
                    self.df["Car model"] == "Calculator Generated"
                ].copy()
                if not calculator_trips.empty:
                    calculator_trips = calculator_trips.sort_values("Rental hour")
                    for _, row in calculator_trips.iterrows():
                        self.saved_data_tree.insert(
                            "",
                            "end",
                            values=(
                                row["Date"],
                                row["Car Cat"],
                                f"{row['Distance (KM)']:.1f}",
                                f"{row['Rental hour']:.1f}",
                                row["Weekday/weekend"].title(),
                                f"${row['Total']:.2f}",
                                f"${row['Cost per KM']:.2f}",
                                f"${row['Cost/HR']:.2f}",
                            ),
                        )
                else:
                    self.saved_data_tree.insert(
                        "",
                        "end",
                        values=(
                            "No calculator trips saved yet",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                            "",
                        ),
                    )
            else:
                self.saved_data_tree.insert(
                    "", "end", values=("No data loaded", "", "", "", "", "", "", "")
                )
        except Exception as e:
            print(f"Error refreshing saved data: {e}")

    def clear_saved_data(self):
        """Clear all calculator-generated trip data"""
        try:
            if self.df is not None and not self.df.empty:
                calculator_trips = self.df[self.df["Car model"] == "Calculator Generated"]
                if calculator_trips.empty:
                    messagebox.showinfo("Info", "No calculator-generated trips found to remove")
                    return
                
                # Confirm deletion
                count = len(calculator_trips)
                if not messagebox.askyesno(
                    "Confirm Deletion",
                    f"Are you sure you want to delete {count} calculator-generated trip{'s' if count != 1 else ''}?\n\nThis action cannot be undone."
                ):
                    return
                
                original_count = len(self.df)
                self.df = self.df[self.df["Car model"] != "Calculator Generated"]
                removed_count = original_count - len(self.df)
                
                if removed_count > 0:
                    if hasattr(self, "records_tree"):
                        self.refresh_records()
                    self.refresh_saved_data()
                    self.save_data()  # Save changes
                    messagebox.showinfo(
                        "Success",
                        f"Removed {removed_count} calculator-generated trip{'s' if removed_count != 1 else ''}",
                    )
            else:
                messagebox.showinfo("Info", "No data loaded")
        except Exception as e:
            self._show_user_friendly_error("Error", f"Failed to clear saved data: {str(e)}")

    def export_saved_data(self):
        """Export calculator-generated trip data to CSV"""
        try:
            if self.df is None or self.df.empty:
                messagebox.showinfo("Info", "No data loaded")
                return

            calculator_trips = self.df[self.df["Car model"] == "Calculator Generated"]
            if calculator_trips.empty:
                messagebox.showinfo("Info", "No calculator-generated trips to export")
                return

            from tkinter import filedialog
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                title="Export Calculator Trip Data",
            )
            if file_path:
                calculator_trips.to_csv(file_path, index=False)
                messagebox.showinfo(
                    "Success",
                    f"Exported {len(calculator_trips)} calculator trips to {file_path}",
                )
        except Exception as e:
            messagebox.showerror("Error", f"Failed to export saved data: {str(e)}")
    def generate_budget_prediction(self):
        """Generate ML-based budget prediction using historical data"""
        if not self._check_data_loaded():
            return

        try:
            # Validate budget input
            budget_str = self.monthly_budget_var.get()
            budget_valid, monthly_budget, budget_error = validate_numeric_input(
                budget_str, "Monthly Budget",
                min_value=0.01, max_value=100000, allow_zero=False, allow_negative=False, required=True
            )
            if not budget_valid:
                self._show_user_friendly_error("Invalid Budget", budget_error, "Monthly Budget")
                return
            
            prediction_period = self.prediction_period_var.get()
            confidence_level = self.confidence_level_var.get()

            # Show loading indicator
            loading = LoadingDialog(self.root, "Generating Prediction", "Analyzing historical data and generating budget prediction...")
            loading.show()

            try:
                # Generate ML prediction
                prediction_result = self.create_ml_budget_prediction(
                    monthly_budget, prediction_period, confidence_level
                )
            finally:
                loading.hide()

            # Update UI with results
            self.update_budget_status(prediction_result)
            self.update_prediction_summary(prediction_result)
            self.generate_smart_recommendations(prediction_result)

            # Store prediction data for charts
            self.budget_prediction_data = prediction_result

            # Update chart
            self.update_budget_chart()

            self.status_var.set("Budget prediction generated successfully!")

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid budget amount")
        except Exception as e:
            messagebox.showerror(
                "Prediction Error", f"Failed to generate prediction: {str(e)}"
            )

    def create_ml_budget_prediction(
        self, monthly_budget, prediction_period, confidence_level
    ):
        """Create ML-based budget prediction using historical data"""
        return create_ml_budget_prediction(
            self.df, monthly_budget, prediction_period, confidence_level
        )

    def update_budget_status(self, prediction_result):
        """Update budget status labels"""
        self.budget_status_labels["budget_set"].config(
            text=f"${prediction_result['monthly_budget']:.2f}"
        )
        self.budget_status_labels["predicted_spending"].config(
            text=f"${prediction_result['predicted_spending']:.2f}"
        )
        
        # Color code budget remaining
        remaining = prediction_result["budget_remaining"]
        if remaining < 0:
            color = "red"
            text = f"-${abs(remaining):.2f}"
        else:
            color = "green"
            text = f"${remaining:.2f}"
        
        self.budget_status_labels["budget_remaining"].config(
            text=text, foreground=color
        )
        
        # Risk level with color coding
        risk = prediction_result["risk_level"]
        risk_colors = {"low": "green", "medium": "orange", "high": "red"}
        self.budget_status_labels["risk_level"].config(
            text=risk.title(), foreground=risk_colors.get(risk, "black")
        )
        
        # Confidence score
        confidence = prediction_result["confidence_score"]
        self.budget_status_labels["confidence"].config(text=f"{confidence:.1%}")

    def update_prediction_summary(self, prediction_result):
        """Update prediction summary labels"""
        self.prediction_summary_labels["model_used"].config(
            text="Historical Analysis + ML"
        )
        self.prediction_summary_labels["data_points"].config(
            text=str(prediction_result["data_points"])
        )
        self.prediction_summary_labels["accuracy"].config(
            text=f"{prediction_result['confidence_score']:.1%}"
        )

        trend = prediction_result["spending_trend"]
        trend_emojis = {
            "increasing": "📈",
            "decreasing": "📉",
            "stable": "➡️",
            "insufficient_data": "❓",
        }
        self.prediction_summary_labels["trend"].config(
            text=f"{trend_emojis.get(trend, '❓')} {trend.title()}"
        )

    def generate_smart_recommendations(self, prediction_result):
        """Generate smart recommendations using Ollama LLM based on prediction results"""
        import json
        import requests

        # Prepare context for LLM
        context = {
            "budget_remaining": prediction_result.get("budget_remaining"),
            "risk_level": prediction_result.get("risk_level"),
            "spending_trend": prediction_result.get("spending_trend"),
            "monthly_budget": prediction_result.get("monthly_budget"),
            "predicted_spending": prediction_result.get("predicted_spending"),
            "data_points": prediction_result.get("data_points"),
        }
        # Add provider info if available
        provider_info = ""
        if (
            self.df is not None
            and not self.df.empty
            and "Car Cat" in self.df.columns
            and "Total" in self.df.columns
        ):
            provider_costs = self.df.groupby("Car Cat")["Total"].mean().sort_values()
            cheapest_provider = provider_costs.index[0]
            provider_info = f"Cheapest provider: {cheapest_provider} (${provider_costs.iloc[0]:.2f} avg)"
        else:
            provider_info = "No provider data available."

        # Compose prompt for Ollama
        prompt = (
            "You are a car rental budget assistant. "
            "Given the following user budget analysis, provide concise, actionable recommendations. "
            "Use bullet points and emojis for clarity. "
            "Be specific and practical. "
            f"Budget remaining: ${context['budget_remaining']:.2f}\n"
            f"Risk level: {context['risk_level']}\n"
            f"Spending trend: {context['spending_trend']}\n"
            f"Monthly budget: ${context['monthly_budget']:.2f}\n"
            f"Predicted spending: ${context['predicted_spending']:.2f}\n"
            f"Data points: {context['data_points']}\n"
            f"{provider_info}\n"
            "What are your top recommendations for the user?"
        )

        # Call Ollama API with improved timeout handling
        ollama_url = "http://localhost:11434/api/generate"
        model_name = getattr(self, "ollama_model_var", None)
        if model_name:
            model_name = model_name.get()
        else:
            model_name = "llama3.1:3b"  # Use faster model by default

        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Lower temperature for more consistent responses
                "top_p": 0.9,
                "max_tokens": 500,  # Limit response length for faster generation
            },
        }

        try:
            # Try with shorter timeout first
            response = requests.post(ollama_url, json=payload, timeout=10)
            response.raise_for_status()
            result = response.json()
            llm_reply = result.get("response", "").strip()
            if not llm_reply:
                llm_reply = "No recommendations generated by Ollama."
        except requests.exceptions.Timeout:
            # If timeout, try with even shorter timeout and simpler prompt
            try:
                simple_prompt = (
                    f"Budget: ${context['budget_remaining']:.2f} remaining, "
                    f"Risk: {context['risk_level']}. "
                    f"Give 3 brief budget tips for car rentals."
                )
                simple_payload = {
                    "model": model_name,
                    "prompt": simple_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,
                        "max_tokens": 200,
                    },
                }
                response = requests.post(ollama_url, json=simple_payload, timeout=10)
                response.raise_for_status()
                result = response.json()
                llm_reply = result.get("response", "").strip()
                if not llm_reply:
                    llm_reply = "No recommendations generated by Ollama."
            except Exception:
                llm_reply = self.generate_fallback_recommendations(context)
        except requests.exceptions.ConnectionError:
            llm_reply = self.generate_fallback_recommendations(context)
        except Exception as e:
            llm_reply = self.generate_fallback_recommendations(context)
        
        # Update recommendations text
        self.recommendations_text.delete(1.0, tk.END)
        self.recommendations_text.insert(tk.END, llm_reply)

    def generate_fallback_recommendations(self, context):
        """Generate fallback recommendations when Ollama is unavailable"""
        budget_remaining = context.get("budget_remaining", 0)
        risk_level = context.get("risk_level", "Medium")
        spending_trend = context.get("spending_trend", "Stable")
        monthly_budget = context.get("monthly_budget", 0)
        predicted_spending = context.get("predicted_spending", 0)

        recommendations = []

        # Budget comparison analysis
        if predicted_spending < monthly_budget:
            surplus = monthly_budget - predicted_spending
            recommendations.append(
                f"✅ **Good News**: You're under budget by ${surplus:.2f} per month!"
            )
        elif predicted_spending > monthly_budget:
            deficit = predicted_spending - monthly_budget
            recommendations.append(
                f"⚠️ **Over Budget**: You're spending ${deficit:.2f} more than planned per month"
            )
        else:
            recommendations.append(
                "⚖️ **On Target**: Your spending matches your budget exactly"
            )

        # Risk-based recommendations
        if risk_level.lower() == "high":
            recommendations.extend(
                [
                    "🚨 **High Risk Alert**: Consider reducing rental frequency",
                    "💰 **Budget Tip**: Switch to cheaper providers (Getgo, Car Club)",
                    "⏰ **Time Management**: Plan shorter trips to reduce costs",
                    "📊 **Monitor**: Track spending weekly to avoid overspending",
                ]
            )
        elif risk_level.lower() == "medium":
            recommendations.extend(
                [
                    "⚖️ **Balanced Approach**: Mix expensive and budget rentals",
                    "📅 **Planning**: Book rentals in advance for better rates",
                    "🎯 **Optimize**: Choose providers based on trip distance",
                ]
            )
        else:  # Low risk
            recommendations.extend(
                [
                    "✅ **Good Budget Control**: Continue current spending pattern",
                    "🚗 **Upgrade Option**: Consider premium providers for special occasions",
                    "📈 **Growth**: You can afford more frequent rentals",
                ]
            )

        # Budget-specific recommendations
        if budget_remaining < 100:
            recommendations.extend(
                [
                    "💡 **Emergency Fund**: Keep some budget buffer for unexpected trips",
                    "🔍 **Compare**: Always check multiple providers before booking",
                ]
            )
        elif budget_remaining > 500:
            recommendations.extend(
                [
                    "🎉 **Flexible Budget**: You have room for spontaneous trips",
                    "🌟 **Premium Options**: Consider luxury car rentals occasionally",
                ]
            )

        # Spending trend recommendations
        if spending_trend.lower() == "increasing":
            recommendations.append(
                "📈 **Trend Alert**: Monitor if spending continues to rise"
            )
        elif spending_trend.lower() == "decreasing":
            recommendations.append("📉 **Good Trend**: Keep up the cost-saving habits!")

        return "\n".join(recommendations)

    def update_budget_chart(self):
        """Update budget analysis chart based on selected type"""
        if self.budget_prediction_data is None:
            self.show_budget_chart_placeholder()
            return
        
        chart_type = self.budget_chart_type_var.get()
        
        if chart_type == "Budget vs Prediction":
            self.plot_budget_vs_prediction()
        elif chart_type == "Spending Trends":
            self.plot_spending_trends()
        elif chart_type == "Monthly Breakdown":
            self.plot_monthly_breakdown()
        elif chart_type == "Provider Analysis":
            self.plot_provider_analysis()
        elif chart_type == "Risk Assessment":
            self.plot_risk_assessment()
        elif chart_type == "Historical vs Predicted":
            self.plot_historical_vs_predicted()

    def show_budget_chart_placeholder(self):
        """Show placeholder when no prediction data is available"""
        self.budget_ax.clear()
        self.budget_ax.text(
            0.5,
            0.5,
            "Generate a budget prediction\nto see analysis charts",
            ha="center",
            va="center",
            transform=self.budget_ax.transAxes,
            fontsize=14,
            bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"),
        )
        self.budget_ax.set_xlim(0, 1)
        self.budget_ax.set_ylim(0, 1)
        self.budget_ax.axis("off")
        self.budget_fig.tight_layout()
        self.budget_canvas.draw()

    def plot_budget_vs_prediction(self):
        """Plot budget vs predicted spending comparison"""
        self.budget_ax.clear()
        
        data = self.budget_prediction_data
        categories = ["Budget", "Predicted\nSpending"]
        values = [
            data["monthly_budget"] * data["period_months"],
            data["predicted_spending"],
        ]
        colors = ["#2E8B57", "#FF6347"]
        
        bars = self.budget_ax.bar(categories, values, color=colors, alpha=0.7)
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            self.budget_ax.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + height * 0.01,
                f"${value:.2f}",
                ha="center",
                va="bottom",
                fontsize=10,
                fontweight="bold",
            )
        
        # Add difference line
        diff = values[0] - values[1]
        if diff > 0:
            self.budget_ax.axhline(
                y=values[0],
                color="green",
                linestyle="--",
                alpha=0.5,
                label=f"Surplus: ${diff:.2f}",
            )
        else:
            self.budget_ax.axhline(
                y=values[0],
                color="red",
                linestyle="--",
                alpha=0.5,
                label=f"Deficit: ${abs(diff):.2f}",
            )

        self.budget_ax.set_ylabel("Amount ($)", fontsize=10)
        self.budget_ax.set_title(
            "Budget vs Predicted Spending", fontsize=12, fontweight="bold"
        )
        self.budget_ax.grid(axis="y", linestyle="--", alpha=0.3)
        self.budget_ax.legend()
        
        self.budget_fig.tight_layout()
        self.budget_canvas.draw()

    def plot_spending_trends(self):
        """Plot historical spending trends"""
        self.budget_ax.clear()
        
        data = self.budget_prediction_data
        monthly_data = data["monthly_data"]
        
        # Create month-year labels
        monthly_data["Month_Year"] = (
            monthly_data["Year"].astype(str)
            + "-"
            + monthly_data["Month"].astype(str).str.zfill(2)
        )
        
        # Plot historical spending
        self.budget_ax.plot(
            monthly_data["Month_Year"],
            monthly_data["Total"],
            marker="o",
            linewidth=2,
            markersize=6,
            label="Historical Spending",
        )
        
        # Add trend line
        x_numeric = np.arange(len(monthly_data))
        z = np.polyfit(x_numeric, monthly_data["Total"], 1)
        p = np.poly1d(z)
        self.budget_ax.plot(
            monthly_data["Month_Year"],
            p(x_numeric),
            "r--",
            alpha=0.7,
            label="Trend Line",
        )
        
        # Add average line
        avg_spending = data["avg_monthly_spending"]
        self.budget_ax.axhline(
            y=avg_spending,
            color="orange",
            linestyle=":",
            alpha=0.7,
            label=f"Average: ${avg_spending:.2f}",
        )

        self.budget_ax.set_xlabel("Month", fontsize=10)
        self.budget_ax.set_ylabel("Monthly Spending ($)", fontsize=10)
        self.budget_ax.set_title(
            "Historical Spending Trends", fontsize=12, fontweight="bold"
        )
        self.budget_ax.grid(True, alpha=0.3)
        self.budget_ax.legend()
        self.budget_ax.tick_params(axis="x", rotation=45)
        
        self.budget_fig.tight_layout()
        self.budget_canvas.draw()

    def plot_monthly_breakdown(self):
        """Plot monthly spending breakdown by category"""
        self.budget_ax.clear()
        
        data = self.budget_prediction_data
        monthly_data = data["monthly_data"]
        
        # Calculate spending by weekend vs weekday
        weekend_spending = (
            monthly_data[monthly_data["Is_Weekend"] > 0.5]["Total"].sum()
            if len(monthly_data[monthly_data["Is_Weekend"] > 0.5]) > 0
            else 0
        )
        weekday_spending = (
            monthly_data[monthly_data["Is_Weekend"] <= 0.5]["Total"].sum()
            if len(monthly_data[monthly_data["Is_Weekend"] <= 0.5]) > 0
            else 0
        )
        
        # If no weekend data, estimate from overall data
        if weekend_spending == 0 and weekday_spending == 0:
            total_spending = monthly_data["Total"].sum()
            weekend_spending = total_spending * 0.3  # Estimate 30% weekend
            weekday_spending = total_spending * 0.7  # Estimate 70% weekday
        
        categories = ["Weekday\nSpending", "Weekend\nSpending"]
        values = [weekday_spending, weekend_spending]
        colors = ["#4A90E2", "#F5A623"]
        
        wedges, texts, autotexts = self.budget_ax.pie(
            values, labels=categories, colors=colors, autopct="%1.1f%%", startangle=90
        )
        
        # Add value labels
        for i, (wedge, value) in enumerate(zip(wedges, values)):
            angle = (wedge.theta2 + wedge.theta1) / 2
            x = 0.7 * np.cos(np.radians(angle))
            y = 0.7 * np.sin(np.radians(angle))
            self.budget_ax.text(
                x,
                y,
                f"${value:.2f}",
                ha="center",
                va="center",
                fontsize=10,
                fontweight="bold",
            )

        self.budget_ax.set_title(
            "Spending Breakdown: Weekday vs Weekend", fontsize=12, fontweight="bold"
        )
        
        self.budget_fig.tight_layout()
        self.budget_canvas.draw()

    def plot_provider_analysis(self):
        """Plot spending analysis by provider"""
        if not self._check_data_loaded(show_error=False):
            self.show_budget_chart_placeholder()
            return
        
        self.budget_ax.clear()
        
        # Filter out calculator-generated records for spending analysis
        df_filtered = self.df.copy()
        if "Car model" in df_filtered.columns:
            df_filtered = df_filtered[
                df_filtered["Car model"] != "Calculator Generated"
            ]
        if "Region" in df_filtered.columns:
            df_filtered = df_filtered[df_filtered["Region"] == self._get_current_region()]

        # Group by provider
        provider_stats = (
            df_filtered.groupby("Car Cat")
            .agg(
                {
            "Total": ["sum", "mean", "count"],
            "Distance (KM)": "mean",
                    "Rental hour": "mean",
                }
            )
            .round(2)
        )
        
        # Flatten column names
        provider_stats.columns = [
            "Total_Sum",
            "Total_Mean",
            "Trip_Count",
            "Avg_Distance",
            "Avg_Duration",
        ]
        provider_stats = provider_stats.reset_index()
        
        # Create subplot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Total spending by provider
        providers = provider_stats["Car Cat"].tolist()
        total_spending = provider_stats["Total_Sum"].tolist()
        
        bars1 = ax1.bar(
            providers,
            total_spending,
            color=["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"],
            alpha=0.7,
        )
        ax1.set_ylabel("Total Spending ($)", fontsize=10)
        ax1.set_title("Total Spending by Provider", fontsize=11)
        ax1.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars1, total_spending):
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(total_spending) * 0.01,
                f"${value:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )
        
        # Average cost per trip
        avg_costs = provider_stats["Total_Mean"].tolist()
        bars2 = ax2.bar(
            providers,
            avg_costs,
            color=["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"],
            alpha=0.7,
        )
        ax2.set_ylabel("Average Cost per Trip ($)", fontsize=10)
        ax2.set_title("Average Cost per Trip by Provider", fontsize=11)
        ax2.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars2, avg_costs):
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + max(avg_costs) * 0.01,
                f"${value:.2f}",
                ha="center",
                va="bottom",
                fontsize=9,
            )
        
        # Clear the main axis and use the subplot
        self.budget_ax.clear()
        self.budget_ax.axis("off")
        
        self.budget_fig.tight_layout()
        self.budget_canvas.draw()

    def plot_risk_assessment(self):
        """Risk assessment visualization with criteria shown for each risk level (by % of budget)"""
        self.budget_ax.clear()
        data = self.budget_prediction_data
        risk = data["risk_level"].capitalize()
        confidence = data["confidence_score"]
        remaining = data["budget_remaining"]
        budget = data.get("budget", 1)  # Avoid division by zero

        # Define risk levels, colors, angles, and criteria (by % of budget)
        risk_levels = ["Low", "Medium", "High"]
        risk_colors = ["#2E8B57", "#FFA500", "#FF4500"]
        risk_angles = [0.25 * np.pi, 0.5 * np.pi, 0.75 * np.pi]
        # Example: Low: >40% remaining, Medium: 20-40%, High: <20%
        risk_criteria = {
            "Low": "> 40% of budget left",
            "Medium": "20% - 40% left",
            "High": "< 20% left",
        }

        # Draw gauge background (arc)
        theta = np.linspace(0, np.pi, 200)
        self.budget_ax.plot(
            np.cos(theta), np.sin(theta), color="gray", lw=3, alpha=0.3, zorder=1
        )

        # Draw colored risk sectors
        for i, (level, color, angle) in enumerate(
            zip(risk_levels, risk_colors, risk_angles)
        ):
            start = 0 if i == 0 else risk_angles[i - 1]
            end = angle
            arc_theta = np.linspace(start, end, 50)
            self.budget_ax.plot(
                np.cos(arc_theta),
                np.sin(arc_theta),
                color=color,
                lw=10,
                solid_capstyle="round",
                zorder=2,
            )

        # Draw current risk pointer
        try:
            idx = risk_levels.index(risk)
        except ValueError:
            idx = 1  # Default to Medium if unknown
        pointer_angle = risk_angles[idx]
        self.budget_ax.plot(
            [0, 0.85 * np.cos(pointer_angle)],
            [0, 0.85 * np.sin(pointer_angle)],
            color="black",
            lw=4,
            marker="o",
            markersize=10,
            zorder=3,
        )

        # Add risk labels and criteria
        for i, (level, color, angle) in enumerate(
            zip(risk_levels, risk_colors, risk_angles)
        ):
            x, y = 1.1 * np.cos(angle), 1.1 * np.sin(angle)
            self.budget_ax.text(
                x,
                y,
                f"{level}\n({risk_criteria[level]})",
                color=color,
                fontsize=10,
                fontweight="bold",
                ha="center",
                va="center",
            )

        # Show actual % remaining
        percent_remaining = 100 * remaining / budget if budget else 0

        # Add main info text (centered, mobile-friendly)
        self.budget_ax.text(
            0,
            -0.2,
            f"Risk: {risk}\nConfidence: {confidence:.0%}\nRemaining: ${remaining:.2f} ({percent_remaining:.0f}% of budget)",
            ha="center",
            va="center",
            fontsize=12,
            fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#f9f9f9", edgecolor="#bbb"),
        )

        self.budget_ax.set_xlim(-1.3, 1.3)
        self.budget_ax.set_ylim(-0.7, 1.2)
        self.budget_ax.set_aspect("equal")
        self.budget_ax.axis("off")
        self.budget_ax.set_title(
            "Budget Risk Assessment", fontsize=13, fontweight="bold", pad=15
        )
        
        self.budget_fig.tight_layout()
        self.budget_canvas.draw()

    def plot_historical_vs_predicted(self):
        """Plot historical vs predicted spending comparison"""
        self.budget_ax.clear()
        
        data = self.budget_prediction_data
        monthly_data = data["monthly_data"]
        
        # Create month-year labels
        monthly_data["Month_Year"] = (
            monthly_data["Year"].astype(str)
            + "-"
            + monthly_data["Month"].astype(str).str.zfill(2)
        )
        
        # Plot historical data
        self.budget_ax.plot(
            monthly_data["Month_Year"],
            monthly_data["Total"],
            marker="o",
            linewidth=2,
            markersize=6,
            label="Historical Spending",
            color="#4A90E2",
        )
        
        # Add predicted spending line
        predicted_monthly = data["predicted_spending"] / data["period_months"]
        self.budget_ax.axhline(
            y=predicted_monthly,
            color="red",
            linestyle="--",
            linewidth=2,
            label=f"Predicted: ${predicted_monthly:.2f}/month",
        )
        
        # Add confidence interval
        std = data["spending_std"]
        self.budget_ax.fill_between(
            monthly_data["Month_Year"],
            predicted_monthly - std,
            predicted_monthly + std,
            alpha=0.2,
            color="red",
            label="Confidence Interval",
        )
        
        # Add average line
        avg_spending = data["avg_monthly_spending"]
        self.budget_ax.axhline(
            y=avg_spending,
            color="orange",
            linestyle=":",
            alpha=0.7,
            label=f"Historical Average: ${avg_spending:.2f}",
        )

        self.budget_ax.set_xlabel("Month", fontsize=10)
        self.budget_ax.set_ylabel("Monthly Spending ($)", fontsize=10)
        self.budget_ax.set_title(
            "Historical vs Predicted Spending", fontsize=12, fontweight="bold"
        )
        self.budget_ax.grid(True, alpha=0.3)
        self.budget_ax.legend()
        self.budget_ax.tick_params(axis="x", rotation=45)
        
        self.budget_fig.tight_layout()
        self.budget_canvas.draw()

    def on_budget_chart_type_changed(self, event=None):
        """Handle budget chart type selection change"""
        self.update_budget_chart()

    def on_calculation_type_changed(self, event=None):
        """Handle calculation type change"""
        calc_type = self.calculation_type_var.get()

        if calc_type == "duration_based":
            self.duration_label.grid()
            self.planning_duration_entry.grid()
            self.mileage_label.grid_remove()
            self.mileage_entry.grid_remove()
        else:
            self.duration_label.grid_remove()
            self.planning_duration_entry.grid_remove()
            self.mileage_label.grid()
            self.mileage_entry.grid()

    def calculate_cost_requirements(self):
        """Calculate cost requirements and scenarios (tidied up)"""
        try:
            target_cost = float(self.target_cost_var.get())
            provider = self.planning_provider_var.get()
            calc_type = self.calculation_type_var.get()

            # Clear previous results and breakdowns
            self.results_text.delete(1.0, tk.END)
            for item in self.scenarios_tree.get_children():
                self.scenarios_tree.delete(item)
            for label in self.breakdown_labels.values():
                label.config(text="$0.00")
            self.cost_planning_ax.clear()

            # Get user input
            duration = mileage = None
            if calc_type == "duration_based":
                val = self.planning_duration_var.get()
                if not val:
                    messagebox.showwarning("Input Required", "Please enter monthly duration.")
                    return
                duration = float(val)
            elif calc_type == "mileage_based":
                val = self.planning_mileage_var.get()
                if not val:
                    messagebox.showwarning("Input Required", "Please enter monthly mileage.")
                    return
                mileage = float(val)
            elif calc_type == "both":
                dur_val = self.planning_duration_var.get()
                mil_val = self.planning_mileage_var.get()
                if not dur_val or not mil_val:
                    messagebox.showwarning("Input Required", "Please enter both duration and mileage.")
                    return
                duration = float(dur_val)
                mileage = float(mil_val)

            # Calculate requirements
            result = calculate_cost_requirements(target_cost, duration, mileage, provider)
            if "error" in result:
                self.results_text.insert(tk.END, f"Error: {result['error']}\n")
                return

            # Display results
            if calc_type == "both":
                if not result.get("achievable"):
                    self.results_text.insert(
                        tk.END,
                        f"Target cost of ${target_cost:.2f} is not achievable with {duration}h and {mileage}km.\n"
                    )
                    self.results_text.insert(
                        tk.END, f"Calculated cost: ${result['calculated_cost']:.2f}\n"
                    )
                    self.results_text.insert(
                        tk.END, f"Difference: ${result['difference']:.2f}\n"
                    )
                else:
                    self.results_text.insert(
                        tk.END, f"✅ Target cost of ${target_cost:.2f} is achievable!\n"
                    )
                    self.results_text.insert(
                        tk.END, f"Calculated cost: ${result['calculated_cost']:.2f}\n"
                    )
                    self.results_text.insert(
                        tk.END, f"Remaining budget: ${result['difference']:.2f}\n"
                    )
            elif calc_type == "duration_based":
                if "required_mileage" in result:
                    self.results_text.insert(
                        tk.END, f"Required mileage: {result['required_mileage']:.2f} km\n"
                    )
                    self.results_text.insert(tk.END, f"Duration: {duration} hours\n")
                    self.results_text.insert(tk.END, f"Provider: {provider}\n\n")
                    for scenario in result.get("scenarios", []):
                        self.scenarios_tree.insert(
                            "",
                            "end",
                            values=(
                                scenario["bookings_per_week"],
                                f"{scenario['hours_per_booking']:.2f}",
                                f"{scenario['km_per_booking']:.1f}",
                                f"{scenario['total_hours_per_month']:.1f}",
                            ),
                        )
                else:
                    self.results_text.insert(
                        tk.END, f"Error: {result.get('error', 'Unknown error')}\n"
                    )
            elif calc_type == "mileage_based":
                if "required_duration" in result:
                    duration_info = result["required_duration"]
                    if duration_info.get("impossible"):
                        self.results_text.insert(
                            tk.END, f"❌ {duration_info['reason']}\n"
                        )
                    else:
                        self.results_text.insert(
                            tk.END,
                            f"Required duration: {duration_info['days']}d {duration_info['hours']}h {duration_info['minutes']}m\n"
                        )
                        self.results_text.insert(
                            tk.END, f"Total hours: {duration_info['total_hours']:.2f}\n"
                        )
                        self.results_text.insert(
                            tk.END, f"Mileage: {mileage} km\n"
                        )
                        self.results_text.insert(
                            tk.END, f"Provider: {provider}\n\n"
                        )
                        for scenario in result.get("scenarios", []):
                            self.scenarios_tree.insert(
                                "",
                                "end",
                                values=(
                                    scenario["bookings_per_week"],
                                    f"{scenario['hours_per_booking']:.2f}",
                                    f"{scenario['km_per_booking']:.1f}",
                                    f"{scenario['total_hours_per_month']:.1f}",
                                ),
                            )
                else:
                    self.results_text.insert(
                        tk.END, f"Error: {result.get('error', 'Unknown error')}\n"
                    )

            # Show cost analysis graph
            self.plot_cost_analysis(target_cost, provider, calc_type, duration, mileage)

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numbers")
        except Exception as e:
            messagebox.showerror("Calculation Error", f"An error occurred: {str(e)}")
    def plot_cost_analysis(
        self,
        target_cost,
        provider,
        calc_type="duration_based",
        duration=None,
        mileage=None,
    ):
        """Plot cost analysis graphs for the cost planning tab, ensuring the graph always stays within the frame."""
        try:
            # Clear the old figure and axes completely to avoid overlap
            self.cost_planning_fig.clf()
            self.cost_planning_ax = self.cost_planning_fig.add_subplot(111)

            # Dynamically resize the figure to match the frame size, but never exceed it
            widget = self.cost_planning_canvas.get_tk_widget()
            widget.update_idletasks()
            width = widget.winfo_width()
            height = widget.winfo_height()
            # Convert from pixels to inches for matplotlib (assuming 100 dpi)
            dpi = self.cost_planning_fig.get_dpi()
            # Set a minimum size to avoid zero division, but never exceed the widget size
            min_in = 2
            fig_width = max(min_in, width / dpi) if width > 0 else min_in
            fig_height = max(min_in, height / dpi) if height > 0 else min_in
            self.cost_planning_fig.set_size_inches(fig_width, fig_height, forward=True)

            if calc_type == "duration_based":
                # Plot cost vs mileage for fixed duration
                required_mileage = calculate_required_mileage(
                    target_cost, duration, provider
                )
                if required_mileage and required_mileage > 0:
                    center = required_mileage
                else:
                    center = 2500  # fallback
                lower = max(0, center * 0.8)
                upper = center * 1.2 if center > 0 else 5000
                mileages = np.linspace(lower, upper, 100)
                costs = []

                for m in mileages:
                    breakdown = calculate_cost_breakdown(m, duration, provider)
                    if breakdown:
                        costs.append(breakdown["total_cost"])
                    else:
                        costs.append(0)

                self.cost_planning_ax.plot(
                    mileages,
                    costs,
                    "b-",
                    linewidth=2,
                    label=f"Total Cost ({duration}h)",
                )
                self.cost_planning_ax.axhline(
                    y=target_cost,
                    color="r",
                    linestyle="--",
                    linewidth=2,
                    label=f"Target Cost (${target_cost:.2f})",
                )

                # Mark the required mileage point
                if required_mileage and required_mileage > 0:
                    breakdown = calculate_cost_breakdown(
                        required_mileage, duration, provider
                    )
                    if breakdown:
                        self.cost_planning_ax.plot(
                            required_mileage,
                            breakdown["total_cost"],
                            "go",
                            markersize=8,
                            label=f"Required Mileage ({required_mileage:.0f} km)",
                        )

                self.cost_planning_ax.set_xlabel("Mileage (km)")
                self.cost_planning_ax.set_ylabel("Cost ($)")
                self.cost_planning_ax.set_title(
                    f"Cost vs Mileage for {duration}h Duration ({provider})"
                )
                self.cost_planning_ax.grid(True, alpha=0.3)
                self.cost_planning_ax.legend()

            else:  # mileage_based
                # Plot cost vs duration for fixed mileage
                required_duration = calculate_required_duration(
                    target_cost, mileage, provider
                )
                if required_duration and required_duration["total_hours"] > 0:
                    center = required_duration["total_hours"]
                else:
                    center = 100  # fallback
                lower = max(0, center * 0.8)
                upper = center * 1.2 if center > 0 else 200
                durations = np.linspace(lower, upper, 100)
                costs = []

                for d in durations:
                    breakdown = calculate_cost_breakdown(mileage, d, provider)
                    if breakdown:
                        costs.append(breakdown["total_cost"])
                    else:
                        costs.append(0)

                self.cost_planning_ax.plot(
                    durations,
                    costs,
                    "g-",
                    linewidth=2,
                    label=f"Total Cost ({mileage} km)",
                )
                self.cost_planning_ax.axhline(
                    y=target_cost,
                    color="r",
                    linestyle="--",
                    linewidth=2,
                    label=f"Target Cost (${target_cost:.2f})",
                )

                # Mark the required duration point
                if required_duration and required_duration["total_hours"] > 0:
                    breakdown = calculate_cost_breakdown(
                        mileage, required_duration["total_hours"], provider
                    )
                    if breakdown:
                        self.cost_planning_ax.plot(
                            required_duration["total_hours"],
                            breakdown["total_cost"],
                            "ro",
                            markersize=8,
                            label=f'Required Duration ({required_duration["total_hours"]:.1f}h)',
                        )

                self.cost_planning_ax.set_xlabel("Duration (hours)")
                self.cost_planning_ax.set_ylabel("Cost ($)")
                self.cost_planning_ax.set_title(
                    f"Cost vs Duration for {mileage} km Mileage ({provider})"
                )
                self.cost_planning_ax.grid(True, alpha=0.3)
                self.cost_planning_ax.legend()

            # Apply tight layout and update the canvas
            self.cost_planning_fig.tight_layout()
            self.cost_planning_canvas.draw()

        except Exception as e:
            print(f"Error plotting cost analysis: {e}")
            # If plotting fails, just clear the graph
            self.cost_planning_fig.clf()
            self.cost_planning_ax = self.cost_planning_fig.add_subplot(111)
            self.cost_planning_ax.text(
                0.5,
                0.5,
                "Graph unavailable",
                ha="center",
                va="center",
                transform=self.cost_planning_ax.transAxes,
            )
            self.cost_planning_canvas.draw()

    def plot_provider_comparison(self, target_cost, duration=None, mileage=None):
        """Plot cost comparison across different providers"""
        try:
            self.cost_planning_ax.clear()

            providers = ["Getgo", "Car Club"]
            colors = ["blue", "green", "red", "orange"]

            if duration is not None:
                # Compare providers for fixed duration
                mileages = np.linspace(0, 5000, 100)

                for i, provider in enumerate(providers):
                    costs = []
                    for m in mileages:
                        breakdown = calculate_cost_breakdown(m, duration, provider)
                        if breakdown:
                            costs.append(breakdown["total_cost"])
                        else:
                            costs.append(0)

                    self.cost_planning_ax.plot(
                        mileages,
                        costs,
                        color=colors[i],
                        linewidth=2,
                        label=f"{provider} ({duration}h)",
                    )

                self.cost_planning_ax.axhline(
                    y=target_cost,
                    color="r",
                    linestyle="--",
                    linewidth=2,
                    label=f"Target Cost (${target_cost:.2f})",
                )
                self.cost_planning_ax.set_xlabel("Mileage (km)")
                self.cost_planning_ax.set_ylabel("Cost ($)")
                self.cost_planning_ax.set_title(
                    f"Provider Comparison - Cost vs Mileage for {duration}h Duration"
                )

            else:
                # Compare providers for fixed mileage
                durations = np.linspace(0, 200, 100)

                for i, provider in enumerate(providers):
                    costs = []
                    for d in durations:
                        breakdown = calculate_cost_breakdown(mileage, d, provider)
                        if breakdown:
                            costs.append(breakdown["total_cost"])
                        else:
                            costs.append(0)

                    self.cost_planning_ax.plot(
                        durations,
                        costs,
                        color=colors[i],
                        linewidth=2,
                        label=f"{provider} ({mileage} km)",
                    )

                self.cost_planning_ax.axhline(
                    y=target_cost,
                    color="r",
                    linestyle="--",
                    linewidth=2,
                    label=f"Target Cost (${target_cost:.2f})",
                )
                self.cost_planning_ax.set_xlabel("Duration (hours)")
                self.cost_planning_ax.set_ylabel("Cost ($)")
                self.cost_planning_ax.set_title(
                    f"Provider Comparison - Cost vs Duration for {mileage} km Mileage"
                )

            self.cost_planning_ax.grid(True, alpha=0.3)
            self.cost_planning_ax.legend()
            self.cost_planning_fig.tight_layout()
            self.cost_planning_canvas.draw()

        except Exception as e:
            print(f"Error plotting provider comparison: {e}")
            self.cost_planning_ax.clear()
            self.cost_planning_ax.text(
                0.5,
                0.5,
                "Graph unavailable",
                ha="center",
                va="center",
                transform=self.cost_planning_ax.transAxes,
            )
            self.cost_planning_canvas.draw()

    def plot_cost_breakdown_pie(self, mileage, duration, provider):
        """Plot cost breakdown as a pie chart"""
        try:
            self.cost_planning_ax.clear()

            breakdown = calculate_cost_breakdown(mileage, duration, provider)
            if not breakdown:
                self.cost_planning_ax.text(
                    0.5,
                    0.5,
                    "No data available",
                    ha="center",
                    va="center",
                    transform=self.cost_planning_ax.transAxes,
                )
                self.cost_planning_canvas.draw()
                return

            # Prepare data for pie chart
            labels = ["Mileage Cost", "Duration Cost"]
            sizes = [breakdown["mileage_cost"], breakdown["duration_cost"]]
            colors = ["lightblue", "lightgreen"]

            # Only show non-zero values
            non_zero_labels = []
            non_zero_sizes = []
            non_zero_colors = []

            for i, size in enumerate(sizes):
                if size > 0:
                    non_zero_labels.append(labels[i])
                    non_zero_sizes.append(size)
                    non_zero_colors.append(colors[i])

            if non_zero_sizes:
                wedges, texts, autotexts = self.cost_planning_ax.pie(
                    non_zero_sizes,
                    labels=non_zero_labels,
                    colors=non_zero_colors,
                    autopct="%1.1f%%",
                    startangle=90,
                )
                self.cost_planning_ax.set_title(
                    f"Cost Breakdown - {provider}\n({mileage} km, {duration}h)"
                )
            else:
                self.cost_planning_ax.text(
                    0.5,
                    0.5,
                    "No cost data",
                    ha="center",
                    va="center",
                    transform=self.cost_planning_ax.transAxes,
                )

            self.cost_planning_fig.tight_layout()
            self.cost_planning_canvas.draw()

        except Exception as e:
            print(f"Error plotting cost breakdown: {e}")
            self.cost_planning_ax.clear()
            self.cost_planning_ax.text(
                0.5,
                0.5,
                "Graph unavailable",
                ha="center",
                va="center",
                transform=self.cost_planning_ax.transAxes,
            )
            self.cost_planning_canvas.draw()

    def plot_monthly_trend(
        self, provider, calc_type="duration_based", duration=None, mileage=None
    ):
        """Plot monthly cost trends for different target costs"""
        try:
            self.cost_planning_ax.clear()

            target_costs = np.linspace(500, 3000, 26)  # 26 points from $500 to $3000
            required_values = []

            for target_cost in target_costs:
                if calc_type == "duration_based":
                    required_mileage = calculate_required_mileage(
                        target_cost, duration, provider
                    )
                    required_values.append(required_mileage if required_mileage else 0)
                else:
                    required_duration = calculate_required_duration(
                        target_cost, mileage, provider
                    )
                    required_values.append(
                        required_duration["total_hours"]
                        if required_duration and not required_duration["impossible"]
                        else 0
                    )

            # Filter out impossible scenarios
            valid_indices = [i for i, val in enumerate(required_values) if val > 0]
            valid_costs = [target_costs[i] for i in valid_indices]
            valid_values = [required_values[i] for i in valid_indices]

            if valid_values:
                self.cost_planning_ax.plot(
                    valid_costs,
                    valid_values,
                    "b-",
                    linewidth=2,
                    marker="o",
                    markersize=4,
                )

                if calc_type == "duration_based":
                    self.cost_planning_ax.set_xlabel("Target Monthly Cost ($)")
                    self.cost_planning_ax.set_ylabel("Required Mileage (km)")
                    self.cost_planning_ax.set_title(
                        f"Monthly Cost vs Required Mileage ({provider}, {duration}h)"
                    )
                else:
                    self.cost_planning_ax.set_xlabel("Target Monthly Cost ($)")
                    self.cost_planning_ax.set_ylabel("Required Duration (hours)")
                    self.cost_planning_ax.set_title(
                        f"Monthly Cost vs Required Duration ({provider}, {mileage} km)"
                    )

                self.cost_planning_ax.grid(True, alpha=0.3)
            else:
                self.cost_planning_ax.text(
                    0.5,
                    0.5,
                    "No valid scenarios",
                    ha="center",
                    va="center",
                    transform=self.cost_planning_ax.transAxes,
                )

            self.cost_planning_fig.tight_layout()
            self.cost_planning_canvas.draw()

        except Exception as e:
            print(f"Error plotting monthly trend: {e}")
            self.cost_planning_ax.clear()
            self.cost_planning_ax.text(
                0.5,
                0.5,
                "Graph unavailable",
                ha="center",
                va="center",
                transform=self.cost_planning_ax.transAxes,
            )
            self.cost_planning_canvas.draw()

    def plot_efficiency_analysis(self, target_cost, provider):
        """Plot efficiency analysis showing cost per km vs duration"""
        try:
            self.cost_planning_ax.clear()

            durations = np.linspace(10, 200, 20)
            mileages = np.linspace(100, 5000, 20)

            efficiency_data = []

            for duration in durations:
                for mileage in mileages:
                    breakdown = calculate_cost_breakdown(mileage, duration, provider)
                    if (
                        breakdown and breakdown["total_cost"] <= target_cost * 1.1
                    ):  # Within 10% of target
                        cost_per_km = (
                            breakdown["total_cost"] / mileage if mileage > 0 else 0
                        )
                        efficiency_data.append(
                            {
                                "duration": duration,
                                "mileage": mileage,
                                "cost_per_km": cost_per_km,
                                "total_cost": breakdown["total_cost"],
                            }
                        )

            if efficiency_data:
                # Convert to arrays for plotting
                durations_plot = [d["duration"] for d in efficiency_data]
                mileages_plot = [d["mileage"] for d in efficiency_data]
                costs_per_km = [d["cost_per_km"] for d in efficiency_data]
                total_costs = [d["total_cost"] for d in efficiency_data]

                # Create scatter plot with color based on total cost
                scatter = self.cost_planning_ax.scatter(
                    durations_plot,
                    mileages_plot,
                    c=total_costs,
                    cmap="viridis",
                    s=50,
                    alpha=0.7,
                )

                # Add colorbar
                cbar = plt.colorbar(scatter, ax=self.cost_planning_ax)
                cbar.set_label("Total Cost ($)")

                self.cost_planning_ax.set_xlabel("Duration (hours)")
                self.cost_planning_ax.set_ylabel("Mileage (km)")
                self.cost_planning_ax.set_title(
                    f"Efficiency Analysis - {provider}\n(Scenarios within ${target_cost:.0f} target)"
                )
                self.cost_planning_ax.grid(True, alpha=0.3)
            else:
                self.cost_planning_ax.text(
                    0.5,
                    0.5,
                    "No efficient scenarios found",
                    ha="center",
                    va="center",
                    transform=self.cost_planning_ax.transAxes,
                )

            self.cost_planning_canvas.draw()

        except Exception as e:
            print(f"Error plotting efficiency analysis: {e}")
            self.cost_planning_ax.clear()
            self.cost_planning_ax.text(
                0.5,
                0.5,
                "Graph unavailable",
                ha="center",
                va="center",
                transform=self.cost_planning_ax.transAxes,
            )
            self.cost_planning_canvas.draw()

    def plot_scenario_comparison(
        self,
        target_cost,
        provider,
        calc_type="duration_based",
        duration=None,
        mileage=None,
    ):
        """Plot comparison of different booking scenarios"""
        try:
            self.cost_planning_ax.clear()

            scenarios = generate_booking_scenarios(
                target_cost, duration, mileage, provider
            )

            if not scenarios:
                self.cost_planning_ax.text(
                    0.5,
                    0.5,
                    "No scenarios available",
                    ha="center",
                    va="center",
                    transform=self.cost_planning_ax.transAxes,
                )
                self.cost_planning_canvas.draw()
                return

            # Extract data for plotting
            bookings_per_week = [s["bookings_per_week"] for s in scenarios]
            hours_per_booking = [s["hours_per_booking"] for s in scenarios]
            km_per_booking = [s["km_per_booking"] for s in scenarios]

            # Create a single comprehensive plot
            scatter = self.cost_planning_ax.scatter(
                bookings_per_week,
                hours_per_booking,
                c=km_per_booking,
                cmap="viridis",
                s=100,
                alpha=0.7,
            )
            self.cost_planning_ax.set_xlabel("Bookings per Week")
            self.cost_planning_ax.set_ylabel("Hours per Booking")
            self.cost_planning_ax.set_title(
                f"Booking Scenarios - {provider}\n(Color indicates km per booking)"
            )
            self.cost_planning_ax.grid(True, alpha=0.3)

            # Add colorbar
            cbar = plt.colorbar(scatter, ax=self.cost_planning_ax)
            cbar.set_label("Km per Booking")

            self.cost_planning_canvas.draw()

        except Exception as e:
            print(f"Error plotting scenario comparison: {e}")
            self.cost_planning_ax.clear()
            self.cost_planning_ax.text(
                0.5,
                0.5,
                "Graph unavailable",
                ha="center",
                va="center",
                transform=self.cost_planning_ax.transAxes,
            )
            self.cost_planning_canvas.draw()

    def on_graph_type_changed(self, event=None):
        """Handle graph type selection change"""
        self.update_selected_graph()

    def update_selected_graph(self):
        """Update the graph based on the selected type"""
        try:
            graph_type = self.graph_type_var.get()
            target_cost = float(self.target_cost_var.get())
            provider = self.planning_provider_var.get()
            calc_type = self.calculation_type_var.get()

            # Get duration or mileage based on calculation type
            duration = None
            mileage = None
            if calc_type == "duration_based":
                duration = (
                    float(self.planning_duration_var.get())
                    if self.planning_duration_var.get()
                    else None
                )
            else:
                mileage = (
                    float(self.mileage_var.get()) if self.mileage_var.get() else None
                )

            if graph_type == "Cost Analysis":
                self.plot_cost_analysis(
                    target_cost, provider, calc_type, duration, mileage
                )
            elif graph_type == "Provider Comparison":
                self.plot_provider_comparison(target_cost, duration, mileage)
            elif graph_type == "Cost Breakdown":
                if duration and mileage:
                    self.plot_cost_breakdown_pie(mileage, duration, provider)
                else:
                    # Use default values for demonstration
                    self.plot_cost_breakdown_pie(1000, 50, provider)
            elif graph_type == "Monthly Trend":
                self.plot_monthly_trend(provider, calc_type, duration, mileage)
            elif graph_type == "Efficiency Analysis":
                self.plot_efficiency_analysis(target_cost, provider)
            elif graph_type == "Scenario Comparison":
                self.plot_scenario_comparison(
                    target_cost, provider, calc_type, duration, mileage
                )

        except Exception as e:
            print(f"Error updating graph: {e}")
            self.cost_planning_ax.clear()
            self.cost_planning_ax.text(
                0.5,
                0.5,
                f"Error: {str(e)}",
                ha="center",
                va="center",
                transform=self.cost_planning_ax.transAxes,
            )
            self.cost_planning_canvas.draw()

    def show_car_models_analysis(self, df):
        """Show analysis of car models"""
        if "Car model" not in df.columns:
            messagebox.showwarning("Missing Data", "Car model information is missing")
            return

        # Group by car model
        model_stats = (
            df.groupby("Car model")
            .agg(
                {
                    "Total": ["mean", "count", "sum"],
                    "Distance (KM)": ["sum", "mean"],
                    "Rental hour": ["sum", "mean"],
                    "Consumption (KM/L)": ["mean"],
                }
            )
            .reset_index()
        )

        # Flatten multi-index columns
        model_stats.columns = [
            "_".join(col).strip("_") for col in model_stats.columns.values
        ]

        # Sort by frequency of use
        model_stats = model_stats.sort_values("Total_count", ascending=False).head(10)

        # Display key statistics
        self.add_stat("Total Models", f"{df['Car model'].nunique()}")
        self.add_stat("Most Used Model", f"{model_stats['Car model'].iloc[0]}")
        self.add_stat("Total Trips", f"{len(df)}")
        self.add_stat("Average Trip Cost", f"${df['Total'].mean():.2f}")

        # Create bar chart for model frequency
        models = model_stats["Car model"].tolist()
        trip_counts = model_stats["Total_count"].tolist()

        # Clear the axis and create horizontal bar chart for better readability with long model names
        self.analysis_ax.clear()
        bars = self.analysis_ax.barh(models, trip_counts, color="#4a6984")

        # Add data labels
        for bar in bars:
            width = bar.get_width()
            self.analysis_ax.text(
                width + 0.1,
                bar.get_y() + bar.get_height() / 2,
                f"{int(width)} trips",
                ha="left",
                va="center",
                fontsize=9,
            )

        # Set chart properties
        self.analysis_ax.set_title("Most Used Car Models", fontsize=12)
        self.analysis_ax.set_xlabel("Number of Trips", fontsize=10)
        self.analysis_ax.set_ylabel("Car Model", fontsize=10)
        self.analysis_ax.grid(axis="x", linestyle="--", alpha=0.3)

        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def show_car_categories_analysis(self, df):
        """Show comprehensive analysis of car categories"""
        if "Car Cat" not in df.columns:
            messagebox.showwarning(
                "Missing Data", "Car category information is missing"
            )
            return

        # Clean and validate data
        df_clean = df.copy()

        # Remove rows with missing car categories
        df_clean = df_clean.dropna(subset=["Car Cat"])

        # Remove empty or invalid car categories
        df_clean = df_clean[df_clean["Car Cat"].str.strip() != ""]

        if df_clean.empty:
            messagebox.showwarning("No Valid Data", "No valid car category data found")
            return

        # Group by car category
        category_stats = (
            df_clean.groupby("Car Cat")
            .agg(
                {
                    "Total": ["mean", "count", "sum"],
                    "Distance (KM)": ["sum", "mean"],
                    "Rental hour": ["sum", "mean"],
                    "Cost per KM": ["mean"],
                    "Cost/HR": ["mean"],
                    "Consumption (KM/L)": ["mean"],
                }
            )
            .reset_index()
        )

        # Flatten multi-index columns
        category_stats.columns = [
            "_".join(col).strip("_") for col in category_stats.columns.values
        ]

        # Sort by total spending
        category_stats = category_stats.sort_values("Total_sum", ascending=False)

        # Display key statistics
        self.add_stat("Total Categories", f"{df_clean['Car Cat'].nunique()}")
        self.add_stat("Most Expensive Category", f"{category_stats['Car Cat'].iloc[0]}")
        self.add_stat("Total Trips", f"{len(df_clean)}")
        self.add_stat("Average Trip Cost", f"${df_clean['Total'].mean():.2f}")

        # Add more detailed statistics
        if len(category_stats) > 1:
            cheapest_category = category_stats.loc[
                category_stats["Total_mean"].idxmin(), "Car Cat"
            ]
            self.add_stat("Cheapest Category", f"{cheapest_category}")

        total_distance = df_clean["Distance (KM)"].sum()
        self.add_stat("Total Distance", f"{total_distance:.1f} km")

        # Create subplot for multiple visualizations
        # Clear the figure completely and create 2x2 subplot layout
        self.analysis_fig.clear()
        gs = self.analysis_fig.add_gridspec(2, 2, hspace=0.3, wspace=0.3)

        # 1. Bar chart: Total spending by category
        ax1 = self.analysis_fig.add_subplot(gs[0, 0])
        categories = category_stats["Car Cat"].tolist()
        total_spending = category_stats["Total_sum"].tolist()

        bars1 = ax1.bar(categories, total_spending, color="#4a6984", alpha=0.7)
        ax1.set_title("Total Spending by Category", fontsize=10)
        ax1.set_ylabel("Total Cost ($)", fontsize=9)
        ax1.tick_params(axis="x", rotation=45)

        # Add value labels on bars
        for bar in bars1:
            height = bar.get_height()
            ax1.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + max(total_spending) * 0.01,
                f"${height:.0f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

        # 2. Bar chart: Average cost per trip by category
        ax2 = self.analysis_fig.add_subplot(gs[0, 1])
        avg_costs = category_stats["Total_mean"].tolist()

        bars2 = ax2.bar(categories, avg_costs, color="#e67e22", alpha=0.7)
        ax2.set_title("Average Cost per Trip", fontsize=10)
        ax2.set_ylabel("Average Cost ($)", fontsize=9)
        ax2.tick_params(axis="x", rotation=45)

        # Add value labels on bars
        for bar in bars2:
            height = bar.get_height()
            ax2.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + max(avg_costs) * 0.01,
                f"${height:.1f}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

        # 3. Bar chart: Number of trips by category
        ax3 = self.analysis_fig.add_subplot(gs[1, 0])
        trip_counts = category_stats["Total_count"].tolist()

        bars3 = ax3.bar(categories, trip_counts, color="#27ae60", alpha=0.7)
        ax3.set_title("Number of Trips", fontsize=10)
        ax3.set_ylabel("Trip Count", fontsize=9)
        ax3.tick_params(axis="x", rotation=45)

        # Add value labels on bars
        for bar in bars3:
            height = bar.get_height()
            ax3.text(
                bar.get_x() + bar.get_width() / 2.0,
                height + max(trip_counts) * 0.01,
                f"{int(height)}",
                ha="center",
                va="bottom",
                fontsize=8,
            )

        # 4. Scatter plot: Cost per KM vs Cost per Hour
        ax4 = self.analysis_fig.add_subplot(gs[1, 1])
        cost_per_km = category_stats["Cost per KM_mean"].tolist()
        cost_per_hr = category_stats["Cost/HR_mean"].tolist()

        # Filter out any NaN values for the scatter plot
        valid_indices = []
        valid_categories = []
        valid_cost_km = []
        valid_cost_hr = []

        for i, (km, hr) in enumerate(zip(cost_per_km, cost_per_hr)):
            if not (pd.isna(km) or pd.isna(hr)):
                valid_indices.append(i)
                valid_categories.append(categories[i])
                valid_cost_km.append(km)
                valid_cost_hr.append(hr)

        if valid_cost_km and valid_cost_hr:
            scatter = ax4.scatter(
                valid_cost_km,
                valid_cost_hr,
                s=100,
                alpha=0.7,
                c=range(len(valid_categories)),
                cmap="viridis",
            )
            ax4.set_title("Cost Efficiency Analysis", fontsize=10)
            ax4.set_xlabel("Avg Cost per KM ($)", fontsize=9)
            ax4.set_ylabel("Avg Cost per Hour ($)", fontsize=9)

            # Add category labels to scatter points
            for i, category in enumerate(valid_categories):
                ax4.annotate(
                    category,
                    (valid_cost_km[i], valid_cost_hr[i]),
                    xytext=(5, 5),
                    textcoords="offset points",
                    fontsize=8,
                )
        else:
            ax4.text(
                0.5,
                0.5,
                "Insufficient data\nfor scatter plot",
                ha="center",
                va="center",
                transform=ax4.transAxes,
                fontsize=10,
                color="gray",
            )
            ax4.set_title("Cost Efficiency Analysis", fontsize=10)

        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def show_analysis_placeholder(self):
        """Show placeholder message when no analysis has been run yet"""
        self.analysis_fig.clear()
        self.analysis_ax = self.analysis_fig.add_subplot(111)
        self.analysis_ax.text(
            0.5,
            0.5,
            'Select an analysis type and click "Run Analysis"\nto view your rental data insights',
            ha="center",
            va="center",
            transform=self.analysis_ax.transAxes,
            fontsize=12,
            color="gray",
        )
        self.analysis_ax.set_title("Data Analysis", fontsize=14)
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def refresh_analysis_data(self):
        """Refresh the analysis data and update the current chart"""
        if not self._check_data_loaded():
            return

        # Reload data from file
        try:
            if hasattr(self, "file_path_var") and self.file_path_var.get():
                self.load_data_file(self.file_path_var.get())
                self.update_analysis_chart()
                self.status_var.set("Analysis data refreshed successfully")
            else:
                messagebox.showinfo("No File", "No data file loaded to refresh")
        except Exception as e:
            messagebox.showerror("Refresh Error", f"Failed to refresh data: {str(e)}")
            self.status_var.set("Failed to refresh data")

    def show_monthly_summary(self, df):
        """Show monthly summary of rental activity"""
        if "Date" not in df.columns:
            messagebox.showwarning("Missing Data", "Date information is missing")
            return

        # Ensure Date column is datetime
        df_copy = df.copy()
        if not pd.api.types.is_datetime64_dtype(df_copy["Date"]):
            try:
                df_copy["Date"] = pd.to_datetime(df_copy["Date"])
            except:
                messagebox.showwarning("Data Error", "Could not parse dates correctly")
                return

        # Extract month and year
        df_copy["Month-Year"] = df_copy["Date"].dt.strftime("%b %Y")
        df_copy["Month"] = df_copy["Date"].dt.month
        df_copy["Year"] = df_copy["Date"].dt.year

        # Get unique month-years in chronological order
        month_years = df_copy.sort_values("Date")["Month-Year"].unique()

        # Group by month-year
        monthly_data = (
            df_copy.groupby("Month-Year")
            .agg({"Total": ["count", "sum"], "Distance (KM)": "sum"})
            .reset_index()
        )

        # Flatten multi-index columns
        monthly_data.columns = [
            "_".join(col).strip("_") for col in monthly_data.columns.values
        ]

        # Calculate average distance per trip
        monthly_data["Avg_Distance"] = (
            monthly_data["Distance (KM)_sum"] / monthly_data["Total_count"]
        )

        # Display key statistics
        first_month = month_years[0] if len(month_years) > 0 else "N/A"
        last_month = month_years[-1] if len(month_years) > 0 else "N/A"

        self.add_stat("Period", f"{first_month} to {last_month}")
        self.add_stat("Total Months", f"{len(month_years)}")
        self.add_stat("Total Trips", f"{df_copy['Total'].count()}")
        self.add_stat("Total Spending", f"${df_copy['Total'].sum():.2f}")

        # Reorder for chronological display (ensure month-years are in order)
        monthly_data = (
            monthly_data.set_index("Month-Year").loc[month_years].reset_index()
        )

        # Clear the axis and plot
        self.analysis_ax.clear()
        x = range(len(monthly_data))
        width = 0.35

        # Primary axis: Trip counts
        bars1 = self.analysis_ax.bar(
            [i - width / 2 for i in x],
            monthly_data["Total_count"],
            width,
            label="Trips",
            color="#4a6984",
        )

        # Secondary axis: Total cost
        ax2 = self.analysis_ax.twinx()
        bars2 = ax2.bar(
            [i + width / 2 for i in x],
            monthly_data["Total_sum"],
            width,
            label="Total Cost ($)",
            color="#e67e22",
        )

        # Add labels and configure axes
        self.analysis_ax.set_title("Monthly Rental Activity", fontsize=12)
        self.analysis_ax.set_ylabel("Number of Trips", fontsize=10)
        ax2.set_ylabel("Total Monthly Cost ($)", fontsize=10, color="#e67e22")

        # Set x-ticks to month-year labels
        self.analysis_ax.set_xticks(x)
        self.analysis_ax.set_xticklabels(
            monthly_data["Month-Year"], rotation=45, ha="right"
        )

        # Add grid
        self.analysis_ax.grid(axis="y", linestyle="--", alpha=0.3)

        # Add legend
        lines = [bars1[0], bars2[0]]
        labels = ["Trips", "Total Cost ($)"]
        self.analysis_ax.legend(lines, labels, loc="upper left")

        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def show_fuel_efficiency_analysis(self, df):
        """Show fuel efficiency analysis comparing different car models and providers"""
        if "Consumption (KM/L)" not in df.columns or "Car model" not in df.columns:
            messagebox.showwarning(
                "Missing Data", "Fuel consumption or car model data is missing"
            )
            return

        # Filter out rows with missing fuel consumption data
        df_filtered = df.dropna(subset=["Consumption (KM/L)"])
        if df_filtered.empty:
            messagebox.showwarning("No Data", "No fuel consumption data available")
            return

        # Group by car model and calculate fuel efficiency stats
        fuel_stats = (
            df_filtered.groupby("Car model")
            .agg(
                {
            "Consumption (KM/L)": ["mean", "count", "std"],
            "Total": "mean",
            "Distance (KM)": "mean",
                    "Car Cat": lambda x: x.mode().iloc[0] if not x.empty else "Unknown",
                }
            )
            .round(2)
        )

        # Flatten column names
        fuel_stats.columns = [
            "Avg_Consumption",
            "Trip_Count",
            "Consumption_Std",
            "Avg_Cost",
            "Avg_Distance",
            "Provider",
        ]
        fuel_stats = fuel_stats.reset_index()

        # Filter models with at least 2 trips for statistical significance
        fuel_stats = fuel_stats[fuel_stats["Trip_Count"] >= 2].sort_values(
            "Avg_Consumption", ascending=False
        )

        # Display key statistics
        self.add_stat(
            "Most Efficient",
            f"{fuel_stats.iloc[0]['Car model']} ({fuel_stats.iloc[0]['Avg_Consumption']:.1f} km/L)",
        )
        self.add_stat(
            "Least Efficient",
            f"{fuel_stats.iloc[-1]['Car model']} ({fuel_stats.iloc[-1]['Avg_Consumption']:.1f} km/L)",
        )
        self.add_stat(
            "Average Efficiency", f"{df_filtered['Consumption (KM/L)'].mean():.1f} km/L"
        )
        self.add_stat("Models Analyzed", f"{len(fuel_stats)}")

        # Create visualization
        self.analysis_ax.clear()
        
        # Create horizontal bar chart
        models = fuel_stats["Car model"].tolist()
        consumption = fuel_stats["Avg_Consumption"].tolist()
        colors = [
            "#2E8B57" if x > df_filtered["Consumption (KM/L)"].mean() else "#CD5C5C"
            for x in consumption
        ]
        
        bars = self.analysis_ax.barh(models, consumption, color=colors, alpha=0.7)
        
        # Add average line
        avg_consumption = df_filtered["Consumption (KM/L)"].mean()
        self.analysis_ax.axvline(
            avg_consumption,
            color="red",
            linestyle="--",
            alpha=0.7,
            label=f"Average ({avg_consumption:.1f} km/L)",
        )
        
        # Add value labels on bars
        for i, (bar, value) in enumerate(zip(bars, consumption)):
            self.analysis_ax.text(
                value + 0.5,
                bar.get_y() + bar.get_height() / 2,
                f"{value:.1f}",
                va="center",
                fontsize=9,
            )
        
        self.analysis_ax.set_xlabel("Fuel Consumption (km/L)", fontsize=10)
        self.analysis_ax.set_title("Fuel Efficiency by Car Model", fontsize=12)
        self.analysis_ax.grid(axis="x", linestyle="--", alpha=0.3)
        self.analysis_ax.legend()
        
        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def show_weekend_weekday_analysis(self, df):
        """Show weekend vs weekday cost and usage patterns"""
        if "Weekday/weekend" not in df.columns:
            messagebox.showwarning(
                "Missing Data", "Weekday/weekend information is missing"
            )
            return

        # Group by weekday/weekend
        weekend_stats = (
            df.groupby("Weekday/weekend")
            .agg(
                {
            "Total": ["count", "mean", "sum"],
            "Distance (KM)": "mean",
            "Rental hour": "mean",
                    "Cost per KM": "mean",
                }
            )
            .round(2)
        )

        # Flatten column names
        weekend_stats.columns = [
            "Trip_Count",
            "Avg_Cost",
            "Total_Cost",
            "Avg_Distance",
            "Avg_Duration",
            "Avg_Cost_Per_KM",
        ]
        weekend_stats = weekend_stats.reset_index()

        # Display key statistics
        weekday_data = weekend_stats[weekend_stats["Weekday/weekend"] == "weekday"]
        weekend_data = weekend_stats[weekend_stats["Weekday/weekend"] == "weekend"]
        
        if not weekday_data.empty:
            self.add_stat(
                "Weekday Avg Cost", f"${weekday_data.iloc[0]['Avg_Cost']:.2f}"
            )
            self.add_stat("Weekday Trips", f"{weekday_data.iloc[0]['Trip_Count']}")
        
        if not weekend_data.empty:
            self.add_stat(
                "Weekend Avg Cost", f"${weekend_data.iloc[0]['Avg_Cost']:.2f}"
            )
            self.add_stat("Weekend Trips", f"{weekend_data.iloc[0]['Trip_Count']}")

        # Create visualization
        self.analysis_ax.clear()
        
        # Create subplots within the existing figure
        self.analysis_fig.clear()
        ax1 = self.analysis_fig.add_subplot(1, 2, 1)
        ax2 = self.analysis_fig.add_subplot(1, 2, 2)
        
        # Cost comparison
        days = weekend_stats["Weekday/weekend"].tolist()
        avg_costs = weekend_stats["Avg_Cost"].tolist()
        trip_counts = weekend_stats["Trip_Count"].tolist()
        
        bars1 = ax1.bar(days, avg_costs, color=["#4A90E2", "#F5A623"], alpha=0.7)
        ax1.set_ylabel("Average Cost ($)", fontsize=10)
        ax1.set_title("Average Cost: Weekend vs Weekday", fontsize=11)
        ax1.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars1, avg_costs):
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1,
                f"${value:.2f}",
                ha="center",
                va="bottom",
                fontsize=10,
            )
        
        # Trip count comparison
        bars2 = ax2.bar(days, trip_counts, color=["#4A90E2", "#F5A623"], alpha=0.7)
        ax2.set_ylabel("Number of Trips", fontsize=10)
        ax2.set_title("Trip Frequency: Weekend vs Weekday", fontsize=11)
        ax2.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars2, trip_counts):
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.5,
                f"{int(value)}",
                ha="center",
                va="bottom",
                fontsize=10,
            )
        
        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def show_distance_cost_analysis(self, df):
        """Show correlation between distance and cost"""
        if "Distance (KM)" not in df.columns or "Total" not in df.columns:
            messagebox.showwarning(
                "Missing Data", "Distance or cost information is missing"
            )
            return

        # Filter out rows with missing data
        df_filtered = df.dropna(subset=["Distance (KM)", "Total"])
        if df_filtered.empty:
            messagebox.showwarning("No Data", "No distance/cost data available")
            return

        # Calculate correlation
        correlation = df_filtered["Distance (KM)"].corr(df_filtered["Total"])
        
        # Display key statistics
        self.add_stat("Distance-Cost Correlation", f"{correlation:.3f}")
        self.add_stat("Avg Distance", f"{df_filtered['Distance (KM)'].mean():.1f} km")
        self.add_stat("Avg Cost", f"${df_filtered['Total'].mean():.2f}")
        self.add_stat("Data Points", f"{len(df_filtered)}")

        # Create scatter plot
        self.analysis_ax.clear()
        
        # Color by provider if available
        if "Car Cat" in df_filtered.columns:
            providers = df_filtered["Car Cat"].unique()
            colors = plt.cm.Set3(np.linspace(0, 1, len(providers)))
            color_map = dict(zip(providers, colors))
            
            for provider in providers:
                provider_data = df_filtered[df_filtered["Car Cat"] == provider]
                self.analysis_ax.scatter(
                    provider_data["Distance (KM)"],
                    provider_data["Total"],
                    c=[color_map[provider]],
                    label=provider,
                    alpha=0.6,
                    s=50,
                )
            self.analysis_ax.legend()
        else:
            self.analysis_ax.scatter(
                df_filtered["Distance (KM)"],
                df_filtered["Total"],
                alpha=0.6,
                s=50,
                color="#4A90E2",
            )

        # Add trend line
        z = np.polyfit(df_filtered["Distance (KM)"], df_filtered["Total"], 1)
        p = np.poly1d(z)
        self.analysis_ax.plot(
            df_filtered["Distance (KM)"],
            p(df_filtered["Distance (KM)"]),
            "r--",
            alpha=0.8,
            linewidth=2,
            label=f"Trend (R²={correlation**2:.3f})",
        )
        
        self.analysis_ax.set_xlabel("Distance (km)", fontsize=10)
        self.analysis_ax.set_ylabel("Total Cost ($)", fontsize=10)
        self.analysis_ax.set_title("Distance vs Cost Correlation", fontsize=12)
        self.analysis_ax.grid(True, alpha=0.3)
        self.analysis_ax.legend()
        
        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def show_electric_vs_traditional_analysis(self, df):
        """Show comprehensive comparison between electric and traditional vehicles"""
        # Improved data validation
        has_ev_data = "kWh Used" in df.columns
        has_traditional_data = "Fuel pumped" in df.columns or "Estimated fuel usage" in df.columns
        
        if not has_ev_data and not has_traditional_data:
            messagebox.showwarning(
                "Missing Data", 
                "No EV or traditional vehicle data found. Need 'kWh Used' for EV or 'Fuel pumped'/'Estimated fuel usage' for traditional vehicles."
            )
            return
        
        # Get settings for calculations
        try:
            fuel_price = float(self.fuel_price_var.get()) if hasattr(self, 'fuel_price_var') and self.fuel_price_var.get() else 2.51
            cost_per_kwh = float(self.cost_per_kwh_var.get()) if hasattr(self, 'cost_per_kwh_var') and self.cost_per_kwh_var.get() else 0.45
        except:
            fuel_price = 2.51
            cost_per_kwh = 0.45
        
        # Categorize vehicles - improved logic
        df_copy = df.copy()
        if has_ev_data:
            df_copy["Vehicle_Type"] = df_copy["kWh Used"].apply(
                lambda x: "Electric" if pd.notna(x) and x > 0 else None
            )
        else:
            df_copy["Vehicle_Type"] = None
        
        # Fill in Traditional for non-EV entries
        df_copy["Vehicle_Type"] = df_copy["Vehicle_Type"].fillna("Traditional")
        
        # Separate EV and Traditional data
        ev_df = df_copy[df_copy["Vehicle_Type"] == "Electric"].copy()
        traditional_df = df_copy[df_copy["Vehicle_Type"] == "Traditional"].copy()
        
        # Calculate efficiency metrics
        ev_stats = {}
        traditional_stats = {}
        
        if not ev_df.empty and has_ev_data:
            # EV efficiency: km/kWh
            ev_df_valid = ev_df[(ev_df["kWh Used"].notna()) & (ev_df["kWh Used"] > 0) & (ev_df["Distance (KM)"].notna()) & (ev_df["Distance (KM)"] > 0)]
            if not ev_df_valid.empty:
                ev_df_valid["Efficiency"] = ev_df_valid["Distance (KM)"] / ev_df_valid["kWh Used"]
                ev_stats = {
                    "trip_count": len(ev_df),
                    "avg_cost": ev_df["Total"].mean() if "Total" in ev_df.columns else 0,
                    "total_cost": ev_df["Total"].sum() if "Total" in ev_df.columns else 0,
                    "avg_distance": ev_df["Distance (KM)"].mean() if "Distance (KM)" in ev_df.columns else 0,
                    "total_distance": ev_df["Distance (KM)"].sum() if "Distance (KM)" in ev_df.columns else 0,
                    "avg_duration": ev_df["Rental hour"].mean() if "Rental hour" in ev_df.columns else 0,
                    "total_duration": ev_df["Rental hour"].sum() if "Rental hour" in ev_df.columns else 0,
                    "avg_cost_per_km": ev_df["Cost per KM"].mean() if "Cost per KM" in ev_df.columns else 0,
                    "avg_cost_per_hour": ev_df["Cost/HR"].mean() if "Cost/HR" in ev_df.columns else 0,
                    "avg_efficiency": ev_df_valid["Efficiency"].mean(),  # km/kWh
                    "total_kwh": ev_df["kWh Used"].sum() if "kWh Used" in ev_df.columns else 0,
                    "total_electricity_cost": ev_df["Electricity Cost"].sum() if "Electricity Cost" in ev_df.columns else (ev_df["kWh Used"].sum() * cost_per_kwh if "kWh Used" in ev_df.columns else 0),
                }
        
        if not traditional_df.empty:
            # Traditional efficiency: km/L
            traditional_df_valid = traditional_df[
                (traditional_df["Fuel pumped"].notna() & (traditional_df["Fuel pumped"] > 0)) |
                (traditional_df["Estimated fuel usage"].notna() & (traditional_df["Estimated fuel usage"] > 0))
            ]
            if not traditional_df_valid.empty:
                # Use Fuel pumped if available, otherwise Estimated fuel usage
                fuel_col = "Fuel pumped" if "Fuel pumped" in traditional_df_valid.columns else "Estimated fuel usage"
                traditional_df_valid = traditional_df_valid[
                    (traditional_df_valid["Distance (KM)"].notna()) & 
                    (traditional_df_valid["Distance (KM)"] > 0) &
                    (traditional_df_valid[fuel_col].notna()) & 
                    (traditional_df_valid[fuel_col] > 0)
                ]
                if not traditional_df_valid.empty:
                    traditional_df_valid["Efficiency"] = traditional_df_valid["Distance (KM)"] / traditional_df_valid[fuel_col]
                    fuel_used = traditional_df[fuel_col].sum() if fuel_col in traditional_df.columns else 0
                    traditional_stats = {
                        "trip_count": len(traditional_df),
                        "avg_cost": traditional_df["Total"].mean() if "Total" in traditional_df.columns else 0,
                        "total_cost": traditional_df["Total"].sum() if "Total" in traditional_df.columns else 0,
                        "avg_distance": traditional_df["Distance (KM)"].mean() if "Distance (KM)" in traditional_df.columns else 0,
                        "total_distance": traditional_df["Distance (KM)"].sum() if "Distance (KM)" in traditional_df.columns else 0,
                        "avg_duration": traditional_df["Rental hour"].mean() if "Rental hour" in traditional_df.columns else 0,
                        "total_duration": traditional_df["Rental hour"].sum() if "Rental hour" in traditional_df.columns else 0,
                        "avg_cost_per_km": traditional_df["Cost per KM"].mean() if "Cost per KM" in traditional_df.columns else 0,
                        "avg_cost_per_hour": traditional_df["Cost/HR"].mean() if "Cost/HR" in traditional_df.columns else 0,
                        "avg_efficiency": traditional_df_valid["Efficiency"].mean(),  # km/L
                        "total_fuel": fuel_used,
                        "total_fuel_cost": traditional_df["Fuel cost"].sum() if "Fuel cost" in traditional_df.columns else (fuel_used * fuel_price),
                    }
        
        # Calculate CO2 emissions
        # Traditional: 2.31 kg CO2 per liter of fuel
        # EV: 0.4 kg CO2 per kWh (Singapore grid average)
        if ev_stats and ev_stats.get("total_kwh", 0) > 0:
            ev_stats["total_co2"] = ev_stats["total_kwh"] * 0.4
            ev_stats["avg_co2_per_trip"] = ev_stats["total_co2"] / ev_stats["trip_count"] if ev_stats["trip_count"] > 0 else 0
        
        if traditional_stats and traditional_stats.get("total_fuel", 0) > 0:
            traditional_stats["total_co2"] = traditional_stats["total_fuel"] * 2.31
            traditional_stats["avg_co2_per_trip"] = traditional_stats["total_co2"] / traditional_stats["trip_count"] if traditional_stats["trip_count"] > 0 else 0
        
        # Calculate cost savings
        cost_savings = {}
        if ev_stats and traditional_stats:
            # Estimate what EV trips would cost as traditional
            if ev_stats.get("total_distance", 0) > 0 and traditional_stats.get("avg_efficiency", 0) > 0:
                estimated_fuel_for_ev_trips = ev_stats["total_distance"] / traditional_stats["avg_efficiency"]
                estimated_traditional_cost = estimated_fuel_for_ev_trips * fuel_price
                ev_savings = estimated_traditional_cost - ev_stats.get("total_electricity_cost", 0)
                cost_savings["ev_savings"] = ev_savings
                cost_savings["ev_savings_pct"] = (ev_savings / estimated_traditional_cost * 100) if estimated_traditional_cost > 0 else 0
            
            # Estimate what traditional trips would cost as EV
            if traditional_stats.get("total_distance", 0) > 0 and ev_stats.get("avg_efficiency", 0) > 0:
                estimated_kwh_for_traditional_trips = traditional_stats["total_distance"] / ev_stats["avg_efficiency"]
                estimated_ev_cost = estimated_kwh_for_traditional_trips * cost_per_kwh
                traditional_savings = traditional_stats.get("total_fuel_cost", 0) - estimated_ev_cost
                cost_savings["traditional_savings"] = traditional_savings
                cost_savings["traditional_savings_pct"] = (traditional_savings / traditional_stats.get("total_fuel_cost", 1) * 100) if traditional_stats.get("total_fuel_cost", 0) > 0 else 0
        
        # Display comprehensive statistics
        if ev_stats:
            self.add_stat("EV Trips", f"{ev_stats['trip_count']}")
            self.add_stat("EV Avg Cost", f"${ev_stats['avg_cost']:.2f}")
            self.add_stat("EV Total Cost", f"${ev_stats['total_cost']:.2f}")
            self.add_stat("EV Avg Distance", f"{ev_stats['avg_distance']:.1f} km")
            self.add_stat("EV Total Distance", f"{ev_stats['total_distance']:.1f} km")
            if ev_stats.get("avg_efficiency", 0) > 0:
                self.add_stat("EV Efficiency", f"{ev_stats['avg_efficiency']:.2f} km/kWh")
            self.add_stat("EV Cost/km", f"${ev_stats['avg_cost_per_km']:.3f}")
            self.add_stat("EV Cost/hr", f"${ev_stats['avg_cost_per_hour']:.2f}")
            if ev_stats.get("total_co2", 0) > 0:
                self.add_stat("EV Total CO2", f"{ev_stats['total_co2']:.1f} kg")
                self.add_stat("EV Avg CO2/Trip", f"{ev_stats['avg_co2_per_trip']:.2f} kg")
        
        if traditional_stats:
            self.add_stat("Traditional Trips", f"{traditional_stats['trip_count']}")
            self.add_stat("Traditional Avg Cost", f"${traditional_stats['avg_cost']:.2f}")
            self.add_stat("Traditional Total Cost", f"${traditional_stats['total_cost']:.2f}")
            self.add_stat("Traditional Avg Distance", f"{traditional_stats['avg_distance']:.1f} km")
            self.add_stat("Traditional Total Distance", f"{traditional_stats['total_distance']:.1f} km")
            if traditional_stats.get("avg_efficiency", 0) > 0:
                self.add_stat("Traditional Efficiency", f"{traditional_stats['avg_efficiency']:.2f} km/L")
            self.add_stat("Traditional Cost/km", f"${traditional_stats['avg_cost_per_km']:.3f}")
            self.add_stat("Traditional Cost/hr", f"${traditional_stats['avg_cost_per_hour']:.2f}")
            if traditional_stats.get("total_co2", 0) > 0:
                self.add_stat("Traditional Total CO2", f"{traditional_stats['total_co2']:.1f} kg")
                self.add_stat("Traditional Avg CO2/Trip", f"{traditional_stats['avg_co2_per_trip']:.2f} kg")
        
        # Display cost savings
        if cost_savings:
            if cost_savings.get("ev_savings", 0) > 0:
                self.add_stat("EV Cost Savings", f"${cost_savings['ev_savings']:.2f} ({cost_savings['ev_savings_pct']:.1f}%)")
            if cost_savings.get("traditional_savings", 0) > 0:
                self.add_stat("Traditional Cost Savings", f"${cost_savings['traditional_savings']:.2f} ({cost_savings['traditional_savings_pct']:.1f}%)")
        
        # CO2 savings
        if ev_stats.get("total_co2", 0) > 0 and traditional_stats.get("total_co2", 0) > 0:
            # Compare CO2 per km
            ev_co2_per_km = ev_stats["total_co2"] / ev_stats["total_distance"] if ev_stats["total_distance"] > 0 else 0
            traditional_co2_per_km = traditional_stats["total_co2"] / traditional_stats["total_distance"] if traditional_stats["total_distance"] > 0 else 0
            if ev_co2_per_km > 0 and traditional_co2_per_km > 0:
                co2_savings_pct = ((traditional_co2_per_km - ev_co2_per_km) / traditional_co2_per_km * 100)
                self.add_stat("EV CO2 Savings", f"{co2_savings_pct:.1f}% per km")
        
        # Provider-specific breakdown
        if "Car Cat" in df_copy.columns:
            provider_breakdown = df_copy.groupby(["Car Cat", "Vehicle_Type"]).agg({
                "Total": ["count", "mean"],
                "Distance (KM)": "mean",
            }).round(2)
            provider_breakdown.columns = ["Trip_Count", "Avg_Cost", "Avg_Distance"]
            provider_breakdown = provider_breakdown.reset_index()
            
            # Find providers with both EV and Traditional
            providers_with_both = []
            for provider in provider_breakdown["Car Cat"].unique():
                provider_data = provider_breakdown[provider_breakdown["Car Cat"] == provider]
                has_ev = "Electric" in provider_data["Vehicle_Type"].values
                has_trad = "Traditional" in provider_data["Vehicle_Type"].values
                if has_ev and has_trad:
                    providers_with_both.append(provider)
            
            if providers_with_both:
                self.add_stat("Providers with Both Types", f"{len(providers_with_both)}")
                # Show best EV provider
                ev_providers = provider_breakdown[provider_breakdown["Vehicle_Type"] == "Electric"]
                if not ev_providers.empty:
                    best_ev_provider = ev_providers.loc[ev_providers["Avg_Cost"].idxmin()]
                    self.add_stat("Best EV Provider", f"{best_ev_provider['Car Cat']} (${best_ev_provider['Avg_Cost']:.2f})")
        
        # Trip type analysis (short/medium/long)
        if not ev_df.empty and not traditional_df.empty and "Distance (KM)" in df_copy.columns:
            # Define trip categories
            ev_df["Trip_Type"] = ev_df["Distance (KM)"].apply(
                lambda x: "Short" if x < 50 else ("Medium" if x <= 100 else "Long")
            )
            traditional_df["Trip_Type"] = traditional_df["Distance (KM)"].apply(
                lambda x: "Short" if x < 50 else ("Medium" if x <= 100 else "Long")
            )
            
            # Compare by trip type
            ev_by_type = ev_df.groupby("Trip_Type").agg({
                "Total": ["count", "mean"],
                "Distance (KM)": "mean",
            }).round(2)
            ev_by_type.columns = ["Count", "Avg_Cost", "Avg_Distance"]
            
            trad_by_type = traditional_df.groupby("Trip_Type").agg({
                "Total": ["count", "mean"],
                "Distance (KM)": "mean",
            }).round(2)
            trad_by_type.columns = ["Count", "Avg_Cost", "Avg_Distance"]
            
            # Show which trip type is most common for each
            if not ev_by_type.empty:
                most_common_ev_type = ev_by_type["Count"].idxmax()
                self.add_stat("EV Most Common Trip", f"{most_common_ev_type} ({ev_by_type.loc[most_common_ev_type, 'Count']} trips)")
            if not trad_by_type.empty:
                most_common_trad_type = trad_by_type["Count"].idxmax()
                self.add_stat("Traditional Most Common Trip", f"{most_common_trad_type} ({trad_by_type.loc[most_common_trad_type, 'Count']} trips)")
        
        # Create enhanced visualizations - 2x3 grid
        self.analysis_fig.clear()
        
        # Create 2x3 subplot grid
        gs = self.analysis_fig.add_gridspec(2, 3, hspace=0.3, wspace=0.3)
        
        # Prepare data for charts
        vehicle_types = []
        avg_costs = []
        trip_counts = []
        efficiencies = []
        cost_per_km_list = []
        co2_emissions = []
        
        if ev_stats:
            vehicle_types.append("Electric")
            avg_costs.append(ev_stats["avg_cost"])
            trip_counts.append(ev_stats["trip_count"])
            efficiencies.append(ev_stats.get("avg_efficiency", 0))
            cost_per_km_list.append(ev_stats["avg_cost_per_km"])
            co2_emissions.append(ev_stats.get("avg_co2_per_trip", 0))
        
        if traditional_stats:
            vehicle_types.append("Traditional")
            avg_costs.append(traditional_stats["avg_cost"])
            trip_counts.append(traditional_stats["trip_count"])
            efficiencies.append(traditional_stats.get("avg_efficiency", 0))
            cost_per_km_list.append(traditional_stats["avg_cost_per_km"])
            co2_emissions.append(traditional_stats.get("avg_co2_per_trip", 0))
        
        colors = {"Electric": "#00CED1", "Traditional": "#FF6347"}
        chart_colors = [colors.get(vt, "#808080") for vt in vehicle_types]
        
        # Chart 1: Average Cost Comparison
        ax1 = self.analysis_fig.add_subplot(gs[0, 0])
        if avg_costs:
            bars1 = ax1.bar(vehicle_types, avg_costs, color=chart_colors, alpha=0.7)
            ax1.set_ylabel("Average Cost ($)", fontsize=9)
            ax1.set_title("Average Cost", fontsize=10)
            ax1.grid(axis="y", linestyle="--", alpha=0.3)
            for bar, value in zip(bars1, avg_costs):
                ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(avg_costs) * 0.02,
                        f"${value:.2f}", ha="center", va="bottom", fontsize=8)
        
        # Chart 2: Trip Count
        ax2 = self.analysis_fig.add_subplot(gs[0, 1])
        if trip_counts:
            bars2 = ax2.bar(vehicle_types, trip_counts, color=chart_colors, alpha=0.7)
            ax2.set_ylabel("Number of Trips", fontsize=9)
            ax2.set_title("Usage (Trip Count)", fontsize=10)
            ax2.grid(axis="y", linestyle="--", alpha=0.3)
            for bar, value in zip(bars2, trip_counts):
                ax2.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(trip_counts) * 0.02,
                        f"{int(value)}", ha="center", va="bottom", fontsize=8)
        
        # Chart 3: Efficiency Comparison
        ax3 = self.analysis_fig.add_subplot(gs[0, 2])
        if efficiencies and any(e > 0 for e in efficiencies):
            # Normalize for display (km/kWh vs km/L are different units, show side by side)
            ev_eff = ev_stats.get("avg_efficiency", 0) if ev_stats else 0
            trad_eff = traditional_stats.get("avg_efficiency", 0) if traditional_stats else 0
            if ev_eff > 0 or trad_eff > 0:
                eff_data = []
                eff_labels = []
                if ev_eff > 0:
                    eff_data.append(ev_eff)
                    eff_labels.append("EV\n(km/kWh)")
                if trad_eff > 0:
                    eff_data.append(trad_eff)
                    eff_labels.append("Traditional\n(km/L)")
                bars3 = ax3.bar(eff_labels, eff_data, color=chart_colors[:len(eff_data)], alpha=0.7)
                ax3.set_ylabel("Efficiency", fontsize=9)
                ax3.set_title("Energy Efficiency", fontsize=10)
                ax3.grid(axis="y", linestyle="--", alpha=0.3)
                for bar, value in zip(bars3, eff_data):
                    ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(eff_data) * 0.02,
                            f"{value:.2f}", ha="center", va="bottom", fontsize=8)
        
        # Chart 4: Cost per KM
        ax4 = self.analysis_fig.add_subplot(gs[1, 0])
        if cost_per_km_list and any(c > 0 for c in cost_per_km_list):
            bars4 = ax4.bar(vehicle_types, cost_per_km_list, color=chart_colors, alpha=0.7)
            ax4.set_ylabel("Cost per KM ($)", fontsize=9)
            ax4.set_title("Cost Efficiency", fontsize=10)
            ax4.grid(axis="y", linestyle="--", alpha=0.3)
            for bar, value in zip(bars4, cost_per_km_list):
                ax4.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(cost_per_km_list) * 0.02,
                        f"${value:.3f}", ha="center", va="bottom", fontsize=8)
        
        # Chart 5: Distance Distribution
        ax5 = self.analysis_fig.add_subplot(gs[1, 1])
        ev_distances = []
        trad_distances = []
        if not ev_df.empty and "Distance (KM)" in ev_df.columns:
            ev_distances = ev_df["Distance (KM)"].dropna().tolist()
        if not traditional_df.empty and "Distance (KM)" in traditional_df.columns:
            trad_distances = traditional_df["Distance (KM)"].dropna().tolist()
        
        if len(ev_distances) > 0 or len(trad_distances) > 0:
            hist_data = []
            hist_labels = []
            hist_colors = []
            if len(ev_distances) > 0:
                hist_data.append(ev_distances)
                hist_labels.append("Electric")
                hist_colors.append("#00CED1")
            if len(trad_distances) > 0:
                hist_data.append(trad_distances)
                hist_labels.append("Traditional")
                hist_colors.append("#FF6347")
            
            if len(hist_data) > 0:
                ax5.hist(hist_data, bins=15, label=hist_labels, color=hist_colors, alpha=0.6, edgecolor="black")
                ax5.set_xlabel("Distance (km)", fontsize=9)
                ax5.set_ylabel("Frequency", fontsize=9)
                ax5.set_title("Distance Distribution", fontsize=10)
                if len(hist_labels) > 1:
                    ax5.legend(fontsize=8)
                ax5.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Chart 6: CO2 Emissions
        ax6 = self.analysis_fig.add_subplot(gs[1, 2])
        if co2_emissions and any(c > 0 for c in co2_emissions):
            bars6 = ax6.bar(vehicle_types, co2_emissions, color=chart_colors, alpha=0.7)
            ax6.set_ylabel("CO2 per Trip (kg)", fontsize=9)
            ax6.set_title("Environmental Impact", fontsize=10)
            ax6.grid(axis="y", linestyle="--", alpha=0.3)
            for bar, value in zip(bars6, co2_emissions):
                ax6.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + max(co2_emissions) * 0.02,
                        f"{value:.2f}", ha="center", va="bottom", fontsize=8)
        
        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def show_cost_efficiency_analysis(self, df):
        """Show cost efficiency analysis (cost per km and cost per hour)"""
        if "Cost per KM" not in df.columns or "Cost/HR" not in df.columns:
            messagebox.showwarning("Missing Data", "Cost efficiency data is missing")
            return

        # Filter out rows with missing data
        df_filtered = df.dropna(subset=["Cost per KM", "Cost/HR"])
        if df_filtered.empty:
            messagebox.showwarning("No Data", "No cost efficiency data available")
            return

        # Group by provider for comparison
        if "Car Cat" in df_filtered.columns:
            efficiency_stats = (
                df_filtered.groupby("Car Cat")
                .agg({"Cost per KM": "mean", "Cost/HR": "mean", "Total": "count"})
                .round(3)
            )
            efficiency_stats = efficiency_stats.reset_index()
            
            # Display key statistics
            best_km = efficiency_stats.loc[efficiency_stats["Cost per KM"].idxmin()]
            best_hr = efficiency_stats.loc[efficiency_stats["Cost/HR"].idxmin()]
            
            self.add_stat(
                "Best $/km", f"{best_km['Car Cat']} (${best_km['Cost per KM']:.3f})"
            )
            self.add_stat(
                "Best $/hr", f"{best_hr['Car Cat']} (${best_hr['Cost/HR']:.2f})"
            )
            self.add_stat("Avg $/km", f"${df_filtered['Cost per KM'].mean():.3f}")
            self.add_stat("Avg $/hr", f"${df_filtered['Cost/HR'].mean():.2f}")

            # Create bubble chart
            self.analysis_ax.clear()
            
            providers = efficiency_stats["Car Cat"].tolist()
            cost_per_km = efficiency_stats["Cost per KM"].tolist()
            cost_per_hr = efficiency_stats["Cost/HR"].tolist()
            trip_counts = efficiency_stats["Total"].tolist()
            
            # Create bubble chart
            scatter = self.analysis_ax.scatter(
                cost_per_km,
                cost_per_hr,
                s=[count * 10 for count in trip_counts],
                alpha=0.6,
                c=range(len(providers)),
                cmap="viridis",
            )
            
            # Add labels for each provider
            for i, provider in enumerate(providers):
                self.analysis_ax.annotate(
                    provider,
                    (cost_per_km[i], cost_per_hr[i]),
                    xytext=(5, 5),
                    textcoords="offset points",
                    fontsize=9,
                )
            
            self.analysis_ax.set_xlabel("Cost per KM ($)", fontsize=10)
            self.analysis_ax.set_ylabel("Cost per Hour ($)", fontsize=10)
            self.analysis_ax.set_title(
                "Cost Efficiency Comparison\n(Bubble size = Trip count)", fontsize=12
            )
            self.analysis_ax.grid(True, alpha=0.3)
            
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=self.analysis_ax)
            cbar.set_label("Provider Index", fontsize=9)
        
        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def show_seasonal_patterns_analysis(self, df):
        """Show quarterly patterns in rental behavior"""
        if "Date" not in df.columns:
            messagebox.showwarning("Missing Data", "Date information is missing")
            return

        # Ensure Date column is datetime
        df_copy = df.copy()
        if not pd.api.types.is_datetime64_dtype(df_copy["Date"]):
            try:
                df_copy["Date"] = pd.to_datetime(df_copy["Date"])
            except:
                messagebox.showwarning("Data Error", "Could not parse dates correctly")
                return

        # Extract month and assign quarters
        df_copy["Month"] = df_copy["Date"].dt.month

        def get_quarter(month):
            if 1 <= month <= 4:
                return "Jan-Apr"
            elif 5 <= month <= 8:
                return "May-Aug"
            else:
                return "Sep-Dec"

        df_copy["Quarter"] = df_copy["Month"].apply(get_quarter)

        # Group by quarter
        quarterly_stats = (
            df_copy.groupby("Quarter")
            .agg(
                {
            "Total": ["count", "mean", "sum"],
            "Distance (KM)": "mean",
                    "Rental hour": "mean",
                }
            )
            .round(2)
        )

        # Flatten column names
        quarterly_stats.columns = [
            "Trip_Count",
            "Avg_Cost",
            "Total_Cost",
            "Avg_Distance",
            "Avg_Duration",
        ]
        quarterly_stats = quarterly_stats.reset_index()

        # Reorder quarters
        quarter_order = ["Jan-Apr", "May-Aug", "Sep-Dec"]
        quarterly_stats = (
            quarterly_stats.set_index("Quarter").reindex(quarter_order).reset_index()
        )

        # Display key statistics
        busiest_quarter = quarterly_stats.loc[quarterly_stats["Trip_Count"].idxmax()]
        most_expensive = quarterly_stats.loc[quarterly_stats["Avg_Cost"].idxmax()]

        self.add_stat(
            "Busiest Quarter",
            f"{busiest_quarter['Quarter']} ({busiest_quarter['Trip_Count']} trips)",
        )
        self.add_stat(
            "Most Expensive",
            f"{most_expensive['Quarter']} (${most_expensive['Avg_Cost']:.2f})",
        )
        self.add_stat("Total Quarters", f"{len(quarterly_stats)}")

        # Create visualization
        self.analysis_ax.clear()
        
        quarters = quarterly_stats["Quarter"].tolist()
        trip_counts = quarterly_stats["Trip_Count"].tolist()
        avg_costs = quarterly_stats["Avg_Cost"].tolist()

        # Create subplots within the existing figure
        self.analysis_fig.clear()
        ax1 = self.analysis_fig.add_subplot(1, 2, 1)
        ax2 = self.analysis_fig.add_subplot(1, 2, 2)

        # Colors for quarters
        q_colors = ["#FF6B6B", "#4ECDC4", "#45B7D1"]

        # Trip count by quarter
        bars1 = ax1.bar(
            quarters, trip_counts, color=q_colors[: len(quarters)], alpha=0.7
        )
        ax1.set_ylabel("Number of Trips", fontsize=10)
        ax1.set_title("Trip Frequency by Quarter", fontsize=11)
        ax1.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars1, trip_counts):
            ax1.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 0.5,
                f"{int(value)}",
                ha="center",
                va="bottom",
                fontsize=10,
            )

        # Average cost by quarter
        bars2 = ax2.bar(quarters, avg_costs, color=q_colors[: len(quarters)], alpha=0.7)
        ax2.set_ylabel("Average Cost ($)", fontsize=10)
        ax2.set_title("Average Cost by Quarter", fontsize=11)
        ax2.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars2, avg_costs):
            ax2.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height() + 1,
                f"${value:.2f}",
                ha="center",
                va="bottom",
                fontsize=10,
            )
        
        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def show_usage_patterns_analysis(self, df):
        """Show usage patterns including duration and distance distributions"""
        if "Rental hour" not in df.columns or "Distance (KM)" not in df.columns:
            messagebox.showwarning("Missing Data", "Usage pattern data is missing")
            return

        # Filter out rows with missing data
        df_filtered = df.dropna(subset=["Rental hour", "Distance (KM)"])
        if df_filtered.empty:
            messagebox.showwarning("No Data", "No usage pattern data available")
            return

        # Calculate usage statistics
        duration_stats = df_filtered["Rental hour"].describe()
        distance_stats = df_filtered["Distance (KM)"].describe()
        
        # Display key statistics
        self.add_stat("Avg Duration", f"{duration_stats['mean']:.1f} hours")
        self.add_stat("Avg Distance", f"{distance_stats['mean']:.1f} km")
        self.add_stat("Longest Trip", f"{distance_stats['max']:.1f} km")
        self.add_stat("Shortest Trip", f"{distance_stats['min']:.1f} km")

        # Create visualization
        self.analysis_ax.clear()
        
        # Create subplots within the existing figure
        self.analysis_fig.clear()
        ax1 = self.analysis_fig.add_subplot(1, 2, 1)
        ax2 = self.analysis_fig.add_subplot(1, 2, 2)
        
        # Duration distribution
        ax1.hist(
            df_filtered["Rental hour"],
            bins=20,
            color="#4A90E2",
            alpha=0.7,
            edgecolor="black",
        )
        ax1.set_xlabel("Rental Duration (hours)", fontsize=10)
        ax1.set_ylabel("Frequency", fontsize=10)
        ax1.set_title("Rental Duration Distribution", fontsize=11)
        ax1.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Distance distribution
        ax2.hist(
            df_filtered["Distance (KM)"],
            bins=20,
            color="#F5A623",
            alpha=0.7,
            edgecolor="black",
        )
        ax2.set_xlabel("Distance (km)", fontsize=10)
        ax2.set_ylabel("Frequency", fontsize=10)
        ax2.set_title("Distance Distribution", fontsize=11)
        ax2.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def _on_record_region_changed(self, event=None):
        """When record form region changes, update provider list and set first provider."""
        region = self.record_region_var.get() or "Singapore"
        if region not in VALID_REGIONS:
            region = "Singapore"
        providers = get_providers_for_region(region)
        if hasattr(self, "record_provider_combo") and self.record_provider_combo is not None:
            self.record_provider_combo["values"] = providers
            if providers:
                self.record_provider_var.set(providers[0])
        self.on_provider_changed()

    def on_provider_changed(self, event=None):
        """Handle provider selection change to show/hide EV-specific and NormalRental fields"""
        provider = self.record_provider_var.get()

        # Show/hide cost per kWh field in settings based on provider
        if hasattr(self, "cost_per_kwh_label") and hasattr(self, "cost_per_kwh_entry"):
            if provider == "Getgo(EV)":
                self.cost_per_kwh_label.grid()
                self.cost_per_kwh_entry.grid()
            else:
                self.cost_per_kwh_label.grid_remove()
                self.cost_per_kwh_entry.grid_remove()

        # Show/hide EV information frame in records management
        if hasattr(self, "ev_frame"):
            if provider == "Getgo(EV)":
                self.ev_frame.pack(fill="both", expand=True, padx=5, pady=5)
            else:
                self.ev_frame.pack_forget()

        # Show/hide NormalRental breakdown (Malaysia) frame
        if hasattr(self, "normal_rental_frame"):
            if provider == "NormalRental":
                self.normal_rental_frame.pack(fill="both", expand=True, padx=5, pady=5)
            else:
                self.normal_rental_frame.pack_forget()

        # Update fuel economy comparison if we have the necessary data
        self.update_fuel_economy_comparison()

    def update_fuel_economy_comparison(self):
        """Calculate and display fuel economy comparison between ICE/Hybrid and EV"""
        # Prevent recursive calls (in case this is called from a trace callback)
        if hasattr(self, '_updating_fuel_economy') and self._updating_fuel_economy:
            return
        self._updating_fuel_economy = True
        try:
            # Check if required variables exist
            if not hasattr(self, 'record_distance_var') or not hasattr(self, 'record_provider_var'):
                return
            
            distance = (
                float(self.record_distance_var.get())
                if self.record_distance_var.get()
                else 0
            )
            fuel_usage = (
                float(self.record_fuel_usage_var.get())
                if self.record_fuel_usage_var.get()
                else 0
            )
            kwh_used = (
                float(self.record_kwh_used_var.get())
                if self.record_kwh_used_var.get()
                else 0
            )
            provider = self.record_provider_var.get()

            if distance > 0:
                # Calculate ICE/Hybrid fuel economy (km/L)
                ice_economy = distance / fuel_usage if fuel_usage > 0 else 0

                # Calculate EV efficiency (km/kWh)
                ev_efficiency = distance / kwh_used if kwh_used > 0 else 0

                # Calculate cost comparison
                fuel_price = (
                    float(self.fuel_price_var.get())
                    if self.fuel_price_var.get()
                    else 2.51
                )
                cost_per_kwh = (
                    float(self.cost_per_kwh_var.get())
                    if self.cost_per_kwh_var.get()
                    else 0.45
                )

                ice_cost_per_km = (
                    (fuel_price * fuel_usage) / distance
                    if distance > 0 and fuel_usage > 0
                    else 0
                )
                ev_cost_per_km = (
                    (cost_per_kwh * kwh_used) / distance
                    if distance > 0 and kwh_used > 0
                    else 0
                )

                # Calculate environmental impact (CO2 emissions)
                # ICE: ~2.3 kg CO2/L of fuel, EV: ~0.5 kg CO2/kWh (Singapore grid)
                ice_co2 = fuel_usage * 2.3 if fuel_usage > 0 else 0
                ev_co2 = kwh_used * 0.5 if kwh_used > 0 else 0

                # Update the comparison display
                if hasattr(self, "fuel_economy_comparison_text"):
                    self.fuel_economy_comparison_text.config(state="normal")
                    self.fuel_economy_comparison_text.delete(1.0, tk.END)

                    comparison_text = f"Fuel Economy Comparison:\n\n"
                    comparison_text += f"Distance: {distance:.1f} km\n"
                    comparison_text += f"Provider: {provider}\n\n"

                    if provider == "Getgo(EV)":
                        comparison_text += f"ACTUAL EV DATA:\n"
                        comparison_text += f"  Efficiency: {ev_efficiency:.2f} km/kWh\n"
                        comparison_text += f"  Cost per km: ${ev_cost_per_km:.3f}\n"
                        comparison_text += (
                            f"  Total Cost: ${cost_per_kwh * kwh_used:.2f}\n"
                        )
                        comparison_text += f"  CO2 Emissions: {ev_co2:.1f} kg\n\n"

                        comparison_text += f"ESTIMATED ICE COMPARISON:\n"
                        typical_ice_economy = 12.0  # km/L
                        typical_ice_cost = fuel_price * distance / typical_ice_economy
                        typical_ice_cost_per_km = typical_ice_cost / distance
                        typical_ice_co2 = (distance / typical_ice_economy) * 2.3

                        comparison_text += (
                            f"  Economy: {typical_ice_economy:.1f} km/L\n"
                        )
                        comparison_text += (
                            f"  Cost per km: ${typical_ice_cost_per_km:.3f}\n"
                        )
                        comparison_text += f"  Total Cost: ${typical_ice_cost:.2f}\n"
                        comparison_text += (
                            f"  CO2 Emissions: {typical_ice_co2:.1f} kg\n\n"
                        )

                        savings = typical_ice_cost - (cost_per_kwh * kwh_used)
                        co2_savings = typical_ice_co2 - ev_co2
                        comparison_text += f"EV SAVINGS:\n"
                        comparison_text += f"  Cost Savings: ${savings:.2f}\n"
                        comparison_text += f"  CO2 Reduction: {co2_savings:.1f} kg\n"
                        comparison_text += (
                            f"  Cost Reduction: {(savings/typical_ice_cost)*100:.1f}%"
                            if typical_ice_cost > 0
                            else "  Cost Reduction: N/A"
                        )
                        comparison_text += (
                            f"  CO2 Reduction: {(co2_savings/typical_ice_co2)*100:.1f}%"
                            if typical_ice_co2 > 0
                            else "  CO2 Reduction: N/A"
                        )
                    else:
                        comparison_text += f"ACTUAL ICE/HYBRID DATA:\n"
                        comparison_text += f"  Economy: {ice_economy:.2f} km/L\n"
                        comparison_text += f"  Cost per km: ${ice_cost_per_km:.3f}\n"
                        comparison_text += (
                            f"  Total Cost: ${fuel_price * fuel_usage:.2f}\n"
                        )
                        comparison_text += f"  CO2 Emissions: {ice_co2:.1f} kg\n\n"

                        comparison_text += f"ESTIMATED EV COMPARISON:\n"
                        typical_ev_efficiency = 6.0  # km/kWh
                        typical_ev_cost = (
                            cost_per_kwh * distance / typical_ev_efficiency
                        )
                        typical_ev_cost_per_km = typical_ev_cost / distance
                        typical_ev_co2 = (distance / typical_ev_efficiency) * 0.5

                        comparison_text += (
                            f"  Efficiency: {typical_ev_efficiency:.1f} km/kWh\n"
                        )
                        comparison_text += (
                            f"  Cost per km: ${typical_ev_cost_per_km:.3f}\n"
                        )
                        comparison_text += f"  Total Cost: ${typical_ev_cost:.2f}\n"
                        comparison_text += (
                            f"  CO2 Emissions: {typical_ev_co2:.1f} kg\n\n"
                        )

                        potential_savings = (fuel_price * fuel_usage) - typical_ev_cost
                        potential_co2_savings = ice_co2 - typical_ev_co2
                        comparison_text += f"POTENTIAL EV SAVINGS:\n"
                        comparison_text += f"  Cost Savings: ${potential_savings:.2f}\n"
                        comparison_text += (
                            f"  CO2 Reduction: {potential_co2_savings:.1f} kg\n"
                        )
                        comparison_text += (
                            f"  Cost Reduction: {(potential_savings/(fuel_price * fuel_usage))*100:.1f}%"
                            if (fuel_price * fuel_usage) > 0
                            else "  Cost Reduction: N/A"
                        )
                        comparison_text += (
                            f"  CO2 Reduction: {(potential_co2_savings/ice_co2)*100:.1f}%"
                            if ice_co2 > 0
                            else "  CO2 Reduction: N/A"
                        )

                    self.fuel_economy_comparison_text.insert(tk.END, comparison_text)
                    self.fuel_economy_comparison_text.config(state="disabled")
        except Exception as e:
            # Only print the error if it's not a division by zero (which we've already handled)
            if "division by zero" not in str(e).lower() and "recursion" not in str(e).lower():
                print(f"Error updating fuel economy comparison: {e}")
        finally:
            # Always reset the flag
            self._updating_fuel_economy = False

    def auto_update_fields(self, *args):
        # Prevent recursive calls
        if self._updating_fields:
            return
        self._updating_fields = True
        try:
            fuel_pumped = (
                float(self.record_fuel_pumped_var.get())
                if self.record_fuel_pumped_var.get()
                else 0
            )
            fuel_price = (
                float(self.fuel_price_var.get()) if self.fuel_price_var.get() else 2.51
            )
            distance = (
                float(self.record_distance_var.get())
                if self.record_distance_var.get()
                else 0
            )
            total_cost = (
                float(self.record_total_cost_var.get())
                if self.record_total_cost_var.get()
                else 0
            )
            duration_cost = (
                float(self.record_duration_cost_var.get())
                if self.record_duration_cost_var.get()
                else 0
            )
            provider = self.record_provider_var.get()
            fuel_usage = (
                float(self.record_fuel_usage_var.get())
                if self.record_fuel_usage_var.get()
                else 0
            )
            kwh_used = (
                float(self.record_kwh_used_var.get())
                if self.record_kwh_used_var.get()
                else 0
            )
            cost_per_kwh = (
                float(self.cost_per_kwh_var.get())
                if self.cost_per_kwh_var.get()
                else 0.45
            )

            if provider == "Getgo(EV)":
                # For EVs, calculate electricity cost and set fuel fields to N/A
                electricity_cost = (
                    kwh_used * cost_per_kwh if kwh_used and cost_per_kwh else 0
                )
                self.record_electricity_cost_var.set(
                    f"{electricity_cost:.2f}" if electricity_cost else ""
                )
                self.record_pumped_cost_var.set("N/A")
                self.record_mileage_cost_var.set("N/A")
                self.record_cost_per_km_var.set("N/A")
                self.record_consumption_var.set("N/A")
                # Total cost = duration cost + electricity cost
                if duration_cost or electricity_cost:
                    total = duration_cost + electricity_cost
                    self.record_total_cost_var.set(f"{total:.2f}")
            else:
                # Pumped fuel cost (Esso Singapore 23% discount when toggle on and region Singapore)
                region = (self.record_region_var.get() or "Singapore").strip()
                factor = self._get_fuel_discount_factor(region)
                pumped_fuel_cost = (
                    fuel_price * factor * fuel_pumped if fuel_pumped and fuel_price else 0
                )
                self.record_pumped_cost_var.set(
                    f"{pumped_fuel_cost:.2f}" if pumped_fuel_cost else ""
                )

                # Mileage cost (always recalculate for non-EV)
                mileage_cost = 0
                if provider == "Getgo":
                    mileage_cost = distance * 0.39
                elif provider == "Car Club":
                    mileage_cost = distance * 0.33
                else:
                    mileage_cost = 0
                self.record_mileage_cost_var.set(
                    f"{mileage_cost:.2f}" if mileage_cost else ""
                )

                # Cost per KM
                if distance > 0 and total_cost > 0:
                    cost_per_km = total_cost / distance
                    self.record_cost_per_km_var.set(f"{cost_per_km:.2f}")
                else:
                    self.record_cost_per_km_var.set("")

                # Consumption (KM/L)
                if distance > 0 and fuel_usage > 0:
                    consumption = distance / fuel_usage
                    self.record_consumption_var.set(f"{consumption:.2f}")
                else:
                    self.record_consumption_var.set("")

                # Total cost
                if pumped_fuel_cost or duration_cost or mileage_cost:
                    total = pumped_fuel_cost + duration_cost + mileage_cost
                    self.record_total_cost_var.set(f"{total:.2f}")

            # Calculate Excel formulas for the current record
            self.calculate_excel_formulas_for_current_record()

            # Update fuel economy comparison
            self.update_fuel_economy_comparison()

            # Update status bar with calculation info
            if distance > 0 and total_cost > 0:
                self.status_var.set(
                    f"Record updated - Distance: {distance}km, Total Cost: ${total_cost:.2f}"
                )
            elif distance > 0:
                self.status_var.set(f"Record updated - Distance: {distance}km")
        except Exception as e:
            # Log error but don't show to user for every field change
            print(f"Auto-update error: {e}")
        finally:
            # Always reset the flag, even if an exception occurred
            self._updating_fields = False

    # ========== Prediction Tab Methods ==========
    
    def select_date(self, date_var):
        """Open a calendar picker dialog; one click shows the calendar grid, clicking a day sets the date and closes."""
        try:
            dialog = tk.Toplevel(self.root)
            dialog.title("Select Date")
            dialog.transient(self.root)
            dialog.grab_set()
            try:
                current = datetime.strptime(date_var.get(), "%Y-%m-%d") if date_var.get() else datetime.now()
            except ValueError:
                current = datetime.now()
            year, month, day = current.year, current.month, current.day

            try:
                from tkcalendar import Calendar
                cal = Calendar(
                    dialog, selectmode="day", year=year, month=month, day=day,
                    date_pattern="y-mm-dd",
                )
                cal.pack(padx=10, pady=10)

                def on_date_selected(event=None):
                    sel = cal.selection_get()
                    if sel:
                        date_var.set(sel.strftime("%Y-%m-%d"))
                    dialog.destroy()

                cal.bind("<<CalendarSelected>>", on_date_selected)
                ttk.Button(dialog, text="Cancel", command=dialog.destroy).pack(pady=(0, 10))
            except ImportError:
                dialog.geometry("280x120")
                ttk.Label(dialog, text="Enter date (YYYY-MM-DD):").pack(pady=10)
                date_entry = ttk.Entry(dialog, width=20)
                date_entry.insert(0, date_var.get() if date_var.get() else datetime.now().strftime("%Y-%m-%d"))
                date_entry.pack(pady=5)

                def set_date():
                    try:
                        test_date = pd.to_datetime(date_entry.get())
                        date_var.set(test_date.strftime("%Y-%m-%d"))
                        dialog.destroy()
                    except Exception:
                        messagebox.showerror("Invalid Date", "Please enter date in YYYY-MM-DD format")
                ttk.Button(dialog, text="OK", command=set_date).pack(pady=10)
        except Exception as e:
            messagebox.showerror("Error", f"Date selection error: {e}")
    
    def generate_pattern_prediction(self):
        """Generate rental pattern prediction for date range"""
        if not self._check_data_loaded():
            return
        
        try:
            # Validate date inputs
            start_date_str = self.pattern_start_date_var.get()
            end_date_str = self.pattern_end_date_var.get()
            
            # Validate date range
            range_valid, start_date, end_date, range_error = validate_date_range(
                start_date_str, end_date_str, "Start Date", "End Date"
            )
            if not range_valid:
                self._show_user_friendly_error("Invalid Date Range", range_error)
                return
            
            granularity = self.pattern_granularity_var.get()
            
            # Get Ollama settings
            use_ollama = self.pattern_use_ollama_var.get()
            ollama_model = getattr(self, 'ollama_model_var', None)
            if ollama_model:
                ollama_model = ollama_model.get() if hasattr(ollama_model, 'get') else str(ollama_model)
            else:
                ollama_model = "llama2"
            
            # Show loading indicator for long operations
            if use_ollama:
                loading = LoadingDialog(self.root, "Generating Prediction", "Analyzing patterns with AI reasoning... This may take a moment.")
                loading.show()
            else:
                loading = LoadingDialog(self.root, "Generating Prediction", "Analyzing rental patterns...")
                loading.show()
            
            try:
                # Generate prediction
                result = predict_rental_patterns(
                    self.df, 
                    start_date, 
                    end_date, 
                    granularity,
                    use_ollama_reasoning=use_ollama,
                    ollama_model=ollama_model
                )
                
                if "error" in result:
                    self._show_user_friendly_error("Prediction Error", result["error"])
                    return
                
                # Display results
                self.display_pattern_results(result)
                
                self.status_var.set("Pattern prediction generated successfully!")
            finally:
                loading.hide()
            
        except ValueError as e:
            self._show_user_friendly_error("Invalid Input", f"Please enter valid dates: {e}")
        except Exception as e:
            self._show_user_friendly_error("Prediction Error", f"Failed to generate prediction: {str(e)}\n\nPlease check your data and try again.")
    
    def display_pattern_results(self, result):
        """Display pattern prediction results in UI"""
        # Update summary labels
        self.pattern_summary_labels["total_rentals"].config(
            text=f"{int(result['rental_frequency']['total'])}"
        )
        self.pattern_summary_labels["total_spending"].config(
            text=f"${result['total_spending']:.2f}"
        )
        self.pattern_summary_labels["avg_distance"].config(
            text=f"{result['avg_distance']:.1f} km"
        )
        
        # Most likely provider
        if result['provider_preferences']:
            top_provider = max(result['provider_preferences'].items(), 
                             key=lambda x: x[1]['probability'])
            self.pattern_summary_labels["top_provider"].config(
                text=f"{top_provider[0]} ({top_provider[1]['probability']*100:.0f}%)"
            )
        else:
            self.pattern_summary_labels["top_provider"].config(text="N/A")
        
        # Confidence
        confidence_pct = result['confidence'] * 100
        self.pattern_summary_labels["confidence"].config(
            text=f"{confidence_pct:.0f}%"
        )
        
        # Display AI reasoning if available
        self.pattern_reasoning_text.config(state=tk.NORMAL)
        self.pattern_reasoning_text.delete(1.0, tk.END)
        if "ai_reasoning" in result and result["ai_reasoning"]:
            reasoning_data = result["ai_reasoning"]
            reasoning_text = reasoning_data.get("reasoning", "No reasoning available.")
            model_used = reasoning_data.get("model_used", "Unknown")
            self.pattern_reasoning_text.insert(1.0, f"{reasoning_text}\n\n[Generated using {model_used}]")
            self.pattern_reasoning_frame.pack(fill="both", expand=False, padx=5, pady=5)
        else:
            self.pattern_reasoning_text.insert(1.0, "AI reasoning not available. Enable 'Use AI Reasoning (Ollama)' option to get insights.")
            self.pattern_reasoning_frame.pack(fill="both", expand=False, padx=5, pady=5)
        self.pattern_reasoning_text.config(state=tk.DISABLED)
        
        # Clear and populate table
        for item in self.pattern_table.get_children():
            self.pattern_table.delete(item)
        
        # Display daily predictions if available
        daily_predictions = result.get('daily_predictions', [])
        
        if daily_predictions:
            # Use a probability threshold to determine if rental will occur (default 0.3)
            rental_threshold = 0.3
            
            for pred in daily_predictions:
                will_rent = "Yes" if pred['rental_probability'] >= rental_threshold else "No"
                duration = pred.get('predicted_duration', 0.0)
                distance = pred.get('predicted_distance', 0.0)
                cost = pred.get('predicted_cost', 0.0)
                
                # Only show duration, distance, and cost if rental is predicted
                if pred['rental_probability'] >= rental_threshold:
                    duration_str = f"{duration:.1f}"
                    distance_str = f"{distance:.1f}"
                    cost_str = f"${cost:.2f}"
                else:
                    duration_str = "-"
                    distance_str = "-"
                    cost_str = "-"
                
                # Add probability percentage to rental status for reference
                prob_pct = pred['rental_probability'] * 100
                will_rent_display = f"{will_rent} ({prob_pct:.0f}%)"
                
                # Use different tags for styling (rental vs no rental)
                tags = ("rental",) if pred['rental_probability'] >= rental_threshold else ("no_rental",)
                
                self.pattern_table.insert("", "end", values=(
                    pred['date'],
                    pred.get('day_name', ''),
                    will_rent_display,
                    duration_str,
                    distance_str,
                    cost_str
                ), tags=tags)
            
            # Configure tag colors
            self.pattern_table.tag_configure("rental", background="#e8f5e9")  # Light green
            self.pattern_table.tag_configure("no_rental", background="#fafafa")  # Light gray
        else:
            # Fallback to period-based display if daily predictions not available
            granularity = result['rental_frequency']['granularity']
            total_rentals = result['rental_frequency']['total']
            per_period = result['rental_frequency']['per_period']
            total_spending = result['total_spending']
            avg_distance = result['avg_distance']
            period_rental_distribution = result.get('period_rental_distribution')
            
            start_date = pd.to_datetime(result['date_range']['start'])
            end_date = pd.to_datetime(result['date_range']['end'])
            
            current_date = start_date
            period_num = 1
            
            while current_date <= end_date:
                period_label = ""
                period_date_str = current_date.strftime("%Y-%m-%d")
                
                if granularity == "daily":
                    period_label = period_date_str
                    next_date = current_date + pd.Timedelta(days=1)
                elif granularity == "weekly":
                    period_label = f"Week {period_num} ({period_date_str})"
                    next_date = current_date + pd.Timedelta(days=7)
                else:  # monthly
                    period_label = current_date.strftime("%B %Y")
                    if current_date.month == 12:
                        next_date = current_date.replace(year=current_date.year + 1, month=1, day=1)
                    else:
                        next_date = current_date.replace(month=current_date.month + 1, day=1)
                
                if period_rental_distribution and period_date_str in period_rental_distribution:
                    period_rentals = period_rental_distribution[period_date_str]
                else:
                    period_rentals = round(per_period)
                
                period_spending = (total_spending / total_rentals) * period_rentals if total_rentals > 0 else 0
                
                self.pattern_table.insert("", "end", values=(
                    period_label,
                    "",
                    f"{int(period_rentals)}",
                    "-",
                    f"{avg_distance:.1f}",
                    f"${period_spending:.2f}"
                ))
                
                current_date = next_date
                period_num += 1
                
                if current_date > end_date:
                    break
        
        # Plot chart

    def generate_possibility_prediction(self):
        """Generate rental possibility prediction for specific date"""
        if not self._check_data_loaded():
            return
        
        try:
            # Validate date input
            target_date_str = self.possibility_date_var.get()
            date_valid, target_date, date_error = validate_date_input(
                target_date_str, "Target Date", allow_future=True, required=True
            )
            if not date_valid:
                self._show_user_friendly_error("Invalid Date", date_error, "Target Date")
                return
            
            # Build situation dictionary
            situation = {}
            
            # Trip details with validation
            distance_str = self.possibility_distance_var.get()
            if distance_str:
                dist_valid, distance, dist_error = validate_numeric_input(
                    distance_str, "Distance", min_value=1, max_value=1000, 
                    allow_zero=False, allow_negative=False, required=False
                )
                if dist_valid and distance is not None:
                    situation["distance"] = distance
                elif not dist_valid:
                    self._show_user_friendly_error("Invalid Distance", dist_error, "Distance")
                    return
            
            duration_str = self.possibility_duration_var.get()
            if duration_str:
                dur_valid, duration, dur_error = validate_numeric_input(
                    duration_str, "Duration", min_value=0.1, max_value=24,
                    allow_zero=False, allow_negative=False, required=False
                )
                if dur_valid and duration is not None:
                    situation["duration"] = duration
                elif not dur_valid:
                    self._show_user_friendly_error("Invalid Duration", dur_error, "Duration")
                    return
            
            situation["is_weekend"] = self.possibility_weekend_var.get()
            
            # Contextual factors
            situation["holiday"] = self.possibility_holiday_var.get()
            
            event_str = self.possibility_event_var.get()
            if event_str:
                situation["special_event"] = event_str
            
            weather_str = self.possibility_weather_var.get()
            if weather_str:
                situation["weather"] = weather_str
            
            schedule_str = self.possibility_schedule_var.get()
            if schedule_str:
                situation["personal_schedule"] = schedule_str
            
            # Show loading indicator
            loading = LoadingDialog(self.root, "Generating Prediction", "Analyzing rental possibility...")
            loading.show()
            
            try:
                # Generate prediction
                result = predict_rental_possibility(self.df, target_date, situation)
                
                if "error" in result:
                    self._show_user_friendly_error("Prediction Error", result["error"])
                    return
                
                # Display results
                self.display_possibility_results(result, target_date)
                
                self.status_var.set("Possibility prediction generated successfully!")
            finally:
                loading.hide()
            
        except ValueError as e:
            self._show_user_friendly_error("Invalid Input", f"Please enter valid values: {e}")
        except Exception as e:
            self._show_user_friendly_error("Prediction Error", f"Failed to generate prediction: {str(e)}\n\nPlease check your data and try again.")
    
    def display_possibility_results(self, result, target_date):
        """Display possibility prediction results in UI"""
        # Update possibility score (large display)
        possibility_pct = result['possibility_percentage']
        
        # Color code based on possibility
        if possibility_pct >= 70:
            color = "#28a745"  # Green
        elif possibility_pct >= 40:
            color = "#ffc107"  # Yellow
        else:
            color = "#dc3545"  # Red
        
        self.possibility_score_label.config(
            text=f"{possibility_pct:.0f}%",
            foreground=color
        )
        
        # Update details
        confidence_pct = result['confidence'] * 100
        self.possibility_details_labels["confidence"].config(
            text=f"{confidence_pct:.0f}%"
        )
        
        cost_range = result['expected_cost_range']
        self.possibility_details_labels["cost_range"].config(
            text=f"${cost_range[0]:.2f} - ${cost_range[1]:.2f}"
        )
        
        self.possibility_details_labels["provider"].config(
            text=result['recommended_provider']
        )
        
        self.possibility_details_labels["method"].config(
            text=result['method']
        )
        
        # Update reasoning
        self.possibility_reasoning_text.delete("1.0", tk.END)
        self.possibility_reasoning_text.insert("1.0", result['reasoning'])
        
        # Update historical comparison
        self.possibility_historical_text.delete("1.0", tk.END)
        
        # Find similar historical rentals
        if self.df is not None and not self.df.empty and "Date" in self.df.columns:
            df_copy = self.df.copy()
            if not pd.api.types.is_datetime64_any_dtype(df_copy["Date"]):
                df_copy["Date"] = pd.to_datetime(df_copy["Date"])
            
            # Filter out calculator-generated records
            if "Car model" in df_copy.columns:
                df_copy = df_copy[df_copy["Car model"] != "Calculator Generated"]
            
            # Find rentals on same day of week and month
            target_day = target_date.weekday()
            target_month = target_date.month
            
            similar_rentals = df_copy[
                (df_copy["Date"].dt.weekday == target_day) &
                (df_copy["Date"].dt.month == target_month)
            ]
            
            if len(similar_rentals) > 0:
                historical_text = f"Found {len(similar_rentals)} similar historical rental(s):\n"
                for idx, row in similar_rentals.head(5).iterrows():
                    rental_date = row["Date"].strftime("%Y-%m-%d")
                    provider = row.get("Car Cat", "Unknown")
                    cost = row.get("Total", 0)
                    distance = row.get("Distance (KM)", 0)
                    historical_text += f"• {rental_date}: {provider}, ${cost:.2f}, {distance:.1f}km\n"
            else:
                historical_text = "No similar historical rentals found for this date pattern."
        else:
            historical_text = "Historical comparison unavailable."
        
        self.possibility_historical_text.insert("1.0", historical_text)


# Main function
def main():
    try:
        root = tk.Tk()

        # Set initial window size
        window_width = 1000
        window_height = 700
        root.geometry(f"{window_width}x{window_height}")

        # Create the app
        app = CarRentalRecommenderApp(root)

        # Center the window on screen after app is fully initialized
        try:
            # Wait a moment for the window to be fully created
            root.update_idletasks()

            # Get screen dimensions
            screen_width = root.winfo_screenwidth()
            screen_height = root.winfo_screenheight()

            # Calculate center position
            center_x = int((screen_width - window_width) / 2)
            center_y = int((screen_height - window_height) / 2)

            # Set window position
            root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        except tk.TclError as e:
            # If window centering fails, just use default positioning
            print(f"Warning: Could not center window: {e}")

        # Start the main loop
        root.mainloop()

    except Exception as e:
        print(f"Error starting application: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
