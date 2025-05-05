import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import threading
import time
import requests
import random
import math


class ATCWindow:
    def __init__(self, root, config, airports):
        self.root = root
        self.config = config
        self.airports = airports
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
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
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
        if list(self.airports.keys()):
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
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create status bar
        self.status_bar = ttk.Label(
            self.main_frame, 
            text="Status: Ready",
            relief=tk.SUNKEN, 
            anchor=tk.W
        )
        self.status_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        
        # Set up controller position tabs
        self.setup_ground_tab()
        self.setup_tower_tab()
        self.setup_approach_tab()
        self.setup_departure_tab()
        self.setup_atis_tab()
        
        # Initialize weather display
        self.update_airport_config()
        self.update_weather_display()

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

    def get_airport_weather_string(self):
        """Get formatted weather string for display"""
        airport_data = self.airports[self.current_airport]
        wind = airport_data.get("wind", "---")
        visibility = airport_data.get("visibility", "---")
        ceiling = airport_data.get("ceiling", "---")

        return f"Wind: {wind} | Visibility: {visibility} | Ceiling: {ceiling}"

    def setup_ground_tab(self):
        """Set up the Ground Control tab"""
        self.ground_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.ground_tab, text="Ground Control")

        # Split the tab into sections
        ground_left_frame = ttk.Frame(self.ground_tab)
        ground_left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        ground_right_frame = ttk.Frame(self.ground_tab)
        ground_right_frame.pack(
            side=tk.RIGHT, fill=tk.BOTH, expand=False, padx=(5, 0)
        )
        ground_right_frame.config(width=400)  # Set width after packing
        ground_right_frame.pack_propagate(False)  # Prevent the frame from shrinking

        # Aircraft list section
        aircraft_frame = ttk.LabelFrame(ground_left_frame, text="Aircraft on Ground")
        aircraft_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        # Create list with scrollbar
        list_frame = ttk.Frame(aircraft_frame)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.ground_aircraft_list = tk.Listbox(
            list_frame, height=15, selectmode=tk.SINGLE, font=("Consolas", 10)
        )
        self.ground_aircraft_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.ground_aircraft_list.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.ground_aircraft_list.yview)

        # Status indicators for aircraft
        indicator_frame = ttk.Frame(aircraft_frame)
        indicator_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        self.ground_status_indicators = []
        for i in range(10):  # Maximum 10 status indicators
            status_canvas = tk.Canvas(
                indicator_frame, width=15, height=15, bg="white", highlightthickness=0
            )
            status_canvas.pack(side=tk.LEFT, padx=1)
            self.ground_status_indicators.append(status_canvas)

        # Bind selection event to update status indicators
        self.ground_aircraft_list.bind(
            "<<ListboxSelect>>", self.update_ground_status_indicators
        )

        # Control buttons
        control_frame = ttk.Frame(aircraft_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=(0, 10))

        ttk.Button(
            control_frame, text="Add Aircraft", command=self.add_ground_aircraft
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            control_frame, text="Remove", command=self.remove_ground_aircraft
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            control_frame, text="Edit Status", command=self.edit_ground_status
        ).pack(side=tk.LEFT, padx=5)

        # Communication buttons
        comm_frame = ttk.LabelFrame(ground_left_frame, text="Communications")
        comm_frame.pack(fill=tk.BOTH, pady=(5, 0), ipady=5)

        button_frame = ttk.Frame(comm_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=(10, 5))

        ttk.Button(
            button_frame,
            text="Taxi Clearance",
            command=lambda: self.issue_instruction("taxi"),
        ).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(
            button_frame,
            text="Hold Position",
            command=lambda: self.issue_instruction("hold"),
        ).pack(side=tk.LEFT, padx=5)
        ttk.Button(
            button_frame,
            text="Transfer to Tower",
            command=lambda: self.transfer_aircraft("Tower"),
        ).pack(side=tk.LEFT, padx=5)

        # Current instruction display
        self.ground_instructions = tk.Text(comm_frame, height=3, wrap=tk.WORD)
        self.ground_instructions.pack(fill=tk.X, padx=10, pady=(5, 10))

        # Airport diagram on the right
        diagram_frame = ttk.LabelFrame(ground_right_frame, text="Airport Diagram")
        diagram_frame.pack(fill=tk.BOTH, expand=True)

        self.ground_canvas = tk.Canvas(diagram_frame, bg="white")
        self.ground_canvas.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Draw initial airport diagram
        self.root.update_idletasks()  # Ensure canvas is properly sized
        self.draw_airport_diagram(self.ground_canvas)

    def setup_tower_tab(self):
        """Set up the tower control tab interface"""
        # Create a frame with left and right sides
        main_frame = ttk.Frame(self.notebook)
        self.notebook.add(main_frame, text="Tower Control")  # Add the tab to the notebook
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left side - Departure and Arrival queues
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side="left", fill="both", expand=True, padx=(0, 5))
        
        # Right side - Runway status and weather
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side="right", fill="both", expand=True, padx=(5, 0))
        
        # === LEFT SIDE - AIRCRAFT QUEUES ===
        # Departure queue frame
        departure_frame = ttk.LabelFrame(left_frame, text="Departure Queue")
        departure_frame.pack(fill="both", expand=True, pady=(0, 5))
        
        # Create departure listbox with scrollbar
        departure_list_frame = ttk.Frame(departure_frame)
        departure_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        departure_scrollbar = ttk.Scrollbar(departure_list_frame)
        departure_scrollbar.pack(side="right", fill="y")
        
        self.departure_listbox = tk.Listbox(
            departure_list_frame,
            height=10,  # Increased height
            width=40,
            yscrollcommand=departure_scrollbar.set,
            selectmode="single",
            font=("Consolas", 10),
            bg="white",  # Explicit background color
            relief=tk.SUNKEN,  # Add border relief
            borderwidth=1      # Add border width
        )
        self.departure_listbox.pack(side="left", fill="both", expand=True)
        departure_scrollbar.config(command=self.departure_listbox.yview)
        
        # Add a placeholder message for empty queue
        self.departure_listbox.insert(tk.END, "No aircraft in departure queue")
        self.departure_listbox.itemconfig(0, {'fg': 'gray'})  # Gray out the placeholder text
        
        # Ensure the departure list frame has a minimum height
        departure_list_frame.update_idletasks()
        min_height = 150  # Minimum height in pixels
        current_height = departure_list_frame.winfo_height()
        if current_height < min_height:
            departure_list_frame.config(height=min_height)
            departure_list_frame.pack_propagate(False)  # Prevent shrinking smaller than min_height
        
        # Departure control buttons
        departure_buttons_frame = ttk.Frame(departure_frame)
        departure_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(
            departure_buttons_frame,
            text="Add Aircraft",
            command=lambda: self.add_aircraft_to_queue("departure")
        ).pack(side="left", padx=2)
        
        ttk.Button(
            departure_buttons_frame,
            text="Remove",
            command=lambda: self.remove_aircraft_from_queue("departure")
        ).pack(side="left", padx=2)
        
        ttk.Button(
            departure_buttons_frame,
            text="Line Up",
            command=self.line_up_departure
        ).pack(side="left", padx=2)
        
        ttk.Button(
            departure_buttons_frame,
            text="Takeoff Clearance",
            command=self.issue_takeoff_clearance
        ).pack(side="left", padx=2)
        
        # Arrival queue frame - Apply the same fixes
        arrival_frame = ttk.LabelFrame(left_frame, text="Arrival Queue")
        arrival_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        # Create arrival listbox with scrollbar
        arrival_list_frame = ttk.Frame(arrival_frame)
        arrival_list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        arrival_scrollbar = ttk.Scrollbar(arrival_list_frame)
        arrival_scrollbar.pack(side="right", fill="y")
        
        self.arrival_listbox = tk.Listbox(
            arrival_list_frame,
            height=10,  # Increased height
            width=40,
            yscrollcommand=arrival_scrollbar.set,
            selectmode="single",
            font=("Consolas", 10),
            bg="white",  # Explicit background color
            relief=tk.SUNKEN,  # Add border relief
            borderwidth=1      # Add border width
        )
        self.arrival_listbox.pack(side="left", fill="both", expand=True)
        arrival_scrollbar.config(command=self.arrival_listbox.yview)
        
        # Add a placeholder message for empty queue
        self.arrival_listbox.insert(tk.END, "No aircraft in arrival queue")
        self.arrival_listbox.itemconfig(0, {'fg': 'gray'})  # Gray out the placeholder text
        
        # Ensure the arrival list frame has a minimum height
        arrival_list_frame.update_idletasks()
        if arrival_list_frame.winfo_height() < min_height:
            arrival_list_frame.config(height=min_height)
            arrival_list_frame.pack_propagate(False)  # Prevent shrinking smaller than min_height
        
        # Arrival control buttons
        arrival_buttons_frame = ttk.Frame(arrival_frame)
        arrival_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(
            arrival_buttons_frame,
            text="Add Aircraft",
            command=lambda: self.add_aircraft_to_queue("arrival")
        ).pack(side="left", padx=2)
        
        ttk.Button(
            arrival_buttons_frame,
            text="Remove",
            command=lambda: self.remove_aircraft_from_queue("arrival")
        ).pack(side="left", padx=2)
        
        ttk.Button(
            arrival_buttons_frame,
            text="Approach Clearance",
            command=self.issue_approach_clearance
        ).pack(side="left", padx=2)
        
        ttk.Button(
            arrival_buttons_frame,
            text="Landing Clearance",
            command=self.issue_landing_clearance
        ).pack(side="left", padx=2)
        
        # === RIGHT SIDE - RUNWAY STATUS AND WEATHER ===
        # Runway status frame
        self.runway_frame = ttk.LabelFrame(right_frame, text="Runway Status")
        self.runway_frame.pack(fill="both", expand=True, pady=(0, 5))
        
        # Initial placeholder for runway frame
        ttk.Label(
            self.runway_frame, 
            text="Select an airport to view runway status"
        ).pack(pady=20)
        
        # Weather information frame
        weather_frame = ttk.LabelFrame(right_frame, text="Current Weather")
        weather_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        # Weather display
        self.tower_weather_display = ttk.Label(
            weather_frame,
            text="No weather data available",
            wraplength=300,
            justify="left"
        )
        self.tower_weather_display.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Weather refresh button
        ttk.Button(
            weather_frame,
            text="Refresh Weather",
            command=self.refresh_current_airport_weather
        ).pack(side="left", padx=10, pady=(0, 10))
        
        # Auto weather update checkbox
        self.auto_weather_var = tk.BooleanVar(value=self.auto_weather_update)
        auto_weather_check = ttk.Checkbutton(
            weather_frame,
            text="Auto Weather Updates",
            variable=self.auto_weather_var,
            command=self.toggle_auto_weather_updates
        )
        auto_weather_check.pack(side="right", padx=10, pady=(0, 10))
        
        # Initial update
        self.update_runway_frame()

    def setup_approach_tab(self):
        """Set up the Approach tab"""
        # Basic structure - to be expanded
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
        """Set up the ATIS Management tab"""
        # Basic structure - to be expanded
        self.atis_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.atis_tab, text="ATIS Management")
        ttk.Label(self.atis_tab, text="ATIS Management - Coming Soon").pack(pady=20)
        ttk.Label(
            self.atis_tab,
            text="This tab will provide tools for creating and updating ATIS information.",
        ).pack()

    # Helper methods for Ground Control tab
    def add_ground_aircraft(self):
        """Add a new aircraft to ground control"""
        # Create a dialog window
        add_dialog = tk.Toplevel(self.root)
        add_dialog.title("Add Aircraft")
        add_dialog.geometry("400x350")
        add_dialog.resizable(False, False)
        add_dialog.transient(self.root)  # Make dialog modal
        add_dialog.grab_set()

        # Create a frame with padding
        frame = ttk.Frame(add_dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Dialog header
        ttk.Label(frame, text="Add New Aircraft", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 15)
        )

        # Input fields
        ttk.Label(frame, text="Callsign:").grid(row=1, column=0, sticky=tk.W, pady=5)
        callsign_var = tk.StringVar()
        callsign_entry = ttk.Entry(frame, textvariable=callsign_var, width=25)
        callsign_entry.grid(row=1, column=1, sticky=tk.W, pady=5)

        ttk.Label(frame, text="Aircraft Type:").grid(
            row=2, column=0, sticky=tk.W, pady=5
        )
        type_var = tk.StringVar()
        type_entry = ttk.Combobox(frame, textvariable=type_var, width=25)
        type_entry["values"] = (
            "C172",
            "C152",
            "PA28",
            "B737",
            "A320",
            "E145",
            "CRJ2",
            "B747",
            "B777",
            "A330",
            "A380",
        )
        type_entry.grid(row=2, column=1, sticky=tk.W, pady=5)

        # Get dynamic locations from current airport
        airport_data = self.airports.get(self.current_airport, {})
        gates = airport_data.get("gates", [])
        taxiways = airport_data.get("taxiways", [])
        runways = airport_data.get("runways", [])
        
        # Create location options based on airport configuration
        location_options = []
        
        # Add gates with proper formatting
        for gate in gates:
            if not gate.startswith("Gate "):
                location_options.append(f"Gate {gate}")
            else:
                location_options.append(gate)
                
        # Add taxiways with proper formatting
        for taxiway in taxiways:
            if not taxiway.startswith("Taxiway "):
                location_options.append(f"Taxiway {taxiway}")
            else:
                location_options.append(taxiway)
                
        # Add runways with proper formatting
        for runway in runways:
            if not runway.startswith("Runway "):
                location_options.append(f"Runway {runway}")
            else:
                location_options.append(runway)
        
        # If no locations found, add some defaults
        if not location_options:
            location_options = [
                "Gate A1", "Gate A2", "Taxiway A", "Taxiway B", "Runway 27"
            ]

        ttk.Label(frame, text="Location:").grid(row=3, column=0, sticky=tk.W, pady=5)
        location_var = tk.StringVar()
        location_entry = ttk.Combobox(frame, textvariable=location_var, width=25)
        location_entry["values"] = tuple(location_options)
        location_entry.grid(row=3, column=1, sticky=tk.W, pady=5)

        # Create dynamic status options based on airport configuration
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

        # Additional options
        ttk.Label(frame, text="Notes:").grid(row=5, column=0, sticky=tk.W, pady=5)
        notes_text = tk.Text(frame, width=30, height=5)
        notes_text.grid(row=5, column=1, sticky=tk.W, pady=5)

        # Buttons frame
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=(20, 0))

        def add_aircraft():
            # Validate inputs
            callsign = callsign_var.get().strip()
            aircraft_type = type_var.get().strip()
            location = location_var.get().strip()
            status = status_var.get().strip()

            if not callsign or not aircraft_type or not location or not status:
                messagebox.showwarning(
                    "Missing Information", "Please fill in all required fields"
                )
                return

            # Create the new aircraft entry
            new_aircraft = f"{callsign} - {aircraft_type} - {location} - {status}"

            # Add to the listbox
            self.ground_aircraft_list.insert(tk.END, new_aircraft)

            # Update status bar
            self.status_bar.config(text=f"Status: Added aircraft {callsign} to ground control")

            # Close the dialog
            add_dialog.destroy()

        def cancel():
            add_dialog.destroy()

        ttk.Button(button_frame, text="Add Aircraft", command=add_aircraft).pack(
            side=tk.LEFT, padx=(0, 10)
        )
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.LEFT)

        # Center the dialog on the parent window
        add_dialog.update_idletasks()
        width = add_dialog.winfo_width()
        height = add_dialog.winfo_height()
        x = self.root.winfo_x() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
        add_dialog.geometry(f"{width}x{height}+{x}+{y}")

        # Focus on the first entry
        callsign_entry.focus_set()

        # Wait for the dialog to be closed
        add_dialog.wait_window()

    def remove_ground_aircraft(self):
        """Remove an aircraft from ground control"""
        selected = self.ground_aircraft_list.curselection()
        if selected:
            self.ground_aircraft_list.delete(selected)
            self.status_bar.config(text="Status: Aircraft removed from ground control")
        else:
            messagebox.showinfo(
                "Selection Required", "Please select an aircraft to remove"
            )

    def edit_ground_status(self):
        """Edit the status of an aircraft on the ground"""
        selected = self.ground_aircraft_list.curselection()
        if not selected:
            messagebox.showinfo(
                "Selection Required", "Please select an aircraft to edit"
            )
            return

        # Get the selected aircraft info
        aircraft_info = self.ground_aircraft_list.get(selected)

        # Create a dialog window
        edit_dialog = tk.Toplevel(self.root)
        edit_dialog.title("Edit Aircraft Status")
        edit_dialog.geometry("400x350")
        edit_dialog.resizable(False, False)
        edit_dialog.transient(self.root)  # Make dialog modal
        edit_dialog.grab_set()

        # Create a frame with padding
        frame = ttk.Frame(edit_dialog, padding="20")
        frame.pack(fill=tk.BOTH, expand=True)

        # Display current aircraft information
        ttk.Label(frame, text="Aircraft Information:", font=("Arial", 12, "bold")).grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=(0, 10)
        )

        # Parse current information (assuming format: "CALLSIGN - TYPE - LOCATION - STATUS")
        parts = aircraft_info.split(" - ")
        callsign = parts[0] if len(parts) > 0 else ""
        aircraft_type = parts[1] if len(parts) > 1 else ""
        location = parts[2] if len(parts) > 2 else ""
        status = parts[3] if len(parts) > 3 else ""

        # Display current info
        ttk.Label(frame, text="Callsign:").grid(row=1, column=0, sticky=tk.W, pady=5)
        ttk.Label(frame, text=callsign).grid(row=1, column=1, sticky=tk.W, pady=5)

        ttk.Label(frame, text="Type:").grid(row=2, column=0, sticky=tk.W, pady=5)
        ttk.Label(frame, text=aircraft_type).grid(row=2, column=1, sticky=tk.W, pady=5)

        # Get dynamic locations from current airport
        airport_data = self.airports.get(self.current_airport, {})
        gates = airport_data.get("gates", [])
        taxiways = airport_data.get("taxiways", [])
        runways = airport_data.get("runways", [])
        
        # Create location options based on airport configuration
        location_options = []
        
        # Add gates with proper formatting
        for gate in gates:
            if not gate.startswith("Gate "):
                location_options.append(f"Gate {gate}")
            else:
                location_options.append(gate)
                
        # Add taxiways with proper formatting
        for taxiway in taxiways:
            if not taxiway.startswith("Taxiway "):
                location_options.append(f"Taxiway {taxiway}")
            else:
                location_options.append(taxiway)
                
        # Add runways with proper formatting
        for runway in runways:
            if not runway.startswith("Runway "):
                location_options.append(f"Runway {runway}")
            else:
                location_options.append(runway)
        
        # If no locations found, add some defaults
        if not location_options:
            location_options = [
                "Gate A1", "Gate A2", "Taxiway A", "Taxiway B", "Runway 27"
            ]

        # Create input fields for editable information
        ttk.Label(frame, text="Location:").grid(row=3, column=0, sticky=tk.W, pady=5)
        location_var = tk.StringVar(value=location)
        location_entry = ttk.Combobox(frame, textvariable=location_var, width=25)
        location_entry["values"] = tuple(location_options)
        location_entry.grid(row=3, column=1, sticky=tk.W, pady=5)

        # Create dynamic status options based on airport configuration
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

        # Additional options
        ttk.Label(frame, text="Notes:").grid(row=5, column=0, sticky=tk.W, pady=5)
        notes_text = tk.Text(frame, width=30, height=5)
        notes_text.grid(row=5, column=1, sticky=tk.W, pady=5)

        # Buttons frame
        button_frame = ttk.Frame(frame)
        button_frame.grid(row=6, column=0, columnspan=2, pady=(20, 0))

        def save_changes():
            # Update the aircraft status in the list
            new_location = location_var.get()
            new_status = status_var.get()
            new_aircraft_info = (
                f"{callsign} - {aircraft_type} - {new_location} - {new_status}"
            )

            # Update the listbox
            self.ground_aircraft_list.delete(selected)
            self.ground_aircraft_list.insert(selected, new_aircraft_info)
            self.ground_aircraft_list.selection_set(selected)

            # Update status bar
            self.status_bar.config(text=f"Status: Updated status for {callsign}")

            # Close the dialog
            edit_dialog.destroy()

        def cancel():
            edit_dialog.destroy()

        ttk.Button(button_frame, text="Save Changes", command=save_changes).pack(
            side=tk.LEFT, padx=(0, 10)
        )
        ttk.Button(button_frame, text="Cancel", command=cancel).pack(side=tk.LEFT)

        # Center the dialog on the parent window
        edit_dialog.update_idletasks()
        width = edit_dialog.winfo_width()
        height = edit_dialog.winfo_height()
        x = self.root.winfo_x() + (self.root.winfo_width() - width) // 2
        y = self.root.winfo_y() + (self.root.winfo_height() - height) // 2
        edit_dialog.geometry(f"{width}x{height}+{x}+{y}")

        # Wait for the dialog to be closed
        edit_dialog.wait_window()

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
        callsign_entry = ttk.Entry(dialog, width=20)
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
            callsign = callsign_entry.get().strip().upper()
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
        callsign = aircraft_info.split(" ")[0]
        
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
        callsign = aircraft_info.split(" ")[0]
        
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

    def issue_instruction(self, instruction_type):
        """Issue an instruction to the selected aircraft"""
        selected = self.ground_aircraft_list.curselection()
        if not selected:
            messagebox.showinfo(
                "Selection Required", "Please select an aircraft to issue an instruction"
            )
            return
            
        aircraft_info = self.ground_aircraft_list.get(selected)
        callsign = aircraft_info.split(" - ")[0]
        
        # Get airport data for specific instructions
        airport_data = self.airports.get(self.current_airport, {})
        icao_code = self.current_airport.split(" - ")[0] if " - " in self.current_airport else ""
        runways = airport_data.get("runways", [])
        taxiways = airport_data.get("taxiways", [])
        
        # Prepare instruction based on instruction type and airport specifics
        instruction_text = ""
        
        if instruction_type == "taxi":
            # Get taxiways and runways from current airport for specific instruction
            taxi_routes = []
            if taxiways:
                # Create some realistic taxi routes using available taxiways
                if len(taxiways) >= 3:
                    taxi_routes.append(f"via {taxiways[0]} then {taxiways[1]} to {taxiways[2]}")
                    if len(taxiways) >= 4:
                        taxi_routes.append(f"via {taxiways[0]} then {taxiways[2]} cross {taxiways[3]}")
                elif len(taxiways) == 2:
                    taxi_routes.append(f"via {taxiways[0]} then {taxiways[1]}")
                else:
                    taxi_routes.append(f"via {taxiways[0]}")
            else:
                taxi_routes = ["via Alpha", "via Bravo then Charlie"]
                
            # Select a random taxi route for variety
            taxi_route = random.choice(taxi_routes)
            
            # Select target runway
            runway = runways[0] if runways else "27"
            
            # Format instruction using correct local phraseology based on ICAO region
            if icao_code.startswith("K"):  # US
                instruction_text = f"{callsign}, taxi to runway {runway} {taxi_route}, hold short."
            elif icao_code.startswith("E"):  # Europe
                instruction_text = f"{callsign}, taxi to holding point runway {runway} {taxi_route}."
            else:  # Default international
                instruction_text = f"{callsign}, taxi to holding point runway {runway} {taxi_route}."
                
        elif instruction_type == "hold":
            current_position = aircraft_info.split(" - ")[2] if len(aircraft_info.split(" - ")) >= 3 else "current position"
            
            # Format hold instruction based on region
            if icao_code.startswith("K"):  # US
                instruction_text = f"{callsign}, hold position at {current_position}."
            else:  # International
                instruction_text = f"{callsign}, hold position at {current_position}."
                
        elif instruction_type == "pushback":
            # Format pushback instruction based on region and terminal area
            terminals = airport_data.get("terminals", ["main terminal"])
            terminal = terminals[0] if terminals else "terminal"
            
            if icao_code.startswith("K"):  # US
                instruction_text = f"{callsign}, pushback approved, expect runway {runways[0] if runways else '27'}."
            elif icao_code.startswith("E"):  # Europe 
                instruction_text = f"{callsign}, push and start approved, face {taxiways[0] if taxiways else 'Alpha'}."
            else:
                instruction_text = f"{callsign}, pushback approved from {terminal}."
                
        else:
            # Generic instruction
            instruction_text = f"{callsign}, {instruction_type} instruction."
            
        # Display the instruction
        self.ground_instructions.delete(1.0, tk.END)
        self.ground_instructions.insert(tk.END, instruction_text)
        
        # For now, just show the instruction in the text area
        # Later, this could update the aircraft's status, log the communication, etc.
        self.status_bar.config(text=f"Status: Issued {instruction_type} instruction to {callsign}")

    def enrich_airport_data(self):
        """Add additional dynamic data to airports to enhance the user experience"""
        for airport_key, airport_data in self.airports.items():
            icao_code = airport_key.split(" - ")[0] if " - " in airport_key else ""
            
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
                if "London" in airport_key or "Heathrow" in airport_key:
                    airport_data["time_restrictions"] = [
                        "Night curfew in effect 23:30-06:00 local time",
                        "Reduced operations between 23:00-23:30"
                    ]
                elif "Frankfurt" in airport_key:
                    airport_data["time_restrictions"] = [
                        "Night flight restrictions 23:00-05:00 local time"
                    ]
                elif "Los Angeles" in airport_key or "LAX" in airport_key:
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
        # Get selected aircraft
        selected = self.ground_aircraft_list.curselection()
        if not selected:
            # Clear all indicators if nothing selected
            for canvas in self.ground_status_indicators:
                canvas.config(bg="white")
            return
            
        # Get the aircraft info
        aircraft_info = self.ground_aircraft_list.get(selected)
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
            self.tower_weather_display.config(text=tower_weather)
        
        # Update status bar
        self.status_bar.config(text=f"Status: Weather updated for {self.current_airport}")

    def transfer_aircraft(self, destination):
        """Transfer an aircraft to another controller position"""
        selected = self.ground_aircraft_list.curselection()
        if not selected:
            messagebox.showinfo(
                "Selection Required", "Please select an aircraft to transfer"
            )
            return
            
        aircraft_info = self.ground_aircraft_list.get(selected)
        callsign = aircraft_info.split(" - ")[0]
        aircraft_type = aircraft_info.split(" - ")[1] if len(aircraft_info.split(" - ")) > 1 else ""
        
        # Remove from ground list
        self.ground_aircraft_list.delete(selected)
        
        # Different behavior based on destination
        if destination == "Tower":
            # Add to Tower's departure queue
            if hasattr(self, "departure_listbox"):
                # Add to departure queue with appropriate status
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
            self.ground_instructions.delete(1.0, tk.END)
            self.ground_instructions.insert(tk.END, f"{callsign}, contact Tower on {self.get_tower_frequency()}")
            
        # Could add other destinations here (Approach, Departure, etc.)
        
        # Update status bar
        self.status_bar.config(text=f"Status: {callsign} transferred to {destination}")
    
    def get_tower_frequency(self):
        """Get the tower frequency for the current airport"""
        airport_data = self.airports.get(self.current_airport, {})
        frequencies = airport_data.get("frequencies", {})
        return frequencies.get("tower", "118.1")  # Default frequency if not defined

    def draw_airport_diagram(self, canvas):
        """Draw the airport diagram on the provided canvas"""
        # Clear the canvas
        canvas.delete("all")
        
        # Get current airport data
        airport_data = self.airports.get(self.current_airport, {})
        
        # Get canvas dimensions
        canvas_width = canvas.winfo_width()
        canvas_height = canvas.winfo_height()
        
        # If canvas hasn't been properly sized yet, use default values
        if canvas_width < 10 or canvas_height < 10:
            canvas_width = 400
            canvas_height = 400
        
        # Draw background
        canvas.create_rectangle(0, 0, canvas_width, canvas_height, fill="#B5D99C", outline="")
        
        # Get airport elements
        runways = airport_data.get("runways", [])
        taxiways = airport_data.get("taxiways", [])
        gates = airport_data.get("gates", [])
        
        # Calculate diagram center
        center_x = canvas_width / 2
        center_y = canvas_height / 2
        
        # Draw runways
        runway_length = min(canvas_width, canvas_height) * 0.7
        runway_width = runway_length * 0.07
        
        if runways:
            # Calculate angles for runways based on their identifiers
            runway_angles = []
            for runway in runways:
                parts = runway.split("/")
                # Extract the runway number (removing L/R/C suffixes)
                runway_num = int(''.join(filter(str.isdigit, parts[0])))
                # Calculate angle (runway 09 = 90 degrees, 27 = 270 degrees, etc.)
                angle = (runway_num * 10) % 360
                runway_angles.append(angle)
            
            # Draw each runway
            for i, (runway, angle) in enumerate(zip(runways, runway_angles)):
                # Convert angle to radians
                angle_rad = angle * 3.14159 / 180
                
                # Calculate runway endpoints
                x1 = center_x - (runway_length / 2) * math.cos(angle_rad)
                y1 = center_y - (runway_length / 2) * math.sin(angle_rad)
                x2 = center_x + (runway_length / 2) * math.cos(angle_rad)
                y2 = center_y + (runway_length / 2) * math.sin(angle_rad)
                
                # Draw the runway
                runway_id = canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill="#444444",
                    width=2,
                    outline="#FFFFFF",
                    tags=f"runway_{runway}"
                )
                
                # Rotate the runway
                canvas.itemconfig(runway_id, tags=f"runway_{runway}")
                
                # Add runway identifier text
                label_x = x2 - (runway_length * 0.1) * math.cos(angle_rad)
                label_y = y2 - (runway_length * 0.1) * math.sin(angle_rad)
                canvas.create_text(
                    label_x, label_y,
                    text=runway,
                    fill="white",
                    font=("Arial", 10, "bold")
                )
        else:
            # If no runways defined, draw default north-south and east-west runways
            # North-South runway
            canvas.create_rectangle(
                center_x - runway_width / 2, center_y - runway_length / 2,
                center_x + runway_width / 2, center_y + runway_length / 2,
                fill="#444444",
                outline="#FFFFFF",
                width=2,
                tags="runway_ns"
            )
            # Add runway identifiers
            canvas.create_text(
                center_x, center_y - runway_length / 2 + 20,
                text="36",
                fill="white",
                font=("Arial", 10, "bold")
            )
            canvas.create_text(
                center_x, center_y + runway_length / 2 - 20,
                text="18",
                fill="white",
                font=("Arial", 10, "bold")
            )
            
            # East-West runway
            canvas.create_rectangle(
                center_x - runway_length / 2, center_y - runway_width / 2,
                center_x + runway_length / 2, center_y + runway_width / 2,
                fill="#444444",
                outline="#FFFFFF",
                width=2,
                tags="runway_ew"
            )
            # Add runway identifiers
            canvas.create_text(
                center_x - runway_length / 2 + 20, center_y,
                text="27",
                fill="white",
                font=("Arial", 10, "bold")
            )
            canvas.create_text(
                center_x + runway_length / 2 - 20, center_y,
                text="09",
                fill="white",
                font=("Arial", 10, "bold")
            )
        
        # Draw taxiways
        if taxiways:
            # Create some random taxiway paths connecting runways
            offset_y = runway_width * 1.5
            for i, taxiway in enumerate(taxiways):
                # Offset from center to create parallel taxiways
                tx_offset = (i - len(taxiways) / 2) * offset_y
                
                # Draw a curved taxiway
                points = []
                for t in range(0, 101, 5):
                    t_normalized = t / 100.0
                    # Create a curve from one side to another
                    curve_x = center_x - runway_length / 2 + runway_length * t_normalized
                    curve_y = center_y + tx_offset + math.sin(t_normalized * 3.14159) * offset_y
                    points.extend([curve_x, curve_y])
                
                # Draw the taxiway
                canvas.create_line(
                    points,
                    fill="#FFFF00",
                    width=3,
                    joinstyle=tk.ROUND,
                    tags=f"taxiway_{taxiway}"
                )
                
                # Add taxiway identifier
                label_t = 50  # Middle point
                label_x = center_x
                label_y = center_y + tx_offset + math.sin(label_t / 100.0 * 3.14159) * offset_y - 10
                canvas.create_text(
                    label_x, label_y,
                    text=taxiway,
                    fill="black",
                    font=("Arial", 8, "bold"),
                    tags=f"taxiway_label_{taxiway}"
                )
        else:
            # Draw default taxiways if none defined
            # Main taxiway parallel to NS runway
            canvas.create_line(
                center_x + runway_width * 2, center_y - runway_length / 2,
                center_x + runway_width * 2, center_y + runway_length / 2,
                fill="#FFFF00",
                width=3,
                tags="taxiway_alpha"
            )
            # Taxiway label
            canvas.create_text(
                center_x + runway_width * 2, center_y,
                text="A",
                fill="black",
                font=("Arial", 8, "bold")
            )
            
            # Main taxiway parallel to EW runway
            canvas.create_line(
                center_x - runway_length / 2, center_y + runway_width * 2,
                center_x + runway_length / 2, center_y + runway_width * 2,
                fill="#FFFF00",
                width=3,
                tags="taxiway_bravo"
            )
            # Taxiway label
            canvas.create_text(
                center_x, center_y + runway_width * 2,
                text="B",
                fill="black",
                font=("Arial", 8, "bold")
            )
        
        # Draw terminal and gates
        terminal_width = runway_length * 0.3
        terminal_height = runway_width * 3
        terminal_x = center_x - terminal_width / 2
        terminal_y = center_y + runway_length / 2 - terminal_height - runway_width * 4
        
        # Draw terminal building
        canvas.create_rectangle(
            terminal_x, terminal_y,
            terminal_x + terminal_width, terminal_y + terminal_height,
            fill="#8A9EA0",
            outline="#444444",
            width=2,
            tags="terminal"
        )
        
        # Draw gates
        if gates:
            # Calculate gate positions along the terminal
            gate_width = terminal_width / (len(gates) + 1)
            for i, gate in enumerate(gates):
                gate_x = terminal_x + gate_width * (i + 1)
                gate_y = terminal_y + terminal_height
                
                # Draw gate
                canvas.create_rectangle(
                    gate_x - gate_width * 0.4, gate_y,
                    gate_x + gate_width * 0.4, gate_y + runway_width * 2,
                    fill="#B5D99C",
                    outline="#FFFFFF",
                    width=1,
                    tags=f"gate_{gate}"
                )
                
                # Add gate label
                canvas.create_text(
                    gate_x, gate_y + runway_width,
                    text=gate,
                    fill="black",
                    font=("Arial", 7)
                )
        else:
            # Draw default gates if none defined
            default_gates = ["A1", "A2", "A3", "B1", "B2"]
            gate_width = terminal_width / (len(default_gates) + 1)
            for i, gate in enumerate(default_gates):
                gate_x = terminal_x + gate_width * (i + 1)
                gate_y = terminal_y + terminal_height
                
                # Draw gate
                canvas.create_rectangle(
                    gate_x - gate_width * 0.4, gate_y,
                    gate_x + gate_width * 0.4, gate_y + runway_width * 2,
                    fill="#B5D99C",
                    outline="#FFFFFF",
                    width=1,
                    tags=f"gate_{gate}"
                )
                
                # Add gate label
                canvas.create_text(
                    gate_x, gate_y + runway_width,
                    text=gate,
                    fill="black",
                    font=("Arial", 7)
                )
        
        # Add airport name and info
        canvas.create_text(
            center_x, 20,
            text=self.current_airport,
            fill="black",
            font=("Arial", 12, "bold")
        )
        
        # Add compass rose in the corner
        radius = 20
        cx, cy = canvas_width - radius - 10, radius + 10
        canvas.create_oval(
            cx - radius, cy - radius,
            cx + radius, cy + radius,
            fill="white",
            outline="black"
        )
        # N marker
        canvas.create_text(cx, cy - radius + 10, text="N", fill="red", font=("Arial", 8, "bold"))
        # E marker
        canvas.create_text(cx + radius - 10, cy, text="E", fill="black", font=("Arial", 8, "bold"))
        # S marker
        canvas.create_text(cx, cy + radius - 10, text="S", fill="black", font=("Arial", 8, "bold"))
        # W marker
        canvas.create_text(cx - radius + 10, cy, text="W", fill="black", font=("Arial", 8, "bold"))
        # Compass lines
        canvas.create_line(cx, cy - radius + 5, cx, cy + radius - 5, fill="black")
        canvas.create_line(cx - radius + 5, cy, cx + radius - 5, cy, fill="black")

    def instruct_go_around(self):
        """Instruct selected arrival aircraft to go around"""
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
        
        # Update aircraft status
        aircraft_data = self.aircraft_data["arrival"][callsign]
        runway = aircraft_data["runway"]
        prev_status = aircraft_data["status"]
        aircraft_data["status"] = "Going Around"
        aircraft_data["last_instruction"] = "Go around"
        
        # Update listbox entry
        self.arrival_listbox.delete(index)
        new_text = f"{callsign} ({aircraft_data['type']}) - Going Around - RWY {runway}"
        self.arrival_listbox.insert(index, new_text)
        
        # Clear runway if this aircraft was using it
        airport_data = self.airports[self.current_airport]
        runway_status = airport_data.get("runway_status", {}).get(runway, {})
        if runway_status.get("current_aircraft") == callsign:
            self.clear_runway(runway)
        
        # Set a timer to return to approach (simulating go-around)
        self.root.after(10000, lambda: self.simulate_aircraft_returning(callsign))
        
        # Update status bar
        self.status_bar.config(text=f"Status: {callsign} instructed to go around from Runway {runway}")
    
    def simulate_aircraft_returning(self, callsign):
        """Simulate aircraft returning to the approach after a go-around"""
        if not hasattr(self, "aircraft_data") or "arrival" not in self.aircraft_data:
            return
            
        if callsign not in self.aircraft_data["arrival"]:
            return
            
        # Update aircraft status
        aircraft_data = self.aircraft_data["arrival"][callsign]
        runway = aircraft_data["runway"]
        aircraft_data["status"] = "On Approach"
        
        # Find and update in listbox
        for i in range(self.arrival_listbox.size()):
            if callsign in self.arrival_listbox.get(i):
                self.arrival_listbox.delete(i)
                new_text = f"{callsign} ({aircraft_data['type']}) - On Approach - RWY {runway}"
                self.arrival_listbox.insert(i, new_text)
                break
                
        # Update status bar
        self.status_bar.config(text=f"Status: {callsign} returning for another approach to Runway {runway}")