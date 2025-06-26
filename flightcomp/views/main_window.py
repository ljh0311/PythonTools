"""
Main GUI Window
Provides the user interface for the ATC Assistant
"""
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import sys
import os

# Add parent directory to path to allow for importing utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.atc_instructions import ATCInstructions, format_readback_example
from utils.atis_decoder import ATISDecoder
from utils.config import Config
from utils.speech import SpeechEngine, AudioPlayer

class MainWindow:
    def __init__(self, root):
        self.root = root
        self.root.title("Pilot ATC Assistant")
        self.root.geometry("900x650")
        self.root.minsize(800, 600)
        
        # Load configuration
        self.config = Config()
        
        # Load airports data from the main config
        self.airports = self.config.get("airports", {})
        
        # Initialize speech engine
        self.speech_engine = SpeechEngine(
            rate=self.config.get("voice_rate"),
            voice_gender="male"
        )
        
        # Initialize audio player
        self.audio_player = AudioPlayer()
        
        # Initialize ATC Instructions with user's settings
        self.atc = ATCInstructions(
            experience_level=self.config.get("experience_level"),
            aircraft_type=self.config.get("aircraft_type")
        )
        
        # Initialize ATIS Decoder
        self.atis_decoder = ATISDecoder(
            experience_level=self.config.get("experience_level")
        )
        
        # Dictionary to store parameter entry widgets
        self.param_entries = {}
        
        # Set up the UI
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the user interface"""
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
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        self.status_bar = ttk.Label(
            self.root, 
            textvariable=self.status_var, 
            anchor=tk.W, 
            relief=tk.SUNKEN
        )
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
    def setup_atc_tab(self):
        """Set up the ATC Instructions tab"""
        # Main frame divided into left and right
        left_frame = ttk.Frame(self.atc_tab, padding=5)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        right_frame = ttk.Frame(self.atc_tab, padding=5)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))

        # --- Left Frame ---
        # Airport Selection
        ttk.Label(left_frame, text="Airport:").pack(anchor=tk.W, pady=(0, 5))
        self.airport_var = tk.StringVar()
        self.airport_combo = ttk.Combobox(
            left_frame,
            textvariable=self.airport_var,
            values=list(self.airports.keys()),
            state="readonly"
        )
        self.airport_combo.pack(fill=tk.X, pady=(0, 10))
        self.airport_combo.bind("<<ComboboxSelected>>", self.on_airport_select)
        if self.airports:
            self.airport_combo.current(0)

        # Instruction type selection
        ttk.Label(left_frame, text="Instruction Type:").pack(anchor=tk.W, pady=(0, 5))
        instruction_var = tk.StringVar()
        instruction_types = self.atc.get_all_instruction_types()
        
        # Set default instruction
        if instruction_types:
            instruction_var.set(instruction_types[0])
        
        # Instruction type dropdown
        self.instruction_type_combo = ttk.Combobox(
            left_frame, 
            textvariable=instruction_var,
            values=instruction_types,
            state="readonly"
        )
        self.instruction_type_combo.pack(fill=tk.X, pady=(0, 10))
        self.instruction_type_combo.bind(
            "<<ComboboxSelected>>", self.on_instruction_select
        )
        
        # Prevent separators from being selected
        def on_combo_select(event):
            selection = self.instruction_type_combo.get()
            if selection.startswith("---"):
                self.instruction_type_combo.set("") # Clear selection or set to previous valid one
                # Or find next valid one
                all_instructions = self.atc.get_all_instruction_types()
                current_index = all_instructions.index(selection)
                if current_index + 1 < len(all_instructions):
                    next_item = all_instructions[current_index + 1]
                    if not next_item.startswith("---"):
                        self.instruction_type_combo.set(next_item)
                        self.on_instruction_select(None) # Manually trigger update
        
        self.instruction_type_combo.bind("<<ComboboxSelected>>", on_combo_select, add=True)
        
        # Parameters frame
        self.param_frame = ttk.LabelFrame(left_frame, text="Parameters", padding="5")
        self.param_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a canvas with scrollbar for parameters
        self.param_canvas = tk.Canvas(self.param_frame)
        self.param_scrollbar = ttk.Scrollbar(self.param_frame, orient="vertical", command=self.param_canvas.yview)
        self.param_canvas.configure(yscrollcommand=self.param_scrollbar.set)
        
        self.param_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.param_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create a frame inside the canvas to hold parameters
        self.param_inner_frame = ttk.Frame(self.param_canvas)
        self.param_canvas.create_window((0, 0), window=self.param_inner_frame, anchor=tk.NW)
        
        # Configure the canvas to resize with the window
        self.param_inner_frame.bind("<Configure>", lambda e: self.param_canvas.configure(
            scrollregion=self.param_canvas.bbox("all"),
            width=self.param_frame.winfo_width() - self.param_scrollbar.winfo_width() - 5
        ))
        
        # Buttons
        bottom_frame = ttk.Frame(left_frame)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))

        self.generate_button = ttk.Button(
            bottom_frame, text="Generate Readback", command=self.generate_readback
        )
        self.generate_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(0, 5))

        self.speak_button = ttk.Button(
            bottom_frame, text="Speak ATC", command=self.speak_atc
        )
        self.speak_button.pack(side=tk.LEFT, expand=True, fill=tk.X, padx=(5, 0))
        
        # --- Right Frame ---
        ttk.Label(right_frame, text="ATC Instruction:").pack(anchor=tk.W, pady=(0, 5))
        
        self.atc_instruction_text = scrolledtext.ScrolledText(
            right_frame, 
            height=6, 
            wrap=tk.WORD
        )
        self.atc_instruction_text.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(right_frame, text="Proper Readback:").pack(anchor=tk.W, pady=(0, 5))
        
        self.readback_text = scrolledtext.ScrolledText(
            right_frame, 
            height=6, 
            wrap=tk.WORD
        )
        self.readback_text.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(right_frame, text="Explanation:").pack(anchor=tk.W, pady=(0, 5))
        
        self.explanation_text = scrolledtext.ScrolledText(
            right_frame, 
            height=6, 
            wrap=tk.WORD
        )
        self.explanation_text.pack(fill=tk.BOTH, expand=True)
        
        # Set initial instruction
        if instruction_types:
            self.on_instruction_select(None)
    
    def setup_atis_tab(self):
        """Set up the ATIS Decoder tab"""
        # Create frames
        top_frame = ttk.Frame(self.atis_tab, padding="5")
        bottom_frame = ttk.Frame(self.atis_tab, padding="5")
        
        top_frame.pack(side=tk.TOP, fill=tk.X)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)
        
        # Top frame - Input
        ttk.Label(top_frame, text="ATIS Message:").pack(anchor=tk.W, pady=(0, 5))
        
        self.atis_input = scrolledtext.ScrolledText(
            top_frame, 
            height=8, 
            wrap=tk.WORD
        )
        self.atis_input.pack(fill=tk.X, pady=(0, 10))
        
        # Sample ATIS button
        self.sample_btn = ttk.Button(
            top_frame, 
            text="Insert Sample ATIS", 
            command=self.insert_sample_atis
        )
        self.sample_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        # Decode button
        self.decode_btn = ttk.Button(
            top_frame, 
            text="Decode ATIS", 
            command=self.decode_atis
        )
        self.decode_btn.pack(side=tk.LEFT, padx=5)
        
        # Clear button
        self.clear_btn = ttk.Button(
            top_frame, 
            text="Clear", 
            command=self.clear_atis
        )
        self.clear_btn.pack(side=tk.LEFT, padx=5)
        
        # Speak button
        self.speak_atis_btn = ttk.Button(
            top_frame, 
            text="Speak ATIS", 
            command=self.speak_atis
        )
        self.speak_atis_btn.pack(side=tk.RIGHT, padx=5)
        
        # Bottom frame - Results
        ttk.Label(bottom_frame, text="Decoded ATIS:").pack(anchor=tk.W, pady=(0, 5))
        
        self.atis_output = scrolledtext.ScrolledText(
            bottom_frame, 
            height=10, 
            wrap=tk.WORD
        )
        self.atis_output.pack(fill=tk.BOTH, expand=True)
    
    def setup_settings_tab(self):
        """Set up the Settings tab"""
        settings_frame = ttk.Frame(self.settings_tab, padding="10")
        settings_frame.pack(fill=tk.BOTH, expand=True)
        
        # Experience level
        ttk.Label(settings_frame, text="Pilot Experience Level:").grid(row=0, column=0, sticky=tk.W, pady=10)
        
        experience_var = tk.StringVar(value=self.config.get("experience_level"))
        experience_options = [
            ("Beginner", "beginner"),
            ("Intermediate", "intermediate"),
            ("Advanced", "advanced")
        ]
        
        exp_frame = ttk.Frame(settings_frame)
        exp_frame.grid(row=0, column=1, sticky=tk.W)
        
        for i, (text, value) in enumerate(experience_options):
            ttk.Radiobutton(
                exp_frame, 
                text=text, 
                variable=experience_var, 
                value=value
            ).grid(row=0, column=i, padx=5)
        
        # Aircraft type
        ttk.Label(settings_frame, text="Aircraft Type:").grid(row=1, column=0, sticky=tk.W, pady=10)
        
        aircraft_var = tk.StringVar(value=self.config.get("aircraft_type"))
        aircraft_options = [
            ("Single Engine", "single_engine"),
            ("Multi Engine", "multi_engine"),
            ("Turboprop", "turboprop"),
            ("Jet", "jet")
        ]
        
        ac_frame = ttk.Frame(settings_frame)
        ac_frame.grid(row=1, column=1, sticky=tk.W)
        
        for i, (text, value) in enumerate(aircraft_options):
            ttk.Radiobutton(
                ac_frame, 
                text=text, 
                variable=aircraft_var, 
                value=value
            ).grid(row=0, column=i, padx=5)
        
        # Voice settings
        ttk.Label(settings_frame, text="Voice Settings:").grid(row=2, column=0, sticky=tk.W, pady=10)
        
        voice_frame = ttk.Frame(settings_frame)
        voice_frame.grid(row=2, column=1, sticky=tk.W)
        
        voice_enabled_var = tk.BooleanVar(value=self.config.get("voice_enabled"))
        ttk.Checkbutton(
            voice_frame, 
            text="Enable Voice", 
            variable=voice_enabled_var
        ).grid(row=0, column=0, padx=5)
        
        ttk.Label(voice_frame, text="Speech Rate:").grid(row=0, column=1, padx=(15, 5))
        
        voice_rate_var = tk.IntVar(value=self.config.get("voice_rate"))
        voice_rate_scale = ttk.Scale(
            voice_frame, 
            from_=80, 
            to=220, 
            variable=voice_rate_var, 
            orient=tk.HORIZONTAL, 
            length=200
        )
        voice_rate_scale.grid(row=0, column=2, padx=5)
        
        voice_rate_label = ttk.Label(voice_frame, text=str(voice_rate_var.get()))
        voice_rate_label.grid(row=0, column=3, padx=5)
        
        def update_rate_label(*args):
            voice_rate_label.config(text=str(int(voice_rate_var.get())))
        
        voice_rate_var.trace_add("write", update_rate_label)
        
        # UI theme
        ttk.Label(settings_frame, text="UI Theme:").grid(row=3, column=0, sticky=tk.W, pady=10)
        
        theme_var = tk.StringVar(value=self.config.get("ui_theme"))
        theme_options = [("Light", "light"), ("Dark", "dark")]
        
        theme_frame = ttk.Frame(settings_frame)
        theme_frame.grid(row=3, column=1, sticky=tk.W)
        
        for i, (text, value) in enumerate(theme_options):
            ttk.Radiobutton(
                theme_frame, 
                text=text, 
                variable=theme_var, 
                value=value
            ).grid(row=0, column=i, padx=5)
        
        # Buttons
        button_frame = ttk.Frame(settings_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=20)
        
        # Save settings callback
        def save_settings():
            self.config.set("experience_level", experience_var.get())
            self.config.set("aircraft_type", aircraft_var.get())
            self.config.set("voice_enabled", voice_enabled_var.get())
            self.config.set("voice_rate", int(voice_rate_var.get()))
            self.config.set("ui_theme", theme_var.get())
            
            if self.config.save_config():
                messagebox.showinfo("Settings", "Settings saved successfully!")
                
                # Update components with new settings
                self.atc = ATCInstructions(
                    experience_level=self.config.get("experience_level"),
                    aircraft_type=self.config.get("aircraft_type")
                )
                
                self.atis_decoder = ATISDecoder(
                    experience_level=self.config.get("experience_level")
                )
                
                self.speech_engine.set_rate(self.config.get("voice_rate"))
                
                # Update instruction dropdown
                self.instruction_type_combo['values'] = self.atc.get_all_instruction_types()
                
                # Reset the selected instruction
                if self.instruction_type_combo['values']:
                    self.instruction_type_combo.current(0)
                    self.on_instruction_select(None)
                
            else:
                messagebox.showerror("Settings", "Failed to save settings!")
        
        ttk.Button(
            button_frame, 
            text="Save Settings", 
            command=save_settings
        ).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(
            button_frame, 
            text="Reset to Defaults", 
            command=self.reset_settings
        ).pack(side=tk.LEFT, padx=5)
        
        # Configure grid to expand
        settings_frame.columnconfigure(1, weight=1)
    
    def on_airport_select(self, event):
        """Handle airport selection change"""
        self.on_instruction_select(None) # Refresh parameters for new airport

    def on_instruction_select(self, event):
        """Handle instruction type selection change"""
        # Clear previous parameter entries by destroying all widgets in the frame
        for widget in self.param_inner_frame.winfo_children():
            widget.destroy()
        self.param_entries.clear()

        # Clear text boxes
        self.atc_instruction_text.delete(1.0, tk.END)
        self.readback_text.delete(1.0, tk.END)
        self.explanation_text.delete(1.0, tk.END)
        
        selected_instruction = self.instruction_type_combo.get()
        if not selected_instruction or selected_instruction.startswith("---"):
            return

        # Get instruction details
        instruction_data = self.atc.get_instruction(selected_instruction)
        if not instruction_data:
            return

        # Populate the explanation box
        self.explanation_text.insert(tk.END, instruction_data.get("explanation", "No explanation available."))

        # Get parameters for the selected instruction
        params = self.atc.get_parameters_for_instruction(selected_instruction)

        # Get data for the currently selected airport
        current_airport_name = self.airport_var.get()
        airport_data = self.airports.get(current_airport_name, {})

        # Create entry fields for each parameter
        for i, param in enumerate(params):
            display_name = param.replace('_', ' ').title()
            
            if param == "taxiways":
                # Create a more complex widget for sequential taxiway selection
                taxiway_container = ttk.LabelFrame(self.param_inner_frame, text="Taxi Route")
                taxiway_container.grid(row=i, column=0, columnspan=2, sticky=tk.EW, pady=5)

                # Data
                available_taxiways = airport_data.get("taxiways", [])
                
                # --- Widgets ---
                # Route display
                current_route_var = tk.StringVar(value="Taxi via: ")
                ttk.Label(taxiway_container, textvariable=current_route_var).pack(anchor=tk.W, padx=5, pady=2)
                
                # Selection UI
                selection_frame = ttk.Frame(taxiway_container)
                selection_frame.pack(fill=tk.X, padx=5, pady=2)

                # Available taxiways list
                ttk.Label(selection_frame, text="Available:").pack(side=tk.LEFT)
                taxiway_list_var = tk.StringVar(value=available_taxiways)
                listbox = tk.Listbox(selection_frame, listvariable=taxiway_list_var, height=4, exportselection=False, width=15)
                listbox.pack(side=tk.LEFT, padx=5)

                # Buttons
                button_frame = ttk.Frame(selection_frame)
                button_frame.pack(side=tk.LEFT, fill=tk.Y, pady=5)
                
                self.param_entries['taxiways'] = [] # Use a list to store the sequence

                def add_taxiway():
                    selected_indices = listbox.curselection()
                    if not selected_indices:
                        return
                    
                    selected_taxiway = available_taxiways[selected_indices[0]]
                    self.param_entries['taxiways'].append(selected_taxiway)
                    
                    route_str = "Taxi via: " + " → ".join(self.param_entries['taxiways'])
                    current_route_var.set(route_str)

                def remove_last_taxiway():
                    if self.param_entries['taxiways']:
                        self.param_entries['taxiways'].pop()
                        route_str = "Taxi via: " + " → ".join(self.param_entries['taxiways'])
                        current_route_var.set(route_str)

                def clear_route():
                    self.param_entries['taxiways'].clear()
                    current_route_var.set("Taxi via: ")

                ttk.Button(button_frame, text="Add →", command=add_taxiway).pack(fill=tk.X, pady=2)
                ttk.Button(button_frame, text="Remove Last", command=remove_last_taxiway).pack(fill=tk.X, pady=2)
                ttk.Button(button_frame, text="Clear", command=clear_route).pack(fill=tk.X, pady=2)

                continue

            var = tk.StringVar()
            entry = None

            # Use comboboxes for parameters with specific options
            if param == "direction":
                if selected_instruction == "Hold":
                    values = ["North", "South", "East", "West", "NE", "NW", "SE", "SW"]
                else:
                    values = ["Left", "Right"]
                entry = ttk.Combobox(self.param_inner_frame, textvariable=var, values=values, width=20)
            elif param == "turn_direction":
                 entry = ttk.Combobox(self.param_inner_frame, textvariable=var, values=["Left", "Right"], width=20)
            elif param == "clock_position":
                entry = ttk.Combobox(self.param_inner_frame, textvariable=var, values=[str(i) for i in range(1, 13)], width=20)
            elif param == "movement":
                entry = ttk.Combobox(self.param_inner_frame, textvariable=var, values=["Northbound", "Southbound", "Eastbound", "Westbound", "Opposite Direction", "Same Direction", "No factor"], width=20)
            elif param == "approach_type":
                entry = ttk.Combobox(self.param_inner_frame, textvariable=var, values=["ILS", "RNAV", "VOR/DME", "Visual"], width=20)
            elif param == "aircraft_type":
                aircraft_options = [
                    # Cessna Aircraft
                    "C152", "C172", "C182", "C206", "C208", "C210", "C310", "C340", "C402", "C414", "C421", "C441", 
                    "C500", "C510", "C525", "C550", "C560", "C650", "C680", "C750", "C850",
                    # Piper Aircraft
                    "PA28", "PA32", "PA34", "PA44", "PA46",
                    # Beechcraft Aircraft
                    "BE20", "BE36", "BE58", "BE60", "BE76", "BE90", "BE99", "BE200", "BE300", "BE350", "BE400", "BE1900",
                    # Boeing Aircraft
                    "B707", "B717", "B727", "B737", "B747", "B757", "B767", "B777", "B787", "B797",
                    # Airbus Aircraft
                    "A220", "A300", "A310", "A318", "A319", "A320", "A321", "A330", "A340", "A350", "A380", "A400M",
                    # Regional Jets
                    "E135", "E140", "E145", "E170", "E175", "E190", "E195", "CRJ1", "CRJ2", "CRJ7", "CRJ9", "CRJ10",
                    # Other Commercial Aircraft
                    "MD80", "MD90", "MD11", "DC9", "DC10", "L1011", "F100", "F70", "F28", "F50", 
                    "ATR42", "ATR72", "DHC8", "SF340", "EMB110", "EMB120", "EMB135", "EMB145", 
                    "EMB170", "EMB175", "EMB190", "EMB195"
                ]
                entry = ttk.Combobox(self.param_inner_frame, textvariable=var, values=aircraft_options, width=20)
            elif param == "destination":
                entry = ttk.Combobox(self.param_inner_frame, textvariable=var, values=list(self.airports.keys()), width=20)
            elif param == "runway":
                entry = ttk.Combobox(self.param_inner_frame, textvariable=var, values=airport_data.get("runways", []), width=20)
            elif param == "frequency":
                 # Use default frequency from airport data if available
                default_freq = airport_data.get("frequencies", {}).get("departure", "121.5")
                var.set(default_freq)
                entry = ttk.Entry(self.param_inner_frame, textvariable=var, width=22)
            else:
                entry = ttk.Entry(self.param_inner_frame, textvariable=var, width=22)

            # Set default values from config first, then airport-specific if available
            defaults = {
                "callsign": "9V-SIA", "runway": "02C", "altitude": "5000",
                "heading": "270", "speed": "210",
                "wind_direction": "270", "wind_speed": "10", "clock_position": "2",
                "distance": "3", "destination": "WSSS", "squawk": "1234",
                "fix": "SELAT", "facility": "Tower",
                "setting": "1013", "aircraft_type": "Boeing 737",
                "movement": "Northbound", "radial": "180", "leg_length": "5",
                "expect_time": "1800Z", "arrival_name": "SELAT1A"
            }
            if not var.get(): # Only set default if not already set by airport data
                if param in defaults:
                    var.set(defaults[param])
            
            # For airport-specific runway and taxiway, if a default is in the list, set it
            if param == "runway" and airport_data.get("runways"):
                var.set(airport_data.get("runways")[0])

            if isinstance(entry, ttk.Combobox) and not var.get() and entry['values']:
                entry.current(0)

            entry.grid(row=i, column=1, sticky=tk.EW, pady=2)
            self.param_entries[param] = var

    def generate_readback(self):
        """Generate and display the readback message"""
        selected_instruction = self.instruction_type_combo.get()
        if not selected_instruction or selected_instruction.startswith("---"):
            messagebox.showwarning(
                "Warning", "Please select a valid instruction type first"
            )
            return

        # Get parameter values from entry fields
        params = {}
        for param, var_or_vars in self.param_entries.items():
            if param == 'taxiways' and isinstance(var_or_vars, list):
                params[param] = " via " + " then ".join(var_or_vars)
            elif hasattr(var_or_vars, 'get'):
                params[param] = var_or_vars.get()
            else:
                params[param] = var_or_vars

        # Get the full instruction and readback
        instruction_data = self.atc.get_instruction(selected_instruction)
        if not instruction_data:
            return
            
        try:
            # Populate the ATC instruction and readback boxes
            atc_text = instruction_data["instruction"].format(**params)
            readback_text = instruction_data["readback"].format(**params)
            
            self.atc_instruction_text.delete(1.0, tk.END)
            self.atc_instruction_text.insert(tk.END, atc_text)
            
            self.readback_text.delete(1.0, tk.END)
            self.readback_text.insert(tk.END, readback_text)

        except KeyError as e:
            messagebox.showerror("Error", f"Missing parameter: {e}")
        except Exception as e:
            messagebox.showerror("Error", f"An error occurred: {e}")
    
    def speak_atc(self):
        """Use text-to-speech to read the ATC instruction"""
        if not self.config.get("voice_enabled"):
            messagebox.showinfo("Voice Disabled", "Voice playback is disabled in settings.")
            return
            
        atc_text = self.atc_instruction_text.get(1.0, tk.END).strip()
        if atc_text:
            self.speech_engine.speak(atc_text)
            self.status_var.set("Speaking ATC instruction...")
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
            decoded, 
            verbose=(self.config.get("experience_level") != "beginner")
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
            messagebox.showinfo("Voice Disabled", "Voice playback is disabled in settings.")
            return
            
        atis_text = self.atis_input.get(1.0, tk.END).strip()
        if atis_text:
            self.speech_engine.speak(atis_text)
            self.status_var.set("Speaking ATIS message...")
        else:
            messagebox.showinfo("Speak", "No ATIS message to speak.")
    
    def reset_settings(self):
        """Reset settings to defaults"""
        if messagebox.askyesno("Reset Settings", "Are you sure you want to reset all settings to defaults?"):
            if self.config.reset_to_defaults():
                messagebox.showinfo("Settings", "Settings reset to defaults. Restart the application for changes to take effect.")
            else:
                messagebox.showerror("Settings", "Failed to reset settings!")


def run_app():
    """Run the application"""
    root = tk.Tk()
    app = MainWindow(root)
    root.mainloop() 