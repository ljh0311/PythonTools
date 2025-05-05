"""
Role Selection Screen
Allows users to choose between Pilot and ATC roles
"""
import tkinter as tk
from tkinter import ttk
import os
import sys
from PIL import Image, ImageTk

class RoleSelectionScreen:
    def __init__(self, root, on_role_selected):
        self.root = root
        self.on_role_selected = on_role_selected
        
        # Configure the window
        self.root.title("Aviation Assistant - Role Selection")
        self.root.geometry("800x500")
        self.root.minsize(700, 450)
        
        # Set up the main frame
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Setup UI components
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface"""
        # Header
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        ttk.Label(
            header_frame, 
            text="SELECT YOUR ROLE", 
            font=("Arial", 20, "bold")
        ).pack(anchor=tk.CENTER)
        
        ttk.Label(
            header_frame, 
            text="Choose your aviation role to access specialized tools",
            font=("Arial", 12)
        ).pack(anchor=tk.CENTER, pady=(5, 0))
        
        # Roles frame
        roles_frame = ttk.Frame(self.main_frame)
        roles_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        roles_frame.columnconfigure(0, weight=1)
        roles_frame.columnconfigure(1, weight=1)
        
        # Load images or create placeholders
        pilot_img = self.load_role_image("pilot.png", (200, 200))
        atc_img = self.load_role_image("atc.png", (200, 200))
        
        # Pilot role
        pilot_frame = ttk.Frame(roles_frame, padding=10)
        pilot_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=10)
        
        ttk.Label(
            pilot_frame, 
            text="PILOT", 
            font=("Arial", 16, "bold")
        ).pack(anchor=tk.CENTER, pady=(0, 10))
        
        if pilot_img:
            ttk.Label(pilot_frame, image=pilot_img).pack(anchor=tk.CENTER, pady=10)
            # Keep a reference to prevent garbage collection
            pilot_frame.pilot_img = pilot_img
        
        ttk.Label(
            pilot_frame,
            text="Access tools for ATC communications,\nreadbacks, and ATIS information",
            justify=tk.CENTER
        ).pack(anchor=tk.CENTER, pady=10)
        
        ttk.Button(
            pilot_frame,
            text="Select Pilot Role",
            command=lambda: self.on_role_selected("pilot"),
            style="Role.TButton",
            width=20
        ).pack(anchor=tk.CENTER, pady=10)
        
        # ATC role
        atc_frame = ttk.Frame(roles_frame, padding=10)
        atc_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=10)
        
        ttk.Label(
            atc_frame, 
            text="AIR TRAFFIC CONTROL", 
            font=("Arial", 16, "bold")
        ).pack(anchor=tk.CENTER, pady=(0, 10))
        
        if atc_img:
            ttk.Label(atc_frame, image=atc_img).pack(anchor=tk.CENTER, pady=10)
            # Keep a reference to prevent garbage collection
            atc_frame.atc_img = atc_img
        
        ttk.Label(
            atc_frame,
            text="Manage ground, tower, and approach/departure\noperations with aircraft sequencing",
            justify=tk.CENTER
        ).pack(anchor=tk.CENTER, pady=10)
        
        ttk.Button(
            atc_frame,
            text="Select ATC Role",
            command=lambda: self.on_role_selected("atc"),
            style="Role.TButton",
            width=20
        ).pack(anchor=tk.CENTER, pady=10)
        
        # Configure style for role buttons
        style = ttk.Style()
        style.configure("Role.TButton", font=("Arial", 12))
    
    def load_role_image(self, filename, size):
        """Load a role image or create a placeholder if not found"""
        # Create icons directory if it doesn't exist
        if not os.path.exists("icons"):
            os.makedirs("icons")
        
        filepath = os.path.join("icons", filename)
        
        try:
            # Create placeholder image if it doesn't exist
            if not os.path.exists(filepath):
                # Choose colors based on role
                if filename == "pilot.png":
                    color = (0, 91, 187)  # Blue
                else:  # ATC
                    color = (204, 0, 0)   # Red
                
                img = Image.new('RGB', size, color=color)
                
                # Draw an icon-like shape
                from PIL import ImageDraw
                draw = ImageDraw.Draw(img)
                
                if filename == "pilot.png":
                    # Draw a simple aircraft shape
                    width, height = size
                    center_x, center_y = width // 2, height // 2
                    
                    # Wings
                    draw.rectangle(
                        [center_x - 80, center_y - 10, center_x + 80, center_y + 10],
                        fill=(255, 255, 255)
                    )
                    
                    # Fuselage
                    draw.rectangle(
                        [center_x - 15, center_y - 60, center_x + 15, center_y + 60],
                        fill=(255, 255, 255)
                    )
                    
                    # Tail
                    draw.rectangle(
                        [center_x - 30, center_y + 40, center_x + 30, center_y + 60],
                        fill=(255, 255, 255)
                    )
                else:  # ATC
                    # Draw a simple radar/tower shape
                    width, height = size
                    center_x, center_y = width // 2, height // 2
                    
                    # Tower base
                    draw.rectangle(
                        [center_x - 30, center_y, center_x + 30, center_y + 80],
                        fill=(255, 255, 255)
                    )
                    
                    # Tower top
                    draw.rectangle(
                        [center_x - 50, center_y - 20, center_x + 50, center_y],
                        fill=(255, 255, 255)
                    )
                    
                    # Radar dish
                    draw.ellipse(
                        [center_x - 40, center_y - 70, center_x + 40, center_y - 20],
                        outline=(255, 255, 255),
                        width=8
                    )
                
                img.save(filepath)
            
            # Load and resize the image
            img = Image.open(filepath)
            img = img.resize(size, Image.Resampling.LANCZOS)
            
            # Convert to Tkinter PhotoImage
            photo_img = ImageTk.PhotoImage(img)
            return photo_img
            
        except Exception as e:
            print(f"Error loading/creating role image: {e}")
            return None 