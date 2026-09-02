"""Smart home integration base."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from ..core.tool_registry import RobotTool


class SmartHomeAdapter(ABC):
  """Base adapter for smart home platforms."""

  name: str = "smart_home"

  @abstractmethod
  def is_available(self) -> bool: ...

  @abstractmethod
  def get_device_state(self, device_id: str) -> Dict[str, Any]: ...

  @abstractmethod
  def turn_on(self, device_id: str) -> Dict[str, Any]: ...

  @abstractmethod
  def turn_off(self, device_id: str) -> Dict[str, Any]: ...

  @abstractmethod
  def get_tools(self) -> List[RobotTool]: ...
