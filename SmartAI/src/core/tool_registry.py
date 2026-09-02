"""RobotMind tool registry — high-level tools, never raw motor PWM."""

from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

from loguru import logger

from .robot_state import RobotMode


@dataclass
class RobotTool:
    name: str
    description: str
    handler: Callable[..., Dict[str, Any]]
    parameters: Optional[Dict[str, str]] = None


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, RobotTool] = {}

    def register(self, tool: RobotTool) -> None:
        self._tools[tool.name] = tool
        logger.debug(f"Registered tool: {tool.name}")

    def register_fn(self, name: str, description: str, handler: Callable, parameters: Optional[Dict] = None) -> None:
        self.register(RobotTool(name, description, handler, parameters))

    def execute(self, name: str, **kwargs) -> Dict[str, Any]:
        tool = self._tools.get(name)
        if not tool:
            return {"success": False, "error": f"Unknown tool: {name}"}
        try:
            result = tool.handler(**kwargs)
            return {"success": True, "tool": name, **(result or {})}
        except Exception as e:
            logger.error(f"Tool {name} failed: {e}")
            return {"success": False, "tool": name, "error": str(e)}

    def list_tools(self) -> List[Dict[str, Any]]:
        return [
            {"name": t.name, "description": t.description, "parameters": t.parameters or {}}
            for t in self._tools.values()
        ]

    def get_tool_names(self) -> List[str]:
        return list(self._tools.keys())

    def get_schemas_for_llm(self) -> str:
        lines = []
        for t in self._tools.values():
            params = ", ".join(f"{k}: {v}" for k, v in (t.parameters or {}).items())
            lines.append(f"- {t.name}({params}): {t.description}")
        return "\n".join(lines)


def build_robot_tools(context: Dict[str, Any], smart_home=None) -> ToolRegistry:
    """Register default robot + optional smart-home tools."""
    registry = ToolRegistry()
    config = context.get("config", {})
    locations = config.get("locations", {})

    def _nav(x: float, y: float) -> dict:
        ctrl = context["autonomous_controller"]
        state = context["robot_state"]
        state.set_mode(RobotMode.AUTONOMOUS)
        ok = ctrl.navigate_to(x, y)
        return {"navigating": ok, "target": {"x": x, "y": y}}

    registry.register_fn(
        "navigate_to",
        "Navigate to world coordinates (cm)",
        lambda x, y: _nav(float(x), float(y)),
        {"x": "float cm", "y": "float cm"},
    )

    registry.register_fn(
        "go_to_kitchen",
        "Navigate to kitchen location from config",
        lambda: _nav(*locations.get("kitchen", [600, 400])),
    )

    registry.register_fn(
        "return_to_home",
        "Return to base/home position",
        lambda: _nav(*config.get("navigation", {}).get("base_location", [500, 500])),
    )

    registry.register_fn(
        "start_exploration",
        "Start autonomous exploration mode",
        lambda: {"started": context["autonomous_controller"].start_exploration()},
    )

    registry.register_fn(
        "stop",
        "Stop navigation and motors",
        lambda: _stop_all(context),
    )

    registry.register_fn(
        "get_status",
        "Get robot system status summary",
        lambda: {"status": _full_status(context)},
    )

    registry.register_fn(
        "scan_surroundings",
        "Trigger vision scene scan (uses last camera frame if available)",
        lambda: _scan_surroundings(context),
    )

    def _blocked_path_status() -> dict:
        mind = context.get("task_boss")
        if mind and hasattr(mind, "mind"):
            return {"pending": mind.mind.blocked_path_handler.get_pending_state()}
        return {"pending": None}

    registry.register_fn(
        "handle_blocked_path",
        "Notify user of blocked path and return drafted resolutions",
        lambda event_id="": _blocked_path_status(),
    )

    registry.register_fn(
        "wait_for_door",
        "Wait for blocked door to open (no motor commands)",
        lambda: {"waiting": True, "action": "wait_for_door"},
    )

    registry.register_fn(
        "try_alternate_route",
        "Attempt alternate route around blocked path",
        lambda: _try_alternate_route(context),
    )

    registry.register_fn(
        "notify_user_open_door",
        "Notify user to open the door blocking the path",
        lambda: _notify_open_door(context),
    )

    if smart_home:
        for tool_def in smart_home.get_tools():
            registry.register(tool_def)

    return registry


def _stop_all(context: dict) -> dict:
    context["autonomous_controller"].stop()
    context["robot_state"].set_mode(RobotMode.IDLE)
    return {"stopped": True}


def _full_status(context: dict) -> dict:
    mc = context.get("motor_controller")
    out = {
        "robot": context["robot_state"].get_status_summary(),
        "navigation": context["autonomous_controller"].get_status(),
        "motors": mc.get_status() if mc and hasattr(mc, "get_status") else {},
    }
    vf = context.get("vision_fusion")
    if vf:
        out["vision"] = vf.get_status()
    return out


def _scan_surroundings(context: dict) -> dict:
    frame = context.get("last_camera_frame")
    vf = context.get("vision_fusion")
    if vf and frame is not None:
        return vf.process_frame(frame)
    analysis = context.get("scene_analysis")
    if analysis:
        return analysis.process(context, frame)
    return {"scanned": False, "reason": "no camera frame or vision fusion"}


def _try_alternate_route(context: dict) -> dict:
    ctrl = context["autonomous_controller"]
    ctrl.replan_attempts = 0
    ok = ctrl._attempt_global_replan() if hasattr(ctrl, "_attempt_global_replan") else False
    if ok:
        from ..navigation.autonomous_controller import NavigationState
        ctrl.nav_state = NavigationState.PLANNING
    return {"alternate_route": ok}


def _notify_open_door(context: dict) -> dict:
    task_boss = context.get("task_boss")
    if task_boss and hasattr(task_boss, "mind"):
        payload = task_boss.mind.notifier.notify(
            "door_blocked",
            "Please open the door — robot cannot reach your room.",
            {},
        )
        return {"notified": True, "notification": payload}
    return {"notified": False}
