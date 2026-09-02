"""Headless navigation helpers for pytest scenarios."""

import math
import time
from contextlib import contextmanager
from unittest.mock import patch

from src.core.robot_state import RobotState
from src.navigation.autonomous_controller import AutonomousController
from src.navigation.pathfinder import Pathfinder

from .config import TestConfig, build_config_dict
from .mocks import EnhancedMockMotorController, MockSensorManager

# Default obstacles from test.py NavigationTester._setup_test_environment
DEFAULT_TEST_OBSTACLES = [
    (3.0, 3.0, 0.3),
    (6.0, 6.0, 0.4),
    (7.0, 2.0, 0.25),
    (2.0, 7.0, 0.35),
    (4.0, 1.0, 0.2),
    (1.0, 4.0, 0.3),
]

PHYSICS_DT = 0.05


@contextmanager
def isolated_learning_data():
    """Prevent tests from loading or writing repo learning data."""
    with patch.object(AutonomousController, '_load_learning_data'), patch.object(
        AutonomousController, '_save_learning_data'
    ):
        yield


def _step_motors(motor_controller, dt=PHYSICS_DT):
    motor_controller._update_speeds(dt)
    return motor_controller.left_speed, motor_controller.right_speed


def _update_robot_physics(robot_state, motor_controller, sensor_manager, pathfinder, dt=PHYSICS_DT):
    left_speed, right_speed = _step_motors(motor_controller, dt)
    if abs(left_speed) < 0.01 and abs(right_speed) < 0.01:
        return

    current_pos = robot_state.get_position()
    if abs(left_speed) > 1.0 or abs(right_speed) > 1.0:
        max_speed = 0.5
        left_vel = (left_speed / 100.0) * max_speed
        right_vel = (right_speed / 100.0) * max_speed
    else:
        left_vel = left_speed
        right_vel = right_speed

    wheel_base = 0.25
    linear_vel = (left_vel + right_vel) / 2.0
    angular_vel = (right_vel - left_vel) / wheel_base

    new_x = current_pos.x + linear_vel * dt * math.cos(current_pos.theta)
    new_y = current_pos.y + linear_vel * dt * math.sin(current_pos.theta)
    new_theta = current_pos.theta + angular_vel * dt
    new_theta = math.atan2(math.sin(new_theta), math.cos(new_theta))

    robot_state.update_position(new_x - current_pos.x, new_y - current_pos.y, new_theta - current_pos.theta)
    pathfinder.update_robot_position(new_x, new_y)
    sensor_manager.set_robot_pose(new_x, new_y, new_theta)


def run_headless_navigation(
    start=(1.0, 1.0, 0.0),
    goal=(5.0, 5.0),
    obstacles=None,
    max_steps=1200,
):
    """Run a short headless navigation scenario and return whether goal was reached."""
    config = TestConfig(enable_camera=False)
    config_dict = build_config_dict(config)

    with isolated_learning_data():
        robot_state = RobotState(config_dict)
        motor_controller = EnhancedMockMotorController(config)
        sensor_manager = MockSensorManager()
        pathfinder = Pathfinder(config_dict)
        controller = AutonomousController(
            robot_state, motor_controller, sensor_manager, pathfinder
        )
        controller.running = True
        controller.emergency_stop = False

        if obstacles:
            for obstacle in obstacles:
                pathfinder.add_obstacle(*obstacle)
            sensor_manager.set_obstacles(list(obstacles))

        start_x, start_y, start_theta = start
        robot_state.reset_position(start_x, start_y, start_theta)
        sensor_manager.set_robot_pose(start_x, start_y, start_theta)
        pathfinder.update_robot_position(start_x, start_y)

        if not controller.navigate_to(goal[0], goal[1]):
            controller.running = False
            return False

        reached = False
        try:
            for _ in range(max_steps):
                controller._update_navigation()
                _update_robot_physics(robot_state, motor_controller, sensor_manager, pathfinder)
                status = controller.get_status()
                nav_state = status.get('navigation_state')
                if nav_state == 'reached_goal':
                    reached = True
                    break
                if nav_state == 'stuck':
                    break
        finally:
            controller.running = False
            controller.motor_controller.stop()

    return reached
