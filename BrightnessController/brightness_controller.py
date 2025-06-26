"""
Brightness Controller module for managing screen brightness based on camera or screen content.
"""

import time
import cv2
import numpy as np
import screen_brightness_control as sbc
from typing import List, Optional


class BrightnessController:
    """Controls screen brightness based on input from camera or screen content."""
    
    def __init__(
        self,
        min_brightness: int = 15,
        max_brightness: int = 100,
        history_size: int = 30,
        transition_steps: int = 5,
        transition_delay: float = 0.05,
        camera_index: int = 0
    ):
        """
        Initialize the brightness controller.
        
        Args:
            min_brightness: Minimum allowed brightness level (default: 15)
            max_brightness: Maximum allowed brightness level (default: 100)
            history_size: Size of brightness history buffer for smoothing (default: 30)
            transition_steps: Number of steps for smooth brightness transition (default: 5)
            transition_delay: Delay between transition steps in seconds (default: 0.05)
            camera_index: Index of the camera to use (default: 0)
        """
        self.min_brightness = min_brightness
        self.max_brightness = max_brightness
        self.history_size = history_size
        self.prev_values: List[float] = []
        self.last_set: Optional[int] = None
        self.transition_steps = transition_steps
        self.transition_delay = transition_delay
        self.camera_index = camera_index
        self.current_brightness = sbc.get_brightness()[0]
        self.cap = None

    def setup_camera(self) -> None:
        """Initialize and configure the camera."""
        if self.cap is not None:
            self.cap.release()
        
        self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.camera_index)
            if not self.cap.isOpened():
                raise RuntimeError(f"Could not open camera {self.camera_index}")
        
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    def get_brightness_from_camera(self) -> float:
        """
        Capture and calculate brightness from camera frame.
        
        Returns:
            float: Average brightness value from camera frame
        """
        if self.cap is None or not self.cap.isOpened():
            self.setup_camera()
            
        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to capture frame")
            
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        return float(np.mean(gray))

    def smooth_transition(self, start_brightness: int, target_brightness: int) -> None:
        """
        Smoothly transition between brightness levels.
        
        Args:
            start_brightness: Starting brightness level
            target_brightness: Target brightness level
        """
        if start_brightness == target_brightness:
            return

        brightness_diff = target_brightness - start_brightness
        step = brightness_diff / self.transition_steps

        for i in range(1, self.transition_steps + 1):
            intermediate_brightness = int(start_brightness + step * i)
            try:
                sbc.set_brightness(intermediate_brightness)
                time.sleep(self.transition_delay)
            except Exception as e:
                print(f"Error during transition: {e}")
                break

    def adjust_screen_brightness(self, brightness: float) -> None:
        """
        Adjust screen brightness based on input value.
        
        Args:
            brightness: Raw brightness value to adjust to
        """
        self.prev_values.append(brightness)
        if len(self.prev_values) > self.history_size:
            self.prev_values.pop(0)

        filtered_brightness = np.median(self.prev_values)
        new_brightness = np.clip(
            int(filtered_brightness / 255 * 100),
            self.min_brightness,
            self.max_brightness,
        )

        if self.last_set is None:
            self.last_set = new_brightness
        elif abs(new_brightness - self.last_set) <= 3:
            # Only print when there's significant change or periodically
            return

        if abs(new_brightness - self.last_set) > 3:
            print(f"🔄 Brightness: {self.current_brightness}% → {new_brightness}% "
                  f"(Raw: {brightness:.1f}, Filtered: {filtered_brightness:.1f})")
            try:
                self.smooth_transition(self.current_brightness, new_brightness)
                self.current_brightness = new_brightness
                self.last_set = new_brightness
            except Exception as e:
                print(f"❌ Error setting brightness: {e}")
        else:
            # Print status every 50 iterations or so to show the system is working
            if len(self.prev_values) % 50 == 0:
                print(f"📊 Status: {new_brightness}% (Raw: {brightness:.1f}, Filtered: {filtered_brightness:.1f})")

    def cleanup(self) -> None:
        """Release camera resources."""
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows() 