#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
The Eyes - GUI Application

This module implements the main GUI application for The Eyes system.
"""

import os
import sys
import time
import json
import logging
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, filedialog
from PIL import Image, ImageTk  # Needed for image processing
import threading  # Needed for camera thread
import cv2  # OpenCV for camera handling
import psutil  # Added import for system monitoring

# Try to import optional modules
try:
    import numpy as np
    from matplotlib.figure import Figure
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

# Import project modules
from .camera.camera_manager import CameraManager
from .utils.config import load_config
from .gui.components.camera_view import CameraView
from .security.motion_detector import MotionDetector, MotionDetectionMethod
from .security.recorder import VideoRecorder
from .security.alert_manager import AlertManager, AlertType, AlertLevel

# After imports and before class TheEyesGUI declaration, add:

class ToolTip:
    """Create a tooltip for a given widget."""
    
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    
    def show_tooltip(self, event=None):
        """Show the tooltip."""
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 5
        
        # Create toplevel window
        self.tooltip_window = tk.Toplevel(self.widget)
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        # Create tooltip content
        label = tk.Label(
            self.tooltip_window, 
            text=self.text, 
            justify=tk.LEFT,
            background="#ffffe0", 
            relief=tk.SOLID, 
            borderwidth=1,
            font=("Segoe UI", 9)
        )
        label.pack(padx=2, pady=2)
    
    def hide_tooltip(self, event=None):
        """Hide the tooltip."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class TheEyesGUI(tk.Tk):
    """Main GUI application for The Eyes."""
    
    def __init__(self):
        """Initialize the application."""
        super().__init__()
        
        # Set up logging
        self.logger = logging.getLogger("the_eyes.gui")
        
        # Set up the application window
        self.title("The Eyes - Home Surveillance")
        self.geometry("1024x768")
        
        # Configure styles before creating UI components
        self.configure_styles()
        
        # Initialize data attributes
        self.camera_manager = None
        self.update_thread = None
        self.is_running = False
        self.camera_views = {}
        self.cameras_initialized = False
        self.current_scene = None
        self.is_ui_setup_complete = False
        self.style = None  # Will be initialized in configure_styles
        
        # Initialize app_config with a default value to prevent None errors
        self.app_config = {"cameras": {}}
        
        # Memory management settings
        self.last_gc_time = time.time()
        self.gc_interval = 60  # Run garbage collection every 60 seconds
        
        # Add system monitoring
        self.system_stats = {
            'cpu': 0,
            'memory': 0,
            'fps': {}
        }
        
        # Start system monitoring
        self.start_system_monitoring()
        
        # Load configuration
        try:
            config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                    "config", "config.json")
            loaded_config = load_config(config_path)
            if loaded_config is not None:
                self.app_config = loaded_config
            self.logger.info(f"Loaded configuration from {config_path}")
        except Exception as e:
            self.logger.error(f"Failed to load configuration: {e}")
            # Keep the default app_config initialized above
        
        # Ensure app_config is never None and has required structure
        if self.app_config is None:
            self.app_config = {"cameras": {}}
        
        # Ensure all required keys exist
        if "cameras" not in self.app_config:
            self.app_config["cameras"] = {}
        if "appearance" not in self.app_config:
            self.app_config["appearance"] = {"dark_mode": False}
        if "display" not in self.app_config:
            self.app_config["display"] = {"show_fps": True}
        if "system" not in self.app_config:
            self.app_config["system"] = {"fps_limit": 30}
        
        # Set up paths
        self.scenes_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                "config", "scenes.json")
        self.screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                    "screenshots")
        os.makedirs(self.screenshots_dir, exist_ok=True)
        
        # Load camera scenes
        try:
            self.scenes = self.load_scenes()
            if self.scenes and len(self.scenes) > 0:
                self.current_scene = self.scenes[0]  # Use first scene as default
        except Exception as e:
            self.logger.error(f"Failed to load scenes: {e}")
            self.scenes = []
            # Add a default scene if none exists
            default_scene = {
                "name": "Default Scene",
                "description": "Default camera configuration",
                "cameras": {}
            }
            self.scenes.append(default_scene)
            self.current_scene = default_scene
        
        # Set up UI components
        self.setup_ui()
        
        # Initialize camera manager
        try:
            self.camera_manager = CameraManager(self.app_config.get("cameras", {}))
            self.logger.info("Camera manager initialized")
            self.cameras_initialized = True
        except Exception as e:
            self.logger.error(f"Failed to initialize camera manager: {e}")
            messagebox.showerror("Camera Error", f"Failed to initialize cameras: {e}")
        
        # Initialize security components
        self.motion_detectors = {}  # Per-camera motion detectors
        self.recorder = None
        self.alert_manager = None
        self._initialize_security_components()
        
        # Start camera views
        if self.cameras_initialized:
            self.start_camera_views()
        
        # Set up window close handler
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        
        # Set up periodic cleanup
        self.after(self.gc_interval * 1000, self.perform_cleanup)
    
    def configure_styles(self):
        """Configure application styles."""
        # Create a style instance
        self.style = ttk.Style(self)
        
        # Try to use a modern theme if available
        try:
            self.style.theme_use('clam')  # Use clam theme as base
        except Exception as e:
            self.logger.warning(f"Could not set 'clam' theme, using default: {str(e)}")
        
        # Check if we should use dark mode from config
        if hasattr(self, 'app_config') and isinstance(self.app_config, dict) and self.app_config is not None:
            self.dark_mode = self.app_config.get('appearance', {}).get('dark_mode', False)
        else:
            self.dark_mode = False
            self.app_config = {'appearance': {'dark_mode': False}}
        
        # Define colors based on mode
        if self.dark_mode:
            bg_color = '#2d2d2d'
            fg_color = '#e0e0e0'
            accent_color = '#3498db'
            highlight_color = '#4a6da7'
            warning_color = '#e67e22'
            error_color = '#e74c3c'
            success_color = '#2ecc71'
        else:
            bg_color = '#f8f9fa'
            fg_color = '#2c3e50'
            accent_color = '#3498db' 
            highlight_color = '#4a6da7'
            warning_color = '#e67e22'
            error_color = '#e74c3c'
            success_color = '#2ecc71'
        
        # Store colors for later use
        self.ui_colors = {
            'bg': bg_color,
            'fg': fg_color,
            'accent': accent_color,
            'highlight': highlight_color,
            'warning': warning_color,
            'error': error_color,
            'success': success_color
        }
        
        # Configure common styles
        self.style.configure('TLabel', font=('Segoe UI', 10), background=bg_color, foreground=fg_color)
        self.style.configure('TButton', font=('Segoe UI', 10))
        self.style.configure('TEntry', font=('Segoe UI', 10))
        self.style.configure('TFrame', background=bg_color)
        self.style.configure('TNotebook', background=bg_color)
        self.style.configure('TNotebook.Tab', background=bg_color, foreground=fg_color)
        
        # Header style
        self.style.configure('Header.TLabel', font=('Segoe UI', 16, 'bold'), foreground=fg_color, background=bg_color)
        
        # Subheader style
        self.style.configure('SubHeader.TLabel', font=('Segoe UI', 12, 'bold'), foreground=fg_color, background=bg_color)
        
        # Action button style
        self.style.configure('Action.TButton', font=('Segoe UI', 10, 'bold'))
        
        # Status indicator styles
        self.style.configure('Active.TLabel', foreground=success_color, background=bg_color)
        self.style.configure('Inactive.TLabel', foreground=error_color, background=bg_color)
        self.style.configure('Warning.TLabel', foreground=warning_color, background=bg_color)
        
        # Tab styling
        self.style.map('TNotebook.Tab', 
                     background=[('selected', accent_color)], 
                     foreground=[('selected', 'white')])
        
        # Status bar style
        self.style.configure('Status.TLabel', font=('Segoe UI', 9), padding=3, 
                            background='#333333' if self.dark_mode else '#f0f0f0',
                            foreground='#ffffff' if self.dark_mode else '#333333')
        
        # Set window background
        self.configure(background=bg_color)
        
        # Add a toggle for dark/light mode in the menu
        self._create_theme_menu()

    def _create_theme_menu(self):
        """Create a menu with appearance options."""
        # Create main menu bar if it doesn't exist
        if not hasattr(self, 'menu_bar'):
            self.menu_bar = tk.Menu(self)
            self.config(menu=self.menu_bar)
        
        # Create appearance menu
        self.appearance_menu = tk.Menu(self.menu_bar, tearoff=0)
        
        # Add dark mode toggle
        self.dark_mode_var = tk.BooleanVar(value=self.dark_mode)
        self.appearance_menu.add_checkbutton(
            label="Dark Mode",
            variable=self.dark_mode_var,
            command=self.toggle_dark_mode
        )
        
        # Add appearance menu to menu bar
        self.menu_bar.add_cascade(label="Appearance", menu=self.appearance_menu)

    def toggle_dark_mode(self):
        """Toggle between dark and light mode."""
        # Update dark mode setting
        self.dark_mode = self.dark_mode_var.get()
        
        # Save to config
        if 'appearance' not in self.app_config:
            self.app_config['appearance'] = {}
        self.app_config['appearance']['dark_mode'] = self.dark_mode
        
        # Reconfigure styles
        self.configure_styles()
        
        # Update all existing frames
        self._update_widget_colors(self)
        
        # Log the change
        self.logger.info(f"Changed to {'dark' if self.dark_mode else 'light'} mode")
        
        # Update the status bar
        self.status_bar.config(text=f"Switched to {'dark' if self.dark_mode else 'light'} mode")

    def _update_widget_colors(self, parent):
        """Recursively update widget colors for dark/light mode."""
        for widget in parent.winfo_children():
            # Update specific widget types
            if isinstance(widget, tk.Canvas):
                if not widget.winfo_class() in ('Canvas'):
                    continue
                # Only change background for canvases not used for camera display
                parent_name = widget.winfo_parent()
                if parent_name and 'camera' not in parent_name.lower():
                    widget.configure(background=self.ui_colors['bg'])
            
            # Recursively update children
            if widget.winfo_children():
                self._update_widget_colors(widget)
    
    def setup_ui(self):
        """Set up the main UI components."""
        # Status bar at the bottom
        self.status_bar = ttk.Label(self, text="Ready", relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Main notebook for tabs
        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add tabs
        self.monitoring_tab = ttk.Frame(self.notebook)
        self.settings_tab = ttk.Frame(self.notebook)
        self.scenes_tab = ttk.Frame(self.notebook)
        self.visualization_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.monitoring_tab, text="Monitoring")
        self.notebook.add(self.settings_tab, text="Camera Settings")
        self.notebook.add(self.scenes_tab, text="Scenes")
        self.notebook.add(self.visualization_tab, text="Visualization")
        
        # Set up tabs
        self.setup_monitoring_tab()
        
        # First set up scenes, as settings depend on scene data
        self.setup_scenes_tab()
        
        # Then set up settings which uses scene data
        self.setup_settings_tab()
        
        # Set up simple placeholder for visualization tab
        # This will be replaced with proper implementation later
        viz_label = ttk.Label(self.visualization_tab, 
                             text="Visualization features coming soon!", 
                             font=('Segoe UI', 14))
        viz_label.pack(expand=True, pady=50)
    
    def setup_monitoring_tab(self):
        """Set up the monitoring tab."""
        # Top control panel
        control_frame = ttk.Frame(self.monitoring_tab)
        control_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Left controls
        left_controls = ttk.Frame(control_frame)
        left_controls.pack(side=tk.LEFT, fill=tk.Y)
        
        # Scan button with improved styling
        scan_button = ttk.Button(left_controls, text="Scan for Cameras", 
                               command=self.scan_for_cameras, style='Action.TButton')
        scan_button.pack(side=tk.LEFT, padx=(5, 10), pady=5)
        ToolTip(scan_button, "Scan your system for connected cameras")
        
        # Camera count with improved styling
        self.camera_count_label = ttk.Label(left_controls, text="No cameras connected")
        self.camera_count_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Right controls
        right_controls = ttk.Frame(control_frame)
        right_controls.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Display options
        display_frame = ttk.Frame(right_controls)
        display_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Layout options with presets
        ttk.Label(display_frame, text="Layout:").pack(side=tk.LEFT, padx=2)
        
        self.layout_var = tk.StringVar(value="auto")
        layout_combobox = ttk.Combobox(display_frame, 
                                     textvariable=self.layout_var,
                                     values=["auto", "1x1", "2x2", "3x3", "4x4", "horizontal", "vertical", "single"],
                                     state="readonly",
                                     width=10)
        layout_combobox.pack(side=tk.LEFT, padx=5)
        layout_combobox.bind("<<ComboboxSelected>>", self.update_camera_layout)
        ToolTip(layout_combobox, "Change how cameras are arranged (auto adapts to camera count)")
        
        # Camera filter
        filter_frame = ttk.Frame(right_controls)
        filter_frame.pack(side=tk.LEFT, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=2)
        
        self.camera_filter_var = tk.StringVar(value="all")
        self.filter_combobox = ttk.Combobox(filter_frame, 
                                         textvariable=self.camera_filter_var,
                                         values=["all"],
                                         state="readonly",
                                         width=10)
        self.filter_combobox.pack(side=tk.LEFT, padx=5)
        self.filter_combobox.bind("<<ComboboxSelected>>", self.update_camera_filter)
        
        # Add screenshot button on the right
        screenshot_button = ttk.Button(right_controls, text="Take Screenshot", 
                                     command=self.take_screenshot)
        screenshot_button.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Create a separator
        separator = ttk.Separator(self.monitoring_tab, orient=tk.HORIZONTAL)
        separator.pack(fill=tk.X, padx=5, pady=2)
        
        # Create frame for camera views with border
        camera_container = ttk.LabelFrame(self.monitoring_tab, text="Camera Feeds")
        camera_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create a frame inside the container for the camera views
        self.camera_frame = ttk.Frame(camera_container)
        self.camera_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create frames for each camera
        self.camera_views = {}
        
        # Initialize camera views using the layout system
        if self.camera_manager and self.camera_manager.cameras:
            # Use the update_camera_layout method to create views with proper layout
            self.update_camera_layout()
            num_cameras = len(self.camera_manager.cameras)
            self.camera_count_label.config(text=f"{num_cameras} camera(s) connected")
        else:
            # No cameras available
            no_cam_label = ttk.Label(self.camera_frame, text="No cameras available", 
                                   font=('Segoe UI', 12), foreground="#888888")
            no_cam_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
    
    def setup_settings_tab(self):
        """Set up the settings tab."""
        # Safety check to ensure app_config is never None
        if self.app_config is None:
            self.app_config = {"cameras": {}}
        
        # Create a main frame for the settings tab
        settings_frame = ttk.Frame(self.settings_tab)
        settings_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add header
        header = ttk.Label(settings_frame, text="Camera Settings", style='Header.TLabel')
        header.pack(anchor=tk.W, pady=(0, 10))
        
        # Split settings into camera selection and camera settings
        settings_pane = ttk.PanedWindow(settings_frame, orient=tk.HORIZONTAL)
        settings_pane.pack(fill=tk.BOTH, expand=True)
        
        # Left side - Camera list
        camera_list_frame = ttk.Frame(settings_pane)
        settings_pane.add(camera_list_frame, weight=1)
        
        # Camera list label
        cameras_label = ttk.Label(camera_list_frame, text="Cameras", style='SubHeader.TLabel')
        cameras_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Camera selection frame
        camera_select_frame = ttk.Frame(camera_list_frame)
        camera_select_frame.pack(fill=tk.X, pady=5)
        
        # Camera dropdown
        self.camera_selector_label = ttk.Label(camera_select_frame, text="Select Camera:")
        self.camera_selector_label.pack(side=tk.LEFT, padx=(0, 5))
        
        # Get camera IDs
        if self.app_config is None:
            self.app_config = {"cameras": {}}
        
        # Ensure cameras key exists and is a dictionary
        if "cameras" not in self.app_config or self.app_config["cameras"] is None:
            self.app_config["cameras"] = {}
        
        camera_ids = list(self.app_config["cameras"].keys())
        if not camera_ids:
            camera_ids = ["No cameras configured"]
        
        self.camera_selector = ttk.Combobox(camera_select_frame, values=camera_ids, width=15, state="readonly")
        self.camera_selector.pack(side=tk.LEFT, padx=5)
        if camera_ids:
            self.camera_selector.current(0)
        
        # When selection changes, update settings
        self.camera_selector.bind("<<ComboboxSelected>>", lambda e: self.load_camera_settings())
        
        # Camera list
        camera_tree_frame = ttk.Frame(camera_list_frame)
        camera_tree_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create a treeview for camera status
        self.camera_tree = ttk.Treeview(camera_tree_frame, columns=("Status",), 
                                      show="headings", height=10)
        self.camera_tree.heading("Status", text="Status")
        self.camera_tree.column("Status", width=100)
        self.camera_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add scrollbar
        tree_scrollbar = ttk.Scrollbar(camera_tree_frame, orient="vertical", 
                                     command=self.camera_tree.yview)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.camera_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        # Add cameras to the tree
        for camera_id in camera_ids:
            if camera_id != "No cameras configured":
                self.camera_tree.insert("", "end", text=camera_id, values=("Offline",), tags=(camera_id,))
        
        # Right side - Camera settings
        camera_settings_frame = ttk.Frame(settings_pane)
        settings_pane.add(camera_settings_frame, weight=2)
        
        # Create a notebook for different settings categories
        settings_notebook = ttk.Notebook(camera_settings_frame)
        settings_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs for different setting categories
        general_tab = ttk.Frame(settings_notebook)
        position_tab = ttk.Frame(settings_notebook)
        advanced_tab = ttk.Frame(settings_notebook)
        
        settings_notebook.add(general_tab, text="General")
        settings_notebook.add(position_tab, text="Position & Orientation")
        settings_notebook.add(advanced_tab, text="Advanced")
        
        # Set up general settings tab
        self.setup_general_settings(general_tab)
        
        # Set up position settings tab
        self.setup_position_settings(position_tab)
        
        # Set up advanced settings tab
        self.setup_advanced_settings(advanced_tab)
        
        # Set up position visualization
        self.setup_position_visualization()
        
        # Now that all UI elements including position entries are set up, update the visualization
        # We'll use a flag to check if all components are initialized to avoid early visualization
        self.is_ui_setup_complete = True
        try:
            self.update_position_visualization()
        except Exception as e:
            self.logger.warning(f"Could not initialize position visualization: {e}")
            # Continue without failing - the visualization will be updated when needed
    
    def setup_position_visualization(self):
        """Set up the 3D visualization for camera positions."""
        try:
            # Import matplotlib-related modules
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg, NavigationToolbar2Tk
            import numpy as np
            
            vis_frame = ttk.LabelFrame(self.settings_tab, text="Camera Position Visualization")
            vis_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
            
            # Controls and view options
            control_frame = ttk.Frame(vis_frame)
            control_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # View selector
            view_label = ttk.Label(control_frame, text="View:")
            view_label.pack(side=tk.LEFT, padx=(0, 5))
            
            self.view_var = tk.StringVar(value="3D")
            self.view_selector = ttk.Combobox(control_frame, textvariable=self.view_var, 
                                            values=["3D", "Top Down (XY)", "Front (XZ)", "Side (YZ)"],
                                            width=15, state="readonly")
            self.view_selector.pack(side=tk.LEFT, padx=5)
            
            # When view changes, update the visualization
            self.view_selector.bind("<<ComboboxSelected>>", lambda e: self.update_view())
            
            # Reset view button
            reset_button = ttk.Button(control_frame, text="Reset View", 
                                    command=lambda: self.reset_view())
            reset_button.pack(side=tk.LEFT, padx=5)
            
            # Create matplotlib figure for 3D visualization
            fig = Figure(figsize=(5, 4), dpi=100)
            self.ax = fig.add_subplot(111, projection='3d')
            
            # Create a frame for the canvas
            canvas_frame = ttk.Frame(vis_frame)
            canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            # Create the matplotlib canvas
            self.canvas = FigureCanvasTkAgg(fig, master=canvas_frame)
            self.canvas.draw()
            self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Add navigation toolbar
            toolbar_frame = ttk.Frame(vis_frame)
            toolbar_frame.pack(fill=tk.X, padx=10, pady=(0, 5))
            
            toolbar = NavigationToolbar2Tk(self.canvas, toolbar_frame)
            toolbar.update()
            
            # Initial setup is complete for visualization
            self.logger.info("Position visualization set up successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to set up position visualization: {e}")
            error_label = ttk.Label(self.settings_tab, 
                               text="Error setting up 3D visualization. Matplotlib may not be installed.",
                               foreground="red")
            error_label.pack(pady=20)
            
            # Create empty attributes to prevent errors
            self.ax = None
            self.canvas = None
            self.view_var = None
    
    def reset_view(self):
        """Reset the 3D visualization view to default."""
        if hasattr(self, 'ax'):
            # Reset the view to default
            self.ax.view_init(elev=30, azim=-60)
            
            # Reset limits
            self.ax.set_xlim(-10, 10)
            self.ax.set_ylim(-10, 10)
            self.ax.set_zlim(-10, 10)
            
            # Update the canvas
            self.canvas.draw()
            
            # Reset view selector to 3D
            if hasattr(self, 'view_var'):
                self.view_var.set("3D")
            
            self.logger.debug("Reset position visualization view")

    def update_view(self):
        """Update the visualization view based on selected view type."""
        if not hasattr(self, 'ax') or not hasattr(self, 'view_var'):
            return
            
        view = self.view_var.get()
        
        # Clear current view
        self.ax.clear()
        
        # Set up the view based on selection
        if view == "Top Down (XY)":
            self.ax.view_init(elev=90, azim=-90)  # Looking from top
            self.ax.set_title('Top Down View (XY Plane)')
        elif view == "Front (XZ)":
            self.ax.view_init(elev=0, azim=-90)  # Looking from front
            self.ax.set_title('Front View (XZ Plane)')
        elif view == "Side (YZ)":
            self.ax.view_init(elev=0, azim=0)  # Looking from side
            self.ax.set_title('Side View (YZ Plane)')
        else:  # 3D view
            self.ax.view_init(elev=30, azim=-60)  # Default 3D view
            self.ax.set_title('3D View')
        
        # Set labels and limits
        self.ax.set_xlabel('X (m)')
        self.ax.set_ylabel('Y (m)')
        self.ax.set_zlabel('Z (m)')
        self.ax.set_xlim(-10, 10)
        self.ax.set_ylim(-10, 10)
        self.ax.set_zlim(-10, 10)
        
        # Update visualization with new view
        self.update_position_visualization(redraw_only=True)
        
        self.logger.debug(f"Changed visualization view to: {view}")
    
    def setup_general_settings(self, tab):
        """Set up the general settings tab."""
        # Add general settings content
        pass
    
    def setup_position_settings(self, tab):
        """Set up the position settings tab."""
        # Add position settings content
        # Create a frame for position settings
        position_frame = ttk.Frame(tab, padding=10)
        position_frame.pack(fill=tk.BOTH, expand=True)
        
        # Position section
        pos_label = ttk.Label(position_frame, text="Camera Position", style='SubHeader.TLabel')
        pos_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Create X position controls
        x_frame = ttk.Frame(position_frame)
        x_frame.pack(fill=tk.X, pady=5)
        
        x_label = ttk.Label(x_frame, text="X Position (m):", width=15)
        x_label.pack(side=tk.LEFT)
        
        x_entry = ttk.Entry(x_frame, width=8)
        x_entry.pack(side=tk.LEFT, padx=5)
        x_entry.insert(0, "0.0")
        
        x_slider = ttk.Scale(x_frame, from_=-10.0, to=10.0, orient=tk.HORIZONTAL)
        x_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        x_slider.set(0.0)
        
        # Store the entry and slider as a dictionary under self.x_position
        self.x_position = {'entry': x_entry, 'slider': x_slider}
        
        # Connect the slider to update the entry
        x_slider.configure(command=lambda v: self._update_position_entry('x_position', v))
        
        # Create Y position controls
        y_frame = ttk.Frame(position_frame)
        y_frame.pack(fill=tk.X, pady=5)
        
        y_label = ttk.Label(y_frame, text="Y Position (m):", width=15)
        y_label.pack(side=tk.LEFT)
        
        y_entry = ttk.Entry(y_frame, width=8)
        y_entry.pack(side=tk.LEFT, padx=5)
        y_entry.insert(0, "0.0")
        
        y_slider = ttk.Scale(y_frame, from_=-10.0, to=10.0, orient=tk.HORIZONTAL)
        y_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        y_slider.set(0.0)
        
        # Store the entry and slider as a dictionary under self.y_position
        self.y_position = {'entry': y_entry, 'slider': y_slider}
        
        # Connect the slider to update the entry
        y_slider.configure(command=lambda v: self._update_position_entry('y_position', v))
        
        # Create Z position controls
        z_frame = ttk.Frame(position_frame)
        z_frame.pack(fill=tk.X, pady=5)
        
        z_label = ttk.Label(z_frame, text="Z Position (m):", width=15)
        z_label.pack(side=tk.LEFT)
        
        z_entry = ttk.Entry(z_frame, width=8)
        z_entry.pack(side=tk.LEFT, padx=5)
        z_entry.insert(0, "0.0")
        
        z_slider = ttk.Scale(z_frame, from_=0.0, to=5.0, orient=tk.HORIZONTAL)
        z_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        z_slider.set(0.0)
        
        # Store the entry and slider as a dictionary under self.z_position
        self.z_position = {'entry': z_entry, 'slider': z_slider}
        
        # Connect the slider to update the entry
        z_slider.configure(command=lambda v: self._update_position_entry('z_position', v))
        
        # Create a separator
        ttk.Separator(position_frame, orient=tk.HORIZONTAL).pack(fill=tk.X, pady=10)
        
        # Rotation section
        rot_label = ttk.Label(position_frame, text="Camera Orientation", style='SubHeader.TLabel')
        rot_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Create Pan angle controls
        pan_frame = ttk.Frame(position_frame)
        pan_frame.pack(fill=tk.X, pady=5)
        
        pan_label = ttk.Label(pan_frame, text="Pan Angle (°):", width=15)
        pan_label.pack(side=tk.LEFT)
        
        pan_entry = ttk.Entry(pan_frame, width=8)
        pan_entry.pack(side=tk.LEFT, padx=5)
        pan_entry.insert(0, "0.0")
        
        pan_slider = ttk.Scale(pan_frame, from_=0.0, to=360.0, orient=tk.HORIZONTAL)
        pan_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        pan_slider.set(0.0)
        
        # Store the entry and slider as a dictionary under self.pan_angle
        self.pan_angle = {'entry': pan_entry, 'slider': pan_slider}
        
        # Connect the slider to update the entry
        pan_slider.configure(command=lambda v: self._update_position_entry('pan_angle', v))
        
        # Create Tilt angle controls
        tilt_frame = ttk.Frame(position_frame)
        tilt_frame.pack(fill=tk.X, pady=5)
        
        tilt_label = ttk.Label(tilt_frame, text="Tilt Angle (°):", width=15)
        tilt_label.pack(side=tk.LEFT)
        
        tilt_entry = ttk.Entry(tilt_frame, width=8)
        tilt_entry.pack(side=tk.LEFT, padx=5)
        tilt_entry.insert(0, "0.0")
        
        tilt_slider = ttk.Scale(tilt_frame, from_=-90.0, to=90.0, orient=tk.HORIZONTAL)
        tilt_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tilt_slider.set(0.0)
        
        # Store the entry and slider as a dictionary under self.tilt_angle
        self.tilt_angle = {'entry': tilt_entry, 'slider': tilt_slider}
        
        # Connect the slider to update the entry
        tilt_slider.configure(command=lambda v: self._update_position_entry('tilt_angle', v))
        
        # Create Roll angle controls
        roll_frame = ttk.Frame(position_frame)
        roll_frame.pack(fill=tk.X, pady=5)
        
        roll_label = ttk.Label(roll_frame, text="Roll Angle (°):", width=15)
        roll_label.pack(side=tk.LEFT)
        
        roll_entry = ttk.Entry(roll_frame, width=8)
        roll_entry.pack(side=tk.LEFT, padx=5)
        roll_entry.insert(0, "0.0")
        
        roll_slider = ttk.Scale(roll_frame, from_=-180.0, to=180.0, orient=tk.HORIZONTAL)
        roll_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        roll_slider.set(0.0)
        
        # Store the entry and slider as a dictionary under self.roll_angle
        self.roll_angle = {'entry': roll_entry, 'slider': roll_slider}
        
        # Connect the slider to update the entry
        roll_slider.configure(command=lambda v: self._update_position_entry('roll_angle', v))
        
        # Add a button to apply the settings
        apply_button = ttk.Button(position_frame, text="Apply Position/Orientation", 
                                command=self.apply_camera_settings, style='Action.TButton')
        apply_button.pack(anchor=tk.E, pady=10)

    def _update_position_entry(self, attr_name, value):
        """Update the entry when the slider is moved."""
        if hasattr(self, attr_name):
            attr = getattr(self, attr_name)
            if isinstance(attr, dict) and 'entry' in attr:
                # Update entry with formatted value
                attr['entry'].delete(0, tk.END)
                attr['entry'].insert(0, f"{float(value):.1f}")
                
                # Update visualization
                self.update_position_visualization(redraw_only=True)

    def apply_camera_settings(self):
        """Apply the current position and rotation settings to the selected camera in the current scene."""
        selected_camera = self.camera_selector.get()
        if not selected_camera:
            messagebox.showwarning("No Camera Selected", "Please select a camera first.")
            return
        
        # Ensure we have a current scene
        if not self.current_scene:
            # Create a new default scene if none exists
            self.current_scene = {
                'name': 'Untitled Scene',
                'description': 'Scene created automatically',
                'cameras': {}
            }
            self.scenes.append(self.current_scene)
            self.update_scene_listbox()
        
        # Create the camera entry if it doesn't exist
        if 'cameras' not in self.current_scene:
            self.current_scene['cameras'] = {}
        
        if selected_camera not in self.current_scene['cameras']:
            self.current_scene['cameras'][selected_camera] = {
                'position': {'x': 0.0, 'y': 0.0, 'z': 0.0},
                'rotation': {'pan': 0.0, 'tilt': 0.0, 'roll': 0.0}
            }
        
        try:
            # Get position values from entries
            x = float(self.x_position['entry'].get())
            y = float(self.y_position['entry'].get())
            z = float(self.z_position['entry'].get())
            
            # Get rotation values from entries
            pan = float(self.pan_angle['entry'].get())
            tilt = float(self.tilt_angle['entry'].get())
            roll = float(self.roll_angle['entry'].get())
            
            # Update the current scene's camera
            self.current_scene['cameras'][selected_camera]['position'] = {
                'x': x, 'y': y, 'z': z
            }
            self.current_scene['cameras'][selected_camera]['rotation'] = {
                'pan': pan, 'tilt': tilt, 'roll': roll
            }
            
            # Save the scenes
            self.save_scenes()
            
            # Update visualization
            self.update_position_visualization()
            
            self.status_bar.config(text=f"Applied position settings for camera {selected_camera}")
            self.logger.info(f"Applied position settings for camera {selected_camera}: pos=({x}, {y}, {z}), rot=({pan}, {tilt}, {roll})")
        
        except ValueError as e:
            messagebox.showerror("Invalid Value", f"Please enter valid numeric values: {str(e)}")
            self.logger.error(f"Failed to apply camera settings: {str(e)}")
            return

    def load_camera_settings(self):
        """Load camera settings based on selected camera."""
        selected_camera = self.camera_selector.get()
        if not selected_camera:
            return
        
        # Update UI with the selected camera's settings
        self.on_camera_selected()
    
    def on_camera_selected(self, event=None):
        """Handle camera selection change."""
        selected_camera = self.camera_selector.get()
        if not selected_camera:
            return
        
        # Update the UI with the selected camera's position if available
        if self.current_scene and selected_camera in self.current_scene['cameras']:
            camera_data = self.current_scene['cameras'][selected_camera]
            
            # Update position entries and sliders
            for axis, attr in [('x', 'x_position'), ('y', 'y_position'), ('z', 'z_position')]:
                self._update_entry_and_slider(
                    attr, 
                    camera_data['position'][axis]
                )
            
            # Update rotation entries and sliders
            for rot, attr in [('pan', 'pan_angle'), ('tilt', 'tilt_angle'), ('roll', 'roll_angle')]:
                self._update_entry_and_slider(
                    attr, 
                    camera_data['rotation'][rot]
                )
            
            # Update visualization
            self.update_position_visualization()
        else:
            # Reset to default values
            self.reset_camera_settings()
    
    def reset_camera_settings(self):
        """Reset camera position settings to default values."""
        # Reset position entries and sliders
        for attr in ['x_position', 'y_position', 'z_position']:
            self._update_entry_and_slider(attr, 0.0)
        
        # Reset rotation entries and sliders
        for attr in ['pan_angle', 'tilt_angle', 'roll_angle']:
            self._update_entry_and_slider(attr, 0.0)
        
        # Update visualization
        self.update_position_visualization()
    
    def quick_save_scene(self):
        """Quick save current settings as a new scene."""
        # First apply any pending changes
        self.apply_camera_settings()
        
        # Prompt for scene name
        scene_name = simpledialog.askstring("Save Scene", "Enter a name for the new scene:",
                                          parent=self)
        if not scene_name:
            return
            
        # Check if scene already exists
        if any(scene['name'] == scene_name for scene in self.scenes):
            overwrite = messagebox.askyesno(
                "Scene Exists", 
                f"A scene named '{scene_name}' already exists. Do you want to overwrite it?",
                parent=self
            )
            if not overwrite:
                return
                
            # Remove existing scene with same name
            self.scenes = [scene for scene in self.scenes if scene['name'] != scene_name]
            
        # Create a new scene with current camera settings
        new_scene = {
            'name': scene_name,
            'description': f"Scene created on {time.strftime('%Y-%m-%d %H:%M:%S')}",
            'cameras': {}
        }
        
        # Add camera settings if we have a current scene
        if self.current_scene and 'cameras' in self.current_scene:
            new_scene['cameras'] = self.current_scene['cameras'].copy()
        
        # Add the new scene to our list
        self.scenes.append(new_scene)
        
        # Set as current scene
        self.current_scene = new_scene
        
        # Save scenes to file
        self.save_scenes()
        
        # Update the scene listbox
        self.update_scene_listbox()
        
        self.status_bar.config(text=f"Created new scene: {scene_name}")
        self.logger.info(f"Created new scene: {scene_name}")
    
    def on_close(self):
        """Handle window close event."""
        # Stop the camera update loop
        self.is_running = False
        
        # Cancel any pending after callbacks
        self.after_cancel(self.after_id) if hasattr(self, 'after_id') else None
        
        # Release camera resources
        if self.camera_manager:
            self.camera_manager.release_all()
            self.logger.info("Released all camera resources")
        
        # Save any pending changes
        try:
            self.save_scenes()
            self.logger.info("Saved scene configurations")
        except Exception as e:
            self.logger.error(f"Error saving scenes on exit: {e}")
        
        # Destroy the window
        self.logger.info("Application closing")
        self.destroy()

    def update_camera_layout(self, event=None):
        """Update the camera layout based on the selected option."""
        layout = self.layout_var.get()
        self.logger.info(f"Changing camera layout to: {layout}")
        
        # Store current state
        was_running = self.is_running
        
        # Stop camera updates temporarily
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(1.0)
        
        # Clear existing views
        for widget in self.camera_frame.winfo_children():
            widget.destroy()
            
        # Re-create camera views with new layout
        if not self.camera_manager or not self.camera_manager.cameras:
            no_cam_label = ttk.Label(self.camera_frame, text="No cameras available", 
                                   font=('Segoe UI', 12), foreground="#888888")
            no_cam_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            return
            
        cameras = self.camera_manager.cameras
        # Apply filter if needed
        if self.camera_filter_var.get() != "all":
            selected_cam = self.camera_filter_var.get()
            if selected_cam in cameras:
                cameras = {selected_cam: cameras[selected_cam]}
            else:
                cameras = {}
                
        if not cameras:
            no_cam_label = ttk.Label(self.camera_frame, text="No cameras match the filter", 
                                   font=('Segoe UI', 12), foreground="#888888")
            no_cam_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
            return
            
        self.camera_views = {}
        
        num_cameras = len(cameras)
        
        # Determine grid dimensions based on layout
        if layout == "auto":
            # Auto-adapt grid based on camera count
            if num_cameras == 1:
                rows, cols = 1, 1
            elif num_cameras <= 4:
                rows, cols = 2, 2
            elif num_cameras <= 9:
                rows, cols = 3, 3
            elif num_cameras <= 16:
                rows, cols = 4, 4
            else:
                # For more than 16, use square grid
                grid_size = int(np.ceil(np.sqrt(num_cameras)))
                rows, cols = grid_size, grid_size
        elif layout == "1x1":
            rows, cols = 1, 1
        elif layout == "2x2":
            rows, cols = 2, 2
        elif layout == "3x3":
            rows, cols = 3, 3
        elif layout == "4x4":
            rows, cols = 4, 4
        elif layout == "horizontal":
            rows, cols = 1, num_cameras
        elif layout == "vertical":
            rows, cols = num_cameras, 1
        elif layout == "single":
            rows, cols = 1, 1
            # Only show first camera
            cameras = {list(cameras.keys())[0]: list(cameras.values())[0]}
            num_cameras = 1
        else:
            # Default to auto
            rows, cols = 2, 2
        
        # Create camera views in grid
        camera_list = list(cameras.items())
        for i, (camera_id, camera) in enumerate(camera_list):
            if i >= rows * cols:
                break  # Don't exceed grid capacity
            row = i // cols
            col = i % cols
            large = (layout == "single" or (rows == 1 and cols == 1))
            self._create_camera_view(camera_id, row, col, large=large)
        
        # Configure grid weights
        for i in range(cols):
            self.camera_frame.columnconfigure(i, weight=1)
        for i in range(rows):
            self.camera_frame.rowconfigure(i, weight=1)
            
        # Restart camera updates if they were running
        if was_running:
            self.start_camera_views()
    
    def _create_camera_view(self, camera_id, row, col, large=False):
        """Create a camera view at the specified grid position using CameraView component."""
        # Get camera name from config or use ID
        camera_name = f"Camera {camera_id}"
        if self.app_config and "cameras" in self.app_config:
            cam_config = self.app_config["cameras"].get(camera_id, {})
            if "name" in cam_config:
                camera_name = cam_config["name"]
        
        # Create CameraView component
        camera_view = CameraView(
            self.camera_frame,
            camera_id=camera_id,
            camera_name=camera_name,
            on_fullscreen=self.show_fullscreen_camera,
            on_snapshot=self.save_camera_image,
            on_settings=lambda cam_id: self.show_camera_settings(cam_id)
        )
        camera_view.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")
        
        # Store the CameraView component in our dictionary
        self.camera_views[camera_id] = {
            'view': camera_view,
            'canvas': camera_view.canvas,  # For backward compatibility
            'status': camera_view.status_label,  # For backward compatibility
        }
    
    def update_camera_filter(self, event=None):
        """Update the camera filter based on the selected option."""
        filter_value = self.camera_filter_var.get()
        self.logger.info(f"Changing camera filter to: {filter_value}")
        
        # Apply the new layout with filter
        self.update_camera_layout()
    
    def update_camera_filters(self):
        """Update the available camera filters based on current cameras."""
        if not self.camera_manager or not self.camera_manager.cameras:
            return
            
        # Get all camera IDs
        camera_ids = ["all"] + list(self.camera_manager.cameras.keys())
        
        # Update the combobox values
        self.filter_combobox['values'] = camera_ids
        
        # If current value is not in the list, reset to "all"
        if self.camera_filter_var.get() not in camera_ids:
            self.camera_filter_var.set("all")

    def _update_entry_and_slider(self, attr_name, value):
        """Update both entry and slider for a given attribute."""
        if hasattr(self, attr_name):
            attr = getattr(self, attr_name)
            if isinstance(attr, dict) and 'entry' in attr and 'slider' in attr:
                # Update entry
                attr['entry'].delete(0, tk.END)
                attr['entry'].insert(0, str(value))
                
                # Update slider
                attr['slider'].set(float(value))

    def load_scenes(self):
        """Load scenes from the JSON file."""
        try:
            if os.path.exists(self.scenes_file):
                with open(self.scenes_file, 'r') as f:
                    return json.load(f)
            else:
                self.logger.info(f"Scenes file does not exist: {self.scenes_file}")
                return []
        except Exception as e:
            self.logger.error(f"Error loading scenes: {e}")
            messagebox.showerror("Error", f"Failed to load scenes: {e}")
            return []

    def save_scenes(self):
        """Save scenes to the JSON file."""
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(self.scenes_file), exist_ok=True)
            
            with open(self.scenes_file, 'w') as f:
                json.dump(self.scenes, f, indent=4)
            
            self.logger.info(f"Saved scenes to {self.scenes_file}")
        except Exception as e:
            self.logger.error(f"Error saving scenes: {e}")
            messagebox.showerror("Error", f"Failed to save scenes: {e}")

    def setup_scenes_tab(self):
        """Set up the scenes tab."""
        # Create frame for scene management
        scenes_frame = ttk.Frame(self.scenes_tab)
        scenes_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add header
        header = ttk.Label(scenes_frame, text="Camera Scene Management", 
                          style='Header.TLabel')
        header.pack(anchor=tk.W, pady=(0, 10))
        
        # Description
        description = ttk.Label(scenes_frame, 
                              text="Scenes allow you to save and recall camera positions and orientations for different monitoring scenarios.", 
                              wraplength=800)
        description.pack(anchor=tk.W, pady=(0, 15))
        
        # Split into left and right panels
        panel_frame = ttk.Frame(scenes_frame)
        panel_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Scene list
        list_frame = ttk.Frame(panel_frame)
        list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Scene list with title
        scene_list_frame = ttk.LabelFrame(list_frame, text="Available Scenes")
        scene_list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a listbox with scrollbar
        list_container = ttk.Frame(scene_list_frame)
        list_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.scene_listbox = tk.Listbox(list_container, font=('Segoe UI', 10), 
                                      activestyle='dotbox', selectbackground='#4a6da7', 
                                      selectforeground='white')
        self.scene_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_container, orient="vertical", command=self.scene_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.scene_listbox.config(yscrollcommand=scrollbar.set)
        
        # Bind double-click to load scene
        self.scene_listbox.bind('<Double-1>', lambda e: self.load_selected_scene())
        
        # Update scene listbox
        self.update_scene_listbox()
        
        # Buttons below list
        list_buttons = ttk.Frame(list_frame)
        list_buttons.pack(fill=tk.X, pady=5)
        
        load_button = ttk.Button(list_buttons, text="Load Selected", 
                               command=self.load_selected_scene, style='Action.TButton')
        load_button.pack(side=tk.LEFT, padx=5)
        
        delete_button = ttk.Button(list_buttons, text="Delete", 
                                 command=self.delete_selected_scene)
        delete_button.pack(side=tk.LEFT, padx=5)
        
        # Right panel - Scene details
        details_frame = ttk.Frame(panel_frame)
        details_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # Create new scene frame
        new_scene_frame = ttk.LabelFrame(details_frame, text="Create New Scene")
        new_scene_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Scene name
        name_frame = ttk.Frame(new_scene_frame, padding=5)
        name_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(name_frame, text="Scene Name:", width=12).pack(side=tk.LEFT)
        
        self.scene_name_entry = ttk.Entry(name_frame)
        self.scene_name_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Description field
        desc_frame = ttk.Frame(new_scene_frame, padding=5)
        desc_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(desc_frame, text="Description:", width=12).pack(side=tk.LEFT)
        
        self.scene_desc_entry = ttk.Entry(desc_frame)
        self.scene_desc_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        
        # Create button
        create_button = ttk.Button(new_scene_frame, text="Create Scene", 
                                 command=self.create_scene, style='Action.TButton')
        create_button.pack(anchor=tk.E, padx=10, pady=10)
        
        # Scene details display
        self.scene_details_frame = ttk.LabelFrame(details_frame, text="Scene Details")
        self.scene_details_frame.pack(fill=tk.BOTH, expand=True)
        
        # No scene selected message
        self.scene_details_label = ttk.Label(self.scene_details_frame, 
                                          text="Select a scene to view details",
                                          font=('Segoe UI', 10),
                                          anchor=tk.CENTER)
        self.scene_details_label.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Scene camera tree view (hidden initially)
        self.scene_tree = ttk.Treeview(self.scene_details_frame, 
                                     columns=("Position", "Rotation"),
                                     show="tree headings")
        self.scene_tree.heading("#0", text="Camera")
        self.scene_tree.heading("Position", text="Position (X, Y, Z)")
        self.scene_tree.heading("Rotation", text="Rotation (Pan, Tilt, Roll)")
        self.scene_tree.column("#0", width=120)
        self.scene_tree.column("Position", width=150)
        self.scene_tree.column("Rotation", width=150)
        
        # Connect scene listbox selection to update details
        self.scene_listbox.bind('<<ListboxSelect>>', self.on_scene_selected)

    def update_scene_listbox(self):
        """Update the scene listbox with available scenes."""
        self.scene_listbox.delete(0, tk.END)
        for scene in self.scenes:
            self.scene_listbox.insert(tk.END, scene['name'])

    def on_scene_selected(self, event=None):
        """Handle scene selection in the listbox."""
        selection = self.scene_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        scene = self.scenes[index]
        
        # Clear existing widgets in scene details frame
        for widget in self.scene_details_frame.winfo_children():
            widget.destroy()
        
        # Create a details view with scene info
        details_container = ttk.Frame(self.scene_details_frame, padding=10)
        details_container.pack(fill=tk.BOTH, expand=True)
        
        # Scene name
        name_label = ttk.Label(details_container, text=scene['name'], 
                             font=('Segoe UI', 12, 'bold'),
                             foreground='#4a6da7')
        name_label.pack(anchor=tk.W, pady=(0, 5))
        
        # Scene description
        if 'description' in scene:
            desc_label = ttk.Label(details_container, text=scene['description'],
                                 font=('Segoe UI', 9),
                                 wraplength=350)
            desc_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Number of cameras
        camera_count = len(scene.get('cameras', {}))
        cam_count_label = ttk.Label(details_container, 
                                  text=f"Contains {camera_count} camera{'s' if camera_count != 1 else ''}")
        cam_count_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Camera details
        if camera_count > 0:
            # Create treeview for camera details
            tree = ttk.Treeview(details_container, 
                              columns=("Position", "Rotation"),
                              show="headings", height=6)
            tree.heading("Position", text="Position (X, Y, Z)")
            tree.heading("Rotation", text="Rotation (Pan, Tilt, Roll)")
            tree.column("Position", width=180)
            tree.column("Rotation", width=180)
            tree.pack(fill=tk.BOTH, expand=True)
            
            # Add camera info to tree
            for camera_id, camera_data in scene['cameras'].items():
                pos = camera_data.get('position', {})
                rot = camera_data.get('rotation', {})
                
                pos_str = f"X: {pos.get('x', 0.0):.1f}, Y: {pos.get('y', 0.0):.1f}, Z: {pos.get('z', 0.0):.1f}"
                rot_str = f"P: {rot.get('pan', 0.0):.1f}, T: {rot.get('tilt', 0.0):.1f}, R: {rot.get('roll', 0.0):.1f}"
                
                # Insert the item and store the returned item ID
                item_id = tree.insert("", "end", text=camera_id, values=(pos_str, rot_str), tags=(camera_id,))
                # Use the actual item ID returned from insert method, not the camera_id
                tree.item(item_id, text=f"Camera {camera_id}")
        else:
            ttk.Label(details_container, text="No cameras configured in this scene").pack(pady=10)
        
        # Actions
        action_frame = ttk.Frame(details_container)
        action_frame.pack(fill=tk.X, pady=10)
        
        # Load button
        load_button = ttk.Button(action_frame, text="Load Scene", 
                               command=self.load_selected_scene, style='Action.TButton')
        load_button.pack(side=tk.LEFT, padx=5)
        
        # Duplicate button
        duplicate_button = ttk.Button(action_frame, text="Duplicate", 
                                    command=self.duplicate_selected_scene)
        duplicate_button.pack(side=tk.LEFT, padx=5)
        
        # Delete button
        delete_button = ttk.Button(action_frame, text="Delete", 
                                 command=self.delete_selected_scene)
        delete_button.pack(side=tk.LEFT, padx=5)

    def create_scene(self):
        """Create a new scene with current camera settings."""
        scene_name = self.scene_name_entry.get().strip()
        if not scene_name:
            messagebox.showwarning("Invalid Name", "Please enter a valid scene name.")
            return
        
        # Check if scene already exists
        if any(scene['name'] == scene_name for scene in self.scenes):
            messagebox.showwarning("Scene Exists", f"A scene named '{scene_name}' already exists.")
            return
        
        # Get description
        description = self.scene_desc_entry.get().strip()
        if not description:
            description = f"Scene created on {time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Create a new scene with current camera settings
        new_scene = {
            'name': scene_name,
            'description': description,
            'cameras': {}
        }
        
        # Add camera settings if we have a current scene
        if self.current_scene and 'cameras' in self.current_scene:
            new_scene['cameras'] = self.current_scene['cameras'].copy()
        
        # Add the new scene to our list
        self.scenes.append(new_scene)
        
        # Set as current scene
        self.current_scene = new_scene
        
        # Save scenes to file
        self.save_scenes()
        
        # Update the scene listbox
        self.update_scene_listbox()
        
        # Select the new scene
        self.scene_listbox.selection_clear(0, tk.END)
        self.scene_listbox.selection_set(len(self.scenes) - 1)
        self.scene_listbox.see(len(self.scenes) - 1)
        self.on_scene_selected()
        
        # Clear the entry fields
        self.scene_name_entry.delete(0, tk.END)
        self.scene_desc_entry.delete(0, tk.END)
        
        self.status_bar.config(text=f"Created new scene: {scene_name}")
        self.logger.info(f"Created new scene: {scene_name}")

    def load_selected_scene(self):
        """Load the selected scene."""
        selection = self.scene_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a scene to load.")
            return
        
        index = selection[0]
        scene = self.scenes[index]
        
        # Set as current scene
        self.current_scene = scene
        
        # Update UI with the selected scene's camera settings
        self.on_scene_selected()
        
        # Also update the position visualization
        self.update_position_visualization()
        
        self.status_bar.config(text=f"Loaded scene: {scene['name']}")
        self.logger.info(f"Loaded scene: {scene['name']}")

    def delete_selected_scene(self):
        """Delete the selected scene."""
        selection = self.scene_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a scene to delete.")
            return
        
        index = selection[0]
        scene_name = self.scenes[index]['name']
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete the scene '{scene_name}'?"):
            return
        
        # Remove the scene
        del self.scenes[index]
        
        # Save scenes to file
        self.save_scenes()
        
        # Update the scene listbox
        self.update_scene_listbox()
        
        # If we deleted the current scene, reset
        if self.current_scene and self.current_scene['name'] == scene_name:
            self.current_scene = None
            self.reset_camera_settings()
        
        self.status_bar.config(text=f"Deleted scene: {scene_name}")
        self.logger.info(f"Deleted scene: {scene_name}")

    def duplicate_selected_scene(self):
        """Create a duplicate of the selected scene."""
        selection = self.scene_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a scene to duplicate.")
            return
        
        index = selection[0]
        original_scene = self.scenes[index]
        
        # Prompt for new name
        new_name = simpledialog.askstring("Duplicate Scene", 
                                        f"Enter name for the duplicate of '{original_scene['name']}':",
                                        initialvalue=f"{original_scene['name']} (Copy)",
                                        parent=self)
        if not new_name:
            return
        
        # Check if name exists
        if any(scene['name'] == new_name for scene in self.scenes):
            messagebox.showwarning("Scene Exists", f"A scene named '{new_name}' already exists.")
            return
        
        # Create a deep copy of the scene
        import copy
        new_scene = copy.deepcopy(original_scene)
        new_scene['name'] = new_name
        new_scene['description'] = f"Copy of {original_scene['name']} made on {time.strftime('%Y-%m-%d %H:%M:%S')}"
        
        # Add to scenes list
        self.scenes.append(new_scene)
        
        # Save to file
        self.save_scenes()
        
        # Update listbox
        self.update_scene_listbox()
        
        # Select the new scene
        self.scene_listbox.selection_clear(0, tk.END)
        self.scene_listbox.selection_set(len(self.scenes) - 1)
        self.scene_listbox.see(len(self.scenes) - 1)
        self.on_scene_selected()
        
        self.status_bar.config(text=f"Duplicated scene: {new_name}")
        self.logger.info(f"Duplicated scene from '{original_scene['name']}' to '{new_name}'")

    def _initialize_security_components(self):
        """Initialize security components (motion detection, recording, alerts)."""
        try:
            security_config = self.app_config.get("security", {})
            
            # Initialize alert manager
            alerts_config = security_config.get("alerts", {})
            if alerts_config.get("enabled", True):
                log_file = alerts_config.get("log_file", "logs/alerts.json")
                self.alert_manager = AlertManager(
                    log_file=log_file,
                    enable_sound=alerts_config.get("enable_sound", True),
                    enable_visual=alerts_config.get("enable_visual", True)
                )
                self.logger.info("Alert manager initialized")
            
            # Initialize video recorder
            recording_config = security_config.get("recording", {})
            if recording_config.get("enabled", False):
                output_dir = recording_config.get("output_dir", "recordings")
                self.recorder = VideoRecorder(
                    output_dir=output_dir,
                    codec=recording_config.get("codec", "mp4v"),
                    fps=recording_config.get("fps", 30.0),
                    max_file_size_mb=recording_config.get("max_file_size_mb", 500),
                    max_duration_minutes=recording_config.get("max_duration_minutes", 60)
                )
                self.logger.info("Video recorder initialized")
            
            # Initialize motion detectors for each camera
            motion_config = security_config.get("motion_detection", {})
            if motion_config.get("enabled", False):
                method_str = motion_config.get("method", "mog2")
                method = MotionDetectionMethod.MOG2 if method_str == "mog2" else (
                    MotionDetectionMethod.KNN if method_str == "knn" else MotionDetectionMethod.FRAME_DIFF
                )
                
                if self.camera_manager and self.camera_manager.cameras:
                    for camera_id in self.camera_manager.cameras:
                        detector = MotionDetector(
                            method=method,
                            sensitivity=motion_config.get("sensitivity", 0.5),
                            min_area=motion_config.get("min_area", 500)
                        )
                        
                        # Add motion callback
                        if self.recorder and recording_config.get("motion_triggered", True):
                            def make_motion_callback(cam_id):
                                def callback(frame, contours, mask):
                                    if not self.recorder.is_recording(cam_id):
                                        h, w = frame.shape[:2]
                                        self.recorder.start_recording(cam_id, w, h, motion_triggered=True)
                                    # Frames are written in update_camera_frames to avoid double-writes.
                                    if self.alert_manager and alerts_config.get("motion_alerts", True):
                                        self.alert_manager.add_alert(
                                            AlertType.MOTION_DETECTED,
                                            f"Motion detected on camera {cam_id}",
                                            camera_id=cam_id,
                                            level=AlertLevel.WARNING,
                                            suppress_duplicates_seconds=alerts_config.get("suppress_duplicates_seconds", 5.0)
                                        )
                                return callback
                            
                            detector.add_motion_callback(make_motion_callback(camera_id))
                        
                        self.motion_detectors[camera_id] = detector
                        self.logger.info(f"Motion detector initialized for camera {camera_id}")
        except Exception as e:
            self.logger.error(f"Error initializing security components: {e}")
    
    def start_camera_views(self):
        """Start updating camera views."""
        if not self.camera_manager:
            return
            
        self.logger.info("Starting camera views")
        self.is_running = True
        
        # Start the update loop directly using tkinter's after method
        # This avoids threading issues and gives better performance
        self.update_camera_frames()
        
        self.status_bar.config(text="Camera views started")

    def update_camera_frames(self):
        """Update camera frames in the UI."""
        if not self.is_running or not self.camera_manager:
            return
        
        try:
            # Capture frames from all cameras at once
            try:
                camera_frames = self.camera_manager.capture_all()
            except Exception as e:
                self.logger.error(f"Error capturing frames: {e}")
                # Continue with an empty dict to avoid crashing
                camera_frames = {}
            
            # Only process visible cameras for better performance
            current_filter = self.camera_filter_var.get() if hasattr(self, 'camera_filter_var') else "all"
            
            # Use a more efficient approach to process frames
            for camera_id, frame in camera_frames.items():
                # Skip if camera doesn't match current filter
                if (current_filter != "all" and camera_id != current_filter) or camera_id not in self.camera_views:
                    continue
                
                # Get the camera view component
                camera_view_data = self.camera_views[camera_id]
                
                # Check if using new CameraView component or old structure
                if 'view' in camera_view_data:
                    # New CameraView component
                    camera_view = camera_view_data['view']
                    
                    # Skip processing if the view isn't visible
                    if not camera_view.winfo_viewable():
                        continue
                    
                    # Update frame using CameraView's method
                    show_fps = self.app_config.get('display', {}).get('show_fps', True)
                    try:
                        # Process motion detection if enabled
                        display_frame = frame.copy()
                        if camera_id in self.motion_detectors:
                            detector = self.motion_detectors[camera_id]
                            motion_detected, motion_mask, contours = detector.detect(frame)
                            
                            if motion_detected:
                                # Draw motion on frame
                                display_frame = detector.draw_motion(display_frame, contours)
                                # Show recording indicator if recording
                                if self.recorder and self.recorder.is_recording(camera_id):
                                    camera_view.show_recording_indicator(True)
                        
                        # Process recording if enabled
                        if self.recorder and self.recorder.is_recording(camera_id):
                            self.recorder.write_frame(camera_id, frame)
                        
                        camera_view.update_frame(display_frame, show_fps=show_fps)
                        
                        # Store FPS for system monitoring
                        if hasattr(self, 'system_stats') and 'fps' in self.system_stats:
                            self.system_stats['fps'][camera_id] = camera_view.fps
                    except Exception as camera_ex:
                        self.logger.error(f"Error processing frame for camera {camera_id}: {camera_ex}")
                        camera_view.set_status("error", f"Error: {str(camera_ex)[:20]}")
                        continue
                else:
                    # Legacy support for old structure
                    canvas = camera_view_data.get('canvas')
                    if not canvas or not canvas.winfo_viewable():
                        continue
                    
                    # Process frame only if it's valid
                    if frame is not None and frame.size > 0:
                        try:
                            # Get canvas dimensions
                            canvas_width = canvas.winfo_width()
                            canvas_height = canvas.winfo_height()
                            
                            # Skip resizing if canvas isn't properly sized yet
                            if canvas_width > 1 and canvas_height > 1:
                                # Optimize resize using INTER_AREA for downscaling
                                frame_height, frame_width = frame.shape[:2]
                                scale_factor = min(canvas_width / frame_width, canvas_height / frame_height)
                                
                                # Resize frame to fit canvas
                                new_width = int(frame_width * scale_factor)
                                new_height = int(frame_height * scale_factor)
                                
                                if new_width > 0 and new_height > 0:
                                    # Use INTER_AREA for downscaling (better quality)
                                    interpolation = cv2.INTER_AREA if scale_factor < 1.0 else cv2.INTER_LINEAR
                                    frame_resized = cv2.resize(frame, (new_width, new_height), interpolation=interpolation)
                                    
                                    # Convert to RGB and PIL Image
                                    frame_rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
                                    img = Image.fromarray(frame_rgb)
                                    
                                    img_tk = ImageTk.PhotoImage(image=img)
                                    
                                    # Save reference to prevent garbage collection
                                    self.camera_views[camera_id]['image'] = img_tk
                                    
                                    # Clear and redraw canvas
                                    canvas.delete("all")
                                    x = (canvas_width - new_width) // 2
                                    y = (canvas_height - new_height) // 2
                                    canvas.create_image(x, y, anchor=tk.NW, image=img_tk)
                                    
                                    # Add FPS overlay if enabled
                                    if self.app_config.get('display', {}).get('show_fps', True):
                                        current_time = time.time()
                                        if 'last_frame_time' in self.camera_views[camera_id]:
                                            elapsed = current_time - self.camera_views[camera_id]['last_frame_time']
                                            fps = 1.0 / elapsed if elapsed > 0 else 0
                                            canvas.create_text(10, 20, anchor=tk.NW, 
                                                          text=f"FPS: {fps:.1f}", 
                                                          fill="lime", font=("Arial", 10))
                                            if hasattr(self, 'system_stats') and 'fps' in self.system_stats:
                                                self.system_stats['fps'][camera_id] = fps
                                        self.camera_views[camera_id]['last_frame_time'] = current_time
                                    
                                    # Update camera status
                                    if 'status' in camera_view_data:
                                        camera_view_data['status'].config(text="Active", foreground="green")
                        except Exception as camera_ex:
                            self.logger.error(f"Error processing frame for camera {camera_id}: {camera_ex}")
                            self.on_camera_error(camera_id, camera_ex)
                            continue
                    else:
                        # Handle invalid frame error
                        self.on_camera_error(camera_id, "Invalid frame received")
            
            # Use a more responsive way to schedule the next update
            # Adaptive frame rate: slower when fewer cameras are visible
            visible_cameras = sum(1 for cam_id in self.camera_views if self.camera_views[cam_id]['canvas'].winfo_viewable())
            delay = max(10, min(50, visible_cameras * 10))  # 10ms min, 50ms max
            self.after_id = self.after(delay, self.update_camera_frames)
                
        except Exception as e:
            self.logger.error(f"Error updating camera frames: {e}")
            # Schedule restart even on error, but with a longer delay
            self.after_id = self.after(1000, self.update_camera_frames)

    def show_fullscreen_camera(self, camera_id):
        """Show a camera in fullscreen mode."""
        if camera_id not in self.camera_manager.cameras:
            messagebox.showerror("Error", f"Camera {camera_id} not available")
            return
        
        # Create a new top-level window
        fullscreen_window = tk.Toplevel(self)
        fullscreen_window.title(f"Camera {camera_id} - Fullscreen View")
        fullscreen_window.geometry("1024x768")
        
        # Create a frame to hold the canvas
        frame = ttk.Frame(fullscreen_window)
        frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create canvas for camera feed
        canvas = tk.Canvas(frame, bg="black")
        canvas.pack(fill=tk.BOTH, expand=True)
        
        # Create info bar
        info_frame = ttk.Frame(fullscreen_window)
        info_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Add info labels
        camera_label = ttk.Label(info_frame, text=f"Camera: {camera_id}", font=("Arial", 10, "bold"))
        camera_label.pack(side=tk.LEFT, padx=5)
        
        self.fullscreen_info_label = ttk.Label(info_frame, text="")
        self.fullscreen_info_label.pack(side=tk.LEFT, padx=5)
        
        # Add close button
        close_button = ttk.Button(
            info_frame, 
            text="Close Fullscreen",
            command=fullscreen_window.destroy
        )
        close_button.pack(side=tk.RIGHT, padx=5)
        
        # Add screenshot button
        screenshot_button = ttk.Button(
            info_frame, 
            text="Take Screenshot",
            command=lambda: self.save_camera_image(camera_id)
        )
        screenshot_button.pack(side=tk.RIGHT, padx=5)
        
        # Function to update the canvas
        def update_fullscreen_canvas():
            if not fullscreen_window.winfo_exists():
                return
            
            try:
                # Capture frame - using capture_all and getting the specific camera frame
                frames = self.camera_manager.capture_all()
                if camera_id not in frames:
                    fullscreen_window.after(1000, update_fullscreen_canvas)
                    return
                
                frame = frames[camera_id]
                if frame is None:
                    fullscreen_window.after(1000, update_fullscreen_canvas)
                    return
                
                # Get canvas dimensions
                canvas_width = canvas.winfo_width()
                canvas_height = canvas.winfo_height()
                
                # Skip if canvas size not yet determined
                if canvas_width <= 1 or canvas_height <= 1:
                    fullscreen_window.after(100, update_fullscreen_canvas)
                    return
                
                # Add timestamp and info
                timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                resolution = f"{frame.shape[1]}x{frame.shape[0]}"
                
                # Update info label
                self.fullscreen_info_label.config(text=f"Resolution: {resolution} | Time: {timestamp}")
                
                # Add timestamp to the frame
                frame_with_text = frame.copy()
                cv2.putText(
                    frame_with_text, 
                    timestamp, 
                    (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.6, 
                    (0, 255, 255), 
                    2
                )
                
                # Convert to PIL Image
                frame_rgb = cv2.cvtColor(frame_with_text, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame_rgb)
                
                # Resize to fit canvas
                img = img.resize((canvas_width, canvas_height), Image.LANCZOS)
                
                # Convert to PhotoImage
                img_tk = ImageTk.PhotoImage(image=img)
                
                # Store reference to prevent garbage collection
                canvas.image = img_tk
                
                # Update canvas
                canvas.delete("all")
                canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
                
                # Schedule next update
                fullscreen_window.after(50, update_fullscreen_canvas)
                
            except Exception as e:
                self.logger.error(f"Error updating fullscreen view: {e}")
                fullscreen_window.after(1000, update_fullscreen_canvas)
        
        # Start updating
        fullscreen_window.after(100, update_fullscreen_canvas)

    def show_camera_settings(self, camera_id):
        """Show settings dialog for a specific camera."""
        if not self.camera_manager or camera_id not in self.camera_manager.cameras:
            messagebox.showerror("Error", f"Camera {camera_id} not available")
            return
        
        # Create a simple settings dialog
        settings_window = tk.Toplevel(self)
        settings_window.title(f"Settings - Camera {camera_id}")
        settings_window.geometry("400x300")
        
        # Add settings content here (placeholder for now)
        ttk.Label(settings_window, text=f"Settings for Camera {camera_id}", 
                 font=("Arial", 12, "bold")).pack(pady=10)
        ttk.Label(settings_window, text="Camera settings panel coming soon...").pack(pady=20)
        
        # Close button
        ttk.Button(settings_window, text="Close", command=settings_window.destroy).pack(pady=10)
    
    def save_camera_image(self, camera_id):
        """Save an image from a specific camera."""
        if camera_id not in self.camera_manager.cameras:
            messagebox.showerror("Error", f"Camera {camera_id} not available")
            return
        
        try:
            # Create screenshots directory if it doesn't exist
            screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            
            # Capture frame using capture_all and getting the specific camera frame
            frames = self.camera_manager.capture_all()
            if camera_id not in frames:
                messagebox.showerror("Error", f"Could not capture image from camera {camera_id}")
                return
            
            frame = frames[camera_id]
            if frame is None:
                messagebox.showerror("Error", f"Could not capture image from camera {camera_id}")
                return
            
            # Generate filename with timestamp
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            filename = os.path.join(screenshots_dir, f"camera_{camera_id}_{timestamp}.jpg")
            
            # Save the image
            cv2.imwrite(filename, frame)
            
            self.status_bar.config(text=f"Saved image from camera {camera_id} to {filename}")
            self.logger.info(f"Saved image from camera {camera_id} to {filename}")
            
            # Show confirmation
            messagebox.showinfo("Screenshot Saved", f"Image saved to:\n{filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving camera image: {e}")
            messagebox.showerror("Error", f"Failed to save image: {e}")

    def take_screenshot(self):
        """Take screenshots of all active camera feeds."""
        if not self.camera_manager or not self.camera_manager.cameras:
            messagebox.showinfo("Screenshot", "No active cameras to capture.")
            return
        
        try:
            # Create screenshots directory if it doesn't exist
            screenshots_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "screenshots")
            os.makedirs(screenshots_dir, exist_ok=True)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            screenshots_taken = 0
            
            # Capture frames from all cameras
            frames = self.camera_manager.capture_all()
            
            for camera_id, frame in frames.items():
                # Save the image
                filename = os.path.join(screenshots_dir, f"camera_{camera_id}_{timestamp}.jpg")
                cv2.imwrite(filename, frame)
                screenshots_taken += 1
            
            if screenshots_taken > 0:
                self.status_bar.config(text=f"Saved {screenshots_taken} screenshots to {screenshots_dir}")
                self.logger.info(f"Saved {screenshots_taken} screenshots to {screenshots_dir}")
            else:
                self.status_bar.config(text="No screenshots were taken")
        except Exception as e:
            self.logger.error(f"Error taking screenshots: {e}")
            messagebox.showerror("Error", f"Failed to take screenshots: {e}")

    def scan_for_cameras(self):
        """Scan for available cameras and update the UI."""
        if not self.camera_manager:
            messagebox.showerror("Error", "Camera manager not initialized")
            return
        
        # Show a scanning message
        self.status_bar.config(text="Scanning for cameras...")
        
        # Show scanning progress
        progress_window = tk.Toplevel(self)
        progress_window.title("Scanning")
        progress_window.geometry("300x100")
        progress_window.resizable(False, False)
        progress_window.transient(self)
        progress_window.grab_set()
        
        progress_frame = ttk.Frame(progress_window, padding=20)
        progress_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(progress_frame, text="Scanning for cameras...").pack(pady=(0, 10))
        
        progress = ttk.Progressbar(progress_frame, mode='indeterminate')
        progress.pack(fill=tk.X)
        progress.start()
        
        # Force UI update
        self.update_idletasks()
        
        # Clear existing camera views
        for widget in self.camera_frame.winfo_children():
            widget.destroy()
        self.camera_views = {}
        
        # Stop the camera update thread
        was_running = self.is_running
        self.is_running = False
        if self.update_thread:
            self.update_thread.join(1.0)
        
        # Function to perform scanning in a separate thread
        def scan_thread():
            try:
                # Refresh the cameras
                detected_cameras = self.camera_manager.refresh_cameras()
                
                # Schedule UI update on the main thread
                self.after(0, lambda: self.update_after_scan(was_running, progress_window))
            except Exception as e:
                self.logger.error(f"Error scanning for cameras: {e}")
                # Schedule error handling on the main thread
                self.after(0, lambda: self.handle_scan_error(e, progress_window))
        
        # Start scanning thread
        threading.Thread(target=scan_thread, daemon=True).start()

    def update_after_scan(self, was_running, progress_window):
        """Update UI after camera scan completes."""
        try:
            # Update camera selector in settings tab
            if self.camera_manager.cameras:
                self.camera_selector['values'] = list(self.camera_manager.cameras.keys())
                if self.camera_selector['values']:
                    self.camera_selector.current(0)
                
            # Update camera filters
            self.update_camera_filters()
                
            # Update camera count label
            num_cameras = len(self.camera_manager.cameras) if self.camera_manager.cameras else 0
            self.camera_count_label.config(text=f"{num_cameras} camera{'s' if num_cameras != 1 else ''} connected")
            
            # Update layout based on current selection
            self.update_camera_layout()
            
            # Restart camera views if they were running
            if was_running:
                self.start_camera_views()
            
            self.status_bar.config(text=f"Found {num_cameras} camera{'s' if num_cameras != 1 else ''}")
            
        except Exception as e:
            self.logger.error(f"Error updating UI after camera scan: {e}")
            messagebox.showerror("Error", f"Failed to update UI after scanning: {e}")
        finally:
            # Close progress window
            if progress_window and progress_window.winfo_exists():
                progress_window.destroy()

    def handle_scan_error(self, error, progress_window):
        """Handle errors during camera scanning."""
        messagebox.showerror("Error", f"Failed to scan for cameras: {error}")
        self.status_bar.config(text="Camera scan failed")
        
        # Close progress window
        if progress_window and progress_window.winfo_exists():
            progress_window.destroy()

    def update_position_visualization(self, redraw_only=False):
        """Update the visualization to reflect current camera positions."""
        # Check if we have the necessary visualization components
        if not hasattr(self, 'ax') or not hasattr(self, 'canvas') or self.ax is None or self.canvas is None:
            self.logger.debug("Cannot update position visualization - components not initialized yet")
            return
        
        # Check if we're still in setup phase
        if not hasattr(self, 'is_ui_setup_complete') or not self.is_ui_setup_complete:
            self.logger.debug("UI setup not complete, deferring visualization update")
            return
        
        try:
            # Import required modules for 3D visualization
            import numpy as np
            
            if not redraw_only:
                # Clear the current plot
                self.ax.clear()
                
                # Set labels
                self.ax.set_xlabel('X (m)')
                self.ax.set_ylabel('Y (m)')
                self.ax.set_zlabel('Z (m)')
                
                # Set limits
                self.ax.set_xlim(-10, 10)
                self.ax.set_ylim(-10, 10)
                self.ax.set_zlim(-10, 10)
                
                # Set title based on current view
                view = self.view_var.get() if hasattr(self, 'view_var') and self.view_var else "3D"
                if view == "Top Down (XY)":
                    self.ax.set_title('Top Down View (XY Plane)')
                elif view == "Front (XZ)":
                    self.ax.set_title('Front View (XZ Plane)')
                elif view == "Side (YZ)":
                    self.ax.set_title('Side View (YZ Plane)')
                else:
                    self.ax.set_title('3D View')
            
            # Draw the room space as a box
            self.ax.plot([-5, 5, 5, -5, -5], [-5, -5, 5, 5, -5], [-0.1, -0.1, -0.1, -0.1, -0.1], 'k-', alpha=0.3)
            
            # Plot all cameras in the current scene if available
            if hasattr(self, 'current_scene') and self.current_scene and 'cameras' in self.current_scene:
                for camera_id, camera_data in self.current_scene['cameras'].items():
                    pos = camera_data.get('position', {})
                    rot = camera_data.get('rotation', {})
                    
                    x = pos.get('x', 0.0)
                    y = pos.get('y', 0.0)
                    z = pos.get('z', 0.0)
                    
                    # Add a sphere for the camera
                    self.ax.scatter([x], [y], [z], color='blue', s=100, label=f'Camera {camera_id}')
                    
                    # Add camera label
                    self.ax.text(x, y, z, f' {camera_id}', color='black', fontsize=9)
                    
                    # Draw camera orientation (simplified representation)
                    # We'll use the pan and tilt angles to draw a line representing camera direction
                    pan = np.radians(rot.get('pan', 0.0))
                    tilt = np.radians(rot.get('tilt', 0.0))
                    
                    # Calculate direction vector using pan and tilt angles
                    dx = np.cos(tilt) * np.sin(pan)
                    dy = np.cos(tilt) * np.cos(pan)
                    dz = np.sin(tilt)
                    
                    # Scale the vector
                    direction_length = 1.0
                    dx *= direction_length
                    dy *= direction_length
                    dz *= direction_length
                    
                    # Draw the direction line
                    self.ax.plot([x, x+dx], [y, y+dy], [z, z+dz], 'r-', linewidth=2)
            
            # Also draw the currently selected camera with different color if not in the scene yet
            # First check if all the required position attributes are available
            has_all_position_attrs = all(hasattr(self, attr) for attr in 
                                       ['x_position', 'y_position', 'z_position', 
                                        'pan_angle', 'tilt_angle', 'roll_angle'])
            
            if (hasattr(self, 'camera_selector') and 
                self.camera_selector.get() and 
                has_all_position_attrs):
                
                selected_camera = self.camera_selector.get()
                is_in_current_scene = (hasattr(self, 'current_scene') and 
                                       self.current_scene and 
                                       'cameras' in self.current_scene and 
                                       selected_camera in self.current_scene['cameras'])
                
                if not is_in_current_scene:
                    try:
                        # Safely access the entry values
                        x = float(self.x_position['entry'].get())
                        y = float(self.y_position['entry'].get())
                        z = float(self.z_position['entry'].get())
                        
                        pan = np.radians(float(self.pan_angle['entry'].get()))
                        tilt = np.radians(float(self.tilt_angle['entry'].get()))
                        
                        # Draw the camera
                        self.ax.scatter([x], [y], [z], color='green', s=100, label=f'Camera {selected_camera} (Editing)')
                        
                        # Add camera label
                        self.ax.text(x, y, z, f' {selected_camera}', color='black', fontsize=9)
                        
                        # Draw orientation
                        dx = np.cos(tilt) * np.sin(pan) * 1.0
                        dy = np.cos(tilt) * np.cos(pan) * 1.0
                        dz = np.sin(tilt) * 1.0
                        
                        self.ax.plot([x, x+dx], [y, y+dy], [z, z+dz], 'g-', linewidth=2)
                    except (ValueError, KeyError, AttributeError) as e:
                        # Handle invalid values or missing elements
                        self.logger.warning(f"Could not draw camera {selected_camera} due to invalid position values: {str(e)}")
            
            # Add a grid for better spatial understanding
            self.ax.grid(True)
            
            # Draw the updated visualization
            self.canvas.draw()
            
        except Exception as e:
            self.logger.error(f"Error updating position visualization: {e}")
            # Don't re-raise the exception to prevent UI crashes

    def setup_advanced_settings(self, tab):
        """Set up the advanced settings tab."""
        # Create a frame for advanced settings
        advanced_frame = ttk.Frame(tab, padding=10)
        advanced_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add a header
        header = ttk.Label(advanced_frame, text="Advanced Camera Settings", style='SubHeader.TLabel')
        header.pack(anchor=tk.W, pady=(0, 10))
        
        # Camera calibration settings
        calib_frame = ttk.LabelFrame(advanced_frame, text="Camera Calibration")
        calib_frame.pack(fill=tk.X, pady=10)
        
        # Calibration status
        status_frame = ttk.Frame(calib_frame)
        status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(status_frame, text="Status:").pack(side=tk.LEFT, padx=(0, 5))
        self.calib_status = ttk.Label(status_frame, text="Not Calibrated", foreground="red")
        self.calib_status.pack(side=tk.LEFT)
        
        # Calibration actions
        button_frame = ttk.Frame(calib_frame)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        calib_button = ttk.Button(button_frame, text="Calibrate Camera", 
                                command=self.calibrate_camera)
        calib_button.pack(side=tk.LEFT, padx=(0, 5))
        
        reset_calib_button = ttk.Button(button_frame, text="Reset Calibration", 
                                      command=self.reset_calibration)
        reset_calib_button.pack(side=tk.LEFT)
        
        # Distortion Correction section
        dist_frame = ttk.LabelFrame(advanced_frame, text="Distortion Correction")
        dist_frame.pack(fill=tk.X, pady=10)
        
        # Enable/disable distortion correction
        enable_frame = ttk.Frame(dist_frame)
        enable_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.distortion_var = tk.BooleanVar(value=False)
        distortion_check = ttk.Checkbutton(enable_frame, text="Enable Distortion Correction", 
                                          variable=self.distortion_var, 
                                          command=self.toggle_distortion_correction)
        distortion_check.pack(anchor=tk.W)
        
        # Performance section
        perf_frame = ttk.LabelFrame(advanced_frame, text="Performance Settings")
        perf_frame.pack(fill=tk.X, pady=10)
        
        # Resolution settings
        res_frame = ttk.Frame(perf_frame)
        res_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(res_frame, text="Resolution:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.resolution_var = tk.StringVar(value="640x480")
        resolution_combo = ttk.Combobox(res_frame, textvariable=self.resolution_var, 
                                      values=["320x240", "640x480", "1280x720", "1920x1080"], 
                                      state="readonly", width=15)
        resolution_combo.pack(side=tk.LEFT)
        resolution_combo.bind("<<ComboboxSelected>>", self.change_resolution)
        
        # FPS limit
        fps_frame = ttk.Frame(perf_frame)
        fps_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(fps_frame, text="FPS Limit:").pack(side=tk.LEFT, padx=(0, 5))
        
        self.fps_var = tk.StringVar(value="30")
        fps_combo = ttk.Combobox(fps_frame, textvariable=self.fps_var, 
                               values=["15", "30", "60", "No Limit"], 
                               state="readonly", width=15)
        fps_combo.pack(side=tk.LEFT)
        fps_combo.bind("<<ComboboxSelected>>", self.change_fps_limit)
        
        # Apply button for advanced settings
        apply_button = ttk.Button(advanced_frame, text="Apply Advanced Settings", 
                                command=self.apply_advanced_settings, style='Action.TButton')
        apply_button.pack(anchor=tk.E, pady=10)

    def calibrate_camera(self):
        """Start the camera calibration process."""
        # This would typically launch a calibration wizard in a real implementation
        messagebox.showinfo("Calibration", "Camera calibration feature not yet implemented.")

    def reset_calibration(self):
        """Reset camera calibration to defaults."""
        if messagebox.askyesno("Reset Calibration", "Are you sure you want to reset the calibration?"):
            self.calib_status.config(text="Not Calibrated", foreground="red")
            messagebox.showinfo("Reset Calibration", "Calibration has been reset.")

    def toggle_distortion_correction(self):
        """Toggle distortion correction on/off."""
        is_enabled = self.distortion_var.get()
        status = "enabled" if is_enabled else "disabled"
        self.status_bar.config(text=f"Distortion correction {status}")

    def change_resolution(self, event=None):
        """Change the camera resolution."""
        resolution = self.resolution_var.get()
        self.status_bar.config(text=f"Resolution changed to {resolution}")

    def change_fps_limit(self, event=None):
        """Change the FPS limit."""
        fps = self.fps_var.get()
        limit_text = f"{fps} FPS" if fps != "No Limit" else "unlimited"
        self.status_bar.config(text=f"FPS limit set to {limit_text}")

    def apply_advanced_settings(self):
        """Apply advanced camera settings."""
        selected_camera = self.camera_selector.get()
        if not selected_camera:
            messagebox.showwarning("No Camera Selected", "Please select a camera first.")
            return
            
        # Apply settings to the selected camera
        self.status_bar.config(text=f"Applied advanced settings to camera {selected_camera}")
        messagebox.showinfo("Settings Applied", f"Advanced settings applied to camera {selected_camera}.")

    def perform_cleanup(self):
        """Perform periodic cleanup to manage memory usage."""
        if not hasattr(self, 'is_running') or not self.is_running:
            return
            
        current_time = time.time()
        
        # Only run full garbage collection periodically
        if current_time - self.last_gc_time > self.gc_interval:
            self.logger.debug("Performing periodic memory cleanup")
            
            # Clear any stored images for non-visible cameras
            for camera_id in self.camera_views:
                canvas = self.camera_views[camera_id]['canvas']
                if not canvas.winfo_viewable() and 'image' in self.camera_views[camera_id]:
                    self.camera_views[camera_id]['image'] = None
            
            # Suggest garbage collection to Python
            import gc
            gc.collect()
            
            self.last_gc_time = current_time
        
        # Schedule next cleanup
        self.after(self.gc_interval * 1000, self.perform_cleanup)

    def on_camera_error(self, camera_id, error_message):
        """Handle camera errors and attempt recovery."""
        self.logger.error(f"Camera {camera_id} error: {error_message}")
        
        # Update the camera status in the UI
        if camera_id in self.camera_views and 'status' in self.camera_views[camera_id]:
            self.camera_views[camera_id]['status'].config(text="Error", foreground="red")
        
        # Check if this is a critical error
        is_critical = False
        if 'init' in str(error_message).lower() or 'open' in str(error_message).lower():
            is_critical = True
        
        # For critical errors, try to recover
        if is_critical and self.camera_manager:
            self.logger.info(f"Attempting to recover camera {camera_id}")
            
            # Update status
            if camera_id in self.camera_views:
                self.camera_views[camera_id]['status'].config(text="Reconnecting...", foreground="orange")
            
            # Attempt to recover in a separate thread to avoid blocking UI
            threading.Thread(
                target=self._attempt_camera_recovery,
                args=(camera_id,),
                daemon=True
            ).start()

    def _attempt_camera_recovery(self, camera_id):
        """Attempt to recover a failed camera connection."""
        try:
            # Make sure camera manager exists
            if not self.camera_manager:
                return
                
            # Try to close and reopen the camera
            success = self.camera_manager.reconnect_camera(camera_id)
            
            # Update status based on result
            if success and camera_id in self.camera_views:
                self.logger.info(f"Successfully recovered camera {camera_id}")
                self.camera_views[camera_id]['status'].config(text="Recovered", foreground="green")
            else:
                self.logger.warning(f"Failed to recover camera {camera_id}")
                if camera_id in self.camera_views:
                    self.camera_views[camera_id]['status'].config(text="Offline", foreground="red")
        except Exception as e:
            self.logger.error(f"Error during camera recovery: {e}")

    def start_system_monitoring(self):
        """Start monitoring system resources."""
        self.system_monitoring_active = True
        self.update_system_stats()

    def update_system_stats(self):
        """Update system resource statistics."""
        if not hasattr(self, 'system_monitoring_active') or not self.system_monitoring_active:
            return
        
        try:
            # Get CPU and memory usage
            self.system_stats['cpu'] = psutil.cpu_percent()
            self.system_stats['memory'] = psutil.virtual_memory().percent
            
            # Update status bar with resource info
            status_text = f"CPU: {self.system_stats['cpu']}% | Memory: {self.system_stats['memory']}%"
            
            # Add average FPS if available
            if self.system_stats['fps'] and len(self.system_stats['fps']) > 0:
                avg_fps = sum(self.system_stats['fps'].values()) / len(self.system_stats['fps'])
                status_text += f" | Avg FPS: {avg_fps:.1f}"
                
            # Add camera count
            if hasattr(self, 'camera_manager') and self.camera_manager and self.camera_manager.cameras:
                status_text += f" | Cameras: {len(self.camera_manager.cameras)}"
            
            # Update status bar
            if hasattr(self, 'status_bar'):
                current_text = self.status_bar.cget('text')
                # Only update if not showing a temporary message
                if current_text.startswith("CPU:") or current_text == "Ready" or not current_text:
                    self.status_bar.config(text=status_text)
            
            # Check for resource issues
            if self.system_stats['cpu'] > 90 or self.system_stats['memory'] > 90:
                self.logger.warning(f"System resources running high: CPU={self.system_stats['cpu']}%, Memory={self.system_stats['memory']}%")
                
                # Take action if resources are critically low
                if self.system_stats['cpu'] > 95 or self.system_stats['memory'] > 95:
                    self.logger.error("System resources critically low! Reducing workload.")
                    self.reduce_system_load()
        
        except Exception as e:
            self.logger.error(f"Error updating system stats: {e}")
        
        # Schedule next update
        self.after(5000, self.update_system_stats)  # Update every 5 seconds

    def reduce_system_load(self):
        """Take actions to reduce system load when resources are critically low."""
        # Stop updating less important cameras
        if hasattr(self, 'camera_views') and len(self.camera_views) > 2:
            self.logger.info("Reducing camera view updates to conserve resources")
            # Implement selective camera updates here
            
        # Force garbage collection
        import gc
        gc.collect()
        
        # Show warning to user
        if hasattr(self, 'status_bar'):
            self.status_bar.config(text="WARNING: System resources critically low. Performance may be affected.")


if __name__ == "__main__":
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run the application
    app = TheEyesGUI()
    app.mainloop() 