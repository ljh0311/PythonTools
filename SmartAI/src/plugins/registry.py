"""Plugin registry — register movement and analysis plugins by name."""

from typing import Dict, Optional, Type

from .base import AnalysisPlugin, MovementPlugin

_movement: Dict[str, MovementPlugin] = {}
_analysis: Dict[str, AnalysisPlugin] = {}


def register_movement(plugin: MovementPlugin) -> None:
  _movement[plugin.name] = plugin


def register_analysis(plugin: AnalysisPlugin) -> None:
  _analysis[plugin.name] = plugin


def get_movement(name: str) -> Optional[MovementPlugin]:
  return _movement.get(name)


def get_analysis(name: str) -> Optional[AnalysisPlugin]:
  return _analysis.get(name)


def list_movement_plugins() -> list:
  return list(_movement.keys())


def list_analysis_plugins() -> list:
  return list(_analysis.keys())


def register_movement_class(name: str, cls: Type[MovementPlugin]) -> None:
  register_movement(cls())

def register_analysis_class(name: str, cls: Type[AnalysisPlugin]) -> None:
  register_analysis(cls())
