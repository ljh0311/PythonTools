"""
GUI application for controlling screen brightness based on camera or screen content.
Includes eye health monitoring for safe brightness levels.
"""

import tkinter as tk
from tkinter import ttk, messagebox
import screen_brightness_control as sbc
from PIL import ImageGrab
import numpy as np
import threading
import time
from typing import Optional, List, Tuple, Dict
from brightness_controller import BrightnessController


class BrightnessGUI:
    """GUI application for brightness control with eye health monitoring."""

    def __init__(self):
        """Initialize the GUI application."""
        self.root = tk.Tk()
        self.root.title("Brightness Control - Eye Health Monitor")
        # self.root.geometry("430x520")  # Increased size for human detection controls
        self.root.resizable(False, False)

        # Initialize controllers and state
        self.controller = BrightnessController()
        self.active_mode = None
        self.running = False
        self.control_thread: Optional[threading.Thread] = None
        self.screen_brightness_history = []
        self.history_size = 5

        # Session tracking
        self.camera_brightness_values: List[float] = []
        self.session_start_time: Optional[float] = None
        self.time_in_unhealthy_range: int = 0
        self.last_health_check_time: Optional[float] = None
        self.warning_shown = False

        # Human detection tracking
        self.human_detection_enabled = tk.BooleanVar(value=True)
        self.strict_detection_enabled = tk.BooleanVar(value=True)
        self.auto_strict_enabled = tk.BooleanVar(value=True)
        self.grace_period_enabled = tk.BooleanVar(value=True)
        self.adaptive_grace_enabled = tk.BooleanVar(value=True)
        self.distance_detection_enabled = tk.BooleanVar(value=True)
        self.human_present = False
        self.last_human_detection_time = None

        # Brightness classification thresholds (0-255 scale)
        # Adjusted for eye health recommendations
        self.brightness_categories = {
            "too_dark": (0, 40),  # Very dim, potential eye strain
            "dark": (40, 80),  # Below recommended range
            "slightly_dark": (80, 100),  # Lower edge of healthy range
            "healthy_low": (100, 130),  # Healthy range for darker environments
            "healthy_mid": (130, 160),  # Optimal eye safety range
            "healthy_high": (160, 190),  # Healthy range for brighter environments
            "bright": (190, 220),  # Above recommended range
            "too_bright": (220, 255),  # Very bright, potential eye strain
        }

        # Category colors with health indicators
        self.category_colors = {
            "too_dark": "#444444",  # Dark gray - warning
            "dark": "#666666",  # Medium gray
            "slightly_dark": "#888888",  # Light gray
            "healthy_low": "#88BB88",  # Light green
            "healthy_mid": "#44AA44",  # Medium green
            "healthy_high": "#88BB88",  # Light green
            "bright": "#CCCCCC",  # Light gray
            "too_bright": "#FF9999",  # Light red - warning
        }

        # Health recommendations for each category
        self.health_recommendations: Dict[str, str] = {
            "too_dark": "Too dark - may cause eye strain. Consider increasing ambient light.",
            "dark": "Below recommended brightness. Consider adjusting screen or room lighting.",
            "slightly_dark": "Slightly dark but acceptable for low-light environments.",
            "healthy_low": "Healthy range for darker environments.",
            "healthy_mid": "Optimal brightness range for eye health.",
            "healthy_high": "Healthy range for brighter environments.",
            "bright": "Above recommended brightness. May be fine for very bright environments.",
            "too_bright": "Too bright - may cause eye strain. Consider reducing screen brightness or ambient light.",
        }

        self._setup_gui()
        self._update_current_brightness()

    def _setup_gui(self):
        """Set up the GUI components."""

        def create_label(parent, text, **kwargs):
            pady = kwargs.pop("pady", 0)
            label = ttk.Label(parent, text=text, **kwargs)
            label.pack(anchor="w", pady=pady)
            return label

        def create_button(parent, text, command, **kwargs):
            button = ttk.Button(parent, text=text, command=command, **kwargs)
            button.pack(side="left", padx=5)
            return button
        
        def create_frame(parent, text, **kwargs):
            frame = ttk.LabelFrame(parent, text=text, **kwargs)
            frame.pack(fill="x", padx=10, pady=5)
            return frame

        # Mode selection
        mode_frame = create_frame(self.root, "Brightness Control Mode")

        self.mode_var = tk.StringVar(value="camera")
        for text, value in [("Camera-based", "camera"), ("Screen Content-based", "screen")]:
            ttk.Radiobutton(mode_frame, text=text, variable=self.mode_var, value=value).pack(anchor="w")

        # Current brightness display
        brightness_frame = create_frame(self.root, "Current Brightness")

        self.brightness_label = create_label(brightness_frame, "Current: 0%")
        self.brightness_bar = ttk.Progressbar(brightness_frame, length=300, mode="determinate")
        self.brightness_bar.pack(fill="x", pady=5)

        # Session stats frame
        self.stats_frame = create_frame(self.root, "Session Statistics")

        self.session_avg_label = create_label(self.stats_frame, "Session Avg: N/A")
        self.session_time_label = create_label(self.stats_frame, "Session Time: 00:00")
        self.category_label = create_label(self.stats_frame, "Brightness Level: N/A", pady=(5, 0))
        self.health_label = create_label(self.stats_frame, "Health Status: N/A", wraplength=380, pady=(5, 0))
        self.unhealthy_time_label = ttk.Label(
            self.stats_frame,
            text="Time in unhealthy range: 00:00",
            foreground="#AA0000",
        )
        self.unhealthy_time_label.pack(anchor="w", pady=(5, 0))

        # Visual brightness category indicator
        category_frame = create_frame(self.stats_frame, "Brightness Category Indicator")

        # Create category indicators
        self.category_indicators = {}
        categories = list(self.brightness_categories.keys())

        for i, category in enumerate(categories):
            frame = ttk.Frame(category_frame, width=40, height=20)
            frame.grid(row=0, column=i, padx=1)
            frame.pack_propagate(False)

            if category in ["healthy_low", "healthy_mid", "healthy_high"]:
                border_frame = ttk.Frame(frame, padding=1)
                border_frame.pack(fill="both", expand=True)
                label = ttk.Label(border_frame, background=self.category_colors[category])
                label.pack(fill="both", expand=True)
                if category == "healthy_mid":
                    label.config(text="SAFE", foreground="#FFFFFF", font=("Arial", 7, "bold"))
            else:
                label = ttk.Label(frame, background=self.category_colors[category])
                label.pack(fill="both", expand=True)

            self.category_indicators[category] = label

        # Category selector (the triangle marker)
        self.category_selector = ttk.Label(
            category_frame, text="▼", foreground="red", font=("Arial", 12, "bold")
        )
        self.category_selector.place(x=0, y=-10)  # Will be positioned dynamically

        # Human detection frame with organized sections
        human_detection_frame = create_frame(self.root, "Human Detection")

        # Main toggle
        main_toggle_frame = ttk.Frame(human_detection_frame)
        main_toggle_frame.pack(fill="x", pady=(0, 10))
        
        self.human_detection_checkbox = ttk.Checkbutton(
            main_toggle_frame,
            text="Enable Human Detection",
            variable=self.human_detection_enabled,
        )
        self.human_detection_checkbox.pack(anchor="w")

        # Detection modes section
        modes_frame = ttk.LabelFrame(human_detection_frame, text="Detection Modes", padding="5")
        modes_frame.pack(fill="x", pady=(0, 10))

        self.distance_detection_checkbox = ttk.Checkbutton(
            modes_frame,
            text="Distance Detection (Primary User vs Background)",
            variable=self.distance_detection_enabled,
        )
        self.distance_detection_checkbox.pack(anchor="w", pady=2)

        self.strict_detection_checkbox = ttk.Checkbutton(
            modes_frame,
            text="Strict Detection (Higher Accuracy)",
            variable=self.strict_detection_enabled,
        )
        self.strict_detection_checkbox.pack(anchor="w", pady=2)

        self.auto_strict_checkbox = ttk.Checkbutton(
            modes_frame,
            text="Auto-Strict (Auto-switch when unstable)",
            variable=self.auto_strict_enabled,
        )
        self.auto_strict_checkbox.pack(anchor="w", pady=2)

        # Grace period section
        grace_frame = ttk.LabelFrame(human_detection_frame, text="Grace Period Settings", padding="5")
        grace_frame.pack(fill="x", pady=(0, 10))

        self.grace_period_checkbox = ttk.Checkbutton(
            grace_frame,
            text="Enable Grace Period (3s delay when looking away)",
            variable=self.grace_period_enabled,
        )
        self.grace_period_checkbox.pack(anchor="w", pady=2)

        self.adaptive_grace_checkbox = ttk.Checkbutton(
            grace_frame,
            text="Adaptive Timing (Learn from your behavior)",
            variable=self.adaptive_grace_enabled,
        )
        self.adaptive_grace_checkbox.pack(anchor="w", pady=2)

        # Status display
        status_frame = ttk.LabelFrame(human_detection_frame, text="Detection Status", padding="5")
        status_frame.pack(fill="x")

        self.human_present_label = create_label(status_frame, "Human Present: N/A")
        self.detection_status_label = create_label(status_frame, "Detection Status: Standard Mode")

        # Control buttons
        button_frame = ttk.Frame(self.root, padding=10)
        button_frame.pack(fill="x", padx=10, pady=5)

        self.start_button = create_button(button_frame, "Start", self.start_control)
        self.stop_button = create_button(button_frame, "Stop", self.stop_control, state="disabled")
        self.test_button = create_button(button_frame, "Test (5s)", self.start_test_control)
        self.help_button = create_button(button_frame, "Eye Health Info", self.show_health_info)
        self.human_info_button = create_button(button_frame, "Human Detection Info", self.show_human_detection_info)
    def show_health_info(self):
        """Show information about brightness and eye health."""
        info_message = """
Eye Health Brightness Guidelines:

• Brightness should match your environment
• Optimal range is typically 100-190 (on 0-255 scale)
• Too bright or too dark can cause eye strain
• Take regular breaks (20-20-20 rule)
• Consider blue light filtering for night use

The 20-20-20 rule: Every 20 minutes, look at something 
20 feet away for 20 seconds to reduce eye strain.

This app helps monitor your brightness levels and 
provides recommendations for healthier screen viewing.
        """
        messagebox.showinfo("Eye Health Information", info_message)

    def show_human_detection_info(self):
        """Show information about human detection functionality."""
        info_message = """
Human Detection Feature:

• Uses computer vision to detect human faces
• Automatically reduces screen brightness to 0% when no human is detected
• Helps save energy and reduce eye strain when you're away
• Uses OpenCV's Haar cascade classifier for face detection
• Requires good lighting and clear view of your face

Detection Modes:
• Standard Detection: Balanced sensitivity for most environments
• Strict Detection: Higher accuracy, reduces false positives from objects
  - Requires better lighting and clearer face positioning
  - More conservative detection parameters
  - Better for environments with many objects
• Auto-Strict Detection: Automatically switches to strict mode when instability is detected
  - Monitors detection stability in real-time
  - Switches to strict mode if too many rapid changes occur
  - Helps maintain consistent detection without manual intervention
• Grace Period: Maintains human detection for 3 seconds when face is temporarily blocked
  - Prevents flickering when you look away briefly
  - Handles temporary face blocking or turning
  - Reduces false negatives from momentary detection loss
• Adaptive Grace Period: Automatically adjusts grace period timing based on your behavior patterns
  - Learns from your recent face loss patterns (last 10 events)
  - Adjusts duration between 1-8 seconds based on your typical behavior
  - Provides personalized timing for optimal user experience
• Distance Detection: Differentiates between primary user (close to camera) and distant people
  - Only considers faces close to the camera as the primary user
  - Ignores people walking by in the background or sitting far away
  - Uses face size relative to frame to determine distance
  - Helps prevent false triggers from distant people
  - Can be calibrated for your specific setup using the test tool

How it works:
• Camera continuously monitors for human presence
• When a face is detected, normal brightness control resumes
• When no face is detected for several frames, brightness drops to 0%
• Detection uses a history buffer to reduce false positives/negatives
• Additional validation checks face quality, size, and aspect ratio

Tips for best results:
• Ensure good lighting on your face (not too dark or too bright)
• Position yourself clearly in front of the camera
• Keep the camera unobstructed
• Use "Strict Detection" if you experience false positives
• Enable "Grace Period" to handle brief moments when looking away
• Enable "Adaptive Grace Period" for personalized timing based on your behavior
• Enable "Distance Detection" to ignore people in the background
• Use the test tool (test.py) to calibrate distance detection for your setup
• The feature works best in camera-based mode

Troubleshooting:
• If detection is unstable, try enabling "Strict Detection"
• If detection is too strict, disable "Strict Detection"
• If detection flickers when looking away, enable "Grace Period"
• If grace period timing doesn't match your behavior, enable "Adaptive Grace Period"
• If people in the background trigger detection, enable "Distance Detection"
• If distance detection is too sensitive/not sensitive enough, use test.py to recalibrate
• Ensure your face takes up a reasonable portion of the camera view
• Check that lighting is consistent and not too harsh

Note: This feature requires a working webcam and may not work perfectly in all lighting conditions.
        """
        messagebox.showinfo("Human Detection Information", info_message)

    def _update_current_brightness(self):
        """Update the brightness display in the GUI."""
        current = sbc.get_brightness()[0]
        self.brightness_label.config(text=f"Current: {current}%")
        self.brightness_bar["value"] = current
        if self.running:
            self.root.after(1000, self._update_current_brightness)

    def is_healthy_brightness(self, category: str) -> bool:
        """Check if the brightness category is in the healthy range."""
        return category in ["healthy_low", "healthy_mid", "healthy_high"]

    def classify_brightness(self, brightness: float) -> Tuple[str, str]:
        for category, (lower, upper) in self.brightness_categories.items():
            if lower <= brightness < upper:
                # Convert category_name to display_name (e.g., "healthy_mid" -> "Healthy Mid")
                display_name = category.replace("_", " ").title()
                return category, display_name

        # Default fallback
        return "healthy_mid", "Healthy Mid"

    def update_unhealthy_time(self, is_current_healthy: bool):
        """Update the time spent in unhealthy brightness ranges."""
        current_time = time.time()

        if self.last_health_check_time is None:
            self.last_health_check_time = current_time
            return

        time_diff = current_time - self.last_health_check_time
        self.last_health_check_time = current_time

        # Only count unhealthy time when a human is present
        # When no human is present (brightness = 0), it's intentional power saving, not unhealthy
        if not is_current_healthy and self.human_present:
            self.time_in_unhealthy_range += int(time_diff)

            # Show warning if in unhealthy range for more than 5 minutes
            if self.time_in_unhealthy_range > 300 and not self.warning_shown:
                messagebox.showwarning(
                    "Eye Health Warning",
                    "You've been using a non-optimal brightness level for over 5 minutes.\n"
                    "This may contribute to eye strain. Consider adjusting your brightness "
                    "or taking a short break.",
                )
                self.warning_shown = True

        # Format and display the unhealthy time
        minutes, seconds = divmod(self.time_in_unhealthy_range, 60)
        if self.human_detection_enabled.get():
            self.unhealthy_time_label.config(
                text=f"Time in unhealthy range (when present): {minutes:02d}:{seconds:02d}"
            )
        else:
            self.unhealthy_time_label.config(
                text=f"Time in unhealthy range: {minutes:02d}:{seconds:02d}"
            )

    def _update_session_stats(self):
        """Update session statistics display."""
        if self.running and self.active_mode == "camera":
            # Update session time
            if self.session_start_time is not None:
                elapsed_seconds = int(time.time() - self.session_start_time)
                minutes, seconds = divmod(elapsed_seconds, 60)
                self.session_time_label.config(
                    text=f"Session Time: {minutes:02d}:{seconds:02d}"
                )

            # Update average brightness and category
            if self.camera_brightness_values:
                avg_brightness = np.mean(self.camera_brightness_values)
                category, display_name = self.classify_brightness(avg_brightness)

                # Update labels
                self.session_avg_label.config(
                    text=f"Session Avg: {avg_brightness:.1f} (0-255)"
                )

                # Set color based on health status
                is_healthy = self.is_healthy_brightness(category)
                text_color = "#006600" if is_healthy else "#AA0000"

                self.category_label.config(
                    text=f"Brightness Level: {display_name}", foreground=text_color
                )

                # Update health recommendation
                if category in self.health_recommendations:
                    self.health_label.config(
                        text=f"Health Status: {self.health_recommendations[category]}",
                        foreground=text_color,
                    )

                # Update unhealthy time tracking
                self.update_unhealthy_time(is_healthy)

                # Position the category selector
                categories = list(self.brightness_categories.keys())
                index = categories.index(category)
                # Each indicator is approximately 40px wide
                x_pos = (index * 42) + 20
                self.category_selector.place(x=x_pos, y=-10)

            # Schedule next update
            self.root.after(1000, self._update_session_stats)

    def get_screen_brightness(self) -> float:
        """
        Calculate average brightness of screen content.

        Returns:
            float: Average brightness value from screen content
        """
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()

        sample_width = screen_width // 2
        sample_height = screen_height // 2
        left = (screen_width - sample_width) // 2
        top = (screen_height - sample_height) // 2

        screenshot = ImageGrab.grab(
            bbox=(left, top, left + sample_width, top + sample_height)
        )
        gray_screenshot = screenshot.convert("L")
        return float(np.mean(np.array(gray_screenshot)))

    def smooth_brightness(self, new_value: float) -> float:
        """
        Apply smoothing to brightness values.

        Args:
            new_value: New brightness value to smooth

        Returns:
            float: Smoothed brightness value
        """
        self.screen_brightness_history.append(new_value)
        if len(self.screen_brightness_history) > self.history_size:
            self.screen_brightness_history.pop(0)
        return float(np.median(self.screen_brightness_history))

    def screen_brightness_control(self):
        """Control brightness based on screen content."""
        last_update_time = 0
        update_interval = 0.2
        iteration_count = 0
        print("🖥️ Starting screen-based brightness control")

        while self.running and self.active_mode == "screen":
            current_time = time.time()
            if current_time - last_update_time >= update_interval:
                brightness = self.get_screen_brightness()
                iteration_count += 1
                
                # Only print screen brightness every 25 iterations to reduce spam
                if iteration_count % 25 == 0:
                    print(f"🖥️ Screen reading #{iteration_count}: {brightness:.1f}")
                
                smoothed_brightness = self.smooth_brightness(brightness)
                self.controller.adjust_screen_brightness(smoothed_brightness)
                last_update_time = current_time
            time.sleep(0.05)

    def camera_brightness_control(self):
        """Control brightness based on camera input."""
        print("📹 Starting camera-based brightness control")
        iteration_count = 0
        while self.running and self.active_mode == "camera":
            brightness = self.controller.get_brightness_from_camera()
            iteration_count += 1
            
            # Update human detection status
            if self.human_detection_enabled.get():
                # Check if brightness is 0 (no human detected)
                self.human_present = brightness > 0.0
                self.last_human_detection_time = time.time()
                
                # Update GUI label
                status_text = "✅ Present" if self.human_present else "❌ Not Detected"
                self.human_present_label.config(
                    text=f"Human Present: {status_text}",
                    foreground="green" if self.human_present else "red"
                )
                
                # Update auto-strict setting if changed
                if hasattr(self.controller, 'auto_strict_detection'):
                    if self.controller.auto_strict_detection != self.auto_strict_enabled.get():
                        self.controller.update_auto_strict_setting(self.auto_strict_enabled.get())
                
                # Update grace period setting if changed
                if hasattr(self.controller, 'grace_period_enabled'):
                    if self.controller.grace_period_enabled != self.grace_period_enabled.get():
                        self.controller.update_grace_period_setting(self.grace_period_enabled.get())
                
                # Update adaptive grace period setting if changed
                if hasattr(self.controller, 'adaptive_grace_period'):
                    if self.controller.adaptive_grace_period != self.adaptive_grace_enabled.get():
                        self.controller.update_adaptive_grace_period_setting(self.adaptive_grace_enabled.get())
                
                # Update distance detection setting if changed
                if hasattr(self.controller, 'enable_distance_detection'):
                    if self.controller.enable_distance_detection != self.distance_detection_enabled.get():
                        self.controller.enable_distance_detection = self.distance_detection_enabled.get()
                
                # Update detection status
                detection_status = self.controller.get_detection_status()
                mode_text = "Strict Mode" if detection_status.get("strict_mode", False) else "Standard Mode"
                auto_text = " (Auto-switched)" if detection_status.get("auto_switched", False) else ""
                stability_text = f" - {detection_status.get('stability_percentage', 0):.0f}% stable"
                grace_text = " [Grace Period]" if detection_status.get("grace_period_active", False) else ""
                
                # Add adaptive grace period info
                if detection_status.get("adaptive_grace_period", False):
                    current_duration = detection_status.get("current_grace_duration", 3.0)
                    face_loss_count = detection_status.get("face_loss_count", 0)
                    adaptive_text = f" (adaptive: {current_duration:.1f}s, {face_loss_count} patterns)"
                else:
                    adaptive_text = ""
                
                self.detection_status_label.config(
                    text=f"Detection Status: {mode_text}{auto_text}{stability_text}{grace_text}{adaptive_text}",
                    foreground="orange" if detection_status.get("strict_mode", False) else "blue"
                )
            
            # Only print camera brightness every 100 iterations to reduce spam
            if iteration_count % 100 == 0:
                human_status = "👤 Present" if self.human_present else "👤 Not Detected"
                print(f"📹 Camera reading #{iteration_count}: {brightness:.1f} ({human_status})")

            # Store the brightness value for session tracking
            self.camera_brightness_values.append(brightness)

            self.controller.adjust_screen_brightness(brightness)
            time.sleep(0.1)

    def start_control(self):
        """Start the brightness control."""
        self.active_mode = self.mode_var.get()
        self.running = True

        # Reset session tracking
        self.camera_brightness_values = []
        self.session_start_time = time.time()
        self.time_in_unhealthy_range = 0
        self.last_health_check_time = None
        self.warning_shown = False

        # Reset human detection status
        self.human_present = False
        self.last_human_detection_time = None

        if self.active_mode == "camera":
            # Reinitialize controller with current human detection setting
            self.controller = BrightnessController(
                enable_human_detection=self.human_detection_enabled.get(),
                strict_detection=self.strict_detection_enabled.get(),
                enable_distance_detection=self.distance_detection_enabled.get()
            )
            self.controller.setup_camera()
            self.control_thread = threading.Thread(
                target=self.camera_brightness_control
            )
        else:
            self.control_thread = threading.Thread(
                target=self.screen_brightness_control
            )

        self.control_thread.daemon = True
        self.control_thread.start()

        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self._update_current_brightness()

        # Start updating session stats if in camera mode
        if self.active_mode == "camera":
            self._update_session_stats()

    def start_test_control(self):
        """Start a 5-second test run of the brightness control."""
        self.test_button.config(state="disabled")
        self.start_button.config(state="disabled")

        # Start the control
        self.start_control()

        # Schedule the stop after 5 seconds
        self.root.after(5000, self.stop_test_control)

    def stop_test_control(self):
        """Stop the test run and reset buttons."""
        self.stop_control()
        self.test_button.config(state="normal")
        self.start_button.config(state="normal")

    def stop_control(self):
        """Stop the brightness control."""
        self.running = False
        if self.control_thread:
            self.control_thread.join()
        if self.active_mode == "camera":
            self.controller.cleanup()

            # Calculate and display final session stats
            if self.camera_brightness_values:
                avg_brightness = np.mean(self.camera_brightness_values)
                category, display_name = self.classify_brightness(avg_brightness)
                is_healthy = self.is_healthy_brightness(category)

                min_brightness = np.min(self.camera_brightness_values)
                max_brightness = np.max(self.camera_brightness_values)

                # Calculate percentage of time in healthy range (only when human is present)
                if self.session_start_time is not None:
                    total_session_time = time.time() - self.session_start_time
                    
                    # Calculate time when human was present
                    if self.human_detection_enabled.get():
                        zero_brightness_count = sum(1 for b in self.camera_brightness_values if b == 0.0)
                        total_readings = len(self.camera_brightness_values)
                        human_present_time = total_session_time * (total_readings - zero_brightness_count) / total_readings
                        
                        # Calculate healthy percentage only for time when human was present
                        healthy_time = human_present_time - self.time_in_unhealthy_range
                        healthy_percentage = (
                            (healthy_time / human_present_time) * 100
                            if human_present_time > 0
                            else 0
                        )
                    else:
                        # If human detection is disabled, use total session time
                        healthy_time = total_session_time - self.time_in_unhealthy_range
                        healthy_percentage = (
                            (healthy_time / total_session_time) * 100
                            if total_session_time > 0
                            else 0
                        )

                print(f"Session Summary:")
                print(f"  Average Brightness: {avg_brightness:.1f} (0-255)")
                print(f"  Brightness Category: {display_name}")
                print(
                    f"  Health Status: {'Healthy' if is_healthy else 'Potentially Straining'}"
                )
                print(f"  Min Brightness: {min_brightness:.1f}")
                print(f"  Max Brightness: {max_brightness:.1f}")
                print(f"  Readings: {len(self.camera_brightness_values)}")

                # Human detection statistics
                if self.human_detection_enabled.get():
                    zero_brightness_count = sum(1 for b in self.camera_brightness_values if b == 0.0)
                    human_detection_percentage = ((len(self.camera_brightness_values) - zero_brightness_count) / len(self.camera_brightness_values)) * 100
                    print(f"  Human Detection: {human_detection_percentage:.1f}% of time")
                    print(f"  Time without human: {zero_brightness_count} readings")

                if self.session_start_time is not None:
                    elapsed_seconds = int(time.time() - self.session_start_time)
                    minutes, seconds = divmod(elapsed_seconds, 60)
                    print(f"  Session Duration: {minutes:02d}:{seconds:02d}")
                    if self.human_detection_enabled.get():
                        print(f"  Time in healthy range (when present): {healthy_percentage:.1f}%")
                    else:
                        print(f"  Time in healthy range: {healthy_percentage:.1f}%")

                    # Show session summary with health recommendations
                    unhealthy_minutes, _ = divmod(self.time_in_unhealthy_range, 60)
                    
                    # Prepare human detection summary
                    human_detection_summary = ""
                    if self.human_detection_enabled.get():
                        zero_brightness_count = sum(1 for b in self.camera_brightness_values if b == 0.0)
                        human_detection_percentage = ((len(self.camera_brightness_values) - zero_brightness_count) / len(self.camera_brightness_values)) * 100
                        human_detection_summary = f"\nHuman detection: {human_detection_percentage:.1f}% of time"
                        if zero_brightness_count > 0:
                            human_detection_summary += f"\nTime without human: {zero_brightness_count} readings"
                    
                    if unhealthy_minutes > 0:
                        messagebox.showinfo(
                            "Session Summary",
                            f"Session completed!\n\n"
                            f"Average brightness: {avg_brightness:.1f}\n"
                            f"Brightness category: {display_name}\n"
                            f"Time spent in non-optimal brightness (when present): {unhealthy_minutes} minutes"
                            f"{human_detection_summary}\n\n"
                            f"Recommendation: {self.health_recommendations.get(category, '')}",
                        )
                    else:
                        messagebox.showinfo(
                            "Session Summary",
                            f"Session completed!\n\n"
                            f"Average brightness: {avg_brightness:.1f}\n"
                            f"Brightness category: {display_name}\n"
                            f"Great job! No unhealthy brightness levels detected when you were present."
                            f"{human_detection_summary}\n\n"
                            f"Recommendation: {self.health_recommendations.get(category, '')}",
                        )

        self.start_button.config(state="normal")
        self.stop_button.config(state="disabled")
        self.test_button.config(state="normal")  # Enable test button
        self.active_mode = None

    def run(self):
        """Start the GUI application."""
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.root.mainloop()

    def on_closing(self):
        """Handle application closing."""
        self.stop_control()
        self.root.destroy()


def main():
    """Main entry point for the application."""
    app = BrightnessGUI()
    app.run()


if __name__ == "__main__":
    main()
