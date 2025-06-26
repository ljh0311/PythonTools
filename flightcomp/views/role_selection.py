"""
Role Selection Screen
Allows users to choose between Pilot and ATC roles
"""
import tkinter as tk
from tkinter import ttk
import os
import sys
from PIL import Image, ImageTk
from PIL import ImageDraw

class RoleSelectionScreen:
    def __init__(self, root, on_role_selected):
        self.root = root
        self.on_role_selected = on_role_selected
        
        # Configure the window
        self.root.title("Aviation Assistant - Role Selection")
        self.root.geometry("800x500")
        self.root.minsize(600, 400) # Adjusted minsize for better scaling
        
        # Bind resize event
        self.root.bind('<Configure>', self.on_window_resize)
        
        # Store original window size for scaling calculations
        self.original_width = 800
        self.original_height = 500
        self.original_font_sizes = {
            'title': 20, 'subtitle': 12, 'role_title': 16,
            'button': 12, 'desc': 10
        }
        self.original_image_size = (200, 200)
        
        # Set up the main frame
        self.main_frame = ttk.Frame(self.root, padding="20")
        self.main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Store UI elements for dynamic scaling
        self.ui_elements = {}
        self.original_pil_images = {}
        self.photo_images = {} # To prevent garbage collection
        
        # Setup UI components
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the user interface"""
        # Header
        header_frame = ttk.Frame(self.main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.ui_elements['title_label'] = ttk.Label(
            header_frame, 
            text="SELECT YOUR ROLE", 
            font=("Arial", self.original_font_sizes['title'], "bold")
        )
        self.ui_elements['title_label'].pack(anchor=tk.CENTER)
        
        self.ui_elements['subtitle_label'] = ttk.Label(
            header_frame, 
            text="Choose your aviation role to access specialized tools",
            font=("Arial", self.original_font_sizes['subtitle'])
        )
        self.ui_elements['subtitle_label'].pack(anchor=tk.CENTER, pady=(5, 0))
        
        # Roles frame
        roles_frame = ttk.Frame(self.main_frame)
        roles_frame.pack(fill=tk.BOTH, expand=True, pady=20)
        roles_frame.columnconfigure(0, weight=1)
        roles_frame.columnconfigure(1, weight=1)
        
        # Load images
        self.original_pil_images["pilot"] = self.load_or_create_pil_image("pilot.png", self.original_image_size)
        self.original_pil_images["atc"] = self.load_or_create_pil_image("atc.png", self.original_image_size)

        # Create initial PhotoImage objects
        self.photo_images['pilot'] = ImageTk.PhotoImage(self.original_pil_images["pilot"])
        self.photo_images['atc'] = ImageTk.PhotoImage(self.original_pil_images["atc"])
        
        # Pilot role
        pilot_frame = ttk.Frame(roles_frame, padding=10)
        pilot_frame.grid(row=0, column=0, sticky=tk.NSEW, padx=10)
        
        self.ui_elements['pilot_title'] = ttk.Label(
            pilot_frame, 
            text="PILOT", 
            font=("Arial", self.original_font_sizes['role_title'], "bold")
        )
        self.ui_elements['pilot_title'].pack(anchor=tk.CENTER, pady=(0, 10))
        
        self.ui_elements['pilot_image'] = ttk.Label(pilot_frame, image=self.photo_images['pilot'])
        self.ui_elements['pilot_image'].pack(anchor=tk.CENTER, pady=10)
        
        self.ui_elements['pilot_desc'] = ttk.Label(
            pilot_frame,
            text="Access tools for ATC communications, readbacks, and ATIS information",
            justify=tk.CENTER,
            font=("Arial", self.original_font_sizes['desc'])
        )
        self.ui_elements['pilot_desc'].pack(anchor=tk.CENTER, pady=10)
        
        self.ui_elements['pilot_button'] = ttk.Button(
            pilot_frame,
            text="Select Pilot Role",
            command=lambda: self.on_role_selected("pilot"),
            style="Role.TButton",
            width=20
        )
        self.ui_elements['pilot_button'].pack(anchor=tk.CENTER, pady=10)
        
        # ATC role
        atc_frame = ttk.Frame(roles_frame, padding=10)
        atc_frame.grid(row=0, column=1, sticky=tk.NSEW, padx=10)
        
        self.ui_elements['atc_title'] = ttk.Label(
            atc_frame, 
            text="AIR TRAFFIC CONTROL", 
            font=("Arial", self.original_font_sizes['role_title'], "bold")
        )
        self.ui_elements['atc_title'].pack(anchor=tk.CENTER, pady=(0, 10))
        
        self.ui_elements['atc_image'] = ttk.Label(atc_frame, image=self.photo_images['atc'])
        self.ui_elements['atc_image'].pack(anchor=tk.CENTER, pady=10)
        
        self.ui_elements['atc_desc'] = ttk.Label(
            atc_frame,
            text="Manage ground, tower, and approach/departure operations with aircraft sequencing",
            justify=tk.CENTER,
            font=("Arial", self.original_font_sizes['desc'])
        )
        self.ui_elements['atc_desc'].pack(anchor=tk.CENTER, pady=10)
        
        self.ui_elements['atc_button'] = ttk.Button(
            atc_frame,
            text="Select ATC Role",
            command=lambda: self.on_role_selected("atc"),
            style="Role.TButton",
            width=20
        )
        self.ui_elements['atc_button'].pack(anchor=tk.CENTER, pady=10)
        
        # Configure style for role buttons
        style = ttk.Style()
        style.configure("Role.TButton", font=("Arial", self.original_font_sizes['button']))
    
    def on_window_resize(self, event):
        """Handle window resize events"""
        if event.widget != self.root:
            return

        current_width = self.root.winfo_width()
        current_height = self.root.winfo_height()
        
        width_scale = current_width / self.original_width
        height_scale = current_height / self.original_height
        scale_factor = min(width_scale, height_scale)
        
        self.update_fonts(scale_factor)
        self.update_images(scale_factor)
        self.update_layout(scale_factor)
    
    def update_fonts(self, scale_factor):
        """Update font sizes based on scale factor"""
        scale_factor = max(0.5, min(scale_factor, 1.5))
        
        for key, original_size in self.original_font_sizes.items():
            new_size = int(original_size * scale_factor)
            
            try:
                if key == 'title' and 'title_label' in self.ui_elements:
                    self.ui_elements['title_label'].configure(font=("Arial", new_size, "bold"))
                elif key == 'subtitle' and 'subtitle_label' in self.ui_elements:
                    self.ui_elements['subtitle_label'].configure(font=("Arial", new_size))
                elif key == 'role_title':
                    if 'pilot_title' in self.ui_elements:
                        self.ui_elements['pilot_title'].configure(font=("Arial", new_size, "bold"))
                    if 'atc_title' in self.ui_elements:
                        self.ui_elements['atc_title'].configure(font=("Arial", new_size, "bold"))
                elif key == 'button':
                    style = ttk.Style()
                    style.configure("Role.TButton", font=("Arial", new_size))
                elif key == 'desc':
                    if 'pilot_desc' in self.ui_elements:
                        self.ui_elements['pilot_desc'].configure(font=("Arial", new_size))
                    if 'atc_desc' in self.ui_elements:
                        self.ui_elements['atc_desc'].configure(font=("Arial", new_size))
            except tk.TclError:
                # Widget may have been destroyed, ignore the error
                pass

    def update_images(self, scale_factor):
        """Resize and update images based on scale factor"""
        scale_factor = max(0.5, min(scale_factor, 1.5))
        new_width = int(self.original_image_size[0] * scale_factor)
        new_height = int(self.original_image_size[1] * scale_factor)

        if new_width < 1 or new_height < 1: return

        for role in ["pilot", "atc"]:
            try:
                if role in self.original_pil_images and f'{role}_image' in self.ui_elements:
                    resized_img = self.original_pil_images[role].resize(
                        (new_width, new_height), Image.Resampling.LANCZOS)
                    
                    self.photo_images[role] = ImageTk.PhotoImage(resized_img)
                    self.ui_elements[f'{role}_image'].configure(image=self.photo_images[role])
            except tk.TclError:
                # Widget may have been destroyed, ignore the error
                pass

    def update_layout(self, scale_factor):
        """Update padding, spacing, and text wrapping."""
        scale_factor = max(0.5, min(scale_factor, 1.5))

        try:
            padding = int(20 * scale_factor)
            self.main_frame.configure(padding=padding)
            
            role_padding = int(10 * scale_factor)
            
            if 'pilot_title' in self.ui_elements and 'atc_title' in self.ui_elements:
                pilot_frame = self.ui_elements['pilot_title'].master
                atc_frame = self.ui_elements['atc_title'].master
                
                pilot_frame.configure(padding=role_padding)
                atc_frame.configure(padding=role_padding)

                # Update wraplength for description labels
                frame_width = pilot_frame.winfo_width()
                if frame_width > 20: # Ensure there's enough space
                    wraplength = frame_width - int(20 * scale_factor)
                    if 'pilot_desc' in self.ui_elements:
                        self.ui_elements['pilot_desc'].configure(wraplength=wraplength)
                    if 'atc_desc' in self.ui_elements:
                        self.ui_elements['atc_desc'].configure(wraplength=wraplength)
        except tk.TclError:
            # Widget may have been destroyed, ignore the error
            pass

    def load_or_create_pil_image(self, filename, size):
        """Load a role image or create a placeholder, returns a PIL image."""
        if not os.path.exists("icons"):
            os.makedirs("icons")
        
        filepath = os.path.join("icons", filename)
        
        try:
            if not os.path.exists(filepath):
                # Create placeholder image
                color = (0, 91, 187) if "pilot" in filename else (204, 0, 0)
                img = Image.new('RGB', size, color=color)
                draw = ImageDraw.Draw(img)
                
                if "pilot" in filename:
                    w, h = size; cx, cy = w//2, h//2
                    draw.rectangle([cx-80, cy-10, cx+80, cy+10], fill="white")
                    draw.rectangle([cx-15, cy-60, cx+15, cy+60], fill="white")
                    draw.rectangle([cx-30, cy+40, cx+30, cy+60], fill="white")
                else: # ATC
                    w, h = size; cx, cy = w//2, h//2
                    draw.rectangle([cx-30, cy, cx+30, cy+80], fill="white")
                    draw.rectangle([cx-50, cy-20, cx+50, cy], fill="white")
                    draw.ellipse([cx-40, cy-70, cx+40, cy-20], outline="white", width=8)

                img.save(filepath)
            
            return Image.open(filepath)
            
        except Exception as e:
            print(f"Error loading/creating PIL image: {e}")
            return Image.new('RGB', size, color="grey") 