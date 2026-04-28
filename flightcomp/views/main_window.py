"""
Main GUI Window
Provides the user interface for the pilot ATC training assistant.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import time
import os

from utils.atc_instructions import ATCInstructions, format_readback_example
from utils.logging_config import get_logger
from utils.atis_decoder import ATISDecoder
from utils.config import Config
from utils.speech import SpeechEngine, AudioPlayer
from data.scenarios.scenario_engine import ScenarioEngine, DifficultyLevel, ScenarioType
from assessment.assessment_engine import AssessmentEngine
from utils.progress_tracker import ProgressTracker
from utils.report_generator import ReportGenerator
from utils.simulator_bridge import SimulatorBridge, SimState
from typing import Optional

logger = get_logger(__name__)


class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Commercial Pilot ATC Training Assistant")
        self.root.geometry("900x650")
        self.root.minsize(800, 600)

        # Load configuration
        self.config = Config()

        # Load airports data from the main config
        self.airports = self.config.get("airports", {})

        # Initialize speech engine with error handling
        try:
            self.speech_engine = SpeechEngine(
                rate=self.config.get("voice_rate", 150), voice_gender="male"
            )
            if not self.speech_engine.is_speech_available():
                logger.warning("Speech engine is not available")
        except Exception as e:
            logger.warning("Failed to initialize speech engine: %s", e)
            # Create a dummy speech engine that doesn't work
            self.speech_engine = None

        # Initialize audio player
        self.audio_player = AudioPlayer()

        # Initialize ATC Instructions with user's settings
        self.atc = ATCInstructions(
            experience_level=self.config.get("experience_level"),
            aircraft_type=self.config.get("aircraft_type"),
        )

        # Initialize ATIS Decoder
        self.atis_decoder = ATISDecoder(
            experience_level=self.config.get("experience_level")
        )

        # Dictionary to store parameter entry widgets
        self.param_entries = {}

        # Initialize AI response handler
        self.ai_handler = None
        try:
            from utils.ai_response_handler import AIResponseHandler

            self.ai_handler = AIResponseHandler(self.config)
            # Set up callback for AI responses
            self.ai_handler.set_ui_update_callback(self.on_ai_response_generated)
        except Exception as e:
            logger.warning("AI response handler not available: %s", e)

        # Initialize scenario engine
        try:
            self.scenario_engine = ScenarioEngine()
        except Exception as e:
            logger.warning("Scenario engine not available: %s", e)
            self.scenario_engine = None

        # Initialize assessment engine
        try:
            self.assessment_engine = AssessmentEngine()
        except Exception as e:
            logger.warning("Assessment engine not available: %s", e)
            self.assessment_engine = None

        # Initialize progress tracker
        try:
            self.progress_tracker = ProgressTracker()
        except Exception as e:
            logger.warning("Progress tracker not available: %s", e)
            self.progress_tracker = None
        self.report_generator = ReportGenerator(self.progress_tracker) if self.progress_tracker else None
        self.last_debrief_text = ""
        self.last_debrief_path = ""

        # Session state
        self.current_session_active = False
        self.current_scenario = None
        self.session_start_time = None
        self.last_atc_message = None
        self.last_atc_timestamp = None
        
        # Objective tracking
        self.completed_objectives = set()
        self.completed_communications = set()
        self.scenario_objectives = []
        self.scenario_expected_communications = []

        # X-Plane / FlyWithLua simulator bridge (optional)
        self.sim_bridge: Optional[SimulatorBridge] = None
        self._sim_bridge_enabled = bool(self.config.get("xplane_bridge_enabled", False))
        self._live_icao = ""
        self._setup_simulator_bridge()

        # Set up the UI
        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface"""
        # Menu bar: Tools, Simulator
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="Validate data...", command=self.open_data_validation)
        sim_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Simulator", menu=sim_menu)
        self.xplane_var = tk.BooleanVar(value=self._sim_bridge_enabled)
        sim_menu.add_checkbutton(
            label="Use X-Plane context",
            variable=self.xplane_var,
            command=self._on_xplane_bridge_toggle,
        )

        # Set up main frame with padding
        self.main_frame = ttk.Frame(self.root, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Create tabs
        self.atc_tab = ttk.Frame(self.notebook)
        self.atis_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)

        self.notebook.add(self.atc_tab, text="ATC Instructions")
        self.notebook.add(self.atis_tab, text="ATIS Decoder")
        self.notebook.add(self.settings_tab, text="Settings")

        # Set up each tab
        self.setup_atc_tab()
        self.setup_atis_tab()
        self.setup_settings_tab()

        # Add AI status indicator and settings button
        self.setup_ai_header()

        # Status bar (may show "Live: ICAO" when X-Plane bridge is active)
        self.status_var = tk.StringVar()
        self._update_status_with_sim()
        self.status_bar = ttk.Label(
            self.root, textvariable=self.status_var, anchor=tk.W, relief=tk.SUNKEN
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self._update_status_with_sim()

    def _update_status_with_sim(self) -> None:
        """Update status bar text; prefix with Live: ICAO when X-Plane bridge has context."""
        if hasattr(self, "status_var"):
            base = "Live: " + self._live_icao + " | " if self._live_icao else ""
            self.status_var.set(base + "Ready")

    def _setup_simulator_bridge(self) -> None:
        """Create and optionally start the X-Plane/FlyWithLua UDP bridge."""
        listen_port = int(self.config.get("xplane_bridge_listen_port", 49000))
        send_port = int(self.config.get("xplane_bridge_send_port", 49001))

        def on_state(state: SimState) -> None:
            self.root.after(0, lambda: self._on_sim_state(state))

        self.sim_bridge = SimulatorBridge(
            listen_port=listen_port,
            send_port=send_port,
            on_state_received=on_state,
        )
        if self._sim_bridge_enabled:
            self.sim_bridge.start()

    def _on_sim_state(self, state: SimState) -> None:
        """Update live ICAO from sim and refresh status bar."""
        self._live_icao = state.icao or ""
        self._update_status_with_sim()

    def _on_xplane_bridge_toggle(self) -> None:
        """Enable or disable the X-Plane bridge and persist setting."""
        enabled = self.xplane_var.get()
        self._sim_bridge_enabled = enabled
        self.config.set("xplane_bridge_enabled", enabled)
        self.config.save_config()
        if self.sim_bridge:
            if enabled:
                self.sim_bridge.start()
            else:
                self.sim_bridge.stop()
                self._live_icao = ""
                self._update_status_with_sim()

    def setup_ai_header(self):
        """Set up AI status indicator and settings button"""
        # Create header frame
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))

        # AI Status indicator
        self.ai_status_label = ttk.Label(
            header_frame,
            text="🤖 AI: Checking...",
            font=("Arial", 9),
            foreground="gray",
        )
        self.ai_status_label.pack(side=tk.LEFT, padx=(0, 10))

        # AI Processing indicator
        self.ai_processing_label = ttk.Label(
            header_frame, text="", font=("Arial", 9), foreground="orange"
        )
        self.ai_processing_label.pack(side=tk.LEFT, padx=(10, 0))

        # AI Settings button
        self.ai_settings_button = ttk.Button(
            header_frame, text="AI Settings", command=self.open_ai_settings
        )
        self.ai_settings_button.pack(side=tk.RIGHT, padx=(10, 0))

        # Check AI status after UI is loaded
        self.root.after(500, self.update_ai_status_indicator)

    def update_ai_status_indicator(self):
        """Update the AI status indicator"""
        try:
            if self.ai_handler and self.ai_handler.is_ai_available():
                self.ai_status_label.config(text="🤖 AI: Available", foreground="green")
            else:
                self.ai_status_label.config(
                    text="🤖 AI: Not Available", foreground="red"
                )
        except Exception as e:
            self.ai_status_label.config(text="🤖 AI: Error", foreground="orange")
            logger.warning("Error updating AI status: %s", e)

    def show_ai_processing(self, message="AI Processing..."):
        """Show AI processing indicator"""
        if hasattr(self, "ai_processing_label"):
            self.ai_processing_label.config(text=f"⏳ {message}", foreground="orange")

    def hide_ai_processing(self):
        """Hide AI processing indicator"""
        if hasattr(self, "ai_processing_label"):
            self.ai_processing_label.config(text="")

    def open_ai_settings(self):
        """Open AI settings dialog"""
        try:
            from views.ai_settings_dialog import AISettingsDialog

            def on_settings_save(new_config):
                """Handle settings save"""
                self.config.update(new_config)
                if self.ai_handler:
                    self.ai_handler.update_config(new_config)
                self.status_var.set("Status: AI settings updated")
                self.update_ai_status_indicator()

            AISettingsDialog(self.root, self.config, on_settings_save)
        except ImportError:
            messagebox.showinfo(
                "AI Settings",
                "AI settings dialog not available. Please check your installation.",
            )

    def open_data_validation(self):
        """Open data validation dialog"""
        try:
            from views.data_validation_dialog import DataValidationDialog
            DataValidationDialog(self.root, self.config)
        except ImportError as e:
            messagebox.showinfo(
                "Data Validation",
                "Data validation dialog not available. Please check your installation.",
            )

    def setup_atc_tab(self):
        """Set up the AI ATC tab with realistic, session-based training workflow"""
        
        # --- Main Split Frame (3 columns) ---
        main_frame = ttk.Frame(self.atc_tab, padding=5)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Left Panel: Session Setup & Controls
        left_frame = ttk.Frame(main_frame, width=250)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 5))
        left_frame.pack_propagate(False)

        # Center Panel: Communication (Main Focus)
        center_frame = ttk.Frame(main_frame)
        center_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

        # Right Panel: Information & Assessment
        right_frame = ttk.Frame(main_frame, width=280)
        right_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(5, 0))
        right_frame.pack_propagate(False)

        # ===== LEFT PANEL: Session Setup & Controls =====
        
        # Session Controls Section
        session_frame = ttk.LabelFrame(left_frame, text="Session Controls", padding=5)
        session_frame.pack(fill=tk.X, pady=(0, 10))

        self.session_status_label = ttk.Label(
            session_frame, text="Status: Inactive", font=("Arial", 9, "bold"), foreground="gray"
        )
        self.session_status_label.pack(anchor=tk.W, pady=(0, 5))

        self.start_session_btn = ttk.Button(
            session_frame,
            text="Start Training Session",
            command=self.start_training_session,
        )
        self.start_session_btn.pack(fill=tk.X, pady=(0, 5))

        self.end_session_btn = ttk.Button(
            session_frame,
            text="End Session",
            command=self.end_training_session,
            state=tk.DISABLED,
        )
        self.end_session_btn.pack(fill=tk.X)

        # Scenario Selection Section
        scenario_frame = ttk.LabelFrame(left_frame, text="Scenario Selection", padding=5)
        scenario_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(scenario_frame, text="Scenario:").pack(anchor=tk.W, pady=(0, 2))
        self.scenario_var = tk.StringVar()
        self.scenario_combo = ttk.Combobox(
            scenario_frame,
            textvariable=self.scenario_var,
            state="readonly",
            width=22,
        )
        self.scenario_combo.pack(fill=tk.X, pady=(0, 5))
        self.scenario_combo.bind("<<ComboboxSelected>>", self.on_scenario_select)

        # Scenario filters
        filter_frame = ttk.Frame(scenario_frame)
        filter_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(filter_frame, text="Difficulty:").pack(anchor=tk.W)
        self.difficulty_filter_var = tk.StringVar(value="All")
        difficulty_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.difficulty_filter_var,
            values=["All", "Beginner", "Intermediate", "Advanced", "Expert"],
            state="readonly",
            width=15,
        )
        difficulty_combo.pack(fill=tk.X, pady=(0, 5))
        difficulty_combo.bind("<<ComboboxSelected>>", lambda e: self.update_scenario_list())

        ttk.Label(filter_frame, text="Type:").pack(anchor=tk.W)
        self.type_filter_var = tk.StringVar(value="All")
        type_combo = ttk.Combobox(
            filter_frame,
            textvariable=self.type_filter_var,
            values=["All", "Normal Operations", "Traffic Management", "Emergency", "Weather"],
            state="readonly",
            width=15,
        )
        type_combo.pack(fill=tk.X, pady=(0, 5))
        type_combo.bind("<<ComboboxSelected>>", lambda e: self.update_scenario_list())

        # Scenario description
        ttk.Label(scenario_frame, text="Description:").pack(anchor=tk.W, pady=(5, 2))
        self.scenario_description = scrolledtext.ScrolledText(
            scenario_frame, height=4, wrap=tk.WORD, font=("Arial", 8), state=tk.DISABLED
        )
        self.scenario_description.pack(fill=tk.X, pady=(0, 5))

        # Aircraft Information Section
        aircraft_frame = ttk.LabelFrame(left_frame, text="Commercial Aircraft Information", padding=5)
        aircraft_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(aircraft_frame, text="Callsign (e.g., SIA123, AK456):").pack(anchor=tk.W, pady=(0, 2))
        # Default to commercial callsign format (e.g., "Singapore 123")
        self.callsign_var = tk.StringVar(value="SIA123")
        callsign_entry = ttk.Entry(aircraft_frame, textvariable=self.callsign_var, width=20)
        callsign_entry.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(aircraft_frame, text="Aircraft Type:").pack(anchor=tk.W, pady=(0, 2))
        # Default to commercial short-haul aircraft
        self.aircraft_type_var = tk.StringVar(value="A320")
        # Use combobox for common commercial aircraft types
        self.aircraft_type_combo = ttk.Combobox(
            aircraft_frame,
            textvariable=self.aircraft_type_var,
            values=["A320", "A321", "A319", "B737-800", "B737-900", "B737-700", "A320neo", "B737 MAX 8"],
            state="readonly",
            width=17
        )
        self.aircraft_type_combo.pack(fill=tk.X)

        # AI Status
        ai_status_frame = ttk.Frame(left_frame)
        ai_status_frame.pack(fill=tk.X, pady=(10, 0))
        self.ai_status_label = ttk.Label(
            ai_status_frame, text="🤖 AI: Checking...", font=("Arial", 8), foreground="gray"
        )
        self.ai_status_label.pack(anchor=tk.W)

        # ===== CENTER PANEL: Communication =====
        
        # Communication Log (Large, prominent)
        comm_label_frame = ttk.Frame(center_frame)
        comm_label_frame.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(comm_label_frame, text="ATC Communication Log", font=("Arial", 10, "bold")).pack(side=tk.LEFT)
        
        self.communication_log = scrolledtext.ScrolledText(
            center_frame, wrap=tk.WORD, font=("Consolas", 10), state=tk.DISABLED
        )
        self.communication_log.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Configure text tags for styling
        self.communication_log.tag_config("atc", foreground="blue", font=("Consolas", 10, "bold"))
        self.communication_log.tag_config("pilot", foreground="green", font=("Consolas", 10))
        self.communication_log.tag_config("timestamp", foreground="gray", font=("Consolas", 8))
        self.communication_log.tag_config("error", foreground="red", font=("Consolas", 9))

        # Input Area
        input_label_frame = ttk.Frame(center_frame)
        input_label_frame.pack(fill=tk.X, pady=(0, 2))
        ttk.Label(input_label_frame, text="Your Transmission:", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        
        self.pilot_input = scrolledtext.ScrolledText(
            center_frame, height=3, wrap=tk.WORD, font=("Consolas", 10)
        )
        self.pilot_input.pack(fill=tk.X, pady=(0, 5))
        self.pilot_input.bind("<Control-Return>", lambda e: self.transmit_message())

        # Transmit button
        transmit_frame = ttk.Frame(center_frame)
        transmit_frame.pack(fill=tk.X)
        self.transmit_btn = ttk.Button(
            transmit_frame,
            text="Transmit (Ctrl+Enter)",
            command=self.transmit_message,
            state=tk.DISABLED,
        )
        self.transmit_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.clear_log_btn = ttk.Button(
            transmit_frame,
            text="Clear Log",
            command=self.clear_communication_log,
        )
        self.clear_log_btn.pack(side=tk.LEFT)

        # ===== RIGHT PANEL: Information & Assessment =====
        
        # Current Situation Section
        situation_frame = ttk.LabelFrame(right_frame, text="Current Situation", padding=5)
        situation_frame.pack(fill=tk.X, pady=(0, 10))

        self.situation_info = scrolledtext.ScrolledText(
            situation_frame, height=6, wrap=tk.WORD, font=("Arial", 8), state=tk.DISABLED
        )
        self.situation_info.pack(fill=tk.X)

        # Real-time Assessment Section
        assessment_frame = ttk.LabelFrame(right_frame, text="Real-time Assessment", padding=5)
        assessment_frame.pack(fill=tk.X, pady=(0, 10))

        # Current score
        score_frame = ttk.Frame(assessment_frame)
        score_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(score_frame, text="Current Score:", font=("Arial", 9)).pack(side=tk.LEFT)
        self.current_score_label = ttk.Label(
            score_frame, text="--", font=("Arial", 12, "bold"), foreground="gray"
        )
        self.current_score_label.pack(side=tk.RIGHT)

        # Recent errors
        ttk.Label(assessment_frame, text="Recent Feedback:", font=("Arial", 9)).pack(anchor=tk.W, pady=(5, 2))
        self.assessment_feedback = scrolledtext.ScrolledText(
            assessment_frame, height=5, wrap=tk.WORD, font=("Arial", 8), state=tk.DISABLED
        )
        self.assessment_feedback.pack(fill=tk.X, pady=(0, 5))

        # Response time indicator
        self.response_time_label = ttk.Label(
            assessment_frame, text="Response Time: --", font=("Arial", 8), foreground="gray"
        )
        self.response_time_label.pack(anchor=tk.W)

        # Session Summary Section
        summary_frame = ttk.LabelFrame(right_frame, text="Session Summary", padding=5)
        summary_frame.pack(fill=tk.BOTH, expand=True)

        self.session_summary = scrolledtext.ScrolledText(
            summary_frame, wrap=tk.WORD, font=("Arial", 8), state=tk.DISABLED
        )
        self.session_summary.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        self.view_progress_btn = ttk.Button(
            summary_frame,
            text="View Progress",
            command=self.view_progress,
            state=tk.DISABLED,
        )
        self.view_progress_btn.pack(fill=tk.X)
        self.save_debrief_btn = ttk.Button(
            summary_frame,
            text="Save Last Debrief",
            command=self.save_last_debrief,
        )
        self.save_debrief_btn.pack(fill=tk.X, pady=(5, 0))

        # Initialize scenario list and available scenarios dict
        self.available_scenarios = {}
        self.update_scenario_list()
        self.update_situation_info()
        self.update_session_summary()
        
        # Update AI status
        self.root.after(500, self.update_ai_status_indicator)

    def update_scenario_list(self):
        """Update the scenario dropdown list based on filters"""
        if not self.scenario_engine:
            return
        
        # Get filter values
        difficulty_filter = self.difficulty_filter_var.get()
        type_filter = self.type_filter_var.get()
        
        # Get all scenarios
        scenarios = self.scenario_engine.get_all_scenarios()
        
        # Apply filters
        filtered_scenarios = []
        for scenario in scenarios:
            # Difficulty filter
            if difficulty_filter != "All":
                difficulty_map = {
                    "Beginner": DifficultyLevel.BEGINNER,
                    "Intermediate": DifficultyLevel.INTERMEDIATE,
                    "Advanced": DifficultyLevel.ADVANCED,
                    "Expert": DifficultyLevel.EXPERT
                }
                if scenario.difficulty != difficulty_map.get(difficulty_filter):
                    continue
            
            # Type filter
            if type_filter != "All":
                type_map = {
                    "Normal Operations": ScenarioType.NORMAL_OPERATIONS,
                    "Traffic Management": ScenarioType.TRAFFIC_MANAGEMENT,
                    "Emergency": ScenarioType.EMERGENCY,
                    "Weather": ScenarioType.WEATHER
                }
                if scenario.scenario_type != type_map.get(type_filter):
                    continue
            
            filtered_scenarios.append(scenario)
        
        # Update combo box
        scenario_names = [f"{s.name} ({s.airport_icao})" for s in filtered_scenarios]
        self.scenario_combo['values'] = scenario_names
        
        # Store scenarios for lookup
        self.available_scenarios = {f"{s.name} ({s.airport_icao})": s for s in filtered_scenarios}
        
        if scenario_names and not self.scenario_var.get():
            self.scenario_combo.current(0)
            self.on_scenario_select(None)

    def on_scenario_select(self, event=None):
        """Handle scenario selection"""
        scenario_name = self.scenario_var.get()
        if not scenario_name or scenario_name not in self.available_scenarios:
            return
        
        scenario = self.available_scenarios[scenario_name]
        self.current_scenario = scenario
        
        # Update description
        self.scenario_description.config(state=tk.NORMAL)
        self.scenario_description.delete(1.0, tk.END)
        desc_text = f"{scenario.description}\n\n"
        desc_text += f"Difficulty: {scenario.difficulty.value.title()}\n"
        desc_text += f"Type: {scenario.scenario_type.value.replace('_', ' ').title()}\n"
        if scenario.objectives:
            desc_text += f"\nObjectives:\n"
            for obj in scenario.objectives:
                desc_text += f"• {obj}\n"
        self.scenario_description.insert(1.0, desc_text)
        self.scenario_description.config(state=tk.DISABLED)
        
        # Update airport selection
        if scenario.airport_icao:
            for airport_name, airport_data in self.airports.items():
                if airport_data.get('icao') == scenario.airport_icao:
                    if hasattr(self, 'airport_var'):
                        self.airport_var.set(airport_name)
                    break
        
        # Update situation info
        self.update_situation_info()

    def start_training_session(self):
        """Start a new training session"""
        if not self.current_scenario:
            messagebox.showwarning("No Scenario", "Please select a scenario first.")
            return
        
        if not self.ai_handler or not self.ai_handler.is_ai_available():
            messagebox.showwarning("AI Not Available", "AI ATC is not available. Please check your Ollama connection.")
            return
        
        # Reset assessment engine for new session
        if self.assessment_engine:
            self.assessment_engine.reset_session()
        
        # Start session with progress tracker
        if self.progress_tracker:
            pilot_id = self.callsign_var.get() or "PILOT"
            session_id = self.progress_tracker.start_session(
                pilot_id=pilot_id,
                scenario_id=self.current_scenario.scenario_id,
                airport_icao=self.current_scenario.airport_icao,
                difficulty=self.current_scenario.difficulty.value,
                metadata={
                    "aircraft_type": self.aircraft_type_var.get(),
                    "scenario_name": self.current_scenario.name
                }
            )
        
        # Set session state
        self.current_session_active = True
        self.session_start_time = time.time()
        
        # Initialize objective tracking
        self.completed_objectives = set()
        self.completed_communications = set()
        self.scenario_objectives = self.current_scenario.objectives if self.current_scenario else []
        self.scenario_expected_communications = self.current_scenario.expected_communications if self.current_scenario else []
        
        # Update UI
        self.session_status_label.config(text="Status: Active", foreground="green")
        self.start_session_btn.config(state=tk.DISABLED)
        self.end_session_btn.config(state=tk.NORMAL)
        self.scenario_combo.config(state=tk.DISABLED)
        self.aircraft_type_combo.config(state="disabled")  # Lock aircraft type for the session
        self.transmit_btn.config(state=tk.NORMAL)
        self.view_progress_btn.config(state=tk.NORMAL)
        
        # Clear communication log
        self.communication_log.config(state=tk.NORMAL)
        self.communication_log.delete(1.0, tk.END)
        self.communication_log.config(state=tk.DISABLED)
        
        # Initialize scenario - get initial ATC message
        self._initialize_scenario()
        
        # Update session summary and situation info (to show objectives)
        self.update_session_summary()
        self.update_situation_info()
        
        self.status_var.set("Status: Training session started")

    def _initialize_scenario(self):
        """Initialize the scenario with initial ATC communication"""
        if not self.current_scenario or not self.ai_handler:
            return
        
        # Get airport info
        airport_name = None
        for name, data in self.airports.items():
            if data.get('icao') == self.current_scenario.airport_icao:
                airport_name = name
                break
        
        airport_info = self.airports.get(airport_name, {})
        
        # Add weather info from scenario
        if self.current_scenario.weather:
            airport_info['weather'] = {
                'wind': f"{self.current_scenario.weather.wind_direction:03d}@{self.current_scenario.weather.wind_speed}",
                'visibility': self.current_scenario.weather.visibility,
                'ceiling': self.current_scenario.weather.ceiling,
                'qnh': self.current_scenario.weather.qnh
            }
        
        # Generate initial ATC greeting/scenario setup
        initial_prompt = f"Initialize scenario: {self.current_scenario.description}. Airport: {self.current_scenario.airport_icao}."
        
        aircraft_info = {
            'callsign': self.callsign_var.get() or "PILOT",
            'aircraft_type': self.aircraft_type_var.get() or "Aircraft"
        }
        
        # Generate initial ATC message
        initial_response = self.ai_handler.generate_atc_response(
            pilot_message=initial_prompt,
            aircraft_info=aircraft_info,
            airport_info=airport_info,
            response_type="scenario_init"
        )
        
        # Display initial message
        self._log_atc_message(initial_response)
        self.last_atc_message = initial_response
        self.last_atc_timestamp = time.time()

    def end_training_session(self):
        """End the current training session"""
        if not self.current_session_active:
            return
        
        # Calculate final assessment
        final_assessment = None
        completed_session_id = None
        if self.progress_tracker and self.progress_tracker.current_session:
            # Get final assessment
            if self.assessment_engine:
                try:
                    # Assess overall session (uses internal communication_history)
                    final_assessment = self.assessment_engine.assess_session()
                    completed_session_id = self.progress_tracker.complete_session(final_assessment)
                except Exception as e:
                    # Log error but don't crash the session end
                    logger.warning("Failed to assess session: %s", e)
                    # Create a minimal assessment result
                    from assessment.assessment_engine import AssessmentResult
                    final_assessment = AssessmentResult(
                        score=0.0,
                        errors=[],
                        strengths=[],
                        recommendations=["Assessment could not be completed due to an error"]
                    )
                    try:
                        completed_session_id = self.progress_tracker.complete_session(final_assessment)
                    except Exception as e2:
                        logger.warning("Failed to complete session: %s", e2)
                finally:
                    # Reset assessment engine for next session
                    self.assessment_engine.reset_session()
        
        # Reset session state
        self.current_session_active = False
        self.session_start_time = None
        
        # Reset objective tracking
        self.completed_objectives = set()
        self.completed_communications = set()
        self.scenario_objectives = []
        self.scenario_expected_communications = []
        
        # Update UI
        self.session_status_label.config(text="Status: Inactive", foreground="gray")
        self.start_session_btn.config(state=tk.NORMAL)
        self.end_session_btn.config(state=tk.DISABLED)
        self.scenario_combo.config(state="readonly")
        self.aircraft_type_combo.config(state="readonly")  # Unlock aircraft type after session
        self.transmit_btn.config(state=tk.DISABLED)
        
        # Show session summary and update situation info
        self.update_session_summary()
        self.update_situation_info()
        
        debrief_text = "Training session completed. Check the Session Summary for results."
        if completed_session_id and self.report_generator and self.progress_tracker:
            session_report = self.report_generator.generate_session_report(completed_session_id)
            pilot_id = self.callsign_var.get().strip() or "PILOT"
            progress_report = self.report_generator.generate_pilot_progress_report(pilot_id, days=30)
            focus_area = "Readback accuracy and phraseology discipline"
            if final_assessment and getattr(final_assessment, "score", 0) >= 85:
                focus_area = "Maintain consistency under workload and reduce response delay"
            debrief_text = self.report_generator.generate_trainee_debrief(
                role="Pilot",
                session_report=session_report,
                progress_report=progress_report,
                extra_metrics={
                    "focus_area": focus_area,
                    "insight": f"Scenario: {self.current_scenario.name if self.current_scenario else 'Unknown'}",
                },
            )
            self.last_debrief_text = debrief_text
            self.last_debrief_path = self._autosave_debrief("pilot", completed_session_id, debrief_text)
            if self.last_debrief_path:
                debrief_text += f"\n\nSaved debrief: {self.last_debrief_path}"

        messagebox.showinfo("Session Ended Debrief", debrief_text)
        self.status_var.set("Status: Training session ended")

    def _autosave_debrief(self, role, session_id, debrief_text):
        """Auto-save debrief to training records folder."""
        if not self.report_generator or not self.progress_tracker:
            return ""
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        filename = f"debrief_{role}_{session_id[:8]}_{timestamp}.txt"
        output_path = os.path.join(self.progress_tracker.data_dir, "debriefs", filename)
        if self.report_generator.export_debrief_text(debrief_text, output_path):
            return output_path
        return ""

    def save_last_debrief(self):
        """Save the most recent pilot debrief to a custom path."""
        if not self.last_debrief_text:
            messagebox.showinfo("No Debrief", "No debrief available yet. Complete a session first.")
            return
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            title="Save Pilot Debrief",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not filename:
            return
        if self.report_generator and self.report_generator.export_debrief_text(self.last_debrief_text, filename):
            self.status_var.set(f"Status: Debrief saved to {filename}")
        else:
            messagebox.showerror("Save Error", "Failed to save debrief.")

    def transmit_message(self):
        """Transmit pilot message and get ATC response"""
        if not self.current_session_active:
            messagebox.showwarning("No Active Session", "Please start a training session first.")
            return
        
        pilot_message = self.pilot_input.get(1.0, tk.END).strip()
        if not pilot_message:
            return
        
        # Calculate response time
        response_time = None
        if self.last_atc_timestamp:
            response_time = time.time() - self.last_atc_timestamp
        
        # Log pilot message
        self._log_pilot_message(pilot_message)
        
        # Clear input
        self.pilot_input.delete(1.0, tk.END)
        
        # Assess the pilot message
        assessment_result = None
        previous_atc_message = self.last_atc_message  # Store the ATC message being read back
        
        if self.assessment_engine and previous_atc_message:
            assessment_result = self.assessment_engine.assess_communication(
                instruction=previous_atc_message,
                readback=pilot_message
            )
            
            # Update assessment display
            self._update_assessment_display(assessment_result, response_time)
            
            # Record in progress tracker
            if self.progress_tracker:
                self.progress_tracker.add_communication(
                    instruction=previous_atc_message,
                    readback=pilot_message,
                    assessment_result=assessment_result,
                    response_time=response_time
                )
        
        # Check for objective completion with the pilot's readback and previous ATC message
        # This checks if the pilot properly read back the previous instruction
        if previous_atc_message:
            self._check_objective_completion(pilot_message, previous_atc_message)
            # Update UI immediately after checking
            self.update_situation_info()
            
            # Check if all objectives are complete after pilot readback
            if self._are_all_objectives_complete():
                self.communication_log.config(state=tk.NORMAL)
                self.communication_log.insert(tk.END, "\n[SYSTEM] ", "timestamp")
                self.communication_log.insert(tk.END, "✓ Scenario objectives completed! Session ending...\n\n", "atc")
                self.communication_log.see(tk.END)
                self.communication_log.config(state=tk.DISABLED)
                # Auto-end the session
                self.end_training_session()
                return
        
        # Generate AI ATC response
        self.show_ai_processing("AI ATC is responding...")
        
        try:
            # Get airport info
            airport_name = None
            if self.current_scenario:
                for name, data in self.airports.items():
                    if data.get('icao') == self.current_scenario.airport_icao:
                        airport_name = name
                        break
            
            airport_info = self.airports.get(airport_name, {})
            
            aircraft_info = {
                'callsign': self.callsign_var.get() or "PILOT",
                'aircraft_type': self.aircraft_type_var.get() or "Aircraft"
            }
            
            # Add scenario context
            if self.current_scenario:
                airport_info['scenario'] = {
                    'type': self.current_scenario.scenario_type.value,
                    'difficulty': self.current_scenario.difficulty.value,
                    'name': self.current_scenario.name,
                    'description': self.current_scenario.description,
                    'objectives': self.current_scenario.objectives
                }
                # Add weather info from scenario if not already present
                if self.current_scenario.weather and 'weather' not in airport_info:
                    airport_info['weather'] = {
                        'wind': f"{self.current_scenario.weather.wind_direction:03d}@{self.current_scenario.weather.wind_speed}",
                        'visibility': self.current_scenario.weather.visibility,
                        'ceiling': self.current_scenario.weather.ceiling,
                        'qnh': self.current_scenario.weather.qnh
                    }
            
            atc_response = self.ai_handler.generate_atc_response(
                pilot_message=pilot_message,
                aircraft_info=aircraft_info,
                airport_info=airport_info,
                response_type="atc_response"
            )
            
            # Log ATC response
            self._log_atc_message(atc_response)
            self.last_atc_message = atc_response
            self.last_atc_timestamp = time.time()
            
            # Check for objective completion with new ATC response
            # This checks if the pilot's request matches objectives
            # self._check_objective_completion(pilot_message, atc_response)
            self._check_object_completion_with_ollama(pilot_message, atc_response)
            
            # Update UI after new ATC response
            self.update_situation_info()
            
            # Check if all objectives are complete after ATC response
            if self._are_all_objectives_complete():
                self.communication_log.config(state=tk.NORMAL)
                self.communication_log.insert(tk.END, "\n[SYSTEM] ", "timestamp")
                self.communication_log.insert(tk.END, "✓ Scenario objectives completed! Session ending...\n\n", "atc")
                self.communication_log.see(tk.END)
                self.communication_log.config(state=tk.DISABLED)
                # Auto-end the session
                self.end_training_session()
                return
            
            # Update session summary
            self.update_session_summary()
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to get ATC response: {str(e)}")
        finally:
            self.hide_ai_processing()

    def _log_atc_message(self, message: str):
        """Log an ATC message to the communication log"""
        self.communication_log.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.communication_log.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.communication_log.insert(tk.END, f"ATC: {message}\n\n", "atc")
        self.communication_log.see(tk.END)
        self.communication_log.config(state=tk.DISABLED)

    def _log_pilot_message(self, message: str):
        """Log a pilot message to the communication log"""
        self.communication_log.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.communication_log.insert(tk.END, f"[{timestamp}] ", "timestamp")
        self.communication_log.insert(tk.END, f"PILOT: {message}\n\n", "pilot")
        self.communication_log.see(tk.END)
        self.communication_log.config(state=tk.DISABLED)

    def _update_assessment_display(self, assessment_result, response_time: float = None):
        """Update the real-time assessment display"""
        if not assessment_result:
            return
        
        # Update score
        score_color = "green" if assessment_result.score >= 80 else "orange" if assessment_result.score >= 60 else "red"
        self.current_score_label.config(
            text=f"{assessment_result.score:.0f}/100",
            foreground=score_color
        )
        
        # Update feedback
        self.assessment_feedback.config(state=tk.NORMAL)
        self.assessment_feedback.delete(1.0, tk.END)
        
        if assessment_result.errors:
            self.assessment_feedback.insert(tk.END, "Errors:\n", "error")
            for error in assessment_result.errors[:3]:  # Show last 3 errors
                self.assessment_feedback.insert(tk.END, f"• {error.message}\n", "error")
            self.assessment_feedback.insert(tk.END, "\n")
        
        if assessment_result.strengths:
            self.assessment_feedback.insert(tk.END, "Strengths:\n")
            for strength in assessment_result.strengths[:2]:  # Show top 2 strengths
                self.assessment_feedback.insert(tk.END, f"✓ {strength}\n")
        
        self.assessment_feedback.config(state=tk.DISABLED)
        
        # Update response time
        if response_time:
            time_text = f"Response Time: {response_time:.1f}s"
            time_color = "green" if response_time < 5.0 else "orange" if response_time < 10.0 else "red"
            self.response_time_label.config(text=time_text, foreground=time_color)

    def clear_communication_log(self):
        """Clear the communication log"""
        if messagebox.askyesno("Clear Log", "Are you sure you want to clear the communication log?"):
            self.communication_log.config(state=tk.NORMAL)
            self.communication_log.delete(1.0, tk.END)
            self.communication_log.config(state=tk.DISABLED)

    def update_situation_info(self):
        """Update the current situation information display"""
        self.situation_info.config(state=tk.NORMAL)
        self.situation_info.delete(1.0, tk.END)
        
        if self.current_scenario:
            scenario = self.current_scenario
            info_text = f"Airport: {scenario.airport_icao}\n"
            info_text += f"Scenario: {scenario.name}\n\n"
            
            if scenario.weather:
                w = scenario.weather
                info_text += f"Weather:\n"
                info_text += f"Wind: {w.wind_direction:03d}@{w.wind_speed} kts\n"
                info_text += f"Visibility: {w.visibility}\n"
                info_text += f"Ceiling: {w.ceiling}\n"
                info_text += f"QNH: {w.qnh}\n\n"
            
            if scenario.traffic_aircraft:
                info_text += f"Traffic: {len(scenario.traffic_aircraft)} aircraft\n\n"
            
            # Show objective progress if session is active
            if self.current_session_active and self.scenario_objectives:
                completed_count = len(self.completed_objectives)
                total_count = len(self.scenario_objectives)
                info_text += f"Objectives: {completed_count}/{total_count} completed\n\n"
                
                # List objectives with completion status
                for objective in self.scenario_objectives:
                    status = "✓" if objective in self.completed_objectives else "○"
                    info_text += f"{status} {objective}\n"
        else:
            info_text = "No scenario selected.\nSelect a scenario to begin."
        
        self.situation_info.insert(1.0, info_text)
        self.situation_info.config(state=tk.DISABLED)

    def _check_objective_completion(self, pilot_message: str, atc_response: str):
        """Check if communications match objectives and expected communications"""
        if not self.current_scenario or not self.scenario_objectives:
            return
        
        pilot_lower = pilot_message.lower()
        atc_lower = atc_response.lower()
        combined_text = f"{pilot_lower} {atc_lower}"
        
        # Check expected communications
        for expected_comm in self.scenario_expected_communications:
            if expected_comm.lower() in combined_text:
                self.completed_communications.add(expected_comm)
        
        # Check objectives by matching keywords - more flexible matching
        objective_keywords = {
            "request taxi clearance": {
                "pilot": [("request", "taxi"), ("taxi", "clearance")],
                "atc": [("taxi", "cleared"), ("taxi", "approved"), ("cleared", "taxi")]
            },
            "follow taxi instructions": {
                "pilot": [("taxi", "via"), ("taxi", "taxiway"), ("roger", "taxi")],
                "atc": [("taxi", "via"), ("taxi", "taxiway"), ("taxi", "to")]
            },
            "request takeoff clearance": {
                "pilot": [("request", "takeoff"), ("takeoff", "clearance"), ("ready", "takeoff")],
                "atc": [("cleared", "takeoff"), ("takeoff", "cleared")]
            },
            "execute proper readbacks": {
                "pilot": [("roger",), ("wilco",), ("cleared", "takeoff"), ("cleared", "land"), ("cleared", "taxi")],
                "atc": []  # Readbacks are in pilot messages
            },
            "request landing clearance": {
                "pilot": [("request", "landing"), ("landing", "clearance"), ("ready", "landing")],
                "atc": [("cleared", "land"), ("landing", "cleared")]
            },
            "follow approach instructions": {
                "pilot": [("roger", "approach"), ("wilco", "approach")],
                "atc": [("cleared", "approach"), ("approach", "cleared"), ("follow", "approach")]
            },
            "maintain proper altitude": {
                "pilot": [("maintain", "altitude"), ("maintain", "flight"), ("climb", "maintain"), ("descend", "maintain")],
                "atc": [("maintain", "altitude"), ("maintain", "flight"), ("climb", "maintain"), ("descend", "maintain")]
            },
            "handle traffic": {
                "pilot": [("traffic", "sight"), ("traffic", "in"), ("following",)],
                "atc": [("traffic",), ("following",)]
            },
            "communicate with ground": {
                "pilot": [("ground",), ("contact", "ground")],
                "atc": [("contact", "ground"), ("ground", "on")]
            },
            "communicate with tower": {
                "pilot": [("tower",), ("contact", "tower")],
                "atc": [("contact", "tower"), ("tower", "on")]
            },
            "communicate with approach": {
                "pilot": [("approach",), ("contact", "approach")],
                "atc": [("contact", "approach"), ("approach", "on")]
            },
        }
        
        objectives_changed = False
        
        for objective in self.scenario_objectives:
            if objective in self.completed_objectives:
                continue
            
            objective_lower = objective.lower()
            is_complete = False
            
            # Check if objective has specific keyword patterns
            if objective_lower in objective_keywords:
                patterns = objective_keywords[objective_lower]
                
                # Check pilot message patterns
                for pattern_list in patterns.get("pilot", []):
                    if all(keyword in pilot_lower for keyword in pattern_list):
                        is_complete = True
                        break
                
                # Check ATC message patterns (if not already complete)
                if not is_complete:
                    for pattern_list in patterns.get("atc", []):
                        if all(keyword in atc_lower for keyword in pattern_list):
                            # For ATC patterns, also check if pilot acknowledged
                            if any(ack in pilot_lower for ack in ["roger", "wilco", "affirmative"]):
                                is_complete = True
                                break
                
                # Special handling for readbacks - check if pilot read back ATC instructions
                if objective_lower == "execute proper readbacks" and not is_complete:
                    # Check if pilot message contains key elements from ATC message
                    atc_keywords = []
                    if "cleared" in atc_lower:
                        atc_keywords.append("cleared")
                    if "runway" in atc_lower:
                        atc_keywords.append("runway")
                    if "taxi" in atc_lower:
                        atc_keywords.append("taxi")
                    if "takeoff" in atc_lower:
                        atc_keywords.append("takeoff")
                    if "land" in atc_lower or "landing" in atc_lower:
                        atc_keywords.append("land")
                    if "maintain" in atc_lower or "climb" in atc_lower or "descend" in atc_lower:
                        atc_keywords.append("maintain")
                    
                    # If pilot message contains at least 2 key elements from ATC, it's a readback
                    if len(atc_keywords) >= 2 and sum(1 for kw in atc_keywords if kw in pilot_lower) >= 2:
                        is_complete = True
                
            else:
                # Generic matching: check if key words from objective are in communications
                objective_words = [w for w in objective_lower.split() if len(w) > 3]
                if objective_words:
                    # Check if at least 50% of significant words match
                    matches = sum(1 for word in objective_words if word in combined_text)
                    if matches >= len(objective_words) * 0.5:
                        is_complete = True
            
            if is_complete:
                self.completed_objectives.add(objective)
                objectives_changed = True
        
        # Update UI immediately if objectives changed
        if objectives_changed:
            self.update_situation_info()


    def _check_object_completion_with_ollama(self, pilot_message: str, atc_response: str):
        """
        Check if communications match objectives and expected communications using Ollama LLM for objective completion logic.
        Falls back to local detection if Ollama is unavailable or times out.
        """
        if not self.current_scenario or not self.scenario_objectives:
            return

        # Check expected communications first (fast lookup, no API needed)
        pilot_lower = pilot_message.lower()
        atc_lower = atc_response.lower()
        combined_text = f"{pilot_lower} {atc_lower}"

        for expected_comm in self.scenario_expected_communications:
            if expected_comm.lower() in combined_text:
                self.completed_communications.add(expected_comm)

        # Get pending objectives (not yet completed)
        pending_objectives = [obj for obj in self.scenario_objectives if obj not in self.completed_objectives]
        
        if not pending_objectives:
            # All objectives already complete, just update UI
            self.update_situation_info()
            return

        # Try to use Ollama if available, but fallback to local detection
        use_ollama = False
        try:
            import requests
            # Quick check if Ollama is available (non-blocking)
            test_response = requests.get("http://localhost:11434/api/tags", timeout=2)
            if test_response.status_code == 200:
                use_ollama = True
        except (ImportError, Exception):
            # Ollama not available or not responding, use local detection
            use_ollama = False

        objectives_changed = False

        if use_ollama:
            # Batch all objectives into a single prompt for efficiency
            objectives_list = "\n".join([f"- {obj}" for obj in pending_objectives])
            
            prompt = f"""You are a proficient ATC simulator evaluator. Analyze the following communication and determine which objectives are met.

Conversation:
PILOT: {pilot_message}
ATC: {atc_response}

Objectives to check:
{objectives_list}

For each objective, respond with "true" if met, "false" if not met.
Respond with ONLY a comma-separated list of true/false values in the same order as the objectives.
Example: true,false,true,false
"""

            ollama_data = {
                "model": self.config.get("ai_model", "llama3"),
                "prompt": prompt.strip(),
                "options": {
                    "temperature": 0.0,
                    "num_predict": 50  # Limit response length
                }
            }

            try:
                response = requests.post(
                    f"{self.config.get('ollama_url', 'http://localhost:11434')}/api/generate",
                    json=ollama_data,
                    timeout=15  # Increased timeout
                )
                response.raise_for_status()
                content = response.json().get("response", "").strip().lower()
                
                # Parse the comma-separated true/false responses
                results = [r.strip() for r in content.split(",")]
                
                # Match results to objectives
                for i, objective in enumerate(pending_objectives):
                    if i < len(results) and results[i].startswith("true"):
                        self.completed_objectives.add(objective)
                        objectives_changed = True
                        
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError, requests.exceptions.RequestException) as ex:
                # Timeout or connection error - fallback to local detection
                logger.debug("Ollama API unavailable (timeout/error), using local detection: %s", ex)
                use_ollama = False  # Trigger fallback
            except Exception as ex:
                # Other errors - fallback to local detection
                logger.debug("Ollama API error, using local detection: %s", ex)
                use_ollama = False  # Trigger fallback

        # Fallback to local detection if Ollama failed or unavailable
        if not use_ollama:
            # Use the original local detection method
            self._check_objective_completion(pilot_message, atc_response)
            objectives_changed = True  # Local method updates UI itself

        # Update UI if objectives changed (only if we used Ollama)
        if objectives_changed and use_ollama:
            self.update_situation_info()
            
    def _are_all_objectives_complete(self) -> bool:
        """Check if all scenario objectives have been completed"""
        if not self.current_scenario or not self.scenario_objectives:
            return False  # No objectives means manual end only
        
        # Check if all objectives are completed
        return len(self.completed_objectives) >= len(self.scenario_objectives)

    def update_session_summary(self):
        """Update the session summary display"""
        self.session_summary.config(state=tk.NORMAL)
        self.session_summary.delete(1.0, tk.END)
        
        if self.current_session_active and self.progress_tracker and self.progress_tracker.current_session:
            session = self.progress_tracker.current_session
            elapsed_time = time.time() - self.session_start_time if self.session_start_time else 0
            
            summary_text = f"Session: {session.session_id[:8]}...\n"
            summary_text += f"Time Elapsed: {int(elapsed_time // 60)}m {int(elapsed_time % 60)}s\n"
            summary_text += f"Communications: {len(session.communications)}\n"
            
            if session.communications:
                avg_score = sum(c.score for c in session.communications) / len(session.communications)
                summary_text += f"Average Score: {avg_score:.1f}/100\n"
            summary_text += f"Pilot Focus: {self._get_pilot_training_focus(session.communications)}\n"
        else:
            summary_text = "No active session.\nStart a training session to begin."
        
        self.session_summary.insert(1.0, summary_text)
        self.session_summary.config(state=tk.DISABLED)

    def _get_pilot_training_focus(self, communications):
        """Provide concise coaching focus for pilot training continuity."""
        if not communications:
            return "Start with accurate readbacks and concise phraseology."

        avg_score = sum(c.score for c in communications) / len(communications)
        if avg_score < 70:
            return "Readback accuracy and critical instruction confirmation."
        if avg_score < 85:
            return "Consistency in phraseology and timing under workload."
        return "Maintain standard phraseology and anticipate next clearance."

    def view_progress(self):
        """View detailed progress and reports"""
        if not self.progress_tracker:
            messagebox.showinfo("Progress Tracker", "Progress tracking is not available.")
            return
        
        # This could open a separate progress dashboard window
        messagebox.showinfo("Progress", "Progress dashboard feature coming soon. Check data/training_records/ for session files.")
        
    def setup_atis_tab(self):
        """Set up the ATIS Decoder tab"""
        # Create frames
        top_frame = ttk.Frame(self.atis_tab, padding="5")
        bottom_frame = ttk.Frame(self.atis_tab, padding="5")

        top_frame.pack(side=tk.TOP, fill=tk.X)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        # Top frame - Input
        ttk.Label(top_frame, text="ATIS Message:").pack(anchor=tk.W, pady=(0, 5))

        self.atis_input = scrolledtext.ScrolledText(top_frame, height=8, wrap=tk.WORD)
        self.atis_input.pack(fill=tk.X, pady=(0, 10))

        # Sample ATIS button
        self.sample_btn = ttk.Button(
            top_frame, text="Insert Sample ATIS", command=self.insert_sample_atis
        )
        self.sample_btn.pack(side=tk.LEFT, padx=(0, 5))

        # Decode button
        self.decode_btn = ttk.Button(
            top_frame, text="Decode ATIS", command=self.decode_atis
        )
        self.decode_btn.pack(side=tk.LEFT, padx=5)

        # Clear button
        self.clear_btn = ttk.Button(top_frame, text="Clear", command=self.clear_atis)
        self.clear_btn.pack(side=tk.LEFT, padx=5)

        # AI Generate ATIS button
        self.ai_atis_btn = ttk.Button(
            top_frame, text="Generate AI ATIS", command=self.generate_ai_atis
        )
        self.ai_atis_btn.pack(side=tk.RIGHT, padx=5)

        # Speak button
        self.speak_atis_btn = ttk.Button(
            top_frame, text="Speak ATIS", command=self.speak_atis
        )
        self.speak_atis_btn.pack(side=tk.RIGHT, padx=5)

        # Bottom frame - Results
        ttk.Label(bottom_frame, text="Decoded ATIS:").pack(anchor=tk.W, pady=(0, 5))

        self.atis_output = scrolledtext.ScrolledText(
            bottom_frame, height=10, wrap=tk.WORD
        )
        self.atis_output.pack(fill=tk.BOTH, expand=True)

    def setup_settings_tab(self):
        """Set up the Settings tab with tabbed interface"""
        # Main container frame
        main_frame = ttk.Frame(self.settings_tab, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Create notebook for tabs
        notebook = ttk.Notebook(main_frame)
        notebook.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Create tabs
        general_tab = ttk.Frame(notebook, padding=15)
        voice_tab = ttk.Frame(notebook, padding=15)
        display_tab = ttk.Frame(notebook, padding=15)
        advanced_tab = ttk.Frame(notebook, padding=15)

        notebook.add(general_tab, text="General")
        notebook.add(voice_tab, text="Voice & Audio")
        notebook.add(display_tab, text="Display")
        notebook.add(advanced_tab, text="Advanced")

        # Store variables as instance attributes for save function
        self.experience_var = tk.StringVar(value=self.config.get("experience_level"))
        self.aircraft_var = tk.StringVar(value=self.config.get("aircraft_type"))
        self.default_aircraft_var = tk.StringVar(value=self.config.get("default_aircraft_type", "A320"))
        self.voice_enabled_var = tk.BooleanVar(value=self.config.get("voice_enabled"))
        self.voice_rate_var = tk.IntVar(value=self.config.get("voice_rate"))
        self.theme_var = tk.StringVar(value=self.config.get("ui_theme"))
        self.font_size_var = tk.IntVar(value=self.config.get("font_size", 12))
        self.phraseology_region_var = tk.StringVar(value=self.config.get("phraseology_region", "US"))
        self.auto_save_notes_var = tk.BooleanVar(value=self.config.get("auto_save_notes", True))
        self.notes_directory_var = tk.StringVar(value=self.config.get("notes_directory", "atc_notes"))

        # Setup each tab
        self.setup_general_tab(general_tab)
        self.setup_voice_tab(voice_tab)
        self.setup_display_tab(display_tab)
        self.setup_advanced_tab(advanced_tab)

        # Buttons frame at bottom
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))

        ttk.Button(button_frame, text="Save Settings", command=self.save_settings).pack(
            side=tk.RIGHT, padx=(10, 0)
        )
        ttk.Button(
            button_frame, text="Reset to Defaults", command=self.reset_settings
        ).pack(side=tk.RIGHT)

    def setup_general_tab(self, parent):
        """Set up the General settings tab"""
        # Pilot Experience Level
        experience_frame = ttk.LabelFrame(parent, text="Pilot Experience Level", padding=15)
        experience_frame.pack(fill=tk.X, pady=(0, 15))

        experience_options = [
            ("Beginner", "beginner"),
            ("Intermediate", "intermediate"),
            ("Advanced", "advanced"),
        ]

        exp_container = ttk.Frame(experience_frame)
        exp_container.pack(anchor=tk.W)

        for i, (text, value) in enumerate(experience_options):
            ttk.Radiobutton(
                exp_container,
                text=text,
                variable=self.experience_var,
                value=value
            ).pack(side=tk.LEFT, padx=(0, 15))

        # Aircraft Type
        aircraft_frame = ttk.LabelFrame(parent, text="Aircraft Type", padding=15)
        aircraft_frame.pack(fill=tk.X, pady=(0, 15))

        aircraft_options = [
            ("Single Engine", "single_engine"),
            ("Multi Engine", "multi_engine"),
            ("Turboprop", "turboprop"),
            ("Jet", "jet"),
        ]

        ac_container = ttk.Frame(aircraft_frame)
        ac_container.pack(anchor=tk.W)

        for i, (text, value) in enumerate(aircraft_options):
            ttk.Radiobutton(
                ac_container,
                text=text,
                variable=self.aircraft_var,
                value=value
            ).pack(side=tk.LEFT, padx=(0, 15))

        # Default Aircraft Type
        default_aircraft_frame = ttk.LabelFrame(parent, text="Default Aircraft Type", padding=15)
        default_aircraft_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            default_aircraft_frame,
            text="Default aircraft model (e.g., A320, B737, C172):"
        ).pack(anchor=tk.W, pady=(0, 5))

        default_aircraft_entry = ttk.Entry(
            default_aircraft_frame,
            textvariable=self.default_aircraft_var,
            width=30
        )
        default_aircraft_entry.pack(anchor=tk.W)

    def setup_voice_tab(self, parent):
        """Set up the Voice & Audio settings tab"""
        # Voice Enable
        voice_enable_frame = ttk.LabelFrame(parent, text="Voice Settings", padding=15)
        voice_enable_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Checkbutton(
            voice_enable_frame,
            text="Enable voice playback for ATC instructions",
            variable=self.voice_enabled_var
        ).pack(anchor=tk.W, pady=(0, 10))

        # Voice Rate
        ttk.Label(
            voice_enable_frame,
            text="Speech Rate (words per minute):"
        ).pack(anchor=tk.W, pady=(0, 5))

        rate_container = ttk.Frame(voice_enable_frame)
        rate_container.pack(fill=tk.X, pady=(0, 5))

        self.voice_rate_label = ttk.Label(
            rate_container,
            text=str(self.voice_rate_var.get()),
            font=("Arial", 10, "bold"),
            width=5
        )
        self.voice_rate_label.pack(side=tk.LEFT, padx=(0, 10))

        voice_rate_scale = ttk.Scale(
            rate_container,
            from_=80,
            to=220,
            variable=self.voice_rate_var,
            orient=tk.HORIZONTAL,
            length=300
        )
        voice_rate_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def update_rate_label(*args):
            self.voice_rate_label.config(text=str(int(self.voice_rate_var.get())))

        self.voice_rate_var.trace_add("write", update_rate_label)

        ttk.Label(
            voice_enable_frame,
            text="80 (Slow) ————————————————— 220 (Fast)",
            font=("Arial", 8),
            foreground="gray"
        ).pack(anchor=tk.W)

    def setup_display_tab(self, parent):
        """Set up the Display settings tab"""
        # UI Theme
        theme_frame = ttk.LabelFrame(parent, text="User Interface Theme", padding=15)
        theme_frame.pack(fill=tk.X, pady=(0, 15))

        theme_options = [("Light", "light"), ("Dark", "dark")]

        theme_container = ttk.Frame(theme_frame)
        theme_container.pack(anchor=tk.W)

        for i, (text, value) in enumerate(theme_options):
            ttk.Radiobutton(
                theme_container,
                text=text,
                variable=self.theme_var,
                value=value
            ).pack(side=tk.LEFT, padx=(0, 15))

        # Font Size
        font_frame = ttk.LabelFrame(parent, text="Font Size", padding=15)
        font_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            font_frame,
            text="Base font size for the application:"
        ).pack(anchor=tk.W, pady=(0, 5))

        font_container = ttk.Frame(font_frame)
        font_container.pack(fill=tk.X, pady=(0, 5))

        self.font_size_label = ttk.Label(
            font_container,
            text=str(self.font_size_var.get()),
            font=("Arial", 10, "bold"),
            width=5
        )
        self.font_size_label.pack(side=tk.LEFT, padx=(0, 10))

        font_size_scale = ttk.Scale(
            font_container,
            from_=8,
            to=18,
            variable=self.font_size_var,
            orient=tk.HORIZONTAL,
            length=300
        )
        font_size_scale.pack(side=tk.LEFT, fill=tk.X, expand=True)

        def update_font_label(*args):
            self.font_size_label.config(text=str(int(self.font_size_var.get())))

        self.font_size_var.trace_add("write", update_font_label)

        ttk.Label(
            font_frame,
            text="8 (Small) ————————————————— 18 (Large)",
            font=("Arial", 8),
            foreground="gray"
        ).pack(anchor=tk.W)

    def setup_advanced_tab(self, parent):
        """Set up the Advanced settings tab"""
        # Phraseology Region
        phraseology_frame = ttk.LabelFrame(parent, text="Phraseology Region", padding=15)
        phraseology_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Label(
            phraseology_frame,
            text="Select the region for ATC phraseology:"
        ).pack(anchor=tk.W, pady=(0, 5))

        phraseology_options = [("US", "US"), ("ICAO", "ICAO"), ("UK", "UK"), ("EU", "EU")]

        phraseology_container = ttk.Frame(phraseology_frame)
        phraseology_container.pack(anchor=tk.W)

        for i, (text, value) in enumerate(phraseology_options):
            ttk.Radiobutton(
                phraseology_container,
                text=text,
                variable=self.phraseology_region_var,
                value=value
            ).pack(side=tk.LEFT, padx=(0, 15))

        # Auto-save Notes
        notes_frame = ttk.LabelFrame(parent, text="Notes & Files", padding=15)
        notes_frame.pack(fill=tk.X, pady=(0, 15))

        ttk.Checkbutton(
            notes_frame,
            text="Automatically save ATC notes",
            variable=self.auto_save_notes_var
        ).pack(anchor=tk.W, pady=(0, 10))

        ttk.Label(
            notes_frame,
            text="Notes Directory:"
        ).pack(anchor=tk.W, pady=(0, 5))

        notes_dir_container = ttk.Frame(notes_frame)
        notes_dir_container.pack(fill=tk.X)

        notes_dir_entry = ttk.Entry(
            notes_dir_container,
            textvariable=self.notes_directory_var,
            width=40
        )
        notes_dir_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))

    def save_settings(self):
        """Save all settings from the settings tabs"""
        # Save all settings
        self.config.set("experience_level", self.experience_var.get())
        self.config.set("aircraft_type", self.aircraft_var.get())
        self.config.set("default_aircraft_type", self.default_aircraft_var.get())
        self.config.set("voice_enabled", self.voice_enabled_var.get())
        self.config.set("voice_rate", int(self.voice_rate_var.get()))
        self.config.set("ui_theme", self.theme_var.get())
        self.config.set("font_size", int(self.font_size_var.get()))
        self.config.set("phraseology_region", self.phraseology_region_var.get())
        self.config.set("auto_save_notes", self.auto_save_notes_var.get())
        self.config.set("notes_directory", self.notes_directory_var.get())

        if self.config.save_config():
            messagebox.showinfo("Settings", "Settings saved successfully!")

            # Update components with new settings
            self.atc = ATCInstructions(
                experience_level=self.config.get("experience_level"),
                aircraft_type=self.config.get("aircraft_type"),
            )

            self.atis_decoder = ATISDecoder(
                experience_level=self.config.get("experience_level")
            )

            if self.speech_engine and self.speech_engine.is_speech_available():
                self.speech_engine.set_rate(self.config.get("voice_rate"))

            # Update instruction dropdown if it exists
            if hasattr(self, "instruction_type_combo"):
                self.instruction_type_combo["values"] = (
                    self.atc.get_all_instruction_types()
                )

                # Reset the selected instruction
                if self.instruction_type_combo["values"]:
                    self.instruction_type_combo.current(0)
                    self.on_instruction_select(None)

        else:
            messagebox.showerror("Settings", "Failed to save settings!")

    def on_airport_select(self, event):
        """Handle airport selection change"""
        # Update situation info when airport changes
        if hasattr(self, 'update_situation_info'):
            self.update_situation_info()

    def on_instruction_select(self, event):
        """Handle instruction type selection change - AI ATC mode"""
        # This method is no longer needed for AI ATC interface
        # All functionality is now handled by AI ATC methods
        pass

    def generate_readback(self):
        """
        Generate and display the readback message.
        Uses AIResponseHandler for enhanced ATC instruction generation if available.
        """
        selected_instruction = self.instruction_type_combo.get()
        if not selected_instruction or selected_instruction.startswith("---"):
            messagebox.showwarning(
                "Warning", "Please select a valid instruction type first"
            )
            return

        # Get current airport data
        current_airport_name = self.airport_var.get()
        airport_data = self.airports.get(current_airport_name, {})

        # Get parameters for the selected instruction
        params = self.atc.get_parameters_for_instruction(selected_instruction)

        # Collect parameter values
        param_values = {}
        for param in params:
            if param in self.param_entries:
                if param == "taxiways":
                    param_values[param] = self.param_entries[param]
                else:
                    param_values[param] = self.param_entries[param].get()
            else:
                param_values[param] = ""

        try:
            # Generate the instruction using the ATC system
            instruction = self.atc.generate_instruction(
                selected_instruction, param_values, airport_data
            )

            # Display in AI conversation if available
            if hasattr(self, "ai_atc_conversation"):
                self.ai_atc_conversation.delete(1.0, tk.END)
                self.ai_atc_conversation.insert(
                    tk.END, f"🎯 Generated Instruction:\n\n"
                )
                self.ai_atc_conversation.insert(tk.END, f"ATC: {instruction}\n\n")

                # Generate AI-enhanced readback if available
                if self.ai_handler and self.ai_handler.is_ai_available():
                    self.show_ai_processing("Generating AI-enhanced readback...")

                    # Get difficulty modifier
                    difficulty = self.difficulty_var.get()
                    difficulty_modifier = self.get_difficulty_modifier(difficulty)

                    # Generate AI-enhanced readback
                    ai_prompt = f"""
                    Generate a realistic pilot readback for this ATC instruction: "{instruction}"
                    
                    Airport: {current_airport_name}
                    Difficulty: {difficulty}
                    {difficulty_modifier}
                    
                    Provide a professional, concise readback that a pilot would give.
                    """

                    ai_response = self.ai_handler.generate_response(ai_prompt)
                    if ai_response and ai_response.strip():
                        self.ai_atc_conversation.insert(
                            tk.END, f"PILOT: {ai_response.strip()}\n\n"
                        )
                    else:
                        # Fallback to template readback
                        readback = self.atc.generate_readback(
                            selected_instruction, param_values, airport_data
                        )
                        self.ai_atc_conversation.insert(
                            tk.END, f"PILOT: {readback}\n\n"
                        )

                    self.hide_ai_processing()
                else:
                    # Use template readback
                    readback = self.atc.generate_readback(
                        selected_instruction, param_values, airport_data
                    )
                    self.ai_atc_conversation.insert(tk.END, f"PILOT: {readback}\n\n")

            self.status_var.set("Status: Instruction generated successfully")

        except KeyError as e:
            messagebox.showerror("Error", f"Missing parameter: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            self.status_var.set("Status: Error generating instruction")

    def speak_atc(self):
        """Use text-to-speech to read the ATC instruction"""
        if not self.config.get("voice_enabled"):
            messagebox.showinfo(
                "Voice Disabled", "Voice playback is disabled in settings."
            )
            return

        # Get ATC text from AI conversation if available
        atc_text = ""
        if hasattr(self, "ai_atc_conversation"):
            conversation_text = self.ai_atc_conversation.get(1.0, tk.END)
            # Extract the last ATC message
            lines = conversation_text.split("\n")
            for line in reversed(lines):
                if line.startswith("ATC:"):
                    atc_text = line.replace("ATC:", "").strip()
                    break

        if atc_text:
            if self.speech_engine and self.speech_engine.is_speech_available():
                self.speech_engine.speak(atc_text)
                self.status_var.set("Speaking ATC instruction...")
            else:
                messagebox.showinfo(
                    "Speech Unavailable",
                    "Speech engine is not available. Please check your system settings.",
                )
        else:
            messagebox.showinfo("No ATC Text", "No ATC instruction found to speak.")

    def speak_atis(self):
        """Speak the ATIS message"""
        if not self.config.get("voice_enabled"):
            messagebox.showinfo(
                "Voice Disabled", "Voice playback is disabled in settings."
            )
            return

        atis_text = self.atis_input.get(1.0, tk.END).strip()
        if atis_text:
            if self.speech_engine and self.speech_engine.is_speech_available():
                self.speech_engine.speak(atis_text)
                self.status_var.set("Speaking ATIS...")
            else:
                messagebox.showinfo(
                    "Speech Unavailable",
                    "Speech engine is not available. Please check your system settings.",
                )
        else:
            messagebox.showinfo("No ATIS Text", "No ATIS message found to speak.")

    def save_instruction(self):
        """Save current instruction as a preset"""
        # Get instruction from AI conversation if available
        instruction_text = ""
        readback_text = ""

        if hasattr(self, "ai_atc_conversation"):
            conversation_text = self.ai_atc_conversation.get(1.0, tk.END)
            lines = conversation_text.split("\n")
            for line in lines:
                if line.startswith("ATC:"):
                    instruction_text = line.replace("ATC:", "").strip()
                elif line.startswith("PILOT:"):
                    readback_text = line.replace("PILOT:", "").strip()

        if not instruction_text:
            messagebox.showwarning(
                "No Instruction", "Please generate an instruction first."
            )
            return

        # Create a simple dialog for naming the preset
        dialog = tk.Toplevel(self.root)
        dialog.title("Save Instruction Preset")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # Preset name entry
        ttk.Label(dialog, text="Preset Name:").pack(anchor=tk.W, pady=(10, 5))
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.pack(fill=tk.X, padx=10, pady=(0, 10))
        name_entry.focus()

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        def save_preset():
            preset_name = name_var.get().strip()
            if not preset_name:
                messagebox.showwarning("Warning", "Please enter a preset name.")
                return

            # Save to presets
            if not hasattr(self, "instruction_presets"):
                self.instruction_presets = {}

            self.instruction_presets[preset_name] = {
                "instruction": instruction_text,
                "readback": readback_text,
                "airport": self.airport_var.get(),
                "instruction_type": getattr(self, "instruction_type_combo", None)
                and self.instruction_type_combo.get()
                or None,
            }

            # Save to file
            try:
                import json

                with open("instruction_presets.json", "w") as f:
                    json.dump(self.instruction_presets, f, indent=2)
                messagebox.showinfo(
                    "Success", f"Preset '{preset_name}' saved successfully!"
                )
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save preset: {e}")

        ttk.Button(button_frame, text="Save", command=save_preset).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(
            side=tk.LEFT
        )

    def load_preset(self):
        """Load a saved instruction preset"""
        presets = self.config.get("instruction_presets", {})

        if not presets:
            messagebox.showinfo("No Presets", "No saved presets found.")
            return

        # Create preset selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Instruction Preset")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Preset list
        ttk.Label(dialog, text="Select a preset to load:").pack(
            anchor=tk.W, pady=(10, 5)
        )

        listbox = tk.Listbox(dialog, height=10)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        for preset_name in presets.keys():
            listbox.insert(tk.END, preset_name)

        # Preview
        preview_frame = ttk.Frame(dialog)
        preview_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Label(preview_frame, text="Preview:").pack(anchor=tk.W)
        preview_text = tk.Text(preview_frame, height=4, wrap=tk.WORD)
        preview_text.pack(fill=tk.X)

        def on_selection_change(event):
            selection = listbox.curselection()
            if selection:
                preset_name = list(presets.keys())[selection[0]]
                preset_data = presets[preset_name]
                preview_text.delete(1.0, tk.END)
                preview_text.insert(
                    tk.END,
                    f"Instruction: {preset_data['instruction']}\n\nReadback: {preset_data['readback']}",
                )

        listbox.bind("<<ListboxSelect>>", on_selection_change)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        def load_selected():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a preset to load.")
                return

            preset_name = list(presets.keys())[selection[0]]
            preset_data = presets[preset_name]

            # Load the preset data into AI conversation
            if hasattr(self, "ai_atc_conversation"):
                self.ai_atc_conversation.delete(1.0, tk.END)
                self.ai_atc_conversation.insert(
                    tk.END, f"🎯 Loaded Preset: {preset_name}\n\n"
                )
                self.ai_atc_conversation.insert(
                    tk.END, f"ATC: {preset_data['instruction']}\n\n"
                )
                self.ai_atc_conversation.insert(
                    tk.END, f"PILOT: {preset_data['readback']}\n\n"
                )

            # Set airport and instruction type if they exist
            if preset_data.get("airport") and preset_data["airport"] in self.airports:
                self.airport_var.set(preset_data["airport"])
                self.on_airport_select(None)

            if preset_data.get("instruction_type") and hasattr(
                self, "instruction_type_combo"
            ):
                self.instruction_type_combo.set(preset_data["instruction_type"])
                self.on_instruction_select(None)

            messagebox.showinfo(
                "Success", f"Preset '{preset_name}' loaded successfully!"
            )
            dialog.destroy()

        ttk.Button(button_frame, text="Load", command=load_selected).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(
            side=tk.LEFT
        )

    def validate_instruction(self):
        """Validate the current instruction and provide tips"""
        # Get instruction from AI conversation if available
        instruction_text = ""
        readback_text = ""

        if hasattr(self, "ai_atc_conversation"):
            conversation_text = self.ai_atc_conversation.get(1.0, tk.END)
            lines = conversation_text.split("\n")
            for line in lines:
                if line.startswith("ATC:"):
                    instruction_text = line.replace("ATC:", "").strip()
                elif line.startswith("PILOT:"):
                    readback_text = line.replace("PILOT:", "").strip()

        if not instruction_text:
            self.validation_text.delete(1.0, tk.END)
            self.validation_text.insert(
                tk.END,
                "❌ No instruction to validate. Please generate an instruction first.",
            )
            return

        validation_results = []
        tips = []

        # Basic validation checks
        if len(instruction_text) < 10:
            validation_results.append("⚠️ Instruction seems too short")
            tips.append("Consider adding more detail to the instruction")

        if not any(
            word in instruction_text.lower()
            for word in [
                "taxi",
                "takeoff",
                "landing",
                "hold",
                "turn",
                "climb",
                "descend",
            ]
        ):
            validation_results.append("⚠️ Instruction may lack standard ATC terminology")
            tips.append(
                "Include standard ATC terms like 'taxi', 'takeoff', 'landing', etc."
            )

        if not readback_text:
            validation_results.append("⚠️ No readback provided")
            tips.append("Generate a readback to practice pilot responses")

        # Display results
        self.validation_text.delete(1.0, tk.END)

        if validation_results:
            self.validation_text.insert(tk.END, "Validation Results:\n\n")
            for result in validation_results:
                self.validation_text.insert(tk.END, f"{result}\n")

            if tips:
                self.validation_text.insert(tk.END, "\nTips:\n\n")
                for tip in tips:
                    self.validation_text.insert(tk.END, f"• {tip}\n")
        else:
            self.validation_text.insert(tk.END, "✅ Instruction looks good!\n\n")
            self.validation_text.insert(
                tk.END,
                "The instruction appears to be well-formed with proper ATC terminology.",
            )

    def get_difficulty_modifier(self):
        """Get AI prompt modifier based on difficulty level"""
        difficulty = self.difficulty_var.get()

        modifiers = {
            "Beginner": "Use simple, clear language. Avoid complex procedures. Focus on basic ATC phraseology.",
            "Intermediate": "Use standard ATC phraseology. Include moderate complexity procedures.",
            "Advanced": "Use professional ATC phraseology. Include complex procedures and multiple clearances.",
            "Expert": "Use advanced ATC phraseology. Include complex procedures, multiple clearances, and emergency scenarios.",
        }

        return modifiers.get(difficulty, modifiers["Beginner"])

    def on_difficulty_change(self, event=None):
        """Handle difficulty level change"""
        difficulty = self.difficulty_var.get()

        # Update instruction types based on difficulty
        if difficulty == "Beginner":
            # Show only basic instructions
            available_types = [
                t
                for t in self.atc.get_all_instruction_types()
                if any(word in t.lower() for word in ["taxi", "takeoff", "landing"])
            ]
        elif difficulty == "Intermediate":
            # Show most instructions except complex ones
            available_types = [
                t
                for t in self.atc.get_all_instruction_types()
                if not any(word in t.lower() for word in ["emergency", "complex"])
            ]
        elif difficulty == "Advanced":
            # Show all instructions
            available_types = self.atc.get_all_instruction_types()
        else:  # Expert
            # Show all instructions including emergency scenarios
            available_types = self.atc.get_all_instruction_types()

        # Update the instruction type combo if it exists
        if hasattr(self, "instruction_type_combo"):
            self.instruction_type_combo["values"] = available_types
            if available_types and not self.instruction_type_combo.get():
                self.instruction_type_combo.set(available_types[0])

        self.status_var.set(f"Status: Difficulty set to {difficulty}")

    def on_preset_select(self, event=None):
        """Handle preset selection"""
        preset = self.preset_var.get()
        if preset != "Custom":
            self.apply_preset()

    def apply_preset(self):
        """Apply selected parameter preset"""
        preset = self.preset_var.get()

        if preset == "Custom":
            return

        # Define preset values
        presets = {
            "Standard Departure": {
                "runway": "09L",
                "direction": "Left",
                "altitude": "3000",
                "heading": "090",
            },
            "Standard Arrival": {
                "runway": "27R",
                "direction": "Right",
                "altitude": "2000",
                "heading": "270",
            },
            "Emergency": {
                "runway": "09L",
                "direction": "Left",
                "altitude": "1000",
                "heading": "090",
            },
            "Training": {
                "runway": "09L",
                "direction": "Left",
                "altitude": "2500",
                "heading": "090",
            },
        }

        if preset in presets:
            preset_values = presets[preset]

            # Apply preset values to parameter fields
            for param, value in preset_values.items():
                if param in self.param_entries:
                    if hasattr(self.param_entries[param], "set"):
                        self.param_entries[param].set(value)

            self.status_var.set(f"Status: Applied {preset} preset")
        else:
            self.status_var.set("Status: Unknown preset")

    def on_ai_mode_toggle(self):
        """Handle AI mode toggle"""
        if self.ai_mode_var.get():
            self.tab_ai_status.config(text="AI Mode: ON", foreground="green")
        else:
            self.tab_ai_status.config(text="Template Mode", foreground="orange")
        self.update_tab_ai_status()

    def update_tab_ai_status(self):
        """Update AI status for the ATC tab"""
        if hasattr(self, "tab_ai_status"):
            if (
                self.ai_mode_var.get()
                and self.ai_handler
                and self.ai_handler.is_ai_available()
            ):
                self.tab_ai_status.config(text="AI Mode: ON", foreground="green")
            elif self.ai_mode_var.get():
                self.tab_ai_status.config(
                    text="AI Mode: OFF (Not Available)", foreground="red"
                )
            else:
                self.tab_ai_status.config(text="Template Mode", foreground="orange")

    def save_instruction(self):
        """Save current instruction as a preset"""
        # Get instruction from AI conversation if available
        instruction_text = ""
        readback_text = ""

        if hasattr(self, "ai_atc_conversation"):
            conversation_text = self.ai_atc_conversation.get(1.0, tk.END)
            lines = conversation_text.split("\n")
            for line in lines:
                if line.startswith("ATC:"):
                    instruction_text = line.replace("ATC:", "").strip()
                elif line.startswith("PILOT:"):
                    readback_text = line.replace("PILOT:", "").strip()

        if not instruction_text:
            messagebox.showwarning(
                "No Instruction", "Please generate an instruction first."
            )
            return

        # Create a simple dialog for naming the preset
        dialog = tk.Toplevel(self.root)
        dialog.title("Save Instruction Preset")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # Preset name entry
        ttk.Label(dialog, text="Preset Name:").pack(anchor=tk.W, pady=(10, 5))
        name_var = tk.StringVar()
        name_entry = ttk.Entry(dialog, textvariable=name_var, width=30)
        name_entry.pack(fill=tk.X, padx=10, pady=(0, 10))
        name_entry.focus()

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        def save_preset():
            preset_name = name_var.get().strip()
            if not preset_name:
                messagebox.showwarning("Warning", "Please enter a preset name.")
                return

            # Save to presets
            if not hasattr(self, "instruction_presets"):
                self.instruction_presets = {}

            self.instruction_presets[preset_name] = {
                "instruction": instruction_text,
                "readback": readback_text,
                "airport": self.airport_var.get(),
                "instruction_type": getattr(self, "instruction_type_combo", None)
                and self.instruction_type_combo.get()
                or None,
            }

            # Save to file
            try:
                import json

                with open("instruction_presets.json", "w") as f:
                    json.dump(self.instruction_presets, f, indent=2)
                messagebox.showinfo(
                    "Success", f"Preset '{preset_name}' saved successfully!"
                )
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save preset: {e}")

        ttk.Button(button_frame, text="Save", command=save_preset).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(
            side=tk.LEFT
        )

    def load_preset(self):
        """Load a saved instruction preset"""
        presets = self.config.get("instruction_presets", {})

        if not presets:
            messagebox.showinfo("No Presets", "No saved presets found.")
            return

        # Create preset selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Instruction Preset")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Preset list
        ttk.Label(dialog, text="Select a preset to load:").pack(
            anchor=tk.W, pady=(10, 5)
        )

        listbox = tk.Listbox(dialog, height=10)
        listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        for preset_name in presets.keys():
            listbox.insert(tk.END, preset_name)

        # Preview
        preview_frame = ttk.Frame(dialog)
        preview_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Label(preview_frame, text="Preview:").pack(anchor=tk.W)
        preview_text = tk.Text(preview_frame, height=4, wrap=tk.WORD)
        preview_text.pack(fill=tk.X)

        def on_selection_change(event):
            selection = listbox.curselection()
            if selection:
                preset_name = list(presets.keys())[selection[0]]
                preset_data = presets[preset_name]
                preview_text.delete(1.0, tk.END)
                preview_text.insert(
                    tk.END,
                    f"Instruction: {preset_data['instruction']}\n\nReadback: {preset_data['readback']}",
                )

        listbox.bind("<<ListboxSelect>>", on_selection_change)

        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        def load_selected():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("Warning", "Please select a preset to load.")
                return

            preset_name = list(presets.keys())[selection[0]]
            preset_data = presets[preset_name]

            # Load the preset data into AI conversation
            if hasattr(self, "ai_atc_conversation"):
                self.ai_atc_conversation.delete(1.0, tk.END)
                self.ai_atc_conversation.insert(
                    tk.END, f"🎯 Loaded Preset: {preset_name}\n\n"
                )
                self.ai_atc_conversation.insert(
                    tk.END, f"ATC: {preset_data['instruction']}\n\n"
                )
                self.ai_atc_conversation.insert(
                    tk.END, f"PILOT: {preset_data['readback']}\n\n"
                )

            # Set airport and instruction type if they exist
            if preset_data.get("airport") and preset_data["airport"] in self.airports:
                self.airport_var.set(preset_data["airport"])
                self.on_airport_select(None)

            if preset_data.get("instruction_type") and hasattr(
                self, "instruction_type_combo"
            ):
                self.instruction_type_combo.set(preset_data["instruction_type"])
                self.on_instruction_select(None)

            messagebox.showinfo(
                "Success", f"Preset '{preset_name}' loaded successfully!"
            )
            dialog.destroy()

        ttk.Button(button_frame, text="Load", command=load_selected).pack(
            side=tk.LEFT, padx=(0, 5)
        )
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(
            side=tk.LEFT
        )

    def validate_instruction(self):
        """
        Validate the current instruction and provide concise, structured feedback.
        """
        # Extract instruction and readback from AI conversation, if available
        instruction_text = ""
        readback_text = ""

        if hasattr(self, "ai_atc_conversation"):
            conversation_text = self.ai_atc_conversation.get(1.0, tk.END)
            for line in conversation_text.split("\n"):
                if line.startswith("ATC:"):
                    instruction_text = line.replace("ATC:", "").strip()
                elif line.startswith("PILOT:"):
                    readback_text = line.replace("PILOT:", "").strip()

        # If no instruction, show error and exit
        if not instruction_text:
            self.validation_text.delete(1.0, tk.END)
            self.validation_text.insert(
                tk.END,
                "❌ No instruction to validate. Please generate an instruction first.",
            )
            return

        # Validation checks
        validation_results = []
        tips = []

        # Check: Instruction length
        if len(instruction_text) < 10:
            validation_results.append("⚠️ Instruction seems too short")
            tips.append("Consider adding more detail to the instruction.")

        # Check: Standard ATC terminology
        atc_terms = ["taxi", "takeoff", "landing", "hold", "turn", "climb", "descend"]
        if not any(term in instruction_text.lower() for term in atc_terms):
            validation_results.append("⚠️ Instruction may lack standard ATC terminology")
            tips.append(
                "Include standard ATC terms like 'taxi', 'takeoff', 'landing', etc."
            )

        # Check: Readback present
        if not readback_text:
            validation_results.append("⚠️ No readback provided")
            tips.append("Generate a readback to practice pilot responses.")

        # Display results in a concise, structured format
        self.validation_text.delete(1.0, tk.END)

        if validation_results:
            self.validation_text.insert(tk.END, "Validation Results:\n\n")
            for result in validation_results:
                self.validation_text.insert(tk.END, f"{result}\n")
            if tips:
                self.validation_text.insert(tk.END, "\nTips:\n\n")
                for tip in tips:
                    self.validation_text.insert(tk.END, f"• {tip}\n")
        else:
            self.validation_text.insert(tk.END, "✅ Instruction looks good!\n\n")
            self.validation_text.insert(
                tk.END,
                "The instruction appears to be well-formed with proper ATC terminology.",
            )

    def generate_readback(self):
        """
        Generate and display the readback message.
        Uses AIResponseHandler for enhanced ATC instruction generation if available.
        """
        selected_instruction = self.instruction_type_combo.get()
        if not selected_instruction or selected_instruction.startswith("---"):
            messagebox.showwarning(
                "Warning", "Please select a valid instruction type first"
            )
            return

        # Gather parameter values from entry fields
        params = {}
        for param, var_or_vars in self.param_entries.items():
            if param == "taxiways" and isinstance(var_or_vars, list):
                params[param] = " via " + " then ".join(var_or_vars)
            elif hasattr(var_or_vars, "get"):
                params[param] = var_or_vars.get()
            else:
                params[param] = var_or_vars

        # Get the full instruction and readback template
        instruction_data = self.atc.get_instruction(selected_instruction)
        if not instruction_data:
            return

        try:
            # Prepare ATC instruction and readback text
            atc_text = instruction_data["instruction"].format(**params)
            readback_text = instruction_data["readback"].format(**params)

            # Display the template instruction in AI ATC conversation
            if hasattr(self, "ai_atc_conversation"):
                self.ai_atc_conversation.delete(1.0, tk.END)
                self.ai_atc_conversation.insert(
                    tk.END,
                    f"🎯 ATC Instruction Template:\n\nATC: {atc_text}\n\nPILOT: {readback_text}\n\n",
                )

            # If AI mode is enabled and AI is available, enhance the instruction
            if (
                self.ai_mode_var.get()
                and self.ai_handler
                and self.ai_handler.is_ai_available()
            ):
                self.show_ai_processing("Generating AI instruction...")
                self.status_var.set("Status: Generating AI-enhanced instruction...")

                # Prepare aircraft and airport info for AI
                aircraft_info = {
                    "callsign": params.get("callsign", ""),
                    "aircraft_type": params.get("aircraft_type", ""),
                    "runway": params.get("runway", ""),
                    "destination": params.get("destination", ""),
                }

                # Get current airport info
                current_airport_name = self.airport_var.get()
                airport_info = self.airports.get(current_airport_name, {})

                # Get difficulty modifier for AI prompt
                difficulty_modifier = self.get_difficulty_modifier()

                # Generate AI-enhanced response with difficulty consideration
                ai_response = self.ai_handler.generate_atc_response(
                    pilot_message=f"Request {selected_instruction.lower()}",
                    aircraft_info=aircraft_info,
                    airport_info=airport_info,
                    response_type=selected_instruction.lower(),
                    additional_context=f"Difficulty Level: {self.difficulty_var.get()}. {difficulty_modifier}",
                )

                # Hide processing indicator
                self.hide_ai_processing()

                if ai_response:
                    # Add AI-enhanced instruction to conversation
                    if hasattr(self, "ai_atc_conversation"):
                        self.ai_atc_conversation.insert(
                            tk.END,
                            f"🤖 AI-Enhanced ATC Instruction:\n\nATC: {ai_response}\n\n",
                        )
                    self.status_var.set("Status: AI-enhanced instruction generated")
                else:
                    self.status_var.set(
                        "Status: Using template instruction (AI unavailable)"
                    )
            elif self.ai_mode_var.get():
                self.status_var.set(
                    "Status: Using template instruction (AI not available)"
                )
            else:
                self.status_var.set(
                    "Status: Using template instruction (AI mode disabled)"
                )

        except KeyError as e:
            messagebox.showerror("Error", f"Missing parameter: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
            self.status_var.set("Status: Error generating instruction")

    def speak_atc(self):
        """Use text-to-speech to read the ATC instruction"""
        if not self.config.get("voice_enabled"):
            messagebox.showinfo(
                "Voice Disabled", "Voice playback is disabled in settings."
            )
            return

        # Get ATC text from AI conversation if available
        atc_text = ""
        if hasattr(self, "ai_atc_conversation"):
            conversation_text = self.ai_atc_conversation.get(1.0, tk.END)
            # Extract the last ATC message
            lines = conversation_text.split("\n")
            for line in reversed(lines):
                if line.startswith("ATC:"):
                    atc_text = line.replace("ATC:", "").strip()
                    break

        if atc_text:
            if self.speech_engine and self.speech_engine.is_speech_available():
                self.speech_engine.speak(atc_text)
                self.status_var.set("Speaking ATC instruction...")
            else:
                messagebox.showinfo(
                    "Speech Not Available",
                    "Text-to-speech is not available on this system.",
                )
        else:
            messagebox.showinfo("Speak", "No ATC instruction to speak.")

    def insert_sample_atis(self):
        """Insert a sample ATIS message"""
        sample_atis = """WSSS INFORMATION ALPHA. 1430Z. RUNWAY IN USE 02L AND 02R. 
WIND 020 AT 8 KNOTS. VISIBILITY 10 KILOMETRES. FEW CLOUDS AT 4000. 
TEMPERATURE 28 DEW POINT 24. QNH 1013. 
ILS APPROACH IN PROGRESS. BIRDS REPORTED VICINITY OF AIRPORT.
ADVISE YOU HAVE INFORMATION ALPHA ON INITIAL CONTACT. CONTACT TOWER ON 118.1."""

        self.atis_input.delete(1.0, tk.END)
        self.atis_input.insert(tk.END, sample_atis)

    def decode_atis(self):
        """Decode the ATIS message"""
        raw_atis = self.atis_input.get(1.0, tk.END).strip()

        if not raw_atis:
            messagebox.showinfo("Decode", "No ATIS message to decode.")
            return

        decoded = self.atis_decoder.decode_atis(raw_atis)
        formatted = self.atis_decoder.format_decoded_atis(
            decoded, verbose=(self.config.get("experience_level") != "beginner")
        )

        self.atis_output.delete(1.0, tk.END)
        self.atis_output.insert(tk.END, formatted)

        self.status_var.set("ATIS decoded successfully")

    def clear_atis(self):
        """Clear the ATIS input and output"""
        self.atis_input.delete(1.0, tk.END)
        self.atis_output.delete(1.0, tk.END)

    def speak_atis(self):
        """Speak the ATIS message"""
        if not self.config.get("voice_enabled"):
            messagebox.showinfo(
                "Voice Disabled", "Voice playback is disabled in settings."
            )
            return

        atis_text = self.atis_input.get(1.0, tk.END).strip()
        if atis_text:
            if self.speech_engine and self.speech_engine.is_speech_available():
                self.speech_engine.speak(atis_text)
            else:
                messagebox.showinfo(
                    "Speech Not Available",
                    "Text-to-speech is not available on this system.",
                )
            self.status_var.set("Speaking ATIS message...")
        else:
            messagebox.showinfo("Speak", "No ATIS message to speak.")

    def generate_ai_atis(self):
        """Generate ATIS using AI"""
        if not self.ai_handler or not self.ai_handler.is_ai_available():
            messagebox.showinfo(
                "AI Not Available",
                "AI features are not available. Please check your Ollama setup.",
            )
            return

        try:
            # Get current airport info
            current_airport_name = self.airport_var.get()
            airport_info = self.airports.get(current_airport_name, {})

            if not airport_info:
                messagebox.showwarning(
                    "No Airport Selected", "Please select an airport first."
                )
                return

            self.show_ai_processing("Generating AI ATIS...")
            self.status_var.set("Status: Generating AI ATIS...")

            # Generate AI ATIS
            atis_message = self.ai_handler.generate_atis_message(airport_info)

            # Hide processing indicator
            self.hide_ai_processing()

            if atis_message:
                # Clear and insert the AI-generated ATIS
                self.atis_input.delete(1.0, tk.END)
                self.atis_input.insert(tk.END, atis_message)
                self.status_var.set("Status: AI ATIS generated successfully")
            else:
                self.status_var.set("Status: Failed to generate AI ATIS")
                messagebox.showwarning(
                    "AI ATIS Generation Failed",
                    "Could not generate ATIS message. Please try again.",
                )

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate AI ATIS: {str(e)}")
            self.status_var.set("Status: Error generating AI ATIS")

    def on_ai_response_generated(self, response, standby_index=None):
        """Handle AI response generation callback (standby_index unused in main window)."""
        # This method is called when AI generates a response asynchronously.
        # For the new UI, responses are handled synchronously in transmit_message,
        # but this callback can still be used for async updates if needed.
        try:
            # If we have a communication log, update it
            if hasattr(self, "communication_log") and self.current_session_active:
                self.root.after(0, lambda: self._log_atc_message(response))
        except Exception as e:
            logger.warning("Error in AI response callback: %s", e)

    def on_ai_mode_toggle(self):
        """Handle AI mode toggle"""
        if self.ai_mode_var.get():
            self.tab_ai_status.config(text="AI Mode: ON", foreground="green")
        else:
            self.tab_ai_status.config(text="Template Mode", foreground="orange")
        self.update_tab_ai_status()

    def update_tab_ai_status(self):
        """Update AI status for the ATC tab"""
        if hasattr(self, "tab_ai_status"):
            if (
                self.ai_mode_var.get()
                and self.ai_handler
                and self.ai_handler.is_ai_available()
            ):
                self.tab_ai_status.config(text="AI Mode: ON", foreground="green")
            elif self.ai_mode_var.get():
                self.tab_ai_status.config(
                    text="AI Mode: OFF (Not Available)", foreground="red"
                )
            else:
                self.tab_ai_status.config(text="Template Mode", foreground="orange")

    def save_instruction(self):
        """Save current instruction as a preset"""
        # Get instruction from AI conversation if available
        instruction_text = ""
        readback_text = ""

        if hasattr(self, "ai_atc_conversation"):
            conversation_text = self.ai_atc_conversation.get(1.0, tk.END)
            lines = conversation_text.split("\n")
            for line in lines:
                if line.startswith("ATC:"):
                    instruction_text = line.replace("ATC:", "").strip()
                elif line.startswith("PILOT:"):
                    readback_text = line.replace("PILOT:", "").strip()

        if not instruction_text:
            messagebox.showwarning(
                "No Instruction", "Please generate an instruction first."
            )
            return

        # Create a simple dialog for naming the preset
        dialog = tk.Toplevel(self.root)
        dialog.title("Save Instruction Preset")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (400 // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (200 // 2)
        dialog.geometry(f"+{x}+{y}")

        ttk.Label(dialog, text="Preset Name:", font=("Arial", 12, "bold")).pack(pady=10)

        name_var = tk.StringVar()
        name_entry = ttk.Entry(
            dialog, textvariable=name_var, width=30, font=("Arial", 10)
        )
        name_entry.pack(pady=10)
        name_entry.focus_set()

        ttk.Label(dialog, text="Description (optional):").pack(pady=(10, 5))
        desc_var = tk.StringVar()
        desc_entry = ttk.Entry(
            dialog, textvariable=desc_var, width=30, font=("Arial", 10)
        )
        desc_entry.pack(pady=5)

        def save_preset():
            name = name_var.get().strip()
            if not name:
                messagebox.showwarning("Invalid Name", "Please enter a preset name.")
                return

            # Save to config
            presets = self.config.get("instruction_presets", {})
            presets[name] = {
                "instruction": instruction_text,
                "readback": readback_text,
                "description": desc_var.get().strip(),
                "airport": self.airport_var.get(),
                "instruction_type": self.instruction_type_combo.get(),
                "parameters": {
                    param: var.get() if hasattr(var, "get") else str(var)
                    for param, var in self.param_entries.items()
                },
            }

            self.config.set("instruction_presets", presets)
            if self.config.save_config():
                messagebox.showinfo("Success", f"Preset '{name}' saved successfully!")
                dialog.destroy()
            else:
                messagebox.showerror("Error", "Failed to save preset.")

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)

        ttk.Button(button_frame, text="Save", command=save_preset).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(
            side=tk.LEFT, padx=5
        )

        # Bind Enter key to save
        name_entry.bind("<Return>", lambda e: save_preset())

    def load_preset(self):
        """Load a saved instruction preset"""
        presets = self.config.get("instruction_presets", {})

        if not presets:
            messagebox.showinfo("No Presets", "No saved presets found.")
            return

        # Create preset selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Load Instruction Preset")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()

        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (500 // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (400 // 2)
        dialog.geometry(f"+{x}+{y}")

        ttk.Label(dialog, text="Select a Preset:", font=("Arial", 12, "bold")).pack(
            pady=10
        )

        # Create listbox for presets
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        listbox = tk.Listbox(list_frame, height=10, font=("Arial", 10))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=listbox.yview)
        listbox.configure(yscrollcommand=scrollbar.set)

        listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Add presets to listbox
        for name, preset_data in presets.items():
            description = preset_data.get("description", "")
            airport = preset_data.get("airport", "")
            instruction_type = preset_data.get("instruction_type", "")
            display_text = f"{name} ({airport} - {instruction_type})"
            if description:
                display_text += f" - {description}"
            listbox.insert(tk.END, display_text)

        # Preview frame
        preview_frame = ttk.LabelFrame(dialog, text="Preview", padding=10)
        preview_frame.pack(fill=tk.X, padx=20, pady=10)

        preview_text = scrolledtext.ScrolledText(
            preview_frame, height=4, wrap=tk.WORD, font=("Arial", 9)
        )
        preview_text.pack(fill=tk.X)

        def on_selection_change(event):
            selection = listbox.curselection()
            if selection:
                preset_name = list(presets.keys())[selection[0]]
                preset_data = presets[preset_name]
                preview_text.delete(1.0, tk.END)
                preview_text.insert(
                    tk.END,
                    f"Instruction: {preset_data['instruction']}\n\nReadback: {preset_data['readback']}",
                )

        listbox.bind("<<ListboxSelect>>", on_selection_change)

        def load_selected():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select a preset.")
                return

            preset_name = list(presets.keys())[selection[0]]
            preset_data = presets[preset_name]

            # Load the preset data into AI conversation
            if hasattr(self, "ai_atc_conversation"):
                self.ai_atc_conversation.delete(1.0, tk.END)
                self.ai_atc_conversation.insert(
                    tk.END, f"🎯 Loaded Preset: {preset_name}\n\n"
                )
                self.ai_atc_conversation.insert(
                    tk.END, f"ATC: {preset_data['instruction']}\n\n"
                )
                self.ai_atc_conversation.insert(
                    tk.END, f"PILOT: {preset_data['readback']}\n\n"
                )

            # Set airport and instruction type if they exist
            if preset_data.get("airport") and preset_data["airport"] in self.airports:
                self.airport_var.set(preset_data["airport"])
                self.on_airport_select(None)

            if preset_data.get("instruction_type"):
                self.instruction_type_combo.set(preset_data["instruction_type"])
                self.on_instruction_select(None)

            # Load parameters
            for param, value in preset_data.get("parameters", {}).items():
                if param in self.param_entries:
                    if hasattr(self.param_entries[param], "set"):
                        self.param_entries[param].set(value)

            messagebox.showinfo(
                "Success", f"Preset '{preset_name}' loaded successfully!"
            )
            dialog.destroy()

        def delete_selected():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning(
                    "No Selection", "Please select a preset to delete."
                )
                return

            preset_name = list(presets.keys())[selection[0]]
            if messagebox.askyesno(
                "Confirm Delete",
                f"Are you sure you want to delete preset '{preset_name}'?",
            ):
                del presets[preset_name]
                self.config.set("instruction_presets", presets)
                self.config.save_config()
                messagebox.showinfo("Success", f"Preset '{preset_name}' deleted.")
                dialog.destroy()

        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)

        ttk.Button(button_frame, text="Load", command=load_selected).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Delete", command=delete_selected).pack(
            side=tk.LEFT, padx=5
        )
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(
            side=tk.LEFT, padx=5
        )

    def on_preset_select(self, event=None):
        """Handle preset selection"""
        preset = self.preset_var.get()
        if preset != "Custom":
            self.apply_preset()

    def apply_preset(self):
        """Apply selected parameter preset"""
        preset = self.preset_var.get()

        if preset == "Custom":
            return

        # Define presets
        presets = {
            "Standard Departure": {
                "callsign": "9V-SIA",
                "runway": "02C",
                "altitude": "5000",
                "heading": "270",
                "speed": "210",
                "destination": "WSSS",
                "squawk": "1234",
                "aircraft_type": "Boeing 737",
            },
            "Standard Arrival": {
                "callsign": "9V-SIA",
                "runway": "02L",
                "altitude": "3000",
                "heading": "090",
                "speed": "180",
                "destination": "WSSS",
                "squawk": "1234",
                "aircraft_type": "Boeing 737",
            },
            "Emergency": {
                "callsign": "9V-SIA",
                "runway": "02C",
                "altitude": "2000",
                "heading": "360",
                "speed": "150",
                "destination": "WSSS",
                "squawk": "7700",
                "aircraft_type": "Boeing 737",
            },
            "Training": {
                "callsign": "N123AB",
                "runway": "02C",
                "altitude": "3000",
                "heading": "180",
                "speed": "120",
                "destination": "WSSS",
                "squawk": "1200",
                "aircraft_type": "C172",
            },
        }

        if preset in presets:
            preset_values = presets[preset]

            # Apply preset values to parameter fields
            for param, value in preset_values.items():
                if param in self.param_entries:
                    if hasattr(self.param_entries[param], "set"):
                        self.param_entries[param].set(value)

            self.status_var.set(f"Status: Applied {preset} preset")
        else:
            self.status_var.set("Status: Unknown preset")

    def validate_instruction(self):
        """Validate the current instruction and provide tips"""
        # Get instruction from AI conversation if available
        instruction_text = ""
        readback_text = ""

        if hasattr(self, "ai_atc_conversation"):
            conversation_text = self.ai_atc_conversation.get(1.0, tk.END)
            lines = conversation_text.split("\n")
            for line in lines:
                if line.startswith("ATC:"):
                    instruction_text = line.replace("ATC:", "").strip()
                elif line.startswith("PILOT:"):
                    readback_text = line.replace("PILOT:", "").strip()

        if not instruction_text:
            self.validation_text.delete(1.0, tk.END)
            self.validation_text.insert(
                tk.END,
                "❌ No instruction to validate. Please generate an instruction first.",
            )
            return

        validation_results = []
        tips = []

        # Basic validation checks
        if len(instruction_text) < 10:
            validation_results.append("⚠️ Instruction seems too short")
            tips.append("• Ensure the instruction contains all necessary information")

        if not any(
            word in instruction_text.upper()
            for word in ["CLEARED", "APPROVED", "CONTACT", "HOLD", "EXPECT"]
        ):
            validation_results.append(
                "⚠️ Instruction may be missing standard ATC keywords"
            )
            tips.append(
                "• Use standard ATC phraseology (cleared, approved, contact, etc.)"
            )

        # Check for callsign
        if not any(char.isdigit() for char in instruction_text):
            validation_results.append("⚠️ No callsign or aircraft identifier found")
            tips.append("• Include the aircraft callsign in your instruction")

        # Check for runway/altitude/heading
        if not any(
            word in instruction_text.upper()
            for word in ["RUNWAY", "RWY", "ALTITUDE", "HEADING", "HDG"]
        ):
            validation_results.append("⚠️ Missing key operational parameters")
            tips.append("• Include runway, altitude, or heading as appropriate")

        # Check readback
        if not readback_text:
            validation_results.append("⚠️ No readback provided")
            tips.append("• Always provide a proper readback for the instruction")

        # Positive feedback
        if len(instruction_text) > 20 and any(
            word in instruction_text.upper() for word in ["CLEARED", "APPROVED"]
        ):
            validation_results.append("✅ Instruction appears well-formed")

        # Display results
        self.validation_text.delete(1.0, tk.END)

        if validation_results:
            self.validation_text.insert(tk.END, "Validation Results:\n")
            for result in validation_results:
                self.validation_text.insert(tk.END, f"{result}\n")

        if tips:
            self.validation_text.insert(tk.END, "\nTips:\n")
            for tip in tips:
                self.validation_text.insert(tk.END, f"{tip}\n")

        # Add general tips based on instruction type
        selected_instruction = self.instruction_type_combo.get()
        if selected_instruction:
            self.validation_text.insert(
                tk.END, f"\nInstruction Type: {selected_instruction}\n"
            )

            if "taxi" in selected_instruction.lower():
                self.validation_text.insert(
                    tk.END, "• Include taxi route and hold short instructions\n"
                )
            elif "takeoff" in selected_instruction.lower():
                self.validation_text.insert(
                    tk.END, "• Include runway, heading, and initial altitude\n"
                )
            elif "landing" in selected_instruction.lower():
                self.validation_text.insert(
                    tk.END,
                    "• Include runway, approach type, and contact instructions\n",
                )

        self.status_var.set("Status: Instruction validation completed")

    def on_ai_atc_mode_change(self, event=None):
        """Handle AI ATC mode change"""
        mode = self.ai_atc_mode_var.get()

        if mode == "Scenario":
            self.ai_atc_status.config(text="🎯 Scenario Mode", foreground="blue")
            self.generate_scenario_btn.config(state="normal")
            self.start_conversation_btn.config(state="normal")
        elif mode == "Conversation":
            self.ai_atc_status.config(text="💬 Conversation Mode", foreground="green")
            self.generate_scenario_btn.config(state="disabled")
            self.start_conversation_btn.config(state="normal")
        elif mode == "Traffic Management":
            self.ai_atc_status.config(text="✈️ Traffic Management", foreground="orange")
            self.generate_scenario_btn.config(state="normal")
            self.start_conversation_btn.config(state="normal")
        elif mode == "Emergency":
            self.ai_atc_status.config(text="🚨 Emergency Mode", foreground="red")
            self.generate_scenario_btn.config(state="normal")
            self.start_conversation_btn.config(state="normal")

        self.update_ai_atc_info()

    def generate_ai_atc_scenario(self):
        """Generate an AI ATC scenario"""
        if not self.ai_handler or not self.ai_handler.is_ai_available():
            messagebox.showwarning(
                "AI Not Available",
                "AI ATC is not available. Please check your Ollama connection.",
            )
            return

        mode = self.ai_atc_mode_var.get()
        airport = self.airport_var.get()

        self.show_ai_processing("Generating AI ATC scenario...")
        self.status_var.set("Status: Generating AI ATC scenario...")

        # Generate scenario based on mode
        scenario_prompt = self.get_scenario_prompt(mode, airport)

        try:
            # Use AI to generate scenario
            scenario = self.ai_handler.generate_atc_response(
                pilot_message=scenario_prompt,
                aircraft_info={"callsign": "PILOT", "aircraft_type": "Aircraft"},
                airport_info=self.airports.get(airport, {}),
                response_type="scenario",
            )

            # Debug: Print the scenario to console
            logger.debug("AI ATC Scenario: %s", scenario)

            if scenario and scenario.strip():
                self.ai_atc_conversation.delete(1.0, tk.END)
                self.ai_atc_conversation.insert(
                    tk.END, f"🎯 AI ATC Scenario ({mode}):\n\n{scenario}\n\n"
                )
                self.ai_atc_conversation.see(tk.END)
                self.update_ai_atc_info()
                self.status_var.set("Status: AI ATC scenario generated")
            else:
                self.ai_atc_conversation.delete(1.0, tk.END)
                self.ai_atc_conversation.insert(
                    tk.END,
                    f"❌ Failed to generate {mode} scenario. Please try again.\n\n",
                )
                self.status_var.set("Status: Failed to generate scenario")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to generate scenario: {str(e)}")
            self.status_var.set("Status: Error generating scenario")
        finally:
            self.hide_ai_processing()

    def get_scenario_prompt(self, mode, airport):
        """Get scenario prompt based on mode"""
        prompts = {
            "Scenario": f"Generate a realistic ATC scenario at {airport}. Include multiple aircraft, weather conditions, and typical ATC communications.",
            "Conversation": f"Create a conversational ATC scenario at {airport} where a pilot requests clearance and ATC responds with instructions.",
            "Traffic Management": f"Generate a traffic management scenario at {airport} with multiple aircraft requiring coordination and sequencing.",
            "Emergency": f"Create an emergency scenario at {airport} requiring immediate ATC response and emergency procedures.",
        }
        return prompts.get(mode, prompts["Scenario"])

    def start_ai_atc_conversation(self):
        """Start an AI ATC conversation"""
        if not self.ai_handler or not self.ai_handler.is_ai_available():
            messagebox.showwarning(
                "AI Not Available",
                "AI ATC is not available. Please check your Ollama connection.",
            )
            return

        # Clear previous conversation
        self.ai_atc_conversation.delete(1.0, tk.END)

        # Start with initial ATC contact
        initial_message = (
            f"🎯 AI ATC at {self.airport_var.get()} - Ready for your call\n\n"
        )
        self.ai_atc_conversation.insert(tk.END, initial_message)

        # Generate initial ATC greeting
        self.show_ai_processing("Starting AI ATC conversation...")

        try:
            greeting = self.ai_handler.generate_atc_response(
                pilot_message="Initial contact with ATC",
                aircraft_info={"callsign": "PILOT", "aircraft_type": "Aircraft"},
                airport_info=self.airports.get(self.airport_var.get(), {}),
                response_type="greeting",
            )

            # Debug: Print the greeting to console
            logger.debug("AI ATC Greeting: %s", greeting)

            if greeting and greeting.strip():
                self.ai_atc_conversation.insert(tk.END, f"ATC: {greeting}\n\n")
                self.ai_atc_conversation.see(tk.END)
                self.status_var.set("Status: AI ATC conversation started")
            else:
                self.ai_atc_conversation.insert(
                    tk.END, "ATC: WSSS Traffic, go ahead.\n\n"
                )
                self.ai_atc_conversation.see(tk.END)
                self.status_var.set("Status: AI ATC conversation started")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to start conversation: {str(e)}")
            self.status_var.set("Status: Error starting conversation")
        finally:
            self.hide_ai_processing()

    def send_ai_atc_response(self):
        """Send pilot response to AI ATC"""
        if not self.ai_handler or not self.ai_handler.is_ai_available():
            messagebox.showwarning("AI Not Available", "AI ATC is not available.")
            return

        pilot_message = self.ai_atc_input.get(1.0, tk.END).strip()
        if not pilot_message:
            messagebox.showwarning("No Message", "Please enter your response.")
            return

        # Add pilot message to conversation
        self.ai_atc_conversation.insert(tk.END, f"PILOT: {pilot_message}\n")
        self.ai_atc_conversation.see(tk.END)

        # Clear input
        self.ai_atc_input.delete(1.0, tk.END)

        # Generate AI ATC response
        self.show_ai_processing("AI ATC is responding...")

        try:
            atc_response = self.ai_handler.generate_atc_response(
                pilot_message=pilot_message,
                aircraft_info={"callsign": "PILOT", "aircraft_type": "Aircraft"},
                airport_info=self.airports.get(self.airport_var.get(), {}),
                response_type="atc_response",
            )

            # Debug: Print the response to console
            logger.debug("AI ATC Response: %s", atc_response)

            if atc_response and atc_response.strip():
                self.ai_atc_conversation.insert(tk.END, f"ATC: {atc_response}\n\n")
                self.ai_atc_conversation.see(tk.END)
                self.status_var.set("Status: AI ATC responded")
            else:
                self.ai_atc_conversation.insert(tk.END, "ATC: Say again, please.\n\n")
                self.ai_atc_conversation.see(tk.END)
                self.status_var.set("Status: AI ATC requested repeat")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to get ATC response: {str(e)}")
            self.status_var.set("Status: Error getting ATC response")
        finally:
            self.hide_ai_processing()

    def clear_ai_atc_conversation(self):
        """Clear the AI ATC conversation"""
        self.ai_atc_conversation.delete(1.0, tk.END)
        self.ai_atc_input.delete(1.0, tk.END)
        self.status_var.set("Status: AI ATC conversation cleared")

    def request_clearance(self):
        """Request clearance from AI ATC"""
        if not self.ai_handler or not self.ai_handler.is_ai_available():
            messagebox.showwarning("AI Not Available", "AI ATC is not available.")
            return

        # Add clearance request to conversation
        clearance_request = "Request clearance for departure"
        self.ai_atc_conversation.insert(tk.END, f"PILOT: {clearance_request}\n")
        self.ai_atc_conversation.see(tk.END)

        # Generate AI ATC clearance
        self.show_ai_processing("AI ATC processing clearance...")

        try:
            clearance = self.ai_handler.generate_atc_response(
                pilot_message=clearance_request,
                aircraft_info={"callsign": "PILOT", "aircraft_type": "Aircraft"},
                airport_info=self.airports.get(self.airport_var.get(), {}),
                response_type="clearance",
            )

            if clearance:
                self.ai_atc_conversation.insert(tk.END, f"ATC: {clearance}\n\n")
                self.ai_atc_conversation.see(tk.END)
                self.status_var.set("Status: AI ATC clearance provided")
            else:
                self.ai_atc_conversation.insert(
                    tk.END, "ATC: Standby for clearance.\n\n"
                )
                self.ai_atc_conversation.see(tk.END)
                self.status_var.set("Status: AI ATC processing clearance")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to get clearance: {str(e)}")
            self.status_var.set("Status: Error getting clearance")
        finally:
            self.hide_ai_processing()

    def report_position(self):
        """Report position to AI ATC"""
        if not self.ai_handler or not self.ai_handler.is_ai_available():
            messagebox.showwarning("AI Not Available", "AI ATC is not available.")
            return

        # Add position report to conversation
        position_report = "Position report: 5 miles north of airport, 3000 feet"
        self.ai_atc_conversation.insert(tk.END, f"PILOT: {position_report}\n")
        self.ai_atc_conversation.see(tk.END)

        # Generate AI ATC acknowledgment
        self.show_ai_processing("AI ATC acknowledging position...")

        try:
            acknowledgment = self.ai_handler.generate_atc_response(
                pilot_message=position_report,
                aircraft_info={"callsign": "PILOT", "aircraft_type": "Aircraft"},
                airport_info=self.airports.get(self.airport_var.get(), {}),
                response_type="acknowledgment",
            )

            if acknowledgment:
                self.ai_atc_conversation.insert(tk.END, f"ATC: {acknowledgment}\n\n")
                self.ai_atc_conversation.see(tk.END)
                self.status_var.set("Status: AI ATC acknowledged position")
            else:
                self.ai_atc_conversation.insert(
                    tk.END, "ATC: Roger, position noted.\n\n"
                )
                self.ai_atc_conversation.see(tk.END)
                self.status_var.set("Status: AI ATC noted position")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to get acknowledgment: {str(e)}")
            self.status_var.set("Status: Error getting acknowledgment")
        finally:
            self.hide_ai_processing()

    def update_ai_atc_info(self):
        """Update AI ATC information display"""
        mode = self.ai_atc_mode_var.get()
        airport = self.airport_var.get()

        info_text = f"AI ATC System Status:\n"
        info_text += f"Mode: {mode}\n"
        info_text += f"Airport: {airport}\n"
        info_text += f"AI Available: {'Yes' if self.ai_handler and self.ai_handler.is_ai_available() else 'No'}\n\n"

        if mode == "Scenario":
            info_text += "Generate realistic ATC scenarios with multiple aircraft and weather conditions."
        elif mode == "Conversation":
            info_text += "Interactive conversation with AI ATC. Practice your radio communications."
        elif mode == "Traffic Management":
            info_text += "AI ATC manages multiple aircraft with traffic coordination and sequencing."
        elif mode == "Emergency":
            info_text += "AI ATC handles emergency situations with priority clearances and procedures."

        self.ai_atc_info.delete(1.0, tk.END)
        self.ai_atc_info.insert(tk.END, info_text)

    def test_ai_atc(self):
        """Test AI ATC functionality"""
        if not self.ai_handler or not self.ai_handler.is_ai_available():
            messagebox.showwarning("AI Not Available", "AI ATC is not available.")
            return

        # Clear conversation
        self.ai_atc_conversation.delete(1.0, tk.END)

        # Test message
        test_message = "WSSS Traffic, this is 9V-SIA, request taxi for departure"
        self.ai_atc_conversation.insert(tk.END, f"PILOT: {test_message}\n")

        # Generate AI response
        self.show_ai_processing("Testing AI ATC...")

        try:
            atc_response = self.ai_handler.generate_atc_response(
                pilot_message=test_message,
                aircraft_info={"callsign": "9V-SIA", "aircraft_type": "Boeing 737"},
                airport_info=self.airports.get(self.airport_var.get(), {}),
                response_type="atc_response",
            )

            logger.debug("Test AI ATC Response: %s", atc_response)

            if atc_response and atc_response.strip():
                self.ai_atc_conversation.insert(tk.END, f"ATC: {atc_response}\n\n")
                self.ai_atc_conversation.see(tk.END)
                self.status_var.set("Status: AI ATC test successful")
            else:
                self.ai_atc_conversation.insert(tk.END, "ATC: Say again, please.\n\n")
                self.ai_atc_conversation.see(tk.END)
                self.status_var.set("Status: AI ATC test failed")

        except Exception as e:
            messagebox.showerror("Error", f"AI ATC test failed: {str(e)}")
            self.status_var.set("Status: AI ATC test error")
        finally:
            self.hide_ai_processing()

    def on_difficulty_change(self, event=None):
        """Handle difficulty level change"""
        difficulty = self.difficulty_var.get()

        # Update instruction types based on difficulty
        if difficulty == "Beginner":
            # Show only basic instructions
            available_types = [
                t
                for t in self.atc.get_all_instruction_types()
                if any(word in t.lower() for word in ["taxi", "takeoff", "landing"])
            ]
        elif difficulty == "Intermediate":
            # Show most instructions except complex ones
            available_types = [
                t
                for t in self.atc.get_all_instruction_types()
                if not any(
                    word in t.lower() for word in ["emergency", "complex", "holding"]
                )
            ]
        elif difficulty == "Advanced":
            # Show all instructions
            available_types = self.atc.get_all_instruction_types()
        else:  # Expert
            # Show all instructions including complex ones
            available_types = self.atc.get_all_instruction_types()

        # Update the instruction type combo
        current_selection = self.instruction_type_combo.get()
        self.instruction_type_combo["values"] = available_types

        # Try to keep the same selection if it's still available
        if current_selection in available_types:
            self.instruction_type_combo.set(current_selection)
        elif available_types:
            self.instruction_type_combo.set(available_types[0])
            self.on_instruction_select(None)

        self.status_var.set(f"Status: Difficulty set to {difficulty}")

    def get_difficulty_modifier(self):
        """Get AI prompt modifier based on difficulty level"""
        difficulty = self.difficulty_var.get()

        modifiers = {
            "Beginner": "Use simple, clear language. Avoid complex procedures. Focus on basic ATC phraseology.",
            "Intermediate": "Use standard ATC phraseology. Include moderate complexity procedures.",
            "Advanced": "Use professional ATC phraseology. Include complex procedures and multiple clearances.",
            "Expert": "Use advanced ATC phraseology. Include complex procedures, multiple clearances, and emergency scenarios.",
        }

        return modifiers.get(difficulty, modifiers["Intermediate"])

    def reset_settings(self):
        """Reset settings to defaults"""
        if messagebox.askyesno(
            "Reset Settings", "Are you sure you want to reset all settings to defaults?"
        ):
            if self.config.reset_to_defaults():
                messagebox.showinfo(
                    "Settings",
                    "Settings reset to defaults. Restart the application for changes to take effect.",
                )
            else:
                messagebox.showerror("Settings", "Failed to reset settings!")


def run_app():
    """Run the application"""
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop()
