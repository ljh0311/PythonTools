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
        # Create frames
        left_frame = ttk.Frame(self.atc_tab, padding="5")
        right_frame = ttk.Frame(self.atc_tab, padding="5")
        
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # Left side - Instruction selection
        ttk.Label(left_frame, text="Instruction Type:").pack(anchor=tk.W, pady=(0, 5))
        
        # Get all instruction types
        instruction_types = self.atc.get_all_instruction_types()
        instruction_var = tk.StringVar()
        
        # Set default instruction
        if instruction_types:
            instruction_var.set(instruction_types[0])
        
        # Instruction type dropdown
        self.instruction_dropdown = ttk.Combobox(
            left_frame, 
            textvariable=instruction_var,
            values=instruction_types,
            state="readonly"
        )
        self.instruction_dropdown.pack(fill=tk.X, pady=(0, 10))
        self.instruction_dropdown.bind("<<ComboboxSelected>>", self.on_instruction_selected)
        
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
        button_frame = ttk.Frame(left_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.generate_btn = ttk.Button(
            button_frame, 
            text="Generate Readback", 
            command=self.generate_readback
        )
        self.generate_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.speak_btn = ttk.Button(
            button_frame, 
            text="Speak ATC", 
            command=self.speak_atc
        )
        self.speak_btn.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(5, 0))
        
        # Right side - Display
        ttk.Label(right_frame, text="ATC Instruction:").pack(anchor=tk.W, pady=(0, 5))
        
        self.instruction_display = scrolledtext.ScrolledText(
            right_frame, 
            height=6, 
            wrap=tk.WORD
        )
        self.instruction_display.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(right_frame, text="Proper Readback:").pack(anchor=tk.W, pady=(0, 5))
        
        self.readback_display = scrolledtext.ScrolledText(
            right_frame, 
            height=6, 
            wrap=tk.WORD
        )
        self.readback_display.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(right_frame, text="Explanation:").pack(anchor=tk.W, pady=(0, 5))
        
        self.explanation_display = scrolledtext.ScrolledText(
            right_frame, 
            height=6, 
            wrap=tk.WORD
        )
        self.explanation_display.pack(fill=tk.BOTH, expand=True)
        
        # Set initial instruction
        if instruction_types:
            self.on_instruction_selected(None)
    
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
                self.instruction_dropdown['values'] = self.atc.get_all_instruction_types()
                
                # Reset the selected instruction
                if self.instruction_dropdown['values']:
                    self.instruction_dropdown.current(0)
                    self.on_instruction_selected(None)
                
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
    
    def on_instruction_selected(self, event):
        """Handle instruction type selection"""
        instruction_type = self.instruction_dropdown.get()
        instruction = self.atc.get_instruction(instruction_type)
        
        if instruction:
            # Clear displays
            self.instruction_display.delete(1.0, tk.END)
            self.readback_display.delete(1.0, tk.END)
            self.explanation_display.delete(1.0, tk.END)
            
            # Show explanation
            self.explanation_display.insert(tk.END, instruction["explanation"])
            
            # Update parameter fields
            self.update_parameter_fields(instruction_type)
    
    def update_parameter_fields(self, instruction_type):
        """Dynamically update parameter entry fields based on instruction type"""
        # Clear existing parameter entries
        for widget in self.param_inner_frame.winfo_children():
            widget.destroy()
        
        self.param_entries = {}
        
        # Get parameters for the selected instruction
        parameters = self.atc.get_parameters_for_instruction(instruction_type)
        
        # Create entry fields for each parameter
        for i, param in enumerate(parameters):
            # Create a friendly display name
            display_name = param.replace('_', ' ').title()
            ttk.Label(self.param_inner_frame, text=f"{display_name}:").grid(row=i, column=0, sticky=tk.W, pady=2)
            
            # For some parameters, we'll use comboboxes with predefined values
            if param == "direction":
                values = ["Left", "Right"]
                if instruction_type == "hold" or instruction_type == "circling_approach":
                    values = ["North", "South", "East", "West"]
                var = tk.StringVar()
                entry = ttk.Combobox(self.param_inner_frame, textvariable=var, values=values, width=20)
                entry.current(0)
            elif param == "climb_descend":
                var = tk.StringVar()
                entry = ttk.Combobox(self.param_inner_frame, textvariable=var, values=["Climb", "Descend"], width=20)
                entry.current(0)
            elif param == "direction_turn":
                var = tk.StringVar()
                entry = ttk.Combobox(self.param_inner_frame, textvariable=var, values=["Right", "Left"], width=20)
                entry.current(0)
            elif param == "approach_type":
                var = tk.StringVar()
                entry = ttk.Combobox(
                    self.param_inner_frame, 
                    textvariable=var, 
                    values=["ILS", "RNAV", "VOR", "NDB", "Visual", "GPS", "Localizer"], 
                    width=20
                )
                entry.current(0)
            else:
                # Use text entry for other parameters
                var = tk.StringVar()
                entry = ttk.Entry(self.param_inner_frame, textvariable=var, width=20)
                
                # Set default values for common parameters
                if param == "callsign":
                    var.set("N123AB")
                elif param == "runway":
                    var.set("27")
                elif param == "altitude":
                    var.set("5000")
                elif param == "heading":
                    var.set("270")
                elif param == "speed":
                    var.set("210")
                elif param == "frequency":
                    var.set("125.5")
                elif param == "wind_direction":
                    var.set("270")
                elif param == "wind_speed":
                    var.set("10")
                elif param == "position":
                    var.set("2")
                elif param == "distance":
                    var.set("3")
                elif param == "destination":
                    var.set("KXYZ")
                elif param == "squawk":
                    var.set("1234")
                elif param == "rate":
                    var.set("1500")
                elif param == "fix":
                    var.set("ALPHA")
                elif param == "facility":
                    var.set("Tower")
                elif param == "taxiways":
                    var.set("A, B, C")
                elif param == "aircraft_type":
                    var.set("Cessna")
                elif param == "setting":
                    var.set("2992")
                elif param == "arrival":
                    var.set("STAR")
            
            entry.grid(row=i, column=1, sticky=tk.EW, pady=2)
            self.param_entries[param] = var
        
        # Configure grid to expand
        self.param_inner_frame.columnconfigure(1, weight=1)
        
        # Update the scrollable region
        self.param_inner_frame.update_idletasks()
        self.param_canvas.configure(scrollregion=self.param_canvas.bbox("all"))
    
    def generate_readback(self):
        """Generate a readback example for the selected instruction"""
        instruction_type = self.instruction_dropdown.get()
        
        # Get parameter values from the entry fields
        params = {}
        for param, var in self.param_entries.items():
            params[param] = var.get()
        
        # Get the instruction and readback
        instruction = self.atc.get_instruction(instruction_type)
        
        if instruction:
            try:
                # Format the instruction and readback
                atc_message = instruction["instruction"].format(**params)
                readback = self.atc.get_readback(instruction_type, **params)
                
                # Display them
                self.instruction_display.delete(1.0, tk.END)
                self.readback_display.delete(1.0, tk.END)
                
                self.instruction_display.insert(tk.END, atc_message)
                self.readback_display.insert(tk.END, readback)
                
                self.status_var.set(f"Generated readback for {instruction_type}")
            except KeyError as e:
                messagebox.showerror("Error", f"Missing parameter: {e}")
    
    def speak_atc(self):
        """Speak the ATC instruction"""
        if not self.config.get("voice_enabled"):
            messagebox.showinfo("Voice Disabled", "Voice playback is disabled in settings.")
            return
            
        atc_text = self.instruction_display.get(1.0, tk.END).strip()
        if atc_text:
            self.speech_engine.speak(atc_text)
            self.status_var.set("Speaking ATC instruction...")
        else:
            messagebox.showinfo("Speak", "No ATC instruction to speak.")
    
    def insert_sample_atis(self):
        """Insert a sample ATIS message"""
        sample_atis = """KXYZ INFORMATION ALPHA. 1430Z. RUNWAY IN USE 27L AND 27R. 
WIND 280 AT 10 KNOTS. VISIBILITY 10 MILES. FEW CLOUDS AT 5000. 
TEMPERATURE 22 DEW POINT 15. ALTIMETER 2992. 
ILS APPROACH IN PROGRESS. BIRDS REPORTED VICINITY OF AIRPORT.
ADVISE YOU HAVE INFORMATION ALPHA ON INITIAL CONTACT. CONTACT TOWER ON 118.7."""
        
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