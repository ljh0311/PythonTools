import tkinter as tk
from tkinter import ttk
import threading
import time
import cv2
import numpy as np
import logging
import os
import open3d as o3d
from PIL import Image, ImageTk

from src.image_processing.processor import ImageProcessor
from src.feature_matching.matcher import FeatureMatcher
from src.reconstruction.reconstructor import Reconstructor
from src.rendering.renderer import Renderer
from src.reconstruction.single_cam_reconstructor import SingleCamReconstructor


class Tooltip:
    """
    Creates a tooltip for a given widget.
    
    This is a simple implementation of tooltips that will create a small text
    box when hovering over a widget with a given text.
    """
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)
    
    def show_tooltip(self, event=None):
        """Display the tooltip."""
        x, y, _, _ = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 25
        
        # Create a toplevel window
        self.tooltip_window = tk.Toplevel(self.widget)
        # Remove the window decorations
        self.tooltip_window.wm_overrideredirect(True)
        self.tooltip_window.wm_geometry(f"+{x}+{y}")
        
        # Create the tooltip label
        label = ttk.Label(self.tooltip_window, text=self.text, 
                          background="#ffffe0", relief="solid", borderwidth=1,
                          wraplength=250, justify="left", padding=(5, 2))
        label.pack()
    
    def hide_tooltip(self, event=None):
        """Hide the tooltip."""
        if self.tooltip_window:
            self.tooltip_window.destroy()
            self.tooltip_window = None


