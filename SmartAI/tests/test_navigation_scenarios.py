"""Pytest scenarios for navigation modes from test.py menu."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fixtures.config import build_config_dict
from fixtures.config import TestConfig as NavigationTestConfig
from fixtures.mocks import EnhancedMockMotorController, MockSensorManager
from fixtures.navigation_harness import run_headless_navigation
from src.core.robot_state import RobotState
from src.navigation.pathfinder import Pathfinder


def test_simple_navigation_smoke():
    """Headless smoke test for menu mode 1: simple navigation."""
    reached = run_headless_navigation(
        start=(1.0, 1.0, 0.0),
        goal=(8.0, 8.0),
        obstacles=[],
        max_steps=1200,
    )
    assert reached


def test_obstacle_avoidance_smoke():
    """Headless smoke test for menu mode 2: obstacle avoidance."""
    reached = run_headless_navigation(
        start=(1.0, 5.0, 0.0),
        goal=(9.0, 5.0),
        obstacles=[(5.0, 5.0, 0.35)],
        max_steps=2000,
    )
    assert reached


def test_mock_sensor_reads_obstacle():
    """Verify mock sensors detect placed obstacles within range."""
    sensor_manager = MockSensorManager()
    sensor_manager.set_robot_pose(1.0, 5.0, 0.0)
    sensor_manager.set_obstacles([(2.0, 5.0, 0.15)])

    readings = sensor_manager.get_sensor_data()['ultrasonic']
    assert readings['front'].valid
    assert readings['front'].value < sensor_manager.max_range


def test_motor_calibration_fixture():
    """Verify mock motor calibration fields update."""
    config = NavigationTestConfig()
    motor = EnhancedMockMotorController(config)
    motor.calibrate(1.1, 0.9)
    status = motor.get_status()
    assert status['left_calibration'] == 1.1
    assert status['right_calibration'] == 0.9


def test_pathfinder_with_fixture_config():
    """Verify pathfinder initializes from shared test config."""
    config = NavigationTestConfig()
    pathfinder = Pathfinder(build_config_dict(config))
    path = pathfinder.find_path(0, 0, 100, 100)
    assert isinstance(path, list)
