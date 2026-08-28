"""Default analysis plugins."""

from typing import Any, Dict, Optional

from ..base import AnalysisPlugin


class SceneAnalysisPlugin(AnalysisPlugin):
  name = "scene_analysis"

  def __init__(self):
    self._fusion = None
    self._last = {}

  def bind_vision_fusion(self, fusion) -> None:
    self._fusion = fusion

  def process(self, context: Dict[str, Any], frame: Optional[Any] = None) -> Dict[str, Any]:
    if self._fusion is None:
      return {"available": False}
    if frame is not None:
      self._last = self._fusion.process_frame(frame)
    else:
      self._last = self._fusion.get_last_result()
    return self._last

  def get_status(self) -> Dict[str, Any]:
    return {"plugin": self.name, "last_result": self._last}
