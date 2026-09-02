"""TaskBoss — AI task orchestrator using tool registry (no direct motor PWM)."""

import re
import threading
from typing import Any, Dict, Optional

from loguru import logger

from .robot_state import SensorData
from .robo_mind import RobotMind
from .tool_registry import ToolRegistry, build_robot_tools
from .proximity_context import (
    build_proximity_context,
    count_vision_labels,
    proximity_rule_decide,
    sensor_cm_to_m,
)


class TaskBoss:
    """Wires RobotMind to high-level tools instead of raw motor commands."""

    PROXIMITY_THINK_TIMEOUT_S = 2.0

    def __init__(self, config: dict, context: Dict[str, Any], smart_home=None):
        self.config = config
        self.context = context
        self.mind = RobotMind(config)
        self.mind.robot_state = context["robot_state"]
        self.mind.autonomous_controller = context["autonomous_controller"]
        self.mind.sensor_manager = context.get("sensor_manager")
        self.mind.pathfinder = context.get("pathfinder")
        self.mind.vision_fusion = context.get("vision_fusion")
        self.mind.context = context
        self.mind.tool_registry: ToolRegistry = build_robot_tools(context, smart_home)
        self.mind.task_boss = self
        self._lock = threading.Lock()
        self._think_busy = threading.Lock()
        self._last_tool_result: Optional[dict] = None
        self._last_proximity_result: Optional[dict] = None

    @property
    def tools(self) -> ToolRegistry:
        return self.mind.tool_registry

    def register_tool(self, name: str, description: str, handler, parameters=None) -> None:
        self.tools.register_fn(name, description, handler, parameters)

    def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        with self._lock:
            result = self.tools.execute(name, **kwargs)
            self._last_tool_result = result
            return result

    def run_task(self, task: str, sensor_data: Optional[SensorData] = None) -> Dict[str, Any]:
        """Parse LLM output or map natural task to tool calls."""
        mapped = self._map_task_to_tool(task)
        if mapped:
            return self.execute_tool(mapped["tool"], **mapped.get("args", {}))

        if sensor_data is None and self.context.get("sensor_manager"):
            raw = self.context["sensor_manager"].get_sensor_data()
            sensor_data = self._to_sensor_data(raw)

        reasoning = self.mind.think_sync(sensor_data, task)
        tool_call = self._parse_tool_from_llm(reasoning)
        if tool_call:
            return self.execute_tool(tool_call["tool"], **tool_call.get("args", {}))

        return {"success": False, "reasoning": reasoning, "error": "no tool mapped"}

    def handle_proximity(
        self,
        sensor_data: SensorData,
        vision_ctx: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Build proximity context, think (sync + timeout), execute resulting tool.

        Skips if a think is already in progress so the nav loop never freezes.
        """
        if not self._think_busy.acquire(blocking=False):
            return {"success": False, "skipped": "busy", "reason": "proximity think already running"}

        try:
            prox_ctx = self._build_proximity_context(sensor_data, vision_ctx)
            self.mind.set_task("proximity_reaction")
            reasoning = self.mind.think_sync(
                sensor_data,
                task="proximity_reaction",
                proximity_ctx=prox_ctx,
                timeout=self.PROXIMITY_THINK_TIMEOUT_S,
            )
            if reasoning.get("skipped"):
                # Keep nav reactive: offline heuristics if LLM times out / busy path
                pos = getattr(self.mind.robot_state, "position", None)
                reasoning = proximity_rule_decide(prox_ctx, position=pos)
                reasoning["source"] = reasoning.get("source", "proximity_rule_fallback") + "_after_timeout"

            tool_call = self._parse_tool_from_llm(reasoning)
            if not tool_call or not tool_call.get("tool"):
                self._last_proximity_result = {
                    "success": False,
                    "reasoning": reasoning,
                    "proximity_ctx": prox_ctx,
                    "error": "no tool mapped",
                }
                return self._last_proximity_result

            result = self.execute_tool(tool_call["tool"], **tool_call.get("args", {}))
            result["reason"] = reasoning.get("reason", "")
            result["source"] = reasoning.get("source", "")
            result["proximity_ctx"] = prox_ctx
            result["reasoning"] = reasoning
            self._last_proximity_result = result
            logger.info(
                f"Proximity tool={tool_call['tool']} reason={reasoning.get('reason')} "
                f"source={reasoning.get('source')}"
            )
            return result
        finally:
            self._think_busy.release()

    def _build_proximity_context(
        self,
        sensor_data: SensorData,
        vision_ctx: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        labels = {"person": 0, "wall": 0, "furniture": 0, "unknown": 0}
        vision_ctx = vision_ctx or {}

        if vision_ctx.get("vision_labels"):
            labels = {**labels, **vision_ctx["vision_labels"]}
        else:
            obstacles = vision_ctx.get("obstacles")
            scene = vision_ctx.get("scene")
            vf = self.context.get("vision_fusion") or getattr(self.mind, "vision_fusion", None)
            if obstacles is None and vf is not None:
                decision = vf.get_navigation_decision() if hasattr(vf, "get_navigation_decision") else None
                obstacles = getattr(decision, "obstacles", None) if decision else None
                last = vf.get_last_result() if hasattr(vf, "get_last_result") else {}
                scene = scene or last.get("scene")
                if last.get("vision_labels"):
                    labels = {**labels, **last["vision_labels"]}
            if not vision_ctx.get("vision_labels"):
                labels = count_vision_labels(obstacles, scene)

        nav = self.context.get("autonomous_controller")
        nav_state = None
        if nav is not None and hasattr(nav, "nav_state"):
            ns = nav.nav_state
            nav_state = ns.value if hasattr(ns, "value") else str(ns)

        safety = (
            self.config.get("robot", {}).get("safety_distances")
            or {"critical": 15, "warning": 35, "comfortable": 50}
        )
        return build_proximity_context(
            sensor_cm_to_m(sensor_data.ultrasonic_front),
            sensor_cm_to_m(sensor_data.ultrasonic_left),
            sensor_cm_to_m(sensor_data.ultrasonic_right),
            vision_labels=labels,
            nav_state=nav_state,
            current_task=self.mind.current_task,
            safety_cm=safety,
        )

    def _map_task_to_tool(self, task: str) -> Optional[Dict[str, Any]]:
        t = task.lower().strip()
        aliases = {
            "go to kitchen": "go_to_kitchen",
            "kitchen": "go_to_kitchen",
            "go home": "return_to_home",
            "return home": "return_to_home",
            "explore": "start_exploration",
            "stop": "stop",
            "status": "get_status",
            "scan": "scan_surroundings",
        }
        for phrase, tool in aliases.items():
            if phrase in t:
                return {"tool": tool, "args": {}}
        nav = re.search(r"navigate\s+to\s*\(?\s*([\d.]+)\s*,\s*([\d.]+)\s*\)?", t)
        if nav:
            return {"tool": "navigate_to", "args": {"x": float(nav.group(1)), "y": float(nav.group(2))}}
        return None

    def _parse_tool_from_llm(self, reasoning: dict) -> Optional[Dict[str, Any]]:
        """Expect LLM JSON: {tool, args} or legacy {action} mapped to stop."""
        if not isinstance(reasoning, dict):
            return None
        if "tool" in reasoning and reasoning["tool"]:
            return {"tool": reasoning["tool"], "args": reasoning.get("args", {}) or {}}
        action = reasoning.get("action", "")
        legacy_map = {
            "stop": "stop",
            "move_forward": "get_status",
            "move_backward": "get_status",
        }
        if action in legacy_map:
            logger.info(f"Legacy motor action '{action}' redirected to tool layer")
            return {"tool": legacy_map[action], "args": {}}
        return None

    def _to_sensor_data(self, raw: dict) -> SensorData:
        us = raw.get("ultrasonic", {})
        ir = raw.get("infrared", {})
        bump = raw.get("bumper", {})
        return SensorData(
            ultrasonic_front=us.get("front", type("o", (), {"value": 100})()).value if hasattr(us.get("front"), "value") else 100,
            ultrasonic_left=us.get("left", type("o", (), {"value": 100})()).value if hasattr(us.get("left"), "value") else 100,
            ultrasonic_right=us.get("right", type("o", (), {"value": 100})()).value if hasattr(us.get("right"), "value") else 100,
            infrared_left=ir.get("left", False) if isinstance(ir.get("left"), bool) else getattr(ir.get("left"), "value", False),
            infrared_right=ir.get("right", False) if isinstance(ir.get("right"), bool) else getattr(ir.get("right"), "value", False),
            bumper_left=bump.get("left", False) if isinstance(bump.get("left"), bool) else getattr(bump.get("left"), "value", False),
            bumper_right=bump.get("right", False) if isinstance(bump.get("right"), bool) else getattr(bump.get("right"), "value", False),
        )

    def get_status(self) -> dict:
        return {
            "tools": self.tools.list_tools(),
            "last_result": self._last_tool_result,
            "last_proximity": self._last_proximity_result,
            "current_task": self.mind.current_task,
            "pending_resolution": self.mind.blocked_path_handler.get_pending_state(),
            "notifications": self.mind.notifier.get_history(limit=10),
        }

    def shutdown(self) -> None:
        self.mind.shutdown()
