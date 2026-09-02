"""Patrol movement tests — waypoint loops and exploration (sweep on hold)."""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fixtures.navigation_harness import (
    run_headless_exploration,
    run_headless_navigation,
    run_headless_patrol_waypoints,
)


# Typical indoor patrol loop (metres, map coords used by test.py)
PATROL_LOOP = [
    (3.0, 3.0),
    (7.0, 3.0),
    (7.0, 7.0),
    (3.0, 7.0),
]


def test_patrol_single_leg_navigation():
    """Patrol leg: navigate to one room corner."""
    assert run_headless_navigation(start=(1.0, 1.0, 0.0), goal=(8.0, 8.0), max_steps=1200)


def test_patrol_with_obstacle_detour():
    """Patrol leg with obstacle — mirrors test.py mode 2."""
    reached = run_headless_navigation(
        start=(1.0, 5.0, 0.0),
        goal=(9.0, 5.0),
        obstacles=[(5.0, 5.0, 0.35)],
        max_steps=2000,
    )
    assert reached


def test_patrol_waypoint_loop():
    """Visit four corners — patrol loop smoke test."""
    reached, total = run_headless_patrol_waypoints(
        PATROL_LOOP,
        start=(2.5, 2.5, 0.0),
        max_steps_per_leg=900,
    )
    assert total == 4
    assert reached >= 2, f"Expected at least 2/4 waypoints, got {reached}"


def test_patrol_exploration_moves():
    """Exploration mode (test.py mode 3) — robot should travel meaningful distance."""
    moved, distance = run_headless_exploration(
        start=(5.0, 5.0, 0.0),
        max_steps=1200,
        min_distance_m=1.0,
    )
    assert moved, f"Exploration distance too low: {distance:.2f} m"
