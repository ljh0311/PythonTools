"""
Robot Control GUI
Comprehensive interface for robot monitoring and control
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import customtkinter as ctk
import threading
import time
import math
import asyncio
from typing import Optional, Dict, Any
from dataclasses import dataclass
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
import PIL.Image
import PIL.ImageTk
import PIL.ImageDraw
import cv2
import queue
from concurrent.futures import ThreadPoolExecutor, Future

from ..core.robot_state import RobotState, RobotMode, Position
from ..hardware.motor_controller import MotorController
from ..hardware.sensor_manager import SensorManager
from ..navigation.pathfinder import Pathfinder
from ..navigation.autonomous_controller import AutonomousController
from ..vision.visual_odometry import VisualOdometry
from ..vision.dynamic_obstacle_predictor import DynamicObstaclePredictor
from ..vision.scene_understanding import SceneUnderstanding


@dataclass
class UpdateConfig:
    """Configuration for UI update rates"""
    ui_rate: float = 30.0  # Hz - UI update rate
    sensor_rate: float = 20.0  # Hz - Sensor data collection rate
    navigation_rate: float = 10.0  # Hz - Navigation status update rate
    map_rate: float = 5.0  # Hz - Map visualization update rate
    camera_rate: float = 15.0  # Hz - Camera frame update rate


class AsyncDataCollector:
    """Async data collector for I/O operations with rate limiting and caching"""
    
    def __init__(self, robot_state: RobotState, sensor_manager: SensorManager,
                 autonomous_controller: AutonomousController, config: UpdateConfig):
        self.robot_state = robot_state
        self.sensor_manager = sensor_manager
        self.autonomous_controller = autonomous_controller
        self.config = config
        
        # Data caches with timestamps
        self.sensor_cache: Optional[Dict[str, Any]] = None
        self.sensor_cache_time: float = 0.0
        self.nav_cache: Optional[Dict[str, Any]] = None
        self.nav_cache_time: float = 0.0
        self.status_cache: Optional[Dict[str, Any]] = None
        self.status_cache_time: float = 0.0
        
        # Rate limiting
        self.last_sensor_read: float = 0.0
        self.last_nav_read: float = 0.0
        self.last_status_read: float = 0.0
        
        # Cache timeout (50ms)
        self.cache_timeout = 0.05
        
        # Data queues for async operations
        self.sensor_queue = asyncio.Queue(maxsize=5)
        self.nav_queue = asyncio.Queue(maxsize=5)
        self.status_queue = asyncio.Queue(maxsize=5)
        
        # Running flag
        self.running = False
        self.collection_task = None
    
    async def _collect_sensor_data(self):
        """Collect sensor data asynchronously with rate limiting"""
        while self.running:
            try:
                current_time = time.time()
                interval = 1.0 / self.config.sensor_rate
                
                if current_time - self.last_sensor_read >= interval:
                    # Check cache first
                    if (self.sensor_cache is not None and 
                        current_time - self.sensor_cache_time < self.cache_timeout):
                        await self.sensor_queue.put(('cached', self.sensor_cache))
                    else:
                        # Collect new data (run in thread pool for blocking I/O)
                        loop = asyncio.get_event_loop()
                        sensor_data = await loop.run_in_executor(
                            None, self.sensor_manager.get_sensor_data
                        )
                        availability = await loop.run_in_executor(
                            None, self.sensor_manager.check_sensor_availability
                        )
                        
                        data = {
                            'sensor_data': sensor_data,
                            'availability': availability,
                            'timestamp': current_time
                        }
                        
                        self.sensor_cache = data
                        self.sensor_cache_time = current_time
                        await self.sensor_queue.put(('new', data))
                        self.last_sensor_read = current_time
                
                await asyncio.sleep(0.01)  # Small sleep to prevent busy waiting
            except Exception as e:
                print(f"Error collecting sensor data: {e}")
                await asyncio.sleep(0.1)
    
    async def _collect_navigation_data(self):
        """Collect navigation status asynchronously with rate limiting"""
        while self.running:
            try:
                current_time = time.time()
                interval = 1.0 / self.config.navigation_rate
                
                if current_time - self.last_nav_read >= interval:
                    # Check cache first
                    if (self.nav_cache is not None and 
                        current_time - self.nav_cache_time < self.cache_timeout):
                        await self.nav_queue.put(('cached', self.nav_cache))
                    else:
                        # Collect new data
                        loop = asyncio.get_event_loop()
                        nav_status = await loop.run_in_executor(
                            None, self.autonomous_controller.get_status
                        )
                        
                        data = {
                            'nav_status': nav_status,
                            'timestamp': current_time
                        }
                        
                        self.nav_cache = data
                        self.nav_cache_time = current_time
                        await self.nav_queue.put(('new', data))
                        self.last_nav_read = current_time
                
                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"Error collecting navigation data: {e}")
                await asyncio.sleep(0.1)
    
    async def _collect_status_data(self):
        """Collect robot status asynchronously with rate limiting"""
        while self.running:
            try:
                current_time = time.time()
                interval = 1.0 / self.config.sensor_rate  # Use sensor rate for status
                
                if current_time - self.last_status_read >= interval:
                    # Check cache first
                    if (self.status_cache is not None and 
                        current_time - self.status_cache_time < self.cache_timeout):
                        await self.status_queue.put(('cached', self.status_cache))
                    else:
                        # Collect new data
                        loop = asyncio.get_event_loop()
                        status = await loop.run_in_executor(
                            None, self.robot_state.get_status_summary
                        )
                        
                        data = {
                            'status': status,
                            'timestamp': current_time
                        }
                        
                        self.status_cache = data
                        self.status_cache_time = current_time
                        await self.status_queue.put(('new', data))
                        self.last_status_read = current_time
                
                await asyncio.sleep(0.01)
            except Exception as e:
                print(f"Error collecting status data: {e}")
                await asyncio.sleep(0.1)
    
    async def start_collection(self):
        """Start async data collection"""
        self.running = True
        # Create tasks for all collection coroutines
        tasks = [
            asyncio.create_task(self._collect_sensor_data()),
            asyncio.create_task(self._collect_navigation_data()),
            asyncio.create_task(self._collect_status_data())
        ]
        # Wait for all tasks (they run until self.running is False)
        try:
            await asyncio.gather(*tasks)
        except asyncio.CancelledError:
            # Tasks were cancelled, which is expected when stopping
            pass
    
    def stop_collection(self):
        """Stop async data collection"""
        self.running = False
        if self.collection_task:
            self.collection_task.cancel()
    
    async def get_sensor_data(self, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """Get sensor data from queue (non-blocking)"""
        try:
            source, data = await asyncio.wait_for(self.sensor_queue.get(), timeout=timeout)
            return data
        except asyncio.TimeoutError:
            return self.sensor_cache  # Return cached data if queue is empty
    
    async def get_nav_data(self, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """Get navigation data from queue (non-blocking)"""
        try:
            source, data = await asyncio.wait_for(self.nav_queue.get(), timeout=timeout)
            return data
        except asyncio.TimeoutError:
            return self.nav_cache  # Return cached data if queue is empty
    
    async def get_status_data(self, timeout: float = 0.1) -> Optional[Dict[str, Any]]:
        """Get status data from queue (non-blocking)"""
        try:
            source, data = await asyncio.wait_for(self.status_queue.get(), timeout=timeout)
            return data
        except asyncio.TimeoutError:
            return self.status_cache  # Return cached data if queue is empty


class RobotGUI:
    """Main robot control GUI"""
    
    def __init__(self, robot_state: RobotState, motor_controller: MotorController,
                 sensor_manager: SensorManager, pathfinder: Pathfinder,
                 autonomous_controller: AutonomousController):
        
        self.robot_state = robot_state
        self.motor_controller = motor_controller
        self.sensor_manager = sensor_manager
        self.pathfinder = pathfinder
        self.autonomous_controller = autonomous_controller
        
        # GUI state
        self.running = False
        self.update_thread = None
        self.camera_available = self._check_camera_available()
        self.visual_odometry_enabled = False
        self.dynamic_obstacle_enabled = False
        self.scene_understanding_enabled = False
        
        # Update configuration
        self.update_config = UpdateConfig()
        
        # Initialize vision modules if camera is available
        if self.camera_available:
            self.visual_odometry = VisualOdometry()
            self.dynamic_obstacle_predictor = DynamicObstaclePredictor()
            self.scene_understanding = SceneUnderstanding()
        else:
            self.visual_odometry = None
            self.dynamic_obstacle_predictor = None
            self.scene_understanding = None
        
        # Initialize async data collector
        self.data_collector = AsyncDataCollector(
            robot_state, sensor_manager, autonomous_controller, self.update_config
        )
        
        # Initialize vision thread pool
        self.vision_executor = ThreadPoolExecutor(max_workers=3, thread_name_prefix="vision")
        self.vision_futures: Dict[str, Future] = {}
        self.vision_results = {
            'visual_odometry': None,
            'dynamic_obstacles': [],
            'scene_analysis': None
        }
        self.last_processed_frame = None
        self.frame_skip_counter = 0
        self.frame_skip_interval = 2  # Process every 2nd frame
        
        # Camera update rate limiting
        self.last_camera_update_time = 0.0
        self.cached_camera_image = None
        self.cached_camera_imagetk = None
        self.camera_image_id = None  # Canvas item ID for incremental updates
        
        # Frame queue for vision processing (prevent backlog)
        self.vision_frame_queue = queue.Queue(maxsize=2)  # Only keep 2 frames max
        self.vision_processing_active = False
        
        # Data caches for UI updates
        self.cached_sensor_data = None
        self.cached_nav_data = None
        self.cached_status_data = None
        
        # Map update counter for frame skipping
        self.map_update_counter = 0
        
        # Map caching for incremental updates
        self.map_cache = {
            'grid': None,
            'robot_pos': None,
            'target_pos': None,
            'path': None,
            'navmesh': None
        }
        self.map_ax_initialized = False
        
        # Widget dirty flags for smart updates
        self.widget_dirty_flags = {}
        
        # Performance monitoring
        self.performance_metrics = {
            'ui_updates': deque(maxlen=100),
            'sensor_updates': deque(maxlen=100),
            'nav_updates': deque(maxlen=100),
            'map_updates': deque(maxlen=100),
            'camera_updates': deque(maxlen=100)
        }
        self.last_perf_log_time = time.time()
        
        # Setup GUI
        self.setup_gui()
        
        # Start update loop
        self.start()
    
    def setup_gui(self):
        """Setup the main GUI window and widgets"""
        # Configure customtkinter - Smart Home Theme
        ctk.set_appearance_mode("light")  # Light mode for smart home aesthetic
        ctk.set_default_color_theme("blue")  # Blue theme matches smart home palette
        
        # Create main window
        self.root = ctk.CTk()
        self.root.title("Smart Home Robot Assistant")
        self.root.geometry("1400x900")
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.minsize(1000, 700)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        
        # Create main container
        self.main_frame = ctk.CTkFrame(self.root)
        self.main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Create tabs
        self.setup_control_tab()
        self.setup_monitoring_tab()
        self.setup_navigation_tab()
        self.setup_settings_tab()
        
        # Add status bar at the bottom - Smart Home Theme
        self.status_bar = ctk.CTkLabel(self.root, text="Ready", anchor="w", height=24, fg_color="#f5f5f5", text_color="#333")
        self.status_bar.grid(row=1, column=0, sticky="ew")
    
    def setup_control_tab(self):
        """Setup the manual control tab"""
        self.control_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(self.control_frame, text="Manual Control")
        
        # Control buttons frame
        control_buttons_frame = ctk.CTkFrame(self.control_frame)
        control_buttons_frame.pack(fill="x", padx=10, pady=10)
        
        # Mode selection
        mode_frame = ctk.CTkFrame(control_buttons_frame)
        mode_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(mode_frame, text="Robot Mode:").pack(side="left", padx=5)
        
        self.mode_var = tk.StringVar(value=RobotMode.IDLE.value)
        mode_menu = ctk.CTkOptionMenu(
            mode_frame, 
            variable=self.mode_var,
            values=[mode.value for mode in RobotMode],
            command=self.on_mode_change
        )
        mode_menu.pack(side="left", padx=5)
        
        # Emergency stop button
        self.emergency_stop_btn = ctk.CTkButton(
            control_buttons_frame,
            text="EMERGENCY STOP",
            fg_color="red",
            hover_color="darkred",
            command=self.emergency_stop
        )
        self.emergency_stop_btn.pack(pady=10)
        
        # Movement controls
        movement_frame = ctk.CTkFrame(self.control_frame)
        movement_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Forward/backward controls
        fwd_back_frame = ctk.CTkFrame(movement_frame)
        fwd_back_frame.pack(pady=10)
        
        self.forward_btn = ctk.CTkButton(
            fwd_back_frame, text="FORWARD", command=lambda: self.move_forward()
        )
        self.forward_btn.pack(pady=5)
        
        back_frame = ctk.CTkFrame(fwd_back_frame)
        back_frame.pack(pady=5)
        
        self.backward_btn = ctk.CTkButton(
            back_frame, text="BACKWARD", command=lambda: self.move_backward()
        )
        self.backward_btn.pack(side="left", padx=5)
        
        self.stop_btn = ctk.CTkButton(
            back_frame, text="STOP", command=self.stop_movement
        )
        self.stop_btn.pack(side="left", padx=5)
        
        # Left/right controls
        left_right_frame = ctk.CTkFrame(movement_frame)
        left_right_frame.pack(pady=10)
        
        self.left_btn = ctk.CTkButton(
            left_right_frame, text="TURN LEFT", command=lambda: self.turn_left()
        )
        self.left_btn.pack(side="left", padx=5)
        
        self.right_btn = ctk.CTkButton(
            left_right_frame, text="TURN RIGHT", command=lambda: self.turn_right()
        )
        self.right_btn.pack(side="left", padx=5)
        
        # Speed control
        speed_frame = ctk.CTkFrame(movement_frame)
        speed_frame.pack(pady=10)
        
        ctk.CTkLabel(speed_frame, text="Speed:").pack(side="left", padx=5)
        
        self.speed_var = tk.DoubleVar(value=50.0)
        self.speed_slider = ctk.CTkSlider(
            speed_frame,
            from_=0,
            to=100,
            variable=self.speed_var,
            number_of_steps=100
        )
        self.speed_slider.pack(side="left", padx=5, fill="x", expand=True)
        
        self.speed_label = ctk.CTkLabel(speed_frame, text="50%")
        self.speed_label.pack(side="left", padx=5)
        
        self.speed_slider.configure(command=self.on_speed_change)
    
    def setup_monitoring_tab(self):
        """Setup the monitoring tab"""
        self.monitoring_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(self.monitoring_frame, text="Monitoring")
        
        # Status display
        status_frame = ctk.CTkFrame(self.monitoring_frame)
        status_frame.pack(fill="x", padx=10, pady=10)
        
        # Robot status
        robot_status_frame = ctk.CTkFrame(status_frame)
        robot_status_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(robot_status_frame, text="Robot Status", font=("Arial", 16, "bold")).pack()
        
        self.status_labels = {}
        status_items = [
            "Mode", "Status", "Battery", "Position X", "Position Y", "Orientation",
            "Total Distance", "Operation Time", "Safe to Move", "Obstacle Detected"
        ]
        
        for item in status_items:
            frame = ctk.CTkFrame(robot_status_frame)
            frame.pack(fill="x", padx=5, pady=2)
            
            ctk.CTkLabel(frame, text=f"{item}:").pack(side="left", padx=5)
            self.status_labels[item] = ctk.CTkLabel(frame, text="--")
            self.status_labels[item].pack(side="right", padx=5)
        
        # Sensor health status
        sensor_health_frame = ctk.CTkFrame(self.monitoring_frame)
        sensor_health_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(sensor_health_frame, text="Sensor Health Status", font=("Arial", 16, "bold")).pack()
        
        self.sensor_health_label = ctk.CTkLabel(sensor_health_frame, text="Checking sensor status...", text_color="#FFA500")
        self.sensor_health_label.pack(pady=5)
        
        # Sensor data
        sensor_frame = ctk.CTkFrame(self.monitoring_frame)
        sensor_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(sensor_frame, text="Sensor Data", font=("Arial", 16, "bold")).pack()
        
        # Create sensor display grid
        sensor_grid = ctk.CTkFrame(sensor_frame)
        sensor_grid.pack(fill="both", expand=True, padx=5, pady=5)
        
        self.sensor_labels = {}
        sensor_items = [
            ("Ultrasonic Front", "ultrasonic_front"),
            ("Ultrasonic Left", "ultrasonic_left"),
            ("Ultrasonic Right", "ultrasonic_right"),
            ("Infrared Left", "infrared_left"),
            ("Infrared Right", "infrared_right"),
            ("Bumper Left", "bumper_left"),
            ("Bumper Right", "bumper_right")
        ]
        
        for i, (label, key) in enumerate(sensor_items):
            row = i // 2
            col = i % 2
            
            frame = ctk.CTkFrame(sensor_grid)
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="ew")
            
            ctk.CTkLabel(frame, text=f"{label}:").pack(side="left", padx=5)
            self.sensor_labels[key] = ctk.CTkLabel(frame, text="--")
            self.sensor_labels[key].pack(side="right", padx=5)
        
        sensor_grid.grid_columnconfigure(0, weight=1)
        sensor_grid.grid_columnconfigure(1, weight=1)

        # Camera view panel
        camera_panel_frame = ctk.CTkFrame(self.monitoring_frame)
        camera_panel_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(camera_panel_frame, text="Camera View", font=("Arial", 16, "bold")).pack()
        self.camera_canvas = tk.Canvas(camera_panel_frame, width=320, height=240, bg="#dddddd", highlightthickness=1, highlightbackground="#333")
        self.camera_canvas.pack(pady=5)
        self._camera_imgtk = None  # To prevent garbage collection

        # Add camera/vision status
        vision_status_frame = ctk.CTkFrame(self.monitoring_frame)
        vision_status_frame.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(vision_status_frame, text="Camera/Vision Features", font=("Arial", 14, "bold")).pack(side="left", padx=5)
        self.vision_status_label = ctk.CTkLabel(vision_status_frame, text="Camera: Available" if self.camera_available else "Camera: Not Available", text_color="#00FF00" if self.camera_available else "#FF0000")
        self.vision_status_label.pack(side="left", padx=10)
        # Add toggles for vision features
        self.vo_toggle = ctk.CTkCheckBox(vision_status_frame, text="Visual Odometry", command=self.toggle_visual_odometry, state="normal" if self.camera_available else "disabled")
        self.vo_toggle.pack(side="left", padx=5)
        self.dynobs_toggle = ctk.CTkCheckBox(vision_status_frame, text="Dynamic Obstacle Prediction", command=self.toggle_dynamic_obstacle, state="normal" if self.camera_available else "disabled")
        self.dynobs_toggle.pack(side="left", padx=5)
        self.scene_toggle = ctk.CTkCheckBox(vision_status_frame, text="Scene Understanding", command=self.toggle_scene_understanding, state="normal" if self.camera_available else "disabled")
        self.scene_toggle.pack(side="left", padx=5)
    
    def setup_navigation_tab(self):
        """Setup the navigation tab"""
        self.navigation_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(self.navigation_frame, text="Navigation")
        
        # Navigation controls
        nav_control_frame = ctk.CTkFrame(self.navigation_frame)
        nav_control_frame.pack(fill="x", padx=10, pady=10)
        
        # Target position input
        target_frame = ctk.CTkFrame(nav_control_frame)
        target_frame.pack(fill="x", padx=5, pady=5)
        
        ctk.CTkLabel(target_frame, text="Target Position:").pack(side="left", padx=5)
        
        self.target_x_var = tk.StringVar(value="500")
        self.target_y_var = tk.StringVar(value="500")
        
        ctk.CTkLabel(target_frame, text="X:").pack(side="left", padx=5)
        ctk.CTkEntry(target_frame, textvariable=self.target_x_var, width=80).pack(side="left", padx=2)
        
        ctk.CTkLabel(target_frame, text="Y:").pack(side="left", padx=5)
        ctk.CTkEntry(target_frame, textvariable=self.target_y_var, width=80).pack(side="left", padx=2)
        
        # Navigation buttons
        nav_buttons_frame = ctk.CTkFrame(nav_control_frame)
        nav_buttons_frame.pack(fill="x", padx=5, pady=5)
        
        self.navigate_btn = ctk.CTkButton(
            nav_buttons_frame, text="Navigate to Target", command=self.navigate_to_target
        )
        self.navigate_btn.pack(side="left", padx=5)
        
        self.explore_btn = ctk.CTkButton(
            nav_buttons_frame, text="Start Exploration", command=self.start_exploration
        )
        self.explore_btn.pack(side="left", padx=5)
        
        self.return_base_btn = ctk.CTkButton(
            nav_buttons_frame, text="Return to Base", command=self.return_to_base
        )
        self.return_base_btn.pack(side="left", padx=5)
        
        self.stop_nav_btn = ctk.CTkButton(
            nav_buttons_frame, text="Stop Navigation", command=self.stop_navigation
        )
        self.stop_nav_btn.pack(side="left", padx=5)
        
        # Map visualization
        map_frame = ctk.CTkFrame(self.navigation_frame)
        map_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(map_frame, text="Navigation Map", font=("Arial", 16, "bold")).pack()
        
        # Create matplotlib figure for map
        self.map_figure = Figure(figsize=(8, 6), dpi=100)
        self.map_ax = self.map_figure.add_subplot(111)
        self.map_canvas = FigureCanvasTkAgg(self.map_figure, map_frame)
        self.map_canvas.get_tk_widget().pack(fill="both", expand=True, padx=5, pady=5)
        
        # Navigation status
        nav_status_frame = ctk.CTkFrame(self.navigation_frame)
        nav_status_frame.pack(fill="x", padx=10, pady=10)
        
        self.nav_status_labels = {}
        nav_status_items = [
            "Navigation State", "Current Target", "Path Length", "Exploration Progress"
        ]
        
        for item in nav_status_items:
            frame = ctk.CTkFrame(nav_status_frame)
            frame.pack(fill="x", padx=5, pady=2)
            
            ctk.CTkLabel(frame, text=f"{item}:").pack(side="left", padx=5)
            self.nav_status_labels[item] = ctk.CTkLabel(frame, text="--")
            self.nav_status_labels[item].pack(side="right", padx=5)
    
    def setup_settings_tab(self):
        """Setup the settings tab"""
        self.settings_frame = ctk.CTkFrame(self.notebook)
        self.notebook.add(self.settings_frame, text="Settings")
        
        # Configuration display and editing
        config_frame = ctk.CTkFrame(self.settings_frame)
        config_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(config_frame, text="Robot Configuration", font=("Arial", 16, "bold")).pack()
        
        # Add configuration editing widgets here
        # (This would be a more complex implementation for editing the config file)
        
        # System diagnostics section
        diagnostics_frame = ctk.CTkFrame(self.settings_frame)
        diagnostics_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(diagnostics_frame, text="System Diagnostics", font=("Arial", 16, "bold")).pack()
        
        # Sensor diagnostics button
        sensor_diag_btn = ctk.CTkButton(
            diagnostics_frame,
            text="Sensor Diagnostics",
            command=self.show_sensor_diagnostics
        )
        sensor_diag_btn.pack(pady=10)
        
        # Log display
        log_frame = ctk.CTkFrame(self.settings_frame)
        log_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        ctk.CTkLabel(log_frame, text="System Log", font=("Arial", 16, "bold")).pack()
        
        self.log_text = ctk.CTkTextbox(log_frame, height=200)
        self.log_text.pack(fill="both", expand=True, padx=5, pady=5)
    
    def start(self):
        """Start the GUI update loop"""
        self.running = True
        
        # Start async data collection in new event loop
        def run_async_collector():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(self.data_collector.start_collection())
        
        self.async_thread = threading.Thread(target=run_async_collector, daemon=True)
        self.async_thread.start()
        
        # Start UI update thread
        self.update_thread = threading.Thread(target=self._update_loop, daemon=True)
        self.update_thread.start()
    
    def stop(self):
        """Stop the GUI"""
        self.running = False
        self.data_collector.stop_collection()
        if self.vision_executor:
            self.vision_executor.shutdown(wait=False)
        if self.update_thread:
            self.update_thread.join(timeout=1.0)
        if hasattr(self, 'async_thread') and self.async_thread:
            self.async_thread.join(timeout=1.0)
    
    def _update_loop(self):
        """Main GUI update loop with improved update rate"""
        update_interval = 1.0 / self.update_config.ui_rate
        last_update = time.time()
        
        while self.running:
            try:
                current_time = time.time()
                
                # Fetch data from async collector (non-blocking)
                self._fetch_async_data()
                
                # Schedule UI update on main thread
                self.root.after(0, self._update_displays)
                
                # Track performance
                self.performance_metrics['ui_updates'].append(current_time)
                
                # Log performance metrics periodically
                if current_time - self.last_perf_log_time > 5.0:  # Every 5 seconds
                    self._log_performance_metrics()
                    self.last_perf_log_time = current_time
                
                # Sleep to maintain target update rate
                elapsed = current_time - last_update
                sleep_time = max(0, update_interval - elapsed)
                time.sleep(sleep_time)
                last_update = time.time()
            except Exception as e:
                print(f"Error in GUI update loop: {e}")
                time.sleep(0.1)
    
    def _log_performance_metrics(self):
        """Log performance metrics for monitoring"""
        try:
            # Calculate actual update rates
            ui_rate = self._calculate_rate(self.performance_metrics['ui_updates'])
            sensor_rate = self._calculate_rate(self.performance_metrics['sensor_updates'])
            nav_rate = self._calculate_rate(self.performance_metrics['nav_updates'])
            map_rate = self._calculate_rate(self.performance_metrics['map_updates'])
            camera_rate = self._calculate_rate(self.performance_metrics['camera_updates'])
            
            # Log if rates are significantly below target
            if ui_rate < self.update_config.ui_rate * 0.8:
                print(f"Performance warning: UI update rate {ui_rate:.1f}Hz (target: {self.update_config.ui_rate}Hz)")
            if sensor_rate < self.update_config.sensor_rate * 0.8:
                print(f"Performance warning: Sensor update rate {sensor_rate:.1f}Hz (target: {self.update_config.sensor_rate}Hz)")
        except Exception as e:
            print(f"Error logging performance metrics: {e}")
    
    def _calculate_rate(self, timestamps: deque) -> float:
        """Calculate update rate from timestamp deque"""
        if len(timestamps) < 2:
            return 0.0
        time_span = timestamps[-1] - timestamps[0]
        if time_span > 0:
            return (len(timestamps) - 1) / time_span
        return 0.0
    
    def _fetch_async_data(self):
        """Fetch data from async collector (runs in update thread)"""
        try:
            # Create a temporary event loop for this thread to fetch data
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Fetch data with short timeout
            sensor_data = loop.run_until_complete(
                self.data_collector.get_sensor_data(timeout=0.01)
            )
            if sensor_data:
                self.cached_sensor_data = sensor_data
                self.performance_metrics['sensor_updates'].append(time.time())
            
            nav_data = loop.run_until_complete(
                self.data_collector.get_nav_data(timeout=0.01)
            )
            if nav_data:
                self.cached_nav_data = nav_data
                self.performance_metrics['nav_updates'].append(time.time())
            
            status_data = loop.run_until_complete(
                self.data_collector.get_status_data(timeout=0.01)
            )
            if status_data:
                self.cached_status_data = status_data
            
            loop.close()
        except Exception as e:
            # Fallback to synchronous reads if async fails
            if self.cached_sensor_data is None:
                try:
                    self.cached_sensor_data = {
                        'sensor_data': self.sensor_manager.get_sensor_data(),
                        'availability': self.sensor_manager.check_sensor_availability(),
                        'timestamp': time.time()
                    }
                except:
                    pass
            if self.cached_nav_data is None:
                try:
                    self.cached_nav_data = {
                        'nav_status': self.autonomous_controller.get_status(),
                        'timestamp': time.time()
                    }
                except:
                    pass
            if self.cached_status_data is None:
                try:
                    self.cached_status_data = {
                        'status': self.robot_state.get_status_summary(),
                        'timestamp': time.time()
                    }
                except:
                    pass
    
    def _update_displays(self):
        """Update all display elements using cached data"""
        try:
            # Update status labels from cache
            if self.cached_status_data:
                status = self.cached_status_data['status']
                self._update_status_labels(status)
            
            # Update sensor health status from cache
            if self.cached_sensor_data:
                self._update_sensor_health_status_cached(self.cached_sensor_data)
                self._update_sensor_labels_cached(self.cached_sensor_data)
            
            # Update navigation status from cache
            if self.cached_nav_data:
                nav_status = self.cached_nav_data['nav_status']
                self._update_navigation_labels(nav_status)
            
            # Update map visualization (with frame skipping)
            self.map_update_counter += 1
            map_skip_interval = int(self.update_config.ui_rate / self.update_config.map_rate)
            if self.map_update_counter >= map_skip_interval:
                self._update_map()
                self.map_update_counter = 0
                self.performance_metrics['map_updates'].append(time.time())
            
            # Update camera view (async processing with rate limiting)
            current_time = time.time()
            camera_interval = 1.0 / self.update_config.camera_rate
            if current_time - self.last_camera_update_time >= camera_interval:
                update_start = time.time()
                self._update_camera_view_async()
                update_duration = time.time() - update_start
                self.last_camera_update_time = current_time
                self.performance_metrics['camera_updates'].append(current_time)
                self.performance_metrics['camera_update_times'].append(update_duration)
                
                # Warn if camera update takes too long (> 50ms for 15Hz = 66ms budget)
                if update_duration > 0.05:
                    if not hasattr(self, '_camera_warning_count'):
                        self._camera_warning_count = 0
                    self._camera_warning_count += 1
                    if self._camera_warning_count % 10 == 0:  # Warn every 10th occurrence
                        print(f"Warning: Camera update took {update_duration*1000:.1f}ms (target: <50ms)")
            
            # Update status bar
            if hasattr(self, 'status_bar'):
                self.status_bar.configure(text="Last update: OK", text_color="#00FF00")
        except Exception as e:
            # Show error in status bar and print to console
            if hasattr(self, 'status_bar'):
                self.status_bar.configure(text=f"Error: {e}", text_color="#FF0000")
            print(f"Error in _update_displays: {e}")
    
    def _update_status_labels(self, status: Dict[str, Any]):
        """Update status labels with smart skipping"""
        updates = {
            "Mode": status['mode'],
            "Status": status['status'],
            "Battery": f"{status['battery']}%",
            "Position X": f"{status['position']['x']:.1f} cm",
            "Position Y": f"{status['position']['y']:.1f} cm",
            "Orientation": f"{status['position']['theta']:.1f}°",
            "Total Distance": f"{status['total_distance']:.1f} cm",
            "Operation Time": f"{status['operation_time']:.1f} s"
        }
        
        for key, value in updates.items():
            if key in self.status_labels:
                if self._should_update_widget(key, value):
                    self.status_labels[key].configure(text=value)
        
        # Color code Safe to Move
        safe_text = "Yes" if status['safe_to_move'] else "No"
        safe_color = "#00FF00" if status['safe_to_move'] else "#FF0000"
        if self._should_update_widget("Safe to Move", safe_text):
            self.status_labels["Safe to Move"].configure(text=safe_text, text_color=safe_color)
        
        # Color code Obstacle Detected
        obs_text = "Yes" if status['obstacle_detected'] else "No"
        obs_color = "#FF0000" if status['obstacle_detected'] else "#00FF00"
        if self._should_update_widget("Obstacle Detected", obs_text):
            self.status_labels["Obstacle Detected"].configure(text=obs_text, text_color=obs_color)
    
    def _should_update_widget(self, widget_key: str, new_value: Any) -> bool:
        """Check if widget should be updated (smart skipping)"""
        if widget_key not in self.widget_dirty_flags:
            self.widget_dirty_flags[widget_key] = None
        
        if self.widget_dirty_flags[widget_key] != new_value:
            self.widget_dirty_flags[widget_key] = new_value
            return True
        return False
    
    def _update_navigation_labels(self, nav_status: Dict[str, Any]):
        """Update navigation labels with smart skipping"""
        nav_state = nav_status.get('navigation_state', 'unknown')
        if self._should_update_widget("Navigation State", nav_state):
            self.nav_status_labels["Navigation State"].configure(text=nav_state)
        
        target = nav_status.get('target_position', {})
        if target.get('x') is not None:
            target_text = f"({target['x']:.1f}, {target['y']:.1f})"
        else:
            target_text = "None"
        if self._should_update_widget("Current Target", target_text):
            self.nav_status_labels["Current Target"].configure(text=target_text)
        
        path_length = str(nav_status.get('total_waypoints', 0))
        if self._should_update_widget("Path Length", path_length):
            self.nav_status_labels["Path Length"].configure(text=path_length)
    
    def _update_sensor_health_status_cached(self, sensor_data_cache: Dict[str, Any]):
        """Update sensor health status display from cache"""
        try:
            availability = sensor_data_cache.get('availability', {})
            health_message = self.sensor_manager.get_sensor_health_message()
            
            # Update health label with appropriate color
            status = availability.get('overall_status', 'unknown')
            if status == 'all_sensors_available':
                color = "#00FF00"
            elif status == 'simulation_mode':
                color = "#FFA500"
            elif status == 'partial_availability':
                color = "#FFA500"
            else:  # no_sensors_available
                color = "#FF0000"
            
            if self._should_update_widget("sensor_health", (status, health_message)):
                self.sensor_health_label.configure(text=health_message, text_color=color)
            
            # Update status bar with system health
            self._update_status_bar_health(availability)
                
        except Exception as e:
            self.sensor_health_label.configure(text=f"Error checking sensor status: {e}", text_color="#FF0000")
    
    def _update_sensor_health_status(self):
        """Update sensor health status display (fallback)"""
        if self.cached_sensor_data:
            self._update_sensor_health_status_cached(self.cached_sensor_data)
        else:
            try:
                availability = self.sensor_manager.check_sensor_availability()
                health_message = self.sensor_manager.get_sensor_health_message()
                # ... rest of original code ...
            except Exception as e:
                self.sensor_health_label.configure(text=f"Error checking sensor status: {e}", text_color="#FF0000")
    
    def _update_status_bar_health(self, availability):
        """Update status bar with system health information"""
        try:
            if hasattr(self, 'status_bar'):
                if availability['overall_status'] == 'all_sensors_available':
                    self.status_bar.configure(text="System: All sensors operational", text_color="#00FF00")
                elif availability['overall_status'] == 'simulation_mode':
                    self.status_bar.configure(text="System: Running in simulation mode", text_color="#FFA500")
                elif availability['overall_status'] == 'partial_availability':
                    unavailable = self.sensor_manager.get_unavailable_sensors()
                    self.status_bar.configure(text=f"System: Partial sensor availability - {len(unavailable)} sensors unavailable", text_color="#FFA500")
                else:  # no_sensors_available
                    self.status_bar.configure(text="System: Sensor not available. Please check your setup", text_color="#FF0000")
        except Exception as e:
            if hasattr(self, 'status_bar'):
                self.status_bar.configure(text=f"System: Error checking health - {e}", text_color="#FF0000")
    
    def _update_sensor_labels_cached(self, sensor_data_cache: Dict[str, Any]):
        """Update sensor data labels from cache"""
        try:
            sensor_data = sensor_data_cache.get('sensor_data', {})
            
            # Update ultrasonic sensors
            ultrasonic_data = sensor_data.get('ultrasonic', {})
            for sensor_name in ['front', 'left', 'right']:
                key = f"ultrasonic_{sensor_name}"
                if key in self.sensor_labels:
                    if sensor_name in ultrasonic_data:
                        reading = ultrasonic_data[sensor_name]
                        if reading.valid:
                            self.sensor_labels[key].configure(text=f"{reading.value:.1f} cm", text_color="#00FF00")
                        else:
                            self.sensor_labels[key].configure(text="Sensor unavailable", text_color="#FF0000")
                    else:
                        self.sensor_labels[key].configure(text="No data", text_color="#FFA500")
            
            # Update infrared sensors
            infrared_data = sensor_data.get('infrared', {})
            for sensor_name in ['left', 'right']:
                key = f"infrared_{sensor_name}"
                if key in self.sensor_labels:
                    if sensor_name in infrared_data:
                        reading = infrared_data[sensor_name]
                        if reading.valid:
                            value = "Yes" if reading.value > 0 else "No"
                            color = "#FF0000" if reading.value > 0 else "#00FF00"
                            self.sensor_labels[key].configure(text=value, text_color=color)
                        else:
                            self.sensor_labels[key].configure(text="Sensor unavailable", text_color="#FF0000")
                    else:
                        self.sensor_labels[key].configure(text="No data", text_color="#FFA500")
            
            # Update bumper sensors
            bumper_data = sensor_data.get('bumper', {})
            for sensor_name in ['left', 'right']:
                key = f"bumper_{sensor_name}"
                if key in self.sensor_labels:
                    if sensor_name in bumper_data:
                        reading = bumper_data[sensor_name]
                        if reading.valid:
                            value = "Pressed" if reading.value > 0 else "Not Pressed"
                            color = "#FF0000" if reading.value > 0 else "#00FF00"
                            if self._should_update_widget(key, (value, color)):
                                self.sensor_labels[key].configure(text=value, text_color=color)
                        else:
                            if self._should_update_widget(key, "Sensor unavailable"):
                                self.sensor_labels[key].configure(text="Sensor unavailable", text_color="#FF0000")
                    else:
                        if self._should_update_widget(key, "No data"):
                            self.sensor_labels[key].configure(text="No data", text_color="#FFA500")
                        
        except Exception as e:
            # If there's an error updating sensor labels, show error on all sensors
            for label in self.sensor_labels.values():
                label.configure(text="Error", text_color="#FF0000")
            print(f"Error updating sensor labels: {e}")
    
    def _update_sensor_labels(self):
        """Update sensor data labels (fallback to cached version)"""
        if self.cached_sensor_data:
            self._update_sensor_labels_cached(self.cached_sensor_data)
        else:
            try:
                sensor_data = self.sensor_manager.get_sensor_data()
                # ... original implementation as fallback ...
            except Exception as e:
                print(f"Error updating sensor labels: {e}")
    
    def _update_map(self):
        """Update the navigation map visualization with incremental updates."""
        try:
            # Get grid data
            grid_status = self.pathfinder.get_grid_status()
            grid = grid_status['grid']
            grid_size = grid_status['grid_size']
            
            # Check if we need to redraw (grid changed or first time)
            grid_changed = self.map_cache['grid'] is None or not np.array_equal(self.map_cache['grid'], grid)
            
            if grid_changed or not self.map_ax_initialized:
                # Full redraw needed
                self.map_ax.clear()
                colors = ['white', 'black', 'red', 'green', 'blue', 'yellow']
                cmap = plt.cm.colors.ListedColormap(colors)
                self.map_ax.imshow(grid, cmap=cmap, origin='lower')
                self.map_cache['grid'] = grid.copy()
                self.map_ax_initialized = True
            else:
                # Incremental update - only update data if grid changed slightly
                # For now, we'll do full redraw but less frequently due to frame skipping
                pass
            
            # --- Navmesh overlay ---
            navmesh = getattr(self.autonomous_controller, 'navmesh_edges', {})
            for (from_cell, to_cell), waypoints in navmesh.items():
                if waypoints and len(waypoints) > 1:
                    x_coords, y_coords = zip(*waypoints)
                    self.map_ax.plot(x_coords, y_coords, color='magenta', linewidth=2, alpha=0.5, label='Navmesh Edge' if from_cell == list(navmesh.keys())[0] else None)
                else:
                    fx, fy = from_cell
                    tx, ty = to_cell
                    fxw = (fx + 0.5) * grid_size
                    fyw = (fy + 0.5) * grid_size
                    txw = (tx + 0.5) * grid_size
                    tyw = (ty + 0.5) * grid_size
                    self.map_ax.plot([fxw, txw], [fyw, tyw], color='magenta', linewidth=2, alpha=0.5, label='Navmesh Edge' if from_cell == list(navmesh.keys())[0] else None)
            # --- End navmesh overlay ---
            
            # --- Learning data visualization ---
            # Visualize stuck locations (red rectangles)
            stuck_locations = getattr(self.autonomous_controller, 'stuck_locations', set())
            for (x, y) in stuck_locations:
                rect = plt.Rectangle((x - grid_size/2, y - grid_size/2), grid_size, grid_size, 
                                   color='red', alpha=0.6, label='Stuck Location' if not hasattr(self, '_learning_legend_added') else None)
                self.map_ax.add_patch(rect)
            
            # Visualize areas of caution (orange rectangles)
            areas_of_caution = getattr(self.autonomous_controller, 'areas_of_caution', set())
            for (i, j) in areas_of_caution:
                x = (j + 0.5) * grid_size
                y = (i + 0.5) * grid_size
                rect = plt.Rectangle((x - grid_size/2, y - grid_size/2), grid_size, grid_size, 
                                   color='orange', alpha=0.4, label='Area of Caution' if not hasattr(self, '_learning_legend_added') else None)
                self.map_ax.add_patch(rect)
            
            # Visualize valid paths (green lines)
            valid_paths = getattr(self.autonomous_controller, 'valid_paths', {})
            for path_key, path_data in valid_paths.items():
                if isinstance(path_data, list) and len(path_data) > 1:
                    x_coords, y_coords = zip(*path_data)
                    self.map_ax.plot(x_coords, y_coords, color='green', linewidth=1, alpha=0.7, 
                                   label='Valid Path' if not hasattr(self, '_learning_legend_added') else None)
            
            # Mark that we've added legend items
            self._learning_legend_added = True
            # --- End learning data visualization ---
            
            # Add robot position (only if changed)
            current_robot_pos = (self.robot_state.position.x, self.robot_state.position.y)
            if self.map_cache['robot_pos'] != current_robot_pos:
                robot_x, robot_y = self.pathfinder.world_to_grid(
                    self.robot_state.position.x, self.robot_state.position.y
                )
                self.map_ax.plot(robot_x, robot_y, 'ro', markersize=10, label='Robot')
                self.map_cache['robot_pos'] = current_robot_pos
            
            # Add target position if exists (use cached nav data)
            nav_status = None
            if self.cached_nav_data:
                nav_status = self.cached_nav_data.get('nav_status', {})
            else:
                nav_status = self.autonomous_controller.get_status()
            
            target_pos = nav_status.get('target_position', {})
            if target_pos.get('x') is not None:
                current_target = (target_pos['x'], target_pos['y'])
                if self.map_cache['target_pos'] != current_target:
                    target_x, target_y = self.pathfinder.world_to_grid(
                        target_pos['x'],
                        target_pos['y']
                    )
                    self.map_ax.plot(target_x, target_y, 'go', markersize=10, label='Target')
                    self.map_cache['target_pos'] = current_target
            else:
                self.map_cache['target_pos'] = None
            
            self.map_ax.set_title(f"Exploration: {grid_status['exploration_percentage']:.1f}%")
            if not hasattr(self, '_map_legend_added'):
                self.map_ax.legend()
                self._map_legend_added = True
            self.map_ax.grid(True)
            
            # Use blit for faster updates if possible, otherwise full draw
            self.map_canvas.draw_idle()  # Use draw_idle for better performance
            
        except Exception as e:
            print(f"Error updating map: {e}")
    
    # Control methods
    def on_mode_change(self, mode):
        """Handle robot mode change"""
        try:
            robot_mode = RobotMode(mode)
            self.robot_state.set_mode(robot_mode)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to change mode: {e}")
    
    def emergency_stop(self):
        """Emergency stop"""
        self.robot_state.set_mode(RobotMode.EMERGENCY_STOP)
        self.motor_controller.emergency_stop()
        self.autonomous_controller.stop()
        messagebox.showwarning("Emergency Stop", "Robot stopped for safety!")
    
    def move_forward(self):
        """Move robot forward"""
        speed = self.speed_var.get()
        self.motor_controller.move_forward(speed)
    
    def move_backward(self):
        """Move robot backward"""
        speed = self.speed_var.get()
        self.motor_controller.move_backward(speed)
    
    def turn_left(self):
        """Turn robot left"""
        speed = self.speed_var.get()
        self.motor_controller.turn_left(speed)
    
    def turn_right(self):
        """Turn robot right"""
        speed = self.speed_var.get()
        self.motor_controller.turn_right(speed)
    
    def stop_movement(self):
        """Stop robot movement"""
        self.motor_controller.stop_motors()
    
    def on_speed_change(self, value):
        """Handle speed slider change"""
        self.speed_label.configure(text=f"{int(value)}%")
    
    def navigate_to_target(self):
        """Navigate to target position"""
        try:
            x = float(self.target_x_var.get())
            y = float(self.target_y_var.get())
            self.autonomous_controller.navigate_to(x, y)
        except ValueError:
            messagebox.showerror("Error", "Invalid target coordinates")
    
    def start_exploration(self):
        """Start autonomous exploration"""
        self.autonomous_controller.start_exploration()
    
    def return_to_base(self):
        """Return to base"""
        self.autonomous_controller.return_to_base()
    
    def stop_navigation(self):
        """Stop navigation"""
        self.autonomous_controller.stop()
        self.robot_state.set_mode(RobotMode.IDLE)
    
    def on_closing(self):
        """Handle window closing"""
        if messagebox.askokcancel("Quit", "Do you want to quit?"):
            self.stop()
            self.root.quit()
    
    def run(self):
        """Run the GUI"""
        self.root.mainloop()
    
    def get_camera_view_image(self, width=320, height=240, fov=90, view_distance=10):
        """
        Simulate a surveillance camera by rendering a cropped, forward-facing region in front of the robot.
        Returns a PIL.Image with vision analysis overlays if enabled.
        """
        # Get robot position and angle
        robot_x = self.robot_state.position.x / 100.0  # convert cm to m
        robot_y = self.robot_state.position.y / 100.0
        robot_angle = math.radians(self.robot_state.position.theta)
        fov_rad = math.radians(fov)
        half_fov = fov_rad / 2
        scale = 20  # pixels per meter
        
        # Create base image
        img = PIL.Image.new("RGB", (width, height), (220, 220, 220))
        draw = PIL.ImageDraw.Draw(img)
        
        # Draw robot's nose
        draw.polygon([
            (width // 2, height - 5),
            (width // 2 - 8, height),
            (width // 2 + 8, height)
        ], fill=(100, 150, 255))
        
        # Add vision analysis overlays if available
        if hasattr(self, 'vision_results') and self.vision_results:
            self._draw_vision_overlays(draw, width, height)
        
        # Cache robot position for next comparison
        if not hasattr(self, '_last_camera_robot_pos'):
            self._last_camera_robot_pos = (robot_x, robot_y, robot_angle)
        else:
            # Only update cache if robot moved significantly
            last_x, last_y, last_angle = self._last_camera_robot_pos
            pos_threshold = 0.05  # 5cm
            angle_threshold = 0.1  # ~6 degrees
            if (abs(robot_x - last_x) >= pos_threshold or 
                abs(robot_y - last_y) >= pos_threshold or
                abs(robot_angle - last_angle) >= angle_threshold):
                self._last_camera_robot_pos = (robot_x, robot_y, robot_angle)
        
        return img
    
    def _draw_vision_overlays(self, draw, width, height):
        """Draw vision analysis overlays on camera view"""
        # Visual Odometry overlay
        if self.vision_results.get('visual_odometry') and self.visual_odometry_enabled:
            motion = self.vision_results['visual_odometry']
            if motion:
                dx, dy, dtheta = motion
                # Draw motion vector
                center_x, center_y = width // 2, height // 2
                end_x = center_x + int(dx * 1000)
                end_y = center_y + int(dy * 1000)
                draw.line([(center_x, center_y), (end_x, end_y)], fill=(0, 255, 0), width=2)
                draw.text((10, 10), f"Motion: dx={dx:.3f}, dy={dy:.3f}", fill=(0, 255, 0))
        
        # Dynamic Obstacle overlay
        if self.vision_results.get('dynamic_obstacles') and self.dynamic_obstacle_enabled:
            obstacles = self.vision_results['dynamic_obstacles']
            for obstacle in obstacles:
                x, y, w, h = obstacle.bbox
                # Scale bbox to camera view
                scale_x = width / 640  # Assuming 640x480 camera
                scale_y = height / 480
                scaled_x = int(x * scale_x)
                scaled_y = int(y * scale_y)
                scaled_w = int(w * scale_x)
                scaled_h = int(h * scale_y)
                
                # Color based on risk level
                color = (255, 0, 0) if obstacle.risk_level == "high" else (255, 165, 0) if obstacle.risk_level == "medium" else (0, 255, 0)
                draw.rectangle([scaled_x, scaled_y, scaled_x + scaled_w, scaled_y + scaled_h], outline=color, width=2)
                
                # Draw predicted position
                if obstacle.predicted_position:
                    pred_x, pred_y = obstacle.predicted_position
                    scaled_pred_x = int(pred_x * scale_x)
                    scaled_pred_y = int(pred_y * scale_y)
                    draw.ellipse([scaled_pred_x-3, scaled_pred_y-3, scaled_pred_x+3, scaled_pred_y+3], fill=(255, 0, 255))
        
        # Scene Understanding overlay
        if self.vision_results.get('scene_analysis') and self.scene_understanding_enabled:
            scene_analysis = self.vision_results['scene_analysis']
            regions = scene_analysis.get('regions', [])
            
            for region in regions:
                x, y, w, h = region.bbox
                # Scale bbox to camera view
                scale_x = width / 640
                scale_y = height / 480
                scaled_x = int(x * scale_x)
                scaled_y = int(y * scale_y)
                scaled_w = int(w * scale_x)
                scaled_h = int(h * scale_y)
                
                # Convert BGR to RGB for PIL
                color = (region.color[2], region.color[1], region.color[0])
                draw.rectangle([scaled_x, scaled_y, scaled_x + scaled_w, scaled_y + scaled_h], outline=color, width=1)
            
            # Display navigation features
            nav_features = scene_analysis.get('navigation_features', {})
            draw.text((10, 30), f"Safe Dir: {len(nav_features.get('safe_directions', []))}", fill=(255, 255, 0))
            draw.text((10, 50), f"Speed: {nav_features.get('recommended_speed', 1.0):.1f}", fill=(255, 255, 0))

    def _check_camera_available(self):
        try:
            cap = cv2.VideoCapture(0)
            if cap is not None and cap.isOpened():
                cap.release()
                return True
            return False
        except Exception:
            return False

    def toggle_visual_odometry(self):
        if self.camera_available:
            self.visual_odometry_enabled = not self.visual_odometry_enabled

    def toggle_dynamic_obstacle(self):
        if self.camera_available:
            self.dynamic_obstacle_enabled = not self.dynamic_obstacle_enabled

    def toggle_scene_understanding(self):
        if self.camera_available:
            self.scene_understanding_enabled = not self.scene_understanding_enabled

    def _update_camera_view_async(self):
        """Update camera view with async vision processing and optimized rendering"""
        try:
            # Check if we have pending vision processing results (non-blocking)
            self._check_vision_futures()
            
            # Get camera frame (with caching to avoid unnecessary processing)
            camera_img = self.get_camera_view_image()
            
            # Only update canvas if image has changed
            if camera_img != self.cached_camera_image:
                # Create PhotoImage only when image changes
                self._camera_imgtk = PIL.ImageTk.PhotoImage(camera_img)
                self.cached_camera_image = camera_img
                
                # Optimize canvas update: use itemconfig if image already exists, otherwise create
                if self.camera_image_id is None:
                    # First time: create image item
                    self.camera_image_id = self.camera_canvas.create_image(0, 0, anchor="nw", image=self._camera_imgtk)
                else:
                    # Update existing image item (more efficient than delete + create)
                    self.camera_canvas.itemconfig(self.camera_image_id, image=self._camera_imgtk)
                
                # Keep reference to prevent garbage collection
                self.cached_camera_imagetk = self._camera_imgtk
            
            # Submit new frame for processing if needed (with frame skipping)
            if self.camera_available:
                self.frame_skip_counter += 1
                if self.frame_skip_counter >= self.frame_skip_interval:
                    self._submit_frame_for_processing(camera_img)
                    self.frame_skip_counter = 0
        except Exception as e:
            print(f"Error updating camera view: {e}")
    
    def _submit_frame_for_processing(self, frame):
        """Submit frame to thread pool for vision processing with queue management"""
        if not self.camera_available:
            return
        
        # Clean up completed futures first
        for key, future in list(self.vision_futures.items()):
            if future.done():
                try:
                    result = future.result(timeout=0.01)
                    if key == 'visual_odometry':
                        self.vision_results['visual_odometry'] = result
                    elif key == 'dynamic_obstacles':
                        self.vision_results['dynamic_obstacles'] = result
                    elif key == 'scene_analysis':
                        self.vision_results['scene_analysis'] = result
                except Exception as e:
                    print(f"Error getting vision result for {key}: {e}")
                del self.vision_futures[key]
        
        # Skip frame if queue is full (prevent backlog)
        try:
            self.vision_frame_queue.put_nowait(frame)
        except:
            # Queue is full, skip this frame to prevent lag
            return
        
        # Process frame from queue if not already processing
        if not self.vision_processing_active:
            self._process_queued_frame()
    
    def _process_queued_frame(self):
        """Process next frame from queue"""
        if self.vision_processing_active:
            return
        
        try:
            frame = self.vision_frame_queue.get_nowait()
            self.vision_processing_active = True
            
            # Submit new processing tasks if not already processing
            if self.visual_odometry and self.visual_odometry_enabled and 'visual_odometry' not in self.vision_futures:
                future = self.vision_executor.submit(self.visual_odometry.process_frame, frame)
                self.vision_futures['visual_odometry'] = future
            
            if self.dynamic_obstacle_predictor and self.dynamic_obstacle_enabled and 'dynamic_obstacles' not in self.vision_futures:
                future = self.vision_executor.submit(self.dynamic_obstacle_predictor.process_frame, frame)
                self.vision_futures['dynamic_obstacles'] = future
            
            if self.scene_understanding and self.scene_understanding_enabled and 'scene_analysis' not in self.vision_futures:
                future = self.vision_executor.submit(self.scene_understanding.process_frame, frame)
                self.vision_futures['scene_analysis'] = future
            
            # Reset processing flag when all futures complete
            if not self.vision_futures:
                self.vision_processing_active = False
            else:
                # Check again after a short delay
                self.root.after(100, self._check_and_process_next_frame)
        except:
            # Queue is empty
            self.vision_processing_active = False
    
    def _check_and_process_next_frame(self):
        """Check if processing is done and process next frame"""
        # Check if all futures are done
        all_done = all(future.done() for future in self.vision_futures.values())
        if all_done:
            self.vision_processing_active = False
            # Process next frame if available
            if not self.vision_frame_queue.empty():
                self._process_queued_frame()
    
    def _check_vision_futures(self):
        """Check and collect completed vision processing futures"""
        for key, future in list(self.vision_futures.items()):
            if future.done():
                try:
                    result = future.result(timeout=0.01)
                    if key == 'visual_odometry':
                        self.vision_results['visual_odometry'] = result
                    elif key == 'dynamic_obstacles':
                        self.vision_results['dynamic_obstacles'] = result
                    elif key == 'scene_analysis':
                        self.vision_results['scene_analysis'] = result
                except Exception as e:
                    print(f"Error getting vision result for {key}: {e}")
                del self.vision_futures[key]
    
    def process_camera_features(self, frame):
        """Process camera frame with vision modules (legacy method, now uses async)"""
        # This method is kept for backward compatibility
        # Actual processing now happens in _submit_frame_for_processing
        return frame

    def get_sensor_diagnostics(self) -> dict:
        """Get detailed sensor diagnostics for troubleshooting"""
        try:
            availability = self.sensor_manager.check_sensor_availability()
            diagnostics = {
                'overall_status': availability['overall_status'],
                'health_message': self.sensor_manager.get_sensor_health_message(),
                'system_healthy': self.sensor_manager.is_system_healthy(),
                'hardware_available': availability['hardware_available'],
                'summary': availability['summary'],
                'unavailable_sensors': self.sensor_manager.get_unavailable_sensors(),
                'detailed_status': {}
            }
            
            # Add detailed status for each sensor type
            for sensor_type in ['ultrasonic', 'infrared', 'bumper']:
                diagnostics['detailed_status'][sensor_type] = {}
                for sensor_name, sensor_info in availability[sensor_type].items():
                    diagnostics['detailed_status'][sensor_type][sensor_name] = {
                        'available': sensor_info['available'],
                        'health': sensor_info['health']
                    }
            
            return diagnostics
            
        except Exception as e:
            return {
                'error': str(e),
                'overall_status': 'error',
                'health_message': f"Error getting diagnostics: {e}",
                'system_healthy': False
            }
    
    def show_sensor_diagnostics(self):
        """Show detailed sensor diagnostics in a popup window"""
        try:
            diagnostics = self.get_sensor_diagnostics()
            
            # Create popup window
            dialog = ctk.CTkToplevel(self.root)
            dialog.title("Sensor Diagnostics")
            dialog.geometry("600x500")
            dialog.transient(self.root)
            dialog.grab_set()
            
            # Create text widget for diagnostics
            text_widget = ctk.CTkTextbox(dialog, width=580, height=450)
            text_widget.pack(padx=10, pady=10, fill="both", expand=True)
            
            # Format diagnostics information
            diagnostic_text = "=== SENSOR DIAGNOSTICS ===\n\n"
            
            diagnostic_text += f"Overall Status: {diagnostics['overall_status']}\n"
            diagnostic_text += f"Health Message: {diagnostics['health_message']}\n"
            diagnostic_text += f"System Healthy: {'Yes' if diagnostics['system_healthy'] else 'No'}\n"
            diagnostic_text += f"Hardware Available: {'Yes' if diagnostics['hardware_available'] else 'No'}\n\n"
            
            if 'summary' in diagnostics:
                summary = diagnostics['summary']
                diagnostic_text += f"=== SUMMARY ===\n"
                diagnostic_text += f"Total Sensors: {summary['total_sensors']}\n"
                diagnostic_text += f"Available Sensors: {summary['available_sensors']}\n"
                diagnostic_text += f"Ultrasonic Available: {summary['ultrasonic_available']}/3\n"
                diagnostic_text += f"Infrared Available: {summary['infrared_available']}/2\n"
                diagnostic_text += f"Bumper Available: {summary['bumper_available']}/2\n\n"
            
            if 'unavailable_sensors' in diagnostics and diagnostics['unavailable_sensors']:
                diagnostic_text += f"=== UNAVAILABLE SENSORS ===\n"
                for sensor in diagnostics['unavailable_sensors']:
                    diagnostic_text += f"- {sensor}\n"
                diagnostic_text += "\n"
            
            if 'detailed_status' in diagnostics:
                diagnostic_text += f"=== DETAILED STATUS ===\n"
                for sensor_type, sensors in diagnostics['detailed_status'].items():
                    diagnostic_text += f"\n{sensor_type.upper()} SENSORS:\n"
                    for sensor_name, sensor_info in sensors.items():
                        diagnostic_text += f"  {sensor_name}:\n"
                        diagnostic_text += f"    Available: {'Yes' if sensor_info['available'] else 'No'}\n"
                        if 'health' in sensor_info:
                            health = sensor_info['health']
                            diagnostic_text += f"    Error Count: {health.get('error_count', 'N/A')}\n"
                            diagnostic_text += f"    Consecutive Failures: {health.get('consecutive_failures', 'N/A')}\n"
                            if health.get('last_error'):
                                diagnostic_text += f"    Last Error: {health['last_error']}\n"
                        diagnostic_text += "\n"
            
            # Insert text
            text_widget.insert("1.0", diagnostic_text)
            text_widget.configure(state="disabled")  # Make read-only
            
            # Add close button
            close_btn = ctk.CTkButton(dialog, text="Close", command=dialog.destroy)
            close_btn.pack(pady=10)
            
        except Exception as e:
            messagebox.showerror("Error", f"Failed to show sensor diagnostics: {e}")

    @staticmethod
    def launch_with_loading(init_fn, *args, **kwargs):
        """
        Show a loading splash, run init_fn in a background thread, then create the main GUI.
        init_fn should return (robot_state, motor_controller, sensor_manager, pathfinder, autonomous_controller)
        Returns the created RobotGUI instance.
        """
        import tkinter as tk
        import threading
        import sys
        import os
        
        # Add gui/dialogs to path for import
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'gui', 'dialogs'))
        
        try:
            from robot_splash_screen import RobotSplashScreen
        except ImportError:
            # Fallback to simple splash if import fails
            from ._simple_splash import SimpleSplashScreen as RobotSplashScreen
        
        # Create a temporary root window for the splash screen
        temp_root = tk.Tk()
        temp_root.withdraw()  # Hide the temporary root
        
        result = {}
        error = {}
        splash_screen = None
        
        def load():
            """Load components in background thread"""
            try:
                result['components'] = init_fn(*args, **kwargs)
            except Exception as e:
                error['exception'] = e
            finally:
                # Signal completion
                if splash_screen:
                    splash_screen.splash.after(0, lambda: None)
        
        def on_splash_complete():
            """Called when splash screen completes"""
            temp_root.quit()
        
        # Create splash screen
        splash_screen = RobotSplashScreen(temp_root, on_splash_complete)
        
        # Start loading in background thread
        threading.Thread(target=load, daemon=True).start()
        
        # Run splash screen
        temp_root.mainloop()
        
        # Clean up temporary root
        temp_root.destroy()
        
        # Check for errors
        if 'exception' in error:
            tk.messagebox.showerror("Error", f"Failed to initialize: {error['exception']}")
            raise error['exception']
        
        # Unpack components and create main GUI
        robot_state, motor_controller, sensor_manager, pathfinder, autonomous_controller = result['components']
        gui = RobotGUI(robot_state, motor_controller, sensor_manager, pathfinder, autonomous_controller)
        return gui
 