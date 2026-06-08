"""
Unit tests for SmartCam pure-logic concerns.

These tests deliberately avoid touching hardware (no real camera) by
constructing `SmartCamera` instances with `__new__` and assigning only the
attributes each method under test depends on.
"""

from __future__ import annotations

import os
import sys
import time
import types
import unittest
from typing import Any, Dict, List, Optional

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from main import SmartCamera  # noqa: E402


def make_camera() -> SmartCamera:
    """Build a SmartCamera without running its hardware-touching __init__."""
    cam = SmartCamera.__new__(SmartCamera)
    cam.ai_capture_settings = {
        'auto_capture_enabled': True,
        'capture_cooldown_seconds': 5,
        'face_capture_threshold': 0.6,
        'object_capture_threshold': 0.7,
        'motion_capture_threshold': 0.5,
        'max_captures_per_minute': 12,
        'capture_sequence_count': 1,
        'capture_sequence_interval': 0.5,
        'save_detection_overlay': True,
        'event_classification': True,
    }
    cam.last_capture_time = 0.0
    cam.capture_count_this_minute = 0
    cam.minute_start_time = time.time()
    cam.recent_captures = []
    cam.max_recent_captures = 8
    return cam


class DuplicateGuardTests(unittest.TestCase):
    """Verify `_is_duplicate_capture` initializes and behaves correctly."""

    def test_first_capture_is_not_duplicate(self):
        cam = make_camera()
        detections = {
            'faces': [{'bbox': (0, 0, 10, 10), 'confidence': 0.9}],
            'objects': [{'class_name': 'person', 'confidence': 0.95}],
            'motion': True,
            'scene': {'location': 'indoor'},
        }
        self.assertFalse(cam._is_duplicate_capture(detections))
        self.assertEqual(len(cam.recent_captures), 1)

    def test_identical_detections_are_treated_as_duplicate(self):
        cam = make_camera()
        detections = {
            'faces': [{'bbox': (0, 0, 10, 10), 'confidence': 0.9}],
            'objects': [{'class_name': 'person', 'confidence': 0.95}],
            'motion': True,
            'scene': {'location': 'indoor'},
        }
        cam._is_duplicate_capture(detections)
        self.assertTrue(cam._is_duplicate_capture(detections))

    def test_different_detections_are_not_duplicates(self):
        cam = make_camera()
        first = {
            'faces': [{'bbox': (0, 0, 10, 10), 'confidence': 0.9}],
            'objects': [{'class_name': 'person', 'confidence': 0.95}],
            'motion': True,
            'scene': {'location': 'indoor'},
        }
        second = {
            'faces': [],
            'objects': [{'class_name': 'cat', 'confidence': 0.95}],
            'motion': True,
            'scene': {'location': 'outdoor'},
        }
        cam._is_duplicate_capture(first)
        self.assertFalse(cam._is_duplicate_capture(second))
        self.assertEqual(len(cam.recent_captures), 2)

    def test_recent_captures_buffer_is_bounded(self):
        cam = make_camera()
        cam.max_recent_captures = 3
        for i in range(10):
            detections = {
                'faces': [],
                'objects': [{'class_name': f'class_{i}', 'confidence': 0.9}],
                'motion': False,
                'scene': {'location': 'indoor'},
            }
            cam._is_duplicate_capture(detections)
        self.assertLessEqual(len(cam.recent_captures), cam.max_recent_captures)


class CapturePolicyTests(unittest.TestCase):
    """Verify `_is_significant_event` cooldown, rate-limit, and anomaly bypass."""

    def test_anomaly_bypasses_cooldown(self):
        cam = make_camera()
        cam.last_capture_time = time.time()  # cooldown active
        cam.capture_count_this_minute = cam.ai_capture_settings['max_captures_per_minute']
        detections = {'anomaly_detected': True}
        self.assertTrue(cam._is_significant_event(detections))

    def test_disabled_auto_capture_returns_false(self):
        cam = make_camera()
        cam.ai_capture_settings['auto_capture_enabled'] = False
        detections = {
            'faces': [{'confidence': 1.0}],
            'objects': [{'confidence': 1.0}],
            'motion': True,
        }
        self.assertFalse(cam._is_significant_event(detections))

    def test_rate_limit_blocks_capture(self):
        cam = make_camera()
        cam.capture_count_this_minute = cam.ai_capture_settings['max_captures_per_minute']
        cam.minute_start_time = time.time()  # current minute
        cam.last_capture_time = 0  # cooldown elapsed
        detections = {'faces': [{'confidence': 0.99}]}
        self.assertFalse(cam._is_significant_event(detections))

    def test_cooldown_blocks_capture(self):
        cam = make_camera()
        cam.last_capture_time = time.time()  # just captured
        cam.capture_count_this_minute = 0
        detections = {'faces': [{'confidence': 0.99}]}
        self.assertFalse(cam._is_significant_event(detections))

    def test_face_threshold_triggers_capture(self):
        cam = make_camera()
        cam.last_capture_time = 0
        cam.capture_count_this_minute = 0
        detections = {'faces': [{'confidence': 0.99}]}
        self.assertTrue(cam._is_significant_event(detections))

    def test_low_face_confidence_does_not_trigger(self):
        cam = make_camera()
        cam.last_capture_time = 0
        cam.capture_count_this_minute = 0
        detections = {'faces': [{'confidence': 0.1}]}
        self.assertFalse(cam._is_significant_event(detections))

    def test_object_threshold_triggers_capture(self):
        cam = make_camera()
        cam.last_capture_time = 0
        cam.capture_count_this_minute = 0
        detections = {'objects': [{'confidence': 0.95}]}
        self.assertTrue(cam._is_significant_event(detections))

    def test_motion_strength_below_threshold_does_not_trigger(self):
        cam = make_camera()
        cam.last_capture_time = 0
        cam.capture_count_this_minute = 0
        detections = {'motion': True, 'motion_strength': 0.1}
        self.assertFalse(cam._is_significant_event(detections))


if __name__ == "__main__":
    unittest.main()
