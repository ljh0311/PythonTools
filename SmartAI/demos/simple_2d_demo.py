# -*- coding: utf-8 -*-
"""
Enhanced 2D Robot Simulation Demo with Floor Plan Editor
Simulates the same platform as main.py with proper RobotState, MotorController, and SensorManager integration
"""

import pygame
import sys
import time
import math
import json
import os
import numpy as np
from loguru import logger
from enum import Enum
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

# Add the src directory to the path
sys.path.append("src")

from src.core.robot_state import RobotState, RobotMode, Position
from src.hardware.motor_controller import MotorController
from src.hardware.sensor_manager import SensorManager, SensorReading
from src.navigation.pathfinder import Pathfinder
from src.navigation.autonomous_controller import AutonomousController
from src.core.floor_plan_types import ObjectType, FloorPlanObject, create_default_floor_plan, load_floor_plan_from_json, save_floor_plan_to_json

# Scaling and zoom constants
PIXELS_PER_METER = 40  # Default scale: 40 pixels per meter
MIN_ZOOM = 0.25        # Minimum zoom (25% of original)
MAX_ZOOM = 4.0         # Maximum zoom (400% of original)
ZOOM_STEP = 0.25       # Zoom increment/decrement step

# Global zoom state
current_zoom = 1.0

def get_scale():
    """Get current scale factor (pixels per meter)"""
    return PIXELS_PER_METER * current_zoom

def zoom_in():
    """Zoom in by one step"""
    global current_zoom
    current_zoom = min(MAX_ZOOM, current_zoom + ZOOM_STEP)
    logger.info(f"Zoom: {current_zoom:.2f}x")

def zoom_out():
    """Zoom out by one step"""
    global current_zoom
    current_zoom = max(MIN_ZOOM, current_zoom - ZOOM_STEP)
    logger.info(f"Zoom: {current_zoom:.2f}x")

def reset_zoom():
    """Reset zoom to default"""
    global current_zoom
    current_zoom = 1.0
    logger.info("Zoom reset to 1.0x")


class SimulatedMotorController(MotorController):
    """Simulated motor controller that tracks wheel speeds for visualization"""
    
    def __init__(self, config):
        super().__init__(config)
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.is_running = False
    
    def set_speeds(self, left: float, right: float):
        """Override to track speeds for simulation"""
        super().set_speeds(left, right)
        self.left_speed = left
        self.right_speed = right
        self.is_running = True
    
    def stop_motors(self):
        """Override to track stop state"""
        super().stop_motors()
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.is_running = False
    
    def emergency_stop(self):
        """Override to track emergency stop"""
        super().emergency_stop()
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.is_running = False


class SimulatedSensorManager(SensorManager):
    """Simulated sensor manager that provides realistic sensor readings based on environment"""
    
    def __init__(self, config):
        super().__init__(config)
        self.floor_plan_objects = []
        self.robot_pose = (0.0, 0.0, 0.0)  # x, y, theta
        self.sensor_angles = {
            'front': 0.0,
            'left': math.pi / 2,
            'right': -math.pi / 2,
            'back': math.pi
        }
        self.max_range = 2.0  # meters

    def set_floor_plan_objects(self, objects: List[FloorPlanObject]):
        """Set the floor plan objects for sensor simulation"""
        self.floor_plan_objects = objects

    def set_robot_pose(self, x: float, y: float, theta: float):
        """Update robot pose for sensor simulation"""
        self.robot_pose = (x, y, theta)

    def _distance_to_obstacle(self, angle_offset: float) -> float:
        """Calculate distance to nearest obstacle in given direction"""
        x, y, theta = self.robot_pose
        angle = theta + angle_offset
        min_dist = self.max_range
        
        for obj in self.floor_plan_objects:
            if not obj.collision:
                continue
            
            # Use rotation if present
            rot = getattr(obj, 'rotation', 0.0)
            distance = self._ray_rect_intersection(
                (x, y), (math.cos(angle), math.sin(angle)), 
                obj.position, obj.dimensions, rot
            )
            if distance is not None and distance < min_dist:
                min_dist = distance
        
        # Add some noise to simulate real sensor
        noise = np.random.normal(0, 0.02)  # 2cm standard deviation
        return max(0.1, min_dist + noise)

    def _ray_rect_intersection(self, ray_origin, ray_direction, rect_center, rect_size, rotation=0.0):
        """Calculate intersection between ray and rotated rectangle"""
        # If rotation is 0, use axis-aligned AABB intersection
        if abs(rotation) < 1e-6:
            rect_min = (rect_center[0] - rect_size[0]/2, rect_center[1] - rect_size[1]/2)
            rect_max = (rect_center[0] + rect_size[0]/2, rect_center[1] + rect_size[1]/2)
            tmin = -float('inf')
            tmax = float('inf')
            for i in range(2):
                origin = ray_origin[i]
                direction = ray_direction[i]
                min_b = rect_min[i]
                max_b = rect_max[i]
                if abs(direction) < 1e-8:
                    if origin < min_b or origin > max_b:
                        return None
                else:
                    t1 = (min_b - origin) / direction
                    t2 = (max_b - origin) / direction
                    t_near = min(t1, t2)
                    t_far = max(t1, t2)
                    tmin = max(tmin, t_near)
                    tmax = min(tmax, t_far)
                    if tmin > tmax or tmax < 0:
                        return None
            if tmin < 0:
                tmin = tmax
                if tmin < 0:
                    return None
            return tmin
        
        # For rotated objects, transform ray into object's local frame
        angle = math.radians(-rotation)
        ox, oy = ray_origin[0] - rect_center[0], ray_origin[1] - rect_center[1]
        local_origin = (
            ox * math.cos(angle) - oy * math.sin(angle),
            ox * math.sin(angle) + oy * math.cos(angle)
        )
        dx, dy = ray_direction
        local_dir = (
            dx * math.cos(angle) - dy * math.sin(angle),
            dx * math.sin(angle) + dy * math.cos(angle)
        )
        rect_min = (-rect_size[0]/2, -rect_size[1]/2)
        rect_max = (rect_size[0]/2, rect_size[1]/2)
        tmin = -float('inf')
        tmax = float('inf')
        for i in range(2):
            origin = local_origin[i]
            direction = local_dir[i]
            min_b = rect_min[i]
            max_b = rect_max[i]
            if abs(direction) < 1e-8:
                if origin < min_b or origin > max_b:
                    return None
            else:
                t1 = (min_b - origin) / direction
                t2 = (max_b - origin) / direction
                t_near = min(t1, t2)
                t_far = max(t1, t2)
                tmin = max(tmin, t_near)
                tmax = min(tmax, t_far)
                if tmin > tmax or tmax < 0:
                    return None
        if tmin < 0:
            tmin = tmax
            if tmin < 0:
                return None
        return tmin

    def get_sensor_data(self) -> Dict:
        """Override to provide simulated sensor data"""
        readings = {}
        for name, angle in self.sensor_angles.items():
            dist = self._distance_to_obstacle(angle)
            readings[name] = SensorReading(value=dist, timestamp=time.time(), valid=True)
        
        return {
            'ultrasonic': readings,
            'infrared': {'left': False, 'right': False},
            'bumper': {'left': False, 'right': False}
        }


