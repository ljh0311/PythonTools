"""Shared HUD state for test visualization dashboards."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class HudState:
    """Live telemetry consumed by pygame HUD and Dear PyGui dashboard."""

    nav_state: str = "idle"
    position: tuple = (0.0, 0.0)
    orientation_deg: float = 0.0
    linear_speed: float = 0.0
    waypoints: int = 0
    sensors: Dict[str, float] = field(default_factory=dict)
    motor_left: float = 0.0
    motor_right: float = 0.0
    robotmind_thought: str = ""
    robotmind_decision: str = ""
    robotmind_resolutions: List[str] = field(default_factory=list)
    vision_action: str = ""
    stuck_count: int = 0
    test_mode: str = ""
    paused: bool = False
    log_lines: List[str] = field(default_factory=list)

    def update_from_status(self, status: Dict[str, Any]) -> None:
        """Populate from NavigationTester status_info dict."""
        pos = status.get("position", {})
        self.nav_state = status.get("navigation_state", self.nav_state)
        self.position = (pos.get("x", 0), pos.get("y", 0))
        self.orientation_deg = pos.get("theta", 0) * 57.2958 if abs(pos.get("theta", 0)) <= 6.28 else pos.get("theta", 0)
        speed = status.get("speed", {})
        self.linear_speed = speed.get("linear", 0) if isinstance(speed, dict) else float(speed or 0)
        self.waypoints = status.get("total_waypoints", 0)
        sensors = status.get("sensors", {})
        if isinstance(sensors, dict):
            self.sensors = {
                "front": sensors.get("front", sensors.get("ultrasonic_front", 0)),
                "left": sensors.get("left", sensors.get("ultrasonic_left", 0)),
                "right": sensors.get("right", sensors.get("ultrasonic_right", 0)),
            }

    def append_log(self, line: str, max_lines: int = 12) -> None:
        self.log_lines.append(line)
        if len(self.log_lines) > max_lines:
            self.log_lines = self.log_lines[-max_lines:]
