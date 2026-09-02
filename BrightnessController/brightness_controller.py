"""
Brightness Controller module for managing screen brightness based on camera or screen content.
"""

import time
import cv2
import numpy as np
import screen_brightness_control as sbc
from typing import List, Optional, Tuple
import os

from desk_presence import DeskPresenceConfig, DeskPresenceTracker, PresenceState
from face_detector_backend import FaceDetectorBackend


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
        strict_detection: bool = False,
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
            strict_detection: Whether to use strict detection parameters (default: False)
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

        self.look_away_floor = 20
        self.brightness_restore_seconds = 3.0
        self.desk_presence = DeskPresenceTracker(DeskPresenceConfig())
        self.last_presence_state = PresenceState.ACTIVE
        self.last_ambient_brightness = 128.0
        self._active_since: Optional[float] = None
        self._holding_look_away_floor = False
        self._last_look_away_log = 0.0

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

        # Suppress OpenCV warnings during camera setup
        original_log_level = None
        try:
            original_log_level = cv2.getLogLevel()
            cv2.setLogLevel(cv2.LOG_LEVEL_ERROR)  # Only show errors, suppress warnings
        except (AttributeError, cv2.error):
            # OpenCV version doesn't support log level control, continue without suppression
            pass
            
            self.cap = cv2.VideoCapture(self.camera_index, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(self.camera_index)
                if not self.cap.isOpened():
                    raise RuntimeError(f"Could not open camera {self.camera_index}")

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
        finally:
            # Restore original log level
            if original_log_level is not None:
                try:
                    cv2.setLogLevel(original_log_level)
                except (AttributeError, cv2.error):
                    pass

    def get_brightness_from_camera(self) -> Tuple[float, PresenceState]:
        """
        Capture brightness from camera and evaluate desk presence.

        Returns:
            Tuple of (ambient brightness 0-255, presence state)
        """
        if self.cap is None or not self.cap.isOpened():
            self.setup_camera()

        ret, frame = self.cap.read()
        if not ret:
            raise RuntimeError("Failed to capture frame")

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ambient = float(np.mean(gray))
        self.last_ambient_brightness = ambient

        if not self.enable_human_detection:
            self.last_presence_state = PresenceState.ACTIVE
            return ambient, PresenceState.ACTIVE

        face_detected = self.human_detector.detect_face_only(frame)
        self.last_presence_state = self.desk_presence.update(frame, face_detected)
        return ambient, self.last_presence_state

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

    def adjust_screen_brightness(
        self, brightness: float, presence_state: Optional[PresenceState] = None
    ) -> None:
        """
        Adjust screen brightness based on input value and presence state.

        Args:
            brightness: Raw ambient brightness value (0-255)
            presence_state: Desk presence state when human detection is enabled
        """
        state = presence_state or self.last_presence_state
        now = time.time()

        if self.enable_human_detection and state == PresenceState.AWAY:
            self._active_since = None
            self._holding_look_away_floor = False
            if self.current_brightness != 0:
                print("🚪 Away — setting brightness to 0%")
                try:
                    sbc.set_brightness(0)
                    self.current_brightness = 0
                    self.last_set = 0
                except Exception as e:
                    print(f"❌ Error setting brightness to 0: {e}")
            return

        if self.enable_human_detection and state == PresenceState.LOOK_AWAY:
            self._active_since = None
            target = max(1, min(100, int(self.look_away_floor)))
            if abs(self.current_brightness - target) > 3:
                # Rate-limit log spam during flaps
                if now - self._last_look_away_log > 2.0:
                    print(f"👀 Look away — holding brightness at {target}% floor")
                    self._last_look_away_log = now
                try:
                    self.smooth_transition(self.current_brightness, target)
                    self.current_brightness = target
                    self.last_set = target
                    self._holding_look_away_floor = True
                except Exception as e:
                    print(f"❌ Error setting look-away floor: {e}")
            else:
                self._holding_look_away_floor = True
            return

        # ACTIVE: require sustained Active before leaving the look-away floor
        if self.enable_human_detection and self._holding_look_away_floor:
            if self._active_since is None:
                self._active_since = now
            restore_hold = max(
                self.brightness_restore_seconds,
                self.desk_presence.config.enter_active_seconds,
            )
            if (now - self._active_since) < restore_hold:
                return
            self._holding_look_away_floor = False
            self._active_since = None
            print("👤 Active confirmed — restoring ambient brightness")
        else:
            self._active_since = now if self.enable_human_detection else None

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

    def update_desk_mode_settings(
        self,
        enabled: Optional[bool] = None,
        use_motion: Optional[bool] = None,
        use_input_activity: Optional[bool] = None,
        last_seen_window_seconds: Optional[float] = None,
        away_timeout_seconds: Optional[float] = None,
        look_away_floor: Optional[int] = None,
        leave_active_seconds: Optional[float] = None,
        enter_active_seconds: Optional[float] = None,
        input_window_seconds: Optional[float] = None,
        brightness_restore_seconds: Optional[float] = None,
    ) -> None:
        """Sync desk-mode and softened away settings from the GUI."""
        if look_away_floor is not None:
            self.look_away_floor = max(5, min(60, int(look_away_floor)))
        if brightness_restore_seconds is not None:
            self.brightness_restore_seconds = max(
                0.5, min(15.0, float(brightness_restore_seconds))
            )
        self.desk_presence.update_config(
            enabled=enabled,
            use_motion=use_motion,
            use_input_activity=use_input_activity,
            last_seen_window_seconds=last_seen_window_seconds,
            away_timeout_seconds=away_timeout_seconds,
            leave_active_seconds=leave_active_seconds,
            enter_active_seconds=enter_active_seconds,
            input_window_seconds=input_window_seconds,
        )

    def get_presence_status(self) -> dict:
        """Return combined face + desk presence status for the UI."""
        status = self.desk_presence.get_status()
        status["look_away_floor"] = self.look_away_floor
        if self.enable_human_detection:
            status.update(self.human_detector.get_detection_status())
        return status

    def update_auto_strict_setting(self, enabled: bool) -> None:
        self.human_detector.update_auto_strict_setting(enabled)

    def update_grace_period_setting(self, enabled: bool, duration: float = None) -> None:
        self.human_detector.update_grace_period_setting(enabled, duration)

    def update_adaptive_grace_period_setting(self, enabled: bool) -> None:
        self.human_detector.update_adaptive_grace_period_setting(enabled)

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
        self._face_backend: Optional[FaceDetectorBackend] = None

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

    @property
    def face_cascade(self) -> Optional[cv2.CascadeClassifier]:
        """Haar cascade when Haar fallback is active (None for YuNet)."""
        if self._face_backend is None:
            return None
        return self._face_backend.face_cascade

    @property
    def profile_cascade(self) -> Optional[cv2.CascadeClassifier]:
        """Profile Haar cascade when Haar fallback is active."""
        if self._face_backend is None:
            return None
        return self._face_backend.profile_cascade

    @property
    def face_detector_ready(self) -> bool:
        return self._face_backend is not None and self._face_backend.is_ready

    def _setup_face_detection(self) -> None:
        """Initialize YuNet face detector with Haar cascade fallback."""
        try:
            auto_download = os.environ.get("BRIGHTNESS_NO_MODEL_DOWNLOAD", "") != "1"
            self._face_backend = FaceDetectorBackend(auto_download=auto_download)
            if not self._face_backend.setup():
                print(
                    "⚠️ Warning: Could not load face detection model. Human detection will be disabled."
                )
                self.enable_human_detection = False
        except Exception as e:
            print(
                f"⚠️ Warning: Error loading face detection model: {e}. Human detection will be disabled."
            )
            self.enable_human_detection = False

    def _validation_thresholds(self, *, desk_mode: bool = False) -> dict:
        if desk_mode:
            return {
                "brightness_min": 25,
                "brightness_max": 230,
                "aspect_min": 0.45,
                "aspect_max": 1.5,
                "min_face_percentage": 0.008,
            }
        if self.strict_detection:
            return {
                "brightness_min": 40,
                "brightness_max": 200,
                "aspect_min": 0.8,
                "aspect_max": 1.3,
                "min_face_percentage": 0.015,
            }
        return {
            "brightness_min": 30,
            "brightness_max": 220,
            "aspect_min": 0.7,
            "aspect_max": 1.5,
            "min_face_percentage": 0.01,
        }

    def _detect_face_rects(self, frame, *, desk_mode: bool = False):
        """Run YuNet or Haar detection and return bounding boxes."""
        if not self.face_detector_ready:
            return []
        return self._face_backend.detect_rects(
            frame,
            desk_mode=desk_mode,
            strict_detection=self.strict_detection,
        )

    def _validate_face_rect(
        self, gray, frame, x: int, y: int, w: int, h: int, *, desk_mode: bool = False
    ) -> bool:
        thresholds = self._validation_thresholds(desk_mode=desk_mode)
        face_brightness = float(np.mean(gray[y : y + h, x : x + w]))
        if not (
            thresholds["brightness_min"]
            < face_brightness
            < thresholds["brightness_max"]
        ):
            return False

        aspect_ratio = w / h
        if not (
            thresholds["aspect_min"] < aspect_ratio < thresholds["aspect_max"]
        ):
            return False

        frame_area = frame.shape[0] * frame.shape[1]
        face_percentage = (w * h) / frame_area
        if self.enable_distance_detection:
            return face_percentage >= self.calibrated_thresholds["primary_user_min"]
        return face_percentage >= thresholds["min_face_percentage"]

    def detect_face_only(self, frame) -> bool:
        """Return whether a face is visible this frame (no history voting)."""
        if not self.enable_human_detection or not self.face_detector_ready:
            return True
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rects = self._detect_face_rects(frame, desk_mode=True)
            if not rects:
                return False

            largest = max(rects, key=lambda r: r[2] * r[3])
            x, y, w, h = largest
            return self._validate_face_rect(gray, frame, x, y, w, h, desk_mode=True)
        except Exception:
            return True

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

        if not self.enable_human_detection or not self.face_detector_ready:
            return True  # If detection is disabled, assume human is present

        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rects = self._detect_face_rects(frame, desk_mode=False)
            faces = rects

            human_detected = False
            primary_user_detected = False
            distant_person_detected = False

            if len(rects) > 0:
                largest_face = max(rects, key=lambda x: x[2] * x[3])
                x, y, w, h = largest_face
                if self._validate_face_rect(gray, frame, x, y, w, h, desk_mode=False):
                    human_detected = True
                    primary_user_detected = True
                    frame_area = frame.shape[0] * frame.shape[1]
                    face_percentage = (w * h) / frame_area
                    if self.enable_distance_detection:
                        if (
                            face_percentage
                            < self.calibrated_thresholds["primary_user_min"]
                        ):
                            human_detected = False
                            primary_user_detected = False
                            if (
                                face_percentage
                                >= self.calibrated_thresholds["distant_person_min"]
                            ):
                                distant_person_detected = True

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
        backend = (
            self._face_backend.backend_name if self._face_backend is not None else None
        )
        if len(self.human_detection_history) < 5:
            return {
                "strict_mode": self.strict_detection,
                "auto_switched": False,
                "instability_count": 0,
                "stability_percentage": 0,
                "auto_strict_enabled": self.auto_strict_detection,
                "grace_period_active": self.grace_period_active,
                "grace_period_enabled": self.grace_period_enabled,
                "face_backend": backend,
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
            "face_backend": backend,
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

        if not self.enable_human_detection or not self.face_detector_ready:
            return {
                "faces_detected": 0,
                "primary_user_detected": False,
                "distant_person_detected": False,
                "largest_face_percentage": 0.0,
                "face_details": [],
            }
        try:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            rects = self._detect_face_rects(frame, desk_mode=False)
            thresholds = self._validation_thresholds(desk_mode=False)
            face_details = []
            frame_area = frame.shape[0] * frame.shape[1]
            primary_user_detected = False
            distant_person_detected = False
            largest_face_percentage = 0.0
            for x, y, w, h in rects:
                face_area = w * h
                face_percentage = face_area / frame_area
                largest_face_percentage = max(largest_face_percentage, face_percentage)
                face_type = "none"
                if self._validate_face_rect(gray, frame, x, y, w, h, desk_mode=False):
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
                    elif face_percentage >= thresholds["min_face_percentage"]:
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
                "faces_detected": len(rects),
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
