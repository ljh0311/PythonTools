"""Headless check: physics updates even when camera_available but frames fail."""
import logging
import os
import sys
import time

import matplotlib
matplotlib.use("Agg")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["SMARTAI_HEADLESS"] = "1"

logging.getLogger("test").setLevel(logging.WARNING)

from test import NavigationTester, VisualizationBackend


class _FailingCamera:
    """Stub VideoCapture that always fails to read."""

    def isOpened(self):
        return True

    def read(self):
        return False, None

    def release(self):
        pass


def main():
    tester = NavigationTester(backend=VisualizationBackend.MATPLOTLIB)
    tester.physics_throttle = False
    tester.camera_available = True
    tester.camera_fail_threshold = 3
    tester.camera = _FailingCamera()
    tester.autonomous_controller.vision_fusion = tester.sim_vision_fusion
    tester.sim_vision_fusion.inject_decision("stop", "stale camera stop", "high")

    tester.reset_robot_state(1.0, 1.0, 0.0)
    start_pos = tester.robot_state.get_position()
    start_x, start_y = start_pos.x, start_pos.y
    # Bypass acceleration ramp so physics movement is measurable immediately
    mc = tester.motor_controller
    mc.left_speed = mc.right_speed = 50.0
    mc.left_target = mc.right_target = 50.0
    mc.is_running = True
    mc.last_update_time = time.time()

    for _ in range(5):
        tester._last_physics_update_time = time.time() - 0.05
        tester._update_robot_physics()

    end = tester.robot_state.get_position()
    moved = ((end.x - start_x) ** 2 + (end.y - start_y) ** 2) ** 0.5

    print(f"moved={moved:.4f}m camera_available={tester.camera_available} "
          f"fail_count={tester.camera_fail_count} "
          f"vision_fusion={tester.autonomous_controller.vision_fusion}")

    assert moved > 0.01, f"expected pose update despite camera fail, moved={moved:.4f}m"
    assert tester.camera_available is False, "camera should disable after consecutive failures"
    assert tester.autonomous_controller.vision_fusion is None, "vision_fusion should be cleared"
    print("PASS: physics-first + camera fail-soft")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
