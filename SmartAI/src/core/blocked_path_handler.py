"""Blocked-path detection, user notification, and resolution drafting."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from loguru import logger

from .notification_service import NotificationService
from .robot_state import SensorData


@dataclass
class PendingResolution:
    event_id: str
    event_type: str
    message: str
    resolutions: List[Dict[str, Any]]
    created_at: float = field(default_factory=time.time)
    selected: Optional[str] = None


class BlockedPathHandler:
    """Detect blocked paths and prepare resolution options for the user."""

    def __init__(self, config: dict, notifier: Optional[NotificationService] = None):
        self.config = config
        self.notifier = notifier or NotificationService(config)
        self._pending: Optional[PendingResolution] = None
        self._event_counter = 0

    def detect_blocked_path(
        self,
        sensor_data: SensorData,
        nav_state: Optional[str] = None,
        replan_failures: int = 0,
        task: Optional[str] = None,
    ) -> bool:
        """Rule-based blocked-path detection (vision/sensors/stuck/replan failure)."""
        front_cm = sensor_data.ultrasonic_front
        front_blocked = front_cm < 35.0
        bumpers = sensor_data.bumper_left or sensor_data.bumper_right
        ir_blocked = sensor_data.infrared_left or sensor_data.infrared_right
        nav_stuck = nav_state in ("stuck", "error", "backtracking", "replanning_route")
        replan_exhausted = replan_failures >= 2

        door_like = front_blocked and (ir_blocked or bumpers) and front_cm < 25.0
        corridor_blocked = front_blocked and nav_stuck
        going_to_room = task and any(
            kw in task.lower() for kw in ("room", "bedroom", "door", "kitchen", "navigate")
        )

        if door_like or corridor_blocked or (going_to_room and replan_exhausted and front_blocked):
            return True
        return False

    def draft_resolutions(self, context: str = "closed_door") -> List[Dict[str, Any]]:
        if context == "closed_door":
            return [
                {"id": "wait_for_door", "label": "Wait for door to open", "tool": "wait_for_door"},
                {"id": "alternate_route", "label": "Try alternate route", "tool": "try_alternate_route"},
                {"id": "notify_open_door", "label": "Notify user to open door", "tool": "notify_user_open_door"},
                {"id": "return_home", "label": "Return to home base", "tool": "return_to_home"},
            ]
        return [
            {"id": "alternate_route", "label": "Try alternate route", "tool": "try_alternate_route"},
            {"id": "return_home", "label": "Return to home base", "tool": "return_to_home"},
            {"id": "stop", "label": "Stop and wait", "tool": "stop"},
        ]

    def handle_blocked_path(
        self,
        sensor_data: SensorData,
        task: Optional[str] = None,
        nav_state: Optional[str] = None,
        replan_failures: int = 0,
    ) -> Dict[str, Any]:
        context = "closed_door" if sensor_data.ultrasonic_front < 25.0 else "blocked_path"
        message = (
            "Path to your room is blocked — closed door detected ahead."
            if context == "closed_door"
            else "Navigation path is blocked; unable to proceed."
        )
        resolutions = self.draft_resolutions(context)

        self._event_counter += 1
        event_id = f"blocked_{self._event_counter}"
        self._pending = PendingResolution(
            event_id=event_id,
            event_type="blocked_path",
            message=message,
            resolutions=resolutions,
        )

        notify_payload = self.notifier.notify(
            "blocked_path",
            message,
            {"event_id": event_id, "resolutions": resolutions, "task": task},
        )

        logger.info(f"Blocked path resolutions drafted: {[r['id'] for r in resolutions]}")
        return {
            "tool": "handle_blocked_path",
            "args": {"event_id": event_id},
            "reason": message,
            "event_id": event_id,
            "resolutions": resolutions,
            "notification": notify_payload,
        }

    def get_pending_state(self) -> Optional[Dict[str, Any]]:
        if not self._pending:
            return None
        p = self._pending
        return {
            "event_id": p.event_id,
            "event_type": p.event_type,
            "message": p.message,
            "resolutions": p.resolutions,
            "created_at": p.created_at,
            "selected": p.selected,
        }

    def select_resolution(self, resolution_id: str) -> Optional[Dict[str, Any]]:
        if not self._pending:
            return None
        for r in self._pending.resolutions:
            if r["id"] == resolution_id:
                self._pending.selected = resolution_id
                return r
        return None

    def clear_pending(self) -> None:
        self._pending = None
