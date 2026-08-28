"""Vision-based path decisions — person/dynamic obstacle detection via camera fusion."""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

import numpy as np
from loguru import logger


@dataclass
class VisionThinkContext:
    """Vision fusion output consumed by RobotMind.think()."""

    action: str = "clear"
    risk_level: str = "low"
    reason: str = ""
    obstacle_count: int = 0
    persons_in_path: int = 0
    min_ttc: Optional[float] = None
    fusion_result: Optional[Dict[str, Any]] = None
    obstacles: Optional[List[Any]] = None


class VisionPathHandler:
    """Maps VisionFusion / SimVisionFusion decisions to RobotMind tool actions."""

    ACTION_TOOLS = {
        "stop": "stop",
        "slow": "scan_surroundings",
        "wait": "wait_for_door",
        "reroute": "try_alternate_route",
    }

    def get_vision_fusion(self, mind) -> Any:
        vf = getattr(mind, "vision_fusion", None)
        if vf:
            return vf
        ac = getattr(mind, "autonomous_controller", None)
        if ac and getattr(ac, "vision_fusion", None):
            return ac.vision_fusion
        tb = getattr(mind, "task_boss", None)
        if tb and hasattr(tb, "context"):
            return tb.context.get("vision_fusion")
        ctx = getattr(mind, "context", None)
        if isinstance(ctx, dict):
            return ctx.get("vision_fusion")
        return None

    def get_camera_frame(self, mind) -> Optional[np.ndarray]:
        frame = getattr(mind, "last_camera_frame", None)
        if frame is not None:
            return frame
        tb = getattr(mind, "task_boss", None)
        if tb and hasattr(tb, "context"):
            frame = tb.context.get("last_camera_frame")
            if frame is not None:
                return frame
        ctx = getattr(mind, "context", None)
        if isinstance(ctx, dict):
            return ctx.get("last_camera_frame")
        sm = getattr(mind, "sensor_manager", None)
        if sm and hasattr(sm, "get_camera_frame"):
            return sm.get_camera_frame()
        return None

    def process_vision(self, mind) -> VisionThinkContext:
        """Run vision fusion on latest frame or consume cached fusion decision."""
        empty = VisionThinkContext()
        vf = self.get_vision_fusion(mind)
        if not vf or not getattr(vf, "enabled", True):
            return empty

        frame = self.get_camera_frame(mind)
        fusion_result: Optional[Dict[str, Any]] = None

        if frame is not None and hasattr(vf, "process_frame"):
            try:
                fusion_result = vf.process_frame(frame)
                logger.debug(f"Vision process_frame: {fusion_result}")
            except Exception as e:
                logger.warning(f"Vision process_frame failed: {e}")

        if not hasattr(vf, "get_navigation_decision"):
            if fusion_result:
                return self._from_fusion_result(fusion_result)
            return empty

        decision = vf.get_navigation_decision()
        if fusion_result is None and hasattr(vf, "get_last_result"):
            fusion_result = vf.get_last_result()

        obstacles = getattr(decision, "obstacles", None) or []
        persons = [
            o for o in obstacles
            if getattr(o, "class_name", "").lower() == "person"
        ]
        ttcs = [
            o.time_to_collision for o in obstacles
            if getattr(o, "time_to_collision", None) is not None
        ]

        return VisionThinkContext(
            action=getattr(decision, "action", "clear"),
            risk_level=getattr(decision, "risk_level", "low"),
            reason=getattr(decision, "reason", "") or (
                fusion_result.get("reason", "") if fusion_result else ""
            ),
            obstacle_count=len(obstacles) or (
                fusion_result.get("obstacle_count", 0) if fusion_result else 0
            ),
            persons_in_path=len(persons),
            min_ttc=min(ttcs) if ttcs else None,
            fusion_result=fusion_result,
            obstacles=obstacles,
        )

    def _from_fusion_result(self, result: Dict[str, Any]) -> VisionThinkContext:
        return VisionThinkContext(
            action=result.get("decision", "clear"),
            risk_level=result.get("risk_level", "low"),
            reason=result.get("reason", ""),
            obstacle_count=result.get("obstacle_count", 0),
            fusion_result=result,
        )

    def should_intercept(self, ctx: VisionThinkContext) -> bool:
        return ctx.action in self.ACTION_TOOLS and ctx.action != "clear"

    def handle_vision_obstacle(self, ctx: VisionThinkContext) -> Dict[str, Any]:
        """Convert vision fusion decision to a RobotMind tool response."""
        tool = self.ACTION_TOOLS.get(ctx.action, "stop")
        parts = [f"Vision: {ctx.reason or ctx.action}"]
        if ctx.persons_in_path:
            parts.append(f"{ctx.persons_in_path} person(s) in path")
        if ctx.min_ttc is not None:
            parts.append(f"TTC={ctx.min_ttc:.1f}s")
        if ctx.obstacle_count and not ctx.persons_in_path:
            parts.append(f"{ctx.obstacle_count} dynamic obstacle(s)")

        reason = " — ".join(parts)
        logger.info(
            f"Vision decision: action={ctx.action} risk={ctx.risk_level} -> tool={tool}"
        )
        return {
            "tool": tool,
            "args": {},
            "reason": reason,
            "vision_action": ctx.action,
            "vision_risk": ctx.risk_level,
            "source": "vision_fusion",
        }

    def format_for_llm(self, ctx: VisionThinkContext) -> str:
        if ctx.action == "clear" and not ctx.fusion_result:
            return ""
        lines = [
            f"Vision Fusion: action={ctx.action}, risk={ctx.risk_level}",
        ]
        if ctx.reason:
            lines.append(f"  Reason: {ctx.reason}")
        if ctx.obstacle_count:
            lines.append(f"  Dynamic obstacles: {ctx.obstacle_count}")
        if ctx.persons_in_path:
            lines.append(f"  Persons in path: {ctx.persons_in_path}")
        if ctx.min_ttc is not None:
            lines.append(f"  Time-to-collision: {ctx.min_ttc:.1f}s")
        return "\n".join(lines)
