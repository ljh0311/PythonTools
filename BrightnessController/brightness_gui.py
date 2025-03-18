"""
GUI application for controlling screen brightness based on camera or screen content.
"""

import tkinter as tk
from tkinter import ttk
import screen_brightness_control as sbc
from PIL import ImageGrab
import numpy as np
import threading
import time
from typing import Optional
from brightness_controller import BrightnessController


class BrightnessGUI:
    """GUI application for brightness control."""

    def __init__(self):
        """Initialize the GUI application."""
        self.root = tk.Tk()
        self.root.title("Brightness Control")
        self.root.geometry("400x300")
        self.root.resizable(False, False)

        # Initialize controllers and state
        self.controller = BrightnessController()
        self.active_mode = None
        self.running = False
        self.control_thread: Optional[threading.Thread] = None
        self.screen_brightness_history = []
        self.history_size = 5

        self._setup_gui()
        self._update_current_brightness()

    def _setup_gui(self):
        """Set up the GUI components."""
        # Mode selection
        mode_frame = ttk.LabelFrame(self.root, text="Brightness Control Mode", padding=10)
        mode_frame.pack(fill="x", padx=10, pady=5)

        self.mode_var = tk.StringVar(value="camera")
        ttk.Radiobutton(mode_frame, text="Camera-based", 
                       variable=self.mode_var, value="camera").pack(anchor="w")
        ttk.Radiobutton(mode_frame, text="Screen Content-based",
                       variable=self.mode_var, value="screen").pack(anchor="w")

        # Current brightness display
        brightness_frame = ttk.LabelFrame(self.root, text="Current Brightness", padding=10)
        brightness_frame.pack(fill="x", padx=10, pady=5)
        
        self.brightness_label = ttk.Label(brightness_frame, text="Current: 0%")
        self.brightness_label.pack(anchor="w")

        self.brightness_bar = ttk.Progressbar(brightness_frame, length=300, 
                                            mode="determinate")
        self.brightness_bar.pack(fill="x", pady=5)

        # Control buttons
        button_frame = ttk.Frame(self.root, padding=10)
        button_frame.pack(fill="x", padx=10, pady=5)

        self.start_button = ttk.Button(button_frame, text="Start", 
                                     command=self.start_control)
        self.start_button.pack(side="left", padx=5)

        self.stop_button = ttk.Button(button_frame, text="Stop",
                                    command=self.stop_control, state="disabled")
        self.stop_button.pack(side="left", padx=5)

        # Add Test button
        self.test_button = ttk.Button(button_frame, text="Test (5s)",
                                    command=self.start_test_control)
        self.test_button.pack(side="left", padx=5)

    def _update_current_brightness(self):
        """Update the brightness display in the GUI."""
        current = sbc.get_brightness()[0]
        self.brightness_label.config(text=f"Current: {current}%")
        self.brightness_bar["value"] = current
        if self.running:
            self.root.after(1000, self._update_current_brightness)

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

        screenshot = ImageGrab.grab(bbox=(left, top, left + sample_width, top + sample_height))
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
            self.controller.adjust_screen_brightness(brightness)
            time.sleep(0.1)

    def start_control(self):
        """Start the brightness control."""
        self.active_mode = self.mode_var.get()
        self.running = True

        if self.active_mode == "camera":
            self.controller.setup_camera()
            self.control_thread = threading.Thread(target=self.camera_brightness_control)
        else:
            self.control_thread = threading.Thread(target=self.screen_brightness_control)

        self.control_thread.daemon = True
        self.control_thread.start()

        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self._update_current_brightness()

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