"""
Headless smoke harness for desk presence + face detection (runbook terminal layer).
No GUI / no live camera required for synthetic cases; optional camera probe if present.
"""

from __future__ import annotations

import os
import sys
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple
from unittest.mock import patch

import cv2
import numpy as np

# Ensure package dir is importable when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from desk_presence import DeskPresenceConfig, DeskPresenceTracker, PresenceState
from brightness_controller import HumanDetector


@dataclass
class CaseResult:
    name: str
    passed: bool
    detail: str


def _blank_frame(h: int = 240, w: int = 320) -> np.ndarray:
    return np.zeros((h, w, 3), dtype=np.uint8)


def test_hysteresis_leave_and_enter() -> CaseResult:
    cfg = DeskPresenceConfig(
        enabled=True,
        leave_active_seconds=0.25,
        enter_active_seconds=0.2,
        enter_active_motion_seconds=0.5,
        last_seen_window_seconds=10.0,
        motion_window_seconds=0.05,
        use_input_activity=False,
        use_motion=True,
    )
    t = DeskPresenceTracker(cfg)
    frame = _blank_frame()

    if t.update(frame, True) != PresenceState.ACTIVE:
        return CaseResult("hysteresis_enter_face", False, f"expected ACTIVE got {t.state}")
    if t.update(frame, False) != PresenceState.ACTIVE:
        return CaseResult("hysteresis_hold", False, f"expected ACTIVE hold got {t.state}")

    time.sleep(0.3)
    if t.update(frame, False) != PresenceState.LOOK_AWAY:
        return CaseResult("hysteresis_leave", False, f"expected LOOK_AWAY got {t.state}")

    # Brief face must not flip immediately
    if t.update(frame, True) != PresenceState.LOOK_AWAY:
        return CaseResult("hysteresis_brief_face", False, f"expected LOOK_AWAY got {t.state}")

    time.sleep(0.25)
    if t.update(frame, True) != PresenceState.ACTIVE:
        return CaseResult("hysteresis_confirm", False, f"expected ACTIVE got {t.state}")

    return CaseResult("hysteresis_leave_and_enter", True, "leave/confirm dwell OK")


def test_motion_alone_needs_longer_confirm() -> CaseResult:
    cfg = DeskPresenceConfig(
        enabled=True,
        leave_active_seconds=0.15,
        enter_active_seconds=0.5,
        enter_active_motion_seconds=0.4,
        last_seen_window_seconds=10.0,
        motion_window_seconds=2.0,
        use_input_activity=False,
        use_motion=True,
        motion_threshold=1.0,
    )
    t = DeskPresenceTracker(cfg)
    a = _blank_frame()
    b = _blank_frame()
    b[40:80, 40:80] = 255  # force motion vs previous

    t.update(a, True)
    time.sleep(0.2)
    t.update(a, False)  # start quiet
    time.sleep(0.2)
    state = t.update(a, False)
    if state != PresenceState.LOOK_AWAY:
        return CaseResult("motion_confirm_setup", False, f"need LOOK_AWAY first, got {state}")

    # One motion frame should still be LOOK_AWAY (confirming)
    state = t.update(b, False)
    if state != PresenceState.LOOK_AWAY:
        return CaseResult(
            "motion_brief",
            False,
            f"brief motion should stay LOOK_AWAY, got {state} source={t.last_signal_source}",
        )

    deadline = time.time() + 1.0
    while time.time() < deadline:
        # Keep feeding alternating frames so motion continues
        state = t.update(a if int(time.time() * 10) % 2 == 0 else b, False)
        if state == PresenceState.ACTIVE and t.last_signal_source == "motion":
            return CaseResult("motion_alone_needs_longer_confirm", True, "motion upgrade OK")
        time.sleep(0.05)

    return CaseResult(
        "motion_alone_needs_longer_confirm",
        False,
        f"never upgraded via motion, state={t.state} source={t.last_signal_source}",
    )


def test_away_after_last_seen() -> CaseResult:
    cfg = DeskPresenceConfig(
        enabled=True,
        leave_active_seconds=0.1,
        enter_active_seconds=0.2,
        last_seen_window_seconds=0.35,
        motion_window_seconds=0.05,
        use_input_activity=False,
        use_motion=False,
    )
    frame = _blank_frame()
    clock = [1000.0]

    def fake_time() -> float:
        return clock[0]

    with patch("desk_presence.time.time", fake_time):
        t = DeskPresenceTracker(cfg)
        t.update(frame, True)
        clock[0] += 0.001
        t.update(frame, False)
        clock[0] += 0.11
        t.update(frame, False)
        if t.state != PresenceState.LOOK_AWAY:
            return CaseResult("away_setup", False, f"expected LOOK_AWAY got {t.state}")
        clock[0] += 0.4
        state = t.update(frame, False)
        if state != PresenceState.AWAY:
            return CaseResult("away_after_last_seen", False, f"expected AWAY got {state}")
    return CaseResult("away_after_last_seen", True, "last-seen → away OK")


