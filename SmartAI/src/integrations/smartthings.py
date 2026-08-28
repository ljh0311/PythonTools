"""Samsung SmartThings REST adapter (Personal Access Token).

API: https://developer.smartthings.com/docs/api/public
Auth: Bearer PAT in Authorization header.
Endpoints: GET /devices, POST /devices/{deviceId}/commands
"""

from typing import Any, Dict, List, Optional

import requests
from loguru import logger

from ..core.tool_registry import RobotTool
from .base import SmartHomeAdapter


class SmartThingsAdapter(SmartHomeAdapter):
    name = "smartthings"

    def __init__(self, config: dict):
        cfg = config.get("integrations", {}).get("smartthings", {})
        self.enabled = cfg.get("enabled", False)
        self.token = cfg.get("personal_access_token") or ""
        self.base_url = cfg.get("api_base", "https://api.smartthings.com/v1")
        self.default_light = cfg.get("default_light_device_id", "")
        self._mock = cfg.get("mock_mode", True)
        self._session = requests.Session()
        if self.token:
            self._session.headers["Authorization"] = f"Bearer {self.token}"

    def is_available(self) -> bool:
        if self._mock or not self.enabled:
            return False
        return bool(self.token)

    def _request(self, method: str, path: str, json_body: Optional[dict] = None) -> Dict[str, Any]:
        if not self.is_available():
            return self._mock_response(path, json_body)
        url = f"{self.base_url}{path}"
        try:
            r = self._session.request(method, url, json=json_body, timeout=10)
            r.raise_for_status()
            return r.json() if r.content else {"ok": True}
        except Exception as e:
            logger.warning(f"SmartThings API error: {e}")
            return {"error": str(e), "mock": True, **self._mock_response(path, json_body)}

    def _mock_response(self, path: str, body: Optional[dict]) -> Dict[str, Any]:
        if "/commands" in path:
            return {"mock": True, "executed": body, "state": "on"}
        if "/devices/" in path and "/status" in path:
            return {"mock": True, "switch": "on", "level": 80}
        return {"mock": True, "devices": [{"deviceId": "mock-light-1", "name": "Living Room Light"}]}

    def list_devices(self) -> Dict[str, Any]:
        return self._request("GET", "/devices")

    def get_device_state(self, device_id: str) -> Dict[str, Any]:
        did = device_id or self.default_light
        return self._request("GET", f"/devices/{did}/status")

    def turn_on(self, device_id: str) -> Dict[str, Any]:
        did = device_id or self.default_light
        body = {"commands": [{"component": "main", "capability": "switch", "command": "on"}]}
        return self._request("POST", f"/devices/{did}/commands", body)

    def turn_off(self, device_id: str) -> Dict[str, Any]:
        did = device_id or self.default_light
        body = {"commands": [{"component": "main", "capability": "switch", "command": "off"}]}
        return self._request("POST", f"/devices/{did}/commands", body)

    def get_tools(self) -> List[RobotTool]:
        adapter = self
        return [
            RobotTool(
                "turn_on_light",
                "Turn on a SmartThings light (device_id optional, uses default)",
                lambda device_id="": adapter.turn_on(device_id),
                {"device_id": "optional SmartThings device ID"},
            ),
            RobotTool(
                "turn_off_light",
                "Turn off a SmartThings light",
                lambda device_id="": adapter.turn_off(device_id),
                {"device_id": "optional SmartThings device ID"},
            ),
            RobotTool(
                "get_device_state",
                "Get SmartThings device state",
                lambda device_id="": adapter.get_device_state(device_id),
                {"device_id": "optional SmartThings device ID"},
            ),
            RobotTool(
                "list_smart_devices",
                "List SmartThings devices",
                lambda: adapter.list_devices(),
            ),
        ]
