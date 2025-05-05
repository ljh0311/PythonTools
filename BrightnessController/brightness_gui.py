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
        self.root.geometry("430x480")  # Increased size for health recommendations
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
        # Mode selection
        mode_frame = ttk.LabelFrame(
            self.root, text="Brightness Control Mode", padding=10
        )
        mode_frame.pack(fill="x", padx=10, pady=5)

        self.mode_var = tk.StringVar(value="camera")
        ttk.Radiobutton(
            mode_frame, text="Camera-based", variable=self.mode_var, value="camera"
        ).pack(anchor="w")
        ttk.Radiobutton(
            mode_frame,
            text="Screen Content-based",
            variable=self.mode_var,
            value="screen",
        ).pack(anchor="w")

        # Current brightness display
        brightness_frame = ttk.LabelFrame(
            self.root, text="Current Brightness", padding=10
        )
        brightness_frame.pack(fill="x", padx=10, pady=5)

        self.brightness_label = ttk.Label(brightness_frame, text="Current: 0%")
        self.brightness_label.pack(anchor="w")

        self.brightness_bar = ttk.Progressbar(
            brightness_frame, length=300, mode="determinate"
        )
        self.brightness_bar.pack(fill="x", pady=5)

        # Session stats frame
        self.stats_frame = ttk.LabelFrame(
            self.root, text="Session Statistics", padding=10
        )
        self.stats_frame.pack(fill="x", padx=10, pady=5)

        self.session_avg_label = ttk.Label(self.stats_frame, text="Session Avg: N/A")
        self.session_avg_label.pack(anchor="w")

        self.session_time_label = ttk.Label(
            self.stats_frame, text="Session Time: 00:00"
        )
        self.session_time_label.pack(anchor="w")

        # Brightness category indicator with health focus
        self.category_label = ttk.Label(self.stats_frame, text="Brightness Level: N/A")
        self.category_label.pack(anchor="w", pady=(5, 0))

        # Health recommendation label
        self.health_label = ttk.Label(
            self.stats_frame, text="Health Status: N/A", wraplength=380
        )
        self.health_label.pack(anchor="w", pady=(5, 0))

        # Unhealthy range time tracker
        self.unhealthy_time_label = ttk.Label(
            self.stats_frame,
            text="Time in unhealthy range: 00:00",
            foreground="#AA0000",
        )
        self.unhealthy_time_label.pack(anchor="w", pady=(5, 0))

        # Visual brightness category indicator
        category_frame = ttk.Frame(self.stats_frame)
        category_frame.pack(fill="x", pady=5)

        # Create category indicators
        self.category_indicators = {}
        categories = list(self.brightness_categories.keys())

        for i, category in enumerate(categories):
            frame = ttk.Frame(category_frame, width=40, height=20)
            frame.grid(row=0, column=i, padx=1)
            frame.pack_propagate(False)

            # Add visual indicator for healthy ranges with border
            if category in ["healthy_low", "healthy_mid", "healthy_high"]:
                border_frame = ttk.Frame(frame, padding=1)
                border_frame.pack(fill="both", expand=True)
                label = ttk.Label(
                    border_frame, background=self.category_colors[category]
                )
                label.pack(fill="both", expand=True)

                # Add "SAFE" text to the healthy_mid category
                if category == "healthy_mid":
                    label.config(
                        text="SAFE", foreground="#FFFFFF", font=("Arial", 7, "bold")
                    )
            else:
                label = ttk.Label(frame, background=self.category_colors[category])
                label.pack(fill="both", expand=True)

            self.category_indicators[category] = label

        # Category selector (the triangle marker)
        self.category_selector = ttk.Label(
            category_frame, text="▼", foreground="red", font=("Arial", 12, "bold")
        )
        self.category_selector.place(x=0, y=-10)  # Will be positioned dynamically

        # Control buttons
        button_frame = ttk.Frame(self.root, padding=10)
        button_frame.pack(fill="x", padx=10, pady=5)

        self.start_button = ttk.Button(
            button_frame, text="Start", command=self.start_control
        )
        self.start_button.pack(side="left", padx=5)

        self.stop_button = ttk.Button(
            button_frame, text="Stop", command=self.stop_control, state="disabled"
        )
        self.stop_button.pack(side="left", padx=5)

        # Add Test button
        self.test_button = ttk.Button(
            button_frame, text="Test (5s)", command=self.start_test_control
        )
        self.test_button.pack(side="left", padx=5)

        # Help button to explain health recommendations
        self.help_button = ttk.Button(
            button_frame, text="Eye Health Info", command=self.show_health_info
        )
        self.help_button.pack(side="left", padx=5)

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

        if not is_current_healthy:
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
        print("Starting screen-based brightness control")

        while self.running and self.active_mode == "screen":
            current_time = time.time()
            if current_time - last_update_time >= update_interval:
                brightness = self.get_screen_brightness()
                print(f"Screen content brightness: {brightness}")
                smoothed_brightness = self.smooth_brightness(brightness)
                print(f"Smoothed brightness: {smoothed_brightness}")
                self.controller.adjust_screen_brightness(smoothed_brightness)
                last_update_time = current_time
            time.sleep(0.05)

    def camera_brightness_control(self):
        """Control brightness based on camera input."""
        print("Starting camera-based brightness control")
        while self.running and self.active_mode == "camera":
            brightness = self.controller.get_brightness_from_camera()
            print(f"Camera brightness: {brightness}")

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

        if self.active_mode == "camera":
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

                # Calculate percentage of time in healthy range
                if self.session_start_time is not None:
                    total_session_time = time.time() - self.session_start_time
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

                if self.session_start_time is not None:
                    elapsed_seconds = int(time.time() - self.session_start_time)
                    minutes, seconds = divmod(elapsed_seconds, 60)
                    print(f"  Session Duration: {minutes:02d}:{seconds:02d}")
                    print(f"  Time in healthy range: {healthy_percentage:.1f}%")

                    # Show session summary with health recommendations
                    unhealthy_minutes, _ = divmod(self.time_in_unhealthy_range, 60)
                    if unhealthy_minutes > 0:
                        messagebox.showinfo(
                            "Session Summary",
                            f"Session completed!\n\n"
                            f"Average brightness: {avg_brightness:.1f}\n"
                            f"Brightness category: {display_name}\n"
                            f"Time spent in non-optimal brightness: {unhealthy_minutes} minutes\n\n"
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