def test_input_holds_active_without_face() -> CaseResult:
    cfg = DeskPresenceConfig(
        enabled=True,
        leave_active_seconds=0.5,
        input_window_seconds=5.0,
        use_input_activity=True,
        use_motion=False,
    )
    t = DeskPresenceTracker(cfg)
    frame = _blank_frame()

    with patch("desk_presence.get_input_idle_seconds", return_value=1.0):
        for _ in range(30):
            state = t.update(frame, False)
            if state == PresenceState.LOOK_AWAY:
                return CaseResult(
                    "input_holds_active",
                    False,
                    "recent input must never enter LOOK_AWAY",
                )

    return CaseResult(
        "input_holds_active_without_face",
        True,
        "mock input idle=1.0s stayed ACTIVE without face",
    )


def test_detector_loads() -> CaseResult:
    detector = HumanDetector(
        enable_human_detection=True,
        strict_detection=False,
        enable_distance_detection=False,
    )
    if not detector.face_detector_ready:
        return CaseResult("detector_loads", False, "no face detector backend ready")
    backend = (
        detector._face_backend.backend_name if detector._face_backend else "unknown"
    )
    profile_path = cv2.data.haarcascades + "haarcascade_profileface.xml"
    if backend == "haar":
        if not os.path.exists(profile_path):
            return CaseResult(
                "detector_loads", False, f"profile path missing: {profile_path}"
            )
        if (
            detector.profile_cascade is None
            or detector.profile_cascade.empty()
        ):
            return CaseResult("detector_loads", False, "profile cascade missing")
    ok = detector.detect_face_only(_blank_frame())
    return CaseResult(
        "detector_loads",
        True,
        f"backend={backend}, blank→{ok}",
    )


def probe_camera(max_index: int = 3) -> CaseResult:
    opened: List[int] = []
    for idx in range(max_index):
        cap = cv2.VideoCapture(idx, cv2.CAP_DSHOW)
        if not cap.isOpened():
            cap = cv2.VideoCapture(idx)
        if cap.isOpened():
            ret, frame = cap.read()
            cap.release()
            if ret and frame is not None:
                opened.append(idx)
        else:
            cap.release()
    if not opened:
        return CaseResult(
            "camera_probe",
            True,
            "SKIP: no camera readable (expected on headless/cloud)",
        )
    return CaseResult("camera_probe", True, f"readable cameras: {opened}")


def live_face_sample(seconds: float = 3.0, camera_index: int = 0) -> CaseResult:
    """Optional short live sample if a camera is available."""
    cap = cv2.VideoCapture(camera_index, cv2.CAP_DSHOW)
    if not cap.isOpened():
        cap = cv2.VideoCapture(camera_index)
    if not cap.isOpened():
        return CaseResult("live_face_sample", True, "SKIP: no camera")

    detector = HumanDetector(
        enable_human_detection=True,
        strict_detection=False,
        enable_distance_detection=False,
    )
    tracker = DeskPresenceTracker(
        DeskPresenceConfig(use_input_activity=False, leave_active_seconds=5.0)
    )

    hits = 0
    frames = 0
    states = {PresenceState.ACTIVE: 0, PresenceState.LOOK_AWAY: 0, PresenceState.AWAY: 0}
    end = time.time() + seconds
    while time.time() < end:
        ret, frame = cap.read()
        if not ret:
            break
        frames += 1
        face = detector.detect_face_only(frame)
        if face:
            hits += 1
        state = tracker.update(frame, face)
        states[state] += 1
        time.sleep(0.05)
    cap.release()

    if frames == 0:
        return CaseResult("live_face_sample", False, "camera opened but no frames")

    face_pct = 100.0 * hits / frames
    detail = (
        f"frames={frames} face={face_pct:.1f}% "
        f"active={states[PresenceState.ACTIVE]} "
        f"look_away={states[PresenceState.LOOK_AWAY]} "
        f"away={states[PresenceState.AWAY]}"
    )
    # Informational: pass if pipeline ran; face rate depends on user presence
    return CaseResult("live_face_sample", True, detail)


def main() -> int:
    print("=== Human detection smoke (runbook terminal) ===")
    results = [
        test_detector_loads(),
        test_hysteresis_leave_and_enter(),
        test_motion_alone_needs_longer_confirm(),
        test_away_after_last_seen(),
        test_input_holds_active_without_face(),
        probe_camera(),
        live_face_sample(3.0),
    ]
    failed = 0
    for r in results:
        mark = "PASS" if r.passed else "FAIL"
        if not r.passed:
            failed += 1
        print(f"[{mark}] {r.name}: {r.detail}")
    print(f"=== {len(results) - failed}/{len(results)} passed ===")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
