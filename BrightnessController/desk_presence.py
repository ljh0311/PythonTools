"""
Desk-mode presence: face, motion, input activity, and hysteretic state machine.

Uses asymmetric dwell (industry presence pattern): stay Active until signals are
gone for a sustained period; only return to Active after a strong signal is
confirmed. Prevents Active ↔ Look-away flapping.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import cv2
import numpy as np


class PresenceState(str, Enum):
    ACTIVE = "active"
    LOOK_AWAY = "look_away"
    AWAY = "away"


@dataclass
class DeskPresenceConfig:
    enabled: bool = True
    use_motion: bool = True
    use_input_activity: bool = True
    motion_threshold: float = 8.0
    motion_window_seconds: float = 8.0
    input_window_seconds: float = 60.0
    last_seen_window_seconds: float = 180.0
    away_timeout_seconds: float = 45.0
    # Hysteresis: all signals absent this long before Active → Look-away
    leave_active_seconds: float = 45.0
    # Hysteresis: strong signal (face/input) must hold before Look-away → Active
    enter_active_seconds: float = 2.5
    # Motion alone needs a longer confirm to upgrade Look-away → Active
    enter_active_motion_seconds: float = 6.0


def get_input_idle_seconds() -> Optional[float]:
    """Return seconds since last keyboard/mouse input (Windows only)."""
    if sys.platform != "win32":
        return None
    try:
        import ctypes

        class LASTINPUTINFO(ctypes.Structure):
            _fields_ = [("cbSize", ctypes.c_uint), ("dwTime", ctypes.c_uint)]

        lii = LASTINPUTINFO()
        lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
        if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii)):
            return None
        tick = ctypes.windll.kernel32.GetTickCount()
        idle_ms = tick - lii.dwTime
        return max(0.0, idle_ms / 1000.0)
    except Exception:
        return None


class DeskPresenceTracker:
    """Combines face, motion, and input signals with anti-flap hysteresis."""

    def __init__(self, config: Optional[DeskPresenceConfig] = None):
        self.config = config or DeskPresenceConfig()
        self._prev_gray: Optional[np.ndarray] = None
        self.last_face_time: Optional[float] = None
        self.last_motion_time: Optional[float] = None
        self.last_input_time: Optional[float] = None
        self.state = PresenceState.ACTIVE
        self.last_signal_source = "startup"
        self._quiet_since: Optional[float] = None
        self._strong_since: Optional[float] = None
        self._motion_only_since: Optional[float] = None
        self._state_changed_at = time.time()

    def update_config(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if value is not None and hasattr(self.config, key):
                setattr(self.config, key, value)

    def _set_state(self, state: PresenceState, source: str, now: float) -> PresenceState:
        if state != self.state:
            self.state = state
            self._state_changed_at = now
            self._quiet_since = None
            self._strong_since = None
            self._motion_only_since = None
        self.last_signal_source = source
        return self.state

    def _detect_motion(self, frame: np.ndarray, now: float) -> bool:
        if not self.config.use_motion:
            return False
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray, (21, 21), 0)
        motion = False
        if self._prev_gray is not None:
            diff = cv2.absdiff(self._prev_gray, gray)
            score = float(np.mean(diff))
            if score >= self.config.motion_threshold:
                motion = True
                self.last_motion_time = now
        self._prev_gray = gray
        return motion

    def _input_within_window(self, now: float) -> bool:
        """True while keyboard/mouse activity is within the input window."""
        if not self.config.use_input_activity:
            return False
        idle = get_input_idle_seconds()
        if idle is not None and idle <= self.config.input_window_seconds:
            self.last_input_time = now - idle
            return True
        if (
            self.last_input_time
            and (now - self.last_input_time) <= self.config.input_window_seconds
        ):
            return True
        return False

    def _input_recent(self, now: float) -> bool:
        return self._input_within_window(now)

    def _last_signal_time(self) -> Optional[float]:
        times = [
            t
            for t in (self.last_face_time, self.last_motion_time, self.last_input_time)
            if t
        ]
        return max(times) if times else None

    def _any_recent(
        self, face_now: bool, motion_now: bool, input_now: bool, now: float
    ) -> bool:
        """Any presence signal still active — resets the leave-active timer."""
        if input_now:
            return True
        if face_now or motion_now:
            return True
        if (
            self.last_motion_time
            and (now - self.last_motion_time) <= self.config.motion_window_seconds
        ):
            return True
        if self._input_within_window(now):
            return True
        return False

    def _all_signals_absent(
        self, face_now: bool, motion_now: bool, input_now: bool, now: float
    ) -> bool:
        """True only when face, motion, and input are all gone (incl. linger windows)."""
        return not self._any_recent(face_now, motion_now, input_now, now)

    def _strong_recent(self, face_now: bool, input_now: bool, now: float) -> bool:
        """Face/input — used to confirm Look-away → Active (not brief motion)."""
        if face_now or input_now or self._input_within_window(now):
            return True
        # Tiny face linger so one missed frame does not reset confirm timer
        if self.last_face_time and (now - self.last_face_time) <= 0.4:
            return True
        return False

    def update(self, frame: np.ndarray, face_detected: bool) -> PresenceState:
        now = time.time()
        if face_detected:
            self.last_face_time = now

        motion_now = self._detect_motion(frame, now)
        input_now = self._input_recent(now)
        any_recent = self._any_recent(face_detected, motion_now, input_now, now)
        strong = self._strong_recent(face_detected, input_now, now)
        motion_only = any_recent and not strong

        if not self.config.enabled:
            return self._update_face_only(face_detected, now)

        last_signal = self._last_signal_time()
        elapsed = (now - last_signal) if last_signal else 0.0

        if self.state == PresenceState.ACTIVE:
            # Hard rule: recent input always keeps Active (even without face/motion)
            if input_now or self._input_within_window(now):
                self._quiet_since = None
                return self._set_state(PresenceState.ACTIVE, "input", now)

            if any_recent:
                self._quiet_since = None
                source = "face" if face_detected else "motion"
                return self._set_state(PresenceState.ACTIVE, source, now)

            if not self._all_signals_absent(face_detected, motion_now, input_now, now):
                self._quiet_since = None
                return self._set_state(PresenceState.ACTIVE, "active_hold", now)

            if self._quiet_since is None:
                self._quiet_since = now
            quiet_for = now - self._quiet_since
            if quiet_for >= self.config.leave_active_seconds:
                return self._set_state(PresenceState.LOOK_AWAY, "look_away", now)
            return self._set_state(PresenceState.ACTIVE, "active_hold", now)

        if self.state == PresenceState.LOOK_AWAY:
            if strong:
                if self._strong_since is None:
                    self._strong_since = now
                self._motion_only_since = None
                if (now - self._strong_since) >= self.config.enter_active_seconds:
                    source = "face" if face_detected else "input"
                    return self._set_state(PresenceState.ACTIVE, source, now)
                return self._set_state(
                    PresenceState.LOOK_AWAY, "confirming_active", now
                )

            if motion_only:
                self._strong_since = None
                if self._motion_only_since is None:
                    self._motion_only_since = now
                if (
                    now - self._motion_only_since
                ) >= self.config.enter_active_motion_seconds:
                    return self._set_state(PresenceState.ACTIVE, "motion", now)
                return self._set_state(
                    PresenceState.LOOK_AWAY, "confirming_motion", now
                )

            self._strong_since = None
            self._motion_only_since = None

            if elapsed > self.config.last_seen_window_seconds:
                return self._set_state(PresenceState.AWAY, "none", now)
            return self._set_state(PresenceState.LOOK_AWAY, "last_seen", now)

        # AWAY
        if strong:
            if self._strong_since is None:
                self._strong_since = now
            if (now - self._strong_since) >= self.config.enter_active_seconds:
                source = "face" if face_detected else "input"
                return self._set_state(PresenceState.ACTIVE, source, now)
            return self._set_state(PresenceState.AWAY, "confirming_return", now)

        self._strong_since = None
        return self._set_state(PresenceState.AWAY, "none", now)

    def _update_face_only(self, face_detected: bool, now: float) -> PresenceState:
        if face_detected:
            return self._set_state(PresenceState.ACTIVE, "face", now)

        last = self.last_face_time
        if last is None:
            return self._set_state(PresenceState.ACTIVE, "startup", now)

        elapsed = now - last
        if elapsed < self.config.leave_active_seconds:
            return self._set_state(PresenceState.ACTIVE, "active_hold", now)
        if elapsed < self.config.last_seen_window_seconds:
            return self._set_state(PresenceState.LOOK_AWAY, "face_grace", now)
        return self._set_state(PresenceState.AWAY, "none", now)

    def get_status(self) -> dict:
        now = time.time()
        last_signal = self._last_signal_time()
        elapsed = (now - last_signal) if last_signal else None
        return {
            "desk_mode": self.config.enabled,
            "state": self.state.value,
            "source": self.last_signal_source,
            "seconds_since_signal": elapsed,
            "seconds_in_state": now - self._state_changed_at,
            "leave_active_seconds": self.config.leave_active_seconds,
            "enter_active_seconds": self.config.enter_active_seconds,
            "last_seen_window": self.config.last_seen_window_seconds,
            "away_timeout": self.config.away_timeout_seconds,
            "input_available": get_input_idle_seconds() is not None,
        }