class VisualizationTab(ttk.Frame):
    """Class to handle 3D visualization tab in the GUI."""

    def __init__(self, parent, camera_manager, config):
        super().__init__(parent)  # Initialize the ttk.Frame
        self.parent = parent
        self.camera_manager = camera_manager
        self.config = config
        self.logger = logging.getLogger("the_eyes.visualization_tab")

        # Initialize with default configs if they don't exist
        if 'visualization' not in self.config:
            self.config['visualization'] = {'mode': 'single'}
            
        if 'single_cam_feature_detection' not in self.config:
            self.config['single_cam_feature_detection'] = SingleCamReconstructor.DEFAULT_CONFIG['feature_detection'].copy()
        if 'single_cam_visualization' not in self.config:
            self.config['single_cam_visualization'] = SingleCamReconstructor.DEFAULT_CONFIG['visualization'].copy()

        # Initialize processing components
        self.image_processor = ImageProcessor(config.get("image_processing", {}))
        self.feature_matcher = FeatureMatcher(config.get("feature_matching", {}))
        self.reconstructor = Reconstructor(config.get("reconstruction", {}))
        self.single_cam_reconstructor = SingleCamReconstructor(config)
        self.renderer = Renderer(config.get("rendering", {}))

        # Set up the tab
        self.tab = parent
        self.setup_ui()

        # Visualization control
        self.is_running = False
        self.update_thread = None
        self.use_single_camera = True  # Default to single camera mode for compatibility
        self.show_config_panel = False # Config panel toggle state

    def setup_ui(self):
        """Set up the user interface for the visualization tab."""
        description_frame = ttk.Frame(self)
        description_frame.pack(side=tk.TOP, fill=tk.X, padx=10, pady=5)
        
        # Add a description of the visualization tab
        description_text = ("This tab displays a 3D visualization of the processed data. "
                           "Single camera mode reconstructs depth from a single camera view, while "
                           "multi-camera mode uses triangulation between cameras.")
        description_label = ttk.Label(description_frame, text=description_text, wraplength=600)
        description_label.pack(side=tk.TOP, padx=5, pady=5)
        
        # Main content frame
        content_frame = ttk.Frame(self)
        content_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Left side - visualization canvas
        viz_frame = ttk.LabelFrame(content_frame, text="3D Visualization")
        viz_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Canvas for visualization
        self.canvas = tk.Canvas(viz_frame, width=800, height=600, bg="black")
        self.canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add initial message to show the canvas is working
        self.canvas.create_text(400, 300, text="3D Visualization Ready\nClick 'Start Visualization' to begin", 
                              fill="white", font=("Arial", 14), justify="center")
        
        # Log that the canvas is created
        self.logger.info("3D visualization canvas created")
        
        # Legend frame below the canvas
        legend_frame = ttk.Frame(viz_frame)
        legend_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        
        # Add legend elements
        legend_label = ttk.Label(legend_frame, text="Visualization Legend:", font=("Arial", 10, "bold"))
        legend_label.pack(side=tk.TOP, anchor=tk.W)
        
        # Points explanation
        points_frame = ttk.Frame(legend_frame)
        points_frame.pack(side=tk.TOP, fill=tk.X, pady=2)
        points_label = ttk.Label(points_frame, text="• Points: ", font=("Arial", 9, "bold"))
        points_label.pack(side=tk.LEFT)
        points_desc = ttk.Label(points_frame, text="3D feature points detected in the image(s)", font=("Arial", 9))
        points_desc.pack(side=tk.LEFT)
        
        # Color modes explanation
        color_frame = ttk.Frame(legend_frame)
        color_frame.pack(side=tk.TOP, fill=tk.X, pady=2)
        color_label = ttk.Label(color_frame, text="• Color modes: ", font=("Arial", 9, "bold"))
        color_label.pack(side=tk.LEFT)
        color_desc = ttk.Label(color_frame, 
                              text="RGB: natural colors, Depth: blue-to-red by distance, Confidence: green-to-red by detection confidence", 
                              font=("Arial", 9), wraplength=600)
        color_desc.pack(side=tk.LEFT)
        
        # Right side - settings panel
        settings_frame = ttk.LabelFrame(content_frame, text="Visualization Settings")
        settings_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)
        
        # Settings notebook (tabbed interface)
        settings_notebook = ttk.Notebook(settings_frame)
        settings_notebook.pack(side=tk.TOP, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Tab 1: Camera Mode
        camera_mode_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(camera_mode_frame, text="Camera Mode")
        
        # Camera mode selection
        camera_mode_label = ttk.Label(camera_mode_frame, text="Camera Mode:")
        camera_mode_label.pack(side=tk.TOP, anchor=tk.W, padx=5, pady=5)
        
        camera_mode_frame_inner = ttk.Frame(camera_mode_frame)
        camera_mode_frame_inner.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        self.camera_mode_var = tk.StringVar(value="single")
        
        single_cam_radio = ttk.Radiobutton(
            camera_mode_frame_inner, 
            text="Single Camera", 
            variable=self.camera_mode_var, 
            value="single",
            command=self.update_camera_mode
        )
        single_cam_radio.pack(side=tk.LEFT, padx=5, pady=5)
        self.create_tooltip(single_cam_radio, "Use depth estimation from a single camera view")
        
        multi_cam_radio = ttk.Radiobutton(
            camera_mode_frame_inner, 
            text="Multi Camera", 
            variable=self.camera_mode_var, 
            value="multi",
            command=self.update_camera_mode
        )
        multi_cam_radio.pack(side=tk.LEFT, padx=5, pady=5)
        self.create_tooltip(multi_cam_radio, "Use triangulation between multiple cameras")
        
        # Feature detection algorithm selection
        feature_frame = ttk.LabelFrame(camera_mode_frame, text="Feature Detection")
        feature_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=10)
        
        # Algorithm selector
        algo_frame = ttk.Frame(feature_frame)
        algo_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        algo_label = ttk.Label(algo_frame, text="Algorithm:")
        algo_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.feature_algo_var = tk.StringVar(value="sift")
        
        algo_combobox = ttk.Combobox(
            algo_frame, 
            textvariable=self.feature_algo_var,
            values=["sift", "orb", "surf", "akaze", "brisk"],
            state="readonly",
            width=10
        )
        algo_combobox.pack(side=tk.LEFT, padx=5, pady=5)
        algo_combobox.bind("<<ComboboxSelected>>", self.update_feature_algorithm)
        self.create_tooltip(algo_combobox, "Select feature detection algorithm")
        
        # Feature count adjustment
        feature_count_frame = ttk.Frame(feature_frame)
        feature_count_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        count_label = ttk.Label(feature_count_frame, text="Max Features:")
        count_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.feature_count_var = tk.IntVar(value=2000)
        
        feature_count_slider = ttk.Scale(
            feature_count_frame,
            from_=500,
            to=5000,
            variable=self.feature_count_var,
            orient=tk.HORIZONTAL,
            command=self.update_feature_count
        )
        feature_count_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        
        # Count display
        self.count_display_label = ttk.Label(feature_count_frame, text="2000")
        self.count_display_label.pack(side=tk.LEFT, padx=5, pady=5)
        self.create_tooltip(feature_count_slider, "Maximum number of features to detect")
        
        # Tab 2: View Controls
        view_control_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(view_control_frame, text="View Controls")
        
        # Auto-rotation control
        auto_rotate_frame = ttk.Frame(view_control_frame)
        auto_rotate_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        self.auto_rotate_var = tk.BooleanVar(value=True)
        auto_rotate_check = ttk.Checkbutton(
            auto_rotate_frame,
            text="Auto-rotate view",
            variable=self.auto_rotate_var
        )
        auto_rotate_check.pack(side=tk.LEFT, padx=5, pady=5)
        self.create_tooltip(auto_rotate_check, "Automatically rotate the 3D view to show all angles")
        
        # Manual rotation controls
        rotation_frame = ttk.LabelFrame(view_control_frame, text="Manual Rotation")
        rotation_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        # Horizontal rotation (yaw)
        yaw_frame = ttk.Frame(rotation_frame)
        yaw_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        yaw_label = ttk.Label(yaw_frame, text="Horizontal:")
        yaw_label.pack(side=tk.LEFT, padx=5)
        
        self.yaw_var = tk.DoubleVar(value=0.0)
        yaw_slider = ttk.Scale(
            yaw_frame,
            from_=0,
            to=360,
            variable=self.yaw_var,
            orient=tk.HORIZONTAL
        )
        yaw_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.create_tooltip(yaw_slider, "Control horizontal rotation (0-360°)")
        
        # Vertical rotation (pitch)
        pitch_frame = ttk.Frame(rotation_frame)
        pitch_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        pitch_label = ttk.Label(pitch_frame, text="Vertical:")
        pitch_label.pack(side=tk.LEFT, padx=5)
        
        self.pitch_var = tk.DoubleVar(value=20.0)
        pitch_slider = ttk.Scale(
            pitch_frame,
            from_=-90,
            to=90,
            variable=self.pitch_var,
            orient=tk.HORIZONTAL
        )
        pitch_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.create_tooltip(pitch_slider, "Control vertical rotation (-90° to 90°)")
        
        # Zoom control
        zoom_frame = ttk.LabelFrame(view_control_frame, text="Zoom")
        zoom_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        self.zoom_var = tk.DoubleVar(value=0.8)
        zoom_slider = ttk.Scale(
            zoom_frame,
            from_=0.1,
            to=2.0,
            variable=self.zoom_var,
            orient=tk.HORIZONTAL
        )
        zoom_slider.pack(side=tk.TOP, fill=tk.X, expand=True, padx=5, pady=5)
        self.create_tooltip(zoom_slider, "Adjust zoom level (0.1-2.0x)")
        
        # Tab 3: Color Settings
        color_settings_frame = ttk.Frame(settings_notebook)
        settings_notebook.add(color_settings_frame, text="Color Settings")
        
        # Color mode
        color_mode_label = ttk.Label(color_settings_frame, text="Color Mode:")
        color_mode_label.pack(side=tk.TOP, anchor=tk.W, padx=5, pady=5)
        
        self.color_mode_var = tk.StringVar(value="rgb")
        
        color_mode_frame = ttk.Frame(color_settings_frame)
        color_mode_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        rgb_radio = ttk.Radiobutton(
            color_mode_frame,
            text="RGB",
            variable=self.color_mode_var,
            value="rgb",
            command=self.update_color_mode
        )
        rgb_radio.pack(side=tk.LEFT, padx=5, pady=5)
        self.create_tooltip(rgb_radio, "Use natural colors from the camera feed")
        
        depth_radio = ttk.Radiobutton(
            color_mode_frame,
            text="Depth",
            variable=self.color_mode_var,
            value="depth",
            command=self.update_color_mode
        )
        depth_radio.pack(side=tk.LEFT, padx=5, pady=5)
        self.create_tooltip(depth_radio, "Color points by their distance from the camera (blue = near, red = far)")
        
        confidence_radio = ttk.Radiobutton(
            color_mode_frame,
            text="Confidence",
            variable=self.color_mode_var,
            value="confidence",
            command=self.update_color_mode
        )
        confidence_radio.pack(side=tk.LEFT, padx=5, pady=5)
        self.create_tooltip(confidence_radio, "Color points by detection confidence (green = high, red = low)")
        
        # Point size
        point_size_frame = ttk.Frame(color_settings_frame)
        point_size_frame.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        
        point_size_label = ttk.Label(point_size_frame, text="Point Size:")
        point_size_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        self.point_size_var = tk.DoubleVar(value=5.0)
        point_size_slider = ttk.Scale(
            point_size_frame,
            from_=1.0,
            to=10.0,
            variable=self.point_size_var,
            orient=tk.HORIZONTAL,
            command=self.update_point_size
        )
        point_size_slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, pady=5)
        self.create_tooltip(point_size_slider, "Adjust the size of points in the visualization (1-10 pixels)")
        
        # Button frame
        button_frame = ttk.Frame(settings_frame)
        button_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=10)
        
        # Add a more prominent start button in the settings panel
        self.start_viz_button = ttk.Button(
            button_frame, 
            text="Start Visualization",
            command=self.toggle_visualization,
            style='Action.TButton'  # Use the action style for emphasis
        )
        self.start_viz_button.pack(side=tk.BOTTOM, fill=tk.X, padx=5, pady=5)
        self.create_tooltip(self.start_viz_button, "Start or stop the 3D visualization")
        
        # Status bar at the bottom
        status_frame = ttk.Frame(self)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(status_frame, text="Ready")
        self.status_label.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Initial state
        self.use_single_camera = True
        self.is_running = False

    def create_tooltip(self, widget, text):
        """Create a tooltip for a widget."""
        tooltip = Tooltip(widget, text)
        return tooltip
    
    def update_camera_mode(self):
        """Update the camera mode based on the selected radio button."""
        mode = self.camera_mode_var.get()
        self.use_single_camera = (mode == "single")
        self.status_label.config(text=f"Camera mode set to: {'Single' if self.use_single_camera else 'Multi'}")
        
        # Update config
        if self.use_single_camera:
            self.config['visualization']['mode'] = 'single'
        else:
            self.config['visualization']['mode'] = 'multi'
    
    def update_color_mode(self):
        """Update the color mode based on the selected radio button."""
        mode = self.color_mode_var.get()
        self.config['single_cam_visualization']['color_mode'] = mode
        self.status_label.config(text=f"Color mode set to: {mode}")
        
        # Update the visualization legend
        self.update_visualization_legend()
    
    def update_point_size(self, value=None):
        """Update the point size based on the slider value."""
        size = self.point_size_var.get()
        self.config['single_cam_visualization']['point_size'] = size
        self.status_label.config(text=f"Point size set to: {size:.1f}")
    
    def update_visualization_legend(self):
        """Update the visualization legend based on current settings."""
        # This would update a dynamic legend based on current settings
        # For now, we're using static text in the UI setup
        pass

    def update_camera_info(self):
        """Update camera information from the camera manager."""
        # This method updates the local camera information from the camera manager
        # It's called before starting the visualization to ensure we have the latest camera data
        try:
            if self.camera_manager:
                # Get latest camera information if needed
                self.camera_manager.update_info()
                
                # Log the camera information
                camera_count = len(self.camera_manager.cameras) if self.camera_manager else 0
                self.logger.info(f"Found {camera_count} cameras for visualization")
                
                # Update settings based on camera count
                if camera_count < 2 and not self.use_single_camera:
                    # Force to single camera mode if we don't have enough cameras for multi-camera mode
                    self.camera_mode_var.set("single")
                    self.use_single_camera = True
                    self.status_label.config(text="Switched to single camera mode (need 2+ cameras for multi-cam)")
        except Exception as e:
            self.logger.error(f"Error updating camera info: {e}")
            self.status_label.config(text=f"Error updating camera info: {str(e)[:50]}")

    def update_mode(self):
        """Update visualization mode based on radio selection."""
        self.use_single_camera = (self.camera_mode_var.get() == "single")
        
        # Check if mode is valid given camera count
        camera_count = len(self.camera_manager.cameras) if self.camera_manager else 0
        
        if not self.use_single_camera and camera_count < 2:
            self.camera_mode_var.set("single")
            self.use_single_camera = True
            self.status_label.config(text="Need 2+ cameras for multi-cam mode")

    def toggle_visualization(self):
        """Toggle visualization on/off."""
        if self.is_running:
            # Stop visualization
            self.is_running = False
            if self.update_thread:
                self.update_thread.join(1.0)
            self.start_viz_button.config(text="Start Visualization")
            self.status_label.config(text="Stopped")
            
            # Reset the canvas to show ready message
            self.canvas.delete("all")
            self.canvas.create_text(400, 300, text="3D Visualization Ready\nClick 'Start Visualization' to begin", 
                                  fill="white", font=("Arial", 14), justify="center")
        else:
            # Start visualization
            self.update_camera_info()
            
            camera_count = len(self.camera_manager.cameras) if self.camera_manager else 0
            
            if camera_count == 0:
                self.status_label.config(text="Warning: No cameras connected. Will show demo visualization.")
            
            if not self.use_single_camera and camera_count < 2:
                self.status_label.config(text="Warning: Need at least 2 cameras for multi-cam mode. Using single camera mode.")
                self.use_single_camera = True
                self.camera_mode_var.set("single")
                return
                
            # Show initializing message
            self.canvas.delete("all")
            self.canvas.create_text(400, 300, text="Initializing 3D visualization...", 
                                 fill="white", font=("Arial", 14), justify="center")
            self.update_idletasks()  # Force UI update
                
            self.is_running = True
            self.update_thread = threading.Thread(target=self.update_visualization)
            self.update_thread.daemon = True
            self.update_thread.start()
            
            self.start_viz_button.config(text="Stop Visualization")
            self.status_label.config(text="Running visualization...")

    def update_visualization(self):
        """Update the visualization in a background thread."""
        temp_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "temp")
        os.makedirs(temp_dir, exist_ok=True)
        
        try:
            # Create Open3D visualizer for off-screen rendering
            self.logger.info("Initializing Open3D visualizer")
            vis = o3d.visualization.Visualizer()
            vis.create_window(visible=False, width=800, height=600)
            self.logger.info("Open3D visualizer initialized successfully")
        except Exception as e:
            self.logger.error(f"Failed to initialize Open3D visualizer: {e}")
            # Show error message in the canvas
            self.parent.after(0, lambda: self.status_label.config(text=f"Error: Failed to initialize 3D visualizer"))
            self.parent.after(0, lambda: self.canvas.delete("all"))
            self.parent.after(0, lambda: self.canvas.create_text(400, 300, 
                               text=f"Failed to initialize 3D visualizer:\n{str(e)[:100]}...", 
                               fill="red", font=("Arial", 12), justify="center"))
            self.is_running = False
            return
        
        # Initialize view parameters
        view_rotation = 0.0
        view_elevation = 20.0
        view_zoom = 0.8
        last_update_time = time.time()
        feature_count = 0
        
        # Create a dummy point cloud for initial visualization
        try:
            dummy_point_cloud = o3d.geometry.PointCloud()
            dummy_points = np.random.rand(100, 3)  # 100 random points
            dummy_point_cloud.points = o3d.utility.Vector3dVector(dummy_points)
            dummy_point_cloud.paint_uniform_color([0.5, 0.5, 1.0])  # Light blue color
        except Exception as e:
            self.logger.error(f"Failed to create dummy point cloud: {e}")
            # Not critical, continue without it
            dummy_point_cloud = None
        
        while self.is_running:
            try:
                # Capture frames
                frames = self.camera_manager.capture_all()
                
                # Variable to store the point cloud we'll visualize
                point_cloud = None
                
                if not frames:
                    self.logger.warning("No camera frames captured, using dummy visualization")
                    # Use the dummy point cloud if available
                    if dummy_point_cloud is not None:
                        point_cloud = dummy_point_cloud
                    else:
                        # Create a simple placeholder point cloud
                        point_cloud = o3d.geometry.PointCloud()
                        placeholder_points = np.array([[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]])  # Origin and axis points
                        point_cloud.points = o3d.utility.Vector3dVector(placeholder_points)
                        colors = np.array([[1, 1, 1], [1, 0, 0], [0, 1, 0], [0, 0, 1]])  # White, Red, Green, Blue
                        point_cloud.colors = o3d.utility.Vector3dVector(colors)
                else:
                    # Process frames
                    processed_frames = self.image_processor.process_batch(frames)
                    
                    # Add stat overlay
                    camera_frames = {}
                    for cam_id, frame in frames.items():
                        height, width = frame.shape[:2]
                        camera_frames[cam_id] = frame.copy()
                        # Add timestamp
                        timestamp = time.strftime("%H:%M:%S")
                        cv2.putText(camera_frames[cam_id], f"Cam: {cam_id} | Time: {timestamp}",
                                  (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                    
                    if self.use_single_camera:
                        # Single camera mode - use the first camera
                        cam_id = list(processed_frames.keys())[0]
                        processed_frame = processed_frames[cam_id]
                        
                        # Get the feature detection method from config
                        method = self.config['single_cam_feature_detection'].get('method', 'sift')
                        max_features = self.config['single_cam_feature_detection'].get('max_features', 2000)
                        
                        # Generate point cloud using single camera reconstructor
                        point_cloud, features = self.single_cam_reconstructor.reconstruct(processed_frame)
                        
                        # Draw features on the camera frame for visualization
                        vis_frame = camera_frames[cam_id].copy()
                        
                        # Draw the detected feature points if available
                        if features is not None and hasattr(features, 'keypoints'):
                            # Draw keypoints
                            cv2.drawKeypoints(
                                vis_frame, 
                                features.keypoints, 
                                vis_frame, 
                                flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS
                            )
                            
                        # Add camera mode overlay
                        cv2.putText(vis_frame, "Mode: Single Camera", 
                                  (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                        
                        # Add feature detection method
                        cv2.putText(vis_frame, f"Method: {method.upper()}", 
                                  (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                        
                        # Count and display number of features
                        feature_count = len(point_cloud.points)
                        cv2.putText(vis_frame, f"Features: {feature_count}", 
                                  (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                        
                        # Replace original frame with visualization frame
                        camera_frames[cam_id] = vis_frame
                        
                    else:
                        # Multi camera mode - use feature matching and triangulation
                        # Extract and match features
                        features = self.feature_matcher.match_features(processed_frames)
                        
                        # Reconstruct 3D model
                        point_cloud, _ = self.reconstructor.reconstruct(features)
                        
                        # Visualize features on each camera view
                        if features and 'matches' in features:
                            # Create visualization frames
                            vis_frames = {}
                            for cam_id, frame in camera_frames.items():
                                vis_frames[cam_id] = frame.copy()
                            
                            # Draw keypoints on each camera
                            for cam_id, keypoints in features.get('keypoints', {}).items():
                                if cam_id in vis_frames and keypoints:
                                    cv2.drawKeypoints(
                                        vis_frames[cam_id],
                                        keypoints,
                                        vis_frames[cam_id],
                                        flags=cv2.DRAW_MATCHES_FLAGS_DRAW_RICH_KEYPOINTS
                                    )
                            
                            # Update camera frames with visualization frames
                            camera_frames = vis_frames
                        
                        # Add overlays to all cameras
                        for cam_id in camera_frames:
                            cv2.putText(camera_frames[cam_id], "Mode: Multi Camera", 
                                      (10, 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                            
                            # Add feature info
                            method = self.config['feature_matching'].get('detector', 'sift').upper()
                            cv2.putText(camera_frames[cam_id], f"Method: {method}", 
                                      (10, 75), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                            
                            # Count keypoints in this camera
                            if features and 'keypoints' in features and cam_id in features['keypoints']:
                                kp_count = len(features['keypoints'][cam_id])
                                cv2.putText(camera_frames[cam_id], f"Keypoints: {kp_count}", 
                                          (10, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2)
                        
                        # Count features
                        feature_count = len(point_cloud.points)
                
                # Auto-rotate the view for better visualization
                current_time = time.time()
                if current_time - last_update_time > 0.05:  # Control rotation speed
                    view_rotation += 0.5  # Rotate 0.5 degrees per update
                    if view_rotation >= 360:
                        view_rotation = 0
                    last_update_time = current_time
                
                # Render the point cloud to an image
                timestamp = int(time.time())
                render_path = os.path.join(temp_dir, f"render_{timestamp}.png")
                
                # Save a camera frame to display alongside the visualization
                camera_frame_path = os.path.join(temp_dir, f"camera_{timestamp}.png")
                if camera_frames:
                    first_cam_id = list(camera_frames.keys())[0]
                    cv2.imwrite(camera_frame_path, camera_frames[first_cam_id])
                
                # Clear previous geometries
                vis.clear_geometries()
                
                # Add the point cloud
                vis.add_geometry(point_cloud)
                
                # Set render options
                render_option = vis.get_render_option()
                render_option.point_size = self.config['single_cam_visualization'].get('point_size', 5.0)
                render_option.background_color = np.array([0.1, 0.1, 0.1])
                
                # Set view control
                ctr = vis.get_view_control()
                ctr.set_zoom(view_zoom)
                ctr.set_lookat([0, 0, 0])  # Look at center
                # Convert degrees to radians for rotation
                ctr.rotate(view_rotation, view_elevation)
                
                # Render to an image
                vis.poll_events()
                vis.update_renderer()
                vis.capture_screen_image(render_path)
                
                # Display the rendered image
                if os.path.exists(render_path):
                    # Prepare a composite image with the camera feed and visualization
                    render_img = cv2.imread(render_path)
                    
                    # Add visualization info overlay
                    cv2.putText(render_img, f"Points: {feature_count}", 
                              (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
                    
                    color_mode = self.config['single_cam_visualization'].get('color_mode', 'rgb')
                    cv2.putText(render_img, f"Color mode: {color_mode}", 
                              (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200, 200, 200), 2)
                    
                    # Instructions text
                    cv2.putText(render_img, "View auto-rotates for better perspective", 
                              (10, render_img.shape[0] - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (150, 150, 150), 2)
                    
                    if os.path.exists(camera_frame_path):
                        # Load camera frame and resize to match visualization height
                        cam_img = cv2.imread(camera_frame_path)
                        if cam_img is not None:
                            target_height = render_img.shape[0]
                            aspect_ratio = cam_img.shape[1] / cam_img.shape[0]
                            target_width = int(target_height * aspect_ratio)
                            cam_img = cv2.resize(cam_img, (target_width, target_height))
                            
                            # Create composite image
                            composite_width = render_img.shape[1] + cam_img.shape[1]
                            composite_img = np.zeros((render_img.shape[0], composite_width, 3), dtype=np.uint8)
                            composite_img[:, :render_img.shape[1]] = render_img
                            composite_img[:, render_img.shape[1]:] = cam_img
                            
                            # Save composite
                            composite_path = os.path.join(temp_dir, f"composite_{timestamp}.png")
                            cv2.imwrite(composite_path, composite_img)
                            
                            # Use the composite instead
                            if os.path.exists(composite_path):
                                img = Image.open(composite_path)
                                # Remove after loading
                                try:
                                    os.remove(composite_path)
                                except:
                                    pass
                            else:
                                img = Image.open(render_path)
                        else:
                            img = Image.open(render_path)
                    else:
                        img = Image.open(render_path)
                    
                    # Resize to fit canvas
                    canvas_width = self.canvas.winfo_width()
                    canvas_height = self.canvas.winfo_height()
                    
                    if canvas_width > 1 and canvas_height > 1:
                        img = img.resize((canvas_width, canvas_height), Image.LANCZOS)
                    
                    # Display
                    img_tk = ImageTk.PhotoImage(image=img)
                    self.canvas.delete("all")  # Clear previous content
                    self.canvas.img = img_tk
                    self.canvas.create_image(0, 0, anchor=tk.NW, image=img_tk)
                    
                    # Remove the files after displaying
                    try:
                        os.remove(render_path)
                        if os.path.exists(camera_frame_path):
                            os.remove(camera_frame_path)
                    except:
                        pass
                
            except Exception as e:
                self.logger.error(f"Error updating visualization: {e}")
                if self.is_running:  # Only update if still running
                    error_msg = str(e)
                    if len(error_msg) > 50:
                        error_msg = error_msg[:50] + "..."
                    self.parent.after(0, lambda: self.status_label.config(text=f"Error: {error_msg}"))
            
            # Sleep to limit updates
            time.sleep(0.1)
        
        # Clean up
        vis.destroy_window()

    def update_feature_algorithm(self, event=None):
        """Update the feature detection algorithm."""
        algo = self.feature_algo_var.get()
        
        # Update configuration
        if 'single_cam_feature_detection' not in self.config:
            self.config['single_cam_feature_detection'] = {}
            
        self.config['single_cam_feature_detection']['method'] = algo
        
        # Also update feature matching config for multi-camera mode
        if 'feature_matching' not in self.config:
            self.config['feature_matching'] = {}
            
        self.config['feature_matching']['detector'] = algo
        self.config['feature_matching']['descriptor'] = algo
        
        self.status_label.config(text=f"Feature algorithm set to: {algo.upper()}")
        self.logger.info(f"Changed feature detection algorithm to {algo}")
    
    def update_feature_count(self, value=None):
        """Update the maximum number of features to detect."""
        count = self.feature_count_var.get()
        
        # Update the display label
        self.count_display_label.config(text=str(count))
        
        # Update configuration
        if 'single_cam_feature_detection' not in self.config:
            self.config['single_cam_feature_detection'] = {}
            
        self.config['single_cam_feature_detection']['max_features'] = count
        
        # Also update feature matching config for multi-camera mode
        if 'feature_matching' not in self.config:
            self.config['feature_matching'] = {}
            
        self.config['feature_matching']['max_features'] = count
        
        self.status_label.config(text=f"Max features set to: {count}")
