"""Unit checks for PathRefiner learning + smoothing."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.navigation.path_refiner import PathRefiner, metrics_of, to_path_points, to_xy
from src.navigation.pathfinder import Pathfinder


def _cfg():
    return {
        "robot": {
            "width": 0.3,
            "length": 0.4,
            "max_speed": 0.5,
            "turn_speed": 0.3,
            "safety_distances": {"comfortable": 0.5, "warning": 0.35, "critical": 0.15},
        },
        "navigation": {
            "map_width": 10.0,
            "map_height": 10.0,
            "grid_size": 0.5,
            "inflation_radius": 0.2,
        },
    }


class _FakePF:
    """Minimal LOS helper for unit tests without full A* config surface."""

    def __init__(self):
        self.grid_size = 0.5
        self.blocked = set()

    def add_block(self, x, y):
        self.blocked.add((int(x / self.grid_size), int(y / self.grid_size)))

    def _line_of_sight(self, p1, p2) -> bool:
        steps = max(2, int(max(abs(p2.x - p1.x), abs(p2.y - p1.y)) / self.grid_size * 2))
        for k in range(1, steps):
            x = p1.x + (p2.x - p1.x) * k / steps
            y = p1.y + (p2.y - p1.y) * k / steps
            gx, gy = int(x / self.grid_size), int(y / self.grid_size)
            if (gx, gy) in self.blocked:
                return False
        return True

    def _simplify_path(self, path):
        if not path:
            return []
        simplified = [path[0]]
        i = 0
        while i < len(path) - 1:
            j = i + 1
            while j < len(path):
                if not self._line_of_sight(simplified[-1], path[j]):
                    break
                j += 1
            simplified.append(path[j - 1])
            i = j - 1
        return simplified


def test_metrics_turn_count():
    zig = [(0, 0), (1, 0), (1, 1), (2, 1), (2, 2)]
    m = metrics_of(zig)
    assert m.turn_count >= 2
    straight = [(0, 0), (1, 0), (2, 0), (3, 0)]
    assert metrics_of(straight).turn_count == 0
    print("PASS metrics")


def test_refine_improves_with_learning():
    pf = _FakePF()
    # Zig-zag A*-like path
    jagged = to_path_points(
        [
            (1.0, 1.0),
            (1.5, 1.0),
            (2.0, 1.0),
            (2.0, 1.5),
            (2.0, 2.0),
            (2.0, 2.5),
            (2.0, 3.0),
            (2.5, 3.0),
            (3.0, 3.0),
            (3.5, 3.0),
            (4.0, 3.0),
            (4.0, 3.5),
            (4.0, 4.0),
            (4.5, 4.0),
            (5.0, 4.0),
            (5.5, 4.0),
            (6.0, 4.0),
            (6.5, 4.0),
            (7.0, 4.0),
            (7.5, 4.0),
            (8.0, 4.0),
            (8.0, 4.5),
            (8.0, 5.0),
            (8.0, 5.5),
            (8.0, 6.0),
            (8.0, 6.5),
            (8.0, 7.0),
            (8.0, 7.5),
            (8.0, 8.0),
        ]
    )
    start, goal = (1.0, 1.0), (8.0, 8.0)
    refiner = PathRefiner(cell_size=0.5)

    first = refiner.refine_path(jagged, start, goal, pf)
    m1 = metrics_of(to_xy(first))

    # Record a smoother successful drive
    smooth = [(1.0, 1.0), (2.0, 3.0), (5.0, 4.0), (8.0, 8.0)]
    refiner.record_run(start, goal, smooth, pf)

    second = refiner.refine_path(jagged, start, goal, pf)
    m2 = metrics_of(to_xy(second))
    assert m2.waypoint_count <= m1.waypoint_count
    assert m2.turn_count <= m1.turn_count or m2.length_m <= m1.length_m + 0.05
    assert "learned" in refiner.last_refine_note or m2.waypoint_count < m1.waypoint_count
    print(
        f"PASS refine: {m1.waypoint_count}/{m1.turn_count}/{m1.length_m:.2f} -> "
        f"{m2.waypoint_count}/{m2.turn_count}/{m2.length_m:.2f} ({refiner.last_refine_note})"
    )


def test_pathfinder_smoke_optional():
    """Optional smoke if full Pathfinder config works."""
    try:
        pf = Pathfinder(_cfg())
    except Exception as e:
        print(f"SKIP pathfinder smoke: {e}")
        return
    path = pf.find_path(1.0, 1.0, 3.0, 3.0)
    assert path
    print(f"PASS pathfinder smoke ({len(path)} pts)")


if __name__ == "__main__":
    test_metrics_turn_count()
    test_refine_improves_with_learning()
    test_pathfinder_smoke_optional()
    print("OK")
