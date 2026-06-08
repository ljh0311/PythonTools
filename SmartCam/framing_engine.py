"""
AI-assisted framing / composition scoring for SmartCam.

Computes lightweight, pure-Python composition scores from detection results
(face/object bboxes) to help the smart camera decide when a scene is well
framed and to draw guidance overlays in the live preview.

Scores are normalized to [0.0, 1.0] (higher is better):
  - centering:      how close the subject is to the frame center
  - rule_of_thirds: how close the subject is to a rule-of-thirds intersection
  - margin:         how comfortably the subject sits inside frame edges
  - coverage:       how well-sized the subject is in the frame

The composite score rewards either centered OR rule-of-thirds compositions
(whichever is better for the current subject) plus margin and coverage.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import cv2
import numpy as np


@dataclass
class FramingScore:
    """Composition score broken down by criterion."""
    composite: float = 0.0
    centering: float = 0.0
    rule_of_thirds: float = 0.0
    margin: float = 0.0
    coverage: float = 0.0
    subject_bbox: Optional[Tuple[int, int, int, int]] = None  # (x, y, w, h)
    subject_kind: Optional[str] = None  # "face" | "object" | None
    has_subject: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            'composite': self.composite,
            'centering': self.centering,
            'rule_of_thirds': self.rule_of_thirds,
            'margin': self.margin,
            'coverage': self.coverage,
            'subject_bbox': list(self.subject_bbox) if self.subject_bbox else None,
            'subject_kind': self.subject_kind,
            'has_subject': self.has_subject,
        }


def select_primary_subject(
    detections: Dict[str, Any],
) -> Tuple[Optional[Tuple[int, int, int, int]], Optional[str]]:
    """Select the most prominent subject from detection results.

    Faces win over objects when present (by largest bbox area). Objects fall
    back to the highest confidence detection.
    """
    faces = detections.get('faces') or []
    if faces:
        best = max(
            faces,
            key=lambda f: _bbox_area(f.get('bbox')) or 0,
            default=None,
        )
        if best and best.get('bbox'):
            return tuple(best['bbox']), 'face'

    objects = detections.get('objects') or []
    if objects:
        best = max(
            objects,
            key=lambda o: o.get('confidence', 0.0),
            default=None,
        )
        if best and best.get('bbox'):
            return tuple(best['bbox']), 'object'

    return None, None


def _bbox_area(bbox: Optional[Tuple[int, int, int, int]]) -> Optional[int]:
    if not bbox or len(bbox) != 4:
        return None
    _, _, w, h = bbox
    return max(0, int(w)) * max(0, int(h))


def _bbox_center(bbox: Tuple[int, int, int, int]) -> Tuple[float, float]:
    x, y, w, h = bbox
    return x + w / 2.0, y + h / 2.0


class FramingEngine:
    """Computes framing scores and renders composition overlays."""

    def __init__(
        self,
        center_weight: float = 0.5,
        margin_weight: float = 0.25,
        coverage_weight: float = 0.25,
        coverage_min: float = 0.05,
        coverage_max: float = 0.60,
        margin_target: float = 0.05,
    ) -> None:
        self.center_weight = center_weight
        self.margin_weight = margin_weight
        self.coverage_weight = coverage_weight
        self.coverage_min = coverage_min
        self.coverage_max = coverage_max
        self.margin_target = margin_target

    def score(
        self,
        frame_shape: Tuple[int, int],
        detections: Dict[str, Any],
    ) -> FramingScore:
        """Score the framing of the primary subject within a frame.

        Args:
            frame_shape: (height, width) of the frame.
            detections: dict with optional 'faces' and 'objects' lists, each
                detection containing a 'bbox' = (x, y, w, h).
        """
        height, width = frame_shape[0], frame_shape[1]
        if width <= 0 or height <= 0:
            return FramingScore()

        bbox, kind = select_primary_subject(detections)
        if bbox is None:
            return FramingScore()

        x, y, w, h = bbox
        if w <= 0 or h <= 0:
            return FramingScore(subject_bbox=bbox, subject_kind=kind, has_subject=True)

        cx, cy = _bbox_center(bbox)

        centering = self._centering_score(cx, cy, width, height)
        thirds = self._rule_of_thirds_score(cx, cy, width, height)
        margin = self._margin_score(x, y, w, h, width, height)
        coverage = self._coverage_score(w, h, width, height)

        # Reward whichever composition style scores higher for the subject.
        composition = max(centering, thirds)
        composite = (
            composition * self.center_weight
            + margin * self.margin_weight
            + coverage * self.coverage_weight
        )
        composite = max(0.0, min(1.0, composite))

        return FramingScore(
            composite=composite,
            centering=centering,
            rule_of_thirds=thirds,
            margin=margin,
            coverage=coverage,
            subject_bbox=bbox,
            subject_kind=kind,
            has_subject=True,
        )

    @staticmethod
    def _centering_score(cx: float, cy: float, width: int, height: int) -> float:
        """1.0 when the subject is at the frame center, 0.0 at the corners."""
        center_x, center_y = width / 2.0, height / 2.0
        dx = (cx - center_x) / max(center_x, 1.0)
        dy = (cy - center_y) / max(center_y, 1.0)
        distance = math.sqrt(dx * dx + dy * dy) / math.sqrt(2.0)
        return max(0.0, 1.0 - distance)

    @staticmethod
    def _rule_of_thirds_score(cx: float, cy: float, width: int, height: int) -> float:
        """1.0 when the subject sits on a rule-of-thirds intersection."""
        thirds_x = [width / 3.0, 2 * width / 3.0]
        thirds_y = [height / 3.0, 2 * height / 3.0]
        intersections = [(tx, ty) for tx in thirds_x for ty in thirds_y]
        diag = math.sqrt(width * width + height * height)
        nearest = min(
            math.sqrt((cx - ix) ** 2 + (cy - iy) ** 2)
            for ix, iy in intersections
        )
        # Tighten the falloff so small offsets are forgiven, large ones hurt.
        normalized = nearest / (diag * 0.25)
        return max(0.0, 1.0 - normalized)

    def _margin_score(
        self, x: int, y: int, w: int, h: int, width: int, height: int,
    ) -> float:
        """Linear penalty as the subject approaches frame edges."""
        margins = [
            x / max(width, 1),
            y / max(height, 1),
            (width - (x + w)) / max(width, 1),
            (height - (y + h)) / max(height, 1),
        ]
        worst = min(margins)
        if worst >= self.margin_target:
            return 1.0
        if worst <= 0:
            return 0.0
        return worst / self.margin_target

    def _coverage_score(
        self, w: int, h: int, width: int, height: int,
    ) -> float:
        """1.0 when subject area is within the preferred range, otherwise scaled down."""
        frame_area = max(width * height, 1)
        ratio = (w * h) / frame_area
        if self.coverage_min <= ratio <= self.coverage_max:
            return 1.0
        if ratio < self.coverage_min:
            return max(0.0, ratio / self.coverage_min)
        # ratio > coverage_max: penalize linearly until 2x max -> 0.
        excess = (ratio - self.coverage_max) / max(self.coverage_max, 1e-6)
        return max(0.0, 1.0 - excess)


def draw_framing_overlay(
    frame: np.ndarray,
    score: FramingScore,
    show_grid: bool = True,
    show_subject: bool = True,
    show_score: bool = True,
) -> np.ndarray:
    """Return a copy of `frame` with rule-of-thirds guides and a framing score.

    Drawing happens on a copy so callers retain the original.
    """
    if frame is None or frame.size == 0:
        return frame
    overlay = frame.copy()
    height, width = overlay.shape[:2]

    if show_grid:
        grid_color = (180, 180, 180)
        for tx in (width // 3, 2 * width // 3):
            cv2.line(overlay, (tx, 0), (tx, height), grid_color, 1)
        for ty in (height // 3, 2 * height // 3):
            cv2.line(overlay, (0, ty), (width, ty), grid_color, 1)

    if show_subject and score.subject_bbox:
        x, y, w, h = score.subject_bbox
        color = _quality_color(score.composite)
        cv2.rectangle(overlay, (x, y), (x + w, y + h), color, 2)
        cx, cy = int(x + w / 2), int(y + h / 2)
        cv2.circle(overlay, (cx, cy), 4, color, -1)

    if show_score and score.has_subject:
        text = f"Framing: {int(score.composite * 100)}%"
        color = _quality_color(score.composite)
        cv2.rectangle(overlay, (10, 10), (220, 40), (0, 0, 0), -1)
        cv2.putText(
            overlay, text, (16, 32),
            cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2,
        )

    return overlay


def _quality_color(score: float) -> Tuple[int, int, int]:
    """Map a 0..1 score to a BGR color (red -> yellow -> green)."""
    s = max(0.0, min(1.0, score))
    if s < 0.5:
        # red -> yellow
        ratio = s / 0.5
        return (0, int(255 * ratio), 255)
    ratio = (s - 0.5) / 0.5
    return (0, 255, int(255 * (1 - ratio)))
