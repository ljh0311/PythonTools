import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import requests
import random
import math
import re
import os
import json
from typing import Dict, Optional, Tuple

from utils.trainee_situation import build_atc_traffic_strip_line
from utils.ai_response_handler import AIResponseHandler
from utils.logging_config import get_logger
from utils.simulator_bridge import SimulatorBridge, SimState
from data.scenarios.scenario_engine import ScenarioEngine, DifficultyLevel, ScenarioType
from assessment.assessment_engine import AssessmentEngine
from utils.progress_tracker import ProgressTracker
from utils.report_generator import ReportGenerator
from utils.airport_path_graph import AirportPathGraph
from utils.atc_npc_system import ATCNpcController
from utils.airport_diagram_theme import (
    DEFAULT_DIAGRAM_THEME,
    compute_diagram_layout,
    runway_centerline_dash,
)

logger = get_logger(__name__)


class ATCWindow:
    def __init__(self, root, config, airports, preferred_airport=None):
        self.root = root
        self.config = config
        self.airports = airports
        
        # Set the current airport - use preferred_airport if provided, otherwise default to first
        if preferred_airport and preferred_airport in airports:
            self.current_airport = preferred_airport
        else:
            self.current_airport = list(airports.keys())[0]  # Default to first airport
        
        # Initialize AI response handler
        self.ai_handler = AIResponseHandler(config)
        self.ai_handler.set_ui_update_callback(self.on_ai_response_generated)
        logger.debug("AI callback set: %s", self.ai_handler.ui_update_callback)
        logger.debug("Callback method: %s", self.on_ai_response_generated)
        
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

        # Session state
        self.current_session_active = False
        self.current_scenario = None
        self.session_start_time = None
        self.active_aircraft = {}  # Dictionary of aircraft in the scenario
        self._npc_controller: Optional[ATCNpcController] = None
        self._npc_tick_id: Optional[str] = None
        self.communication_history = []  # Track all communications for assessment
        self.atc_training_metrics = {
            "clearances_issued": 0,
            "critical_clearances": 0,
            "high_risk_clearances": 0,
        }
        self.last_debrief_text = ""
        self.last_debrief_path = ""
        
        # Enrich airport data with dynamic content
        self.enrich_airport_data()

        # Editable taxi/runway path graph (per ICAO, saved under data/airports/path_graphs/)
        self._path_graph_cached_icao: Optional[str] = None
        self._path_graph_obj: Optional[AirportPathGraph] = None
        self._path_link_first: Optional[str] = None
        self.path_edit_mode_var = tk.StringVar(value="off")
        self.path_node_label_var = tk.StringVar(value="")
        self.path_show_schematic_var = tk.BooleanVar(value=True)
        self._traffic_anim: Dict[str, dict] = {}
        self._traffic_prev_xy: Dict[str, Tuple[float, float]] = {}
        self._traffic_anim_job: Optional[str] = None

        # ATC trainee: Ground tab strip tracks **selected traffic**, not "your" pilot position
        self._atc_strip_last_ground_tx: str = ""
        self._atc_strip_last_pilot_log_line: str = ""

        # X-Plane / FlyWithLua simulator bridge (optional)
        self.sim_bridge: Optional[SimulatorBridge] = None
        self._sim_bridge_enabled = bool(config.get("xplane_bridge_enabled", False))
        self._setup_simulator_bridge()

        self.setup_ui()

    def setup_ui(self):
        """Set up the main UI with session-based training workflow"""
        # Configure main window
        self.root.title("ATC Training System")
        self.root.geometry("1400x900")
        
        # Create main frame (fills root)
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header frame for airport selection and weather
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        
        # Airport selection (left side of header)
        airport_frame = ttk.Frame(header_frame)
        airport_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(airport_frame, text="Airport:").pack(side=tk.LEFT, padx=(0, 5))
        self.airport_var = tk.StringVar()
        self.airport_combo = ttk.Combobox(
            airport_frame, 
            textvariable=self.airport_var,
            values=list(self.airports.keys()),
            state="readonly",
            width=15
        )
        self.airport_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        if list(self.airports.keys()):
            try:
                current_index = list(self.airports.keys()).index(self.current_airport)
                self.airport_combo.current(current_index)
            except ValueError:
                self.airport_combo.current(0)
                self.current_airport = list(self.airports.keys())[0]
        
        self.airport_combo.bind("<<ComboboxSelected>>", self.on_airport_change)

        self.data_manager_btn = ttk.Button(
            airport_frame,
            text="Manage Data",
            command=self.open_data_manager_dialog,
        )
        self.data_manager_btn.pack(side=tk.LEFT, padx=(5, 5))

        # X-Plane bridge: checkbox and Live indicator
        self.xplane_var = tk.BooleanVar(value=self._sim_bridge_enabled)
        self.xplane_cb = ttk.Checkbutton(
            airport_frame,
            text="Use X-Plane context",
            variable=self.xplane_var,
            command=self._on_xplane_bridge_toggle,
        )
        self.xplane_cb.pack(side=tk.LEFT, padx=(15, 5))
        self.live_icao_label = ttk.Label(
            airport_frame,
            text="Live: ---",
            font=("Arial", 9),
            foreground="gray",
        )
        self.live_icao_label.pack(side=tk.LEFT, padx=(0, 5))
        if self.sim_bridge and self._sim_bridge_enabled:
            state = self.sim_bridge.get_state()
            if state.icao:
                self.live_icao_label.config(text=f"Live: {state.icao}", foreground="green")

        # AI Status indicator
        self.ai_status_label = ttk.Label(
            airport_frame,
            text="🤖 AI: Checking...",
            font=("Arial", 9),
            foreground="gray"
        )
        self.ai_status_label.pack(side=tk.LEFT, padx=(10, 0))

        ttk.Label(airport_frame, text="Your role:").pack(side=tk.LEFT, padx=(12, 4))
        self.training_role_var = tk.StringVar(
            value="Tower (combined — surface + runway)"
        )
        self.training_role_combo = ttk.Combobox(
            airport_frame,
            textvariable=self.training_role_var,
            state="readonly",
            width=36,
            values=(
                "Tower (combined — surface + runway)",
                "Ground (surface / taxi only)",
                "Approach / Arrival (radar / sequence)",
            ),
        )
        self.training_role_combo.pack(side=tk.LEFT, padx=(0, 4))
        
        # Weather display (right side of header)
        self.weather_frame = ttk.LabelFrame(header_frame, text="Current Weather")
        self.weather_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.weather_display = ttk.Label(
            self.weather_frame,
            text="No weather data available",
            font=("Arial", 9)
        )
        self.weather_display.pack(padx=10, pady=5)
        
        # Main content area - 3 panel layout
        content_paned = ttk.PanedWindow(self.main_frame, orient=tk.HORIZONTAL)
        content_paned.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Left Panel: Session Controls & Aircraft Summary
        left_frame = ttk.Frame(content_paned, width=300)
        content_paned.add(left_frame, weight=1)
        self.setup_left_panel(left_frame)
        
        # Center Panel: Main Radar/Airport View
        center_frame = ttk.Frame(content_paned)
        content_paned.add(center_frame, weight=3)
        self.setup_center_panel(center_frame)
        
        # Right Panel: Communication & Quick Actions
        right_frame = ttk.Frame(content_paned, width=350)
        content_paned.add(right_frame, weight=1)
        self.setup_right_panel(right_frame)
        
        # Status bar (bottom of main frame)
        self.status_bar = ttk.Label(
            self.main_frame, 
            text="Status: Ready - Select a scenario and start training session",
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Initialize weather update timer
        self.auto_weather_update = False
        self.weather_update_interval = 15 * 60 * 1000
        self.weather_update_id = None

        # Check AI status after UI is loaded
        self.root.after(500, self.update_ai_status_indicator)

        # Initialize weather display and airport config
        self.update_airport_config()
        self.update_weather_display()
        
        # Initialize scenario list
        self.available_scenarios = {}
        self.update_scenario_list()

    def _get_data_directory(self):
        """Return absolute path to the project data directory."""
        return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")

    def _get_data_json_files(self):
        """Return sorted JSON files under data directory as relative paths."""
        data_dir = self._get_data_directory()
        files = []
        for root_dir, _, filenames in os.walk(data_dir):
            for name in filenames:
                if name.lower().endswith(".json"):
                    full_path = os.path.join(root_dir, name)
                    files.append(os.path.relpath(full_path, data_dir).replace("\\", "/"))
        return sorted(files)

    def open_data_manager_dialog(self):
        """Open a dialog to load/edit/add JSON data entries from data directory."""
        dialog = tk.Toplevel(self.root)
        dialog.title("Data Manager")
        dialog.geometry("900x600")
        dialog.transient(self.root)
        dialog.grab_set()

        controls = ttk.Frame(dialog, padding=8)
        controls.pack(fill=tk.X)

        ttk.Label(controls, text="Dataset:").pack(side=tk.LEFT)
        dataset_var = tk.StringVar()
        dataset_combo = ttk.Combobox(controls, textvariable=dataset_var, state="readonly", width=50)
        dataset_combo.pack(side=tk.LEFT, padx=(6, 6))

        editor = scrolledtext.ScrolledText(dialog, wrap=tk.WORD, font=("Consolas", 10))
        editor.pack(fill=tk.BOTH, expand=True, padx=8, pady=(0, 8))

        status_var = tk.StringVar(value="Select a dataset to start editing.")
        status_label = ttk.Label(dialog, textvariable=status_var, anchor=tk.W)
        status_label.pack(fill=tk.X, padx=8, pady=(0, 8))

        data_dir = self._get_data_directory()

        def selected_path():
            relative = dataset_var.get().strip()
            if not relative:
                return None
            return os.path.join(data_dir, relative.replace("/", os.sep))

        def load_selected():
            path = selected_path()
            if not path:
                status_var.set("No dataset selected.")
                return
            if not os.path.exists(path):
                status_var.set("Selected dataset does not exist.")
                return
            try:
                with open(path, "r", encoding="utf-8") as f:
                    content = json.load(f)
                editor.delete("1.0", tk.END)
                editor.insert(tk.END, json.dumps(content, indent=2, ensure_ascii=False))
                status_var.set(f"Loaded: {dataset_var.get()}")
            except (OSError, json.JSONDecodeError) as e:
                messagebox.showerror("Load Error", f"Failed to load dataset:\n{e}")
                status_var.set("Load failed.")

        def save_selected():
            path = selected_path()
            if not path:
                status_var.set("No dataset selected.")
                return
            raw_text = editor.get("1.0", tk.END).strip()
            if not raw_text:
                messagebox.showwarning("Empty Content", "Editor is empty. Add valid JSON before saving.")
                return
            try:
                parsed = json.loads(raw_text)
            except json.JSONDecodeError as e:
                messagebox.showerror("Invalid JSON", f"Please fix JSON first:\n{e}")
                return

            try:
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(parsed, f, indent=2, ensure_ascii=False)
                    f.write("\n")
                status_var.set(f"Saved: {dataset_var.get()}")
                self._refresh_runtime_data_after_edit(dataset_var.get(), parsed)
            except OSError as e:
                messagebox.showerror("Save Error", f"Failed to save dataset:\n{e}")
                status_var.set("Save failed.")

        def add_entry_template():
            try:
                parsed = json.loads(editor.get("1.0", tk.END).strip() or "{}")
            except json.JSONDecodeError:
                messagebox.showwarning("Invalid JSON", "Fix JSON before using Add Entry.")
                return

            # Simple helper to accelerate adding objects to common list-based datasets.
            inserted = False
            if isinstance(parsed, dict):
                for key in ("airports", "scenarios", "emergencies", "checklists", "records"):
                    if key in parsed and isinstance(parsed[key], list):
                        parsed[key].append({"id": "new_id", "name": "New Item"})
                        inserted = True
                        break
                if not inserted:
                    parsed["new_item"] = {"id": "new_id", "name": "New Item"}
                    inserted = True
            elif isinstance(parsed, list):
                parsed.append({"id": "new_id", "name": "New Item"})
                inserted = True

            if inserted:
                editor.delete("1.0", tk.END)
                editor.insert(tk.END, json.dumps(parsed, indent=2, ensure_ascii=False))
                status_var.set("Inserted a new entry template. Edit values, then save.")

        def refresh_dataset_list():
            files = self._get_data_json_files()
            dataset_combo["values"] = files
            if files and not dataset_var.get():
                dataset_var.set(files[0])
                load_selected()

        ttk.Button(controls, text="Reload List", command=refresh_dataset_list).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(controls, text="Load", command=load_selected).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(controls, text="Add Entry", command=add_entry_template).pack(side=tk.LEFT, padx=(0, 6))
        ttk.Button(controls, text="Save", command=save_selected).pack(side=tk.LEFT)

        dataset_combo.bind("<<ComboboxSelected>>", lambda _event: load_selected())
        refresh_dataset_list()

    def _refresh_runtime_data_after_edit(self, relative_dataset_path, parsed_content):
        """Refresh in-memory airport/scenario data if related dataset changed."""
        normalized = relative_dataset_path.replace("\\", "/").lower()
        if normalized == "airports/airport_info.json":
            # Keep runtime list in sync after airport edits.
            airports = {}
            for airport in parsed_content.get("airports", []):
                icao = airport.get("airport_icao", "----")
                name = airport.get("airport_name", "Unknown Airport")
                key = f"{icao} - {name}"
                runways = [r.get("designation", "") for r in airport.get("runways", []) if isinstance(r, dict)]
                taxiways = [t.get("name", "") for t in airport.get("taxiways", []) if isinstance(t, dict)]
                gates = [g.get("gate_number", "") for g in airport.get("gates", []) if isinstance(g, dict)]
                airports[key] = {
                    "icao": icao,
                    "name": name,
                    "runways": [x for x in runways if x],
                    "taxiways": [x for x in taxiways if x],
                    "gates": [x for x in gates if x],
                    "wind": "Calm",
                    "visibility": "10 miles",
                    "ceiling": "Clear",
                }

            if airports:
                self.airports = airports
                self.airport_combo["values"] = list(self.airports.keys())
                if self.current_airport not in self.airports:
                    self.current_airport = list(self.airports.keys())[0]
                self.airport_var.set(self.current_airport)
                self.update_airport_config()
                self.update_weather_display()
                self.refresh_airport_view()
                self.status_bar.config(text="Status: Airport data refreshed from edited dataset")

    def setup_left_panel(self, parent):
        """Set up left panel: Session controls, scenario selection, aircraft summary"""
        # Session Controls Section
        session_frame = ttk.LabelFrame(parent, text="Session Controls", padding=5)
        session_frame.pack(fill=tk.X, pady=(0, 10))

        self.session_status_label = ttk.Label(
            session_frame, text="Status: Inactive", font=("Arial", 9, "bold"), foreground="gray"
        )
        self.session_status_label.pack(anchor=tk.W, pady=(0, 5))

        self.start_session_btn = ttk.Button(
            session_frame,
            text="Start Training Session",
            command=self.start_atc_session,
        )
        self.start_session_btn.pack(fill=tk.X, pady=(0, 5))

        self.end_session_btn = ttk.Button(
            session_frame,
            text="End Session",
            command=self.end_atc_session,
            state=tk.DISABLED,
        )
        self.end_session_btn.pack(fill=tk.X)

        # Live training insight section (UI/UX + traffic awareness)
        insight_frame = ttk.LabelFrame(parent, text="Training Insights", padding=5)
        insight_frame.pack(fill=tk.X, pady=(0, 10))
        self.workload_label = ttk.Label(insight_frame, text="Workload: Low")
        self.workload_label.pack(anchor=tk.W)
        self.conflict_label = ttk.Label(insight_frame, text="Runway Conflicts: None")
        self.conflict_label.pack(anchor=tk.W)
        self.recommendation_label = ttk.Label(
            insight_frame,
            text="Recommendation: Start a session to activate live advisories.",
            wraplength=260,
            justify=tk.LEFT,
        )
        self.recommendation_label.pack(anchor=tk.W, pady=(4, 0))

        # Scenario Selection Section
        scenario_frame = ttk.LabelFrame(parent, text="Scenario Selection", padding=5)
        scenario_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(scenario_frame, text="Scenario:").pack(anchor=tk.W, pady=(0, 2))
        self.scenario_var = tk.StringVar()
        self.scenario_combo = ttk.Combobox(
            scenario_frame,
            textvariable=self.scenario_var,
            state="readonly",
            width=25,
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
            width=20,
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
            width=20,
        )
        type_combo.pack(fill=tk.X, pady=(0, 5))
        type_combo.bind("<<ComboboxSelected>>", lambda e: self.update_scenario_list())

        # Scenario description
        ttk.Label(scenario_frame, text="Description:").pack(anchor=tk.W, pady=(5, 2))
        self.scenario_description = scrolledtext.ScrolledText(
            scenario_frame, height=4, wrap=tk.WORD, font=("Arial", 8), state=tk.DISABLED
        )
        self.scenario_description.pack(fill=tk.X)

        # Active Aircraft Summary Section
        aircraft_frame = ttk.LabelFrame(parent, text="Active Aircraft", padding=5)
        aircraft_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        # Aircraft list
        aircraft_list_frame = ttk.Frame(aircraft_frame)
        aircraft_list_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("Callsign", "Type", "Airline", "Status", "Position")
        self.aircraft_tree = ttk.Treeview(aircraft_list_frame, columns=columns, show="headings", height=10)
        widths = {"Callsign": 72, "Type": 76, "Airline": 88, "Status": 96, "Position": 110}
        for col in columns:
            self.aircraft_tree.heading(col, text=col)
            self.aircraft_tree.column(col, width=widths.get(col, 72), anchor="w")
        
        aircraft_scrollbar = ttk.Scrollbar(aircraft_list_frame, orient="vertical", command=self.aircraft_tree.yview)
        self.aircraft_tree.configure(yscrollcommand=aircraft_scrollbar.set)
        
        self.aircraft_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        aircraft_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Bind aircraft selection
        self.aircraft_tree.bind("<<TreeviewSelect>>", self.on_aircraft_select)

    def setup_center_panel(self, parent):
        """Set up center panel: Main radar/airport view"""
        # Main view frame
        view_frame = ttk.LabelFrame(parent, text="Airport View / Radar", padding=5)
        view_frame.pack(fill=tk.BOTH, expand=True)

        self._setup_path_editor_toolbar(view_frame)

        # Canvas for airport diagram/radar
        self.airport_canvas = tk.Canvas(view_frame, bg="#1a1a2e", highlightthickness=1)
        self.airport_canvas.pack(fill=tk.BOTH, expand=True)
        self.airport_canvas.bind("<Configure>", lambda event: self.draw_airport_diagram(event.widget))
        self.airport_canvas.bind("<Button-1>", self._on_path_canvas_click)
        self.airport_canvas.bind("<Button-3>", self._on_path_canvas_right_click)

        # Control buttons below canvas
        control_frame = ttk.Frame(view_frame)
        control_frame.pack(fill=tk.X, pady=(5, 0))

        ttk.Button(control_frame, text="Refresh View", command=self.refresh_airport_view).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Zoom In", command=self.zoom_in).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Zoom Out", command=self.zoom_out).pack(side=tk.LEFT, padx=5)

    def setup_right_panel(self, parent):
        """Set up right panel: Communication log, quick actions, assessment"""
        # Communication Log Section
        comm_frame = ttk.LabelFrame(parent, text="Communication Log", padding=5)
        comm_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.communication_log = scrolledtext.ScrolledText(
            comm_frame, wrap=tk.WORD, font=("Consolas", 9), state=tk.DISABLED, height=15
        )
        self.communication_log.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for styling
        self.communication_log.tag_config("atc", foreground="blue", font=("Consolas", 9, "bold"))
        self.communication_log.tag_config("pilot", foreground="green", font=("Consolas", 9))
        self.communication_log.tag_config("system", foreground="gray", font=("Consolas", 8))
        self.communication_log.tag_config("error", foreground="red", font=("Consolas", 9))

        # Communication Input Section
        input_frame = ttk.LabelFrame(parent, text="Issue Clearance", padding=5)
        input_frame.pack(fill=tk.X, pady=(0, 10))

        ttk.Label(input_frame, text="Aircraft:").pack(anchor=tk.W, pady=(0, 2))
        self.selected_aircraft_var = tk.StringVar()
        self.aircraft_combo = ttk.Combobox(
            input_frame,
            textvariable=self.selected_aircraft_var,
            state="readonly",
            width=25,
        )
        self.aircraft_combo.pack(fill=tk.X, pady=(0, 5))

        ttk.Label(input_frame, text="Clearance:").pack(anchor=tk.W, pady=(0, 2))
        self.clearance_input = scrolledtext.ScrolledText(
            input_frame, height=3, wrap=tk.WORD, font=("Consolas", 9)
        )
        self.clearance_input.pack(fill=tk.X, pady=(0, 5))

        # Quick action buttons
        quick_frame = ttk.Frame(input_frame)
        quick_frame.pack(fill=tk.X, pady=(0, 5))

        ttk.Button(quick_frame, text="Taxi", command=lambda: self.quick_clearance("taxi")).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="Takeoff", command=lambda: self.quick_clearance("takeoff")).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="Landing", command=lambda: self.quick_clearance("landing")).pack(side=tk.LEFT, padx=2)
        ttk.Button(quick_frame, text="Hold", command=lambda: self.quick_clearance("hold")).pack(side=tk.LEFT, padx=2)
        ttk.Button(
            quick_frame,
            text="Resolve Conflicts",
            command=self.suggest_conflict_resolution,
        ).pack(side=tk.LEFT, padx=2)

        ttk.Button(input_frame, text="Transmit Clearance", command=self.transmit_clearance).pack(fill=tk.X)

        # Assessment Section
        assessment_frame = ttk.LabelFrame(parent, text="Performance Assessment", padding=5)
        assessment_frame.pack(fill=tk.X)

        # Current score
        score_frame = ttk.Frame(assessment_frame)
        score_frame.pack(fill=tk.X, pady=(0, 5))
        ttk.Label(score_frame, text="Current Score:", font=("Arial", 9)).pack(side=tk.LEFT)
        self.atc_score_label = ttk.Label(
            score_frame, text="--", font=("Arial", 12, "bold"), foreground="gray"
        )
        self.atc_score_label.pack(side=tk.RIGHT)

        # Feedback
        ttk.Label(assessment_frame, text="Feedback:", font=("Arial", 9)).pack(anchor=tk.W, pady=(5, 2))
        self.atc_feedback = scrolledtext.ScrolledText(
            assessment_frame, height=4, wrap=tk.WORD, font=("Arial", 8), state=tk.DISABLED
        )
        self.atc_feedback.pack(fill=tk.X)

        # Session Summary
        summary_frame = ttk.LabelFrame(parent, text="Session Summary", padding=5)
        summary_frame.pack(fill=tk.X, pady=(10, 0))

        self.session_summary = scrolledtext.ScrolledText(
            summary_frame, height=3, wrap=tk.WORD, font=("Arial", 8), state=tk.DISABLED
        )
        self.session_summary.pack(fill=tk.X)
        ttk.Button(summary_frame, text="Save Last Debrief", command=self.save_last_debrief).pack(fill=tk.X, pady=(5, 0))

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

    def start_atc_session(self):
        """Start a new ATC training session"""
        if not self.current_scenario:
            messagebox.showwarning("No Scenario", "Please select a scenario first.")
            return
        
        # Reset assessment engine for new session
        if self.assessment_engine:
            self.assessment_engine.reset_session()
        
        # Start session with progress tracker
        if self.progress_tracker:
            controller_id = "ATC_CONTROLLER"  # Could be configurable
            session_id = self.progress_tracker.start_session(
                pilot_id=controller_id,
                scenario_id=self.current_scenario.scenario_id,
                airport_icao=self.current_scenario.airport_icao,
                difficulty=self.current_scenario.difficulty.value,
                metadata={
                    "scenario_name": self.current_scenario.name,
                    "scenario_type": self.current_scenario.scenario_type.value
                }
            )
        
        self._cancel_npc_tick()
        self._npc_controller = ATCNpcController.from_scenario(self.current_scenario)
        pg = self._path_graph()
        self.active_aircraft = self._npc_controller.as_active_aircraft(pg)

        # Set session state
        self.current_session_active = True
        self.session_start_time = time.time()
        self.communication_history = []
        self.atc_training_metrics = {
            "clearances_issued": 0,
            "critical_clearances": 0,
            "high_risk_clearances": 0,
        }
        
        # Update UI
        self.session_status_label.config(text="Status: Active", foreground="green")
        self.start_session_btn.config(state=tk.DISABLED)
        self.end_session_btn.config(state=tk.NORMAL)
        self.scenario_combo.config(state=tk.DISABLED)
        
        # Update aircraft tree
        self.update_aircraft_tree()
        
        # Log session start
        self._log_system_message(f"Training session started: {self.current_scenario.name}")
        self._log_system_message(f"Airport: {self.current_scenario.airport_icao}")
        self._log_system_message(f"Aircraft in scenario: {len(self.active_aircraft)}")
        if self._npc_controller:
            ctx = self._npc_controller.npc_scenario_context
            self._log_system_message(
                f"NPC training context: flow={ctx.primary_flow}, type={ctx.scenario_type}, "
                f"difficulty={ctx.difficulty}. {ctx.npc_brief[:200]}"
            )
        if pg.nodes:
            self._log_system_message(
                f"Map: traffic blips use your path graph ({len(pg.nodes)} nodes) — "
                "taxi/vacate on taxiway nodes; add Holding nodes (or taxi linked to runway) "
                "for hold-short; NPC taxi routes use shortest path on your links."
            )
            self._log_system_message(
                "Departures: outbound traffic holds at the gate / short of runway until you issue "
                "taxi, line-up, and takeoff clearances; blips animate between graph positions."
            )
        self._log_system_message(
            f"Training role: {self.training_role_var.get()} — "
            "Use the header dropdown to match who you are simulating; clearances still train phraseology."
        )
        if not self.current_scenario.traffic_aircraft:
            self._log_system_message(
                "NPC traffic: scenario had no predefined aircraft — procedural traffic spawned. "
                "Ground tab 'Add Aircraft' is separate (manual surface traffic)."
            )
        self._schedule_npc_tick()

        # Update session summary
        self.update_session_summary()

        self.status_bar.config(text="Status: Training session active - Manage traffic and issue clearances")
        self._refresh_operational_insights()

    def end_atc_session(self):
        """End the current ATC training session (non-blocking, so UI won't freeze)"""
        if not self.current_session_active:
            return

        def finish_session():
            # Calculate final assessment
            final_assessment = None
            completed_session_id = None
            if self.progress_tracker and self.progress_tracker.current_session:
                if self.assessment_engine:
                    # Assess overall session (may be slow)
                    final_assessment = self.assessment_engine.assess_session()
                    completed_session_id = self.progress_tracker.complete_session(final_assessment)

            def ui_finalize():
                # Show results (if any)
                if final_assessment is not None:
                    self._show_session_results(final_assessment, completed_session_id)

                # Reset session state
                self.current_session_active = False
                self.session_start_time = None
                self.active_aircraft = {}
                self._npc_controller = None
                self._cancel_npc_tick()
                self._cancel_traffic_blip_anim()
                self.communication_history = []
                self.atc_training_metrics = {
                    "clearances_issued": 0,
                    "critical_clearances": 0,
                    "high_risk_clearances": 0,
                }

                # Update UI
                self.session_status_label.config(text="Status: Inactive", foreground="gray")
                self.start_session_btn.config(state=tk.NORMAL)
                self.end_session_btn.config(state=tk.DISABLED)
                self.scenario_combo.config(state="readonly")

                # Clear aircraft tree
                for item in self.aircraft_tree.get_children():
                    self.aircraft_tree.delete(item)

                # Log session end
                self._log_system_message("Training session ended")

                # Update session summary
                self.update_session_summary()

                self.status_bar.config(text="Status: Session ended - Review results and start a new session")
                self._refresh_operational_insights()

            # UI updates must be run on the main thread
            self.root.after(0, ui_finalize)

        # Run heavy assessment in a background thread to avoid UI freezing
        import threading
        threading.Thread(target=finish_session, daemon=True).start()
    def _cancel_npc_tick(self) -> None:
        if self._npc_tick_id is not None:
            try:
                self.root.after_cancel(self._npc_tick_id)
            except tk.TclError:
                pass
            self._npc_tick_id = None

    def _schedule_npc_tick(self) -> None:
        """Advance NPC flight phases on a timer while a session is active."""
        self._cancel_npc_tick()
        if not self.current_session_active or self._npc_controller is None:
            return
        self._npc_tick_id = self.root.after(4000, self._on_npc_tick)

    def _on_npc_tick(self) -> None:
        self._npc_tick_id = None
        if not self.current_session_active or self._npc_controller is None:
            return
        try:
            for msg in self._npc_controller.tick():
                self._log_system_message(msg)
        except Exception as exc:
            logger.warning("NPC tick failed: %s", exc)
        self.active_aircraft = self._npc_controller.as_active_aircraft(
            self._path_graph()
        )
        self.update_aircraft_tree()
        self._redraw_all_airport_canvases()
        self._refresh_operational_insights()
        self._npc_tick_id = self.root.after(4000, self._on_npc_tick)

    def update_aircraft_tree(self):
        """Update the aircraft tree view with current aircraft"""
        # Clear existing items
        for item in self.aircraft_tree.get_children():
            self.aircraft_tree.delete(item)

        callsigns: list[str] = []
        for callsign, ac_data in self.active_aircraft.items():
            callsigns.append(callsign)
            self.aircraft_tree.insert(
                "",
                tk.END,
                values=(
                    ac_data["callsign"],
                    ac_data["type"],
                    ac_data.get("airline", ""),
                    ac_data["status"],
                    ac_data["position"],
                ),
            )
        if hasattr(self, "aircraft_combo"):
            self.aircraft_combo["values"] = callsigns
            cur = self.selected_aircraft_var.get()
            if callsigns and cur not in callsigns:
                self.selected_aircraft_var.set(callsigns[0])
            elif not callsigns:
                self.selected_aircraft_var.set("")
        self._sync_traffic_anim_from_active()

    def on_aircraft_select(self, event=None):
        """Handle aircraft selection"""
        selection = self.aircraft_tree.selection()
        if selection:
            item = self.aircraft_tree.item(selection[0])
            callsign = item['values'][0]
            self.selected_aircraft_var.set(callsign)

    def transmit_clearance(self):
        """Transmit clearance to selected aircraft"""
        if not self.current_session_active:
            messagebox.showwarning("No Active Session", "Please start a training session first.")
            return
        
        callsign = self.selected_aircraft_var.get()
        if not callsign:
            messagebox.showwarning("No Aircraft Selected", "Please select an aircraft first.")
            return
        
        clearance_text = self.clearance_input.get(1.0, tk.END).strip()
        if not clearance_text:
            messagebox.showwarning("No Clearance", "Please enter a clearance.")
            return
        
        # Log the clearance
        self._log_atc_message(f"{callsign}, {clearance_text}")

        readback_text = ""
        if self._npc_controller:
            npc_lines, _ok = self._npc_controller.apply_clearance(
                callsign, clearance_text, self._path_graph()
            )
            for line in npc_lines:
                self._log_pilot_message(line)
            readback_text = npc_lines[0] if npc_lines else ""
            self.active_aircraft = self._npc_controller.as_active_aircraft(
                self._path_graph()
            )
            self.update_aircraft_tree()
            self._redraw_all_airport_canvases()
        
        # Assess the clearance
        assessment = None
        if self.assessment_engine:
            assessment = self._assess_atc_clearance(clearance_text, callsign)
            self._update_atc_assessment_display(assessment)
            
            # Record in assessment engine for session assessment
            self.assessment_engine.communication_history.append({
                "instruction": clearance_text,  # ATC clearance
                "readback": readback_text,
                "timestamp": time.time(),
                "response_time": None,
                "score": assessment['score']
            })
        
        # Record communication
        self.communication_history.append({
            'time': time.time(),
            'callsign': callsign,
            'clearance': clearance_text,
            'type': 'atc_clearance',
            'assessment': assessment
        })
        self._update_atc_training_metrics(clearance_text, assessment)
        
        # Clear input
        self.clearance_input.delete(1.0, tk.END)
        
        # Update session summary
        self.update_session_summary()
        self._refresh_operational_insights()
        
        self.status_bar.config(text=f"Status: Clearance issued to {callsign}")

    def _update_atc_training_metrics(self, clearance_text, assessment):
        """Track ATC training quality metrics for debriefing."""
        self.atc_training_metrics["clearances_issued"] += 1
        upper = clearance_text.upper()
        critical_terms = ("HOLD SHORT", "LINE UP", "TAKEOFF", "LAND", "CROSS RUNWAY")
        if any(term in upper for term in critical_terms):
            self.atc_training_metrics["critical_clearances"] += 1
        if assessment and assessment.get("score", 100) < 70:
            self.atc_training_metrics["high_risk_clearances"] += 1

    def quick_clearance(self, clearance_type):
        """Generate a quick clearance based on type"""
        callsign = self.selected_aircraft_var.get()
        if not callsign:
            messagebox.showwarning("No Aircraft Selected", "Please select an aircraft first.")
            return
        
        if callsign not in self.active_aircraft:
            return
        
        ac_data = self.active_aircraft[callsign]
        clearance = ""
        
        airport_data = self.airports.get(self.current_airport, {})
        active_runway = self._get_preferred_runway(airport_data)
        wind = airport_data.get("wind", "calm")

        if clearance_type == "taxi":
            clearance = f"{callsign}, taxi to runway {active_runway} via taxiway A, hold short runway {active_runway}"
        elif clearance_type == "takeoff":
            clearance = f"{callsign}, runway {active_runway}, cleared for takeoff, wind {wind}"
        elif clearance_type == "landing":
            clearance = f"{callsign}, runway {active_runway}, cleared to land, wind {wind}"
        elif clearance_type == "hold":
            clearance = f"{callsign}, hold position"
        
        self.clearance_input.delete(1.0, tk.END)
        self.clearance_input.insert(1.0, clearance)

    def _get_preferred_runway(self, airport_data):
        """Pick a runway for phraseology/clearance defaults."""
        runways = airport_data.get("runways", [])
        if runways and isinstance(runways, list):
            return runways[0]
        return "27"

    def _collect_runway_conflicts(self):
        """Collect runway conflict warnings from active arrivals/departures."""
        conflicts = []
        if not hasattr(self, "aircraft_data"):
            return conflicts

        departure = self.aircraft_data.get("departure", {})
        arrival = self.aircraft_data.get("arrival", {})

        dep_by_runway = {}
        for callsign, aircraft in departure.items():
            runway = aircraft.get("runway")
            if runway:
                dep_by_runway.setdefault(runway, []).append((callsign, aircraft.get("status", "")))

        for callsign, aircraft in arrival.items():
            runway = aircraft.get("runway")
            if runway and runway in dep_by_runway:
                conflicts.append(f"{runway}: arrival {callsign} vs departure queue")

        return conflicts

    def _estimate_workload(self):
        """Estimate controller workload from traffic volume and conflicts."""
        total_aircraft = len(self.active_aircraft)
        if hasattr(self, "aircraft_data"):
            total_aircraft += len(self.aircraft_data.get("departure", {}))
            total_aircraft += len(self.aircraft_data.get("arrival", {}))

        conflict_count = len(self._collect_runway_conflicts())
        score = total_aircraft + (conflict_count * 2)

        if score >= 12:
            return "High", score
        if score >= 6:
            return "Medium", score
        return "Low", score

    def _refresh_operational_insights(self):
        """Refresh UI insight labels for workload/conflicts/recommendations."""
        if not hasattr(self, "workload_label"):
            return

        workload, workload_score = self._estimate_workload()
        conflicts = self._collect_runway_conflicts()

        self.workload_label.config(text=f"Workload: {workload} ({workload_score})")
        ctx_note = ""
        if getattr(self, "_npc_controller", None):
            c = self._npc_controller.npc_scenario_context
            ctx_note = f"[{c.primary_flow}] {c.name}. "
        if conflicts:
            self.conflict_label.config(text=f"Runway Conflicts: {len(conflicts)}", foreground="red")
            self.recommendation_label.config(
                text=ctx_note
                + "Recommendation: Sequence arrivals before departures on shared runways and use hold instructions."
            )
        else:
            self.conflict_label.config(text="Runway Conflicts: None", foreground="green")
            if workload == "High":
                self.recommendation_label.config(
                    text=ctx_note
                    + "Recommendation: Slow pace with 'standby' calls and prioritize separation-critical clearances."
                )
            else:
                self.recommendation_label.config(
                    text=ctx_note
                    + "Recommendation: Maintain concise readback/hearback loops for each clearance."
                )

    def _assess_atc_clearance(self, clearance, callsign):
        """Assess an ATC clearance for quality and correctness"""
        errors = []
        warnings = []
        score = 100.0
        
        clearance_upper = clearance.upper()
        
        # Check for callsign in clearance
        if callsign.upper() not in clearance_upper:
            errors.append("Callsign not included in clearance")
            score -= 15
        
        # Check for standard phraseology
        standard_terms = ["CLEARED", "TAXI", "HOLD", "APPROVED", "ROGER", "WILCO", "AFFIRMATIVE", "NEGATIVE"]
        if not any(term in clearance_upper for term in standard_terms):
            warnings.append("May be missing standard ATC phraseology")
            score -= 10
        
        # Check for informal language (should not be used)
        informal_terms = ["PLEASE", "THANKS", "THANK YOU", "OK", "OKAY", "YEAH", "YEP"]
        if any(term in clearance_upper for term in informal_terms):
            errors.append("Informal language detected - use standard phraseology")
            score -= 20
        
        # Check clearance completeness based on type
        if "TAXI" in clearance_upper and "RUNWAY" not in clearance_upper and "TAXIWAY" not in clearance_upper:
            warnings.append("Taxi clearance may be missing route information")
            score -= 5
        
        if "TAKEOFF" in clearance_upper or "LANDING" in clearance_upper:
            if "RUNWAY" not in clearance_upper:
                errors.append("Runway number missing from takeoff/landing clearance")
                score -= 15
        
        # Check for proper format (should start with callsign)
        if not clearance_upper.startswith(callsign.upper()):
            warnings.append("Consider starting clearance with callsign")
            score -= 5

        # Encourage hearback/readback loop for critical instructions
        critical_terms = ("HOLD SHORT", "LINE UP", "CLEARED FOR TAKEOFF", "CLEARED TO LAND", "CROSS RUNWAY")
        if any(term in clearance_upper for term in critical_terms):
            if "READ BACK" not in clearance_upper and "REPORT" not in clearance_upper:
                warnings.append("Critical instruction should include readback/report requirement")
                score -= 8
        
        return {
            'score': max(0, score),
            'errors': errors,
            'warnings': warnings
        }

    def suggest_conflict_resolution(self):
        """Suggest immediate ATC actions for current runway conflicts."""
        conflicts = self._collect_runway_conflicts()
        if not conflicts:
            message = "No active runway conflicts detected.\nMaintain normal sequencing and readback checks."
            self._log_system_message(message)
            self.status_bar.config(text="Status: No conflicts detected")
            self._refresh_operational_insights()
            return

        suggestions = []
        for conflict in conflicts:
            runway = conflict.split(":")[0]
            suggestions.append(
                f"{runway}: Hold departure traffic, continue arrival to vacate runway, then release departure."
            )

        advisory = "Conflict Resolution Advisory:\n" + "\n".join(f"- {s}" for s in suggestions)
        self._log_system_message(advisory)
        messagebox.showinfo("Conflict Resolution Assistant", advisory)
        self.status_bar.config(text="Status: Conflict resolution advisory generated")
        self._refresh_operational_insights()

    def _update_atc_assessment_display(self, assessment):
        """Update the ATC assessment display"""
        score = assessment['score']
        score_color = "green" if score >= 80 else "orange" if score >= 60 else "red"
        self.atc_score_label.config(
            text=f"{score:.0f}/100",
            foreground=score_color
        )
        
        # Update feedback
        self.atc_feedback.config(state=tk.NORMAL)
        self.atc_feedback.delete(1.0, tk.END)
        
        has_issues = False
        if assessment.get('errors'):
            self.atc_feedback.insert(tk.END, "Errors:\n", "error")
            for error in assessment['errors']:
                self.atc_feedback.insert(tk.END, f"• {error}\n", "error")
            has_issues = True
        
        if assessment.get('warnings'):
            if has_issues:
                self.atc_feedback.insert(tk.END, "\n")
            self.atc_feedback.insert(tk.END, "Warnings:\n")
            for warning in assessment['warnings']:
                self.atc_feedback.insert(tk.END, f"• {warning}\n")
            has_issues = True
        
        if not has_issues:
            self.atc_feedback.insert(tk.END, "✓ Clearance looks good!\n")
        
        self.atc_feedback.config(state=tk.DISABLED)
        
        # Note: Communication is already recorded in transmit_clearance method

    def _log_atc_message(self, message):
        """Log an ATC message to the communication log"""
        self.communication_log.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.communication_log.insert(tk.END, f"[{timestamp}] ", "system")
        self.communication_log.insert(tk.END, f"ATC: {message}\n\n", "atc")
        self.communication_log.see(tk.END)
        self.communication_log.config(state=tk.DISABLED)

    def _log_system_message(self, message):
        """Log a system message to the communication log"""
        self.communication_log.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.communication_log.insert(tk.END, f"[{timestamp}] ", "system")
        self.communication_log.insert(tk.END, f"SYSTEM: {message}\n\n", "system")
        self.communication_log.see(tk.END)
        self.communication_log.config(state=tk.DISABLED)

    def _log_pilot_message(self, message: str) -> None:
        """Log a simulated pilot readback (NPC)."""
        self.communication_log.config(state=tk.NORMAL)
        timestamp = time.strftime("%H:%M:%S")
        self.communication_log.insert(tk.END, f"[{timestamp}] ", "system")
        self.communication_log.insert(tk.END, f"PILOT: {message}\n\n", "pilot")
        self.communication_log.see(tk.END)
        self.communication_log.config(state=tk.DISABLED)

    def update_session_summary(self):
        """Update the session summary display"""
        self.session_summary.config(state=tk.NORMAL)
        self.session_summary.delete(1.0, tk.END)
        
        if self.current_session_active:
            elapsed_time = time.time() - self.session_start_time if self.session_start_time else 0
            summary_text = f"Session: {self.current_scenario.name if self.current_scenario else 'Unknown'}\n"
            summary_text += f"Time: {int(elapsed_time // 60)}m {int(elapsed_time % 60)}s\n"
            summary_text += f"Aircraft: {len(self.active_aircraft)}\n"
            summary_text += f"Communications: {len(self.communication_history)}\n"
            summary_text += f"Clearances: {self.atc_training_metrics['clearances_issued']}\n"
            if self.atc_training_metrics["critical_clearances"] > 0:
                summary_text += f"Critical Clearances: {self.atc_training_metrics['critical_clearances']}\n"
            summary_text += f"ATC Focus: {self._get_atc_training_focus()}\n"
        else:
            summary_text = "No active session.\nSelect a scenario and start training."
        
        self.session_summary.insert(1.0, summary_text)
        self.session_summary.config(state=tk.DISABLED)

    def _show_session_results(self, assessment, session_id=None):
        """Show session results dialog"""
        result_text = f"Session Complete!\n\n"
        result_text += f"Final Score: {assessment.score:.1f}/100\n"
        result_text += f"Total Communications: {len(self.communication_history)}\n"
        result_text += f"Errors: {len(assessment.errors)}\n\n"
        result_text += f"ATC Focus Area: {self._get_atc_training_focus()}\n\n"
        
        if assessment.recommendations:
            result_text += "Recommendations:\n"
            for rec in assessment.recommendations[:3]:
                result_text += f"• {rec}\n"

        if session_id and self.report_generator and self.progress_tracker:
            session_report = self.report_generator.generate_session_report(session_id)
            progress_report = self.report_generator.generate_pilot_progress_report("ATC_CONTROLLER", days=30)
            debrief = self.report_generator.generate_trainee_debrief(
                role="ATC",
                session_report=session_report,
                progress_report=progress_report,
                extra_metrics={
                    "focus_area": self._get_atc_training_focus(),
                    "insight": f"High-risk clearances: {self.atc_training_metrics.get('high_risk_clearances', 0)}",
                },
            )
            self.last_debrief_text = debrief
            self.last_debrief_path = self._autosave_debrief("atc", session_id, debrief)
            result_text += "\n" + ("-" * 50) + "\n" + debrief
            if self.last_debrief_path:
                result_text += f"\n\nSaved debrief: {self.last_debrief_path}"

        messagebox.showinfo("Session Results", result_text)

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
        """Save last generated debrief to custom path."""
        if not self.last_debrief_text:
            messagebox.showinfo("No Debrief", "No debrief available yet. Complete a session first.")
            return
        from tkinter import filedialog
        filename = filedialog.asksaveasfilename(
            title="Save ATC Debrief",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if not filename:
            return
        if self.report_generator and self.report_generator.export_debrief_text(self.last_debrief_text, filename):
            self.status_bar.config(text=f"Status: Debrief saved to {filename}")
        else:
            messagebox.showerror("Save Error", "Failed to save debrief.")

    def _get_atc_training_focus(self):
        """Return training focus text for ATC coaching."""
        risk_count = self.atc_training_metrics.get("high_risk_clearances", 0)
        conflicts = len(self._collect_runway_conflicts())
        if risk_count >= 3:
            return "Phraseology precision and readback enforcement"
        if conflicts > 0:
            return "Runway sequencing and separation management"
        return "Maintain concise clearances and proactive traffic scan"

    def refresh_airport_view(self):
        """Refresh the airport view/radar"""
        self._redraw_all_airport_canvases()

    def _redraw_all_airport_canvases(self) -> None:
        if hasattr(self, "airport_canvas"):
            self.draw_airport_diagram(self.airport_canvas)
        if hasattr(self, "ground_canvas"):
            self.draw_airport_diagram(self.ground_canvas)
        self._refresh_path_connectivity_display()

    def zoom_in(self):
        """Zoom in on airport view"""
        # Placeholder for zoom functionality
        pass

    def zoom_out(self):
        """Zoom out on airport view"""
        # Placeholder for zoom functionality
        pass

    def setup_ground_tab(self):
        """Set up the Ground Control tab with a resizable layout."""
        self.ground_tab = ttk.Frame(self.notebook, padding=5)
        self.notebook.add(self.ground_tab, text="Ground Control")

        # Use a main horizontal paned window
        ground_paned_window = ttk.PanedWindow(self.ground_tab, orient=tk.HORIZONTAL)
        ground_paned_window.pack(fill=tk.BOTH, expand=True)

        # --- Left Frame (now a vertical paned window) ---
        left_paned = ttk.PanedWindow(ground_paned_window, orient=tk.VERTICAL)
        ground_paned_window.add(left_paned, weight=2)

        # --- Top-left section for aircraft list ---
        aircraft_section = ttk.Frame(left_paned, padding=5)
        left_paned.add(aircraft_section, weight=3) # Give more initial space to the list

        aircraft_header = ttk.Label(aircraft_section, text="Aircraft on Ground", font=("Arial", 11, "bold"))
        aircraft_header.pack(anchor="w", pady=(0, 2))

        aircraft_frame = ttk.Frame(aircraft_section)
        aircraft_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        columns = ("Callsign", "Type", "Location", "Status")
        self.ground_aircraft_tree = ttk.Treeview(aircraft_frame, columns=columns, show="headings", height=10)
        for col in columns:
            self.ground_aircraft_tree.heading(col, text=col, command=lambda c=col: self._sort_treeview_column(self.ground_aircraft_tree, c, False))
            self.ground_aircraft_tree.column(col, width=90 if col!="Status" else 120, anchor="w")
        
        self.ground_aircraft_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        aircraft_scrollbar = ttk.Scrollbar(aircraft_frame, orient="vertical", command=self.ground_aircraft_tree.yview)
        self.ground_aircraft_tree.configure(yscrollcommand=aircraft_scrollbar.set)
        aircraft_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.ground_aircraft_tree.bind(
            "<<TreeviewSelect>>",
            lambda _e: self._refresh_atc_traffic_strip(),
        )

        control_frame = ttk.Frame(aircraft_section)
        control_frame.pack(fill=tk.X, pady=5)
        ttk.Button(control_frame, text="Add Aircraft", command=self.add_ground_aircraft).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(control_frame, text="Remove", command=self.remove_ground_aircraft).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Edit Status", command=self.edit_ground_status).pack(side=tk.LEFT, padx=5)

        # --- Bottom-left section for communications ---
        comm_section = ttk.Frame(left_paned, padding=5)
        left_paned.add(comm_section, weight=1)

        comm_header = ttk.Label(comm_section, text="Communications", font=("Arial", 11, "bold"))
        comm_header.pack(anchor="w", pady=(0, 2))

        comm_button_frame = ttk.Frame(comm_section)
        comm_button_frame.pack(fill=tk.X, pady=2)
        ttk.Button(comm_button_frame, text="Taxi Clearance", command=self.issue_taxi_clearance).pack(side=tk.LEFT)
        ttk.Button(comm_button_frame, text="Hold Position", command=self.issue_hold_instruction).pack(side=tk.LEFT, padx=5)
        ttk.Button(comm_button_frame, text="Transfer to Tower", command=lambda: self.transfer_aircraft("Tower")).pack(side=tk.LEFT, padx=5)
        
        # AI Response section
        ai_frame = ttk.Frame(comm_section)
        ai_frame.pack(fill=tk.X, pady=(10, 5))
        
        # AI status indicator
        self.ai_processing_label = ttk.Label(ai_frame, text="🤖 AI Ready", font=("Arial", 9), foreground="green")
        self.ai_processing_label.pack(side=tk.LEFT, padx=(0, 10))
        
        ttk.Label(ai_frame, text="Pilot Message:").pack(side=tk.LEFT, padx=(0, 5))
        self.ai_input_var = tk.StringVar()
        self.ai_input_entry = ttk.Entry(ai_frame, textvariable=self.ai_input_var, width=40)
        self.ai_input_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.ai_input_entry.bind("<Return>", self.send_ai_response)
        self.ai_input_entry.bind("<Control-Return>", self.send_ai_response)  # Ctrl+Enter shortcut
        
        self.send_ai_response_btn = ttk.Button(ai_frame, text="Send AI Response", command=self.send_ai_response)
        self.send_ai_response_btn.pack(side=tk.LEFT)
        ttk.Button(ai_frame, text="Clear Input", command=self.clear_ai_input).pack(side=tk.LEFT, padx=5)
        
        # Add clear log button
        ttk.Button(ai_frame, text="Clear Log", command=self.clear_communication_log).pack(side=tk.LEFT, padx=5)
        
        # Add example messages button
        ttk.Button(ai_frame, text="Examples", command=self.show_example_messages).pack(side=tk.LEFT, padx=5)
        
        # Add save log button
        ttk.Button(ai_frame, text="Save Log", command=self.save_communication_log).pack(side=tk.LEFT, padx=5)
        
        # Add help button
        ttk.Button(ai_frame, text="?", command=self.show_ai_help).pack(side=tk.LEFT, padx=5)
        
        # Add separator
        separator = ttk.Separator(comm_section, orient='horizontal')
        separator.pack(fill=tk.X, pady=10)

        trainee_frame = ttk.LabelFrame(
            comm_section,
            text="Selected traffic (ATC trainee — you are the controller)",
            padding=4,
        )
        trainee_frame.pack(fill=tk.X, pady=(0, 6))
        self.atc_mode_role_hint = ttk.Label(
            trainee_frame,
            text="This window is for ATC training. The row you select is traffic you are working. "
            "Pilot Message + AI below simulate pilot-side comms for phraseology practice only.",
            font=("Arial", 8),
            foreground="gray",
            wraplength=560,
            justify=tk.LEFT,
        )
        self.atc_mode_role_hint.pack(anchor=tk.W, pady=(0, 4))
        self.atc_traffic_strip_label = ttk.Label(
            trainee_frame,
            text="Select an aircraft in the list to see list state and recent comms to that callsign.",
            font=("Consolas", 9),
            wraplength=560,
            justify=tk.LEFT,
        )
        self.atc_traffic_strip_label.pack(anchor=tk.W)
        
        # Communication log label
        ttk.Label(comm_section, text="Communication Log:", font=("Arial", 10, "bold")).pack(anchor="w", pady=(10, 5))
        
        # Enhanced communication log
        self.ground_instructions = scrolledtext.ScrolledText(
            comm_section, 
            height=8,  # Increased height
            wrap=tk.WORD, 
            state=tk.DISABLED,
            font=("Consolas", 9),  # Monospace font for better readability
            background="#f8f9fa",  # Light background
            foreground="#212529"   # Dark text
        )
        self.ground_instructions.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # --- Right frame for airport diagram ---
        right_frame = ttk.Frame(ground_paned_window, padding=5)
        ground_paned_window.add(right_frame, weight=1)

        diagram_frame = ttk.LabelFrame(right_frame, text="Airport Diagram")
        diagram_frame.pack(fill=tk.BOTH, expand=True)
        self.atc_diagram_traffic_hint = ttk.Label(
            diagram_frame,
            text="",
            font=("Arial", 8),
            foreground="#333333",
            wraplength=320,
            justify=tk.LEFT,
        )
        self.atc_diagram_traffic_hint.pack(anchor=tk.W, padx=4, pady=(2, 0))
        self.ground_canvas = tk.Canvas(diagram_frame, bg="lightgrey")
        self.ground_canvas.pack(fill=tk.BOTH, expand=True)
        self.ground_canvas.bind("<Configure>", lambda event: self.draw_airport_diagram(event.widget))
        self.ground_canvas.bind("<Button-1>", self._on_path_canvas_click)
        self.ground_canvas.bind("<Button-3>", self._on_path_canvas_right_click)

    def refresh_current_airport_weather(self):
        """Refresh weather for current airport"""
        icao_code = self.current_airport.split(" - ")[0]
        self.fetch_live_weather(icao_code)

    def toggle_auto_weather_updates(self):
        """Toggle automatic weather updates"""
        if self.auto_weather_var.get():
            # Start automatic updates
            self.schedule_weather_update()
            self.status_bar.config(text="Status: Automatic weather updates enabled")
        else:
            # Cancel automatic updates if scheduled
            if self.weather_update_id:
                self.root.after_cancel(self.weather_update_id)
                self.weather_update_id = None
            self.status_bar.config(text="Status: Automatic weather updates disabled")

    def schedule_weather_update(self):
        """Schedule the next weather update"""
        # Cancel any existing scheduled update
        if self.weather_update_id:
            self.root.after_cancel(self.weather_update_id)

        # Schedule the next update
        self.weather_update_id = self.root.after(
            self.weather_update_interval, self.auto_update_weather
        )

    def auto_update_weather(self):
        """Perform automated weather update and schedule next one"""
        # Refresh weather
        self.refresh_current_airport_weather()

        # Schedule next update if auto-update is still enabled
        if self.auto_weather_var.get():
            self.schedule_weather_update()
        
        # Also update the tower weather display if it exists
        if hasattr(self, 'tower_weather_display'):
            self.update_tower_weather_display()

    def get_airport_weather_string(self):
        """Get formatted weather string for display"""
        airport_data = self.airports[self.current_airport]
        wind = airport_data.get("wind", "---")
        visibility = airport_data.get("visibility", "---")
        ceiling = airport_data.get("ceiling", "---")

        return f"Wind: {wind} | Visibility: {visibility} | Ceiling: {ceiling}"

    def setup_tower_tab(self):
        """Set up the Tower Control tab"""
        self.tower_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.tower_tab, text="Tower")

        # Use a paned window for resizable sections
        tower_paned_window = ttk.PanedWindow(self.tower_tab, orient=tk.HORIZONTAL)
        tower_paned_window.pack(fill=tk.BOTH, expand=True)

        # Left frame for queues
        left_frame = ttk.Frame(tower_paned_window, padding=5)
        tower_paned_window.add(left_frame, weight=1)

        # Right frame for status and info
        right_frame = ttk.Frame(tower_paned_window, padding=5)
        tower_paned_window.add(right_frame, weight=2)

        # --- Left Frame: Departure and Arrival Queues ---
        # Departure Queue
        dep_queue_frame = ttk.LabelFrame(left_frame, text="Departure Queue")
        dep_queue_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        dep_list_frame = ttk.Frame(dep_queue_frame)
        dep_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        dep_scrollbar = ttk.Scrollbar(dep_list_frame)
        dep_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.departure_listbox = tk.Listbox(dep_list_frame, height=10, yscrollcommand=dep_scrollbar.set)
        self.departure_listbox.pack(fill=tk.BOTH, expand=True)
        dep_scrollbar.config(command=self.departure_listbox.yview)

        dep_button_frame = ttk.Frame(dep_queue_frame)
        dep_button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(dep_button_frame, text="Add Aircraft", command=lambda: self.add_aircraft_to_queue("departure")).pack(side=tk.LEFT)
        ttk.Button(dep_button_frame, text="Remove", command=lambda: self.remove_aircraft_from_queue("departure")).pack(side=tk.LEFT, padx=5)
        ttk.Button(dep_button_frame, text="Line Up", command=self.line_up_departure).pack(side=tk.LEFT, padx=5)
        ttk.Button(dep_button_frame, text="Takeoff Clearance", command=self.issue_takeoff_clearance).pack(side=tk.LEFT, padx=5)

        # Arrival Queue
        arr_queue_frame = ttk.LabelFrame(left_frame, text="Arrival Queue")
        arr_queue_frame.pack(fill=tk.BOTH, expand=True, pady=(5, 0))
        
        arr_list_frame = ttk.Frame(arr_queue_frame)
        arr_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        arr_scrollbar = ttk.Scrollbar(arr_list_frame)
        arr_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.arrival_listbox = tk.Listbox(arr_list_frame, height=10, yscrollcommand=arr_scrollbar.set)
        self.arrival_listbox.pack(fill=tk.BOTH, expand=True)
        arr_scrollbar.config(command=self.arrival_listbox.yview)

        arr_button_frame = ttk.Frame(arr_queue_frame)
        arr_button_frame.pack(fill=tk.X, padx=10, pady=(0, 10))
        ttk.Button(arr_button_frame, text="Add Aircraft", command=lambda: self.add_aircraft_to_queue("arrival")).pack(side=tk.LEFT)
        ttk.Button(arr_button_frame, text="Remove", command=lambda: self.remove_aircraft_from_queue("arrival")).pack(side=tk.LEFT, padx=5)
        ttk.Button(arr_button_frame, text="Approach Clearance", command=self.issue_approach_clearance).pack(side=tk.LEFT, padx=5)
        ttk.Button(arr_button_frame, text="Landing Clearance", command=self.issue_landing_clearance).pack(side=tk.LEFT, padx=5)
        ttk.Button(arr_button_frame, text="Transfer to Ground", command=self.transfer_to_ground).pack(side=tk.LEFT, padx=5)

        # --- Right Frame: Notebook for different info ---
        right_notebook = ttk.Notebook(right_frame)
        right_notebook.pack(fill=tk.BOTH, expand=True)

        # Runway Status Tab
        runway_tab = ttk.Frame(right_notebook, padding=5)
        right_notebook.add(runway_tab, text="Runway Status")
        self.runway_frame = ttk.LabelFrame(runway_tab, text="Runway Status")
        self.runway_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # Instructions Tab
        instructions_tab = ttk.Frame(right_notebook, padding=5)
        right_notebook.add(instructions_tab, text="Instructions")
        instructions_frame = ttk.LabelFrame(instructions_tab, text="Instructions")
        instructions_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        self.tower_instructions_text = scrolledtext.ScrolledText(instructions_frame, wrap=tk.WORD, height=10, relief=tk.FLAT, background=self.root.cget('bg'), state=tk.DISABLED)
        self.tower_instructions_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Log initial instructions
        self.log_communication(
            self.tower_instructions_text, 
            "SYSTEM", 
            "Tower control initialized. Monitor runway status and queues.",
            clear=True
        )

        # Weather Tab
        weather_tab = ttk.Frame(right_notebook, padding=5)
        right_notebook.add(weather_tab, text="Weather")
        weather_frame = ttk.LabelFrame(weather_tab, text="Current Weather")
        weather_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))
        
        self.tower_weather_display = scrolledtext.ScrolledText(weather_frame, wrap=tk.WORD, height=10)
        self.tower_weather_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.tower_weather_display.config(state=tk.DISABLED)

        # Initialize runway status and weather for tower tab
        # Note: These calls are moved to the end to ensure all UI elements are created first
        self.root.after(100, self.update_runway_frame)
        self.root.after(100, self.update_tower_weather_display)

    def update_tower_weather_display(self):
        """Updates the weather display in the tower tab"""
        if hasattr(self, 'tower_weather_display'):
            airport_data = self.airports.get(self.current_airport, {})
            weather_str = self.get_airport_weather_string()
            
            metar = airport_data.get("metar", "No METAR available")
            
            full_weather_text = f"Current Weather:\n{weather_str}\n\nMETAR:\n{metar}"
            
            self.tower_weather_display.config(state=tk.NORMAL)
            self.tower_weather_display.delete(1.0, tk.END)
            self.tower_weather_display.insert(tk.END, full_weather_text)
            self.tower_weather_display.config(state=tk.DISABLED)

    def setup_approach_tab(self):
        """Set up the Approach Control tab"""
        self.approach_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.approach_tab, text="Approach Control")
        ttk.Label(self.approach_tab, text="Approach Control - Coming Soon").pack(pady=20)
        ttk.Label(
            self.approach_tab,
            text="This tab will provide tools for managing approaching aircraft.",
        ).pack()

    def setup_departure_tab(self):
        """Set up the Departure tab"""
        # Basic structure - to be expanded
        self.departure_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.departure_tab, text="Departure Control")
        ttk.Label(self.departure_tab, text="Departure Control - Coming Soon").pack(pady=20)
        ttk.Label(
            self.departure_tab,
            text="This tab will provide tools for managing departing aircraft.",
        ).pack()

    def setup_atis_tab(self):
        """Set up the ATIS Management tab."""
        self.atis_tab = ttk.Frame(self.notebook, padding=10)
        self.notebook.add(self.atis_tab, text="ATIS Management")

        # ATIS Display Frame
        atis_display_frame = ttk.LabelFrame(self.atis_tab, text="Current ATIS Message")
        atis_display_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))

        self.atis_message_text = scrolledtext.ScrolledText(atis_display_frame, wrap=tk.WORD, height=10, state=tk.DISABLED)
        self.atis_message_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # ATIS Control Frame
        atis_control_frame = ttk.LabelFrame(self.atis_tab, text="ATIS Generation")
        atis_control_frame.pack(fill=tk.X)

        control_grid = ttk.Frame(atis_control_frame, padding=10)
        control_grid.pack(fill=tk.X)

        # Phonetic designator
        ttk.Label(control_grid, text="Information:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.atis_designator_var = tk.StringVar()
        self.phonetic_alphabet = [chr(i) for i in range(ord('A'), ord('Z') + 1)]
        self.atis_designator_combo = ttk.Combobox(
            control_grid, 
            textvariable=self.atis_designator_var,
            values=self.phonetic_alphabet,
            width=5,
            state="readonly"
        )
        self.atis_designator_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        self.atis_designator_combo.set("A")

        # Remarks
        ttk.Label(control_grid, text="Remarks:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.atis_remarks_var = tk.StringVar()
        remarks_entry = ttk.Entry(control_grid, textvariable=self.atis_remarks_var, width=60)
        remarks_entry.grid(row=1, column=1, columnspan=3, sticky=tk.EW, padx=5, pady=5)
        control_grid.columnconfigure(1, weight=1)
        
        # Buttons
        button_frame = ttk.Frame(control_grid)
        button_frame.grid(row=2, column=0, columnspan=4, pady=10)
        
        ttk.Button(button_frame, text="Generate New ATIS", command=self.generate_atis_message).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Generate AI ATIS", command=self.generate_ai_atis).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Broadcast ATIS", command=self.broadcast_atis).pack(side=tk.LEFT, padx=5)

    def generate_atis_message(self):
        """Generates the ATIS message content based on current data."""
        airport_data = self.airports.get(self.current_airport)
        if not airport_data:
            messagebox.showerror("Error", "No airport data available.")
            return

        # Get data points
        icao = airport_data.get("icao", "----")
        designator = self.atis_designator_var.get()
        now_utc = time.gmtime()
        time_str = time.strftime("%H%M", now_utc) + "Z"
        
        # Weather
        wind = airport_data.get("wind", "not available")
        visibility = airport_data.get("visibility", "not available")
        ceiling = airport_data.get("ceiling", "not available")
        # In a real app, you'd also fetch temp, dewpoint, altimeter
        metar = airport_data.get("metar", "")
        altimeter_match = re.search(r"Q(\d{4})", metar)
        altimeter = f"Altimeter {altimeter_match.group(1)}" if altimeter_match else "Altimeter not available"

        # Active Runways
        runway_status = airport_data.get("runway_status", {})
        active_runways = [rwy for rwy, status in runway_status.items() if status.get("active")]
        dep_rwy_text = f"Departing runways {', '.join(active_runways)}." if active_runways else "No runways available for departure."
        arr_rwy_text = f"Landing runways {', '.join(active_runways)}." if active_runways else "No runways available for landing."

        # Remarks
        remarks = self.atis_remarks_var.get().strip()
        remarks_text = f"Remarks... {remarks}..." if remarks else ""

        # Assemble the message
        message = (
            f"{icao} airport information {designator}... time {time_str}...\n"
            f"Wind {wind}... visibility {visibility}... ceiling {ceiling}...\n"
            f"{altimeter}...\n"
            f"{dep_rwy_text} {arr_rwy_text}\n"
            f"{remarks_text}\n"
            f"Advise controller on initial contact you have information {designator}."
        )

        # Display the message
        self.atis_message_text.config(state=tk.NORMAL)
        self.atis_message_text.delete(1.0, tk.END)
        self.atis_message_text.insert(tk.END, message)
        self.atis_message_text.config(state=tk.DISABLED)
        
        self.status_bar.config(text=f"Status: Generated new ATIS Information {designator} for review.")

    def broadcast_atis(self):
        """Makes the generated ATIS the current one and advances the designator."""
        atis_message = self.atis_message_text.get(1.0, tk.END).strip()
        if not atis_message:
            messagebox.showwarning("Warning", "No ATIS message has been generated yet.")
            return

        designator = self.atis_designator_var.get()
        
        # Store in the airport data
        airport_data = self.airports.get(self.current_airport)
        if airport_data:
            airport_data['atis'] = {
                "designator": designator,
                "message": atis_message,
                "timestamp": time.time()
            }
        
        self.status_bar.config(text=f"Status: ATIS Information {designator} is now being broadcast.")
        
        # Advance to the next designator
        current_index = self.phonetic_alphabet.index(designator)
        next_index = (current_index + 1) % len(self.phonetic_alphabet)
        self.atis_designator_combo.set(self.phonetic_alphabet[next_index])

    # Helper methods for Ground Control tab
    def add_ground_aircraft(self):
        """Add a new aircraft to ground control (Treeview version)"""
        add_dialog = tk.Toplevel(self.root)
        add_dialog.title("Add Aircraft")
        add_dialog.geometry("400x350")
        add_dialog.resizable(False, False)
        add_dialog.transient(self.root)
        add_dialog.grab_set()

        frame = ttk.Frame(add_dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Add New Aircraft", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15))
        ttk.Label(frame, text="Callsign:").grid(row=1, column=0, sticky=tk.W, pady=5)
        callsign_var = tk.StringVar()
        def to_uppercase(*args):
            callsign_var.set(callsign_var.get().upper())
        callsign_var.trace_add("write", to_uppercase)
        callsign_entry = ttk.Entry(frame, textvariable=callsign_var, width=25)
        callsign_entry.grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Label(frame, text="Aircraft Type:").grid(row=2, column=0, sticky=tk.W, pady=5)
        type_var = tk.StringVar()
        type_entry = ttk.Combobox(frame, textvariable=type_var, width=25)
        type_entry["values"] = (
            "C152", "C172", "C182", "C206", "C208", "C210", "C310", "C340", "C402", "C414", "C421", "C441", "C500", "C510", "C525", "C550", "C560", "C650", "C680", "C750", "C850",
            "PA28", "PA32", "PA34", "PA44", "PA46",
            "BE20", "BE36", "BE58", "BE60", "BE76", "BE90", "BE99", "BE200", "BE300", "BE350", "BE400", "BE1900",
            "B707", "B717", "B727", "B737", "B747", "B757", "B767", "B777", "B787", "B797",
            "A220", "A300", "A310", "A318", "A319", "A320", "A321", "A330", "A340", "A350", "A380", "A400M",
            "E135", "E140", "E145", "E170", "E175", "E190", "E195", "CRJ1", "CRJ2", "CRJ7", "CRJ9", "CRJ10",
            "MD80", "MD90", "MD11", "DC9", "DC10", "L1011", "F100", "F70", "F28", "F50", "ATR42", "ATR72", "DHC8", "SF340", "EMB110", "EMB120", "EMB135", "EMB145", "EMB170", "EMB175", "EMB190", "EMB195"
        )
        type_entry.grid(row=2, column=1, sticky=tk.W, pady=5)
        location_options = self._get_location_options()
        ttk.Label(frame, text="Location:").grid(row=3, column=0, sticky=tk.W, pady=5)
        location_var = tk.StringVar()
        location_entry = ttk.Combobox(frame, textvariable=location_var, values=tuple(location_options), width=25)
        location_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        runways = self.airports.get(self.current_airport, {}).get("runways", [])
        if runways:
            hold_short_options = [f"Hold Short Runway {runway}" for runway in runways]
        else:
            hold_short_options = ["Hold Short Runway 27", "Hold Short Runway 36"]
        status_options = [
            "Ready to Taxi",
            "Pushback",
            "Taxiing to Runway",
        ] + hold_short_options + [
            "Taxiing to Gate",
            "Parked",
            "Cleared for Takeoff",
            "Line Up and Wait",
        ]
        ttk.Label(frame, text="Status:").grid(row=4, column=0, sticky=tk.W, pady=5)
        status_var = tk.StringVar()
        status_entry = ttk.Combobox(frame, textvariable=status_var, width=25)
        status_entry["values"] = tuple(status_options)
        status_entry.grid(row=4, column=1, sticky=tk.W, pady=5)
        ttk.Label(frame, text="Notes:").grid(row=5, column=0, sticky=tk.W, pady=5)
        notes_text = tk.Text(frame, width=30, height=5)
        notes_text.grid(row=5, column=1, sticky=tk.W, pady=5)
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=(20, 0))
        def add_aircraft():
            callsign = callsign_var.get().strip()
            aircraft_type = type_var.get().strip()
            location = location_var.get().strip()
            status = status_var.get().strip()
            if not callsign or not aircraft_type or not location or not status:
                messagebox.showwarning("Missing Information", "Please fill in all required fields")
                return
            # Add to the Treeview
            self.ground_aircraft_tree.insert("", tk.END, values=(callsign, aircraft_type, location, status))
            self.status_bar.config(text=f"Status: Added aircraft {callsign} to ground control")
            self._refresh_atc_traffic_strip()
            add_dialog.destroy()
        def cancel():
            add_dialog.destroy()
        ttk.Button(button_frame, text="Add Aircraft", command=add_aircraft).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.LEFT)
        add_dialog.update_idletasks()
        width = add_dialog.winfo_width()
        height = add_dialog.winfo_height()
        x = self.root.winfo_x() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
        add_dialog.geometry(f"{width}x{height}+{x}+{y}")
        callsign_entry.focus_set()
        add_dialog.wait_window()

    def remove_ground_aircraft(self):
        """Remove an aircraft from ground control (Treeview version)"""
        selected = self.ground_aircraft_tree.selection()
        if selected:
            self.ground_aircraft_tree.delete(selected)
            self.status_bar.config(text="Status: Aircraft removed from ground control")
        else:
            messagebox.showinfo("Selection Required", "Please select an aircraft to remove")

    def edit_ground_status(self):
        """Edit the status of an aircraft on the ground (Treeview version)"""
        selected = self.ground_aircraft_tree.selection()
        if not selected:
            messagebox.showinfo("Selection Required", "Please select an aircraft to edit")
            return
        aircraft_info = self.ground_aircraft_tree.item(selected, "values")
        edit_dialog = tk.Toplevel(self.root)
        edit_dialog.title("Edit Aircraft Status")
        edit_dialog.geometry("400x350")
        edit_dialog.resizable(False, False)
        edit_dialog.transient(self.root)
        edit_dialog.grab_set()
        frame = ttk.Frame(edit_dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Aircraft Information:", font=("Arial", 12, "bold")).grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10))
        callsign = aircraft_info[0] if len(aircraft_info) > 0 else ""
        aircraft_type = aircraft_info[1] if len(aircraft_info) > 1 else ""
        location = aircraft_info[2] if len(aircraft_info) > 2 else ""
        status = aircraft_info[3] if len(aircraft_info) > 3 else ""
        ttk.Label(frame, text="Callsign:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Label(frame, text=callsign).grid(row=1, column=1, sticky=tk.W, pady=5)
        ttk.Label(frame, text="Type:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Label(frame, text=aircraft_type).grid(row=2, column=1, sticky=tk.W, pady=5)
        location_options = self._get_location_options()
        ttk.Label(frame, text="Location:").grid(row=3, column=0, sticky=tk.W, pady=5)
        location_var = tk.StringVar(value=location)
        location_entry = ttk.Combobox(frame, textvariable=location_var, values=tuple(location_options), width=25)
        location_entry.grid(row=3, column=1, sticky=tk.W, pady=5)
        runways = self.airports.get(self.current_airport, {}).get("runways", [])
        if runways:
            hold_short_options = [f"Hold Short Runway {runway}" for runway in runways]
        else:
            hold_short_options = ["Hold Short Runway 27", "Hold Short Runway 36"]
        status_options = [
            "Ready to Taxi",
            "Pushback",
            "Taxiing to Runway",
        ] + hold_short_options + [
            "Taxiing to Gate",
            "Parked",
            "Cleared for Takeoff",
            "Line Up and Wait",
        ]
        ttk.Label(frame, text="Status:").grid(row=4, column=0, sticky=tk.W, pady=5)
        status_var = tk.StringVar(value=status)
        status_entry = ttk.Combobox(frame, textvariable=status_var, width=25)
        status_entry["values"] = tuple(status_options)
        status_entry.grid(row=4, column=1, sticky=tk.W, pady=5)
        ttk.Label(frame, text="Notes:").grid(row=5, column=0, sticky=tk.W, pady=5)
        notes_text = tk.Text(frame, width=30, height=5)
        notes_text.grid(row=5, column=1, sticky=tk.W, pady=5)
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=(20, 0))
        def save_changes():
            new_location = location_var.get()
            new_status = status_var.get()
            new_aircraft_info = (callsign, aircraft_type, new_location, new_status)
            self.ground_aircraft_tree.item(selected, values=new_aircraft_info)
            self.ground_aircraft_tree.selection_set(selected)
            self.status_bar.config(text=f"Status: Updated status for {callsign}")
            self._refresh_atc_traffic_strip()
            edit_dialog.destroy()
        def cancel():
            edit_dialog.destroy()
        ttk.Button(button_frame, text="Save Changes", command=save_changes).pack(side=tk.LEFT, padx=(0, 10))
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.LEFT)
        edit_dialog.update_idletasks()
        width = edit_dialog.winfo_width()
        height = edit_dialog.winfo_height()
        x = self.root.winfo_x() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
        edit_dialog.geometry(f"{width}x{height}+{x}+{y}")
        edit_dialog.wait_window()

    def _get_location_options(self):
        """Get a list of all available location options for the current airport."""
        airport_data = self.airports.get(self.current_airport, {})
        gates = airport_data.get("gates", [])
        taxiways = airport_data.get("taxiways", [])
        runways = airport_data.get("runways", [])
        
        location_options = []
        
        # Expand and add gates
        expanded_gates = []
        for gate in gates:
            # Handle ranges like "A1-A20"
            match = re.match(r"([A-Z]+)(\d+)-[A-Z]*(\d+)", gate)
            if match:
                prefix, start_str, end_str = match.groups()
                start, end = int(start_str), int(end_str)
                expanded_gates.extend([f"{prefix}{i}" for i in range(start, end + 1)])
            else:
                expanded_gates.append(gate)
        
        for gate in expanded_gates:
            location_options.append(f"Gate {gate}")
            
        # Add taxiways
        for taxiway in taxiways:
            location_options.append(f"Taxiway {taxiway}")
            
        # Add runways
        for runway in runways:
            location_options.append(f"Runway {runway}")

        try:
            location_options.extend(self._path_graph().location_choices())
        except Exception:
            pass
            
        if not location_options:
            return ["Gate A1", "Gate A2", "Taxiway A", "Runway 27"] # Fallback
            
        return location_options

    # Helper methods for Tower tab
    def add_aircraft_to_queue(self, queue_type):
        """Add an aircraft to the departure or arrival queue"""
        # Create a dialog to get aircraft details
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Add Aircraft to {queue_type.capitalize()} Queue")
        dialog.geometry("400x250")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Create form fields
        ttk.Label(dialog, text="Callsign:").grid(row=0, column=0, sticky="w", padx=10, pady=5)
        callsign_var = tk.StringVar()
        def to_uppercase(*args):
            callsign_var.set(callsign_var.get().upper())
        callsign_var.trace_add("write", to_uppercase)
        callsign_entry = ttk.Entry(dialog, textvariable=callsign_var, width=20)
        callsign_entry.grid(row=0, column=1, padx=10, pady=5)
        callsign_entry.focus_set()
        
        ttk.Label(dialog, text="Aircraft Type:").grid(row=1, column=0, sticky="w", padx=10, pady=5)
        aircraft_type_entry = ttk.Entry(dialog, width=20)
        aircraft_type_entry.grid(row=1, column=1, padx=10, pady=5)
        
        # Get available runways for this airport
        airport_data = self.airports.get(self.current_airport, {})
        runways = airport_data.get("runways", [])
        
        ttk.Label(dialog, text="Runway:").grid(row=2, column=0, sticky="w", padx=10, pady=5)
        runway_var = tk.StringVar()
        runway_combo = ttk.Combobox(dialog, textvariable=runway_var, values=runways, state="readonly", width=10)
        runway_combo.grid(row=2, column=1, padx=10, pady=5)
        if runways:
            runway_combo.current(0)
        
        # For departures, add gate information from airport configuration
        if queue_type == "departure":
            ttk.Label(dialog, text="Gate:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
            
            # Get gates from airport configuration
            gates = airport_data.get("gates", [])
            gate_options = []
            for gate in gates:
                if not gate.startswith("Gate "):
                    gate_options.append(f"Gate {gate}")
                else:
                    gate_options.append(gate)
                    
            # Use default if no gates defined
            if not gate_options:
                gate_options = ["Gate A1", "Gate B1", "Gate C1"]
                
            gate_var = tk.StringVar()
            gate_combo = ttk.Combobox(dialog, textvariable=gate_var, values=gate_options, width=20)
            gate_combo.grid(row=3, column=1, padx=10, pady=5)
            if gate_options:
                gate_combo.current(0)
                
            # Create dynamic departure status options based on runways
            dep_status_options = ["Ready for Taxi", "Taxiing"]
            
            # Add runway-specific options
            for runway in runways:
                dep_status_options.append(f"Ready for Departure RWY {runway}")
                dep_status_options.append(f"Lined Up RWY {runway}")
                
            if not runways:
                dep_status_options.extend(["Ready for Departure", "Lined Up"])
                
            ttk.Label(dialog, text="Status:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
            status_var = tk.StringVar(value=dep_status_options[0] if dep_status_options else "Ready for Taxi")
            status_combo = ttk.Combobox(dialog, textvariable=status_var, 
                                       values=dep_status_options, 
                                       state="readonly", width=20)
            status_combo.grid(row=4, column=1, padx=10, pady=5)
            
        # For arrivals, add approach information based on airport capabilities
        else:  # arrival queue
            ttk.Label(dialog, text="Approach Type:").grid(row=3, column=0, sticky="w", padx=10, pady=5)
            
            # Get approach types based on airport capabilities
            approach_options = ["ILS"]
            
            # Add runway-specific approaches
            for runway in runways:
                # Check if the airport has special approach types for this runway
                runway_approaches = airport_data.get(f"approaches_{runway}", [])
                if runway_approaches:
                    approach_options.extend(runway_approaches)
                    
            # Add standard approach types if not already included
            for approach in ["Visual", "RNAV", "VOR"]:
                if approach not in approach_options:
                    approach_options.append(approach)
                    
            approach_var = tk.StringVar(value=approach_options[0] if approach_options else "ILS")
            approach_combo = ttk.Combobox(dialog, textvariable=approach_var, 
                                         values=approach_options, state="readonly", width=10)
            approach_combo.grid(row=3, column=1, padx=10, pady=5)
            
            # Create dynamic approach status options based on runways
            arr_status_options = []
            
            # Add generic options
            arr_status_options.append("On Approach")
            
            # Add runway-specific options
            for runway in runways:
                arr_status_options.append(f"Final Approach RWY {runway}")
                arr_status_options.append(f"Short Final RWY {runway}")
                arr_status_options.append(f"Landed RWY {runway}")
                
            if not runways:
                arr_status_options.extend(["Final Approach", "Short Final", "Landed"])
                
            ttk.Label(dialog, text="Status:").grid(row=4, column=0, sticky="w", padx=10, pady=5)
            status_var = tk.StringVar(value=arr_status_options[0] if arr_status_options else "On Approach")
            status_combo = ttk.Combobox(dialog, textvariable=status_var, 
                                       values=arr_status_options, 
                                       state="readonly", width=20)
            status_combo.grid(row=4, column=1, padx=10, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.grid(row=5, column=0, columnspan=2, pady=15)
        
        def add_aircraft():
            # Validate entries
            callsign = callsign_var.get().strip()
            aircraft_type = aircraft_type_entry.get().strip().upper()
            runway = runway_var.get()
            status = status_var.get()
            
            if not callsign or not aircraft_type or not runway:
                messagebox.showerror("Error", "Callsign, Aircraft Type, and Runway are required")
                return
            
            # Create aircraft data structure
            aircraft_data = {
                "callsign": callsign,
                "type": aircraft_type,
                "runway": runway,
                "status": status,
                "last_instruction": "",
                "time_added": time.strftime("%H:%M:%S")
            }
            
            # Add extra fields based on queue type
            if queue_type == "departure":
                aircraft_data["gate"] = gate_var.get() if queue_type == "departure" else ""
            else:
                aircraft_data["approach_type"] = approach_var.get()
            
            # Add to the appropriate listbox
            listbox = self.departure_listbox if queue_type == "departure" else self.arrival_listbox
            
            # Clear placeholder message if it's the only item
            if listbox.size() == 1:
                first_item = listbox.get(0)
                if "No aircraft in" in first_item:
                    listbox.delete(0)
            
            # Add the new aircraft
            display_text = f"{callsign} ({aircraft_type}) - {status} - RWY {runway}"
            listbox.insert(tk.END, display_text)
            
            # Store the full aircraft data (we'll need a data structure for this)
            if not hasattr(self, "aircraft_data"):
                self.aircraft_data = {"departure": {}, "arrival": {}}
            
            self.aircraft_data[queue_type][callsign] = aircraft_data
            
            # Update status bar
            self.status_bar.config(text=f"Status: Added {callsign} to {queue_type} queue")
            
            # Close the dialog
            dialog.destroy()
        
        ttk.Button(button_frame, text="Add", command=add_aircraft).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=10)
        
        # Center the dialog on the parent window
        dialog.update_idletasks()
        width = dialog.winfo_width()
        height = dialog.winfo_height()
        x = (self.root.winfo_width() // 2) - (width // 2) + self.root.winfo_x()
        y = (self.root.winfo_height() // 2) - (height // 2) + self.root.winfo_y()
        dialog.geometry(f"{width}x{height}+{x}+{y}")
    
    def remove_aircraft_from_queue(self, queue_type):
        """Remove the selected aircraft from the departure or arrival queue"""
        listbox = self.departure_listbox if queue_type == "departure" else self.arrival_listbox
        selection = listbox.curselection()
        
        if not selection:
            messagebox.showinfo("Information", f"Please select an aircraft from the {queue_type} queue")
            return
        
        index = selection[0]
        aircraft_info = listbox.get(index)
        
        # Extract callsign from the displayed text
        callsign = aircraft_info.split(" ")[0]
        
        # Remove from listbox
        listbox.delete(index)
        
        # Add placeholder message if queue is now empty
        if listbox.size() == 0:
            placeholder = f"No aircraft in {queue_type} queue"
            listbox.insert(tk.END, placeholder)
            listbox.itemconfig(0, {'fg': 'gray'})  # Gray out the placeholder text
        
        # Remove from data structure
        if hasattr(self, "aircraft_data") and queue_type in self.aircraft_data:
            if callsign in self.aircraft_data[queue_type]:
                del self.aircraft_data[queue_type][callsign]
        
        # Update status bar
        self.status_bar.config(text=f"Status: Removed {callsign} from {queue_type} queue")
    
    def line_up_departure(self):
        """Issue line up and wait instruction to selected departure aircraft"""
        selection = self.departure_listbox.curselection()
        
        if not selection:
            messagebox.showinfo("Information", "Please select a departure aircraft")
            return
        
        index = selection[0]
        aircraft_info = self.departure_listbox.get(index)
        
        # Use regex to reliably extract the callsign
        match = re.match(r"^([A-Z0-9]+)", aircraft_info)
        if not match:
            messagebox.showerror("Error", "Could not extract callsign from selected aircraft.")
            return
        callsign = match.group(1)
        
        if not hasattr(self, "aircraft_data") or "departure" not in self.aircraft_data:
            messagebox.showerror("Error", "Aircraft data not found")
            return
        
        if callsign not in self.aircraft_data["departure"]:
            messagebox.showerror("Error", f"Aircraft {callsign} not found in departure data")
            return
        
        # Update aircraft status
        aircraft_data = self.aircraft_data["departure"][callsign]
        prev_status = aircraft_data["status"]
        aircraft_data["status"] = "Lined Up"
        aircraft_data["last_instruction"] = "Line up and wait"
        
        # Update listbox entry
        runway = aircraft_data["runway"]
        self.departure_listbox.delete(index)
        new_text = f"{callsign} ({aircraft_data['type']}) - Lined Up - RWY {runway}"
        self.departure_listbox.insert(index, new_text)
        
        # Update runway status to show aircraft is using runway
        self.set_runway_aircraft(runway, callsign)
        
        # Update status bar
        self.status_bar.config(text=f"Status: {callsign} instructed to line up and wait on Runway {runway}")
    
    def issue_takeoff_clearance(self):
        """Issue takeoff clearance to selected departure aircraft"""
        selection = self.departure_listbox.curselection()
        
        if not selection:
            messagebox.showinfo("Information", "Please select a departure aircraft")
            return
        
        index = selection[0]
        aircraft_info = self.departure_listbox.get(index)
        
        # Use regex to reliably extract the callsign
        match = re.match(r"^([A-Z0-9]+)", aircraft_info)
        if not match:
            messagebox.showerror("Error", "Could not extract callsign from selected aircraft.")
            return
        callsign = match.group(1)
        
        if not hasattr(self, "aircraft_data") or "departure" not in self.aircraft_data:
            messagebox.showerror("Error", "Aircraft data not found")
            return
        
        if callsign not in self.aircraft_data["departure"]:
            messagebox.showerror("Error", f"Aircraft {callsign} not found in departure data")
            return
        
        # Get aircraft data
        aircraft_data = self.aircraft_data["departure"][callsign]
        runway = aircraft_data["runway"]
        airport_data = self.airports.get(self.current_airport, {})
        runway_status = airport_data.get("runway_status", {}).get(runway, {})
        
        # Check if aircraft is lined up
        if aircraft_data["status"] != "Lined Up":
            message = f"Aircraft {callsign} is not lined up yet. Issue takeoff clearance anyway?"
            if not messagebox.askyesno("Confirm", message):
                return

        occupied_by = runway_status.get("current_aircraft")
        if occupied_by and occupied_by != callsign:
            message = f"Runway {runway} currently occupied by {occupied_by}. Issue takeoff clearance anyway?"
            if not messagebox.askyesno("Runway Occupied", message):
                return
        
        # Update aircraft status
        aircraft_data["status"] = "Taking Off"
        aircraft_data["last_instruction"] = "Cleared for takeoff"
        
        # Update listbox entry
        self.departure_listbox.delete(index)
        new_text = f"{callsign} ({aircraft_data['type']}) - Taking Off - RWY {runway}"
        self.departure_listbox.insert(index, new_text)
        
        # Set an automatic removal timer (simulating aircraft departure)
        self.root.after(10000, lambda: self.simulate_aircraft_departure(callsign))
        
        # Update status bar
        self.status_bar.config(text=f"Status: {callsign} cleared for takeoff on Runway {runway}")
        self._refresh_operational_insights()
    
    def simulate_aircraft_departure(self, callsign):
        """Simulate aircraft departure by removing it from the queue after takeoff"""
        if not hasattr(self, "aircraft_data") or "departure" not in self.aircraft_data:
            return
            
        if callsign not in self.aircraft_data["departure"]:
            return
            
        # Find the aircraft in the listbox
        aircraft_data = self.aircraft_data["departure"][callsign]
        runway = aircraft_data["runway"]
        
        # Find and remove from listbox
        for i in range(self.departure_listbox.size()):
            if callsign in self.departure_listbox.get(i):
                self.departure_listbox.delete(i)
                break
                
        # Add placeholder message if queue is now empty
        if self.departure_listbox.size() == 0:
            placeholder = "No aircraft in departure queue"
            self.departure_listbox.insert(tk.END, placeholder)
            self.departure_listbox.itemconfig(0, {'fg': 'gray'})  # Gray out the placeholder text
                
        # Remove from data structure
        del self.aircraft_data["departure"][callsign]
        
        # Clear runway
        self.clear_runway(runway)
        
        # Update status bar
        self.status_bar.config(text=f"Status: {callsign} has departed")
        self._refresh_operational_insights()
    
    def issue_landing_clearance(self):
        """Issue landing clearance to selected arrival aircraft"""
        selection = self.arrival_listbox.curselection()
        
        if not selection:
            messagebox.showinfo("Information", "Please select an arrival aircraft")
            return
        
        index = selection[0]
        aircraft_info = self.arrival_listbox.get(index)
        callsign = aircraft_info.split(" ")[0]
        
        if not hasattr(self, "aircraft_data") or "arrival" not in self.aircraft_data:
            messagebox.showerror("Error", "Aircraft data not found")
            return
        
        if callsign not in self.aircraft_data["arrival"]:
            messagebox.showerror("Error", f"Aircraft {callsign} not found in arrival data")
            return
        
        # Get aircraft data
        aircraft_data = self.aircraft_data["arrival"][callsign]
        runway = aircraft_data["runway"]
        
        # Check runway status
        airport_data = self.airports[self.current_airport]
        runway_status = airport_data.get("runway_status", {}).get(runway, {})
        
        if runway_status.get("current_aircraft") and runway_status["current_aircraft"] != callsign:
            message = f"Runway {runway} is currently occupied by {runway_status['current_aircraft']}. Clear for landing anyway?"
            if not messagebox.askyesno("Warning", message):
                return
        
        # Update aircraft status
        aircraft_data["status"] = "Cleared to Land"
        aircraft_data["last_instruction"] = "Cleared to land"
        
        # Update listbox entry
        self.arrival_listbox.delete(index)
        new_text = f"{callsign} ({aircraft_data['type']}) - Cleared to Land - RWY {runway}"
        self.arrival_listbox.insert(index, new_text)
        
        # Set runway status
        self.set_runway_aircraft(runway, callsign)
        
        # Set an automatic status update timer (simulating landing)
        self.root.after(8000, lambda: self.simulate_aircraft_landing(callsign))
        
        # Update status bar
        self.status_bar.config(text=f"Status: {callsign} cleared to land on Runway {runway}")
        self._refresh_operational_insights()
    
    def simulate_aircraft_landing(self, callsign):
        """Simulate aircraft landing by updating its status"""
        if not hasattr(self, "aircraft_data") or "arrival" not in self.aircraft_data:
            return
            
        if callsign not in self.aircraft_data["arrival"]:
            return
            
        # Update aircraft status
        aircraft_data = self.aircraft_data["arrival"][callsign]
        runway = aircraft_data["runway"]
        aircraft_data["status"] = "Landed"
        
        # Find and update in listbox
        for i in range(self.arrival_listbox.size()):
            if callsign in self.arrival_listbox.get(i):
                self.arrival_listbox.delete(i)
                new_text = f"{callsign} ({aircraft_data['type']}) - Landed - RWY {runway}"
                self.arrival_listbox.insert(i, new_text)
                break
                
        # Set a timer to clear the runway (simulating vacating)
        self.root.after(5000, lambda: self.simulate_runway_vacated(callsign))
        
        # Update status bar
        self.status_bar.config(text=f"Status: {callsign} has landed on Runway {runway}")
        self._refresh_operational_insights()
    
    def simulate_runway_vacated(self, callsign):
        """Simulate aircraft vacating the runway after landing"""
        if not hasattr(self, "aircraft_data") or "arrival" not in self.aircraft_data:
            return
            
        if callsign not in self.aircraft_data["arrival"]:
            return
            
        # Get aircraft data
        aircraft_data = self.aircraft_data["arrival"][callsign]
        runway = aircraft_data["runway"]
        
        # Clear runway
        self.clear_runway(runway)
        
        # Update aircraft status
        aircraft_data["status"] = "Taxiing to Gate"
        
        # Find and update in listbox
        for i in range(self.arrival_listbox.size()):
            if callsign in self.arrival_listbox.get(i):
                self.arrival_listbox.delete(i)
                new_text = f"{callsign} ({aircraft_data['type']}) - Taxiing to Gate"
                self.arrival_listbox.insert(i, new_text)
                break
                
        # Update status bar
        self.status_bar.config(text=f"Status: {callsign} has vacated Runway {runway}")
        self._refresh_operational_insights()
    
    def issue_approach_clearance(self):
        """Issue approach clearance to selected arrival aircraft"""
        selection = self.arrival_listbox.curselection()
        
        if not selection:
            messagebox.showinfo("Information", "Please select an arrival aircraft")
            return
        
        index = selection[0]
        aircraft_info = self.arrival_listbox.get(index)
        callsign = aircraft_info.split(" ")[0]
        
        if not hasattr(self, "aircraft_data") or "arrival" not in self.aircraft_data:
            messagebox.showerror("Error", "Aircraft data not found")
            return
        
        if callsign not in self.aircraft_data["arrival"]:
            messagebox.showerror("Error", f"Aircraft {callsign} not found in arrival data")
            return
        
        # Get aircraft data
        aircraft_data = self.aircraft_data["arrival"][callsign]
        runway = aircraft_data["runway"]
        approach_type = aircraft_data.get("approach_type", "ILS")
        
        # Update aircraft status
        prev_status = aircraft_data["status"]
        aircraft_data["status"] = "Final Approach"
        aircraft_data["last_instruction"] = f"Cleared for {approach_type} approach runway {runway}"
        
        # Update listbox entry
        self.arrival_listbox.delete(index)
        new_text = f"{callsign} ({aircraft_data['type']}) - Final Approach - RWY {runway}"
        self.arrival_listbox.insert(index, new_text)
        
        # Set a timer to simulate aircraft getting closer (for visual indication)
        self.root.after(8000, lambda: self.simulate_aircraft_on_final(callsign))
        
        # Update status bar
        self.status_bar.config(text=f"Status: {callsign} cleared for {approach_type} approach to Runway {runway}")
        self._refresh_operational_insights()
        
    def simulate_aircraft_on_final(self, callsign):
        """Simulate aircraft reaching final approach phase"""
        if not hasattr(self, "aircraft_data") or "arrival" not in self.aircraft_data:
            return
            
        if callsign not in self.aircraft_data["arrival"]:
            return
            
        # Update aircraft status
        aircraft_data = self.aircraft_data["arrival"][callsign]
        runway = aircraft_data["runway"]
        aircraft_data["status"] = "Short Final"
        
        # Find and update in listbox
        for i in range(self.arrival_listbox.size()):
            if callsign in self.arrival_listbox.get(i):
                self.arrival_listbox.delete(i)
                new_text = f"{callsign} ({aircraft_data['type']}) - Short Final - RWY {runway}"
                self.arrival_listbox.insert(i, new_text)
                self.arrival_listbox.selection_set(i)
                break
                
        # Update status bar
        self.status_bar.config(text=f"Status: {callsign} on short final for Runway {runway}")
    
    def set_runway_aircraft(self, runway, callsign):
        """Set an aircraft as currently using a runway"""
        airport_data = self.airports[self.current_airport]
        if "runway_status" not in airport_data:
            airport_data["runway_status"] = {}
            
        if runway not in airport_data["runway_status"]:
            airport_data["runway_status"][runway] = {
                "active": True,
                "direction": "Both",
                "current_aircraft": None
            }
            
        airport_data["runway_status"][runway]["current_aircraft"] = callsign
        
        # Update the runway display
        self.update_runway_frame()
    
    def clear_runway(self, runway):
        """Clear an aircraft from a runway"""
        airport_data = self.airports[self.current_airport]
        if "runway_status" in airport_data and runway in airport_data["runway_status"]:
            airport_data["runway_status"][runway]["current_aircraft"] = None
            
        # Update the runway display
        self.update_runway_frame()

    def update_frequency_display(self):
        """Update all frequency displays in the UI with the current airport frequencies"""
        # Update frequency information in the status bar
        if hasattr(self, "frequency_label") and self.airport_config.get('frequencies'):
            frequencies = self.airport_config['frequencies']
            tower_freq = frequencies.get('tower', 'N/A')
            ground_freq = frequencies.get('ground', 'N/A')
            
            freq_text = f"TWR: {tower_freq} | GND: {ground_freq}"
            
            # Optional frequencies if available
            if 'approach' in frequencies:
                freq_text += f" | APP: {frequencies['approach']}"
            if 'departure' in frequencies:
                freq_text += f" | DEP: {frequencies['departure']}"
            if 'atis' in frequencies:
                freq_text += f" | ATIS: {frequencies['atis']}"
                
            self.frequency_label.config(text=freq_text)
        
        # Update frequencies in the Tower tab
        if hasattr(self, "tower_freq_display"):
            tower_freq = self.airport_config.get('frequencies', {}).get('tower', 'N/A')
            self.tower_freq_display.config(text=f"TWR: {tower_freq}")
            
        # Update frequencies in the Ground tab
        if hasattr(self, "ground_freq_display"):
            ground_freq = self.airport_config.get('frequencies', {}).get('ground', 'N/A')
            self.ground_freq_display.config(text=f"GND: {ground_freq}")
            
        # Update frequencies in any other tabs as needed
        # For example, Approach tab
        if hasattr(self, "approach_freq_display") and hasattr(self.airport_config.get('frequencies', {}), 'approach'):
            approach_freq = self.airport_config['frequencies']['approach']
            self.approach_freq_display.config(text=f"APP: {approach_freq}")

    def update_runway_frame(self):
        """Update the runway status display in the Tower tab"""
        # Clear existing runway frame contents
        for widget in self.runway_frame.winfo_children():
            widget.destroy()
            
        # Get current airport data
        airport_data = self.airports.get(self.current_airport, {})
        runways = airport_data.get("runways", [])
        
        if not runways:
            ttk.Label(self.runway_frame, text="No runways defined for this airport").pack(pady=10)
            return
            
        # Create a frame for each runway
        runway_grid = ttk.Frame(self.runway_frame)
        runway_grid.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Header row
        ttk.Label(runway_grid, text="Runway", font=("Arial", 10, "bold")).grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(runway_grid, text="Status", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(runway_grid, text="Direction", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=5, pady=5)
        ttk.Label(runway_grid, text="Current Aircraft", font=("Arial", 10, "bold")).grid(row=0, column=3, padx=5, pady=5)
        ttk.Label(runway_grid, text="Action", font=("Arial", 10, "bold")).grid(row=0, column=4, padx=5, pady=5)
        
        # Initialize runway status if not present
        if "runway_status" not in airport_data:
            airport_data["runway_status"] = {}
            
        # Create a row for each runway
        for idx, runway in enumerate(runways):
            # Get or create runway status
            if runway not in airport_data["runway_status"]:
                airport_data["runway_status"][runway] = {
                    "active": True,
                    "direction": "Both",
                    "current_aircraft": None
                }
                
            runway_status = airport_data["runway_status"][runway]
            
            # Runway identifier
            ttk.Label(runway_grid, text=runway).grid(row=idx+1, column=0, padx=5, pady=5)
            
            # Status (Active/Closed)
            status_text = "Active" if runway_status["active"] else "Closed"
            status_color = "green" if runway_status["active"] else "red"
            status_label = ttk.Label(runway_grid, text=status_text)
            status_label.grid(row=idx+1, column=1, padx=5, pady=5)
            
            # Apply color to status label using a style
            style_name = f"Runway{idx}.TLabel"
            style = ttk.Style()
            style.configure(style_name, foreground=status_color)
            status_label.configure(style=style_name)
            
            # Direction selector
            direction_var = tk.StringVar(value=runway_status["direction"])
            direction_combo = ttk.Combobox(
                runway_grid, 
                textvariable=direction_var,
                values=["Both", runway.split("/")[0], runway.split("/")[1] if "/" in runway else ""],
                width=10,
                state="readonly"
            )
            direction_combo.grid(row=idx+1, column=2, padx=5, pady=5)
            
            # Bind direction change event
            direction_combo.bind(
                "<<ComboboxSelected>>", 
                lambda event, rwy=runway: self.change_runway_direction(rwy, event.widget.get())
            )
            
            # Current aircraft
            aircraft = runway_status.get("current_aircraft", "None")
            aircraft_text = aircraft if aircraft else "None"
            aircraft_color = "red" if aircraft else "black"
            aircraft_label = ttk.Label(runway_grid, text=aircraft_text)
            aircraft_label.grid(row=idx+1, column=3, padx=5, pady=5)
            
            # Apply color for aircraft label
            aircraft_style = f"Aircraft{idx}.TLabel"
            style.configure(aircraft_style, foreground=aircraft_color)
            aircraft_label.configure(style=aircraft_style)
            
            # Toggle active status button
            toggle_text = "Close Runway" if runway_status["active"] else "Activate Runway"
            toggle_button = ttk.Button(
                runway_grid,
                text=toggle_text,
                command=lambda rwy=runway: self.toggle_runway_status(rwy)
            )
            toggle_button.grid(row=idx+1, column=4, padx=5, pady=5)
            
        # Instructions panel below runway grid
        instr_frame = ttk.LabelFrame(self.runway_frame, text="Instructions")
        instr_frame.pack(fill="x", padx=10, pady=(10, 5))
        
        # Get airport-specific instructions if available
        icao_code = self.current_airport.split(" - ")[0] if " - " in self.current_airport else ""
        runway_instructions = []
        
        # Add airport-specific instructions if they exist
        airport_specific_instructions = airport_data.get("runway_instructions", [])
        if airport_specific_instructions:
            runway_instructions.extend(airport_specific_instructions)
        
        # Check for special procedures based on ICAO region
        if icao_code.startswith("K"):  # USA
            if not runway_instructions:
                runway_instructions.append(f"• {icao_code} follows FAA procedures for runway operations")
            runway_instructions.append("• Land and Hold Short Operations (LAHSO) may be in effect")
            
        elif icao_code.startswith("E"):  # Europe
            if not runway_instructions:
                runway_instructions.append(f"• {icao_code} follows EASA procedures for runway operations")
            runway_instructions.append("• Reduced separation on parallel runways may be applied")
            
        elif icao_code.startswith("R"):  # Russia
            if not runway_instructions:
                runway_instructions.append(f"• {icao_code} follows Russian procedures for runway operations")
            
        elif icao_code.startswith("Z"):  # China
            if not runway_instructions:
                runway_instructions.append(f"• {icao_code} follows CAAC procedures for runway operations")
            
        # Add generic instructions if no specific ones defined
        if not runway_instructions:
            runway_instructions = [
                "• Active runways are available for takeoffs and landings",
                "• Set runway direction based on current wind and traffic",
                "• Aircraft will appear in the 'Current Aircraft' column when using the runway",
                "• Close a runway for maintenance or emergencies"
            ]
        
        # Look for special runway configurations
        is_parallel = any("/" in runway for runway in runways)
        if is_parallel:
            runway_instructions.append("• Parallel runway operations in effect - monitor separations carefully")
        
        if len(runways) > 2:
            runway_instructions.append("• Multiple runway configuration - coordinate crossing clearances")
            
        # Add instructions about current weather if available
        wind = airport_data.get("wind", "")
        if wind and "calm" not in wind.lower():
            runway_instructions.append(f"• Current winds: {wind} - select runway direction accordingly")
            
        # Add instructions about local time restrictions if in airport data
        time_restrictions = airport_data.get("time_restrictions", [])
        if time_restrictions:
            for restriction in time_restrictions:
                runway_instructions.append(f"• {restriction}")
        
        # Display all instructions
        for instr in runway_instructions:
            ttk.Label(instr_frame, text=instr, wraplength=600, justify="left").pack(anchor="w", padx=5, pady=2)
    
    def toggle_runway_status(self, runway):
        """Toggle a runway between active and closed status"""
        airport_data = self.airports[self.current_airport]
        if "runway_status" not in airport_data:
            airport_data["runway_status"] = {}
            
        if runway not in airport_data["runway_status"]:
            airport_data["runway_status"][runway] = {
                "active": True,
                "direction": "Both",
                "current_aircraft": None
            }
        
        # Toggle the status
        current_status = airport_data["runway_status"][runway]["active"]
        new_status = not current_status
        airport_data["runway_status"][runway]["active"] = new_status
        
        # Check if an aircraft is currently on this runway
        current_aircraft = airport_data["runway_status"][runway].get("current_aircraft")
        if current_aircraft and not new_status:
            # Warn user about closing a runway with aircraft on it
            if not messagebox.askyesno(
                "Warning", 
                f"Runway {runway} currently has aircraft {current_aircraft} on it. Are you sure you want to close it?"
            ):
                # Revert the change if user cancels
                airport_data["runway_status"][runway]["active"] = current_status
                return
                
        # Update the runway display
        self.update_runway_frame()
        
        # Update status bar
        status_text = "active" if new_status else "closed"
        self.status_bar.config(text=f"Status: Runway {runway} is now {status_text}")
        
    def change_runway_direction(self, runway, direction):
        """Change the active direction for a runway"""
        airport_data = self.airports[self.current_airport]
        if "runway_status" not in airport_data:
            airport_data["runway_status"] = {}
            
        if runway not in airport_data["runway_status"]:
            airport_data["runway_status"][runway] = {
                "active": True,
                "direction": "Both",
                "current_aircraft": None
            }
            
        # Update the direction
        airport_data["runway_status"][runway]["direction"] = direction
        
        # Update status bar
        self.status_bar.config(text=f"Status: Runway {runway} direction set to {direction}")
        
    def update_airport_config(self):
        """Update the airport configuration when the current airport changes"""
        # Get the current airport information
        self.airport_config = self.airports.get(self.current_airport, {})
        
        # Update all displays that depend on airport information
        if hasattr(self, "runway_frame"):
            self.update_runway_frame()
        self.update_frequency_display()
        
        # Path graph is per-ICAO — reload when airport changes
        self._path_graph_cached_icao = None
        self._path_graph_obj = None
        self._path_link_first = None

        # Update any diagrams or visualizations
        self._redraw_all_airport_canvases()
            
        # Clear and update aircraft lists based on current airport
        if hasattr(self, "ground_aircraft_list"):
            self.ground_aircraft_list.delete(0, tk.END)
        
        # Reset aircraft data structures
        self.aircraft_data = {"departure": {}, "arrival": {}}
        
        # Clear tower tab listboxes and add placeholders
        if hasattr(self, "departure_listbox"):
            self.departure_listbox.delete(0, tk.END)
            self.departure_listbox.insert(tk.END, "No aircraft in departure queue")
            self.departure_listbox.itemconfig(0, {'fg': 'gray'})
            
        if hasattr(self, "arrival_listbox"):
            self.arrival_listbox.delete(0, tk.END)
            self.arrival_listbox.insert(tk.END, "No aircraft in arrival queue")
            self.arrival_listbox.itemconfig(0, {'fg': 'gray'})
            
        # Update status bar
        self.status_bar.config(text=f"Status: Switched to airport {self.current_airport}")
        
    def on_airport_change(self, event):
        """Handle when the user selects a different airport"""
        self.current_airport = self.airport_var.get()
        self.update_airport_config()
        self.update_weather_display()

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
        """Apply received sim state: update Live label and optionally switch airport by ICAO."""
        if hasattr(self, "live_icao_label"):
            if state.icao:
                self.live_icao_label.config(text=f"Live: {state.icao}", foreground="green")
            else:
                self.live_icao_label.config(text="Live: ---", foreground="gray")
        if not state.icao or not self.airports:
            return
        for name, data in self.airports.items():
            if (data.get("icao") or "").upper() == state.icao.upper():
                if name != self.current_airport and hasattr(self, "airport_var"):
                    self.current_airport = name
                    self.airport_var.set(name)
                    if hasattr(self, "airport_combo"):
                        try:
                            idx = list(self.airports.keys()).index(name)
                            self.airport_combo.current(idx)
                        except (ValueError, tk.TclError):
                            pass
                    self.update_airport_config()
                break

    def _on_xplane_bridge_toggle(self) -> None:
        """Enable or disable the X-Plane bridge and persist setting."""
        enabled = self.xplane_var.get()
        self._sim_bridge_enabled = enabled
        self.config.set("xplane_bridge_enabled", enabled)
        self.config.save_config()
        if self.sim_bridge:
            if enabled:
                if self.sim_bridge.start():
                    self.status_bar.config(text="Status: X-Plane bridge enabled - receiving sim context")
                else:
                    self.xplane_var.set(False)
                    self._sim_bridge_enabled = False
                    self.status_bar.config(text="Status: Could not start X-Plane bridge (port in use?)")
            else:
                self.sim_bridge.stop()
                if hasattr(self, "live_icao_label"):
                    self.live_icao_label.config(text="Live: ---", foreground="gray")
                self.status_bar.config(text="Status: X-Plane bridge disabled")

    def issue_instruction(self, instruction_type):
        """Issue a specific instruction to a selected aircraft"""
        # Determine which listbox is active based on the notebook tab
        selected_tab = self.notebook.tab(self.notebook.select(), "text")
        if selected_tab == "Ground Control":
            listbox = self.ground_aircraft_list
        elif selected_tab == "Tower":
            # In Tower, we need to determine if it's departure or arrival
            # For now, we'll use departure listbox as default
            listbox = self.departure_listbox
        else:
            # For now, only ground and tower have instruction context
            messagebox.showinfo("Unsupported", "Instructions can only be issued from Ground or Tower tabs.")
            return

        selected = listbox.curselection()
        if not selected:
            messagebox.showinfo(
                "Selection Required", "Please select an aircraft to issue an instruction to"
            )
            return
            
        aircraft_info = listbox.get(selected)
        callsign = aircraft_info.split(" - ")[0]
        
        # Create a dialog to get instruction details
        dialog = tk.Toplevel(self.root)
        dialog.title("Issue Instruction")
        dialog.geometry("450x300")
        dialog.transient(self.root)
        dialog.grab_set()

        # Instruction categories
        instructions = {
            "Ground": [
                "Taxi to Runway", "Taxi to Gate", "Taxi to Holding Point", 
                "Hold Position", "Pushback Approved"
            ],
            "Departure": [
                "Line Up and Wait", "Cleared for Takeoff", "Cancel Takeoff Clearance"
            ],
            "En-route": [
                "Climb and Maintain", "Descend and Maintain", "Proceed Direct", 
                "Contact Approach", "Contact Center"
            ],
            "Arrival": [
                "Cleared for ILS Approach", "Cleared for Visual Approach", "Cleared for RNAV Approach",
                "Cleared to Land", "Go Around"
            ]
        }
        
        # Create a list with separators
        instruction_options = []
        for category, items in instructions.items():
            instruction_options.append(f"--- {category.upper()} ---")
            instruction_options.extend(items)
            
        ttk.Label(dialog, text="Instruction Type:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        instruction_var = tk.StringVar()
        instruction_combo = ttk.Combobox(
            dialog, textvariable=instruction_var, values=instruction_options,
            state="readonly", width=30
        )
        instruction_combo.grid(row=0, column=1, padx=10, pady=10)

        # Prevent selection of separators
        def on_instruction_select(event):
            selected_item = instruction_var.get()
            if selected_item.startswith("---"):
                # Find the next valid item to select
                current_index = instruction_options.index(selected_item)
                if current_index + 1 < len(instruction_options):
                    next_item = instruction_options[current_index + 1]
                    if not next_item.startswith("---"):
                        instruction_combo.set(next_item)
                else: # if separator is the last item, clear selection
                    instruction_combo.set("")
        
        instruction_combo.bind("<<ComboboxSelected>>", on_instruction_select)

        # Frame for dynamic input fields
        params_frame = ttk.Frame(dialog)
        params_frame.grid(row=1, column=0, columnspan=2, padx=10, pady=10, sticky="nsew")

        # Function to update parameters based on selected instruction
        def update_params(event):
            # Clear previous params
            for widget in params_frame.winfo_children():
                widget.destroy()
            
            instruction = instruction_var.get()
            
            if instruction == "Taxi to Runway":
                ttk.Label(params_frame, text="Runway:").grid(row=0, column=0, sticky="w")
                runway_entry = ttk.Entry(params_frame)
                runway_entry.grid(row=0, column=1)
                
                ttk.Label(params_frame, text="Taxi Route:").grid(row=1, column=0, sticky="w")
                route_entry = ttk.Entry(params_frame)
                route_entry.grid(row=1, column=1)
                
            elif instruction == "Hold Position":
                ttk.Label(params_frame, text="Location:").grid(row=0, column=0, sticky="w")
                loc_entry = ttk.Entry(params_frame)
                loc_entry.insert(0, "Current Position")
                loc_entry.grid(row=0, column=1)

        instruction_combo.bind("<<ComboboxSelected>>", update_params, add="+")

        def issue():
            selected_instruction = instruction_var.get()
            # This is where you would build the full instruction text based on params
            # For now, we just show a confirmation
            
            instruction_text = f"Issued '{selected_instruction}' to {callsign}"
            
            messagebox.showinfo("Instruction Issued", instruction_text)
            self.status_bar.config(text=f"Status: {instruction_text}")
            dialog.destroy()

        ttk.Button(dialog, text="Issue", command=issue).grid(row=2, column=0, columnspan=2, pady=20)

        dialog.wait_window()

    def enrich_airport_data(self):
        """Enriches airport data with dynamic information like runway directions"""
        for airport_code, airport_data in self.airports.items():
            icao_code = airport_code.split(" - ")[0] if " - " in airport_code else ""
            
            # Add specific runway instructions if not present
            if "runway_instructions" not in airport_data:
                if icao_code.startswith("K"):  # US airports
                    airport_data["runway_instructions"] = [
                        f"• {icao_code} follows FAA standard operating procedures",
                        "• Intersection departures are available upon request",
                        "• Monitor ATIS for active runway configurations"
                    ]
                elif icao_code.startswith("E"):  # European airports
                    airport_data["runway_instructions"] = [
                        f"• {icao_code} follows EASA standard operating procedures",
                        "• Noise abatement procedures in effect between 2200-0600 local",
                        "• Monitor ATIS for active runway configurations"
                    ]
                else:
                    airport_data["runway_instructions"] = [
                        f"• Follow standard operating procedures for {icao_code}",
                        "• Monitor current weather for runway selection",
                        "• Refer to local airport regulations"
                    ]
            
            # Add time restrictions if not present
            if "time_restrictions" not in airport_data:
                if "London" in airport_code or "Heathrow" in airport_code:
                    airport_data["time_restrictions"] = [
                        "Night curfew in effect 23:30-06:00 local time",
                        "Reduced operations between 23:00-23:30"
                    ]
                elif "Frankfurt" in airport_code:
                    airport_data["time_restrictions"] = [
                        "Night flight restrictions 23:00-05:00 local time"
                    ]
                elif "Los Angeles" in airport_code or "LAX" in airport_code:
                    airport_data["time_restrictions"] = [
                        "Over-ocean operations typically from midnight to 06:30"
                    ]
            
            # Add approach types for specific runways
            runways = airport_data.get("runways", [])
            for runway in runways:
                approach_key = f"approaches_{runway}"
                if approach_key not in airport_data:
                    # Create default approaches
                    approaches = ["ILS", "Visual"]
                    
                    # Add more specific approaches based on airport
                    if icao_code.startswith("K"):  # US
                        approaches.extend(["RNAV (GPS)", "RNAV (RNP)"])
                        if int(runway.replace('L', '').replace('R', '').replace('C', '')) < 18:
                            approaches.append("VOR/DME")
                    elif icao_code.startswith("E"):  # Europe
                        approaches.extend(["RNAV (GPS)", "VOR/DME"])
                        if runway.endswith('L') or runway.endswith('R'):
                            approaches.append("LLZ")
                    else:
                        approaches.append("NDB")
                        
                    airport_data[approach_key] = approaches
                    
            # Add terminal information if not present
            if "terminals" not in airport_data and "gates" in airport_data:
                # Try to deduce terminals from gate naming
                terminals = set()
                for gate in airport_data["gates"]:
                    if gate.startswith("T") and len(gate) > 1 and gate[1].isdigit():
                        terminals.add(f"Terminal {gate[1]}")
                    elif gate[0].isalpha() and len(gate) > 1:
                        terminals.add(f"Terminal {gate[0]}")
                        
                if terminals:
                    airport_data["terminals"] = list(terminals)
                else:
                    airport_data["terminals"] = ["Main Terminal"]

    def update_ground_status_indicators(self, event):
        """Update the status indicators when an aircraft is selected"""
        # Check if ground_status_indicators exists
        if not hasattr(self, "ground_status_indicators"):
            return
            
        # Get selected aircraft
        selected = self.ground_aircraft_tree.curselection()
        if not selected:
            # Clear all indicators if nothing selected
            for canvas in self.ground_status_indicators:
                canvas.config(bg="white")
            return
            
        # Get the aircraft info
        aircraft_info = self.ground_aircraft_tree.get(selected)
        status = aircraft_info.split(" - ")[3] if len(aircraft_info.split(" - ")) > 3 else ""
        
        # Reset all indicators
        for canvas in self.ground_status_indicators:
            canvas.config(bg="white")
            
        # Set indicators based on status
        if "Ready to Taxi" in status:
            self.ground_status_indicators[0].config(bg="green")
        elif "Pushback" in status:
            self.ground_status_indicators[1].config(bg="blue")
        elif "Taxiing" in status:
            self.ground_status_indicators[2].config(bg="yellow")
            self.ground_status_indicators[3].config(bg="yellow")
        elif "Hold Short" in status:
            self.ground_status_indicators[4].config(bg="red")
        elif "Line Up" in status or "Takeoff" in status:
            self.ground_status_indicators[5].config(bg="purple")
        elif "Parked" in status:
            self.ground_status_indicators[6].config(bg="gray")

    def fetch_live_weather(self, icao_code):
        """Fetch live weather data for the specified airport ICAO code"""
        # Use threading to avoid freezing the UI
        def fetch_weather_thread():
            try:
                # In a real application, you would make an API call here
                # For example: response = requests.get(f"https://api.example.com/metar/{icao_code}")
                
                # For demonstration, simulate a response with sample data
                # Randomize weather slightly for realism
                wind_dir = random.randint(0, 359)
                wind_speed = random.randint(3, 15)
                
                # Get airport data to potentially use for weather simulation
                airport_data = self.airports.get(self.current_airport, {})
                
                # Simulate different weather based on ICAO region
                if icao_code.startswith("K"):  # US airports
                    visibility = random.choice(["10SM", "7SM", "5SM", "3SM"])
                    ceiling = random.choice(["CLR", "FEW050", "SCT065", "BKN080"])
                    temp = random.randint(15, 30)
                    dewpoint = random.randint(10, 20)
                elif icao_code.startswith("E"):  # European airports
                    visibility = random.choice(["9999", "8000", "5000", "2500"])
                    ceiling = random.choice(["NSC", "FEW045", "SCT060", "BKN070"])
                    temp = random.randint(10, 25)
                    dewpoint = random.randint(5, 15)
                else:
                    visibility = random.choice(["9999", "8000", "5000"])
                    ceiling = random.choice(["NSC", "FEW040", "SCT055"])
                    temp = random.randint(15, 35)
                    dewpoint = random.randint(10, 25)
                
                # Create simulated METAR
                metar = f"{icao_code} {self._get_time_string()} AUTO {wind_dir:03d}{wind_speed:02d}KT {visibility} {ceiling} {temp:02d}/{dewpoint:02d} Q{random.randint(1013, 1030)}"
                
                # Update weather data in airport configuration
                if not icao_code.startswith("K"):  # Non-US format
                    wind_str = f"{wind_dir:03d}° at {wind_speed} KT"
                else:  # US format
                    wind_str = f"{wind_dir:03d}° at {wind_speed} KTS"
                    
                if self.current_airport in self.airports:
                    self.airports[self.current_airport]["wind"] = wind_str
                    self.airports[self.current_airport]["visibility"] = visibility
                    self.airports[self.current_airport]["ceiling"] = ceiling
                    self.airports[self.current_airport]["metar"] = metar
                    
                # Update the display
                self.root.after(0, self.update_weather_display)
                
            except Exception as e:
                # In a real application, handle errors gracefully
                logger.warning("Error fetching weather: %s", e)
                self.root.after(0, lambda: self.status_bar.config(text=f"Status: Error fetching weather data"))
        
        # Start the thread
        threading.Thread(target=fetch_weather_thread).start()
        
        # Update status bar
        self.status_bar.config(text=f"Status: Fetching weather for {icao_code}...")
        
    def _get_time_string(self):
        """Create a time string in METAR format (ddhhmm)Z"""
        from datetime import datetime
        now = datetime.utcnow()
        return f"{now.day:02d}{now.hour:02d}{now.minute:02d}Z"
        
    def update_weather_display(self):
        """Update the weather display with current data"""
        # Get current airport weather data
        airport_data = self.airports.get(self.current_airport, {})
        
        # Format the weather information
        wind = airport_data.get("wind", "No data")
        visibility = airport_data.get("visibility", "No data")
        ceiling = airport_data.get("ceiling", "No data")
        metar = airport_data.get("metar", "No METAR available")
        
        # Update the main weather display
        weather_text = f"Wind: {wind}\nVis: {visibility}\nCeiling: {ceiling}"
        self.weather_display.config(text=weather_text)
        
        # Update Tower tab weather display if available
        if hasattr(self, "tower_weather_display"):
            tower_weather = f"Current Weather:\n{wind}\nVisibility: {visibility}\nCeiling: {ceiling}\n\nMETAR:\n{metar}"
            self.tower_weather_display.config(state=tk.NORMAL)
            self.tower_weather_display.delete(1.0, tk.END)
            self.tower_weather_display.insert(tk.END, tower_weather)
            self.tower_weather_display.config(state=tk.DISABLED)
        
        # Update status bar
        self.status_bar.config(text=f"Status: Weather updated for {self.current_airport}")

    def transfer_aircraft(self, destination):
        """Transfer an aircraft to another controller position"""
        selected_item = self.ground_aircraft_tree.selection()
        if not selected_item:
            messagebox.showinfo(
                "Selection Required", "Please select an aircraft to transfer"
            )
            return
            
        aircraft_info = self.ground_aircraft_tree.item(selected_item[0], 'values')
        callsign = aircraft_info[0]
        aircraft_type = aircraft_info[1]
        
        # Remove from ground list
        self.ground_aircraft_tree.delete(selected_item[0])
        
        # Different behavior based on destination
        if destination == "Tower":
            # Add to Tower's departure queue
            if hasattr(self, "departure_listbox"):
                # Remove placeholder if it exists
                if self.departure_listbox.size() > 0 and "No aircraft" in self.departure_listbox.get(0):
                    self.departure_listbox.delete(0)

                display_text = f"{callsign} ({aircraft_type}) - Ready for Departure"
                self.departure_listbox.insert(tk.END, display_text)
                
                # Store additional data if we have the aircraft_data structure
                if hasattr(self, "aircraft_data") and "departure" in self.aircraft_data:
                    # Get current airport data
                    airport_data = self.airports.get(self.current_airport, {})
                    runways = airport_data.get("runways", [])
                    runway = runways[0] if runways else "27"  # Default runway if none defined
                    
                    # Create aircraft data structure
                    self.aircraft_data["departure"][callsign] = {
                        "callsign": callsign,
                        "type": aircraft_type,
                        "runway": runway,
                        "status": "Ready for Departure",
                        "last_instruction": "Contact Tower",
                        "time_added": time.strftime("%H:%M:%S")
                    }
                
            # Display transfer message
            tower_freq = self.get_tower_frequency()
            self.log_communication(self.ground_instructions, "GROUND", f"{callsign}, contact Tower on {tower_freq}.")
            
        # Could add other destinations here (Approach, Departure, etc.)
        
        # Update status bar
        self.status_bar.config(text=f"Status: {callsign} transferred to {destination}")
    
    def get_tower_frequency(self):
        """Get the tower frequency for the current airport"""
        airport_data = self.airports.get(self.current_airport, {})
        frequencies = airport_data.get("frequencies", {})
        return frequencies.get("tower", "118.1")  # Default frequency if not defined

    def draw_airport_diagram(self, canvas):
        """Draw a detailed and improved airport diagram on the provided canvas."""
        canvas.delete("all")

        # Get canvas dimensions. If they are 1, the canvas is not yet sized.
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()

        if canvas_width <= 1 or canvas_height <= 1:
            return # Don't draw if canvas is not yet sized

        airport_data = self.airports.get(self.current_airport, {})

        if not self.path_show_schematic_var.get():
            try:
                bg = canvas.cget("bg")
            except tk.TclError:
                bg = "#2b2b3a"
            canvas.create_rectangle(0, 0, canvas_width, canvas_height, fill=bg, outline="")
            canvas.create_text(
                canvas_width / 2,
                14,
                text="Airport schematic hidden — path graph only",
                font=("Arial", 9, "italic"),
                fill="#95a5a6",
                tags="schematic_hint",
            )
            self._draw_path_graph_overlay(canvas)
            self._draw_session_traffic_blips(canvas)
            return

        theme = DEFAULT_DIAGRAM_THEME
        canvas.create_rectangle(
            0, 0, canvas_width, canvas_height, fill=theme.grass_top, outline=""
        )
        canvas.create_rectangle(
            0,
            canvas_height * 0.55,
            canvas_width,
            canvas_height,
            fill=theme.grass_horizon,
            outline="",
        )
        canvas.create_rectangle(
            0,
            canvas_height * 0.72,
            canvas_width,
            canvas_height,
            fill=theme.grass_bottom,
            outline="",
        )

        runways = airport_data.get("runways", [])
        taxiways = airport_data.get("taxiways", [])
        gates = airport_data.get("gates", [])

        if not runways:
            self._draw_no_diagram_message(canvas, canvas_width, canvas_height)
            self._draw_path_graph_overlay(canvas)
            self._draw_session_traffic_blips(canvas)
            return

        n_rwys = min(len(runways), 4)
        layout = compute_diagram_layout(canvas_width, canvas_height, n_rwys)
        runway_length = layout["runway_length"]
        runway_width = layout["runway_width"]
        runway_ys = layout["runway_ys"]
        main_taxiway_y = layout["main_taxiway_y"]
        apron_top_y = layout["apron_top_y"]
        apron_bottom_y = layout["apron_bottom_y"]

        for i in range(n_rwys):
            self._draw_runway(
                canvas,
                canvas_width,
                runway_ys[i],
                runway_length,
                runway_width,
                runways[i],
                theme,
            )

        self._draw_taxiways(
            canvas,
            canvas_width,
            runway_length,
            runway_ys,
            main_taxiway_y,
            taxiways,
            runway_width,
            (airport_data.get("icao") or "").upper(),
            theme,
            layout["taxi_main_width"],
            layout["taxi_conn_width"],
        )
        self._draw_aprons_and_gates(
            canvas, canvas_width, apron_top_y, apron_bottom_y, gates, theme
        )
        self._draw_diagram_labels(canvas, canvas_width, canvas_height, airport_data, theme)
        self._draw_path_graph_overlay(canvas)
        self._draw_session_traffic_blips(canvas)

    def _traffic_anim_smooth(self, u: float) -> float:
        u = max(0.0, min(1.0, u))
        return u * u * (3.0 - 2.0 * u)

    def _sync_traffic_anim_from_active(self) -> None:
        """Interpolate blips when map_nx/map_ny changes (node-to-node movement)."""
        if not getattr(self, "current_session_active", False):
            return
        for cs in list(self._traffic_prev_xy):
            if cs not in self.active_aircraft:
                self._traffic_prev_xy.pop(cs, None)
                self._traffic_anim.pop(cs, None)
        started = False
        for cs, ac in self.active_aircraft.items():
            nx = float(ac.get("map_nx", 0.5))
            ny = float(ac.get("map_ny", 0.5))
            if cs not in self._traffic_prev_xy:
                self._traffic_prev_xy[cs] = (nx, ny)
                continue
            px, py = self._traffic_prev_xy[cs]
            if abs(px - nx) > 1e-5 or abs(py - ny) > 1e-5:
                self._traffic_anim[cs] = {
                    "sx": px,
                    "sy": py,
                    "tx": nx,
                    "ty": ny,
                    "t0": time.monotonic(),
                    "dur": 0.65,
                }
                self._traffic_prev_xy[cs] = (nx, ny)
                started = True
        if started or (self._traffic_anim and self._traffic_anim_job is None):
            self._schedule_traffic_blip_anim()

    def _schedule_traffic_blip_anim(self) -> None:
        if self._traffic_anim_job is not None:
            return
        self._traffic_anim_job = self.root.after(30, self._traffic_blip_anim_tick)

    def _traffic_blip_anim_tick(self) -> None:
        self._traffic_anim_job = None
        if not getattr(self, "current_session_active", False):
            self._traffic_anim.clear()
            return
        now = time.monotonic()
        alive = False
        for cs, st in list(self._traffic_anim.items()):
            if (now - st["t0"]) < st["dur"]:
                alive = True
                break
        for w in self._path_canvas_widgets():
            w.delete("traffic_blip")
            self._draw_session_traffic_blips(w)
        if alive:
            self._traffic_anim_job = self.root.after(30, self._traffic_blip_anim_tick)

    def _cancel_traffic_blip_anim(self) -> None:
        if self._traffic_anim_job is not None:
            try:
                self.root.after_cancel(self._traffic_anim_job)
            except tk.TclError:
                pass
            self._traffic_anim_job = None
        self._traffic_anim.clear()
        self._traffic_prev_xy.clear()

    def _draw_session_traffic_blips(self, canvas: tk.Canvas) -> None:
        """Draw active session aircraft on the diagram (tags above path graph redraw)."""
        if not getattr(self, "current_session_active", False) or not self.active_aircraft:
            return
        cw = canvas.winfo_width()
        ch = canvas.winfo_height()
        if cw <= 1 or ch <= 1:
            return
        light_bg = self.path_show_schematic_var.get()
        text_fill = "#1a2433" if light_bg else "#ecf0f1"
        now = time.monotonic()
        for cs, ac in self.active_aircraft.items():
            nx = float(ac.get("map_nx", 0.5))
            ny = float(ac.get("map_ny", 0.5))
            anim = self._traffic_anim.get(cs)
            if anim:
                elapsed = now - anim["t0"]
                u = self._traffic_anim_smooth(elapsed / anim["dur"]) if anim["dur"] > 0 else 1.0
                nx = anim["sx"] + (anim["tx"] - anim["sx"]) * u
                ny = anim["sy"] + (anim["ty"] - anim["sy"]) * u
                if elapsed >= anim["dur"]:
                    self._traffic_anim.pop(cs, None)
            x, y = nx * cw, ny * ch
            fill = "#e74c3c" if ac.get("emergency") else "#f39c12"
            r = 6
            canvas.create_oval(
                x - r, y - r, x + r, y + r,
                fill=fill, outline="#ecf0f1", width=2, tags="traffic_blip",
            )
            label = ac.get("callsign", "?")
            canvas.create_text(
                x + r + 4, y,
                text=label,
                anchor=tk.W,
                font=("Arial", 8, "bold"),
                fill=text_fill,
                tags="traffic_blip",
            )

    def _icao_from_current_airport(self) -> str:
        ap = self.current_airport or ""
        if " - " in ap:
            return ap.split(" - ")[0].strip().upper() or "XXXX"
        return "XXXX"

    def _path_graph(self) -> AirportPathGraph:
        icao = self._icao_from_current_airport()
        if self._path_graph_obj is None or self._path_graph_cached_icao != icao:
            self._path_graph_obj = AirportPathGraph.load_for_icao(
                icao, self._get_data_directory()
            )
            self._path_graph_cached_icao = icao
        return self._path_graph_obj

    def _setup_path_editor_toolbar(self, parent: ttk.Frame) -> None:
        """Toolbar for placing runway / taxiway / gate nodes and linking edges on the diagram."""
        edit = ttk.LabelFrame(
            parent,
            text="Path graph (click diagram — aircraft can use [path:…] locations)",
            padding=4,
        )
        edit.pack(fill=tk.X)
        row1 = ttk.Frame(edit)
        row1.pack(fill=tk.X)
        ttk.Label(row1, text="Mode:").pack(side=tk.LEFT, padx=(0, 4))
        modes = [
            ("off", "View"),
            ("runway", "Runway node"),
            ("taxiway", "Taxiway node"),
            ("holding", "Holding (short of rwy)"),
            ("gate", "Gate node"),
            ("link", "Link nodes"),
        ]
        for val, txt in modes:
            ttk.Radiobutton(
                row1,
                text=txt,
                value=val,
                variable=self.path_edit_mode_var,
                command=self._on_path_mode_changed,
            ).pack(side=tk.LEFT, padx=2)
        row2 = ttk.Frame(edit)
        row2.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(row2, text="Label:").pack(side=tk.LEFT)
        ttk.Entry(row2, textvariable=self.path_node_label_var, width=16).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(row2, text="Undo node", command=self._path_undo_node).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(row2, text="Clear graph", command=self._path_clear_graph).pack(
            side=tk.LEFT, padx=4
        )
        ttk.Button(row2, text="Save", command=self._path_save_graph).pack(side=tk.LEFT, padx=4)
        ttk.Checkbutton(
            row2,
            text="Show airport schematic",
            variable=self.path_show_schematic_var,
            command=self._redraw_all_airport_canvases,
        ).pack(side=tk.LEFT, padx=(12, 0))
        ttk.Label(
            edit,
            text="LMB: place or link (A then B)  •  RMB: delete nearest node",
            font=("Arial", 8),
            foreground="#555",
        ).pack(anchor=tk.W, pady=(2, 0))

        sum_lf = ttk.LabelFrame(
            edit, text="Connectivity — what links to what", padding=2
        )
        sum_lf.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.path_connectivity_text = scrolledtext.ScrolledText(
            sum_lf,
            height=6,
            wrap=tk.WORD,
            font=("Consolas", 9),
            state=tk.DISABLED,
            background="#f8f9fa",
        )
        self.path_connectivity_text.pack(fill=tk.BOTH, expand=True)

    def _refresh_path_connectivity_display(self) -> None:
        if not hasattr(self, "path_connectivity_text"):
            return
        tb = self.path_connectivity_text
        try:
            lines = self._path_graph().connectivity_summary_lines()
        except Exception:
            lines = []
        tb.config(state=tk.NORMAL)
        tb.delete("1.0", tk.END)
        if lines:
            tb.insert(tk.END, "\n".join(lines))
        else:
            tb.insert(
                tk.END,
                "(No path nodes yet — add nodes with Runway/Taxiway/Gate mode, "
                "then use Link mode to connect them.)",
            )
        tb.config(state=tk.DISABLED)

    def _on_path_mode_changed(self) -> None:
        self._path_link_first = None
        self._redraw_all_airport_canvases()
        mode = self.path_edit_mode_var.get()
        tips = {
            "off": "Path editor off (view only)",
            "runway": "Left-click diagram to add a runway node",
            "taxiway": "Left-click diagram to add a taxiway node",
            "gate": "Left-click diagram to add a gate / stand node",
            "holding": "Left-click to add a hold-short point (link to taxi + runway)",
            "link": "Left-click node A, then node B to add a taxi segment",
        }
        self.status_bar.config(text=f"Status: {tips.get(mode, '')}")

    def _path_canvas_widgets(self):
        w = []
        if getattr(self, "airport_canvas", None) is not None:
            w.append(self.airport_canvas)
        if getattr(self, "ground_canvas", None) is not None:
            w.append(self.ground_canvas)
        return w

    def _on_path_canvas_click(self, event: tk.Event) -> None:
        if event.widget not in self._path_canvas_widgets():
            return
        mode = self.path_edit_mode_var.get()
        if mode == "off":
            return
        w, h = event.widget.winfo_width(), event.widget.winfo_height()
        if w <= 1 or h <= 1:
            return
        nx, ny = event.x / w, event.y / h
        g = self._path_graph()
        if mode == "link":
            hit = g.find_node_at_normalized(nx, ny)
            if not hit:
                self._path_link_first = None
                self._redraw_all_airport_canvases()
                self.status_bar.config(text="Status: Link cancelled (no node here)")
                return
            if self._path_link_first is None:
                self._path_link_first = hit
                self._redraw_all_airport_canvases()
                self.status_bar.config(text="Status: Link — pick second node")
                return
            if self._path_link_first == hit:
                self._path_link_first = None
                self._redraw_all_airport_canvases()
                self.status_bar.config(text="Status: Link cancelled (same node)")
                return
            if g.add_edge(self._path_link_first, hit):
                self.status_bar.config(text="Status: Path segment added")
            else:
                self.status_bar.config(text="Status: Segment already exists")
            self._path_link_first = None
            self._redraw_all_airport_canvases()
            return
        kind = mode
        if kind not in ("runway", "taxiway", "gate", "holding"):
            return
        lbl = self.path_node_label_var.get().strip()
        g.add_node(kind, nx, ny, lbl)
        self.path_node_label_var.set("")
        self._redraw_all_airport_canvases()
        self.status_bar.config(text=f"Status: Added {kind} node")

    def _on_path_canvas_right_click(self, event: tk.Event) -> None:
        if event.widget not in self._path_canvas_widgets():
            return
        if self.path_edit_mode_var.get() == "off":
            return
        w, h = event.widget.winfo_width(), event.widget.winfo_height()
        if w <= 1 or h <= 1:
            return
        nx, ny = event.x / w, event.y / h
        g = self._path_graph()
        hit = g.find_node_at_normalized(nx, ny)
        if hit:
            g.remove_node(hit)
            if self._path_link_first == hit:
                self._path_link_first = None
            self._redraw_all_airport_canvases()
            self.status_bar.config(text="Status: Node removed")

    def _path_undo_node(self) -> None:
        g = self._path_graph()
        if g.pop_last_node():
            self._redraw_all_airport_canvases()
            self.status_bar.config(text="Status: Removed last placed node")
        else:
            self.status_bar.config(text="Status: Nothing to undo")

    def _path_clear_graph(self) -> None:
        if not messagebox.askyesno("Clear path graph", "Remove all nodes and edges for this airport?"):
            return
        g = self._path_graph()
        g.nodes.clear()
        g.edges.clear()
        self._path_link_first = None
        self._redraw_all_airport_canvases()
        self.status_bar.config(text="Status: Path graph cleared (not saved yet)")

    def _path_save_graph(self) -> None:
        path = self._path_graph().save(self._get_data_directory())
        self.status_bar.config(text=f"Status: Path graph saved to {path}")

    @staticmethod
    def _path_edge_strip_coords(
        x1: float, y1: float, x2: float, y2: float, half_width: float
    ) -> Optional[tuple]:
        """Quad coords for a strip along (x1,y1)-(x2,y2), perpendicular width 2*half_width."""
        dx, dy = x2 - x1, y2 - y1
        L = math.hypot(dx, dy)
        if L < 1.0:
            return None
        px = (-dy / L) * half_width
        py = (dx / L) * half_width
        return (
            x1 + px,
            y1 + py,
            x2 + px,
            y2 + py,
            x2 - px,
            y2 - py,
            x1 - px,
            y1 - py,
        )

    def _draw_path_graph_overlay(self, canvas: tk.Canvas) -> None:
        """Draw user-defined nodes and edges on top of the schematic diagram."""
        try:
            g = self._path_graph()
        except Exception:
            return
        w, h = canvas.winfo_width(), canvas.winfo_height()
        if w <= 1 or h <= 1:
            return
        t = DEFAULT_DIAGRAM_THEME
        colors = {
            "runway": t.path_node_runway,
            "taxiway": t.path_node_taxiway,
            "gate": t.path_node_gate,
            "holding": t.path_node_holding,
        }
        scale = min(w, h)
        hw_runway = max(10.0, scale * 0.02)
        hw_taxi = max(5.0, scale * 0.009)
        for e in g.edges:
            na, nb = g.node_by_id(e.get("a", "")), g.node_by_id(e.get("b", ""))
            if not na or not nb:
                continue
            x1, y1 = float(na["nx"]) * w, float(na["ny"]) * h
            x2, y2 = float(nb["nx"]) * w, float(nb["ny"]) * h
            ta = str(na.get("type", "")).lower()
            tb = str(nb.get("type", "")).lower()
            if ta == "runway" and tb == "runway":
                coords = self._path_edge_strip_coords(x1, y1, x2, y2, hw_runway)
                if coords:
                    canvas.create_polygon(
                        *coords,
                        fill=t.path_runway_strip_fill,
                        outline=t.path_runway_strip_outline,
                        width=2,
                        tags="pathgraph",
                    )
            elif ta == "taxiway" and tb == "taxiway":
                coords = self._path_edge_strip_coords(x1, y1, x2, y2, hw_taxi)
                if coords:
                    canvas.create_polygon(
                        *coords,
                        fill=t.path_taxi_strip_fill,
                        outline=t.path_taxi_strip_outline,
                        width=2,
                        tags="pathgraph",
                    )
            else:
                canvas.create_line(
                    x1, y1, x2, y2,
                    fill=t.path_other_edge,
                    width=3,
                    tags="pathgraph",
                )
        r = max(7, int(scale * 0.012))
        for n in g.nodes:
            cx, cy = float(n["nx"]) * w, float(n["ny"]) * h
            col = colors.get(str(n.get("type", "")), t.path_node_default)
            canvas.create_oval(
                cx - r, cy - r, cx + r, cy + r,
                fill=col,
                outline=t.path_node_outline,
                width=2,
                tags="pathgraph",
            )
            if self._path_link_first and n.get("id") == self._path_link_first:
                canvas.create_oval(
                    cx - r - 5, cy - r - 5, cx + r + 5, cy + r + 5,
                    outline=t.path_link_highlight,
                    width=2,
                    tags="pathgraph",
                )
            canvas.create_text(
                cx,
                cy - r - 12,
                text=g.visible_label(n),
                font=("Arial", 8, "bold"),
                fill=t.path_node_outline,
                tags="pathgraph",
            )

    def _draw_runway(self, canvas, c_width, r_y, r_length, r_width, rwy_name, theme):
        """Draws the runway with more details."""
        x_start = (c_width - r_length) / 2
        x_end = x_start + r_length
        margin = max(50.0, r_length * 0.06)
        key_w = max(3.0, r_width * 0.12)
        key_gap = max(3.0, r_width * 0.08)
        dash = runway_centerline_dash(r_length)

        canvas.create_rectangle(
            x_start, r_y - r_width / 2, x_end, r_y + r_width / 2,
            fill=theme.runway_fill, outline=theme.runway_outline, width=2, tags="runway"
        )
        canvas.create_line(
            x_start + margin, r_y, x_end - margin, r_y,
            fill=theme.runway_centerline, width=2, dash=dash, tags="runway_marking"
        )

        for i in range(5):
            offset = i * (key_w + key_gap)
            canvas.create_rectangle(
                x_start + 15 + offset, r_y - r_width / 3,
                x_start + 15 + offset + key_w, r_y + r_width / 3,
                fill=theme.runway_centerline, outline="",
            )
            canvas.create_rectangle(
                x_end - 15 - offset - key_w, r_y - r_width / 3,
                x_end - 15 - offset, r_y + r_width / 3,
                fill=theme.runway_centerline, outline="",
            )

        rwy_labels = rwy_name.split('/')
        canvas.create_text(
            x_start + 45, r_y, text=rwy_labels[0], fill=theme.runway_centerline,
            font=("Consolas", 14, "bold"), anchor="center"
        )
        if len(rwy_labels) > 1:
            canvas.create_text(
                x_end - 45, r_y, text=rwy_labels[1], fill=theme.runway_centerline,
                font=("Consolas", 14, "bold"), anchor="center"
            )

    def _taxi_segment_h(self, canvas, x1, x2, y, pavement_w, theme):
        canvas.create_line(
            x1, y, x2, y,
            fill=theme.taxiway_pavement, width=pavement_w, capstyle=tk.ROUND, tags="taxiway",
        )
        canvas.create_line(
            x1, y, x2, y,
            fill=theme.taxiway_centerline, width=2, dash=(14, 10), tags="taxiway_marking",
        )

    def _taxi_segment_v(self, canvas, x, y1, y2, pavement_w, theme):
        canvas.create_line(
            x, y1, x, y2,
            fill=theme.taxiway_pavement, width=pavement_w, capstyle=tk.ROUND, tags="taxiway",
        )
        canvas.create_line(
            x, y1, x, y2,
            fill=theme.taxiway_centerline, width=2, dash=(14, 10), tags="taxiway_marking",
        )

    def _draw_taxiways(
        self,
        canvas,
        c_width,
        r_length,
        runway_ys,
        north_tw_y,
        taxiways,
        runway_width,
        icao: str,
        theme,
        tw_main: int,
        tw_conn: int,
    ):
        """Draw taxi schematic: single-runway uses named connectors; multi-runway avoids fake TWY IDs."""
        x_start = (c_width - r_length) / 2
        x_end = x_start + r_length
        lbl_fill = theme.taxiway_edge_line

        if len(runway_ys) <= 1:
            r_y = runway_ys[0]
            t_y = north_tw_y
            self._taxi_segment_h(canvas, x_start, x_end, t_y, tw_main, theme)
            main_lbl = (taxiways[0] if taxiways else "A")[:14]
            canvas.create_text(
                x_start - 12, t_y, text=main_lbl,
                fill=lbl_fill, font=("Arial", 9, "bold"), anchor="e",
            )
            num_connectors = 5
            pad = (taxiways[1:] + [""] * (num_connectors - 1))[: num_connectors - 1]
            for i in range(1, num_connectors):
                conn_x = x_start + (r_length / num_connectors) * i
                self._taxi_segment_v(
                    canvas, conn_x, t_y, r_y - runway_width / 2, tw_conn, theme,
                )
                lbl = pad[i - 1]
                if lbl:
                    canvas.create_text(
                        conn_x, t_y + 14, text=str(lbl)[:10],
                        fill=lbl_fill, font=("Arial", 8, "bold"),
                    )
            return

        southmost = max(runway_ys)
        south_tw_y = southmost + runway_width / 2 + 28

        def band(y):
            self._taxi_segment_h(canvas, x_start, x_end, y, tw_main, theme)

        band(north_tw_y)
        band(south_tw_y)

        north_caption = "Parallel taxi (north)"
        south_caption = "Parallel taxi (south)"
        if icao == "WSSS":
            north_caption = "Terminal / north parallel (schematic)"
            south_caption = "South parallel (schematic)"

        canvas.create_text(
            x_start - 8, north_tw_y, text=north_caption,
            fill=lbl_fill, font=("Arial", 8, "bold"), anchor="e",
        )
        canvas.create_text(
            x_start - 8, south_tw_y, text=south_caption,
            fill=lbl_fill, font=("Arial", 8, "bold"), anchor="e",
        )

        corridor_xs = [
            x_start + r_length * 0.18,
            x_start + r_length * 0.82,
        ]
        for cx in corridor_xs:
            self._taxi_segment_v(canvas, cx, north_tw_y, south_tw_y, tw_conn, theme)

        stub_w = max(4, tw_conn // 2)
        for cx in corridor_xs:
            for i in range(len(runway_ys) - 1):
                y_hi = runway_ys[i]
                y_lo = runway_ys[i + 1]
                mid = (y_hi + y_lo) / 2
                canvas.create_line(
                    cx - 14, mid, cx + 14, mid,
                    fill=theme.taxiway_stub, width=stub_w, capstyle=tk.ROUND, tags="taxiway",
                )
                canvas.create_line(
                    cx - 14, mid, cx + 14, mid,
                    fill=theme.taxiway_centerline, width=1, dash=(6, 4), tags="taxiway_marking",
                )

        note = "Taxi routes illustrative — use AIP / airport chart for real TWYs"
        canvas.create_text(
            (x_start + x_end) / 2,
            north_tw_y - 14,
            text=note,
            fill=theme.text_note,
            font=("Arial", 7, "italic"),
        )

    def _draw_aprons_and_gates(self, canvas, c_width, top_y, bottom_y, gates, theme):
        """Lays out aprons horizontally to avoid overlap."""
        # Classify gates
        main_bays = sorted([g for g in gates if g.isdigit() or g.endswith(('R', 'L', 'C'))])
        remote_bays = sorted([g for g in gates if g.startswith('R') and g[1:].isdigit()])
        ga_bays = sorted([g for g in gates if g.startswith(('G', 'H'))])

        # Define horizontal sections for each apron, with reduced width for margins
        sections = []
        if ga_bays: sections.append({"name": "GA Parking", "bays": ga_bays, "width_ratio": 0.22})
        if main_bays: sections.append({"name": "Main Terminal", "bays": main_bays, "width_ratio": 0.46})
        if remote_bays: sections.append({"name": "Remote Bays", "bays": remote_bays, "width_ratio": 0.22})
        
        total_ratio = sum(s['width_ratio'] for s in sections)
        
        margin = (c_width - (c_width * total_ratio)) / 2
        current_x = margin

        for section in sections:
            section_width = c_width * section['width_ratio']
            self._draw_apron_section(
                canvas,
                section["name"],
                section["bays"],
                current_x,
                top_y,
                section_width,
                top_y - bottom_y,
                theme,
            )
            current_x += section_width

    def _draw_diagram_labels(self, canvas, c_width, c_height, airport_data, theme):
        """Draws the airport name and other diagram labels."""
        airport_name = airport_data.get("name", "Unknown Airport")
        canvas.create_text(
            c_width / 2,
            c_height * 0.06,
            text=airport_name,
            font=("Arial", 18, "bold"),
            fill=theme.text_title,
        )
        icao = (airport_data.get("icao") or "").upper()
        if icao == "WSSS":
            canvas.create_text(
                c_width / 2,
                c_height * 0.10,
                text="Three parallel runways (02L/20R, 02C/20C, 02R/20L) — schematic per ICAO layout",
                font=("Arial", 9),
                fill=theme.text_subtitle,
            )
        canvas.create_text(
            c_width - 10,
            c_height - 10,
            text="Diagram not to scale",
            anchor="se",
            font=("Arial", 8, "italic"),
            fill=theme.text_diagram_footer,
        )

    def _draw_no_diagram_message(self, canvas, width, height):
        """Draw a message when no diagram is available."""
        canvas.create_text(
            width / 2, height / 2,
            text="No Airport Diagram Available for this airport.",
            font=("Arial", 14, "italic"),
            fill="#888888"
        )

    def _draw_apron_section(self, canvas, name, gates, x_pos, y_pos, width, height, theme):
        """Draws a single apron section with gates, updated for new layout."""
        canvas.create_rectangle(
            x_pos, y_pos - height, x_pos + width, y_pos,
            fill=theme.apron_fill, outline=theme.apron_outline, width=2, tags="apron"
        )
        canvas.create_text(
            x_pos + width / 2, y_pos - height + 20, text=name,
            font=("Arial", 11, "bold"), fill=theme.apron_label,
        )
        
        # Draw gates
        num_gates = len(gates)
        if num_gates == 0: return

        gate_spacing = width / (num_gates + 1)
        gate_y_start = y_pos - height + 40
        gate_y_end = y_pos - 15

        for i, gate in enumerate(gates):
            gate_x = x_pos + gate_spacing * (i + 1)
            # Parking line
            canvas.create_line(
                gate_x,
                gate_y_start,
                gate_x,
                gate_y_end,
                fill=theme.taxiway_centerline,
                width=1.5,
                dash=(4, 4),
            )
            # Gate label
            canvas.create_text(gate_x, gate_y_end + 8, text=gate, font=("Arial", 9, "bold"), anchor="n")

    def issue_taxi_clearance(self):
        """Opens a dialog to issue a taxi clearance."""
        selected_item = self.ground_aircraft_tree.selection()
        if not selected_item:
            messagebox.showinfo("Selection Required", "Please select an aircraft.")
            return

        aircraft_info = self.ground_aircraft_tree.item(selected_item[0], 'values')
        callsign = aircraft_info[0]

        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Taxi Clearance for {callsign}")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Taxi to:").grid(row=0, column=0, sticky=tk.W, pady=5)
        runway_var = tk.StringVar()
        runways = self.airports.get(self.current_airport, {}).get("runways", [])
        runway_combo = ttk.Combobox(frame, textvariable=runway_var, values=runways, width=25)
        runway_combo.grid(row=0, column=1, sticky=tk.EW, pady=5)
        if runways:
            runway_combo.current(0)
            
        ttk.Label(frame, text="Via Taxiway(s):").grid(row=1, column=0, sticky=tk.W, pady=5)
        route_var = tk.StringVar()
        route_entry = ttk.Entry(frame, textvariable=route_var, width=27)
        route_entry.grid(row=1, column=1, sticky=tk.EW, pady=5)
        
        def issue():
            runway = runway_var.get()
            route = route_var.get()
            if not runway or not route:
                messagebox.showwarning("Missing Info", "Please specify runway and taxi route.")
                return

            instruction = f"{callsign}, taxi to runway {runway} via taxiway(s) {route}."
            self.log_communication(self.ground_instructions, "GROUND", instruction)
            
            # Update aircraft status
            new_status = f"Taxiing to Runway {runway}"
            parts = list(aircraft_info)
            parts[2] = route # Update Location
            parts[3] = new_status # Update Status
            self.ground_aircraft_tree.item(selected_item[0], values=tuple(parts))

            self.status_bar.config(text=f"Status: Taxi clearance issued to {callsign}")
            dialog.destroy()

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Issue Clearance", command=issue).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def issue_hold_instruction(self):
        """Opens a dialog to issue a hold instruction."""
        selected_item = self.ground_aircraft_tree.selection()
        if not selected_item:
            messagebox.showinfo("Selection Required", "Please select an aircraft.")
            return

        aircraft_info = self.ground_aircraft_tree.item(selected_item[0], 'values')
        callsign = aircraft_info[0]

        # Create dialog
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Hold Instruction for {callsign}")
        dialog.geometry("400x150")
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.Frame(dialog, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Hold short of:").grid(row=0, column=0, sticky=tk.W, pady=5)
        hold_point_var = tk.StringVar()
        hold_point_entry = ttk.Entry(frame, textvariable=hold_point_var, width=27)
        hold_point_entry.grid(row=0, column=1, sticky=tk.EW, pady=5)

        def issue():
            hold_point = hold_point_var.get()
            if not hold_point:
                messagebox.showwarning("Missing Info", "Please specify the holding point.")
                return

            instruction = f"{callsign}, hold short of {hold_point}."
            self.log_communication(self.ground_instructions, "GROUND", instruction)

            # Update aircraft status
            new_status = f"Holding short of {hold_point}"
            parts = list(aircraft_info)
            parts[3] = new_status # Update Status
            self.ground_aircraft_tree.item(selected_item[0], values=tuple(parts))

            self.status_bar.config(text=f"Status: Hold instruction issued to {callsign}")
            dialog.destroy()

        button_frame = ttk.Frame(frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=10)
        ttk.Button(button_frame, text="Issue Instruction", command=issue).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side=tk.LEFT, padx=5)

    def transfer_to_ground(self):
        """Transfer selected arrival aircraft to ground control"""
        selection = self.arrival_listbox.curselection()
        
        if not selection:
            messagebox.showinfo("Information", "Please select an arrival aircraft")
            return
        
        index = selection[0]
        aircraft_info = self.arrival_listbox.get(index)
        
        # Use regex to reliably extract the callsign
        match = re.match(r"^([A-Z0-9]+)", aircraft_info)
        if not match:
            messagebox.showerror("Error", "Could not extract callsign from selected aircraft.")
            return
        callsign = match.group(1)
        
        if not hasattr(self, "aircraft_data") or "arrival" not in self.aircraft_data:
            messagebox.showerror("Error", "Aircraft data not found")
            return
        
        if callsign not in self.aircraft_data["arrival"]:
            messagebox.showerror("Error", f"Aircraft {callsign} not found in arrival data")
            return
        
        # Get aircraft data
        aircraft_data = self.aircraft_data["arrival"][callsign]
        aircraft_type = aircraft_data["type"]
        
        # Remove from arrival listbox
        self.arrival_listbox.delete(index)
        
        # Add placeholder message if queue is now empty
        if self.arrival_listbox.size() == 0:
            placeholder = "No aircraft in arrival queue"
            self.arrival_listbox.insert(tk.END, placeholder)
            self.arrival_listbox.itemconfig(0, {'fg': 'gray'})
        
        # Add to ground control list
        if hasattr(self, "ground_aircraft_list"):
            display_text = f"{callsign} - {aircraft_type} - Taxiway A - Taxiing to Gate"
            self.ground_aircraft_list.insert(tk.END, display_text)
        
        # Remove from data structure
        del self.aircraft_data["arrival"][callsign]
        
        # Update status bar
        self.status_bar.config(text=f"Status: {callsign} transferred to Ground Control")

    def _selected_ground_callsign(self) -> Optional[str]:
        if not hasattr(self, "ground_aircraft_tree"):
            return None
        sel = self.ground_aircraft_tree.selection()
        if not sel:
            return None
        vals = self.ground_aircraft_tree.item(sel[0], "values")
        return str(vals[0]) if vals else None

    def _message_callsign_prefix(self, message: str) -> Optional[str]:
        if not message or "," not in message:
            m = re.match(r"^(\S+)", message.strip())
            return m.group(1) if m else None
        return message.split(",", 1)[0].strip()

    def _update_atc_traffic_strip_context(self, message: str, sender: str) -> None:
        """Track last ATC/GROUND to selected callsign, and last pilot line in log (simulated / practice)."""
        cs = self._selected_ground_callsign()
        if not cs or not message:
            return
        if sender == "PILOT":
            self._atc_strip_last_pilot_log_line = message.strip()
            return
        prefix = self._message_callsign_prefix(message)
        if not prefix or prefix.upper() != cs.upper():
            return
        if sender in ("ATC", "GROUND"):
            self._atc_strip_last_ground_tx = message.strip()

    def _refresh_atc_traffic_strip(self) -> None:
        if not hasattr(self, "atc_traffic_strip_label"):
            return
        cs = self._selected_ground_callsign()
        if not cs:
            self.atc_traffic_strip_label.config(
                text="Select an aircraft in the list to see its list state and recent comms to that callsign."
            )
            if hasattr(self, "atc_diagram_traffic_hint"):
                self.atc_diagram_traffic_hint.config(text="")
            return
        sel = self.ground_aircraft_tree.selection()
        if not sel:
            return
        vals = self.ground_aircraft_tree.item(sel[0], "values")
        loc = str(vals[2]) if len(vals) > 2 else ""
        st = str(vals[3]) if len(vals) > 3 else ""
        summary = build_atc_traffic_strip_line(
            cs,
            loc,
            st,
            self._atc_strip_last_ground_tx or "",
            self._atc_strip_last_pilot_log_line or "",
        )
        self.atc_traffic_strip_label.config(text=summary)
        if hasattr(self, "atc_diagram_traffic_hint"):
            short = summary if len(summary) <= 140 else summary[:137] + "…"
            self.atc_diagram_traffic_hint.config(text=short)

    def log_communication(self, text_widget, sender, message, clear=False):
        """Log communication messages to the specified text widget"""
        logger.debug("Logging communication - %s: %s", sender, message)
        if clear:
            text_widget.config(state=tk.NORMAL)
            text_widget.delete(1.0, tk.END)
            text_widget.config(state=tk.DISABLED)
        
        # Get current time
        current_time = time.strftime("%H:%M:%S")
        
        # Format the message with better styling
        if sender == "PILOT":
            formatted_message = f"[{current_time}] ✈️ PILOT: {message}\n"
        elif sender == "ATC":
            formatted_message = f"[{current_time}] 🎯 ATC: {message}\n"
        else:
            formatted_message = f"[{current_time}] {sender}: {message}\n"
        
        # Add to the text widget
        text_widget.config(state=tk.NORMAL)
        text_widget.insert(tk.END, formatted_message)
        text_widget.see(tk.END)  # Scroll to the end
        text_widget.config(state=tk.DISABLED)

        gi = getattr(self, "ground_instructions", None)
        if gi is not None and text_widget is gi:
            if sender == "PILOT":
                self._update_atc_traffic_strip_context(message, sender)
            elif sender in ("ATC", "GROUND") and "standby" not in message.lower():
                self._update_atc_traffic_strip_context(message, sender)
            self._refresh_atc_traffic_strip()

    def _sort_treeview_column(self, tv, col, reverse):
        """Sort a treeview column when the heading is clicked."""
        l = [(tv.set(k, col), k) for k in tv.get_children('')]
        
        # Try to sort numerically if possible
        try:
            l.sort(key=lambda t: float(t[0]), reverse=reverse)
        except ValueError:
            l.sort(key=lambda t: t[0], reverse=reverse)

        # Rearrange items in sorted positions
        for index, (val, k) in enumerate(l):
            tv.move(k, '', index)

        # Reverse sort next time
        tv.heading(col, command=lambda: self._sort_treeview_column(tv, col, not reverse))
    
    # AI Response Methods
    def open_ai_settings(self):
        """Open AI settings dialog"""
        from views.ai_settings_dialog import AISettingsDialog
        
        def on_settings_save(new_config):
            """Handle settings save"""
            self.config.update(new_config)
            self.ai_handler.update_config(new_config)
            self.status_bar.config(text="Status: AI settings updated")
        
        AISettingsDialog(self.root, self.config, on_settings_save)
    
    def send_ai_response(self, event=None):
        """Send AI-generated response"""
        pilot_message = self.ai_input_var.get().strip()
        if not pilot_message:
            messagebox.showwarning("Input Required", "Please enter a pilot message.")
            return
        
        # Get selected aircraft info
        selected_item = self.ground_aircraft_tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Required", "Please select an aircraft first.")
            return
        
        aircraft_info = self.ground_aircraft_tree.item(selected_item[0], 'values')
        callsign = aircraft_info[0]
        aircraft_type = aircraft_info[1]
        location = aircraft_info[2]
        status = aircraft_info[3]
        
        # Prepare aircraft info for AI
        aircraft_data = {
            'callsign': callsign,
            'aircraft_type': aircraft_type,
            'location': location,
            'status': status,
            'squawk_code': '1200'  # Default squawk
        }
        
        # Get airport info
        airport_data = self.airports.get(self.current_airport, {})
        airport_data["traffic"] = list(self.active_aircraft.values()) if self.active_aircraft else []
        response_type = self._infer_response_type(pilot_message)
        
        # Log the pilot message first
        self.log_communication(self.ground_instructions, "PILOT", pilot_message)
        
        # Show processing indicator and disable transmit while AI is generating
        self.ai_processing_label.config(text="🤖 AI Processing...", foreground="orange")
        self.send_ai_response_btn.config(state=tk.DISABLED)
        self.ai_input_entry.config(state=tk.DISABLED)
        
        # Add standby message that will be replaced by AI response
        self.log_communication(self.ground_instructions, "ATC", f"{callsign}, roger, standby...")
        
        # Store the standby line index for replacement (normalize line endings for consistency)
        content = self.ground_instructions.get(1.0, tk.END).replace("\r\n", "\n").replace("\r", "\n")
        lines = content.splitlines()
        self.standby_message_index = len(lines) - 1 if lines else 0
        
        # Generate AI response asynchronously (pass standby index for in-place replacement)
        response = self.ai_handler.generate_atc_response(
            pilot_message=pilot_message,
            aircraft_info=aircraft_data,
            airport_info=airport_data,
            response_type=response_type,
            standby_index=self.standby_message_index,
        )
        
        # Clear input
        self.ai_input_var.set("")
        
        # Update status
        self.status_bar.config(text=f"Status: AI response generated for {callsign}")
        self._refresh_operational_insights()

    def _infer_response_type(self, pilot_message):
        """Infer response type from pilot intent for better AI prompting."""
        msg = pilot_message.lower()
        if "pushback" in msg or "taxi" in msg:
            return "taxi"
        if "takeoff" in msg or "departure" in msg:
            return "takeoff"
        if "landing" in msg or "final" in msg or "approach" in msg:
            return "landing"
        if "hold" in msg:
            return "hold"
        return "general"
    
    def clear_ai_input(self):
        """Clear AI input field"""
        self.ai_input_var.set("")
    
    def clear_communication_log(self):
        """Clear the communication log"""
        self.ground_instructions.config(state=tk.NORMAL)
        self.ground_instructions.delete(1.0, tk.END)
        self.ground_instructions.config(state=tk.DISABLED)
        self._atc_strip_last_ground_tx = ""
        self._atc_strip_last_pilot_log_line = ""
        if hasattr(self, "ai_handler") and self.ai_handler:
            self.ai_handler.clear_history()
        self._refresh_atc_traffic_strip()
        self.status_bar.config(text="Status: Communication log cleared")
    
    def show_example_messages(self):
        """Show example pilot messages"""
        examples = [
            "Request taxi clearance to runway 27",
            "Ready for departure",
            "Request pushback",
            "Holding short of runway 27",
            "Request landing clearance",
            "Contact ground for taxi instructions",
            "Request frequency change",
            "Standing by",
            "Request takeoff clearance",
            "Ready for takeoff"
        ]
        
        # Create a simple dialog with examples
        dialog = tk.Toplevel(self.root)
        dialog.title("Example Pilot Messages")
        dialog.geometry("400x300")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (400 // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (300 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Title
        ttk.Label(dialog, text="Example Pilot Messages", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Instructions
        ttk.Label(dialog, text="Click on any message to copy it to the input field:").pack(pady=(0, 10))
        
        # Create frame for examples
        examples_frame = ttk.Frame(dialog)
        examples_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)
        
        # Add examples as clickable buttons
        for example in examples:
            btn = ttk.Button(
                examples_frame,
                text=example,
                command=lambda msg=example: self.copy_example_message(msg, dialog)
            )
            btn.pack(fill=tk.X, pady=2)
        
        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    def copy_example_message(self, message, dialog):
        """Copy example message to input field"""
        self.ai_input_var.set(message)
        dialog.destroy()
        self.ai_input_entry.focus_set()
        self.status_bar.config(text="Status: Example message copied to input field")
    
    def save_communication_log(self):
        """Save communication log to file"""
        try:
            from tkinter import filedialog
            import os
            
            # Get the log content
            log_content = self.ground_instructions.get(1.0, tk.END)
            
            if not log_content.strip():
                messagebox.showwarning("Empty Log", "No communication log to save.")
                return
            
            # Create default filename with timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            default_filename = f"atc_communications_{timestamp}.txt"
            
            # Ask user for save location
            filename = filedialog.asksaveasfilename(
                title="Save Communication Log",
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                initialname=default_filename
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(f"Air Traffic Control Communication Log\n")
                    f.write(f"Airport: {self.current_airport}\n")
                    f.write(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 50 + "\n\n")
                    f.write(log_content)
                
                messagebox.showinfo("Success", f"Communication log saved to:\n{filename}")
                self.status_bar.config(text="Status: Communication log saved")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to save communication log:\n{str(e)}")
            self.status_bar.config(text="Status: Error saving communication log")
    
    def show_ai_help(self):
        """Show AI help dialog"""
        help_text = """🤖 AI-Powered ATC Responses

How to use:
1. Select an aircraft from the list above
2. Type a pilot message in the input field
3. Press Enter or click "Send AI Response"
4. The AI will generate an appropriate ATC response

Keyboard shortcuts:
• Enter: Send AI response
• Ctrl+Enter: Send AI response (alternative)

Features:
• Real-time AI processing with status indicator
• Professional aviation phraseology
• Context-aware responses based on aircraft and airport
• Communication log with timestamps
• Save logs for record keeping

Tips:
• Use the "Examples" button to see sample messages
• Clear the log when starting a new session
• Save important communications for reference

The AI considers:
• Aircraft type and callsign
• Current location and status
• Airport configuration
• Weather conditions
• Recent communication history"""
        
        # Create help dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("AI Help")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        x = self.root.winfo_x() + (self.root.winfo_width() // 2) - (500 // 2)
        y = self.root.winfo_y() + (self.root.winfo_height() // 2) - (400 // 2)
        dialog.geometry(f"+{x}+{y}")
        
        # Create text widget for help content
        help_text_widget = scrolledtext.ScrolledText(
            dialog,
            wrap=tk.WORD,
            font=("Arial", 10),
            background="#f8f9fa",
            state=tk.DISABLED
        )
        help_text_widget.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Insert help text
        help_text_widget.config(state=tk.NORMAL)
        help_text_widget.insert(tk.END, help_text)
        help_text_widget.config(state=tk.DISABLED)
        
        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(pady=10)
    
    def on_ai_response_generated(self, response, standby_index=None, request_id=None):
        """Handle AI response generation callback (standby_index for in-place replacement)."""
        if request_id is not None and request_id != self.ai_handler.last_dispatch_seq:
            return

        try:
            self.pending_ai_response = response
            self.pending_standby_index = standby_index
            self.root.after(0, self._process_pending_ai_response)
        except Exception:
            self._update_ui_with_response(response, standby_index=standby_index)
    
    def test_callback(self):
        """Test the callback mechanism"""
        logger.debug("Testing callback mechanism...")
        test_response = "Test ATC response from callback"
        self.on_ai_response_generated(test_response)
    
    def _process_pending_ai_response(self):
        """Process pending AI response on main thread"""
        if hasattr(self, 'pending_ai_response'):
            response = self.pending_ai_response
            standby_index = getattr(self, 'pending_standby_index', None)
            delattr(self, 'pending_ai_response')
            if hasattr(self, 'pending_standby_index'):
                delattr(self, 'pending_standby_index')
            self._update_ui_with_response(response, standby_index=standby_index)
    

    
    def _update_ui_with_response(self, response, standby_index=None):
        """Update UI with AI response on the main thread"""
        self.replace_last_atc_message(response, standby_index=standby_index)
        self.ai_processing_label.config(text="🤖 AI Ready", foreground="green")
        self.status_bar.config(text="Status: AI response completed")
        # Re-enable transmit now that AI has finished
        self.send_ai_response_btn.config(state=tk.NORMAL)
        self.ai_input_entry.config(state=tk.NORMAL)
    
    def _is_atc_line(self, line: str) -> bool:
        """Return True if the line looks like an ATC log line (robust to encoding)."""
        return "ATC:" in line

    def replace_last_atc_message(self, new_message, standby_index=None):
        """Replace the standby/placeholder ATC message with the actual AI response.
        Uses standby_index when provided (for correct replacement with out-of-order
        callbacks); otherwise finds the last ATC line. Normalizes line endings for
        Windows. Falls back to appending only if replacement is not possible.
        """
        try:
            current_time = time.strftime("%H:%M:%S")
            formatted_message = f"[{current_time}] 🎯 ATC: {new_message}\n"

            # Get content and normalize line endings (Windows \r\n)
            current_content = self.ground_instructions.get(1.0, tk.END)
            current_content = current_content.replace("\r\n", "\n").replace("\r", "\n")
            lines = current_content.splitlines()

            replace_index = -1
            if standby_index is not None and 0 <= standby_index < len(lines):
                if self._is_atc_line(lines[standby_index]):
                    replace_index = standby_index

            if replace_index == -1:
                # Fallback: find last line that looks like ATC
                for i in range(len(lines) - 1, -1, -1):
                    if self._is_atc_line(lines[i]):
                        replace_index = i
                        break

            if replace_index != -1:
                lines[replace_index] = formatted_message.rstrip("\n")
                new_content = "\n".join(lines) + ("\n" if current_content.endswith("\n") else "")

                self.ground_instructions.config(state=tk.NORMAL)
                self.ground_instructions.delete(1.0, tk.END)
                self.ground_instructions.insert(1.0, new_content)
                self.ground_instructions.config(state=tk.DISABLED)
                self.ground_instructions.see(tk.END)
                self._update_atc_traffic_strip_context(new_message.strip(), "ATC")
                self._refresh_atc_traffic_strip()
            else:
                self.log_communication(self.ground_instructions, "ATC", new_message)

        except Exception:
            self.log_communication(self.ground_instructions, "ATC", new_message)
    
    def generate_ai_atis(self):
        """Generate ATIS using AI"""
        airport_data = self.airports.get(self.current_airport, {})
        
        # Generate AI ATIS
        atis_message = self.ai_handler.generate_atis_message(airport_data)
        
        # Update ATIS display
        if hasattr(self, 'atis_message_text'):
            self.atis_message_text.config(state=tk.NORMAL)
            self.atis_message_text.delete(1.0, tk.END)
            self.atis_message_text.insert(tk.END, atis_message)
            self.atis_message_text.config(state=tk.DISABLED)
        
        self.status_bar.config(text="Status: AI-generated ATIS created")
    
    def update_ai_status_indicator(self):
        """Update the AI status indicator"""
        try:
            if self.ai_handler.is_ai_available():
                self.ai_status_label.config(
                    text="🤖 AI: Available",
                    foreground="green"
                )
            else:
                self.ai_status_label.config(
                    text="🤖 AI: Not Available",
                    foreground="red"
                )
        except Exception as e:
            self.ai_status_label.config(
                text="🤖 AI: Error",
                foreground="orange"
            )
            logger.warning("Error updating AI status: %s", e)