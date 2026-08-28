"""Smart home bridge — aggregates adapters and optional MQTT bus."""

from typing import Any, Dict, List, Optional

from loguru import logger

from ..core.tool_registry import RobotTool
from .google_home import GoogleHomeAdapter
from .smartthings import SmartThingsAdapter


class SmartHomeBridge:
    """Unified smart home access for RobotMind tools."""

    def __init__(self, config: dict):
        self.config = config
        self.adapters = []
        integ = config.get("integrations", {})

        if integ.get("smartthings", {}).get("enabled", False):
            self.adapters.append(SmartThingsAdapter(config))
        elif integ.get("smartthings", {}).get("mock_mode", True):
            self.adapters.append(SmartThingsAdapter(config))

        if integ.get("google_home", {}).get("enabled", False):
            self.adapters.append(GoogleHomeAdapter(config))
        elif integ.get("google_home", {}).get("mock_mode", True):
            self.adapters.append(GoogleHomeAdapter(config))

        self._mqtt = None
        mqtt_cfg = integ.get("mqtt", {})
        if mqtt_cfg.get("enabled", False):
            self._init_mqtt(mqtt_cfg)

    def _init_mqtt(self, mqtt_cfg: dict) -> None:
        try:
            import paho.mqtt.client as mqtt
            self._mqtt = mqtt.Client()
            host = mqtt_cfg.get("host", "localhost")
            port = mqtt_cfg.get("port", 1883)
            self._mqtt.connect(host, port, 60)
            self._mqtt.loop_start()
            logger.info(f"MQTT bus connected to {host}:{port}")
        except Exception as e:
            logger.warning(f"MQTT unavailable: {e}")
            self._mqtt = None

    def publish(self, topic: str, payload: str) -> bool:
        if not self._mqtt:
            return False
        try:
            self._mqtt.publish(topic, payload)
            return True
        except Exception:
            return False

    def get_tools(self) -> List[RobotTool]:
        tools: List[RobotTool] = []
        for adapter in self.adapters:
            tools.extend(adapter.get_tools())
        return tools

    def get_status(self) -> Dict[str, Any]:
        return {
            "adapters": [a.name for a in self.adapters],
            "available": {a.name: a.is_available() for a in self.adapters},
            "mqtt": self._mqtt is not None,
        }