class RobotVisualizer:
    """Visualizes the robot state in Pygame"""
    
    def __init__(self, robot_state: RobotState, sensor_manager: SimulatedSensorManager):
        self.robot_state = robot_state
        self.sensor_manager = sensor_manager
        self.robot_size = 0.25  # 25cm radius for visualization
        
    def draw(self, screen, offset_x=0, offset_y=0):
        """Draw the robot based on RobotState"""
        # Get current scale
        scale = get_scale()
        
        # Get robot position from RobotState
        position = self.robot_state.get_position()
        screen_x = offset_x + position.x * scale
        screen_y = offset_y + position.y * scale
        
        # Robot dimensions: 50cm x 50cm (0.5m x 0.5m)
        robot_width = 0.5 * scale
        robot_height = 0.5 * scale
        
        # Calculate rectangle corners for the robot
        half_width = robot_width / 2
        half_height = robot_height / 2
        
        # Calculate the four corners of the rectangle
        corners = [
            # Front left
            (screen_x + half_width * math.cos(position.theta - math.pi/2) - half_height * math.cos(position.theta),
             screen_y + half_width * math.sin(position.theta - math.pi/2) - half_height * math.sin(position.theta)),
            # Front right
            (screen_x + half_width * math.cos(position.theta + math.pi/2) - half_height * math.cos(position.theta),
             screen_y + half_width * math.sin(position.theta + math.pi/2) - half_height * math.sin(position.theta)),
            # Back right
            (screen_x + half_width * math.cos(position.theta + math.pi/2) + half_height * math.cos(position.theta),
             screen_y + half_width * math.sin(position.theta + math.pi/2) + half_height * math.sin(position.theta)),
            # Back left
            (screen_x + half_width * math.cos(position.theta - math.pi/2) + half_height * math.cos(position.theta),
             screen_y + half_width * math.sin(position.theta - math.pi/2) + half_height * math.sin(position.theta))
        ]
        
        # Draw filled rectangle in light blue color
        pygame.draw.polygon(screen, (100, 150, 255), corners)
        # Draw black outline around the rectangle with 2-pixel thickness
        pygame.draw.polygon(screen, (0, 0, 0), corners, 2)
        
        # Draw a red line extending from robot center to show facing direction
        end_x = screen_x + 0.75 * scale * math.cos(position.theta)
        end_y = screen_y + 0.75 * scale * math.sin(position.theta)
        pygame.draw.line(screen, (255, 0, 0), (screen_x, screen_y), (end_x, end_y), 3)
        
        # Draw sensor indicators
        sensor_colors = {
            'front': (255, 0, 0),   # Red
            'back': (0, 255, 0),    # Green
            'left': (0, 0, 255),    # Blue
            'right': (255, 255, 0)  # Yellow
        }
        
        # Draw sensor indicators at robot edges
        for sensor_name, angle_offset in self.sensor_manager.sensor_angles.items():
            sensor_angle = position.theta + angle_offset
            sensor_x = screen_x + half_width * 1.2 * math.cos(sensor_angle)
            sensor_y = screen_y + half_width * 1.2 * math.sin(sensor_angle)
            
            # Draw sensor dot
            pygame.draw.circle(screen, sensor_colors[sensor_name], 
                             (int(sensor_x), int(sensor_y)), 3)
            
            # Draw sensor reading line if obstacle detected
            sensor_data = self.sensor_manager.get_sensor_data()
            ultrasonic_readings = sensor_data.get('ultrasonic', {})
            if sensor_name in ultrasonic_readings:
                reading = ultrasonic_readings[sensor_name].value
                if reading < self.sensor_manager.max_range:
                    end_x = sensor_x + reading * scale * math.cos(sensor_angle)
                    end_y = sensor_y + reading * scale * math.sin(sensor_angle)
                    pygame.draw.line(screen, sensor_colors[sensor_name], 
                                   (sensor_x, sensor_y), (end_x, end_y), 2)


