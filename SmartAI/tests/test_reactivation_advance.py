#!/usr/bin/env python3
"""Reproduce: past strategy window must advance reactivation within 1-2 ticks."""

import os
import sys
import time
import types
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.navigation.autonomous_controller import AutonomousController, NavigationState
from src.core.robot_state import Position


def _make_controller():
    robot_state = MagicMock()
    robot_state.get_position.return_value = Position(1.0, 1.0, 0.0)
    robot_state.config = {
        "navigation": {"grid_size": 0.2, "map_width": 10.0, "map_height": 10.0},
        "robot": {"width": 0.3, "length": 0.4, "max_speed": 0.83},
    }

    motor = MagicMock()
    motor.get_speeds.return_value = (0.0, 0.0)

    reading = types.SimpleNamespace(value=2.0)
    sensors = MagicMock()
    sensors.get_sensor_data.return_value = {
        "ultrasonic": {"front": reading, "left": reading, "right": reading},
    }

    pathfinder = MagicMock()
    ac = AutonomousController(robot_state, motor, sensors, pathfinder, vision_fusion=None)
    ac._set_linear_mps = MagicMock()
    ac._set_wheel_linear_mps = MagicMock()
    return ac


def test_strategy_advances_past_movement_window():
    ac = _make_controller()
    ac.nav_state = NavigationState.REACTIVATING
    ac.current_reactivation_strategy = ac.reactivation_strategies.index("aggressive_backup")
    ac.reactivation_attempts = 0
    ac.reactivation_start_time = time.time() - 4.5  # past 4s aggressive_backup window
    ac.stuck_position = (1.0, 1.0)  # 0.00m movement → check fails

    before = ac.current_reactivation_strategy
    ac._handle_reactivation()
    after_tick1 = ac.current_reactivation_strategy

    assert after_tick1 != before, (
        f"strategy should advance on fail within 1 tick ({before} -> {after_tick1})"
    )
    assert ac.reactivation_attempts == 1
    assert ac.nav_state == NavigationState.REACTIVATING

    # Second tick should run the new strategy, not spam-fail the same one
    ac._handle_reactivation()
    assert ac.current_reactivation_strategy == after_tick1
    assert ac.nav_state == NavigationState.REACTIVATING


def test_max_attempts_goes_to_error():
    ac = _make_controller()
    ac.nav_state = NavigationState.REACTIVATING
    ac.current_reactivation_strategy = 0
    ac.reactivation_attempts = ac.max_reactivation_attempts - 1
    ac.reactivation_start_time = time.time() - 4.5
    ac.stuck_position = (1.0, 1.0)

    ac._handle_reactivation()
    assert ac.nav_state == NavigationState.ERROR


def test_sensors_only_ignores_missing_vision():
    ac = _make_controller()
    assert ac.vision_fusion is None
    ac.stuck_position = (1.0, 1.0)
    # Clear ultrasonics but no movement → fail without touching vision
    assert ac._check_if_reactivation_successful() is False
    ac.stuck_position = (0.0, 0.0)  # moved ~1.4m
    assert ac._check_if_reactivation_successful() is True


if __name__ == "__main__":
    test_strategy_advances_past_movement_window()
    test_max_attempts_goes_to_error()
    test_sensors_only_ignores_missing_vision()
    print("PASS: reactivation advance-on-fail")
