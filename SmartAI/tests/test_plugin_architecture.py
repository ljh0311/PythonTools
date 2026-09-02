#!/usr/bin/env python3
"""Tests for plug-and-play architecture, tools, vision fusion, and integrations."""

import os
import sys
import yaml

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.hardware.factory import create_hardware_transport, register_transport
from src.hardware.transport import HardwareTransport
from src.plugins.defaults import register_default_plugins
from src.plugins import registry as plugin_registry
from src.core.tool_registry import build_robot_tools
from src.core.robot_state import RobotState, RobotMode
from src.hardware.motor_controller import MotorController
from src.hardware.sensor_manager import SensorManager
from src.navigation.pathfinder import Pathfinder
from src.navigation.autonomous_controller import AutonomousController
from src.vision.vision_fusion import VisionFusion
from src.integrations.bridge import SmartHomeBridge


def load_config():
    with open(os.path.join(os.path.dirname(__file__), "..", "config", "robot_config.yaml")) as f:
        return yaml.safe_load(f)


def test_hardware_transport():
    config = load_config()
    transport = create_hardware_transport(config)
    assert transport.get_backend_name() == "gpio"
    assert transport.motors is not None
    assert transport.sensors is not None


def test_plugin_registry():
    register_default_plugins()
    assert "path_following" in plugin_registry.list_movement_plugins()
    assert "scene_analysis" in plugin_registry.list_analysis_plugins()


def test_tool_registry():
    config = load_config()
    robot_state = RobotState(config)
    motor = MotorController(config)
    sensors = SensorManager(config)
    pf = Pathfinder(config)
    ac = AutonomousController(robot_state, motor, sensors, pf)
    ctx = {
        "config": config,
        "robot_state": robot_state,
        "motor_controller": motor,
        "sensor_manager": sensors,
        "pathfinder": pf,
        "autonomous_controller": ac,
    }
    bridge = SmartHomeBridge(config)
    tools = build_robot_tools(ctx, bridge)
    names = tools.get_tool_names()
    assert "navigate_to" in names
    assert "go_to_kitchen" in names
    assert "turn_on_light" in names
    result = tools.execute("get_status")
    assert result.get("success") is True


def test_vision_fusion_decision():
    config = load_config()
    pf = Pathfinder(config)
    vf = VisionFusion(config, pf)
    frame = np.zeros((480, 640, 3), dtype=np.uint8)
    result = vf.process_frame(frame)
    assert "enabled" in result
    assert vf.get_navigation_decision().action in ("clear", "slow", "stop", "reroute")


def test_smart_home_mock():
    config = load_config()
    bridge = SmartHomeBridge(config)
    tools = {t.name: t for t in bridge.get_tools()}
    on = tools["turn_on_light"].handler()
    assert on.get("mock") is True or "error" not in on
