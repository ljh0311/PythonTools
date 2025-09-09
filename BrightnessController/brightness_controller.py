"""
Brightness Controller module for managing screen brightness based on camera or screen content.
"""

import time
import cv2
import numpy as np
import screen_brightness_control as sbc
from typing import List, Optional
import os


class BrightnessController:
    """Controls screen brightness based on input from camera or screen content."""

    def __init__(
        self,
        min_brightness: int = 15,
        max_brightness: int = 100,
        history_size: int = 30,
        transition_steps: int = 5,
        transition_delay: float = 0.05,
        camera_index: int = 0,
        enable_human_detection: bool = True,
        strict_detection: bool = True,
        enable_distance_detection: bool = True,
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
            enable_human_detection: Whether to enable human detection (default: True)
            strict_detection: Whether to use strict detection parameters (default: True)
            enable_distance_detection: Whether to differentiate between close and distant people (default: True)
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
        self.enable_human_detection = enable_human_detection
        self.strict_detection = strict_detection
        self.enable_distance_detection = enable_distance_detection
        self.auto_strict_detection = (
            True  # Enable automatic strict mode (can be toggled)
        )
        self.face_cascade = None
        self.human_detection_history: List[bool] = []
        self.detection_history_size = (
            20  # Number of consecutive detections to confirm human presence
        )

        # Distance-based detection parameters
        self.primary_user_face_size_threshold = (
            0.025  # 2.5% of frame - minimum for primary user
        )
        self.distant_person_face_size_threshold = (
            0.008  # 0.8% of frame - minimum for any person
        )
        self.calibration_mode = False
        self.calibration_samples = []
        self.calibrated_thresholds = {
            "primary_user_min": 0.025,
            "primary_user_max": 0.15,
            "distant_person_min": 0.008,
            "distant_person_max": 0.025,
        }

        # Auto-strict detection tracking
        self.detection_instability_count = 0
        self.last_detection_changes = []
        self.instability_threshold = 5  # Number of rapid changes to trigger strict mode

        # Grace period for temporary face blocking/looking away
        self.grace_period_enabled = True
        self.grace_period_duration = (
            3.0  # seconds to maintain detection when face is temporarily lost
        )
        self.adaptive_grace_period = True  # Enable adaptive grace period timing
        self.last_human_detected_time = None
        self.grace_period_active = False

        # Adaptive grace period tracking
        self.face_loss_durations = []  # Track how long face is typically lost
        self.face_return_times = []  # Track when face returns after being lost
        self.adaptive_history_size = 10  # Number of recent face loss events to consider
        self.min_grace_period = 1.0  # Minimum grace period duration
        self.max_grace_period = 8.0  # Maximum grace period duration

        self.human_detector = HumanDetector(
            enable_human_detection=self.enable_human_detection,
            strict_detection=self.strict_detection,
            enable_distance_detection=self.enable_distance_detection,
            auto_strict_detection=self.auto_strict_detection,
            detection_history_size=self.detection_history_size,
        )
        # Initialize face detection if enabled
        if self.enable_human_detection:
            self.human_detector._setup_face_detection()
            

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

        # Check for human presence if detection is enabled
        if self.enable_human_detection:
            human_present = self.human_detector.detect_human(frame)
            if not human_present:
                # Return 0 brightness when no human is detected
                return 0.0

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
        # If brightness is 0 (no human detected), set screen to 0 immediately
        if brightness == 0.0 and self.enable_human_detection:
            if self.current_brightness != 0:
                print("👤 No human detected - setting brightness to 0%")
                try:
                    sbc.set_brightness(0)
                    self.current_brightness = 0
                    self.last_set = 0
                except Exception as e:
                    print(f"❌ Error setting brightness to 0: {e}")
            return

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
            print(
                f"🔄 Brightness: {self.current_brightness}% → {new_brightness}% "
                f"(Raw: {brightness:.1f}, Filtered: {filtered_brightness:.1f})"
            )
            try:
                self.smooth_transition(self.current_brightness, new_brightness)
                self.current_brightness = new_brightness
                self.last_set = new_brightness
            except Exception as e:
                print(f"❌ Error setting brightness: {e}")
        else:
            # Print status every 50 iterations or so to show the system is working
            if len(self.prev_values) % 50 == 0:
                print(
                    f"📊 Status: {new_brightness}% (Raw: {brightness:.1f}, Filtered: {filtered_brightness:.1f})"
                )

    def cleanup(self) -> None:
        """Release camera resources."""
        if self.cap is not None:
            self.cap.release()
        cv2.destroyAllWindows()


class HumanDetector:
    def __init__(
        self,
        enable_human_detection=True,
        strict_detection=False,
        enable_distance_detection=False,
        auto_strict_detection=True,
        detection_history_size=20,
        primary_user_face_size_threshold=0.025,
        distant_person_face_size_threshold=0.008,
        calibrated_thresholds=None,
        grace_period_enabled=True,
        grace_period_duration=3.0,
        adaptive_grace_period=True,
        adaptive_history_size=10,
        min_grace_period=1.0,
        max_grace_period=8.0,
        instability_threshold=5,
    ):
        self.enable_human_detection = enable_human_detection
        self.strict_detection = strict_detection
        self.enable_distance_detection = enable_distance_detection
        self.auto_strict_detection = auto_strict_detection
        self.detection_history_size = detection_history_size
        self.primary_user_face_size_threshold = primary_user_face_size_threshold
        self.distant_person_face_size_threshold = distant_person_face_size_threshold
        self.calibration_mode = False
        self.calibration_samples = []
        self.calibrated_thresholds = calibrated_thresholds or {
            "primary_user_min": 0.025,
            "primary_user_max": 0.15,
            "distant_person_min": 0.008,
            "distant_person_max": 0.025,
        }
        self.detection_instability_count = 0
        self.last_detection_changes = []
        self.instability_threshold = instability_threshold
        self.human_detection_history = []
        self.face_cascade = None

        self.grace_period_enabled = grace_period_enabled
        self.grace_period_duration = grace_period_duration
        self.adaptive_grace_period = adaptive_grace_period
        self.last_human_detected_time = None
        self.grace_period_active = False

        self.face_loss_durations = []
        self.face_return_times = []
        self.adaptive_history_size = adaptive_history_size
        self.min_grace_period = min_grace_period
        self.max_grace_period = max_grace_period

        if self.enable_human_detection:
            self._setup_face_detection()

    def _setup_face_detection(self) -> None:
        """Initialize the face detection cascade classifier."""
        try:
            import cv2
            import os

            # Try to load the cascade classifier from OpenCV's data directory
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            if os.path.exists(cascade_path):
                self.face_cascade = cv2.CascadeClassifier(cascade_path)
            else:
                # Fallback: try to find it in common locations
                possible_paths = [
                    "haarcascade_frontalface_default.xml",
                    "data/haarcascade_frontalface_default.xml",
                    "/usr/share/opencv4/haarcascades/haarcascade_frontalface_default.xml",
                ]
                for path in possible_paths:
                    if os.path.exists(path):
                        self.face_cascade = cv2.CascadeClassifier(path)
                        break
                if self.face_cascade is None:
                    print(
                        "⚠️ Warning: Could not load face detection model. Human detection will be disabled."
                    )
                    self.enable_human_detection = False
                    return
            if self.face_cascade.empty():
                print(
                    "⚠️ Warning: Face detection model is empty. Human detection will be disabled."
                )
                self.enable_human_detection = False
            else:
                print("✅ Face detection model loaded successfully")
        except Exception as e:
            print(
                f"⚠️ Warning: Error loading face detection model: {e}. Human detection will be disabled."
            )
            self.enable_human_detection = False

    def detect_human(self, frame) -> bool:
        """
        Detect if a human is present in the frame using face detection.
        With distance detection enabled, only considers close faces as primary users.
        Args:
            frame: Camera frame as numpy array
        Returns:
            bool: True if primary user (close) is detected, False otherwise
        """
        import cv2
        import numpy as np
        import time

        if not self.enable_human_detection or self.face_cascade is None:
            return True  # If detection is disabled, assume human is present

        try:
            # Convert to grayscale for face detection
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Use more strict detection parameters to reduce false positives
            if self.strict_detection:
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.2, minNeighbors=12, minSize=(60, 60)
                )
            else:
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.15, minNeighbors=8, minSize=(50, 50)
                )

            human_detected = False
            primary_user_detected = False
            distant_person_detected = False

            if len(faces) > 0:
                largest_face = max(faces, key=lambda x: x[2] * x[3])
                x, y, w, h = largest_face
                face_region = gray[y : y + h, x : x + w]
                face_brightness = np.mean(face_region)
                brightness_min = 40 if self.strict_detection else 30
                brightness_max = 200 if self.strict_detection else 220

                if brightness_min < face_brightness < brightness_max:
                    aspect_ratio = w / h
                    aspect_min = 0.8 if self.strict_detection else 0.7
                    aspect_max = 1.3 if self.strict_detection else 1.5

                    if aspect_min < aspect_ratio < aspect_max:
                        frame_area = frame.shape[0] * frame.shape[1]
                        face_area = w * h
                        face_percentage = face_area / frame_area

                        if self.enable_distance_detection:
                            if (
                                face_percentage
                                >= self.calibrated_thresholds["primary_user_min"]
                            ):
                                primary_user_detected = True
                                human_detected = True
                            elif (
                                face_percentage
                                >= self.calibrated_thresholds["distant_person_min"]
                            ):
                                distant_person_detected = True
                        else:
                            min_face_percentage = (
                                0.015 if self.strict_detection else 0.01
                            )
                            if face_percentage >= min_face_percentage:
                                human_detected = True
                                primary_user_detected = True

            current_time = time.time()

            if human_detected:
                if self.grace_period_active:
                    face_loss_duration = current_time - self.last_human_detected_time
                    self._update_face_loss_patterns(face_loss_duration)
                self.last_human_detected_time = current_time
                self.grace_period_active = False
            elif (
                self.grace_period_enabled and self.last_human_detected_time is not None
            ):
                time_since_last_detection = current_time - self.last_human_detected_time
                current_grace_duration = self._calculate_adaptive_grace_period()
                if time_since_last_detection <= current_grace_duration:
                    human_detected = True
                    self.grace_period_active = True
                    if int(time_since_last_detection * 10) % 5 == 0:
                        remaining_grace = (
                            current_grace_duration - time_since_last_detection
                        )
                        adaptive_text = (
                            f" (adaptive: {current_grace_duration:.1f}s)"
                            if self.adaptive_grace_period
                            else ""
                        )
                        print(
                            f"⏰ Grace period active: {remaining_grace:.1f}s remaining{adaptive_text}"
                        )
                else:
                    self.grace_period_active = False

            self.human_detection_history.append(human_detected)
            if len(self.human_detection_history) > self.detection_history_size:
                self.human_detection_history.pop(0)

            self._check_detection_instability()

            if len(self.human_detection_history) >= 5:
                required_percentage = 0.7 if self.strict_detection else 0.6
                final_result = (
                    sum(self.human_detection_history)
                    >= len(self.human_detection_history) * required_percentage
                )
                if len(self.human_detection_history) % 50 == 0:
                    print(
                        f"🔍 Detection: {len(faces)} faces found, history: {sum(self.human_detection_history)}/{len(self.human_detection_history)}, result: {final_result}"
                    )
                return final_result
            elif len(self.human_detection_history) >= 3:
                required_detections = 3 if self.strict_detection else 2
                final_result = sum(self.human_detection_history) >= required_detections
                if len(self.human_detection_history) % 30 == 0:
                    print(
                        f"🔍 Detection: {len(faces)} faces found, history: {sum(self.human_detection_history)}/{len(self.human_detection_history)}, result: {final_result}"
                    )
                return final_result

            if len(self.human_detection_history) % 20 == 0:
                print(
                    f"🔍 Detection: {len(faces)} faces found, current: {human_detected}"
                )
            return human_detected

        except Exception as e:
            print(f"⚠️ Error in human detection: {e}")
            return True

    def _check_detection_instability(self):
        if not self.auto_strict_detection or len(self.human_detection_history) < 10:
            return
        changes = 0
        for i in range(1, len(self.human_detection_history)):
            if self.human_detection_history[i] != self.human_detection_history[i - 1]:
                changes += 1
        if changes >= self.instability_threshold and not self.strict_detection:
            self.strict_detection = True
            print(
                f"🔧 Auto-switched to Strict Detection due to instability ({changes} changes in {len(self.human_detection_history)} readings)"
            )
            self.detection_instability_count = 0
        self.detection_instability_count = changes

    def _calculate_adaptive_grace_period(self) -> float:
        if not self.adaptive_grace_period or len(self.face_loss_durations) < 3:
            return self.grace_period_duration
        recent_durations = self.face_loss_durations[-self.adaptive_history_size :]
        median_duration = sorted(recent_durations)[len(recent_durations) // 2]
        adaptive_duration = median_duration * 1.2
        adaptive_duration = max(
            self.min_grace_period, min(self.max_grace_period, adaptive_duration)
        )
        adaptive_duration = round(adaptive_duration * 2) / 2
        return adaptive_duration

    def _update_face_loss_patterns(self, duration: float):
        if duration > 0:
            self.face_loss_durations.append(duration)
            if len(self.face_loss_durations) > self.adaptive_history_size:
                self.face_loss_durations.pop(0)
            if len(self.face_loss_durations) % 3 == 0:
                avg_duration = sum(self.face_loss_durations) / len(
                    self.face_loss_durations
                )
                adaptive_duration = self._calculate_adaptive_grace_period()
                print(
                    f"📊 Face loss pattern: avg={avg_duration:.1f}s, adaptive grace={adaptive_duration:.1f}s"
                )

    def get_detection_status(self) -> dict:
        if len(self.human_detection_history) < 5:
            return {
                "strict_mode": self.strict_detection,
                "auto_switched": False,
                "instability_count": 0,
                "stability_percentage": 0,
                "auto_strict_enabled": self.auto_strict_detection,
                "grace_period_active": self.grace_period_active,
                "grace_period_enabled": self.grace_period_enabled,
            }
        changes = 0
        for i in range(1, len(self.human_detection_history)):
            if self.human_detection_history[i] != self.human_detection_history[i - 1]:
                changes += 1
        stability_percentage = (
            (len(self.human_detection_history) - changes)
            / len(self.human_detection_history)
        ) * 100
        return {
            "strict_mode": self.strict_detection,
            "auto_switched": self.detection_instability_count
            >= self.instability_threshold,
            "instability_count": self.detection_instability_count,
            "stability_percentage": stability_percentage,
            "auto_strict_enabled": self.auto_strict_detection,
            "grace_period_active": self.grace_period_active,
            "grace_period_enabled": self.grace_period_enabled,
            "adaptive_grace_period": self.adaptive_grace_period,
            "current_grace_duration": self._calculate_adaptive_grace_period(),
            "face_loss_count": len(self.face_loss_durations),
        }

    def update_auto_strict_setting(self, enabled: bool):
        self.auto_strict_detection = enabled
        if enabled:
            print("🔧 Auto-strict detection enabled")
        else:
            print("🔧 Auto-strict detection disabled")

    def update_grace_period_setting(self, enabled: bool, duration: float = None):
        self.grace_period_enabled = enabled
        if duration is not None:
            self.grace_period_duration = duration
        if enabled:
            print(f"⏰ Grace period enabled ({self.grace_period_duration}s)")
        else:
            print("⏰ Grace period disabled")

    def update_adaptive_grace_period_setting(self, enabled: bool):
        self.adaptive_grace_period = enabled
        if enabled:
            print("🧠 Adaptive grace period enabled")
        else:
            print("🧠 Adaptive grace period disabled")

    def start_calibration(self):
        self.calibration_mode = True
        self.calibration_samples = []
        print(
            "🎯 Calibration mode started. Position yourself at different distances from the camera."
        )

    def stop_calibration(self):
        import numpy as np

        if len(self.calibration_samples) < 5:
            print("⚠️ Not enough calibration samples. Need at least 5 samples.")
            return False
        face_sizes = [sample["face_percentage"] for sample in self.calibration_samples]
        face_sizes.sort()
        primary_user_min = np.percentile(face_sizes, 20)
        primary_user_max = np.percentile(face_sizes, 80)
        distant_person_min = np.percentile(face_sizes, 5)
        self.calibrated_thresholds = {
            "primary_user_min": max(0.015, min(0.05, primary_user_min)),
            "primary_user_max": max(0.1, min(0.2, primary_user_max)),
            "distant_person_min": max(0.005, min(0.02, distant_person_min)),
            "distant_person_max": max(0.015, min(0.05, primary_user_min * 0.8)),
        }
        self.calibration_mode = False
        print(f"✅ Calibration complete! New thresholds: {self.calibrated_thresholds}")
        return True

    def add_calibration_sample(self, face_percentage: float, distance_type: str):
        import time

        if self.calibration_mode:
            self.calibration_samples.append(
                {
                    "face_percentage": face_percentage,
                    "distance_type": distance_type,
                    "timestamp": time.time(),
                }
            )
            print(
                f"📊 Calibration sample added: {face_percentage:.3f} ({distance_type})"
            )

    def get_detection_info(self, frame) -> dict:
        import cv2
        import numpy as np

        if not self.enable_human_detection or self.face_cascade is None:
            return {
                "faces_detected": 0,
                "primary_user_detected": False,
                "distant_person_detected": False,
                "largest_face_percentage": 0.0,
                "face_details": [],
            }
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if self.strict_detection:
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.2, minNeighbors=12, minSize=(60, 60)
                )
            else:
                faces = self.face_cascade.detectMultiScale(
                    gray, scaleFactor=1.15, minNeighbors=8, minSize=(50, 50)
                )
            face_details = []
            frame_area = frame.shape[0] * frame.shape[1]
            primary_user_detected = False
            distant_person_detected = False
            largest_face_percentage = 0.0
            for x, y, w, h in faces:
                face_area = w * h
                face_percentage = face_area / frame_area
                largest_face_percentage = max(largest_face_percentage, face_percentage)
                face_type = "none"
                if self.enable_distance_detection:
                    if (
                        face_percentage
                        >= self.calibrated_thresholds["primary_user_min"]
                    ):
                        face_type = "primary_user"
                        primary_user_detected = True
                    elif (
                        face_percentage
                        >= self.calibrated_thresholds["distant_person_min"]
                    ):
                        face_type = "distant_person"
                        distant_person_detected = True
                else:
                    min_threshold = 0.015 if self.strict_detection else 0.01
                    if face_percentage >= min_threshold:
                        face_type = "detected"
                        primary_user_detected = True
                face_details.append(
                    {
                        "x": x,
                        "y": y,
                        "w": w,
                        "h": h,
                        "face_percentage": face_percentage,
                        "face_type": face_type,
                    }
                )
            return {
                "faces_detected": len(faces),
                "primary_user_detected": primary_user_detected,
                "distant_person_detected": distant_person_detected,
                "largest_face_percentage": largest_face_percentage,
                "face_details": face_details,
                "calibration_mode": self.calibration_mode,
                "thresholds": self.calibrated_thresholds,
            }
        except Exception as e:
            print(f"⚠️ Error in detection info: {e}")
            return {
                "faces_detected": 0,
                "primary_user_detected": False,
                "distant_person_detected": False,
                "largest_face_percentage": 0.0,
                "face_details": [],
            }
