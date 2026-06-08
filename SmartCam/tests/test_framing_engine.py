"""
Unit tests for the framing/composition scoring engine.

These tests use synthetic detection dictionaries; no camera or image data is
required.
"""

from __future__ import annotations

import os
import sys
import unittest

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from framing_engine import FramingEngine, select_primary_subject  # noqa: E402


def make_face(x, y, w, h, conf=0.9):
    return {'bbox': (x, y, w, h), 'confidence': conf}


def make_object(x, y, w, h, conf=0.9, class_name='person'):
    return {'bbox': (x, y, w, h), 'confidence': conf, 'class_name': class_name}


class SubjectSelectionTests(unittest.TestCase):
    def test_no_detections_returns_none(self):
        bbox, kind = select_primary_subject({})
        self.assertIsNone(bbox)
        self.assertIsNone(kind)

    def test_face_wins_over_object(self):
        detections = {
            'faces': [make_face(0, 0, 50, 50)],
            'objects': [make_object(0, 0, 200, 200)],
        }
        bbox, kind = select_primary_subject(detections)
        self.assertEqual(kind, 'face')

    def test_largest_face_is_selected(self):
        detections = {
            'faces': [
                make_face(0, 0, 10, 10),
                make_face(20, 20, 100, 100),
                make_face(200, 200, 50, 50),
            ],
        }
        bbox, kind = select_primary_subject(detections)
        self.assertEqual(bbox, (20, 20, 100, 100))
        self.assertEqual(kind, 'face')

    def test_highest_confidence_object_when_no_faces(self):
        detections = {
            'objects': [
                make_object(0, 0, 50, 50, conf=0.4),
                make_object(20, 20, 50, 50, conf=0.9),
            ],
        }
        bbox, kind = select_primary_subject(detections)
        self.assertEqual(bbox, (20, 20, 50, 50))
        self.assertEqual(kind, 'object')


class FramingScoreTests(unittest.TestCase):
    def setUp(self):
        self.engine = FramingEngine()
        self.frame_shape = (480, 640)  # height, width

    def test_empty_detections_have_no_subject(self):
        score = self.engine.score(self.frame_shape, {})
        self.assertFalse(score.has_subject)
        self.assertEqual(score.composite, 0.0)

    def test_perfectly_centered_subject_has_high_score(self):
        height, width = self.frame_shape
        bbox = (width // 2 - 50, height // 2 - 50, 100, 100)
        detections = {'faces': [make_face(*bbox)]}
        score = self.engine.score(self.frame_shape, detections)
        self.assertTrue(score.has_subject)
        self.assertGreaterEqual(score.centering, 0.95)
        self.assertGreaterEqual(score.composite, 0.6)

    def test_corner_subject_has_low_centering_score(self):
        bbox = (0, 0, 60, 60)
        detections = {'faces': [make_face(*bbox)]}
        score = self.engine.score(self.frame_shape, detections)
        self.assertLess(score.centering, 0.4)

    def test_rule_of_thirds_alignment_gives_credit(self):
        height, width = self.frame_shape
        cx = width // 3
        cy = height // 3
        bbox = (cx - 30, cy - 30, 60, 60)
        detections = {'faces': [make_face(*bbox)]}
        score = self.engine.score(self.frame_shape, detections)
        self.assertGreater(score.rule_of_thirds, 0.85)

    def test_too_small_subject_has_low_coverage(self):
        bbox = (10, 10, 5, 5)
        detections = {'faces': [make_face(*bbox)]}
        score = self.engine.score(self.frame_shape, detections)
        self.assertLess(score.coverage, 0.5)

    def test_subject_at_edge_has_low_margin(self):
        height, width = self.frame_shape
        bbox = (0, height // 2 - 50, 100, 100)
        detections = {'faces': [make_face(*bbox)]}
        score = self.engine.score(self.frame_shape, detections)
        self.assertLess(score.margin, 0.2)

    def test_score_is_clamped_to_unit_interval(self):
        height, width = self.frame_shape
        bbox = (width // 2 - 100, height // 2 - 100, 200, 200)
        detections = {'faces': [make_face(*bbox)]}
        score = self.engine.score(self.frame_shape, detections)
        self.assertGreaterEqual(score.composite, 0.0)
        self.assertLessEqual(score.composite, 1.0)

    def test_score_to_dict_is_serializable(self):
        height, width = self.frame_shape
        bbox = (width // 2 - 30, height // 2 - 30, 60, 60)
        detections = {'faces': [make_face(*bbox)]}
        score = self.engine.score(self.frame_shape, detections)
        data = score.to_dict()
        self.assertIn('composite', data)
        self.assertIn('subject_bbox', data)
        self.assertIsInstance(data['subject_bbox'], list)


if __name__ == "__main__":
    unittest.main()