def draw_sensor_readings(screen, sensor_manager: SimulatedSensorManager, x, y):
    """Draw sensor readings panel"""
    font = pygame.font.Font(None, 24)
    
    # Draw background
    panel_width = 200
    panel_height = 120
    pygame.draw.rect(screen, (240, 240, 240), (x, y, panel_width, panel_height))
    pygame.draw.rect(screen, (0, 0, 0), (x, y, panel_width, panel_height), 2)
    
    # Draw title
    title = font.render("Sensor Readings", True, (0, 0, 0))
    screen.blit(title, (x + 10, y + 10))
    
    # Get sensor data
    sensor_data = sensor_manager.get_sensor_data()
    ultrasonic_readings = sensor_data.get('ultrasonic', {})
    
    # Draw sensor values
    sensor_colors = {
        'front': (255, 0, 0),
        'back': (0, 255, 0),
        'left': (0, 0, 255),
        'right': (255, 255, 0)
    }
    
    y_offset = 35
    for sensor_name, reading in ultrasonic_readings.items():
        color = sensor_colors.get(sensor_name, (0, 0, 0))
        text = f"{sensor_name.capitalize()}: {reading.value:.2f}m"
        text_surface = font.render(text, True, color)
        screen.blit(text_surface, (x + 10, y + y_offset))
        y_offset += 20


