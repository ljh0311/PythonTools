"""
Unit tests for processing_profiles (no hardware required).
"""

from __future__ import annotations

import os
import sys
import unittest
from unittest import mock

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from processing_profiles import (  # noqa: E402
    BALANCED, PERFORMANCE, QUALITY, RPI,
    get_default_profile_name, get_profile, list_profile_names,
)


class ProfileLookupTests(unittest.TestCase):
    def test_known_profiles_returned_by_name(self):
        self.assertEqual(get_profile("quality"), QUALITY)
        self.assertEqual(get_profile("balanced"), BALANCED)
        self.assertEqual(get_profile("performance"), PERFORMANCE)
        self.assertEqual(get_profile("rpi"), RPI)

    def test_unknown_profile_falls_back_to_default(self):
        self.assertIn(
            get_profile("definitely_unknown"),
            (BALANCED, RPI),
        )

    def test_auto_resolves_to_default(self):
        result = get_profile("auto")
        self.assertIn(result, (BALANCED, RPI))

    def test_list_profile_names_contains_all(self):
        names = list_profile_names()
        for expected in ("quality", "balanced", "performance", "rpi"):
            self.assertIn(expected, names)


class DefaultProfileTests(unittest.TestCase):
    @mock.patch("processing_profiles.is_raspberry_pi", create=True)
    def test_default_falls_back_to_balanced_on_desktop(self, _mock):
        with mock.patch("camera_service.is_raspberry_pi", return_value=False):
            self.assertEqual(get_default_profile_name(), "balanced")

    def test_default_uses_rpi_on_raspberry_pi(self):
        with mock.patch("camera_service.is_raspberry_pi", return_value=True):
            self.assertEqual(get_default_profile_name(), "rpi")


class ProfileShapeTests(unittest.TestCase):
    """Sanity checks on knob ranges so we can't regress them silently."""

    def test_quality_disables_frame_skip(self):
        self.assertEqual(QUALITY.preview_frame_skip, 0)
        self.assertTrue(QUALITY.enable_object_in_preview)

    def test_rpi_uses_smaller_preview_than_quality(self):
        rw, rh = RPI.detection_preview_size
        qw, qh = QUALITY.detection_preview_size
        self.assertLess(rw * rh, qw * qh)

    def test_recommended_fps_is_positive(self):
        for profile in (QUALITY, BALANCED, PERFORMANCE, RPI):
            self.assertGreater(profile.recommended_max_fps, 0)


if __name__ == "__main__":
    unittest.main()
