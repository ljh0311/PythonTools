"""Shared test configuration for navigation scenarios."""

from dataclasses import dataclass
from typing import Any, Dict


@dataclass
class TestConfig:
    """Configuration for testing"""

    __test__ = False

    map_width: float = 9.7
    map_height: float = 9.7
    grid_size: float = 0.2

    robot_width: float = 0.3
    robot_length: float = 0.4
    max_speed: float = 0.83
    turn_speed: float = 0.3

    comfortable: float = 0.5
    warning: float = 0.3
    critical: float = 0.15

    camera_index: int = 0
    frame_width: int = 640
    frame_height: int = 480
    camera_fps: int = 30
    enable_camera: bool = True

    object_detection_model: str = 'efficientdet.tflite'
    max_detections: int = 5
    detection_threshold: float = 0.25

    ultrasonic_weight: float = 0.6
    visual_weight: float = 0.4

    show_camera_feed: bool = True
    show_detections: bool = True
    show_optical_flow: bool = True
    show_motor_indicators: bool = True


def build_config_dict(config: TestConfig) -> Dict[str, Any]:
    """Build navigation config dict from TestConfig."""
    return {
        'navigation': {
            'grid_size': config.grid_size,
            'map_width': config.map_width,
            'map_height': config.map_height,
        },
        'robot': {
            'width': config.robot_width,
            'length': config.robot_length,
            'max_speed': config.max_speed,
            'turn_speed': config.turn_speed,
            'safety_distances': {
                'comfortable': config.comfortable,
                'warning': config.warning,
                'critical': config.critical,
            },
        },
    }
