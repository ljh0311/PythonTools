"""Google Home / Device Access API adapter.

Uses Google Home Device Access (SDM) REST API for supported devices.
Docs: https://developers.home.google.com/cloud-to-cloud/get-started
OAuth client credentials + refresh token required for production.
Falls back to mock when credentials missing.
"""

from typing import Any, Dict, List, Optional

import requests
from loguru import logger

from ..core.tool_registry import RobotTool
from .base import SmartHomeAdapter


class GoogleHomeAdapter(SmartHomeAdapter):
    name = "google_home"

    def __init__(self, config: dict):
        cfg = config.get("integrations", {}).get("google_home", {})
        self.enabled = cfg.get("enabled", False)
        self.project_id = cfg.get("project_id", "")
        self.client_id = cfg.get("client_id", "")
        self.client_secret = cfg.get("client_secret", "")
        self.refresh_token = cfg.get("refresh_token", "")
        self.default_device = cfg.get("default_device_id", "")
        self._mock = cfg.get("mock_mode", True)
        self._access_token: Optional[str] = None
        self._session = requests.Session()

    def is_available(self) -> bool:
        if self._mock or not self.enabled:
            return False
        return bool(self.project_id and self.refresh_token)

    def _ensure_token(self) -> bool:
        if self._access_token:
            return True
        if not self.refresh_token:
            return False
        try:
            r = requests.post(
                "https://oauth2.googleapis.com/token",
                data={
                    "client_id": self.client_id,
                    "client_secret": self.client_secret,
                    "refresh_token": self.refresh_token,
                    "grant_type": "refresh_token",
                },
                timeout=10,
            )
            r.raise_for_status()
            self._access_token = r.json().get("access_token")
            self._session.headers["Authorization"] = f"Bearer {self._access_token}"
            return bool(self._access_token)
        except Exception as e:
            logger.warning(f"Google Home token refresh failed: {e}")
            return False

    def _request(self, method: str, path: str, json_body: Optional[dict] = None) -> Dict[str, Any]:
        if not self.is_available() or not self._ensure_token():
            return self._mock_response(path, json_body)
        url = f"https://smartdevicemanagement.googleapis.com/v1/{path}"
        try:
            r = self._session.request(method, url, json=json_body, timeout=10)
            r.raise_for_status()
            return r.json() if r.content else {"ok": True}
        except Exception as e:
            logger.warning(f"Google Home API error: {e}")
            return {"error": str(e), "mock": True, **self._mock_response(path, json_body)}

    def _mock_response(self, path: str, body: Optional[dict]) -> Dict[str, Any]:
        if "execute" in path:
            return {"mock": True, "executed": body, "state": "ON"}
        return {"mock": True, "devices": [{"name": "mock-google-light", "type": "action.devices.types.LIGHT"}]}

    def list_devices(self) -> Dict[str, Any]:
        return self._request("GET", f"enterprises/{self.project_id}/devices")

    def get_device_state(self, device_id: str) -> Dict[str, Any]:
        did = device_id or self.default_device
        return self._request("GET", f"enterprises/{self.project_id}/devices/{did}")

    def turn_on(self, device_id: str) -> Dict[str, Any]:
        return self._execute(device_id, "action.devices.commands.OnOff", {"on": True})

    def turn_off(self, device_id: str) -> Dict[str, Any]:
        return self._execute(device_id, "action.devices.commands.OnOff", {"on": False})

    def _execute(self, device_id: str, cmd: str, params: dict) -> Dict[str, Any]:
        did = device_id or self.default_device
        body = {"command": cmd, "params": params}
        path = f"enterprises/{self.project_id}/devices/{did}:executeCommand"
        return self._request("POST", path, body)

    def get_tools(self) -> List[RobotTool]:
        adapter = self
        return [
            RobotTool(
                "google_turn_on_light",
                "Turn on a Google Home linked light",
                lambda device_id="": adapter.turn_on(device_id),
                {"device_id": "optional Google device ID"},
            ),
            RobotTool(
                "google_turn_off_light",
                "Turn off a Google Home linked light",
                lambda device_id="": adapter.turn_off(device_id),
            ),
            RobotTool(
                "google_get_device_state",
                "Get Google Home device state",
                lambda device_id="": adapter.get_device_state(device_id),
            ),
        ]
