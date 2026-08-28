"""Learn and refine navigation paths over successful runs.

Records driven trajectories and, on later plans for similar start→goal,
prefers shorter / fewer-turn corridors and line-of-sight shortcuts.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from .pathfinder import PathPoint


@dataclass
class PathMetrics:
    waypoint_count: int
    length_m: float
    turn_count: int

    def better_than(self, other: "PathMetrics") -> bool:
        if self.length_m < other.length_m - 0.05:
            return True
        if abs(self.length_m - other.length_m) <= 0.05 and self.turn_count < other.turn_count:
            return True
        if (
            abs(self.length_m - other.length_m) <= 0.05
            and self.turn_count == other.turn_count
            and self.waypoint_count < other.waypoint_count
        ):
            return True
        return False


@dataclass
class LearnedCorridor:
    start_cell: Tuple[int, int]
    goal_cell: Tuple[int, int]
    waypoints: List[Tuple[float, float]]
    metrics: PathMetrics
    uses: int = 1


def path_length(points: List[Tuple[float, float]]) -> float:
    if len(points) < 2:
        return 0.0
    total = 0.0
    for i in range(1, len(points)):
        total += math.hypot(points[i][0] - points[i - 1][0], points[i][1] - points[i - 1][1])
    return total


def turn_count(points: List[Tuple[float, float]], min_angle_deg: float = 25.0) -> int:
    if len(points) < 3:
        return 0
    min_rad = math.radians(min_angle_deg)
    turns = 0
    for i in range(1, len(points) - 1):
        ax = points[i][0] - points[i - 1][0]
        ay = points[i][1] - points[i - 1][1]
        bx = points[i + 1][0] - points[i][0]
        by = points[i + 1][1] - points[i][1]
        la = math.hypot(ax, ay)
        lb = math.hypot(bx, by)
        if la < 1e-6 or lb < 1e-6:
            continue
        dot = max(-1.0, min(1.0, (ax * bx + ay * by) / (la * lb)))
        ang = math.acos(dot)
        if ang >= min_rad:
            turns += 1
    return turns


def metrics_of(points: List[Tuple[float, float]]) -> PathMetrics:
    return PathMetrics(
        waypoint_count=len(points),
        length_m=path_length(points),
        turn_count=turn_count(points),
    )


def to_xy(path: List[PathPoint]) -> List[Tuple[float, float]]:
    return [(p.x, p.y) for p in path]


def to_path_points(xy: List[Tuple[float, float]]) -> List[PathPoint]:
    out: List[PathPoint] = []
    for i, (x, y) in enumerate(xy):
        if i + 1 < len(xy):
            theta = math.atan2(xy[i + 1][1] - y, xy[i + 1][0] - x)
        elif i > 0:
            theta = math.atan2(y - xy[i - 1][1], x - xy[i - 1][0])
        else:
            theta = 0.0
        out.append(PathPoint(x=x, y=y, theta=theta, speed=0.5, action="forward"))
    if out:
        out[-1] = PathPoint(x=out[-1].x, y=out[-1].y, theta=out[-1].theta, speed=0.0, action="stop")
    return out


class PathRefiner:
    """Stores successful runs and refines new A* paths using that memory."""

    def __init__(self, cell_size: float = 0.5, match_cells: int = 1):
        self.cell_size = cell_size
        self.match_cells = match_cells
        self.corridors: Dict[Tuple[Tuple[int, int], Tuple[int, int]], LearnedCorridor] = {}
        self.history: List[Dict[str, Any]] = []
        self.last_refine_note: str = ""

    def _cell(self, x: float, y: float) -> Tuple[int, int]:
        return (int(x // self.cell_size), int(y // self.cell_size))

    def _corridor_key(self, sx: float, sy: float, gx: float, gy: float):
        return (self._cell(sx, sy), self._cell(gx, gy))

    def record_run(
        self,
        start: Tuple[float, float],
        goal: Tuple[float, float],
        driven: List[Tuple[float, float]],
        pathfinder: Any = None,
    ) -> Optional[PathMetrics]:
        """Record a successful drive; keep best corridor for that start/goal cell pair."""
        if len(driven) < 2:
            return None
        simplified = driven
        if pathfinder is not None and hasattr(pathfinder, "_simplify_path"):
            simplified = to_xy(pathfinder._simplify_path(to_path_points(driven)))
            if len(simplified) < 2:
                simplified = driven

        m = metrics_of(simplified)
        key = self._corridor_key(start[0], start[1], goal[0], goal[1])
        existing = self.corridors.get(key)
        if existing is None or m.better_than(existing.metrics):
            self.corridors[key] = LearnedCorridor(
                start_cell=key[0],
                goal_cell=key[1],
                waypoints=list(simplified),
                metrics=m,
                uses=1 if existing is None else existing.uses + 1,
            )
            note = "new best" if existing is None else "improved"
            logger.info(
                f"PathRefiner: {note} corridor {key} len={m.length_m:.2f}m "
                f"turns={m.turn_count} pts={m.waypoint_count}"
            )
        else:
            existing.uses += 1

        self.history.append(
            {
                "start": start,
                "goal": goal,
                "path": list(simplified),
                "metrics": m,
                "key": key,
            }
        )
        return m

    def _find_learned(self, sx: float, sy: float, gx: float, gy: float) -> Optional[LearnedCorridor]:
        key = self._corridor_key(sx, sy, gx, gy)
        hit = self.corridors.get(key)
        if hit:
            return hit
        sc, gc = key
        for (a, b), corr in self.corridors.items():
            if abs(a[0] - sc[0]) <= self.match_cells and abs(a[1] - sc[1]) <= self.match_cells:
                if abs(b[0] - gc[0]) <= self.match_cells and abs(b[1] - gc[1]) <= self.match_cells:
                    return corr
        return None

    def refine_path(
        self,
        path: List[PathPoint],
        start: Tuple[float, float],
        goal: Tuple[float, float],
        pathfinder: Any,
    ) -> List[PathPoint]:
        """Prefer learned corridor when clear; always LOS-simplify + light corner trim."""
        if not path:
            self.last_refine_note = "empty"
            return path

        base = to_xy(path)
        base_m = metrics_of(base)
        candidate = base
        note = "astar"

        learned = self._find_learned(start[0], start[1], goal[0], goal[1])
        if learned and len(learned.waypoints) >= 2:
            # Stitch current start → learned → goal, then simplify if clear
            stitched = [start] + list(learned.waypoints) + [goal]
            stitched_pts = to_path_points(stitched)
            try:
                simplified = pathfinder._simplify_path(stitched_pts)
                if simplified and self._path_clear(simplified, pathfinder):
                    cand_xy = to_xy(simplified)
                    cand_m = metrics_of(cand_xy)
                    if cand_m.better_than(base_m) or cand_m.turn_count < base_m.turn_count:
                        candidate = cand_xy
                        note = f"learned(uses={learned.uses})"
            except Exception as e:
                logger.debug(f"PathRefiner learned stitch failed: {e}")

        # Always simplify A*/candidate with LOS
        try:
            simplified = pathfinder._simplify_path(to_path_points(candidate))
            if simplified and self._path_clear(simplified, pathfinder):
                candidate = to_xy(simplified)
                if note == "astar":
                    note = "simplified"
        except Exception:
            pass

        candidate = self._trim_shallow_corners(candidate, pathfinder)
        out_m = metrics_of(candidate)
        self.last_refine_note = (
            f"{note}: {base_m.waypoint_count}->{out_m.waypoint_count} pts, "
            f"{base_m.length_m:.2f}->{out_m.length_m:.2f}m, "
            f"{base_m.turn_count}->{out_m.turn_count} turns"
        )
        logger.info(f"PathRefiner: {self.last_refine_note}")
        return to_path_points(candidate)

    def _path_clear(self, path: List[PathPoint], pathfinder: Any) -> bool:
        for i in range(len(path) - 1):
            if not pathfinder._line_of_sight(path[i], path[i + 1]):
                return False
        return True

    def _trim_shallow_corners(
        self, points: List[Tuple[float, float]], pathfinder: Any, min_angle_deg: float = 18.0
    ) -> List[Tuple[float, float]]:
        """Drop midpoints that barely change heading if LOS still holds."""
        if len(points) < 3:
            return points
        min_rad = math.radians(min_angle_deg)
        changed = True
        pts = list(points)
        while changed and len(pts) >= 3:
            changed = False
            i = 1
            while i < len(pts) - 1:
                ax = pts[i][0] - pts[i - 1][0]
                ay = pts[i][1] - pts[i - 1][1]
                bx = pts[i + 1][0] - pts[i][0]
                by = pts[i + 1][1] - pts[i][1]
                la = math.hypot(ax, ay)
                lb = math.hypot(bx, by)
                drop = False
                if la > 1e-6 and lb > 1e-6:
                    dot = max(-1.0, min(1.0, (ax * bx + ay * by) / (la * lb)))
                    ang = math.acos(dot)
                    if ang < min_rad:
                        p0 = PathPoint(x=pts[i - 1][0], y=pts[i - 1][1], theta=0.0, speed=0.5, action="forward")
                        p2 = PathPoint(x=pts[i + 1][0], y=pts[i + 1][1], theta=0.0, speed=0.5, action="forward")
                        if pathfinder._line_of_sight(p0, p2):
                            drop = True
                if drop:
                    pts.pop(i)
                    changed = True
                else:
                    i += 1
        return pts

    def get_history_paths(self) -> List[List[Tuple[float, float]]]:
        return [h["path"] for h in self.history]

    def get_status(self) -> dict:
        return {
            "corridors": len(self.corridors),
            "runs_recorded": len(self.history),
            "last_refine": self.last_refine_note,
        }
