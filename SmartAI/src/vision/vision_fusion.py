"""Vision fusion for navigation — projects camera detections onto the pathfinder grid.

Research applied (Tesla/Xiaomi/Narwal robot vac patterns):
- Short-range reactive layer: emergency stop when obstacle crosses forward cone (Narwal-style).
- Predictive layer: track velocity, estimate time-to-intersection; reroute if TTC < horizon
  else slow/stop (similar to proactive replanning in premium vacuums).
- Stop vs reroute: high risk → stop; medium risk with alternate path → temporary grid
  obstacles + replan (Tesla-style layered planning).
"""

import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
from loguru import logger

from ..navigation.pathfinder import Pathfinder
from .dynamic_obstacle_predictor import DynamicObstacle, DynamicObstaclePredictor
from .scene_understanding import SceneUnderstanding
from ..core.proximity_context import count_vision_labels


@dataclass
class VisionNavDecision:
  action: str  # clear, slow, stop, reroute
  risk_level: str = "low"
  reason: str = ""
  dynamic_cells: List[Tuple[int, int]] = field(default_factory=list)
  obstacles: List[DynamicObstacle] = field(default_factory=list)


class VisionFusion:
  """Fuses vision modules into navigation obstacle grid and reactive decisions."""

  def __init__(self, config: dict, pathfinder: Pathfinder):
    self.config = config
    vision_cfg = config.get("vision", {})
    cam = config.get("hardware", {}).get("camera", {})
    w = cam.get("width", 640)
    h = cam.get("height", 480)

    self.enabled = vision_cfg.get("fusion_enabled", True)
    self.stop_ttc = vision_cfg.get("stop_time_to_collision", 1.0)
    self.reroute_ttc = vision_cfg.get("reroute_time_to_collision", 3.0)
    self.fov_deg = vision_cfg.get("camera_fov_deg", 60.0)
    self.max_range_cm = vision_cfg.get("max_range_cm", 300.0)

    self.pathfinder = pathfinder
    self.predictor = DynamicObstaclePredictor(
      model_path=vision_cfg.get("model_path", "efficientdet.tflite"),
      prediction_horizon=vision_cfg.get("prediction_horizon", 2.0),
    )
    self.scene = SceneUnderstanding(frame_width=w, frame_height=h)
    self._last_result: Dict[str, Any] = {}
    self._last_decision = VisionNavDecision(action="clear")
    self._dynamic_obstacles: List[Tuple[float, float, float, float]] = []

  def process_frame(self, frame: np.ndarray) -> Dict[str, Any]:
    if not self.enabled or frame is None:
      return {"enabled": False}

    obstacles = self.predictor.process_frame(frame)
    scene = self.scene.process_frame(frame)
    decision = self._decide(obstacles, scene)
    self._apply_to_grid(decision, obstacles)
    self._last_decision = decision
    vision_labels = count_vision_labels(obstacles, scene)
    self._last_result = {
      "enabled": True,
      "decision": decision.action,
      "risk_level": decision.risk_level,
      "reason": decision.reason,
      "obstacle_count": len(obstacles),
      "scene_regions": len(scene.get("regions", [])),
      "dynamic_cells": decision.dynamic_cells,
      "scene": scene,
      "vision_labels": vision_labels,
    }
    return self._last_result

  def get_last_result(self) -> Dict[str, Any]:
    return self._last_result

  def get_navigation_decision(self) -> VisionNavDecision:
    return self._last_decision

  def should_stop(self) -> bool:
    return self._last_decision.action == "stop"

  def should_reroute(self) -> bool:
    return self._last_decision.action == "reroute"

  def should_slow(self) -> bool:
    return self._last_decision.action in ("slow", "stop")

  def clear_dynamic_layer(self) -> None:
    for x, y, r, _ in self._dynamic_obstacles:
      self.pathfinder.remove_obstacle(x, y, r)
    self._dynamic_obstacles.clear()

  def _decide(self, obstacles: List[DynamicObstacle], scene: dict) -> VisionNavDecision:
    high = [o for o in obstacles if o.risk_level == "high"]
    medium = [o for o in obstacles if o.risk_level == "medium"]

    if high:
      return VisionNavDecision(
        action="stop",
        risk_level="high",
        reason="Predicted path crossing — emergency stop (TTC < 1s)",
        obstacles=high,
      )

    crossing = self._path_crossing_obstacles(obstacles)
    if crossing:
      worst = min(crossing, key=lambda o: o.time_to_collision or 999)
      ttc = worst.time_to_collision or self.reroute_ttc
      if ttc < self.stop_ttc:
        return VisionNavDecision(
          action="stop",
          risk_level="high",
          reason=f"Dynamic obstacle crossing path (TTC={ttc:.1f}s)",
          obstacles=crossing,
        )
      if ttc < self.reroute_ttc:
        cells = self._project_obstacles_to_grid(crossing)
        return VisionNavDecision(
          action="reroute",
          risk_level="medium",
          reason=f"Obstacle approaching — reroute (TTC={ttc:.1f}s)",
          dynamic_cells=cells,
          obstacles=crossing,
        )

    if medium:
      return VisionNavDecision(
        action="slow",
        risk_level="medium",
        reason="Nearby dynamic obstacle — reduce speed",
        obstacles=medium,
      )

    # Scene understanding: blocked forward corridor
    # Scene understanding: forward path not in safe directions
    nav_hints = scene.get("navigation_features", {})
    safe_dirs = nav_hints.get("safe_directions", [])
    forward_clear = any(d.get("direction") == "forward" for d in safe_dirs)
    if safe_dirs and not forward_clear:
      return VisionNavDecision(
        action="slow",
        risk_level="medium",
        reason="Scene analysis: forward corridor blocked",
      )

    return VisionNavDecision(action="clear", risk_level="low")

  def _path_crossing_obstacles(self, obstacles: List[DynamicObstacle]) -> List[DynamicObstacle]:
    """Obstacles in lower-center FOV cone (likely crossing robot path)."""
    crossing = []
    for o in obstacles:
      cx, cy = self.predictor._get_center(o.bbox)
      # Lower half of frame, center third
      if cy > self.scene.frame_height * 0.35 and abs(cx - self.scene.frame_width / 2) < self.scene.frame_width * 0.35:
        if o.time_to_collision is not None and o.time_to_collision < self.reroute_ttc:
          crossing.append(o)
    return crossing

  def _project_obstacles_to_grid(self, obstacles: List[DynamicObstacle]) -> List[Tuple[int, int]]:
    cells = []
    for o in obstacles:
      wx, wy = self._bbox_to_world(o.bbox)
      gx, gy = self.pathfinder.world_to_grid(wx, wy)
      cells.append((gx, gy))
    return cells

  def _bbox_to_world(self, bbox: Tuple[int, int, int, int]) -> Tuple[float, float]:
    """Project image bbox to approximate world cm ahead of robot."""
    x, y, w, h = bbox
    cx = x + w / 2
    cy = y + h / 2
    # Larger y (lower in image) = closer
    depth_frac = max(0.05, min(1.0, cy / self.scene.frame_height))
    range_cm = self.max_range_cm * (1.0 - depth_frac * 0.7)
    half_fov = math.radians(self.fov_deg / 2)
    angle = (cx / self.scene.frame_width - 0.5) * 2 * half_fov
    wx = range_cm * math.sin(angle)
    wy = range_cm * math.cos(angle)
    return wx, wy

  def _apply_to_grid(self, decision: VisionNavDecision, obstacles: List[DynamicObstacle]) -> None:
    self.clear_dynamic_layer()
    if decision.action not in ("reroute", "slow", "stop"):
      return
    radius = self.config.get("robot", {}).get("width", 30) / 2 + 15
    for o in decision.obstacles or obstacles:
      wx, wy = self._bbox_to_world(o.bbox)
      if o.predicted_position:
        px = o.predicted_position[0] / self.scene.frame_width * self.max_range_cm
        py = o.predicted_position[1] / self.scene.frame_height * self.max_range_cm
        wx = (wx + px) / 2
        wy = (wy + py) / 2
      self.pathfinder.add_obstacle(wx, wy, radius)
      self._dynamic_obstacles.append((wx, wy, radius, time.time()))

  def get_status(self) -> dict:
    return {
      "enabled": self.enabled,
      "last_decision": self._last_decision.action,
      "risk_level": self._last_decision.risk_level,
      "dynamic_obstacle_count": len(self._dynamic_obstacles),
    }
