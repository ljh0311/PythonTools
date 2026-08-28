"""Headless validation for test.py mode 1 (simple navigation)."""
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


def main():
    tester = NavigationTester(backend=VisualizationBackend.MATPLOTLIB)
    tester.autonomous_controller.start()
    tester._reset_demo_state(clear_paths=True)
    tester.reset_robot_state(1.0, 1.0, 0.0)
    tester.sensor_manager.set_robot_pose(1.0, 1.0, 0.0)

    goal_x, goal_y = 8.0, 8.0
    ok = tester.autonomous_controller.navigate_to(goal_x, goal_y, tolerance=0.15, timeout=90.0)
    assert ok, "navigate_to failed"

    tester.test_running = True
    steps = 0
    max_steps = 3000
    reached = False
    stuck = False

    while tester.test_running and steps < max_steps:
        tester._update_robot_physics()
        status = tester.autonomous_controller.get_status()
        state = status.get("navigation_state", "")
        if state == "reached_goal" or tester.autonomous_controller.goal_reached_flag:
            reached = True
            break
        if state in ("stuck", "error"):
            stuck = True
            break
        steps += 1
        if steps % 200 == 0:
            pos = tester.robot_state.get_position()
            print(f"step {steps}: state={state} pos=({pos.x:.2f},{pos.y:.2f})")

    tester.autonomous_controller.stop()
    pos = tester.robot_state.get_position()
    dist = ((pos.x - goal_x) ** 2 + (pos.y - goal_y) ** 2) ** 0.5
    completion_tol = tester.autonomous_controller.goal_completion_tolerance

    print(f"steps={steps} reached={reached} stuck={stuck} dist_to_goal={dist:.2f}m")
    print(f"valid_paths={len(tester.autonomous_controller.valid_paths)} "
          f"stuck_locs={len(tester.autonomous_controller.stuck_locations)}")
    passed = reached or dist <= completion_tol
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
