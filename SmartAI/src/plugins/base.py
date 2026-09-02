"""Logic plugin interfaces for movement and analysis."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class MovementPlugin(ABC):
  """High-level movement behaviors (path follow, exploration)."""

  name: str = "movement"

  @abstractmethod
  def start(self, context: Dict[str, Any], **kwargs) -> bool: ...

  @abstractmethod
  def stop(self, context: Dict[str, Any]) -> bool: ...

  @abstractmethod
  def tick(self, context: Dict[str, Any]) -> None: ...


class AnalysisPlugin(ABC):
  """Perception / scene analysis plugins."""

  name: str = "analysis"

  @abstractmethod
  def process(self, context: Dict[str, Any], frame: Optional[Any] = None) -> Dict[str, Any]: ...

  @abstractmethod
  def get_status(self) -> Dict[str, Any]: ...
