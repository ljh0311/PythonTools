"""3D home environment visualizer — wraps existing World3D for test.py."""

import math
from typing import Any, Dict, List, Optional, Tuple

from loguru import logger

from ..simulation.world_3d import World3D, WorldObject, ObjectType


class World3DVisualizer:
    """
    OpenGL 3D view of home floor plan synced from 2D navigation.
    Map coords: test.py (x, y) → 3D (x, height, z=y).
    Window opens lazily on first redraw (not during terminal menu).
    """

    def __init__(self, config):
        self.config = config
        self.world: Optional[World3D] = None
        self._world_ready = False
        self._obstacle_ids: List[Tuple[float, float]] = []
        self.robot_pos = (0.0, 0.0)
        self.robot_angle = 0.0
        self.goal_pos: Optional[Tuple[float, float]] = None

    def _ensure_world(self):
        if self._world_ready:
            return
        self.world = World3D(width=1000, height=720)
        self._world_ready = True
        self._sync_robot_to_world()

    def _sync_robot_to_world(self):
        if self.world and self.world.robot:
            self.world.robot.position = (
                self.robot_pos[0],
                0.12,
                self.robot_pos[1],
            )
            self.world.robot.orientation = self.robot_angle

    def update_robot_position(self, x: float, y: float, orientation: float):
        self.robot_pos = (x, y)
        self.robot_angle = orientation
        self._sync_robot_to_world()

    def update_path(self, path):
        pass

    def update_goal(self, x: float, y: float):
        self.goal_pos = (x, y)

    def add_obstacle(self, x: float, y: float, radius: float = 0.2):
        self._ensure_world()
        key = (round(x, 2), round(y, 2))
        if key in self._obstacle_ids:
            return
        self._obstacle_ids.append(key)
        h = max(0.4, radius * 3)
        self.world.add_object(
            WorldObject(
                obj_type=ObjectType.OBSTACLE,
                position=(x, h / 2, y),
                dimensions=(radius * 2, h, radius * 2),
                color=(120, 130, 140),
            )
        )

    def update_grid(self, grid):
        pass

    def update_explored(self, explored_cells, grid_size):
        pass

    def update_lidar_rays(self, *args, **kwargs):
        pass

    def update_learning_data_visualization(self, learning_data, grid_size):
        pass

    def update_status_text(self, status: Dict[str, Any]):
        pass

    def update_camera_feed(self, frame, detections=None, flow_vectors=None):
        pass

    def update_motor_indicators(self, *args):
        pass

    def handle_events(self):
        if not self._world_ready:
            return True
        import pygame

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                return False
            if event.type == pygame.MOUSEMOTION and event.buttons[0]:
                if self.world.last_mouse_pos:
                    dx = event.pos[0] - self.world.last_mouse_pos[0]
                    dy = event.pos[1] - self.world.last_mouse_pos[1]
                    self.world.camera.phi += dx * self.world.mouse_sensitivity
                    self.world.camera.theta = max(
                        0.1,
                        min(math.pi - 0.1, self.world.camera.theta + dy * self.world.mouse_sensitivity),
                    )
                self.world.last_mouse_pos = event.pos
            if event.type == pygame.MOUSEBUTTONUP:
                self.world.last_mouse_pos = None
        return True

    def redraw(self, navmesh_edges=None, grid_size=None):
        self._ensure_world()
        self.world.render()

    def quit(self):
        if self._world_ready:
            import pygame

            pygame.quit()
