"""Offline proximity reaction via RobotMind / TaskBoss (Approach B)."""

from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.core.proximity_context import (
    build_proximity_context,
    proximity_rule_decide,
    count_vision_labels,
)
from src.core.robot_state import SensorData, RobotState
from src.core.robo_mind import RobotMind
from src.core.task_boss import TaskBoss


def _cfg():
    return {
        "robot": {
            "name": "Test",
            "model": "llama3.1:8b",
            "safety_distances": {"critical": 15, "warning": 35, "comfortable": 50},
            "width": 30,
        },
        "navigation": {"base_location": [500, 500], "grid_size": 10},
        "locations": {"kitchen": [600, 400]},
        "notifications": {"enabled": False, "channels": {"log": True}},
    }


def test_rule_person_front_stops():
    ctx = build_proximity_context(
        0.25, 1.0, 1.0,
        vision_labels={"person": 1, "wall": 0, "furniture": 0, "unknown": 0},
        safety_cm={"critical": 15, "warning": 35, "comfortable": 50},
    )
    d = proximity_rule_decide(ctx)
    assert d["tool"] == "stop"
    assert "person" in d["reason"]
    assert "front" in d["reason"]


def test_rule_wall_reroutes():
    ctx = build_proximity_context(
        0.40, 0.80, 1.2,
        vision_labels={"person": 0, "wall": 2, "furniture": 0, "unknown": 0},
        safety_cm={"critical": 15, "warning": 35, "comfortable": 50},
    )
    d = proximity_rule_decide(ctx)
    assert d["tool"] == "try_alternate_route"
    assert "wall" in d["reason"]


def test_rule_furniture_reroute_or_offset():
    close = build_proximity_context(
        0.30, 0.90, 0.70,
        vision_labels={"person": 0, "wall": 0, "furniture": 1, "unknown": 0},
        safety_cm={"critical": 15, "warning": 35, "comfortable": 50},
    )
    d = proximity_rule_decide(close)
    assert d["tool"] == "try_alternate_route"
    assert "furniture" in d["reason"]

    farther = build_proximity_context(
        0.45, 0.90, 0.70,
        vision_labels={"person": 0, "wall": 0, "furniture": 1, "unknown": 0},
        safety_cm={"critical": 15, "warning": 35, "comfortable": 50},
    )
    d2 = proximity_rule_decide(farther, position=type("P", (), {"x": 100.0, "y": 200.0})())
    assert d2["tool"] == "navigate_to"
    assert "furniture" in d2["reason"]
    assert "x" in d2["args"] and "y" in d2["args"]


def test_rule_unknown_close_stops():
    ctx = build_proximity_context(
        0.28, 1.0, 1.0,
        vision_labels={"person": 0, "wall": 0, "furniture": 0, "unknown": 0},
        safety_cm={"critical": 15, "warning": 35, "comfortable": 50},
    )
    d = proximity_rule_decide(ctx)
    assert d["tool"] == "stop"
    assert "unknown" in d["reason"]


def test_count_vision_labels_walls():
    class Obs:
        class_name = "chair"

    class Wall:
        element_type = type("E", (), {"value": "wall"})()

    counts = count_vision_labels([Obs()], {"regions": [Wall()]})
    assert counts["furniture"] == 1
    assert counts["wall"] == 1


def test_mind_offline_proximity_fallback():
    mind = RobotMind(_cfg())
    mind._ollama_available = False
    mind._probe_ollama = lambda: False  # type: ignore
    mind.robot_state = RobotState(_cfg())
    prox = build_proximity_context(
        0.22, 1.0, 0.9,
        vision_labels={"person": 1, "wall": 0, "furniture": 0, "unknown": 0},
        safety_cm=_cfg()["robot"]["safety_distances"],
    )
    sensor = SensorData(ultrasonic_front=22, ultrasonic_left=100, ultrasonic_right=90)
    result = mind.think_sync(sensor, task="proximity_reaction", proximity_ctx=prox)
    assert result["tool"] == "stop"
    assert "person" in result["reason"]
    assert "proximity_rule_fallback" in result.get("source", "")


def test_task_boss_handle_proximity_offline():
    config = _cfg()
    robot_state = RobotState(config)
    ac = MagicMock()
    ac.nav_state = type("NS", (), {"value": "following_path"})()
    ac.replan_attempts = 0
    ctx = {
        "config": config,
        "robot_state": robot_state,
        "autonomous_controller": ac,
        "sensor_manager": None,
        "pathfinder": MagicMock(),
        "vision_fusion": None,
        "motor_controller": MagicMock(),
    }
    boss = TaskBoss(config, ctx, smart_home=None)
    boss.mind._ollama_available = False
    boss.mind._probe_ollama = lambda: False  # type: ignore

    # Avoid executing real stop (AC.stop) — stub tools
    executed = []

    def _capture(name, **kwargs):
        executed.append((name, kwargs))
        return {"success": True, "tool": name}

    boss.execute_tool = _capture  # type: ignore

    sensor = SensorData(ultrasonic_front=30, ultrasonic_left=80, ultrasonic_right=120)
    result = boss.handle_proximity(
        sensor,
        vision_ctx={"vision_labels": {"person": 0, "wall": 1, "furniture": 0, "unknown": 0}},
    )
    assert result.get("success") is True or result.get("tool") or executed
    assert executed, f"expected tool execution, got {result}"
    tool_name, _ = executed[0]
    assert tool_name == "try_alternate_route"
    assert "wall" in (result.get("reason") or "")
    assert "front" in (result.get("reason") or "") or "left" in (result.get("reason") or "")


def test_task_boss_skips_when_busy():
    config = _cfg()
    robot_state = RobotState(config)
    ctx = {
        "config": config,
        "robot_state": robot_state,
        "autonomous_controller": MagicMock(nav_state=type("NS", (), {"value": "idle"})()),
        "sensor_manager": None,
        "pathfinder": MagicMock(),
        "vision_fusion": None,
        "motor_controller": MagicMock(),
    }
    boss = TaskBoss(config, ctx)
    boss.mind._ollama_available = False
    boss.mind._probe_ollama = lambda: False  # type: ignore
    assert boss._think_busy.acquire(blocking=False)
    try:
        sensor = SensorData(ultrasonic_front=25, ultrasonic_left=100, ultrasonic_right=100)
        out = boss.handle_proximity(sensor)
        assert out.get("skipped") == "busy"
    finally:
        boss._think_busy.release()


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:
                failed += 1
                print(f"FAIL {name}: {e}")
    total = sum(1 for k, v in globals().items() if k.startswith("test_") and callable(v))
    print(f"\n{total - failed}/{total} passed")
    raise SystemExit(1 if failed else 0)
