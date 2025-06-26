import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import requests
import random
import math
import re


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
        
        # Enrich airport data with dynamic content
        self.enrich_airport_data()
        
        self.setup_ui()

    def setup_ui(self):
        """Set up the main UI components"""
        # Configure main window
        self.root.title("Air Traffic Control System")
        self.root.geometry("1200x800")
        
        # Create main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create header frame for airport selection and weather
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(side=tk.TOP, fill=tk.X, pady=(0, 10))
        
        # Airport selection
        airport_frame = ttk.Frame(header_frame)
        airport_frame.pack(side=tk.LEFT, fill=tk.Y)
        
        ttk.Label(airport_frame, text="Current Airport:").pack(side=tk.LEFT, padx=(0, 5))
        self.airport_var = tk.StringVar()
        self.airport_combo = ttk.Combobox(
            airport_frame, 
            textvariable=self.airport_var,
            values=list(self.airports.keys()),
            state="readonly",
            width=10
        )
        self.airport_combo.pack(side=tk.LEFT, padx=(0, 5))
        
        # Set the current airport in the combo box
        if list(self.airports.keys()):
            # Find the index of the current airport
            try:
                current_index = list(self.airports.keys()).index(self.current_airport)
                self.airport_combo.current(current_index)
            except ValueError:
                # If current_airport not found, default to first
                self.airport_combo.current(0)
                self.current_airport = list(self.airports.keys())[0]
        
        # Refresh weather button
        self.refresh_weather_button = ttk.Button(
            airport_frame, 
            text="Refresh Weather", 
            command=self.refresh_current_airport_weather
        )
        self.refresh_weather_button.pack(side=tk.LEFT, padx=(5, 0))
        
        # Auto-weather update checkbox
        self.auto_weather_var = tk.BooleanVar(value=False)
        self.auto_weather_check = ttk.Checkbutton(
            airport_frame,
            text="Auto Weather",
            variable=self.auto_weather_var,
            command=self.toggle_auto_weather_updates
        )
        self.auto_weather_check.pack(side=tk.LEFT, padx=(10, 0))
        
        # Initialize weather update timer
        self.auto_weather_update = False
        self.weather_update_interval = 15 * 60 * 1000  # 15 minutes in milliseconds
        self.weather_update_id = None
        
        # Weather display
        self.weather_frame = ttk.LabelFrame(header_frame, text="Current Weather")
        self.weather_frame.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.weather_display = ttk.Label(
            self.weather_frame,
            text="No weather data available",
            font=("Arial", 10)
        )
        self.weather_display.pack(padx=10, pady=5)
        
        # Bind airport selection change
        self.airport_combo.bind("<<ComboboxSelected>>", self.on_airport_change)
        
        # Create main notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        
        # Create status bar
        self.status_bar = ttk.Label(
            self.main_frame, 
            text="Status: Ready",
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        
        # Correct packing order: bottom, top, then fill
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=(5,0))
        
        # Set up controller position tabs
        self.setup_ground_tab()
        self.setup_tower_tab()
        self.setup_approach_tab()
        self.setup_departure_tab()
        self.setup_atis_tab()
        
        # Initialize weather display
        self.update_airport_config()
        self.update_weather_display()

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
        
        self.ground_instructions = scrolledtext.ScrolledText(comm_section, height=4, wrap=tk.WORD, state=tk.DISABLED)
        self.ground_instructions.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # --- Right frame for airport diagram ---
        right_frame = ttk.Frame(ground_paned_window, padding=5)
        ground_paned_window.add(right_frame, weight=1)

        diagram_frame = ttk.LabelFrame(right_frame, text="Airport Diagram")
        diagram_frame.pack(fill=tk.BOTH, expand=True)
        self.airport_canvas = tk.Canvas(diagram_frame, bg="lightgrey")
        self.airport_canvas.pack(fill=tk.BOTH, expand=True)
        self.airport_canvas.bind("<Configure>", lambda event: self.draw_airport_diagram(event.widget))

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
        
        # Check if aircraft is lined up
        if aircraft_data["status"] != "Lined Up":
            message = f"Aircraft {callsign} is not lined up yet. Issue takeoff clearance anyway?"
            if not messagebox.askyesno("Confirm", message):
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
        
        # Update any diagrams or visualizations
        if hasattr(self, "ground_canvas"):
            self.draw_airport_diagram(self.ground_canvas)
            
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
        
        # Update the display with the new airport information
        self.update_airport_config()
        
        # Fetch the weather for the new airport
        self.update_weather_display()

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
                print(f"Error fetching weather: {e}")
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

        # Draw a subtle background gradient
        canvas.create_rectangle(0, 0, canvas_width, canvas_height, fill="#E0E4E8", outline="")
        canvas.create_rectangle(0, canvas_height * 0.6, canvas_width, canvas_height, fill="#D0D5DC", outline="")

        runways = airport_data.get("runways", [])
        taxiways = airport_data.get("taxiways", [])
        gates = airport_data.get("gates", [])

        if not runways:
            self._draw_no_diagram_message(canvas, canvas_width, canvas_height)
            return

        # --- Define layout parameters based on percentages ---
        runway_length = canvas_width * 0.9
        runway_width = 20
        runway_y = canvas_height * 0.88
        main_taxiway_y = runway_y - 55
        apron_top_y = main_taxiway_y - 15
        apron_bottom_y = canvas_height * 0.15  # 15% margin from top

        # --- Draw Components ---
        self._draw_runway(canvas, canvas_width, runway_y, runway_length, runway_width, runways[0])
        self._draw_taxiways(canvas, canvas_width, runway_length, runway_y, main_taxiway_y, taxiways)
        self._draw_aprons_and_gates(canvas, canvas_width, apron_top_y, apron_bottom_y, gates)
        self._draw_diagram_labels(canvas, canvas_width, canvas_height, airport_data)

    def _draw_runway(self, canvas, c_width, r_y, r_length, r_width, rwy_name):
        """Draws the runway with more details."""
        x_start = (c_width - r_length) / 2
        x_end = x_start + r_length

        # Runway asphalt
        canvas.create_rectangle(
            x_start, r_y - r_width / 2, x_end, r_y + r_width / 2,
            fill="#4a4a4a", outline="#6e6e6e", width=2, tags="runway"
        )
        # Centerline
        canvas.create_line(
            x_start + 70, r_y, x_end - 70, r_y,
            fill="white", width=2, dash=(30, 20), tags="runway_marking"
        )
        
        # Threshold markings (piano keys)
        for i in range(5):
            offset = i * 4
            canvas.create_rectangle(x_start + 15 + offset, r_y - r_width/3, x_start + 20 + offset, r_y + r_width/3, fill="white", outline="")
            canvas.create_rectangle(x_end - 15 - offset, r_y - r_width/3, x_end - 20 - offset, r_y + r_width/3, fill="white", outline="")

        # Runway labels
        rwy_labels = rwy_name.split('/')
        canvas.create_text(
            x_start + 45, r_y, text=rwy_labels[0], fill="white",
            font=("Consolas", 14, "bold"), anchor="center"
        )
        if len(rwy_labels) > 1:
            canvas.create_text(
                x_end - 45, r_y, text=rwy_labels[1], fill="white",
                font=("Consolas", 14, "bold"), anchor="center"
            )

    def _draw_taxiways(self, canvas, c_width, r_length, r_y, t_y, taxiways):
        """Draws a more complex taxiway system."""
        x_start = (c_width - r_length) / 2
        x_end = x_start + r_length
        taxiway_width = 12

        # Main parallel taxiway
        canvas.create_line(
            x_start, t_y, x_end, t_y,
            fill="#a08b5f", width=taxiway_width, capstyle=tk.ROUND, tags="taxiway"
        )
        canvas.create_line(
            x_start, t_y, x_end, t_y,
            fill="#796841", width=1, tags="taxiway_edge"
        )
        canvas.create_text(
            x_start - 15, t_y, text=taxiways[0] if taxiways else 'A', 
            fill="#796841", font=("Arial", 9, "bold"), anchor="e"
        )
        
        # Perpendicular connectors to runway
        num_connectors = 5
        connector_labels = (taxiways[1:] + ["", "", "", ""])[:num_connectors-1] # Pad list to avoid index errors

        for i in range(1, num_connectors):
            conn_x = x_start + (r_length / num_connectors) * i
            canvas.create_line(
                conn_x, t_y, conn_x, r_y - (20 / 2),
                fill="#a08b5f", width=taxiway_width-2, capstyle=tk.ROUND, tags="taxiway"
            )
            label = connector_labels[i-1]
            if label:
                canvas.create_text(
                    conn_x, t_y + 15, text=label,
                    fill="#796841", font=("Arial", 8, "bold")
                )

    def _draw_aprons_and_gates(self, canvas, c_width, top_y, bottom_y, gates):
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
            self._draw_apron_section(canvas, section['name'], section['bays'], current_x, top_y, section_width, top_y - bottom_y)
            current_x += section_width

    def _draw_diagram_labels(self, canvas, c_width, c_height, airport_data):
        """Draws the airport name and other diagram labels."""
        airport_name = airport_data.get("name", "Unknown Airport")
        canvas.create_text(
            c_width / 2, c_height * 0.07, text=airport_name,
            font=("Arial", 18, "bold"), fill="#2c3e50"
        )
        canvas.create_text(
            c_width - 10, c_height - 10, text="Diagram not to scale",
            anchor="se", font=("Arial", 8, "italic"), fill="grey"
        )

    def _draw_no_diagram_message(self, canvas, width, height):
        """Draw a message when no diagram is available."""
        canvas.create_text(
            width / 2, height / 2,
            text="No Airport Diagram Available for this airport.",
            font=("Arial", 14, "italic"),
            fill="#888888"
        )

    def _draw_apron_section(self, canvas, name, gates, x_pos, y_pos, width, height):
        """Draws a single apron section with gates, updated for new layout."""
        # Apron background
        canvas.create_rectangle(
            x_pos, y_pos - height, x_pos + width, y_pos,
            fill="#C8C8C8", outline="#A0A0A0", width=2, tags="apron"
        )
        # Apron label
        canvas.create_text(
            x_pos + width / 2, y_pos - height + 20, text=name, 
            font=("Arial", 11, "bold"), fill="#555555"
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
            canvas.create_line(gate_x, gate_y_start, gate_x, gate_y_end, fill="#eac117", width=1.5, dash=(4, 4))
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

    def log_communication(self, text_widget, sender, message, clear=False):
        """Log communication messages to the specified text widget"""
        if clear:
            text_widget.config(state=tk.NORMAL)
            text_widget.delete(1.0, tk.END)
            text_widget.config(state=tk.DISABLED)
        
        # Get current time
        current_time = time.strftime("%H:%M:%S")
        
        # Format the message
        formatted_message = f"[{current_time}] {sender}: {message}\n"
        
        # Add to the text widget
        text_widget.config(state=tk.NORMAL)
        text_widget.insert(tk.END, formatted_message)
        text_widget.see(tk.END)  # Scroll to the end
        text_widget.config(state=tk.DISABLED)

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