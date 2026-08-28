"""Enhanced 2D pygame visualizer with side HUD panel (Tesla/Xiaomi-style test cockpit)."""

import math
from typing import Any, Dict, List, Optional, Tuple

import pygame

from .hud_state import HudState

try:
    import numpy as np
except ImportError:
    np = None


class EnhancedPygameVisualizer:
    """
    Split-view 2D nav: map + status panel.
    Hotkeys (IR-SIM inspired): Space pause, R reset signal, Esc quit.
    """

    PANEL_WIDTH = 320
    MAP_MARGIN = 40

    def __init__(self, config):
        self.config = config
        self.hud = HudState()
        self.map_width_px = 880
        self.screen_height = 720
        self.screen_width = self.map_width_px + self.PANEL_WIDTH
        self.paused = False
        self.reset_requested = False
        self._display_ready = False
        self.screen = None
        self.clock = None
        self.font = None
        self.font_lg = None
        self.font_sm = None

        self._init_colors()
        self._init_state(config)
        self._camera_surface: Optional[pygame.Surface] = None
        self._status_info: Dict[str, Any] = {}
        self._motor = (0.0, 0.0, 0.0, 0.0)

    def _ensure_display(self):
        """Open pygame window on first draw — avoids freeze during terminal menu."""
        if self._display_ready:
            return
        pygame.init()
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("SmartAI Navigation — Enhanced 2D")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 22)
        self.font_lg = pygame.font.Font(None, 28)
        self.font_sm = pygame.font.Font(None, 18)
        self._display_ready = True
        self.draw()  # paint immediately so window is not black

    def _init_colors(self):
        self.C = {
            "bg": (245, 247, 250),
            "panel": (32, 36, 48),
            "panel_text": (230, 234, 242),
            "accent": (0, 180, 216),
            "warn": (255, 183, 77),
            "danger": (239, 83, 80),
            "ok": (102, 187, 106),
            "map_grid": (220, 224, 230),
            "robot": (66, 133, 244),
            "path": (52, 168, 83),
            "goal": (234, 67, 53),
            "lidar": (156, 39, 176),
            "obstacle": (96, 125, 139),
        }

    def _init_state(self, config):
        self.robot_pos = (0.0, 0.0)
        self.robot_angle = 0.0
        self.goal_pos: Optional[Tuple[float, float]] = None
        self.path_points: List[Tuple[float, float]] = []
        self.path_history: List[List[Tuple[float, float]]] = []
        self.refine_hud: Dict[str, Any] = {}
        self.obstacles: List[Tuple[float, float, float]] = []
        self.grid = None
        self.explored_cells = set()
        self.lidar_rays: List[Tuple[float, float, float, float]] = []
        self.scale_x = (self.map_width_px - 2 * self.MAP_MARGIN) / config.map_width
        self.scale_y = (self.screen_height - 2 * self.MAP_MARGIN) / config.map_height

    def world_to_screen(self, x: float, y: float) -> Tuple[int, int]:
        sx = int(x * self.scale_x + self.MAP_MARGIN)
        sy = int(self.screen_height - self.MAP_MARGIN - y * self.scale_y)
        return sx, sy

    def update_robot_position(self, x: float, y: float, orientation: float):
        self.robot_pos = (x, y)
        self.robot_angle = orientation

    def update_path(self, path):
        self.path_points = [(p.x, p.y) for p in path]

    def set_path_history(self, history: List[List[Tuple[float, float]]]):
        """Previous planned/driven paths for refinement demo overlays."""
        self.path_history = list(history or [])

    def set_refine_hud(self, info: Dict[str, Any]):
        self.refine_hud = dict(info or {})

    def update_goal(self, x: float, y: float):
        self.goal_pos = (x, y)

    def add_obstacle(self, x: float, y: float, radius: float = 0.2):
        self.obstacles.append((x, y, radius))

    def update_grid(self, grid):
        self.grid = grid

    def update_explored(self, explored_cells, grid_size):
        self.explored_cells = explored_cells

    def update_lidar_rays(self, robot_x, robot_y, robot_theta, sensor_distances, sensor_angles, lidar_scan=None):
        self.lidar_rays = []
        if lidar_scan:
            for angle_deg, dist in lidar_scan:
                angle_rad = math.radians(angle_deg) + robot_theta
                ex = robot_x + dist * math.cos(angle_rad)
                ey = robot_y + dist * math.sin(angle_rad)
                self.lidar_rays.append((robot_x, robot_y, ex, ey))

    def update_learning_data_visualization(self, learning_data, grid_size):
        self._learning = learning_data
        self._grid_size = grid_size

    def update_status_text(self, status: Dict[str, Any]):
        self._status_info = status
        self.hud.update_from_status(status)
        rm = status.get("robotmind") or {}
        if rm:
            self.hud.robotmind_thought = rm.get("thought", self.hud.robotmind_thought)
            self.hud.robotmind_decision = rm.get("decision", self.hud.robotmind_decision)
            self.hud.robotmind_resolutions = rm.get("resolutions", self.hud.robotmind_resolutions)
        self.hud.vision_action = status.get("vision_action", self.hud.vision_action)

    def update_camera_feed(self, frame, detections=None, flow_vectors=None):
        if frame is None:
            return
        try:
            import cv2
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            rgb = cv2.resize(rgb, (280, 157))
            surf = pygame.surfarray.make_surface(rgb.swapaxes(0, 1))
            self._camera_surface = surf
        except Exception:
            self._camera_surface = None

    def update_motor_indicators(self, left_speed, right_speed, left_target, right_target):
        self._motor = (left_speed, right_speed, left_target, right_target)
        self.hud.motor_left = left_speed
        self.hud.motor_right = right_speed

    def handle_events(self):
        if not self._display_ready:
            return True
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                if event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                    self.hud.paused = self.paused
                if event.key == pygame.K_r:
                    self.reset_requested = True
        return True

    @property
    def is_paused(self) -> bool:
        return self.paused

    def consume_reset_request(self) -> bool:
        if self.reset_requested:
            self.reset_requested = False
            return True
        return False

    def redraw(self, navmesh_edges=None, grid_size=None):
        self.draw()

    def draw(self):
        self._ensure_display()
        self.screen.fill(self.C["bg"])
        self._draw_map_area()
        self._draw_learning_overlays()
        self._draw_panel()
        pygame.display.flip()

    def _draw_map_area(self):
        map_rect = pygame.Rect(0, 0, self.map_width_px, self.screen_height)
        pygame.draw.rect(self.screen, (255, 255, 255), map_rect)
        if self.grid is not None and np is not None:
            rows, cols = self.grid.shape
            for i in range(rows):
                for j in range(cols):
                    x = (j + 0.5) * self.config.grid_size
                    y = (i + 0.5) * self.config.grid_size
                    sx, sy = self.world_to_screen(x, y)
                    if self.grid[i, j] == 2:
                        pygame.draw.circle(self.screen, self.C["obstacle"], (sx, sy), 4)
        for i, j in self.explored_cells:
            x = (j + 0.5) * self.config.grid_size
            y = (i + 0.5) * self.config.grid_size
            sx, sy = self.world_to_screen(x, y)
            pygame.draw.circle(self.screen, self.C["map_grid"], (sx, sy), 2)
        for x, y, r in self.obstacles:
            sx, sy = self.world_to_screen(x, y)
            pygame.draw.circle(self.screen, self.C["obstacle"], (sx, sy), max(3, int(r * self.scale_x)))
        for ray in self.lidar_rays:
            a = self.world_to_screen(ray[0], ray[1])
            b = self.world_to_screen(ray[2], ray[3])
            pygame.draw.line(self.screen, self.C["lidar"], a, b, 1)
        if self.path_history:
            n = len(self.path_history)
            for idx, hist in enumerate(self.path_history):
                if len(hist) < 2:
                    continue
                # Older runs fade; newest history entry brighter amber
                t = (idx + 1) / max(n, 1)
                color = (int(40 + 180 * t), int(80 + 100 * t), 40)
                width = 1 if idx < n - 1 else 2
                pts = [self.world_to_screen(x, y) for x, y in hist]
                pygame.draw.lines(self.screen, color, False, pts, width)
        if len(self.path_points) > 1:
            pts = [self.world_to_screen(x, y) for x, y in self.path_points]
            pygame.draw.lines(self.screen, self.C["path"], False, pts, 3)
        if self.goal_pos:
            gx, gy = self.world_to_screen(self.goal_pos[0], self.goal_pos[1])
            pygame.draw.circle(self.screen, self.C["goal"], (gx, gy), 10, 0)
        self._draw_robot()
        self._draw_refine_banner()
        pygame.draw.line(self.screen, self.C["map_grid"], (self.map_width_px, 0), (self.map_width_px, self.screen_height), 2)

    def _draw_refine_banner(self):
        info = getattr(self, "refine_hud", None) or {}
        if not info:
            return
        run = info.get("run", "?")
        pts = info.get("waypoints", "?")
        length = info.get("length_m", "?")
        turns = info.get("turns", "?")
        note = info.get("note", "")
        line = f"Run {run}  pts={pts}  len={length}m  turns={turns}"
        if note:
            line = f"{line}  |  {note}"
        font = pygame.font.SysFont("consolas", 16)
        surf = font.render(line, True, (230, 230, 230))
        bg = pygame.Surface((surf.get_width() + 12, surf.get_height() + 8), pygame.SRCALPHA)
        bg.fill((20, 24, 32, 180))
        self.screen.blit(bg, (12, 12))
        self.screen.blit(surf, (18, 16))

    def _draw_robot(self):
        sx, sy = self.world_to_screen(self.robot_pos[0], self.robot_pos[1])
        rw = max(8, int(self.config.robot_width * self.scale_x))
        rl = max(10, int(self.config.robot_length * self.scale_y))
        surf = pygame.Surface((rw, rl), pygame.SRCALPHA)
        pygame.draw.rect(surf, self.C["robot"], (0, 0, rw, rl), border_radius=3)
        # Front caster dot
        pygame.draw.circle(surf, (255, 255, 255), (rw // 2, 2), 3)
        rot = pygame.transform.rotate(surf, -math.degrees(self.robot_angle))
        rect = rot.get_rect(center=(sx, sy))
        self.screen.blit(rot, rect)
        ex = sx + 20 * math.cos(self.robot_angle)
        ey = sy - 20 * math.sin(self.robot_angle)
        pygame.draw.line(self.screen, self.C["warn"], (sx, sy), (ex, ey), 2)

    def _draw_learning_overlays(self):
        if not hasattr(self, "_learning"):
            return
        ld = self._learning
        gs = getattr(self, "_grid_size", self.config.grid_size)
        for loc in ld.get("stuck_locations", []):
            if isinstance(loc, dict):
                x, y = loc.get("x", 0), loc.get("y", 0)
            else:
                x, y = float(loc[0]), float(loc[1])
            sx, sy = self.world_to_screen(x, y)
            pygame.draw.rect(self.screen, self.C["danger"], (sx - 6, sy - 6, 12, 12), 2)

    def _draw_panel(self):
        px = self.map_width_px
        panel = pygame.Rect(px, 0, self.PANEL_WIDTH, self.screen_height)
        pygame.draw.rect(self.screen, self.C["panel"], panel)
        y = 12
        y = self._text(px + 12, y, "SMARTAI TEST", self.font_lg, self.C["accent"])
        y = self._text(px + 12, y + 4, f"Mode: {self.hud.test_mode or '—'}", self.font_sm)
        state_color = self.C["ok"] if self.hud.nav_state in ("idle", "reached_goal") else self.C["accent"]
        y = self._text(px + 12, y + 8, f"State: {self.hud.nav_state}", self.font, state_color)
        if self.hud.paused:
            y = self._text(px + 12, y, "⏸ PAUSED", self.font, self.C["warn"])
        y = self._text(px + 12, y + 4, f"Pos ({self.robot_pos[0]:.2f}, {self.robot_pos[1]:.2f})", self.font_sm)
        y = self._text(px + 12, y, f"Speed {self.hud.linear_speed:.2f} m/s", self.font_sm)
        y = self._section(px, y + 8, "Sensors (m)")
        for name, val in self.hud.sensors.items():
            col = self.C["danger"] if val < 0.25 else self.C["panel_text"]
            y = self._text(px + 16, y, f"  {name}: {val:.2f}", self.font_sm, col)
        y = self._section(px, y + 6, "Rear drive motors")
        y = self._text(px + 16, y, f"  L: {self.hud.motor_left:.0f}  R: {self.hud.motor_right:.0f}", self.font_sm)
        y = self._section(px, y + 6, "RobotMind")
        thought = (self.hud.robotmind_thought or "—")[:42]
        y = self._text(px + 16, y, thought, self.font_sm, self.C["warn"])
        dec = (self.hud.robotmind_decision or self.hud.vision_action or "—")[:42]
        y = self._text(px + 16, y, f"→ {dec}", self.font_sm, self.C["accent"])
        if self._camera_surface:
            y = self._section(px, y + 8, "Camera")
            self.screen.blit(self._camera_surface, (px + 12, y))
            y += 162
        y = self._section(px, y + 4, "Keys: Space pause · R reset · Esc quit")

    def _section(self, px: int, y: int, title: str) -> int:
        pygame.draw.line(self.screen, (60, 65, 80), (px + 10, y), (px + self.PANEL_WIDTH - 10, y), 1)
        return self._text(px + 12, y + 6, title, self.font_sm, (160, 168, 180))

    def _text(self, x: int, y: int, text: str, font, color=None) -> int:
        color = color or self.C["panel_text"]
        surf = font.render(str(text), True, color)
        self.screen.blit(surf, (x, y))
        return y + surf.get_height() + 2

    def quit(self):
        if self._display_ready:
            pygame.quit()