def get_camera_view_surface(robot_state: RobotState, floor_plan, width=320, height=240, fov=90, view_distance=10):
    """
    Simulate a surveillance camera by rendering a cropped, forward-facing region in front of the robot.
    Returns a pygame.Surface.
    """
    # Create a surface for the camera view
    camera_surface = pygame.Surface((width, height))
    camera_surface.fill((220, 220, 220))

    # Camera parameters
    scale = get_scale()
    position = robot_state.get_position()
    robot_x, robot_y = position.x, position.y
    robot_angle = position.theta
    fov_rad = math.radians(fov)
    half_fov = fov_rad / 2

    # Draw objects in camera view
    for obj in floor_plan.objects:
        # Transform object position to robot's local frame
        dx = obj.position[0] - robot_x
        dy = obj.position[1] - robot_y
        # Rotate to robot's frame
        local_x = dx * math.cos(-robot_angle) - dy * math.sin(-robot_angle)
        local_y = dx * math.sin(-robot_angle) + dy * math.cos(-robot_angle)
        # Only draw objects in front of robot and within FOV
        angle_to_obj = math.atan2(local_y, local_x)
        if local_x > 0 and abs(angle_to_obj) < half_fov and local_x < view_distance:
            # Project to camera surface
            px = int(width / 2 + (local_y / (view_distance * math.tan(half_fov))) * (width / 2))
            py = int(height - (local_x / view_distance) * height)
            obj_w = max(2, int(obj.dimensions[0] * scale * width / (view_distance * scale)))
            obj_h = max(2, int(obj.dimensions[1] * scale * height / (view_distance * scale)))
            rect = pygame.Rect(px - obj_w // 2, py - obj_h // 2, obj_w, obj_h)
            pygame.draw.rect(camera_surface, obj.color, rect)
            pygame.draw.rect(camera_surface, (0, 0, 0), rect, 1)
    
    # Draw a triangle for the robot's nose (bottom center)
    pygame.draw.polygon(camera_surface, (100, 150, 255), [
        (width // 2, height - 5),
        (width // 2 - 8, height),
        (width // 2 + 8, height)
    ])
    return camera_surface


def draw_camera_panel(screen, robot_state: RobotState, floor_plan, x, y, width=320, height=240):
    """Draw the camera view panel on the main screen."""
    cam_surf = get_camera_view_surface(robot_state, floor_plan, width, height)
    screen.blit(cam_surf, (x, y))
    pygame.draw.rect(screen, (0, 0, 0), (x, y, width, height), 2)
    font = pygame.font.Font(None, 24)
    label = font.render("Camera View", True, (0, 0, 0))
    screen.blit(label, (x, y - 25))


class FloorPlanEditor:
    """GUI for editing the floor plan"""
    
    def __init__(self, screen_width, screen_height):
        self.screen_width = screen_width
        self.screen_height = screen_height
        self.objects: List[FloorPlanObject] = []
        self.selected_object = None
        self.dragging = False
        self.edit_mode = False
        self.current_tool = ObjectType.WALL
        self.object_colors = {
            ObjectType.WALL: (150, 150, 150),
            ObjectType.OBSTACLE: (255, 0, 0),
            ObjectType.FURNITURE: (139, 69, 19),
            ObjectType.DOOR: (139, 69, 19),
            ObjectType.WINDOW: (173, 216, 230),
        }
        self.resize_handle_index = None
        self.resize_start_mouse = None
        self.resize_start_dims = None
        self.resize_start_pos = None
        self.rotating = False
        self.rotation_start_angle = None
        self.rotation_start_mouse = None
        self.create_default_floor_plan()
    
    def create_default_floor_plan(self):
        """Create the default floor plan"""
        self.objects = create_default_floor_plan()
        logger.info(f"Created default floor plan with {len(self.objects)} objects")
    
    def handle_events(self, events):
        """Handle pygame events for the editor"""
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.handle_mouse_click(event.pos)
                elif event.button == 3:  # Right click
                    self.handle_right_click(event.pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    self.handle_mouse_release(event.pos)
            elif event.type == pygame.MOUSEMOTION:
                if self.dragging and self.selected_object:
                    self.handle_mouse_drag(event.pos)
            elif event.type == pygame.KEYDOWN:
                self.handle_key_press(event.key)
    
    def handle_mouse_click(self, pos):
        """Handle mouse click in editor"""
        if not self.edit_mode:
            return
        
        world_pos = self.screen_to_world(pos)
        if self.selected_object:
            handle_idx = self.get_resize_handle_at(pos)
            if handle_idx is not None:
                self.resize_handle_index = handle_idx
                self.resize_start_mouse = pos
                self.resize_start_dims = self.selected_object.dimensions
                self.resize_start_pos = self.selected_object.position
                self.dragging = True
                return
            elif self.get_rotation_handle_at(pos):
                self.rotating = True
                self.rotation_start_mouse = pos
                self.rotation_start_angle = self.selected_object.rotation
                self.dragging = True
                return
        
        clicked_object = self.get_object_at(world_pos)
        if clicked_object:
            self.selected_object = clicked_object
            self.dragging = True
        else:
            self.add_object_at(world_pos)
    
    def handle_right_click(self, pos):
        """Handle right click (delete object)"""
        if not self.edit_mode:
            return
        
        world_pos = self.screen_to_world(pos)
        clicked_object = self.get_object_at(world_pos)
        if clicked_object:
            self.objects.remove(clicked_object)
    
    def handle_mouse_drag(self, pos):
        """Handle mouse drag for moving or resizing objects"""
        if not self.selected_object:
            return
        if self.resize_handle_index is not None:
            self.resize_object_with_handle(pos)
        elif self.rotating:
            self.rotate_object_with_handle(pos)
        else:
            world_pos = self.screen_to_world(pos)
            self.selected_object.position = world_pos
    
    def handle_mouse_release(self, pos):
        self.dragging = False
        self.resize_handle_index = None
        self.resize_start_mouse = None
        self.resize_start_dims = None
        self.resize_start_pos = None
        self.rotating = False
        self.rotation_start_angle = None
        self.rotation_start_mouse = None
        self.selected_object = None
    
    def handle_key_press(self, key):
        """Handle keyboard input"""
        if key == pygame.K_e:
            self.edit_mode = not self.edit_mode
            logger.info(f"Edit mode: {'ON' if self.edit_mode else 'OFF'}")
        elif key == pygame.K_1:
            self.current_tool = ObjectType.WALL
        elif key == pygame.K_2:
            self.current_tool = ObjectType.OBSTACLE
        elif key == pygame.K_3:
            self.current_tool = ObjectType.FURNITURE
        elif key == pygame.K_4:
            self.current_tool = ObjectType.DOOR
        elif key == pygame.K_5:
            self.current_tool = ObjectType.WINDOW
        elif key == pygame.K_s:
            self.save_floor_plan()
        elif key == pygame.K_l:
            self.load_floor_plan()
        elif key == pygame.K_r:
            self.create_default_floor_plan()
    
    def screen_to_world(self, screen_pos):
        """Convert screen coordinates to world coordinates"""
        scale = get_scale()
        center_x, center_y = self.screen_width // 2, self.screen_height // 2
        world_x = (screen_pos[0] - center_x) / scale
        world_y = (screen_pos[1] - center_y) / scale
        return (world_x, world_y)
    
    def get_object_at(self, world_pos):
        """Get object at world position"""
        for obj in self.objects:
            obj_min = (obj.position[0] - obj.dimensions[0]/2, obj.position[1] - obj.dimensions[1]/2)
            obj_max = (obj.position[0] + obj.dimensions[0]/2, obj.position[1] + obj.dimensions[1]/2)
            
            if (obj_min[0] <= world_pos[0] <= obj_max[0] and 
                obj_min[1] <= world_pos[1] <= obj_max[1]):
                return obj
        return None
    
    def add_object_at(self, world_pos):
        """Add new object at world position"""
        default_sizes = {
            ObjectType.WALL: (2, 0.1),
            ObjectType.OBSTACLE: (0.5, 0.5),
            ObjectType.FURNITURE: (1, 1),
            ObjectType.DOOR: (0.1, 1),
            ObjectType.WINDOW: (0.1, 1),
        }
        
        dimensions = default_sizes.get(self.current_tool, (1, 1))
        name = f"{self.current_tool.value.capitalize()}_{len(self.objects)+1}"
        
        new_object = FloorPlanObject(
            obj_type=self.current_tool,
            position=world_pos,
            dimensions=dimensions,
            color=self.object_colors[self.current_tool],
            collision=self.current_tool not in [ObjectType.DOOR, ObjectType.WINDOW],
            name=name
        )
        
        self.objects.append(new_object)
        logger.info(f"Added {name} at {world_pos}")
    
    def save_floor_plan(self):
        """Save floor plan to JSON file"""
        success = save_floor_plan_to_json(self.objects)
        if success:
            logger.info("Floor plan saved to floor_plan.json")
        else:
            logger.error("Failed to save floor plan")
    
    def load_floor_plan(self):
        """Load floor plan from JSON file"""
        loaded_objects = load_floor_plan_from_json()
        if loaded_objects:
            self.objects = loaded_objects
            logger.info(f"Floor plan loaded with {len(self.objects)} objects")
        else:
            logger.warning("No saved floor plan found, keeping current floor plan")
    
    def draw(self, screen):
        scale = get_scale()
        center_x, center_y = self.screen_width // 2, self.screen_height // 2
        
        # Draw adaptive grid
        if current_zoom >= 2.0:
            grid_spacing = 1
        elif current_zoom >= 1.0:
            grid_spacing = 2
        elif current_zoom >= 0.5:
            grid_spacing = 5
        else:
            grid_spacing = 10
        
        grid_range = max(20, int(max(self.screen_width, self.screen_height) / scale / grid_spacing))
        
        for i in range(-grid_range, grid_range + 1, grid_spacing):
            grid_x = center_x + i * scale
            pygame.draw.line(screen, (200, 200, 200), (grid_x, 0), (grid_x, self.screen_height))
            grid_y = center_y + i * scale
            pygame.draw.line(screen, (200, 200, 200), (0, grid_y), (self.screen_width, grid_y))
        
        # Draw coordinate axes
        pygame.draw.line(screen, (100, 100, 100), (center_x, 0), (center_x, self.screen_height), 2)
        pygame.draw.line(screen, (100, 100, 100), (0, center_y), (self.screen_width, center_y), 2)
        
        # Draw objects
        for obj in self.objects:
            self.draw_object(screen, obj, scale, center_x, center_y)
            if self.edit_mode and obj == self.selected_object:
                self.draw_handles(screen, obj, scale, center_x, center_y)

    def draw_object(self, screen, obj, scale, center_x, center_y):
        cx, cy = obj.position
        w, h = obj.dimensions
        angle = math.radians(obj.rotation)
        corners = [
            (-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)
        ]
        points = []
        for x, y in corners:
            rx = x * math.cos(angle) - y * math.sin(angle)
            ry = x * math.sin(angle) + y * math.cos(angle)
            sx = center_x + (cx + rx) * scale
            sy = center_y + (cy + ry) * scale
            points.append((sx, sy))
        pygame.draw.polygon(screen, obj.color, points)
        pygame.draw.polygon(screen, (0, 0, 0), points, 2)
        
        if self.edit_mode:
            font = pygame.font.Font(None, 20)
            text_surface = font.render(obj.name, True, (0, 0, 0))
            text_rect = text_surface.get_rect(center=(center_x + cx*scale, center_y + cy*scale))
            screen.blit(text_surface, text_rect)

    def draw_handles(self, screen, obj, scale, center_x, center_y):
        cx, cy = obj.position
        w, h = obj.dimensions
        angle = math.radians(obj.rotation)
        corners = [
            (-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)
        ]
        handle_radius = 7
        for x, y in corners:
            rx = x * math.cos(angle) - y * math.sin(angle)
            ry = x * math.sin(angle) + y * math.cos(angle)
            sx = center_x + (cx + rx) * scale
            sy = center_y + (cy + ry) * scale
            pygame.draw.circle(screen, (0, 200, 0), (int(sx), int(sy)), handle_radius)
        
        # Rotation handle
        top_center = (0, -h/2)
        rx = top_center[0] * math.cos(angle) - top_center[1] * math.sin(angle)
        ry = top_center[0] * math.sin(angle) + top_center[1] * math.cos(angle)
        rot_x = center_x + (cx + rx) * scale
        rot_y = center_y + (cy + ry - 0.5) * scale
        
        pygame.draw.circle(screen, (200, 0, 0), (int(rot_x), int(rot_y)), handle_radius)

    def draw_ui(self, screen):
        """Draw the editor UI"""
        font = pygame.font.Font(None, 24)
        
        mode_text = f"Edit Mode: {'ON' if self.edit_mode else 'OFF'}"
        text_surface = font.render(mode_text, True, (255, 0, 0) if self.edit_mode else (0, 255, 0))
        screen.blit(text_surface, (10, 10))
        
        tool_text = f"Tool: {self.current_tool.value.capitalize()}"
        text_surface = font.render(tool_text, True, (0, 0, 0))
        screen.blit(text_surface, (10, 40))
        
        controls = [
            "E - Toggle Edit Mode",
            "1-5 - Select Tool",
            "Left Click - Add/Move Object",
            "Right Click - Delete Object",
            "Drag Green Handles - Resize Object",
            "Drag Red Handle - Rotate Object",
            "S - Save Floor Plan",
            "L - Load Floor Plan",
            "R - Reset to Default",
            "+/- - Zoom In/Out",
            "0 - Reset Zoom"
        ]
        
        for i, control in enumerate(controls):
            text_surface = font.render(control, True, (100, 100, 100))
            screen.blit(text_surface, (10, 70 + i * 25))
        
        count_text = f"Objects: {len(self.objects)}"
        text_surface = font.render(count_text, True, (0, 0, 0))
        screen.blit(text_surface, (10, self.screen_height - 30))
    
    def check_collision(self, robot_pos, robot_size):
        """Check if robot collides with any objects"""
        for obj in self.objects:
            if not obj.collision:
                continue
            
            obj_min = (obj.position[0] - obj.dimensions[0]/2, obj.position[1] - obj.dimensions[1]/2)
            obj_max = (obj.position[0] + obj.dimensions[0]/2, obj.position[1] + obj.dimensions[1]/2)
            
            robot_min = (robot_pos[0] - robot_size, robot_pos[1] - robot_size)
            robot_max = (robot_pos[0] + robot_size, robot_pos[1] + robot_size)
            
            if (robot_min[0] < obj_max[0] and robot_max[0] > obj_min[0] and
                robot_min[1] < obj_max[1] and robot_max[1] > obj_min[1]):
                return True
        
        return False

    def get_resize_handle_at(self, mouse_pos, tol=12):
        """Return handle index (0-3) if mouse is near a resize handle, else None"""
        if not self.selected_object:
            return None
        scale = get_scale()
        center_x, center_y = self.screen_width // 2, self.screen_height // 2
        cx, cy = self.selected_object.position
        w, h = self.selected_object.dimensions
        angle = math.radians(self.selected_object.rotation)
        corners = [
            (-w/2, -h/2), (w/2, -h/2), (w/2, h/2), (-w/2, h/2)
        ]
        for i, (x, y) in enumerate(corners):
            rx = x * math.cos(angle) - y * math.sin(angle)
            ry = x * math.sin(angle) + y * math.cos(angle)
            sx = center_x + (cx + rx) * scale
            sy = center_y + (cy + ry) * scale
            if (abs(mouse_pos[0] - sx) < tol) and (abs(mouse_pos[1] - sy) < tol):
                return i
        return None

    def resize_object_with_handle(self, mouse_pos):
        """Resize the selected object by dragging a corner handle"""
        if not self.selected_object or self.resize_handle_index is None:
            return
        scale = get_scale()
        center_x, center_y = self.screen_width // 2, self.screen_height // 2
        start_dims = self.resize_start_dims
        start_pos = self.resize_start_pos
        idx = self.resize_handle_index
        w0, h0 = start_dims
        angle = math.radians(self.selected_object.rotation)
        corners = [
            (-w0/2, -h0/2), (w0/2, -h0/2), (w0/2, h0/2), (-w0/2, h0/2)
        ]
        opp_idx = (idx + 2) % 4
        opp_x, opp_y = corners[opp_idx]
        mx, my = (mouse_pos[0] - center_x) / scale, (mouse_pos[1] - center_y) / scale
        dx = mx - start_pos[0]
        dy = my - start_pos[1]
        local_x = dx * math.cos(-angle) - dy * math.sin(-angle)
        local_y = dx * math.sin(-angle) + dy * math.cos(-angle)
        new_w = max(0.1, abs(local_x - opp_x))
        new_h = max(0.1, abs(local_y - opp_y))
        mid_x = (local_x + opp_x) / 2
        mid_y = (local_y + opp_y) / 2
        world_mid_x = start_pos[0] + mid_x * math.cos(angle) - mid_y * math.sin(angle)
        world_mid_y = start_pos[1] + mid_x * math.sin(angle) + mid_y * math.cos(angle)
        self.selected_object.dimensions = (new_w, new_h)
        self.selected_object.position = (world_mid_x, world_mid_y)

    def get_rotation_handle_at(self, mouse_pos, tol=12):
        """Return True if mouse is near the rotation handle, else False"""
        if not self.selected_object:
            return False
        scale = get_scale()
        center_x, center_y = self.screen_width // 2, self.screen_height // 2
        cx, cy = self.selected_object.position
        w, h = self.selected_object.dimensions
        angle = math.radians(self.selected_object.rotation)
        
        top_center = (0, -h/2)
        rx = top_center[0] * math.cos(angle) - top_center[1] * math.sin(angle)
        ry = top_center[0] * math.sin(angle) + top_center[1] * math.cos(angle)
        rot_x = center_x + (cx + rx) * scale
        rot_y = center_y + (cy + ry - 0.5) * scale
        
        return (abs(mouse_pos[0] - rot_x) < tol) and (abs(mouse_pos[1] - rot_y) < tol)

    def rotate_object_with_handle(self, mouse_pos):
        """Rotate the selected object with the rotation handle"""
        if not self.selected_object or self.rotation_start_mouse is None:
            return
        
        scale = get_scale()
        center_x, center_y = self.screen_width // 2, self.screen_height // 2
        cx, cy = self.selected_object.position
        
        obj_screen_x = center_x + cx * scale
        obj_screen_y = center_y + cy * scale
        
        start_dx = self.rotation_start_mouse[0] - obj_screen_x
        start_dy = self.rotation_start_mouse[1] - obj_screen_y
        start_angle = math.atan2(start_dy, start_dx)
        
        current_dx = mouse_pos[0] - obj_screen_x
        current_dy = mouse_pos[1] - obj_screen_y
        current_angle = math.atan2(current_dy, current_dx)
        
        angle_diff = current_angle - start_angle
        new_rotation = self.rotation_start_angle + math.degrees(angle_diff)
        new_rotation = new_rotation % 360
        if new_rotation > 180:
            new_rotation -= 360
        
        self.selected_object.rotation = new_rotation


def main():
    # Initialize Pygame
    pygame.init()
    screen_width, screen_height = 1200, 800
    screen = pygame.display.set_mode((screen_width, screen_height))
    pygame.display.set_caption("Enhanced 2D Robot Simulation with Sensors")
    clock = pygame.time.Clock()
    
    # Load config
    import yaml
    with open("config/robot_config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # Create robot components using the same platform as main.py
    robot_state = RobotState(config)
    motor_controller = SimulatedMotorController(config)
    sensor_manager = SimulatedSensorManager(config)
    pathfinder = Pathfinder(config)
    autonomous_controller = AutonomousController(
        robot_state, motor_controller, sensor_manager, pathfinder
    )
    
    # Create floor plan editor
    floor_plan = FloorPlanEditor(screen_width - 400, screen_height)
    
    # Set floor plan objects in sensor manager
    sensor_manager.set_floor_plan_objects(floor_plan.objects)
    
    # Create robot visualizer
    robot_visualizer = RobotVisualizer(robot_state, sensor_manager)
    
    # Start components
    motor_controller.start()
    sensor_manager.start()
    autonomous_controller.start()
    
    # Set initial robot position
    robot_state.reset_position(1.5, 0.0, 0.0)  # Start at (1.5, 0) facing right
    
    # Simulation variables
    running = True
    last_time = time.time()
    
    # Demo mode
    demo_mode = "manual"  # or "autonomous"
    
    logger.info("Enhanced 2D Robot Simulation with Sensors")
    logger.info("Controls:")
    logger.info("  Arrow keys - Move robot")
    logger.info("  A - Toggle autonomous mode")
    logger.info("  E - Toggle edit mode")
    logger.info("  1-5 - Select tool (Wall, Obstacle, Furniture, Door, Window)")
    logger.info("  Left Click - Add/Move object (in edit mode)")
    logger.info("  Right Click - Delete object (in edit mode)")
    logger.info("  S - Save floor plan")
    logger.info("  L - Load floor plan")
    logger.info("  R - Reset to default floor plan")
    logger.info("  +/- - Zoom in/out")
    logger.info("  0 - Reset zoom")
    logger.info("  ESC - Exit")
    
    while running:
        current_time = time.time()
        dt = current_time - last_time
        last_time = current_time
        
        # Handle events
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_a:
                    demo_mode = "autonomous" if demo_mode == "manual" else "manual"
                    logger.info(f"Switched to {demo_mode} mode")
                # Zoom controls
                elif event.key == pygame.K_PLUS or event.key == pygame.K_EQUALS:
                    zoom_in()
                elif event.key == pygame.K_MINUS:
                    zoom_out()
                elif event.key == pygame.K_0:  # Reset zoom
                    reset_zoom()
        
        # Handle floor plan editor events
        floor_plan.handle_events(events)
        
        # Update sensor manager with current floor plan objects
        sensor_manager.set_floor_plan_objects(floor_plan.objects)
        
        # Handle input (only if not in edit mode)
        if not floor_plan.edit_mode:
            keys = pygame.key.get_pressed()
            
            if demo_mode == "manual":
                # Manual control using motor controller
                if keys[pygame.K_UP]:
                    motor_controller.move_forward(50)
                elif keys[pygame.K_DOWN]:
                    motor_controller.move_backward(50)
                elif keys[pygame.K_LEFT]:
                    motor_controller.turn_left(30)
                elif keys[pygame.K_RIGHT]:
                    motor_controller.turn_right(30)
                else:
                    motor_controller.stop_motors()
            else:
                # Autonomous mode - let autonomous controller handle movement
                pass
            
            # Update robot physics based on motor controller speeds
            left_speed, right_speed = motor_controller.get_current_speeds()
            
            # Simple physics simulation
            wheel_base = 0.25  # Distance between wheels
            linear_vel = (left_speed + right_speed) / 200.0  # Average speed
            angular_vel = (right_speed - left_speed) / (100.0 * wheel_base)  # Angular velocity
            
            # Update robot state position
            current_pos = robot_state.get_position()
            new_x = current_pos.x + linear_vel * math.cos(current_pos.theta) * dt
            new_y = current_pos.y + linear_vel * math.sin(current_pos.theta) * dt
            new_theta = current_pos.theta + angular_vel * dt
            
            # Keep theta in [-pi, pi]
            new_theta = math.atan2(math.sin(new_theta), math.cos(new_theta))
            
            # Check collision with floor plan objects
            if floor_plan.check_collision((new_x, new_y), 0.25):  # 25cm collision radius
                # Collision detected - don't update position
                motor_controller.stop_motors()
            else:
                # Update robot state
                robot_state.update_position(new_x - current_pos.x, new_y - current_pos.y, new_theta - current_pos.theta)
            
            # Update sensor manager with new robot pose
            position = robot_state.get_position()
            sensor_manager.set_robot_pose(position.x, position.y, position.theta)
            
            # Update pathfinder with new robot position
            pathfinder.update_robot_position(position.x, position.y)
        
        # Clear screen
        screen.fill((240, 240, 240))  # Light gray background
        
        # Draw floor plan
        floor_plan.draw(screen)
        
        # Draw robot (only if not in edit mode)
        if not floor_plan.edit_mode:
            robot_visualizer.draw(
                screen,
                offset_x=(screen_width - 400) // 2,
                offset_y=screen_height // 2,
            )
        
        # Draw UI
        floor_plan.draw_ui(screen)
        
        # Draw right panel background
        right_panel_x = screen_width - 400
        right_panel_y = 0
        right_panel_width = 400
        right_panel_height = screen_height
        pygame.draw.rect(screen, (255, 255, 255), (right_panel_x, right_panel_y, right_panel_width, right_panel_height))
        
        # Draw status text, stacked vertically
        font = pygame.font.Font(None, 36)
        y_offset = 10
        line_spacing = 40
        status_text = f"Mode: {demo_mode.capitalize()}"
        text_surface = font.render(status_text, True, (0, 0, 0))
        screen.blit(text_surface, (right_panel_x + 20, y_offset))
        y_offset += line_spacing
        
        # Sensor readings panel
        draw_sensor_readings(screen, sensor_manager, right_panel_x + 20, y_offset)
        y_offset += 140  # Height of sensor panel
        
        # Position, angle, zoom, scale
        font = pygame.font.Font(None, 32)
        position = robot_state.get_position()
        pos_text = f"Position: ({position.x:.1f}, {position.y:.1f})"
        text_surface = font.render(pos_text, True, (0, 0, 0))
        screen.blit(text_surface, (right_panel_x + 20, y_offset))
        y_offset += line_spacing
        angle_text = f"Angle: {math.degrees(position.theta):.1f}°"
        text_surface = font.render(angle_text, True, (0, 0, 0))
        screen.blit(text_surface, (right_panel_x + 20, y_offset))
        y_offset += line_spacing
        
        # Motor speeds
        left_speed, right_speed = motor_controller.get_current_speeds()
        speed_text = f"Speeds: L={left_speed:.0f}, R={right_speed:.0f}"
        text_surface = font.render(speed_text, True, (0, 0, 0))
        screen.blit(text_surface, (right_panel_x + 20, y_offset))
        y_offset += line_spacing
        
        zoom_text = f"Zoom: {current_zoom:.2f}x"
        text_surface = font.render(zoom_text, True, (0, 0, 0))
        screen.blit(text_surface, (right_panel_x + 20, y_offset))
        y_offset += line_spacing
        scale_text = f"Scale: {get_scale():.1f} px/m"
        text_surface = font.render(scale_text, True, (0, 0, 0))
        screen.blit(text_surface, (right_panel_x + 20, y_offset))
        y_offset += line_spacing
        
        # Draw camera view panel below all text
        camera_panel_y = y_offset + 20
        draw_camera_panel(screen, robot_state, floor_plan, right_panel_x + 20, camera_panel_y, 320, 240)
        
        # Update display
        pygame.display.flip()
        clock.tick(60)
    
    # Cleanup
    motor_controller.stop()
    sensor_manager.stop()
    autonomous_controller.stop()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
