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

        # Import core logic
from car_rental_recommender_core import (
    load_data,
    enhance_dataframe,
    create_complete_cost_analysis,
    calculate_estimated_cost,
    get_recommendations,
    analyze_rental_costs,
    calculate_required_mileage,
    calculate_required_duration,
    generate_booking_scenarios,
    calculate_cost_breakdown,
    get_enhanced_recommendations,
    get_ollama_enhanced_recommendations,
)


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

        # Initialize variables
        self.df = None
        self.cost_analysis = None
        self.settings = {}
        self.selected_record = None
        self.cost_per_kwh_var = tk.StringVar(value="0.45")

        # Initialize StringVar objects that are used across multiple tabs
        self.fuel_price_var = tk.StringVar(value="2.51")
        self.fuel_cost_var = tk.StringVar(value="20")
        self.tank_distance_var = tk.StringVar(value="110")
        self.getgo_mileage_var = tk.StringVar(value="0.39")
        self.carclub_mileage_var = tk.StringVar(value="0.33")

        # Initialize StringVar objects for records management tab
        self.record_date_var = tk.StringVar()
        self.record_car_model_var = tk.StringVar()
        self.record_provider_var = tk.StringVar()
        self.record_distance_var = tk.StringVar()
        self.record_hours_var = tk.StringVar()
        self.record_fuel_pumped_var = tk.StringVar()
        self.record_fuel_usage_var = tk.StringVar()
        self.record_weekend_var = tk.StringVar()
        self.record_total_cost_var = tk.StringVar()
        self.record_pumped_cost_var = tk.StringVar()
        self.record_cost_per_km_var = tk.StringVar()
        self.record_duration_cost_var = tk.StringVar()
        self.record_kwh_used_var = tk.StringVar()
        self.record_electricity_cost_var = tk.StringVar()
        self.search_var = tk.StringVar()

        self.record_consumption_var = tk.StringVar()
        self.record_fuel_savings_var = tk.StringVar()
        self.record_cost_per_hr_var = tk.StringVar()
        self.record_mileage_cost_var = tk.StringVar()
        self.record_kwh_used_var = tk.StringVar()
        self.record_electricity_cost_var = tk.StringVar()

        # Initialize style
        self.style = ttk.Style()

        # Create main container
        self.main_frame = ttk.Frame(root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        # Create tabs
        self.recommendation_tab = ttk.Frame(self.notebook)
        self.data_analysis_tab = ttk.Frame(self.notebook)
        self.records_management_tab = ttk.Frame(self.notebook)
        self.cost_planning_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.recommendation_tab, text="Recommendations")
        self.notebook.add(self.data_analysis_tab, text="Data Analysis")
        self.notebook.add(self.records_management_tab, text="Records Management")
        self.notebook.add(self.cost_planning_tab, text="Budget Planner")
        self.notebook.add(self.settings_tab, text="Settings")

        # Set up each tab
        self.setup_recommendation_tab()
        self.setup_data_analysis_tab()
        self.setup_records_management_tab()
        self.setup_cost_planning_tab()
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

        # Initialize with default data file if it exists
        default_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "22 - Sheet1.csv"
        )
        if os.path.exists(default_file):
            self.load_data_file(default_file)

        # Ensure input fields are properly initialized after a short delay
        self.root.after(100, self.ensure_input_fields_ready)

    def setup_recommendation_tab(self):
        def create_checkbutton(parent, text, variable, **kwargs):
            cb = ttk.Checkbutton(parent, text=text, variable=variable, **kwargs)
            cb.pack(side=tk.LEFT, padx=(0, 10))
            return cb

        def create_label(parent, text, **kwargs):
            lbl = ttk.Label(parent, text=text, **kwargs)
            lbl.pack(side=tk.LEFT, padx=(10, 2))
            return lbl

        def create_combobox(parent, textvariable, values, width, **kwargs):
            cb = ttk.Combobox(
                parent,
                textvariable=textvariable,
                values=values,
                width=width,
                state="readonly",
                **kwargs,
            )
            cb.pack(side=tk.LEFT, padx=(0, 5))
            return cb

        # Create a container frame
        container = ttk.Frame(self.recommendation_tab)
        container.pack(fill=tk.BOTH, expand=True)

        # Create left panel for chat interface
        left_panel = ttk.LabelFrame(
            container, text="Car Rental Assistant", padding=(10, 5)
        )
        left_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5), pady=5)

        # Chat display area
        chat_frame = ttk.Frame(left_panel)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Chat display with scrollbar
        self.chat_display = tk.Text(
            chat_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Segoe UI", 10),
            bg="white",
            relief=tk.SUNKEN,
            borderwidth=1,
        )
        chat_scrollbar = ttk.Scrollbar(
            chat_frame, orient=tk.VERTICAL, command=self.chat_display.yview
        )
        self.chat_display.configure(yscrollcommand=chat_scrollbar.set)
        self.chat_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chat_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Input area
        input_frame = ttk.Frame(left_panel)
        input_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        # Message input field
        self.message_var = tk.StringVar()
        self.message_entry = ttk.Entry(
            input_frame,
            textvariable=self.message_var,
            font=("Segoe UI", 10),
            state="normal",
        )
        self.message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

        # Send button
        send_button = ttk.Button(
            input_frame, text="Send", command=self.send_message, style="Accent.TButton"
        )
        send_button.pack(side=tk.RIGHT)

        # Bind Enter key to send message
        self.message_entry.bind("<Return>", lambda e: self.send_message())

        # Settings panel
        settings_frame = ttk.LabelFrame(left_panel, text="Settings", padding=(5, 5))
        settings_frame.pack(fill=tk.X, padx=5, pady=(5, 0))

        # Weekend checkbox
        self.is_weekend_var = tk.BooleanVar()
        create_checkbutton(settings_frame, "Weekend Trip", self.is_weekend_var)

        # Machine Learning option
        self.use_ml_var = tk.BooleanVar(value=True)
        create_checkbutton(settings_frame, "Use Machine Learning", self.use_ml_var)

        # Ollama LLM option
        self.use_ollama_var = tk.BooleanVar(value=False)
        create_checkbutton(settings_frame, "Use Ollama LLM", self.use_ollama_var)

        # Ollama model selection
        create_label(settings_frame, "Model:")
        self.ollama_model_var = tk.StringVar(value="llama3.2:3b")
        create_combobox(
            settings_frame,
            self.ollama_model_var,
            [
                "llama3.2:3b",
                "llama2",
                "llama2:7b",
                "llama2:13b",
                "mistral",
                "codellama",
                "neural-chat",
            ],
            width=12,
        )

        # Car category selection
        create_label(settings_frame, "Category:")
        self.car_cat_var = tk.StringVar(value="All")
        car_cat_combo = ttk.Combobox(
            settings_frame,
            textvariable=self.car_cat_var,
            values=["All", "Getgo", "Car Club", "Econ", "Stand", "Getgo(EV)"],
            width=10,
            state="readonly",
        )
        car_cat_combo.pack(side=tk.LEFT)

        # Initialize chat state with enhanced memory
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

        # Start the conversation
        self.start_chat()

        # Create right panel for results
        right_panel = ttk.LabelFrame(container, text="Recommendations", padding=(10, 5))
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0), pady=5)

        # Error display area
        error_frame = ttk.LabelFrame(right_panel, text="Error Log", padding=(5, 5))
        error_frame.pack(fill=tk.X, padx=5, pady=(0, 5))

        # Error display with scrollbar and clear button
        error_display_frame = ttk.Frame(error_frame)
        error_display_frame.pack(fill=tk.BOTH, expand=True)

        self.error_display = tk.Text(
            error_display_frame,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Segoe UI", 9),
            bg="#fff5f5",
            fg="#d73a49",
            relief=tk.SUNKEN,
            borderwidth=1,
            height=3,
        )
        error_scrollbar = ttk.Scrollbar(
            error_display_frame, orient=tk.VERTICAL, command=self.error_display.yview
        )
        self.error_display.configure(yscrollcommand=error_scrollbar.set)

        # Clear button for error display
        clear_error_button = ttk.Button(
            error_display_frame,
            text="Clear",
            command=self.clear_error_display,
            style="Accent.TButton",
        )

        self.error_display.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        error_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        clear_error_button.pack(side=tk.RIGHT, padx=(5, 0))

        # Results treeview
        self.results_tree = ttk.Treeview(
            right_panel,
            columns=(
                "provider",
                "car_model",
                "cost",
                "method",
                "confidence",
                "reasoning",
                "full_reasoning",
            ),
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
                self.results_tree.column(
                    col, width=width, anchor=anchor, stretch=(col != "full_reasoning")
                )
            else:
                self.results_tree.column(
                    col, width=width, stretch=(col != "full_reasoning")
                )
        self.results_tree.column("full_reasoning", stretch=False)

        # Add scrollbar to treeview
        results_scroll = ttk.Scrollbar(
            right_panel, orient=tk.VERTICAL, command=self.results_tree.yview
        )
        self.results_tree.configure(yscrollcommand=results_scroll.set)

        # Bind double-click event to show detailed explanation
        self.results_tree.bind("<Double-1>", self.show_recommendation_details)

        results_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Add chart frame
        self.chart_frame = ttk.LabelFrame(
            right_panel, text="Cost Comparison", padding=(10, 5)
        )
        self.chart_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create a placeholder for the chart
        self.fig, self.ax = plt.subplots(figsize=(5, 3), dpi=100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.chart_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        # Data file selection frame
        file_frame = ttk.LabelFrame(right_panel, text="Data Source", padding=5)
        file_frame.pack(fill=tk.X, padx=5, pady=5)

        # Variables for file display
        self.data_file_var = tk.StringVar()
        self.file_path_var = tk.StringVar()

        # File label
        file_label = ttk.Label(file_frame, text="Loaded File:", width=12, anchor="w")
        file_label.grid(row=0, column=0, sticky=tk.W, padx=(0, 2), pady=2)

        # File name (short, read-only)
        file_name_entry = ttk.Entry(
            file_frame,
            textvariable=self.data_file_var,
            state="readonly",
            width=24,
            font=("Segoe UI", 9),
        )
        file_name_entry.grid(row=0, column=1, sticky=tk.W + tk.E, padx=(0, 5), pady=2)

        # File path (full, read-only, with tooltip)
        file_path_entry = ttk.Entry(
            file_frame, textvariable=self.file_path_var, state="readonly", width=28
        )
        file_path_entry.grid(
            row=1, column=1, sticky=tk.W + tk.E, padx=(0, 5), pady=(0, 2)
        )

        # Browse button
        browse_button = ttk.Button(
            file_frame, text="Browse...", command=self.browse_file
        )
        browse_button.grid(
            row=0, column=2, rowspan=2, sticky=tk.NS + tk.E, padx=(5, 0), pady=2
        )

        # Configure grid weights for responsive resizing
        file_frame.columnconfigure(1, weight=1)

    def start_chat(self):
        """Initialize the chat conversation"""
        welcome_message = """🤖 Hello! I'm your Car Rental Assistant. I can help you find the best car for your trip.

To get started, I need to know a few details about your journey:

1. How far will you be traveling? (in kilometers)
2. How long will you need the car? (in hours)

Just tell me the distance first, and I'll guide you through the rest!"""

        self.add_bot_message(welcome_message)
        self.chat_state["waiting_for_distance"] = True
        self.chat_state["conversation_started"] = True

    def add_bot_message(self, message):
        """Add a bot message to the chat display and update conversation history"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "🤖 Assistant: ", "bot_name")
        self.chat_display.insert(tk.END, message + "\n\n", "bot_message")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
        
        # Add to conversation history
        self.chat_state["conversation_history"].append({
            "type": "bot",
            "message": message,
            "timestamp": self.get_current_time()
        })
    
    def get_current_time(self):
        """Get current timestamp for conversation history"""
        import datetime
        return datetime.datetime.now().strftime("%H:%M:%S")

    def add_error_message(self, error_message):
        """Add an error message to the error display area"""
        if hasattr(self, "error_display"):
            self.error_display.config(state=tk.NORMAL)
            timestamp = datetime.now().strftime("%H:%M:%S")
            self.error_display.insert(
                tk.END, f"[{timestamp}] ❌ {error_message}\n", "error"
            )
            self.error_display.config(state=tk.DISABLED)
            # Auto-scroll to the bottom
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
            timestamp = datetime.now().strftime("%H:%M:%S")
            # Temporarily change color to green for success message
            original_fg = self.error_display.cget("fg")
            self.error_display.config(fg="#28a745")
            self.error_display.insert(
                tk.END, f"[{timestamp}] ✅ {success_message}\n", "success"
            )
            self.error_display.config(fg=original_fg)
            self.error_display.config(state=tk.DISABLED)
            # Auto-scroll to the bottom
            self.error_display.see(tk.END)
        self.chat_display.see(tk.END)

    def add_user_message(self, message):
        """Add a user message to the chat display and update conversation history"""
        self.chat_display.config(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "👤 You: ", "user_name")
        self.chat_display.insert(tk.END, message + "\n\n", "user_message")
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
        
        # Add to conversation history
        self.chat_state["conversation_history"].append({
            "type": "user",
            "message": message,
            "timestamp": self.get_current_time()
        })

    def send_message(self):
        """Handle sending a message in the chat"""
        message = self.message_var.get().strip()
        if not message:
            return

        # Add user message to chat
        self.add_user_message(message)

        # Clear input field
        self.message_var.set("")

        # Process the message based on chat state
        self.process_message(message)

    def process_message(self, message):
        """Process user message based on current chat state and input"""
        msg_lower = message.lower().strip()

        # Check for restart or reset commands first, regardless of state
        if any(word in msg_lower for word in ["restart", "new", "again", "reset"]):
            self.restart_conversation()
            return

        # Handle expected input states
        if self.chat_state.get("waiting_for_distance", False):
            self.handle_distance_input(message)
        elif self.chat_state.get("waiting_for_duration", False):
            self.handle_duration_input(message)
        else:
            # Handle context-aware responses and follow-up questions
            self.handle_contextual_response(message)

    def handle_distance_input(self, message):
        """Handle distance input from user with enhanced natural language processing"""
        try:
            # Extract number from message with better pattern matching
            import re
            
            # Look for various distance patterns
            distance_patterns = [
                r'(\d+(?:\.\d+)?)\s*(?:km|kilometers?|kms?)',  # "50 km", "25 kilometers"
                r'(\d+(?:\.\d+)?)\s*(?:miles?|mi)',  # "30 miles" (convert to km)
                r'(\d+(?:\.\d+)?)\s*(?:minutes?|mins?)',  # "45 minutes" (estimate distance)
                r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)',  # "2 hours" (estimate distance)
                r'(\d+(?:\.\d+)?)',  # Just numbers
            ]
            
            distance = None
            unit_type = "km"
            
            for pattern in distance_patterns:
                match = re.search(pattern, message.lower())
                if match:
                    value = float(match.group(1))
                    if 'mile' in pattern or 'mi' in pattern:
                        distance = value * 1.60934  # Convert miles to km
                        unit_type = "miles"
                    elif 'minute' in pattern or 'min' in pattern:
                        # Estimate: 1 minute ≈ 1 km in city driving
                        distance = value
                        unit_type = "minutes"
                    elif 'hour' in pattern or 'hr' in pattern:
                        # Estimate: 1 hour ≈ 30 km average
                        distance = value * 30
                        unit_type = "hours"
                    else:
                        distance = value
                    break
            
            if distance is not None and distance > 0:
                # Validate reasonable distance range
                if distance > 1000:
                    self.add_bot_message(
                        f"That's quite a long distance ({distance:.1f} km)! Are you sure? "
                        f"For very long trips, you might want to consider different transportation options. "
                        f"Please confirm or provide a different distance."
                    )
                    return
                elif distance < 1:
                    self.add_bot_message(
                        "That's a very short distance! For trips under 1 km, walking or cycling might be more practical. "
                        "Please provide a distance of at least 1 km, or let me know if you meant something else."
                    )
                    return
                
                self.chat_state["distance"] = distance
                self.chat_state["waiting_for_distance"] = False
                self.chat_state["waiting_for_duration"] = True
                
                # Provide context-aware response with helpful tips
                if unit_type != "km":
                    response = f"Got it! {distance:.1f} km (from {value} {unit_type}). Now, how many hours will you need the car for?"
                else:
                    response = f"Perfect! {distance} km. Now, how many hours will you need the car for?"
                
                # Add helpful context based on distance
                if distance <= 10:
                    response += "\n💡 **Short trip tip:** Perfect for local errands and quick outings!"
                elif distance <= 50:
                    response += "\n🚗 **Medium trip tip:** Great for shopping, appointments, or city exploration!"
                else:
                    response += "\n🌅 **Long trip tip:** Ideal for day trips, sightseeing, or visiting nearby areas!"
                
                self.add_bot_message(response)
            else:
                self.add_bot_message(
                    "I couldn't find a valid distance in your message. Please tell me the distance in kilometers (e.g., '50 km', '25 miles', or just '50')."
                )
        except ValueError:
            self.add_bot_message("Please enter a valid number for the distance.")

    def handle_duration_input(self, message):
        """Handle duration input from user with enhanced natural language processing"""
        try:
            # Extract number from message with better pattern matching
            import re
            
            # Look for various duration patterns (order matters - most specific first)
            duration_patterns = [
                r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?|h)',  # "2 hours", "1.5 hrs"
                r'(\d+(?:\.\d+)?)\s*(?:minutes?|mins?|m)',  # "90 minutes" (convert to hours)
                r'(\d+(?:\.\d+)?)\s*(?:days?|d)',  # "2 days" (convert to hours)
                r'^(\d+(?:\.\d+)?)\s*$',  # Just numbers (only if no unit specified)
            ]
            
            duration = None
            unit_type = "hours"
            
            for i, pattern in enumerate(duration_patterns):
                match = re.search(pattern, message.lower())
                if match:
                    value = float(match.group(1))
                    if i == 1:  # minutes pattern
                        duration = value / 60  # Convert minutes to hours
                        unit_type = "minutes"
                    elif i == 2:  # days pattern
                        duration = value * 24  # Convert days to hours
                        unit_type = "days"
                    else:  # hours pattern or just numbers
                        duration = value
                        unit_type = "hours"
                    break
            
            if duration is not None and duration > 0:
                # Validate reasonable duration range
                if duration > 72:  # More than 3 days
                    self.add_bot_message(
                        f"That's a very long rental period ({duration:.1f} hours = {duration/24:.1f} days)! "
                        f"For rentals longer than 3 days, you might want to consider weekly rates or different providers. "
                        f"Please confirm this duration or provide a different one."
                    )
                    return
                elif duration < 0.5:  # Less than 30 minutes
                    self.add_bot_message(
                        "That's a very short rental period! Most car rental services have minimum rental periods. "
                        "Please provide a duration of at least 30 minutes (0.5 hours), or let me know if you meant something else."
                    )
                    return
                
                self.chat_state["duration"] = duration
                self.chat_state["waiting_for_duration"] = False
                
                # Provide context-aware response before getting recommendations
                if unit_type != "hours":
                    response = f"Perfect! {duration:.1f} hours (from {value} {unit_type}). Let me find the best car rental options for you..."
                else:
                    response = f"Great! {duration} hours. Let me find the best car rental options for you..."
                
                # Add helpful context based on duration
                if duration <= 2:
                    response += "\n⏰ **Quick rental tip:** Perfect for short errands and quick trips!"
                elif duration <= 8:
                    response += "\n🚗 **Half-day rental tip:** Great for shopping, appointments, or leisure activities!"
                else:
                    response += "\n🌅 **Full-day rental tip:** Ideal for sightseeing, long-distance travel, or multiple stops!"
                
                self.add_bot_message(response)
                
                # Get recommendations
                self.get_chat_recommendations()
            else:
                self.add_bot_message(
                    "I couldn't find a valid duration in your message. Please tell me the duration in hours (e.g., '2 hours', '90 minutes', or just '2')."
                )
        except ValueError:
            self.add_bot_message("Please enter a valid number for the duration.")

    def handle_contextual_response(self, message):
        """Handle contextual responses and follow-up questions based on conversation history"""
        message_lower = message.lower().strip()
        
        # Handle restart command
        if any(word in message_lower for word in ['restart', 'new', 'again', 'reset']):
            self.restart_conversation()
            return
        
        # Handle questions about recommendations
        if self.chat_state.get("last_recommendations"):
            if any(word in message_lower for word in ['cheaper', 'cheapest', 'budget', 'cost', 'price']):
                self.handle_cost_question()
                return
            elif any(word in message_lower for word in ['best', 'recommend', 'suggest', 'which']):
                self.handle_recommendation_question()
                return
            elif any(word in message_lower for word in ['details', 'more', 'info', 'information']):
                self.handle_details_question()
                return
            elif any(word in message_lower for word in ['compare', 'difference', 'vs', 'versus']):
                self.handle_comparison_question()
                return
        
        # Handle general help
        if any(word in message_lower for word in ['help', 'how', 'what', 'can you']):
            self.handle_help_request()
            return
        
        # Handle trip modification
        if any(word in message_lower for word in ['change', 'modify', 'update', 'different']):
            self.handle_trip_modification()
            return
        
        # Default contextual response
        self.add_bot_message(
            "I'm here to help! You can ask me about:\n"
            "• 'restart' - Get recommendations for a new trip\n"
            "• 'cheaper options' - Find budget-friendly alternatives\n"
            "• 'more details' - Get additional information about recommendations\n"
            "• 'compare' - Compare different options\n"
            "• 'help' - Learn more about what I can do\n\n"
            "Or just tell me your trip details (distance and duration) to get started!"
        )

    def handle_cost_question(self):
        """Handle questions about cost and budget options"""
        if not self.chat_state.get("last_recommendations"):
            self.add_bot_message("I don't have any recent recommendations to compare. Please get some recommendations first!")
            return
        
        recommendations = self.chat_state["last_recommendations"]
        cheapest = min(recommendations, key=lambda x: x.get("total_cost", float('inf')))
        
        self.add_bot_message(
            f"💰 **Budget Option:**\n"
            f"🚗 **{cheapest.get('model', 'Unknown')}** ({cheapest.get('provider', 'Unknown')})\n"
            f"💵 **Cost:** ${cheapest.get('total_cost', 0):.2f}\n"
            f"💡 **Why it's budget-friendly:** {cheapest.get('reasoning', 'Lowest cost option available')}\n\n"
            f"💬 Want to see all budget options? Check the recommendations panel on the right!"
        )

    def handle_recommendation_question(self):
        """Handle questions about best recommendations"""
        if not self.chat_state.get("last_recommendations"):
            self.add_bot_message("I don't have any recent recommendations. Please get some recommendations first!")
            return
        
        best = self.chat_state["last_recommendations"][0]
        self.add_bot_message(
            f"⭐ **My Top Recommendation:**\n"
            f"🚗 **{best.get('model', 'Unknown')}** ({best.get('provider', 'Unknown')})\n"
            f"💰 **Cost:** ${best.get('total_cost', 0):.2f}\n"
            f"🔬 **Method:** {best.get('method', 'Standard')}\n"
            f"💡 **Why this is best:** {best.get('reasoning', 'Best overall value')}\n\n"
            f"📋 Check the recommendations panel for the complete list!"
        )

    def handle_details_question(self):
        """Handle requests for more detailed information"""
        if not self.chat_state.get("last_recommendations"):
            self.add_bot_message("I don't have any recent recommendations. Please get some recommendations first!")
            return
        
        recommendations = self.chat_state["last_recommendations"]
        trip_context = self.chat_state.get("trip_context", {})
        
        self.add_bot_message(
            f"📊 **Detailed Analysis for {trip_context.get('distance', 'N/A')} km, {trip_context.get('duration', 'N/A')} hours:**\n\n"
            f"🔍 **Analysis Methods Used:**\n"
            f"• Historical data analysis\n"
            f"• Cost optimization algorithms\n"
            f"• Provider reliability assessment\n\n"
            f"📈 **Key Metrics:**\n"
            f"• Total options found: {len(recommendations)}\n"
            f"• Price range: ${min(r.get('total_cost', 0) for r in recommendations):.2f} - ${max(r.get('total_cost', 0) for r in recommendations):.2f}\n"
            f"• Providers analyzed: {len(set(r.get('provider', '') for r in recommendations))}\n\n"
            f"💡 **Pro Tip:** The recommendations are ranked by best value (cost vs. quality balance)!"
        )

    def handle_comparison_question(self):
        """Handle requests to compare different options"""
        if not self.chat_state.get("last_recommendations"):
            self.add_bot_message("I don't have any recent recommendations. Please get some recommendations first!")
            return
        
        recommendations = self.chat_state["last_recommendations"][:3]  # Top 3 for comparison
        
        comparison_text = "🔄 **Top 3 Options Comparison:**\n\n"
        for i, rec in enumerate(recommendations, 1):
            comparison_text += f"**{i}. {rec.get('model', 'Unknown')} ({rec.get('provider', 'Unknown')})**\n"
            comparison_text += f"   💰 ${rec.get('total_cost', 0):.2f} | 🔬 {rec.get('method', 'Standard')}\n"
            if rec.get('reasoning'):
                reasoning = rec.get('reasoning', '')[:100]
                comparison_text += f"   💡 {reasoning}{'...' if len(rec.get('reasoning', '')) > 100 else ''}\n"
            comparison_text += "\n"
        
        comparison_text += "📋 **Full comparison available in the recommendations panel on the right!**"
        self.add_bot_message(comparison_text)

    def handle_help_request(self):
        """Handle help requests"""
        self.add_bot_message(
            "🤖 **Car Rental Assistant Help**\n\n"
            "**What I can do:**\n"
            "• Find the best car rental options for your trip\n"
            "• Compare costs and features across different providers\n"
            "• Provide detailed analysis and recommendations\n"
            "• Answer questions about your options\n\n"
            "**How to use me:**\n"
            "1. Tell me your trip distance (e.g., '50 km' or '25 miles')\n"
            "2. Tell me how long you need the car (e.g., '2 hours' or '90 minutes')\n"
            "3. I'll find the best options for you!\n\n"
            "**Commands:**\n"
            "• 'restart' - Start a new recommendation\n"
            "• 'cheaper' - Find budget options\n"
            "• 'compare' - Compare top options\n"
            "• 'details' - Get more information\n\n"
            "💬 Just start by telling me your trip details!"
        )

    def handle_trip_modification(self):
        """Handle requests to modify trip details"""
        self.add_bot_message(
            "🔄 **Modify Your Trip**\n\n"
            "I can help you adjust your trip details! You can:\n"
            "• Change the distance (e.g., 'change to 60 km')\n"
            "• Change the duration (e.g., 'make it 3 hours')\n"
            "• Or say 'restart' to begin completely fresh\n\n"
            "What would you like to change?"
        )

    def get_chat_recommendations(self):
        """Get recommendations based on chat inputs"""
        distance = self.chat_state["distance"]
        duration = self.chat_state["duration"]

        if self.df is None or self.df.empty:
            self.add_bot_message(
                "❌ I need rental data to provide recommendations. Please load a data file first using the 'Browse...' button."
            )
            return

        try:
            is_weekend = self.is_weekend_var.get()
            selected_cat = self.car_cat_var.get()
            use_ml = self.use_ml_var.get() if hasattr(self, "use_ml_var") else True
            use_ollama = (
                self.use_ollama_var.get() if hasattr(self, "use_ollama_var") else False
            )
            ollama_model = (
                self.ollama_model_var.get()
                if hasattr(self, "use_ollama_var")
                else "llama3.2:3b"
            )

            # Get enhanced recommendations
            if self.cost_analysis is None:
                self.cost_analysis = create_complete_cost_analysis(self.df)

            try:
                recommendations = get_ollama_enhanced_recommendations(
                    distance,
                    duration,
                    self.df,
                    self.cost_analysis,
                    is_weekend,
                    top_n=10,
                    use_ollama=use_ollama,
                    ollama_model=ollama_model,
                    use_ml=use_ml,
                )
            except Exception as e:
                error_msg = f"Ollama LLM is not available: {str(e)}"
                self.add_error_message(error_msg)
                if use_ollama:
                    self.add_bot_message(
                        f"⚠️ {error_msg}\nContinuing with other recommendation methods."
                    )
                    recommendations = get_ollama_enhanced_recommendations(
                        distance,
                        duration,
                        self.df,
                        self.cost_analysis,
                        is_weekend,
                        top_n=10,
                        use_ollama=False,
                        ollama_model=ollama_model,
                        use_ml=use_ml,
                    )
                else:
                    raise e

            # Filter recommendations by selected category if not "All"
            if selected_cat != "All":
                recommendations = [
                    rec for rec in recommendations if rec["provider"] == selected_cat
                ]

            # Display recommendations in chat
            self.display_chat_recommendations(recommendations, distance, duration)

            # Update the results treeview
            self.update_results_tree(recommendations)

            # Show comparison chart
            self.show_recommendation_chart(recommendations)

            # Show success message
            success_msg = f"Generated {len(recommendations)} recommendations for {distance} km, {duration} hours"
            self.add_success_message(success_msg)

        except Exception as e:
            error_msg = f"An error occurred while getting recommendations: {str(e)}"
            self.add_error_message(error_msg)
            self.add_bot_message(f"❌ {error_msg}")

    def display_chat_recommendations(self, recommendations, distance, duration):
        """Display recommendations in the chat interface with enhanced formatting and clarity."""
        if not recommendations:
            self.add_bot_message(
                "❌ Sorry, I couldn't find any suitable car rental options for your trip details."
            )
            return

        best_rec = recommendations[0]
        model = best_rec.get("model", "Unknown Model")
        provider = best_rec.get("provider", "Unknown Provider")
        total_cost = best_rec.get("total_cost", 0.0)
        method = best_rec.get("method", "Standard")
        confidence = best_rec.get("confidence", None)
        reasoning = best_rec.get("reasoning", "")

        # Calculate cost per km and per hour for better context
        cost_per_km = total_cost / distance if distance > 0 else 0
        cost_per_hour = total_cost / duration if duration > 0 else 0

        # Create more informative summary
        summary_lines = [
            f"🎯 **Best Recommendation for {distance} km, {duration} hours:**\n",
            f"🚗 **{model}** ({provider})",
            f"💰 **Total Cost:** ${total_cost:.2f}",
            f"📊 **Cost Breakdown:** ${cost_per_km:.2f}/km, ${cost_per_hour:.2f}/hour",
            f"🔬 **Analysis Method:** {method}",
        ]

        if confidence is not None:
            confidence_text = f"{confidence:.1%}"
            if confidence >= 0.8:
                confidence_emoji = "🟢"
            elif confidence >= 0.6:
                confidence_emoji = "🟡"
            else:
                confidence_emoji = "🔴"
            summary_lines.append(f"{confidence_emoji} **Confidence:** {confidence_text}")

        if reasoning:
            display_reasoning = reasoning
            if len(display_reasoning) > 150:
                display_reasoning = display_reasoning[:150] + "..."
            summary_lines.append(f"💡 **Why this car:** {display_reasoning}")

        # Add helpful context based on trip characteristics
        if duration <= 2:
            summary_lines.append("⏰ **Quick trip tip:** Perfect for short errands or quick outings!")
        elif duration <= 6:
            summary_lines.append("🚗 **Half-day trip:** Great for shopping, appointments, or leisure activities!")
        else:
            summary_lines.append("🌅 **Full-day adventure:** Ideal for sightseeing, long-distance travel, or multiple stops!")

        # Add cost comparison context
        if total_cost < 25:
            summary_lines.append("💵 **Budget-friendly:** Excellent value for money!")
        elif total_cost < 40:
            summary_lines.append("⚖️ **Balanced option:** Good mix of cost and convenience!")
        else:
            summary_lines.append("⭐ **Premium choice:** Higher cost but maximum comfort and features!")

        summary_lines.append(
            f"\n📋 I found {len(recommendations)} total options. Check the recommendations panel on the right for the full list!"
        )
        summary_lines.append(
            "💬 You can say 'restart' to get recommendations for a different trip, or ask me anything else!"
        )

        summary = "\n".join(summary_lines)
        self.add_bot_message(summary)
        
        # Store recommendations for context
        self.chat_state["last_recommendations"] = recommendations
        self.chat_state["trip_context"] = {
            "distance": distance,
            "duration": duration,
            "timestamp": self.get_current_time()
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

        # Create grid for statistics
        self.stats_grid = ttk.Frame(self.stats_frame)
        self.stats_grid.pack(fill=tk.X, expand=True, padx=5, pady=5)

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
        if self.df is None or self.df.empty:
            messagebox.showwarning("No Data", "Please load rental data first")
            return

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

        if filtered_df.empty:
            messagebox.showinfo("No Data", "No data available for the selected period")
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
        """Add a statistic to the stats grid"""
        row = len(self.stats_labels) // 3
        col = len(self.stats_labels) % 3

        # Create a frame for this statistic
        frame = ttk.Frame(self.stats_grid)
        frame.grid(row=row, column=col, padx=10, pady=5, sticky=tk.W)

        # Add label and value
        label_widget = ttk.Label(frame, text=f"{label}:", font=("Segoe UI", 9))
        label_widget.pack(anchor=tk.W)

        value_widget = ttk.Label(frame, text=value, font=("Segoe UI", 10, "bold"))
        value_widget.pack(anchor=tk.W)

        # Store references to labels for later cleanup
        self.stats_labels.extend([frame, label_widget, value_widget])

    def export_analysis_results(self):
        """Export analysis results to CSV"""
        if self.df is None or self.df.empty:
            messagebox.showwarning("No Data", "No data to export")
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

        # Divider
        ttk.Separator(data_frame, orient="horizontal").grid(row=1, column=0, columnspan=4, sticky="ew", pady=(5, 5))

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

        # Save settings button
        save_button = ttk.Button(
            self.settings_tab, text="Save Settings", command=self.save_settings
        )
        save_button.pack(anchor="w", padx=10, pady=20)

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
            "Excel Total",
            "Excel Cost/KM",
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
            "Excel Total": 80,
            "Excel Cost/KM": 90,
            "Fuel Used": 70,
            "Consumption": 80,
        }

        for col in columns:
            self.records_tree.heading(col, text=col)
            self.records_tree.column(
                col, width=column_widths.get(col, 100), anchor="center"
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

        # Enhanced Record Form on the right
        form_frame = ttk.LabelFrame(right_frame, text="📝 Record Details")
        form_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Create scrollable canvas for the form with proper configuration
        canvas = tk.Canvas(
            form_frame, height=600, width=1000
        )  # Increased width to prevent text cutoff
        scrollbar = ttk.Scrollbar(form_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)

        # Configure the scrollable frame to update canvas scroll region
        def configure_scroll_region(event):
            canvas.configure(scrollregion=canvas.bbox("all"))

        scrollable_frame.bind("<Configure>", configure_scroll_region)

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=980)
        canvas.configure(yscrollcommand=scrollbar.set)

        # Bind mouse wheel to canvas scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Create two frames for better organization
        left_form_frame = ttk.Frame(scrollable_frame)
        left_form_frame.pack(side="left", fill="both", expand=True, padx=10, pady=5)

        right_form_frame = ttk.Frame(scrollable_frame)
        right_form_frame.pack(side="right", fill="both", expand=True, padx=10, pady=5)

        # Left form fields - Basic Information
        basic_info_frame = ttk.LabelFrame(left_form_frame, text="📋 Basic Information")
        basic_info_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Date and Car Model with better layout
        ttk.Label(basic_info_frame, text="📅 Date (DD/MM/YYYY):").grid(
            row=0, column=0, padx=5, pady=5, sticky="w"
        )
        date_entry = ttk.Entry(
            basic_info_frame, textvariable=self.record_date_var, width=15
        )
        date_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        # Add today's date button
        ttk.Button(
            basic_info_frame, text="Today", command=self.set_today_date, width=8
        ).grid(row=0, column=2, padx=2, pady=5, sticky="w")

        ttk.Label(basic_info_frame, text="🚗 Car Model:").grid(
            row=1, column=0, padx=5, pady=5, sticky="w"
        )
        ttk.Entry(
            basic_info_frame, textvariable=self.record_car_model_var, width=25
        ).grid(row=1, column=1, columnspan=2, padx=5, pady=5, sticky="w")

        # Provider and Weekend/Weekday
        ttk.Label(basic_info_frame, text="🏢 Provider:").grid(
            row=2, column=0, padx=5, pady=5, sticky="w"
        )
        provider_combo = ttk.Combobox(
            basic_info_frame,
            textvariable=self.record_provider_var,
            values=["Getgo", "Car Club", "Econ", "Stand", "Getgo(EV)"],
            width=15,
        )
        provider_combo.grid(row=2, column=1, padx=5, pady=5, sticky="w")
        provider_combo.bind("<<ComboboxSelected>>", self.on_provider_changed)

        ttk.Label(basic_info_frame, text="📅 Day Type:").grid(
            row=3, column=0, padx=5, pady=5, sticky="w"
        )
        ttk.Combobox(
            basic_info_frame,
            textvariable=self.record_weekend_var,
            values=["weekday", "weekend"],
            width=15,
        ).grid(row=3, column=1, padx=5, pady=5, sticky="w")

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

        # Auto-calculate total cost button
        ttk.Button(
            cost_frame,
            text="Auto-calc Total",
            command=self.auto_calculate_total_cost,
            width=12,
        ).grid(row=3, column=0, columnspan=4, padx=5, pady=5, sticky="ew")

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

        ttk.Button(
            primary_buttons,
            text="🆕 Add New Record",
            command=self.add_record,
            style="Accent.TButton",
        ).pack(side="left", padx=5, fill="x", expand=True)
        ttk.Button(
            primary_buttons,
            text="💾 Update Record",
            command=self.update_record,
            style="Accent.TButton",
        ).pack(side="left", padx=5, fill="x", expand=True)

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

        # Pack the canvas and scrollbar with proper layout
        canvas.pack(side="left", fill="both", expand=True, padx=(0, 2))
        scrollbar.pack(side="right", fill="y", padx=(2, 0))

        # Update scroll region after all widgets are added
        def update_scroll_region():
            try:
                canvas.update_idletasks()
                bbox = canvas.bbox("all")
                if bbox:
                    canvas.configure(scrollregion=bbox)
                    # Ensure the scrollable frame width matches canvas
                    canvas_window = canvas.find_withtag("all")
                    if canvas_window:
                        canvas.itemconfig(canvas_window[0], width=980)
            except Exception as e:
                print(f"Error updating scroll region: {e}")

        # Schedule the update after the GUI is fully loaded
        self.root.after(100, update_scroll_region)
        self.root.after(
            500, update_scroll_region
        )  # Second update to ensure proper sizing

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

                # Fuel cost
                fuel_cost = fuel_pumped * fuel_price * 0.91  # With discount

                total_cost = mileage_cost + duration_cost + fuel_cost

            self.record_total_cost_var.set(f"{total_cost:.2f}")
            messagebox.showinfo(
                "Auto-calculation", f"Total cost calculated: ${total_cost:.2f}"
            )

        except ValueError:
            messagebox.showerror("Error", "Invalid values for calculation.")

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

    def load_data_file(self, file_path):
        """Load and process data from file"""
        try:
            self.df = load_data(file_path)
            self.df = enhance_dataframe(self.df)
            self.cost_analysis = create_complete_cost_analysis(self.df)
            success_msg = f"Data loaded successfully from {os.path.basename(file_path)}"
            self.add_success_message(success_msg)
            messagebox.showinfo("Success", success_msg)

            # Remove message labels once data is loaded
            if hasattr(self, "message_label"):
                self.message_label.place_forget()
            if hasattr(self, "analysis_label"):
                self.analysis_label.place_forget()

            # Refresh records if tab exists
            if hasattr(self, "records_tree"):
                self.refresh_records()

        except Exception as e:
            error_msg = f"Failed to load data: {str(e)}"
            self.add_error_message(error_msg)
            messagebox.showerror("Error", error_msg)

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
            # Load the new file
            new_df = load_data(file_path)
            new_df = enhance_dataframe(new_df)

            if upload_mode == "Replace Current Data":
                # Replace current data
                self.df = new_df
                self.cost_analysis = create_complete_cost_analysis(self.df)

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
                    self.cost_analysis = create_complete_cost_analysis(self.df)
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
                    self.cost_analysis = create_complete_cost_analysis(self.df)

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
                    full_reasoning = f"AI-powered recommendation for {provider}: {display_reasoning[:-3]}...\n\nThis recommendation is based on your profile as a 24-year-old value-conscious driver who wants to maximize rental value for errands, leisure, and sightseeing. The AI analyzed your historical rental patterns and current trip requirements to provide this personalized suggestion."
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
This recommendation considers your profile as a 24-year-old value-conscious driver with 3 years of experience who wants to maximize rental value for errands, leisure, and sightseeing.

Tip: Ollama recommendations are personalized based on your user profile and historical rental patterns to help you make the most cost-effective decision.
        """

        # Show in a new window
        detail_window = tk.Toplevel(self.root)
        detail_window.title(f"Recommendation Details - {provider}")
        detail_window.geometry("500x400")
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
        # Clear previous chart
        self.ax.clear()

        if not recommendations:
            return

        # Extract data for chart
        providers = [rec["provider"] for rec in recommendations]
        models = [rec["model"] for rec in recommendations]
        costs = [rec["total_cost"] for rec in recommendations]
        methods = [rec.get("method", "Standard") for rec in recommendations]

        # Create unique labels combining provider and model
        labels = [
            f"{p} - {m}" if m != "Average" else p for p, m in zip(providers, models)
        ]

        # Limit to top 5 for readability
        if len(labels) > 5:
            labels = labels[:5]
            costs = costs[:5]
            methods = methods[:5]

        # Create color map based on method
        colors = []
        for method in methods:
            if method == "Ollama Analysis":
                colors.append("#28a745")  # Green for Ollama
            elif method == "ML Prediction":
                colors.append("#4a90e2")  # Blue for ML
            elif method == "Historical Analysis":
                colors.append("#f39c12")  # Orange for historical
            else:
                colors.append("#95a5a6")  # Gray for default

        # Create horizontal bar chart
        bars = self.ax.barh(labels, costs, color=colors)

        # Add labels
        for bar in bars:
            width = bar.get_width()
            self.ax.text(
                width + 1,
                bar.get_y() + bar.get_height() / 2,
                f"{width:.2f}",
                ha="left",
                va="center",
                fontsize=9,
            )

        # Set title and labels
        self.ax.set_title("Cost Comparison by Method", fontsize=12, pad=10)
        self.ax.set_xlabel("Estimated Cost ($)", fontsize=10)

        # Add legend for methods
        from matplotlib.patches import Patch

        legend_elements = [
            Patch(facecolor="#28a745", label="Ollama Analysis"),
            Patch(facecolor="#4a90e2", label="ML Prediction"),
            Patch(facecolor="#f39c12", label="Historical Analysis"),
            Patch(facecolor="#95a5a6", label="Default Pricing"),
        ]
        self.ax.legend(handles=legend_elements, loc="upper right")

        # Remove top and right spines
        self.ax.spines["right"].set_visible(False)
        self.ax.spines["top"].set_visible(False)

        # Add grid lines
        self.ax.grid(axis="x", linestyle="--", alpha=0.7)

        # Adjust layout and redraw
        plt.tight_layout()
        self.canvas.draw()

    def save_settings(self):
        """Save current settings to a JSON file"""
        settings_file = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "settings.json"
        )
        try:
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
            }

    def refresh_records(self):
        """Refresh the records list in the treeview"""
        if self.df is None:
            messagebox.showwarning("Warning", "No data loaded")
            return

        # Clear existing records
        for item in self.records_tree.get_children():
            self.records_tree.delete(item)

        # Add records from dataframe
        for idx, row in self.df.iterrows():
            try:
                # Format date for display
                date_str = (
                    row["Date"].strftime("%d/%m/%Y") if pd.notna(row["Date"]) else ""
                )

                # Get Excel calculated values if available
                excel_total = row.get("Excel_Calculated_total", 0)
                excel_cost_per_km = row.get("Excel_Calculated_cost_per_km", 0)

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
                        f"${excel_total:.2f}" if excel_total else "",
                        f"${excel_cost_per_km:.2f}" if excel_cost_per_km else "",
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

        # Populate the form fields
        self.record_date_var.set(
            row["Date"].strftime("%d/%m/%Y") if pd.notna(row["Date"]) else ""
        )
        self.record_car_model_var.set(
            row["Car model"] if pd.notna(row["Car model"]) else ""
        )
        self.record_provider_var.set(row["Car Cat"] if pd.notna(row["Car Cat"]) else "")
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

        # Calculate Excel formulas for the selected record
        self.calculate_excel_formulas_for_current_record()

    def clear_record_form(self):
        """Clear all form fields and prepare for new record entry"""
        self.current_record_index = None

        # Clear all form fields
        self.record_date_var.set("")
        self.record_car_model_var.set("")
        self.record_provider_var.set("")
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


        # Clear fuel economy comparison
        if hasattr(self, "fuel_economy_comparison_text"):
            self.fuel_economy_comparison_text.config(state="normal")
            self.fuel_economy_comparison_text.delete(1.0, tk.END)
            self.fuel_economy_comparison_text.config(state="disabled")

        # Hide EV frame when clearing form
        if hasattr(self, "ev_frame"):
            self.ev_frame.pack_forget()

        # Update status bar
        self.status_var.set("Form cleared - Ready for new record entry")

        # Focus on the first field for better UX
        self.root.focus_set()

    def get_form_data(self):
        """Get data from the form fields and validate it"""
        try:
            # Parse date
            date_str = self.record_date_var.get()
            try:
                date = pd.to_datetime(date_str, format="%d/%m/%Y")
            except:
                messagebox.showerror(
                    "Error", "Invalid date format. Please use DD/MM/YYYY."
                )
                return None

            # Get other field values with validation
            car_model = self.record_car_model_var.get()
            if not car_model:
                messagebox.showerror("Error", "Car model is required.")
                return None

            provider = self.record_provider_var.get()
            if not provider:
                messagebox.showerror("Error", "Provider is required.")
                return None

            # Parse numeric fields
            try:
                distance = (
                    float(self.record_distance_var.get())
                    if self.record_distance_var.get()
                    else None
                )
                rental_hour = (
                    float(self.record_hours_var.get())
                    if self.record_hours_var.get()
                    else None
                )
                fuel_pumped = (
                    float(self.record_fuel_pumped_var.get())
                    if self.record_fuel_pumped_var.get()
                    else None
                )
                fuel_usage = (
                    float(self.record_fuel_usage_var.get())
                    if self.record_fuel_usage_var.get()
                    else None
                )
                total = (
                    float(self.record_total_cost_var.get())
                    if self.record_total_cost_var.get()
                    else None
                )
                pumped_cost = (
                    float(self.record_pumped_cost_var.get())
                    if self.record_pumped_cost_var.get()
                    else None
                )
                cost_per_km = (
                    float(self.record_cost_per_km_var.get())
                    if self.record_cost_per_km_var.get()
                    else None
                )
                duration_cost = (
                    float(self.record_duration_cost_var.get())
                    if self.record_duration_cost_var.get()
                    else None
                )
                consumption = (
                    float(self.record_consumption_var.get())
                    if self.record_consumption_var.get()
                    else None
                )
                fuel_savings = (
                    float(self.record_fuel_savings_var.get())
                    if self.record_fuel_savings_var.get()
                    else None
                )
                cost_per_hr = (
                    float(self.record_cost_per_hr_var.get())
                    if self.record_cost_per_hr_var.get()
                    else None
                )

                # Parse EV-specific fields
                kwh_used = (
                    float(self.record_kwh_used_var.get())
                    if self.record_kwh_used_var.get()
                    else None
                )
                electricity_cost = (
                    float(self.record_electricity_cost_var.get())
                    if self.record_electricity_cost_var.get()
                    else None
                )
            except ValueError:
                messagebox.showerror(
                    "Error", "Invalid numeric value in one or more fields."
                )
                return None

            weekend = self.record_weekend_var.get()

            # Create record dict
            record = {
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

            return record
        except Exception as e:
            messagebox.showerror("Error", f"Error validating form data: {str(e)}")
            return None

    def add_record(self):
        """Add a new record from form data with enhanced validation and feedback"""
        if self.df is None:
            messagebox.showerror(
                "Error", "No data loaded. Please load a data file first."
            )
            return

        # Validate required fields before getting form data
        if not self.record_distance_var.get() or not self.record_hours_var.get():
            messagebox.showerror(
                "Error", "Distance and Rental Hours are required fields."
            )
            return

        record = self.get_form_data()
        if record is None:
            return

        try:
            # Add record to dataframe
            self.df = pd.concat([self.df, pd.DataFrame([record])], ignore_index=True)

            # Refresh the cost analysis
            self.cost_analysis = create_complete_cost_analysis(self.df)

            # Refresh the records list
            self.refresh_records()

            # Clear the form
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
        if self.df is None:
            messagebox.showerror("Error", "No data loaded")
            return

        if self.current_record_index is None:
            messagebox.showerror("Error", "No record selected")
            return

        record = self.get_form_data()
        if record is None:
            return

        # Update record in dataframe
        for key, value in record.items():
            if key in self.df.columns:
                self.df.at[self.current_record_index, key] = value

        # Refresh the cost analysis
        self.cost_analysis = create_complete_cost_analysis(self.df)

        # Refresh the records list
        self.refresh_records()

        # Show success message
        messagebox.showinfo("Success", "Record updated successfully")

        # Save the changes
        self.save_data()
        self.auto_update_fields()

    def delete_record(self):
        """Delete the selected record"""
        if self.df is None:
            messagebox.showerror("Error", "No data loaded")
            return

        selected_items = self.records_tree.selection()
        if not selected_items:
            messagebox.showerror("Error", "No record selected")
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
        self.cost_analysis = create_complete_cost_analysis(self.df)

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
        if self.df is None or self.df.empty:
            messagebox.showwarning("No Data", "No records to export")
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
        if self.df is None:
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
                    ),
                )

        # Update status
        match_count = len(self.records_tree.get_children())
        self.status_var.set(f"Found {match_count} matching records for '{search_text}'")

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
        budget_entry = ttk.Entry(budget_input_frame, textvariable=self.monthly_budget_var, width=15)
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
            ("Confidence", "confidence")
        ]

        for i, (label_text, key) in enumerate(status_fields):
            ttk.Label(status_frame, text=f"{label_text}:").grid(
                row=i, column=0, padx=5, pady=2, sticky="w"
            )
            label = ttk.Label(status_frame, text="--", font=("Arial", 9, "bold"))
            label.grid(row=i, column=1, padx=5, pady=2, sticky="w")
            self.budget_status_labels[key] = label

        # Recommendations Frame
        recommendations_frame = ttk.LabelFrame(left_frame, text="💡 Smart Recommendations")
        recommendations_frame.pack(fill="both", expand=True, padx=5, pady=5)

        # Create text widget for recommendations
        self.recommendations_text = tk.Text(recommendations_frame, wrap=tk.WORD, height=12, width=45)
        recommendations_scroll = ttk.Scrollbar(
            recommendations_frame, orient="vertical", command=self.recommendations_text.yview
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
            ("Trend", "trend")
        ]

        for i, (label_text, key) in enumerate(summary_fields):
            ttk.Label(summary_frame, text=f"{label_text}:").grid(
                row=i//2, column=(i%2)*2, padx=5, pady=2, sticky="w"
            )
            label = ttk.Label(summary_frame, text="--", font=("Arial", 9))
            label.grid(row=i//2, column=(i%2)*2+1, padx=5, pady=2, sticky="w")
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
                "Historical vs Predicted"
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
        budget_chart_combo.bind("<<ComboboxSelected>>", self.on_budget_chart_type_changed)

        # Create matplotlib figure for budget charts
        self.budget_fig, self.budget_ax = plt.subplots(figsize=(12, 8))
        self.budget_canvas = FigureCanvasTkAgg(self.budget_fig, charts_frame)
        self.budget_canvas.get_tk_widget().pack(fill="both", expand=True)

        # Add navigation toolbar
        self.budget_toolbar = NavigationToolbar2Tk(self.budget_canvas, charts_frame)
        self.budget_toolbar.update()
        self.budget_toolbar.pack(fill="x")

        # Initialize prediction data
        self.budget_prediction_data = None
        self.ml_model = None

    def generate_budget_prediction(self):
        """Generate ML-based budget prediction using historical data"""
        if self.df is None or self.df.empty:
            messagebox.showwarning("No Data", "Please load rental data first to generate predictions")
            return

        try:
            # Get user inputs
            monthly_budget = float(self.monthly_budget_var.get())
            prediction_period = self.prediction_period_var.get()
            confidence_level = self.confidence_level_var.get()

            # Generate ML prediction
            prediction_result = self.create_ml_budget_prediction(monthly_budget, prediction_period, confidence_level)
            
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
            messagebox.showerror("Prediction Error", f"Failed to generate prediction: {str(e)}")

    def create_ml_budget_prediction(self, monthly_budget, prediction_period, confidence_level):
        """Create ML-based budget prediction using historical data"""
        try:
            # Prepare historical data for ML
            df_copy = self.df.copy()
            
            # Ensure Date column is datetime
            if not pd.api.types.is_datetime64_dtype(df_copy["Date"]):
                df_copy["Date"] = pd.to_datetime(df_copy["Date"])
            
            # Extract features for ML
            df_copy["Month"] = df_copy["Date"].dt.month
            df_copy["Year"] = df_copy["Date"].dt.year
            df_copy["Weekday"] = df_copy["Date"].dt.weekday
            df_copy["Is_Weekend"] = (df_copy["Weekday"] >= 5).astype(int)
            
            # Group by month-year for monthly spending analysis
            monthly_spending = df_copy.groupby(["Year", "Month"]).agg({
                "Total": "sum",
                "Distance (KM)": "sum",
                "Rental hour": "sum",
                "Is_Weekend": "mean"
            }).reset_index()
            
            # Calculate monthly statistics
            avg_monthly_spending = monthly_spending["Total"].mean()
            spending_std = monthly_spending["Total"].std()
            spending_trend = self.calculate_spending_trend(monthly_spending)
            
            # Apply confidence level adjustments
            confidence_multipliers = {
                "conservative": 1.2,  # 20% higher prediction
                "medium": 1.0,       # No adjustment
                "optimistic": 0.8    # 20% lower prediction
            }
            
            confidence_multiplier = confidence_multipliers.get(confidence_level, 1.0)
            
            # Generate prediction based on period
            if prediction_period == "next_month":
                predicted_spending = avg_monthly_spending * confidence_multiplier
                period_months = 1
            elif prediction_period == "next_3_months":
                predicted_spending = avg_monthly_spending * 3 * confidence_multiplier
                period_months = 3
            elif prediction_period == "next_6_months":
                predicted_spending = avg_monthly_spending * 6 * confidence_multiplier
                period_months = 6
            else:  # next_year
                predicted_spending = avg_monthly_spending * 12 * confidence_multiplier
                period_months = 12
            
            # Calculate risk assessment
            budget_remaining = monthly_budget * period_months - predicted_spending
            risk_level = self.assess_budget_risk(budget_remaining, predicted_spending, spending_std)
            
            # Calculate confidence score
            confidence_score = self.calculate_confidence_score(len(monthly_spending), spending_std)
            
            return {
                "monthly_budget": monthly_budget,
                "predicted_spending": predicted_spending,
                "budget_remaining": budget_remaining,
                "risk_level": risk_level,
                "confidence_score": confidence_score,
                "spending_trend": spending_trend,
                "avg_monthly_spending": avg_monthly_spending,
                "spending_std": spending_std,
                "data_points": len(monthly_spending),
                "period_months": period_months,
                "confidence_level": confidence_level,
                "monthly_data": monthly_spending
            }
            
        except Exception as e:
            raise Exception(f"ML prediction failed: {str(e)}")

    def calculate_spending_trend(self, monthly_data):
        """Calculate spending trend from historical data"""
        if len(monthly_data) < 2:
            return "insufficient_data"
        
        # Simple linear trend calculation
        x = np.arange(len(monthly_data))
        y = monthly_data["Total"].values
        
        # Calculate slope
        slope = np.polyfit(x, y, 1)[0]
        
        if slope > 50:
            return "increasing"
        elif slope < -50:
            return "decreasing"
        else:
            return "stable"

    def assess_budget_risk(self, budget_remaining, predicted_spending, spending_std):
        """Assess budget risk level"""
        if budget_remaining < 0:
            return "high"
        elif budget_remaining < spending_std:
            return "medium"
        else:
            return "low"

    def calculate_confidence_score(self, data_points, spending_std):
        """Calculate confidence score based on data quality"""
        # Base confidence on data points and variance
        base_confidence = min(0.95, 0.5 + (data_points * 0.05))
        
        # Adjust for variance (lower variance = higher confidence)
        variance_factor = max(0.7, 1.0 - (spending_std / 1000))
        
        return base_confidence * variance_factor

    def update_budget_status(self, prediction_result):
        """Update budget status labels"""
        self.budget_status_labels["budget_set"].config(text=f"${prediction_result['monthly_budget']:.2f}")
        self.budget_status_labels["predicted_spending"].config(text=f"${prediction_result['predicted_spending']:.2f}")
        
        # Color code budget remaining
        remaining = prediction_result['budget_remaining']
        if remaining < 0:
            color = "red"
            text = f"-${abs(remaining):.2f}"
        else:
            color = "green"
            text = f"${remaining:.2f}"
        
        self.budget_status_labels["budget_remaining"].config(text=text, foreground=color)
        
        # Risk level with color coding
        risk = prediction_result['risk_level']
        risk_colors = {"low": "green", "medium": "orange", "high": "red"}
        self.budget_status_labels["risk_level"].config(text=risk.title(), foreground=risk_colors.get(risk, "black"))
        
        # Confidence score
        confidence = prediction_result['confidence_score']
        self.budget_status_labels["confidence"].config(text=f"{confidence:.1%}")

    def update_prediction_summary(self, prediction_result):
        """Update prediction summary labels"""
        self.prediction_summary_labels["model_used"].config(text="Historical Analysis + ML")
        self.prediction_summary_labels["data_points"].config(text=str(prediction_result['data_points']))
        self.prediction_summary_labels["accuracy"].config(text=f"{prediction_result['confidence_score']:.1%}")
        
        trend = prediction_result['spending_trend']
        trend_emojis = {"increasing": "📈", "decreasing": "📉", "stable": "➡️", "insufficient_data": "❓"}
        self.prediction_summary_labels["trend"].config(text=f"{trend_emojis.get(trend, '❓')} {trend.title()}")

    def generate_smart_recommendations(self, prediction_result):
        """Generate smart recommendations using Ollama LLM based on prediction results"""
        import json
        import requests

        # Prepare context for LLM
        context = {
            "budget_remaining": prediction_result.get('budget_remaining'),
            "risk_level": prediction_result.get('risk_level'),
            "spending_trend": prediction_result.get('spending_trend'),
            "monthly_budget": prediction_result.get('monthly_budget'),
            "predicted_spending": prediction_result.get('predicted_spending'),
            "data_points": prediction_result.get('data_points'),
        }
        # Add provider info if available
        provider_info = ""
        if self.df is not None and not self.df.empty and "Car Cat" in self.df.columns and "Total" in self.df.columns:
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
        model_name = getattr(self, 'ollama_model_var', None)
        if model_name:
            model_name = model_name.get()
        else:
            model_name = "llama3.2:3b"  # Use faster model by default
            
        payload = {
            "model": model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": 0.3,  # Lower temperature for more consistent responses
                "top_p": 0.9,
                "max_tokens": 500,  # Limit response length for faster generation
            }
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
                    }
                }
                response = requests.post(ollama_url, json=simple_payload, timeout=5)
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
        budget_remaining = context.get('budget_remaining', 0)
        risk_level = context.get('risk_level', 'Medium')
        spending_trend = context.get('spending_trend', 'Stable')
        monthly_budget = context.get('monthly_budget', 0)
        predicted_spending = context.get('predicted_spending', 0)
        
        recommendations = []
        
        # Budget comparison analysis
        if predicted_spending < monthly_budget:
            surplus = monthly_budget - predicted_spending
            recommendations.append(f"✅ **Good News**: You're under budget by ${surplus:.2f} per month!")
        elif predicted_spending > monthly_budget:
            deficit = predicted_spending - monthly_budget
            recommendations.append(f"⚠️ **Over Budget**: You're spending ${deficit:.2f} more than planned per month")
        else:
            recommendations.append("⚖️ **On Target**: Your spending matches your budget exactly")
        
        # Risk-based recommendations
        if risk_level.lower() == 'high':
            recommendations.extend([
                "🚨 **High Risk Alert**: Consider reducing rental frequency",
                "💰 **Budget Tip**: Switch to cheaper providers (Getgo, Car Club)",
                "⏰ **Time Management**: Plan shorter trips to reduce costs",
                "📊 **Monitor**: Track spending weekly to avoid overspending"
            ])
        elif risk_level.lower() == 'medium':
            recommendations.extend([
                "⚖️ **Balanced Approach**: Mix expensive and budget rentals",
                "📅 **Planning**: Book rentals in advance for better rates",
                "🎯 **Optimize**: Choose providers based on trip distance"
            ])
        else:  # Low risk
            recommendations.extend([
                "✅ **Good Budget Control**: Continue current spending pattern",
                "🚗 **Upgrade Option**: Consider premium providers for special occasions",
                "📈 **Growth**: You can afford more frequent rentals"
            ])
        
        # Budget-specific recommendations
        if budget_remaining < 100:
            recommendations.extend([
                "💡 **Emergency Fund**: Keep some budget buffer for unexpected trips",
                "🔍 **Compare**: Always check multiple providers before booking"
            ])
        elif budget_remaining > 500:
            recommendations.extend([
                "🎉 **Flexible Budget**: You have room for spontaneous trips",
                "🌟 **Premium Options**: Consider luxury car rentals occasionally"
            ])
        
        # Spending trend recommendations
        if spending_trend.lower() == 'increasing':
            recommendations.append("📈 **Trend Alert**: Monitor if spending continues to rise")
        elif spending_trend.lower() == 'decreasing':
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
        self.budget_ax.text(0.5, 0.5, "Generate a budget prediction\nto see analysis charts", 
                           ha='center', va='center', transform=self.budget_ax.transAxes, 
                           fontsize=14, bbox=dict(boxstyle="round,pad=0.3", facecolor="lightgray"))
        self.budget_ax.set_xlim(0, 1)
        self.budget_ax.set_ylim(0, 1)
        self.budget_ax.axis('off')
        self.budget_fig.tight_layout()
        self.budget_canvas.draw()

    def plot_budget_vs_prediction(self):
        """Plot budget vs predicted spending comparison"""
        self.budget_ax.clear()
        
        data = self.budget_prediction_data
        categories = ['Budget', 'Predicted\nSpending']
        values = [data['monthly_budget'] * data['period_months'], data['predicted_spending']]
        colors = ['#2E8B57', '#FF6347']
        
        bars = self.budget_ax.bar(categories, values, color=colors, alpha=0.7)
        
        # Add value labels on bars
        for bar, value in zip(bars, values):
            height = bar.get_height()
            self.budget_ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                               f'${value:.2f}', ha='center', va='bottom', fontsize=10, fontweight='bold')
        
        # Add difference line
        diff = values[0] - values[1]
        if diff > 0:
            self.budget_ax.axhline(y=values[0], color='green', linestyle='--', alpha=0.5, label=f'Surplus: ${diff:.2f}')
        else:
            self.budget_ax.axhline(y=values[0], color='red', linestyle='--', alpha=0.5, label=f'Deficit: ${abs(diff):.2f}')
        
        self.budget_ax.set_ylabel('Amount ($)', fontsize=10)
        self.budget_ax.set_title('Budget vs Predicted Spending', fontsize=12, fontweight='bold')
        self.budget_ax.grid(axis='y', linestyle='--', alpha=0.3)
        self.budget_ax.legend()
        
        self.budget_fig.tight_layout()
        self.budget_canvas.draw()

    def plot_spending_trends(self):
        """Plot historical spending trends"""
        self.budget_ax.clear()
        
        data = self.budget_prediction_data
        monthly_data = data['monthly_data']
        
        # Create month-year labels
        monthly_data['Month_Year'] = monthly_data['Year'].astype(str) + '-' + monthly_data['Month'].astype(str).str.zfill(2)
        
        # Plot historical spending
        self.budget_ax.plot(monthly_data['Month_Year'], monthly_data['Total'], 
                           marker='o', linewidth=2, markersize=6, label='Historical Spending')
        
        # Add trend line
        x_numeric = np.arange(len(monthly_data))
        z = np.polyfit(x_numeric, monthly_data['Total'], 1)
        p = np.poly1d(z)
        self.budget_ax.plot(monthly_data['Month_Year'], p(x_numeric), 
                           'r--', alpha=0.7, label='Trend Line')
        
        # Add average line
        avg_spending = data['avg_monthly_spending']
        self.budget_ax.axhline(y=avg_spending, color='orange', linestyle=':', alpha=0.7, 
                              label=f'Average: ${avg_spending:.2f}')
        
        self.budget_ax.set_xlabel('Month', fontsize=10)
        self.budget_ax.set_ylabel('Monthly Spending ($)', fontsize=10)
        self.budget_ax.set_title('Historical Spending Trends', fontsize=12, fontweight='bold')
        self.budget_ax.grid(True, alpha=0.3)
        self.budget_ax.legend()
        self.budget_ax.tick_params(axis='x', rotation=45)
        
        self.budget_fig.tight_layout()
        self.budget_canvas.draw()

    def plot_monthly_breakdown(self):
        """Plot monthly spending breakdown by category"""
        self.budget_ax.clear()
        
        data = self.budget_prediction_data
        monthly_data = data['monthly_data']
        
        # Calculate spending by weekend vs weekday
        weekend_spending = monthly_data[monthly_data['Is_Weekend'] > 0.5]['Total'].sum() if len(monthly_data[monthly_data['Is_Weekend'] > 0.5]) > 0 else 0
        weekday_spending = monthly_data[monthly_data['Is_Weekend'] <= 0.5]['Total'].sum() if len(monthly_data[monthly_data['Is_Weekend'] <= 0.5]) > 0 else 0
        
        # If no weekend data, estimate from overall data
        if weekend_spending == 0 and weekday_spending == 0:
            total_spending = monthly_data['Total'].sum()
            weekend_spending = total_spending * 0.3  # Estimate 30% weekend
            weekday_spending = total_spending * 0.7  # Estimate 70% weekday
        
        categories = ['Weekday\nSpending', 'Weekend\nSpending']
        values = [weekday_spending, weekend_spending]
        colors = ['#4A90E2', '#F5A623']
        
        wedges, texts, autotexts = self.budget_ax.pie(values, labels=categories, colors=colors, 
                                                     autopct='%1.1f%%', startangle=90)
        
        # Add value labels
        for i, (wedge, value) in enumerate(zip(wedges, values)):
            angle = (wedge.theta2 + wedge.theta1) / 2
            x = 0.7 * np.cos(np.radians(angle))
            y = 0.7 * np.sin(np.radians(angle))
            self.budget_ax.text(x, y, f'${value:.2f}', ha='center', va='center', 
                               fontsize=10, fontweight='bold')
        
        self.budget_ax.set_title('Spending Breakdown: Weekday vs Weekend', fontsize=12, fontweight='bold')
        
        self.budget_fig.tight_layout()
        self.budget_canvas.draw()

    def plot_provider_analysis(self):
        """Plot spending analysis by provider"""
        if self.df is None or self.df.empty:
            self.show_budget_chart_placeholder()
            return
        
        self.budget_ax.clear()
        
        # Group by provider
        provider_stats = self.df.groupby("Car Cat").agg({
            "Total": ["sum", "mean", "count"],
            "Distance (KM)": "mean",
            "Rental hour": "mean"
        }).round(2)
        
        # Flatten column names
        provider_stats.columns = ["Total_Sum", "Total_Mean", "Trip_Count", "Avg_Distance", "Avg_Duration"]
        provider_stats = provider_stats.reset_index()
        
        # Create subplot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
        
        # Total spending by provider
        providers = provider_stats["Car Cat"].tolist()
        total_spending = provider_stats["Total_Sum"].tolist()
        
        bars1 = ax1.bar(providers, total_spending, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'], alpha=0.7)
        ax1.set_ylabel("Total Spending ($)", fontsize=10)
        ax1.set_title("Total Spending by Provider", fontsize=11)
        ax1.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars1, total_spending):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(total_spending)*0.01,
                    f'${value:.2f}', ha='center', va='bottom', fontsize=9)
        
        # Average cost per trip
        avg_costs = provider_stats["Total_Mean"].tolist()
        bars2 = ax2.bar(providers, avg_costs, color=['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'], alpha=0.7)
        ax2.set_ylabel("Average Cost per Trip ($)", fontsize=10)
        ax2.set_title("Average Cost per Trip by Provider", fontsize=11)
        ax2.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars2, avg_costs):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max(avg_costs)*0.01,
                    f'${value:.2f}', ha='center', va='bottom', fontsize=9)
        
        # Clear the main axis and use the subplot
        self.budget_ax.clear()
        self.budget_ax.axis('off')
        
        self.budget_fig.tight_layout()
        self.budget_canvas.draw()

    def plot_risk_assessment(self):
        """Risk assessment visualization with criteria shown for each risk level (by % of budget)"""
        self.budget_ax.clear()
        data = self.budget_prediction_data
        risk = data['risk_level'].capitalize()
        confidence = data['confidence_score']
        remaining = data['budget_remaining']
        budget = data.get('budget', 1)  # Avoid division by zero

        # Define risk levels, colors, angles, and criteria (by % of budget)
        risk_levels = ['Low', 'Medium', 'High']
        risk_colors = ['#2E8B57', '#FFA500', '#FF4500']
        risk_angles = [0.25 * np.pi, 0.5 * np.pi, 0.75 * np.pi]
        # Example: Low: >40% remaining, Medium: 20-40%, High: <20%
        risk_criteria = {
            'Low': '> 40% of budget left',
            'Medium': '20% - 40% left',
            'High': '< 20% left'
        }

        # Draw gauge background (arc)
        theta = np.linspace(0, np.pi, 200)
        self.budget_ax.plot(np.cos(theta), np.sin(theta), color='gray', lw=3, alpha=0.3, zorder=1)

        # Draw colored risk sectors
        for i, (level, color, angle) in enumerate(zip(risk_levels, risk_colors, risk_angles)):
            start = 0 if i == 0 else risk_angles[i-1]
            end = angle
            arc_theta = np.linspace(start, end, 50)
            self.budget_ax.plot(np.cos(arc_theta), np.sin(arc_theta), color=color, lw=10, solid_capstyle='round', zorder=2)

        # Draw current risk pointer
        try:
            idx = risk_levels.index(risk)
        except ValueError:
            idx = 1  # Default to Medium if unknown
        pointer_angle = risk_angles[idx]
        self.budget_ax.plot([0, 0.85 * np.cos(pointer_angle)], [0, 0.85 * np.sin(pointer_angle)],
                            color='black', lw=4, marker='o', markersize=10, zorder=3)

        # Add risk labels and criteria
        for i, (level, color, angle) in enumerate(zip(risk_levels, risk_colors, risk_angles)):
            x, y = 1.1 * np.cos(angle), 1.1 * np.sin(angle)
            self.budget_ax.text(
                x, y,
                f"{level}\n({risk_criteria[level]})",
                color=color, fontsize=10, fontweight='bold', ha='center', va='center'
            )

        # Show actual % remaining
        percent_remaining = 100 * remaining / budget if budget else 0

        # Add main info text (centered, mobile-friendly)
        self.budget_ax.text(
            0, -0.2,
            f'Risk: {risk}\nConfidence: {confidence:.0%}\nRemaining: ${remaining:.2f} ({percent_remaining:.0f}% of budget)',
            ha='center', va='center', fontsize=12, fontweight='bold',
            bbox=dict(boxstyle="round,pad=0.4", facecolor="#f9f9f9", edgecolor="#bbb")
        )

        self.budget_ax.set_xlim(-1.3, 1.3)
        self.budget_ax.set_ylim(-0.7, 1.2)
        self.budget_ax.set_aspect('equal')
        self.budget_ax.axis('off')
        self.budget_ax.set_title('Budget Risk Assessment', fontsize=13, fontweight='bold', pad=15)

        self.budget_fig.tight_layout()
        self.budget_canvas.draw()
    def plot_historical_vs_predicted(self):
        """Plot historical vs predicted spending comparison"""
        self.budget_ax.clear()
        
        data = self.budget_prediction_data
        monthly_data = data['monthly_data']
        
        # Create month-year labels
        monthly_data['Month_Year'] = monthly_data['Year'].astype(str) + '-' + monthly_data['Month'].astype(str).str.zfill(2)
        
        # Plot historical data
        self.budget_ax.plot(monthly_data['Month_Year'], monthly_data['Total'], 
                           marker='o', linewidth=2, markersize=6, label='Historical Spending', color='#4A90E2')
        
        # Add predicted spending line
        predicted_monthly = data['predicted_spending'] / data['period_months']
        self.budget_ax.axhline(y=predicted_monthly, color='red', linestyle='--', linewidth=2, 
                              label=f'Predicted: ${predicted_monthly:.2f}/month')
        
        # Add confidence interval
        std = data['spending_std']
        self.budget_ax.fill_between(monthly_data['Month_Year'], 
                                   predicted_monthly - std, predicted_monthly + std, 
                                   alpha=0.2, color='red', label='Confidence Interval')
        
        # Add average line
        avg_spending = data['avg_monthly_spending']
        self.budget_ax.axhline(y=avg_spending, color='orange', linestyle=':', alpha=0.7, 
                              label=f'Historical Average: ${avg_spending:.2f}')
        
        self.budget_ax.set_xlabel('Month', fontsize=10)
        self.budget_ax.set_ylabel('Monthly Spending ($)', fontsize=10)
        self.budget_ax.set_title('Historical vs Predicted Spending', fontsize=12, fontweight='bold')
        self.budget_ax.grid(True, alpha=0.3)
        self.budget_ax.legend()
        self.budget_ax.tick_params(axis='x', rotation=45)
        
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
        """Calculate cost requirements and scenarios"""
        try:
            target_cost = float(self.target_cost_var.get())
            provider = self.planning_provider_var.get()
            calc_type = self.calculation_type_var.get()

            # Clear previous results
            self.results_text.delete(1.0, tk.END)
            for item in self.scenarios_tree.get_children():
                self.scenarios_tree.delete(item)

            # Clear breakdown
            for label in self.breakdown_labels.values():
                label.config(text="$0.00")

            # Clear previous graph
            self.cost_planning_ax.clear()

            if calc_type == "duration_based":
                if not self.planning_duration_var.get():
                    messagebox.showwarning(
                        "Input Required", "Please enter monthly duration."
                    )
                    return

                duration = float(self.planning_duration_var.get())
                required_mileage = calculate_required_mileage(
                    target_cost, duration, provider
                )

                if required_mileage is None or required_mileage <= 0:
                    self.results_text.insert(
                        tk.END,
                        f"Error: Cannot reach target cost of ${target_cost:.2f} with {duration} hours.\n",
                    )
                    self.results_text.insert(
                        tk.END, "The mileage cost alone would exceed your target.\n"
                    )
                    self.results_text.insert(
                        tk.END, "Try increasing duration or reducing target cost.\n\n"
                    )

                    # Show cost analysis graph for this case
                    self.plot_cost_analysis(
                        target_cost,
                        provider,
                        calc_type="duration_based",
                        duration=duration,
                    )
                    return

                # Calculate cost breakdown
                breakdown = calculate_cost_breakdown(
                    required_mileage, duration, provider
                )
                if breakdown:
                    self.breakdown_labels["Mileage Cost"].config(
                        text=f"${breakdown['mileage_cost']:.2f}"
                    )
                    self.breakdown_labels["Duration Cost"].config(
                        text=f"${breakdown['duration_cost']:.2f}"
                    )
                    self.breakdown_labels["Total Cost"].config(
                        text=f"${breakdown['total_cost']:.2f}"
                    )

                # Display results
                self.results_text.insert(tk.END, f"Target Cost: ${target_cost:.2f}\n")
                self.results_text.insert(
                    tk.END, f"Monthly Duration: {duration} hours\n"
                )
                self.results_text.insert(
                    tk.END, f"Required Mileage: {required_mileage:.2f} km\n"
                )
                self.results_text.insert(
                    tk.END, f"Weekly Mileage: {required_mileage/4:.2f} km\n\n"
                )

                # Generate booking scenarios
                scenarios = generate_booking_scenarios(
                    target_cost, duration=duration, provider=provider
                )

                # Plot cost analysis
                self.plot_cost_analysis(
                    target_cost, provider, calc_type="duration_based", duration=duration
                )

            else:  # mileage_based
                if not self.mileage_var.get():
                    messagebox.showwarning(
                        "Input Required", "Please enter monthly mileage."
                    )
                    return

                mileage = float(self.mileage_var.get())
                required_duration = calculate_required_duration(
                    target_cost, mileage, provider
                )

                if required_duration is None or required_duration["total_hours"] <= 0:
                    if required_duration and required_duration.get("impossible"):
                        self.results_text.insert(
                            tk.END, f"Error: {required_duration['reason']}\n"
                        )
                        self.results_text.insert(
                            tk.END,
                            "Try reducing mileage or increasing target cost.\n\n",
                        )
                    else:
                        self.results_text.insert(
                            tk.END,
                            f"Error: Cannot reach target cost of ${target_cost:.2f} with {mileage} km.\n",
                        )
                        self.results_text.insert(
                            tk.END, "The mileage cost alone would exceed your target.\n"
                        )
                        self.results_text.insert(
                            tk.END,
                            "Try reducing mileage or increasing target cost.\n\n",
                        )

                    # Show cost analysis graph for this case
                    self.plot_cost_analysis(
                        target_cost,
                        provider,
                        calc_type="mileage_based",
                        mileage=mileage,
                    )
                    return

                # Calculate cost breakdown
                breakdown = calculate_cost_breakdown(
                    mileage, required_duration["total_hours"], provider
                )
                if breakdown:
                    self.breakdown_labels["Mileage Cost"].config(
                        text=f"${breakdown['mileage_cost']:.2f}"
                    )
                    self.breakdown_labels["Duration Cost"].config(
                        text=f"${breakdown['duration_cost']:.2f}"
                    )
                    self.breakdown_labels["Total Cost"].config(
                        text=f"${breakdown['total_cost']:.2f}"
                    )

                # Display results
                self.results_text.insert(tk.END, f"Target Cost: ${target_cost:.2f}\n")
                self.results_text.insert(tk.END, f"Monthly Mileage: {mileage} km\n")
                self.results_text.insert(
                    tk.END,
                    f"Required Duration: {required_duration['days']} days, {required_duration['hours']} hours, {required_duration['minutes']} minutes\n",
                )
                self.results_text.insert(
                    tk.END,
                    f"Total Hours: {required_duration['total_hours']:.2f} hours\n\n",
                )

                # Generate booking scenarios
                scenarios = generate_booking_scenarios(
                    target_cost, mileage=mileage, provider=provider
                )

                # Plot cost analysis
                self.plot_cost_analysis(
                    target_cost, provider, calc_type="mileage_based", mileage=mileage
                )

            # Update the selected graph type if it's not the default "Cost Analysis"
            if self.graph_type_var.get() != "Cost Analysis":
                self.update_selected_graph()

            # Display scenarios in treeview
            for scenario in scenarios:
                self.scenarios_tree.insert(
                    "",
                    "end",
                    values=(
                        scenario["bookings_per_week"],
                        f"{scenario['hours_per_booking']:.2f}",
                        f"{scenario['km_per_booking']:.2f}",
                        f"{scenario['total_hours_per_month']:.2f}",
                    ),
                )

            # Update status
            self.status_var.set(
                f"Generated {len(scenarios)} booking scenarios for target cost ${target_cost:.2f}"
            )

        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter valid numeric values.")
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
        if self.df is None or self.df.empty:
            messagebox.showwarning("No Data", "Please load rental data first")
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
            messagebox.showwarning("Missing Data", "Fuel consumption or car model data is missing")
            return

        # Filter out rows with missing fuel consumption data
        df_filtered = df.dropna(subset=["Consumption (KM/L)"])
        if df_filtered.empty:
            messagebox.showwarning("No Data", "No fuel consumption data available")
            return

        # Group by car model and calculate fuel efficiency stats
        fuel_stats = df_filtered.groupby("Car model").agg({
            "Consumption (KM/L)": ["mean", "count", "std"],
            "Total": "mean",
            "Distance (KM)": "mean",
            "Car Cat": lambda x: x.mode().iloc[0] if not x.empty else "Unknown"
        }).round(2)

        # Flatten column names
        fuel_stats.columns = ["Avg_Consumption", "Trip_Count", "Consumption_Std", "Avg_Cost", "Avg_Distance", "Provider"]
        fuel_stats = fuel_stats.reset_index()

        # Filter models with at least 2 trips for statistical significance
        fuel_stats = fuel_stats[fuel_stats["Trip_Count"] >= 2].sort_values("Avg_Consumption", ascending=False)

        # Display key statistics
        self.add_stat("Most Efficient", f"{fuel_stats.iloc[0]['Car model']} ({fuel_stats.iloc[0]['Avg_Consumption']:.1f} km/L)")
        self.add_stat("Least Efficient", f"{fuel_stats.iloc[-1]['Car model']} ({fuel_stats.iloc[-1]['Avg_Consumption']:.1f} km/L)")
        self.add_stat("Average Efficiency", f"{df_filtered['Consumption (KM/L)'].mean():.1f} km/L")
        self.add_stat("Models Analyzed", f"{len(fuel_stats)}")

        # Create visualization
        self.analysis_ax.clear()
        
        # Create horizontal bar chart
        models = fuel_stats["Car model"].tolist()
        consumption = fuel_stats["Avg_Consumption"].tolist()
        colors = ['#2E8B57' if x > df_filtered['Consumption (KM/L)'].mean() else '#CD5C5C' for x in consumption]
        
        bars = self.analysis_ax.barh(models, consumption, color=colors, alpha=0.7)
        
        # Add average line
        avg_consumption = df_filtered['Consumption (KM/L)'].mean()
        self.analysis_ax.axvline(avg_consumption, color='red', linestyle='--', alpha=0.7, label=f'Average ({avg_consumption:.1f} km/L)')
        
        # Add value labels on bars
        for i, (bar, value) in enumerate(zip(bars, consumption)):
            self.analysis_ax.text(value + 0.5, bar.get_y() + bar.get_height()/2, 
                                f'{value:.1f}', va='center', fontsize=9)
        
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
            messagebox.showwarning("Missing Data", "Weekday/weekend information is missing")
            return

        # Group by weekday/weekend
        weekend_stats = df.groupby("Weekday/weekend").agg({
            "Total": ["count", "mean", "sum"],
            "Distance (KM)": "mean",
            "Rental hour": "mean",
            "Cost per KM": "mean"
        }).round(2)

        # Flatten column names
        weekend_stats.columns = ["Trip_Count", "Avg_Cost", "Total_Cost", "Avg_Distance", "Avg_Duration", "Avg_Cost_Per_KM"]
        weekend_stats = weekend_stats.reset_index()

        # Display key statistics
        weekday_data = weekend_stats[weekend_stats["Weekday/weekend"] == "weekday"]
        weekend_data = weekend_stats[weekend_stats["Weekday/weekend"] == "weekend"]
        
        if not weekday_data.empty:
            self.add_stat("Weekday Avg Cost", f"${weekday_data.iloc[0]['Avg_Cost']:.2f}")
            self.add_stat("Weekday Trips", f"{weekday_data.iloc[0]['Trip_Count']}")
        
        if not weekend_data.empty:
            self.add_stat("Weekend Avg Cost", f"${weekend_data.iloc[0]['Avg_Cost']:.2f}")
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
        
        bars1 = ax1.bar(days, avg_costs, color=['#4A90E2', '#F5A623'], alpha=0.7)
        ax1.set_ylabel("Average Cost ($)", fontsize=10)
        ax1.set_title("Average Cost: Weekend vs Weekday", fontsize=11)
        ax1.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars1, avg_costs):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                    f'${value:.2f}', ha='center', va='bottom', fontsize=10)
        
        # Trip count comparison
        bars2 = ax2.bar(days, trip_counts, color=['#4A90E2', '#F5A623'], alpha=0.7)
        ax2.set_ylabel("Number of Trips", fontsize=10)
        ax2.set_title("Trip Frequency: Weekend vs Weekday", fontsize=11)
        ax2.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars2, trip_counts):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{int(value)}', ha='center', va='bottom', fontsize=10)
        
        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def show_distance_cost_analysis(self, df):
        """Show correlation between distance and cost"""
        if "Distance (KM)" not in df.columns or "Total" not in df.columns:
            messagebox.showwarning("Missing Data", "Distance or cost information is missing")
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
                self.analysis_ax.scatter(provider_data["Distance (KM)"], provider_data["Total"], 
                                       c=[color_map[provider]], label=provider, alpha=0.6, s=50)
            self.analysis_ax.legend()
        else:
            self.analysis_ax.scatter(df_filtered["Distance (KM)"], df_filtered["Total"], 
                                   alpha=0.6, s=50, color='#4A90E2')

        # Add trend line
        z = np.polyfit(df_filtered["Distance (KM)"], df_filtered["Total"], 1)
        p = np.poly1d(z)
        self.analysis_ax.plot(df_filtered["Distance (KM)"], p(df_filtered["Distance (KM)"]), 
                             "r--", alpha=0.8, linewidth=2, label=f'Trend (R²={correlation**2:.3f})')
        
        self.analysis_ax.set_xlabel("Distance (km)", fontsize=10)
        self.analysis_ax.set_ylabel("Total Cost ($)", fontsize=10)
        self.analysis_ax.set_title("Distance vs Cost Correlation", fontsize=12)
        self.analysis_ax.grid(True, alpha=0.3)
        self.analysis_ax.legend()
        
        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def show_electric_vs_traditional_analysis(self, df):
        """Show comparison between electric and traditional vehicles"""
        if "kWh Used" not in df.columns:
            messagebox.showwarning("Missing Data", "Electric vehicle data (kWh Used) is missing")
            return

        # Categorize vehicles
        df["Vehicle_Type"] = df["kWh Used"].apply(lambda x: "Electric" if pd.notna(x) and x > 0 else "Traditional")
        
        # Group by vehicle type
        vehicle_stats = df.groupby("Vehicle_Type").agg({
            "Total": ["count", "mean", "sum"],
            "Distance (KM)": "mean",
            "Rental hour": "mean",
            "Cost per KM": "mean"
        }).round(2)

        # Flatten column names
        vehicle_stats.columns = ["Trip_Count", "Avg_Cost", "Total_Cost", "Avg_Distance", "Avg_Duration", "Avg_Cost_Per_KM"]
        vehicle_stats = vehicle_stats.reset_index()

        # Display key statistics
        electric_data = vehicle_stats[vehicle_stats["Vehicle_Type"] == "Electric"]
        traditional_data = vehicle_stats[vehicle_stats["Vehicle_Type"] == "Traditional"]
        
        if not electric_data.empty:
            self.add_stat("Electric Avg Cost", f"${electric_data.iloc[0]['Avg_Cost']:.2f}")
            self.add_stat("Electric Trips", f"{electric_data.iloc[0]['Trip_Count']}")
        
        if not traditional_data.empty:
            self.add_stat("Traditional Avg Cost", f"${traditional_data.iloc[0]['Avg_Cost']:.2f}")
            self.add_stat("Traditional Trips", f"{traditional_data.iloc[0]['Trip_Count']}")

        # Create visualization
        self.analysis_ax.clear()
        
        # Create comparison chart
        vehicle_types = vehicle_stats["Vehicle_Type"].tolist()
        avg_costs = vehicle_stats["Avg_Cost"].tolist()
        trip_counts = vehicle_stats["Trip_Count"].tolist()
        
        # Create subplots within the existing figure
        self.analysis_fig.clear()
        ax1 = self.analysis_fig.add_subplot(1, 2, 1)
        ax2 = self.analysis_fig.add_subplot(1, 2, 2)
        
        # Cost comparison
        bars1 = ax1.bar(vehicle_types, avg_costs, color=['#00CED1', '#FF6347'], alpha=0.7)
        ax1.set_ylabel("Average Cost ($)", fontsize=10)
        ax1.set_title("Average Cost: Electric vs Traditional", fontsize=11)
        ax1.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars1, avg_costs):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                    f'${value:.2f}', ha='center', va='bottom', fontsize=10)
        
        # Trip count comparison
        bars2 = ax2.bar(vehicle_types, trip_counts, color=['#00CED1', '#FF6347'], alpha=0.7)
        ax2.set_ylabel("Number of Trips", fontsize=10)
        ax2.set_title("Usage: Electric vs Traditional", fontsize=11)
        ax2.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars2, trip_counts):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{int(value)}', ha='center', va='bottom', fontsize=10)
        
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
            efficiency_stats = df_filtered.groupby("Car Cat").agg({
                "Cost per KM": "mean",
                "Cost/HR": "mean",
                "Total": "count"
            }).round(3)
            efficiency_stats = efficiency_stats.reset_index()
            
            # Display key statistics
            best_km = efficiency_stats.loc[efficiency_stats["Cost per KM"].idxmin()]
            best_hr = efficiency_stats.loc[efficiency_stats["Cost/HR"].idxmin()]
            
            self.add_stat("Best $/km", f"{best_km['Car Cat']} (${best_km['Cost per KM']:.3f})")
            self.add_stat("Best $/hr", f"{best_hr['Car Cat']} (${best_hr['Cost/HR']:.2f})")
            self.add_stat("Avg $/km", f"${df_filtered['Cost per KM'].mean():.3f}")
            self.add_stat("Avg $/hr", f"${df_filtered['Cost/HR'].mean():.2f}")

            # Create bubble chart
            self.analysis_ax.clear()
            
            providers = efficiency_stats["Car Cat"].tolist()
            cost_per_km = efficiency_stats["Cost per KM"].tolist()
            cost_per_hr = efficiency_stats["Cost/HR"].tolist()
            trip_counts = efficiency_stats["Total"].tolist()
            
            # Create bubble chart
            scatter = self.analysis_ax.scatter(cost_per_km, cost_per_hr, s=[count*10 for count in trip_counts], 
                                             alpha=0.6, c=range(len(providers)), cmap='viridis')
            
            # Add labels for each provider
            for i, provider in enumerate(providers):
                self.analysis_ax.annotate(provider, (cost_per_km[i], cost_per_hr[i]), 
                                        xytext=(5, 5), textcoords='offset points', fontsize=9)
            
            self.analysis_ax.set_xlabel("Cost per KM ($)", fontsize=10)
            self.analysis_ax.set_ylabel("Cost per Hour ($)", fontsize=10)
            self.analysis_ax.set_title("Cost Efficiency Comparison\n(Bubble size = Trip count)", fontsize=12)
            self.analysis_ax.grid(True, alpha=0.3)
            
            # Add colorbar
            cbar = plt.colorbar(scatter, ax=self.analysis_ax)
            cbar.set_label('Provider Index', fontsize=9)
        
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
        quarterly_stats = df_copy.groupby("Quarter").agg({
            "Total": ["count", "mean", "sum"],
            "Distance (KM)": "mean",
            "Rental hour": "mean"
        }).round(2)

        # Flatten column names
        quarterly_stats.columns = ["Trip_Count", "Avg_Cost", "Total_Cost", "Avg_Distance", "Avg_Duration"]
        quarterly_stats = quarterly_stats.reset_index()

        # Reorder quarters
        quarter_order = ["Jan-Apr", "May-Aug", "Sep-Dec"]
        quarterly_stats = quarterly_stats.set_index("Quarter").reindex(quarter_order).reset_index()

        # Display key statistics
        busiest_quarter = quarterly_stats.loc[quarterly_stats["Trip_Count"].idxmax()]
        most_expensive = quarterly_stats.loc[quarterly_stats["Avg_Cost"].idxmax()]
        
        self.add_stat("Busiest Quarter", f"{busiest_quarter['Quarter']} ({busiest_quarter['Trip_Count']} trips)")
        self.add_stat("Most Expensive", f"{most_expensive['Quarter']} (${most_expensive['Avg_Cost']:.2f})")
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
        q_colors = ['#FF6B6B', '#4ECDC4', '#45B7D1']
        
        # Trip count by quarter
        bars1 = ax1.bar(quarters, trip_counts, color=q_colors[:len(quarters)], alpha=0.7)
        ax1.set_ylabel("Number of Trips", fontsize=10)
        ax1.set_title("Trip Frequency by Quarter", fontsize=11)
        ax1.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars1, trip_counts):
            ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5, 
                    f'{int(value)}', ha='center', va='bottom', fontsize=10)
        
        # Average cost by quarter
        bars2 = ax2.bar(quarters, avg_costs, color=q_colors[:len(quarters)], alpha=0.7)
        ax2.set_ylabel("Average Cost ($)", fontsize=10)
        ax2.set_title("Average Cost by Quarter", fontsize=11)
        ax2.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Add value labels
        for bar, value in zip(bars2, avg_costs):
            ax2.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1, 
                    f'${value:.2f}', ha='center', va='bottom', fontsize=10)
        
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
        ax1.hist(df_filtered["Rental hour"], bins=20, color='#4A90E2', alpha=0.7, edgecolor='black')
        ax1.set_xlabel("Rental Duration (hours)", fontsize=10)
        ax1.set_ylabel("Frequency", fontsize=10)
        ax1.set_title("Rental Duration Distribution", fontsize=11)
        ax1.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Distance distribution
        ax2.hist(df_filtered["Distance (KM)"], bins=20, color='#F5A623', alpha=0.7, edgecolor='black')
        ax2.set_xlabel("Distance (km)", fontsize=10)
        ax2.set_ylabel("Frequency", fontsize=10)
        ax2.set_title("Distance Distribution", fontsize=11)
        ax2.grid(axis="y", linestyle="--", alpha=0.3)
        
        # Adjust layout
        self.analysis_fig.tight_layout()
        self.analysis_canvas.draw()

    def on_provider_changed(self, event=None):
        """Handle provider selection change to show/hide EV-specific fields"""
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

        # Update fuel economy comparison if we have the necessary data
        self.update_fuel_economy_comparison()

    def update_fuel_economy_comparison(self):
        """Calculate and display fuel economy comparison between ICE/Hybrid and EV"""
        try:
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
            if "division by zero" not in str(e).lower():
                print(f"Error updating fuel economy comparison: {e}")

    def auto_update_fields(self, *args):
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
                # Pumped fuel cost (with 0.91 factor)
                pumped_fuel_cost = (
                    fuel_price * 0.91 * fuel_pumped if fuel_pumped and fuel_price else 0
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
