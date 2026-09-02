"""Register default movement and analysis plugins."""

from .analysis.scene_analysis import SceneAnalysisPlugin
from .movement.path_following import ExplorationPlugin, PathFollowingPlugin, ReturnHomePlugin
from .registry import register_analysis, register_movement


def register_default_plugins() -> None:
    register_movement(PathFollowingPlugin())
    register_movement(ExplorationPlugin())
    register_movement(ReturnHomePlugin())
    register_analysis(SceneAnalysisPlugin())
