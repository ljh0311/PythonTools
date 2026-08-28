"""Multi-channel notifications for robot events (log, API queue, optional TTS/GUI)."""

import json
import threading
import time
from typing import Any, Dict, List, Optional

from loguru import logger


class NotificationService:
    """Dispatches robot notifications to configured channels."""

    def __init__(self, config: dict):
        notify_cfg = config.get("notifications", {})
        self.enabled = notify_cfg.get("enabled", True)
        channels = notify_cfg.get("channels", {})
        self.log_enabled = channels.get("log", True)
        self.api_enabled = channels.get("api", True)
        self.tts_enabled = channels.get("tts", False)
        self.gui_enabled = channels.get("gui_toast", False)
        self._lock = threading.Lock()
        self._history: List[Dict[str, Any]] = []
        self._max_history = notify_cfg.get("max_history", 50)
        self._gui_messages: List[str] = []

    def notify(
        self,
        event_type: str,
        message: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        payload = {
            "event_type": event_type,
            "message": message,
            "timestamp": time.time(),
            "data": data or {},
        }
        if not self.enabled:
            return payload

        if self.log_enabled:
            logger.warning(f"[NOTIFY:{event_type}] {message}")
            if data:
                logger.info(f"Notification data: {json.dumps(data, default=str)}")

        if self.tts_enabled:
            logger.info(f"[TTS stub] {message}")

        with self._lock:
            self._history.append(payload)
            if len(self._history) > self._max_history:
                self._history = self._history[-self._max_history :]
            if self.gui_enabled:
                self._gui_messages.append(message)
                if len(self._gui_messages) > 20:
                    self._gui_messages = self._gui_messages[-20:]

        return payload

    def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._lock:
            return list(self._history[-limit:])

    def get_gui_messages(self) -> List[str]:
        with self._lock:
            return list(self._gui_messages)

    def clear_gui_messages(self) -> None:
        with self._lock:
            self._gui_messages.clear()
