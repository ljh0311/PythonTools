"""Default movement plugins delegating to AutonomousController."""

from typing import Any, Dict

from loguru import logger

from ..base import MovementPlugin


class PathFollowingPlugin(MovementPlugin):
  name = "path_following"

  def start(self, context: Dict[str, Any], **kwargs) -> bool:
    ctrl = context.get("autonomous_controller")
    x, y = kwargs.get("x"), kwargs.get("y")
    if ctrl is None or x is None or y is None:
      return False
    return ctrl.navigate_to(float(x), float(y))

  def stop(self, context: Dict[str, Any]) -> bool:
    ctrl = context.get("autonomous_controller")
    if ctrl:
      ctrl.stop()
      return True
    return False

  def tick(self, context: Dict[str, Any]) -> None:
    pass


class ExplorationPlugin(MovementPlugin):
  name = "exploration"

  def start(self, context: Dict[str, Any], **kwargs) -> bool:
    ctrl = context.get("autonomous_controller")
    if ctrl is None:
      return False
    return ctrl.start_exploration()

  def stop(self, context: Dict[str, Any]) -> bool:
    ctrl = context.get("autonomous_controller")
    if ctrl:
      ctrl.stop_exploration()
      return True
    return False

  def tick(self, context: Dict[str, Any]) -> None:
    pass


class ReturnHomePlugin(MovementPlugin):
  name = "return_home"

  def start(self, context: Dict[str, Any], **kwargs) -> bool:
    config = context.get("config", {})
    base = config.get("navigation", {}).get("base_location", [500, 500])
    ctrl = context.get("autonomous_controller")
    if ctrl is None:
      return False
    logger.info(f"Return home to ({base[0]}, {base[1]})")
    return ctrl.navigate_to(float(base[0]), float(base[1]))

  def stop(self, context: Dict[str, Any]) -> bool:
    return PathFollowingPlugin().stop(context)

  def tick(self, context: Dict[str, Any]) -> None:
    pass
