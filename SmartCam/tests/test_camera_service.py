"""
Unit tests for camera_service utilities (no hardware required).
"""

from __future__ import annotations

import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import cv2  # noqa: E402

from camera_service import (  # noqa: E402
    get_default_backend_preference,
    resolve_backend_preference,
)


class BackendPreferenceTests(unittest.TestCase):
    def test_auto_returns_non_empty_list(self):
        result = get_default_backend_preference()
        self.assertIsInstance(result, list)
        self.assertGreater(len(result), 0)
        for value in result:
            self.assertIsInstance(value, int)

    def test_resolve_auto_alias(self):
        self.assertEqual(
            resolve_backend_preference("auto"),
            get_default_backend_preference(),
        )

    def test_resolve_none_alias(self):
        self.assertEqual(
            resolve_backend_preference(None),
            get_default_backend_preference(),
        )

    def test_resolve_string_backend(self):
        result = resolve_backend_preference("CAP_ANY")
        self.assertIn(cv2.CAP_ANY, result)

    def test_resolve_unknown_string_falls_back_to_auto(self):
        result = resolve_backend_preference("CAP_DEFINITELY_NOT_REAL")
        self.assertEqual(result, get_default_backend_preference())

    def test_resolve_list_appends_cap_any(self):
        result = resolve_backend_preference(["CAP_ANY"])
        self.assertEqual(result[-1], cv2.CAP_ANY)

    def test_resolve_list_with_int(self):
        result = resolve_backend_preference([cv2.CAP_ANY])
        self.assertIn(cv2.CAP_ANY, result)


if __name__ == "__main__":
    unittest.main()
