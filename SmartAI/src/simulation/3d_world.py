"""
3D World Simulation
Provides a virtual 3D environment for robot testing and development
"""

import pygame
import numpy as np
import math
from typing import List, Tuple, Optional, Dict
from dataclasses import dataclass
from enum import Enum
import random
from loguru import logger


class ObjectType(Enum):
    """Types of objects in the 3D world"""
    WALL = "wall"
    OBSTACLE = "obstacle"
    FURNITURE = "furniture"
    DOOR = "door"
    WINDOW = "window"
    FLOOR = "floor"
    CEILING = "ceiling"


@dataclass
class WorldObject:
    """3D object in the simulation world"""
    obj_type: ObjectType
    position: Tuple[float, float, float]  # x, y, z
    dimensions: Tuple[float, float, float]  # width, height, depth
    color: Tuple[int, int, int]
    texture: Optional[str] = None
    collision: bool = True
    transparent: bool = False


@dataclass
class Robot3D:
    """3D representation of the robot"""
    position: Tuple[float, float, float]  # x, y, z
    orientation: float  # rotation around Y axis (radians)
    dimensions: Tuple[float, float, float]  # width, height, depth
    color: Tuple[int, int, int] = (100, 150, 255)
    velocity: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    angular_velocity: float = 0.0


class Camera3D:
    """3D camera for viewing the simulation"""
    
    def __init__(self, position: Tuple[float, float, float], target: Tuple[float, float, float]):
        self.position = np.array(position, dtype=np.float32)
        self.target = np.array(target, dtype=np.float32)
        self.up = np.array([0, 1, 0], dtype=np.float32)
        self.fov = 60.0
        self.near = 0.1
        self.far = 1000.0
        
        # Camera movement
        self.speed = 5.0
        self.rotation_speed = 0.02
        self.distance = 20.0
        self.phi = 0.0  # horizontal angle
        self.theta = math.pi / 4  # vertical angle
    
    def update(self, keys_pressed: Dict[int, bool], mouse_delta: Tuple[int, int]):
        """Update camera position based on input"""
        # Mouse look
        if mouse_delta[0] != 0:
            self.phi += mouse_delta[0] * self.rotation_speed
        if mouse_delta[1] != 0:
            self.theta += mouse_delta[1] * self.rotation_speed
            self.theta = max(0.1, min(math.pi - 0.1, self.theta))
        
        # Keyboard movement
        forward = np.array([
            math.sin(self.phi) * math.cos(self.theta),
            math.sin(self.theta),
            math.cos(self.phi) * math.cos(self.theta)
        ])
        right = np.array([
            math.cos(self.phi),
            0,
            -math.sin(self.phi)
        ])
        
        if keys_pressed.get(pygame.K_w):
            self.position += forward * self.speed
        if keys_pressed.get(pygame.K_s):
            self.position -= forward * self.speed
        if keys_pressed.get(pygame.K_a):
            self.position -= right * self.speed
        if keys_pressed.get(pygame.K_d):
            self.position += right * self.speed
        if keys_pressed.get(pygame.K_SPACE):
            self.position[1] += self.speed
        if keys_pressed.get(pygame.K_LSHIFT):
            self.position[1] -= self.speed
    
    def get_view_matrix(self) -> np.ndarray:
        """Get view matrix for rendering"""
        forward = np.array([
            math.sin(self.phi) * math.cos(self.theta),
            math.sin(self.theta),
            math.cos(self.phi) * math.cos(self.theta)
        ])
        self.target = self.position + forward
        
        # Calculate view matrix
        z = self.position - self.target
        z = z / np.linalg.norm(z)
        
        x = np.cross(self.up, z)
        x = x / np.linalg.norm(x)
        
        y = np.cross(z, x)
        
        view_matrix = np.array([
            [x[0], x[1], x[2], -np.dot(x, self.position)],
            [y[0], y[1], y[2], -np.dot(y, self.position)],
            [z[0], z[1], z[2], -np.dot(z, self.position)],
            [0, 0, 0, 1]
        ])
        
        return view_matrix
    
    def get_projection_matrix(self, aspect_ratio: float) -> np.ndarray:
        """Get projection matrix for rendering"""
        f = 1.0 / math.tan(math.radians(self.fov) / 2.0)
        
        projection_matrix = np.array([
            [f / aspect_ratio, 0, 0, 0],
            [0, f, 0, 0],
            [0, 0, (self.far + self.near) / (self.near - self.far), (2 * self.far * self.near) / (self.near - self.far)],
            [0, 0, -1, 0]
        ])
        
        return projection_matrix


class World3D:
    """3D world simulation environment"""
    
    def __init__(self, width: int = 800, height: int = 600):
        self.width = width
        self.height = height
        self.aspect_ratio = width / height
        
        # Initialize Pygame
        pygame.init()
        self.screen = pygame.display.set_mode((width, height), pygame.OPENGL | pygame.DOUBLEBUF)
        pygame.display.set_caption("Smart Robot 3D Simulation")
        
        # Initialize OpenGL
        self._setup_opengl()
        
        # World objects
        self.objects: List[WorldObject] = []
        self.robot: Optional[Robot3D] = None
        
        # Camera
        self.camera = Camera3D((0, 10, 20), (0, 0, 0))
        
        # Lighting
        self.light_position = np.array([10.0, 20.0, 10.0, 1.0])
        self.light_color = np.array([1.0, 1.0, 1.0, 1.0])
        
        # Mouse control
        self.mouse_sensitivity = 0.002
        self.last_mouse_pos = None
        
        # Create default world
        self._create_default_world()
    
    def _setup_opengl(self):
        """Setup OpenGL rendering context"""
        import OpenGL.GL as gl
        import OpenGL.GLU as glu
        
        gl.glEnable(gl.GL_DEPTH_TEST)
        gl.glEnable(gl.GL_LIGHTING)
        gl.glEnable(gl.GL_LIGHT0)
        gl.glEnable(gl.GL_COLOR_MATERIAL)
        gl.glEnable(gl.GL_CULL_FACE)
        
        # Set up lighting
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_POSITION, self.light_position)
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_DIFFUSE, self.light_color)
        gl.glLightfv(gl.GL_LIGHT0, gl.GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        
        # Set up material
        gl.glMaterialfv(gl.GL_FRONT, gl.GL_AMBIENT, [0.2, 0.2, 0.2, 1.0])
        gl.glMaterialfv(gl.GL_FRONT, gl.GL_DIFFUSE, [0.8, 0.8, 0.8, 1.0])
        gl.glMaterialfv(gl.GL_FRONT, gl.GL_SPECULAR, [1.0, 1.0, 1.0, 1.0])
        gl.glMaterialf(gl.GL_FRONT, gl.GL_SHININESS, 50.0)
    
    def _create_default_world(self):
        """Create a default house environment"""
        # Floor
        self.add_object(WorldObject(
            obj_type=ObjectType.FLOOR,
            position=(0, 0, 0),
            dimensions=(50, 0.1, 50),
            color=(200, 200, 200),
            collision=True
        ))
        
        # Ceiling
        self.add_object(WorldObject(
            obj_type=ObjectType.CEILING,
            position=(0, 3, 0),
            dimensions=(50, 0.1, 50),
            color=(180, 180, 180),
            collision=False
        ))
        
        # Walls
        wall_height = 3.0
        wall_thickness = 0.2
        
        # North wall
        self.add_object(WorldObject(
            obj_type=ObjectType.WALL,
            position=(0, wall_height/2, -25),
            dimensions=(50, wall_height, wall_thickness),
            color=(150, 150, 150),
            collision=True
        ))
        
        # South wall
        self.add_object(WorldObject(
            obj_type=ObjectType.WALL,
            position=(0, wall_height/2, 25),
            dimensions=(50, wall_height, wall_thickness),
            color=(150, 150, 150),
            collision=True
        ))
        
        # East wall
        self.add_object(WorldObject(
            obj_type=ObjectType.WALL,
            position=(25, wall_height/2, 0),
            dimensions=(wall_thickness, wall_height, 50),
            color=(150, 150, 150),
            collision=True
        ))
        
        # West wall
        self.add_object(WorldObject(
            obj_type=ObjectType.WALL,
            position=(-25, wall_height/2, 0),
            dimensions=(wall_thickness, wall_height, 50),
            color=(150, 150, 150),
            collision=True
        ))
        
        # Add some furniture/obstacles
        self.add_object(WorldObject(
            obj_type=ObjectType.FURNITURE,
            position=(-10, 0.5, -10),
            dimensions=(2, 1, 2),
            color=(139, 69, 19),  # Brown
            collision=True
        ))
        
        self.add_object(WorldObject(
            obj_type=ObjectType.FURNITURE,
            position=(10, 0.5, 10),
            dimensions=(3, 0.8, 1.5),
            color=(139, 69, 19),
            collision=True
        ))
        
        self.add_object(WorldObject(
            obj_type=ObjectType.OBSTACLE,
            position=(0, 0.25, 15),
            dimensions=(1, 0.5, 1),
            color=(255, 0, 0),  # Red
            collision=True
        ))
        
        # Add a door
        self.add_object(WorldObject(
            obj_type=ObjectType.DOOR,
            position=(-25, 1.5, 0),
            dimensions=(0.1, 2, 1),
            color=(139, 69, 19),
            collision=False
        ))
        
        # Add windows
        self.add_object(WorldObject(
            obj_type=ObjectType.WINDOW,
            position=(25, 1.5, 10),
            dimensions=(0.1, 1, 1),
            color=(173, 216, 230),  # Light blue
            collision=False,
            transparent=True
        ))
        
        self.add_object(WorldObject(
            obj_type=ObjectType.WINDOW,
            position=(25, 1.5, -10),
            dimensions=(0.1, 1, 1),
            color=(173, 216, 230),
            collision=False,
            transparent=True
        ))
    
    def add_object(self, obj: WorldObject):
        """Add an object to the world"""
        self.objects.append(obj)
    
    def add_robot(self, robot: Robot3D):
        """Add robot to the world"""
        self.robot = robot
    
    def update_robot_position(self, x: float, y: float, z: float, orientation: float):
        """Update robot position in the world"""
        if self.robot:
            self.robot.position = (x, y, z)
            self.robot.orientation = orientation
    
    def get_robot_position(self) -> Optional[Tuple[float, float, float]]:
        """Get current robot position"""
        if self.robot:
            return self.robot.position
        return None
    
    def check_collision(self, position: Tuple[float, float, float], 
                       dimensions: Tuple[float, float, float]) -> bool:
        """Check if a position collides with any objects"""
        for obj in self.objects:
            if not obj.collision:
                continue
            
            # Simple AABB collision detection
            obj_min = (
                obj.position[0] - obj.dimensions[0]/2,
                obj.position[1] - obj.dimensions[1]/2,
                obj.position[2] - obj.dimensions[2]/2
            )
            obj_max = (
                obj.position[0] + obj.dimensions[0]/2,
                obj.position[1] + obj.dimensions[1]/2,
                obj.position[2] + obj.dimensions[2]/2
            )
            
            test_min = (
                position[0] - dimensions[0]/2,
                position[1] - dimensions[1]/2,
                position[2] - dimensions[2]/2
            )
            test_max = (
                position[0] + dimensions[0]/2,
                position[1] + dimensions[1]/2,
                position[2] + dimensions[2]/2
            )
            
            if (test_min[0] < obj_max[0] and test_max[0] > obj_min[0] and
                test_min[1] < obj_max[1] and test_max[1] > obj_min[1] and
                test_min[2] < obj_max[2] and test_max[2] > obj_min[2]):
                return True
        
        return False
    
    def get_sensor_readings(self, robot_pos: Tuple[float, float, float], 
                           robot_orientation: float) -> Dict[str, float]:
        """Simulate sensor readings from robot position"""
        readings = {
            'ultrasonic_front': float('inf'),
            'ultrasonic_left': float('inf'),
            'ultrasonic_right': float('inf'),
            'infrared_left': False,
            'infrared_right': False
        }
        
        # Sensor directions (relative to robot orientation)
        sensor_directions = {
            'ultrasonic_front': (0, 0, 1),  # Forward
            'ultrasonic_left': (-1, 0, 0),  # Left
            'ultrasonic_right': (1, 0, 0),  # Right
        }
        
        for sensor_name, direction in sensor_directions.items():
            # Rotate direction by robot orientation
            cos_rot = math.cos(robot_orientation)
            sin_rot = math.sin(robot_orientation)
            
            rotated_dir = (
                direction[0] * cos_rot - direction[2] * sin_rot,
                direction[1],
                direction[0] * sin_rot + direction[2] * cos_rot
            )
            
            # Ray casting for distance measurement
            min_distance = float('inf')
            for obj in self.objects:
                if not obj.collision:
                    continue
                
                # Simple ray-box intersection
                distance = self._ray_box_intersection(
                    robot_pos, rotated_dir, obj.position, obj.dimensions
                )
                if distance is not None and distance < min_distance:
                    min_distance = distance
            
            readings[sensor_name] = min_distance if min_distance != float('inf') else 400.0
        
        # Infrared sensors (simplified - just check if obstacles are very close)
        readings['infrared_left'] = readings['ultrasonic_left'] < 10.0
        readings['infrared_right'] = readings['ultrasonic_right'] < 10.0
        
        return readings
    
    def _ray_box_intersection(self, ray_origin: Tuple[float, float, float],
                             ray_direction: Tuple[float, float, float],
                             box_center: Tuple[float, float, float],
                             box_size: Tuple[float, float, float]) -> Optional[float]:
        """Calculate ray-box intersection distance"""
        # Convert to AABB format
        box_min = (
            box_center[0] - box_size[0]/2,
            box_center[1] - box_size[1]/2,
            box_center[2] - box_size[2]/2
        )
        box_max = (
            box_center[0] + box_size[0]/2,
            box_center[1] + box_size[1]/2,
            box_center[2] + box_size[2]/2
        )
        
        # Ray-box intersection algorithm
        t_min = (box_min[0] - ray_origin[0]) / ray_direction[0]
        t_max = (box_max[0] - ray_origin[0]) / ray_direction[0]
        
        if t_min > t_max:
            t_min, t_max = t_max, t_min
        
        ty_min = (box_min[1] - ray_origin[1]) / ray_direction[1]
        ty_max = (box_max[1] - ray_origin[1]) / ray_direction[1]
        
        if ty_min > ty_max:
            ty_min, ty_max = ty_max, ty_min
        
        if t_min > ty_max or ty_min > t_max:
            return None
        
        if ty_min > t_min:
            t_min = ty_min
        if ty_max < t_max:
            t_max = ty_max
        
        tz_min = (box_min[2] - ray_origin[2]) / ray_direction[2]
        tz_max = (box_max[2] - ray_origin[2]) / ray_direction[2]
        
        if tz_min > tz_max:
            tz_min, tz_max = tz_max, tz_min
        
        if t_min > tz_max or tz_min > t_max:
            return None
        
        if tz_min > t_min:
            t_min = tz_min
        if tz_max < t_max:
            t_max = tz_max
        
        if t_min < 0:
            return None
        
        return t_min
    
    def render(self):
        """Render the 3D world"""
        import OpenGL.GL as gl
        import OpenGL.GLU as glu
        
        # Clear buffers
        gl.glClear(gl.GL_COLOR_BUFFER_BIT | gl.GL_DEPTH_BUFFER_BIT)
        gl.glLoadIdentity()
        
        # Set up camera
        view_matrix = self.camera.get_view_matrix()
        gl.glMultMatrixf(view_matrix.T)
        
        # Render objects
        for obj in self.objects:
            self._render_object(obj)
        
        # Render robot
        if self.robot:
            self._render_robot(self.robot)
        
        # Update display
        pygame.display.flip()
    
    def _render_object(self, obj: WorldObject):
        """Render a single object"""
        import OpenGL.GL as gl
        
        gl.glPushMatrix()
        gl.glTranslatef(*obj.position)
        
        # Set color
        gl.glColor3f(obj.color[0]/255.0, obj.color[1]/255.0, obj.color[2]/255.0)
        
        # Render as cube
        self._render_cube(obj.dimensions)
        
        gl.glPopMatrix()
        gl.glColor3f(1.0, 1.0, 1.0)  # Reset color
    
    def _render_robot(self, robot: Robot3D):
        """Render the robot"""
        import OpenGL.GL as gl
        
        gl.glPushMatrix()
        gl.glTranslatef(*robot.position)
        gl.glRotatef(math.degrees(robot.orientation), 0, 1, 0)
        
        # Robot body
        gl.glColor3f(robot.color[0]/255.0, robot.color[1]/255.0, robot.color[2]/255.0)
        self._render_cube(robot.dimensions)
        
        # Robot direction indicator
        gl.glColor3f(1.0, 0.0, 0.0)  # Red arrow
        gl.glBegin(gl.GL_LINES)
        gl.glVertex3f(0, 0.1, 0)
        gl.glVertex3f(0, 0.1, robot.dimensions[2]/2 + 0.5)
        gl.glEnd()
        
        gl.glPopMatrix()
        gl.glColor3f(1.0, 1.0, 1.0)  # Reset color
    
    def _render_cube(self, dimensions: Tuple[float, float, float]):
        """Render a cube with given dimensions"""
        import OpenGL.GL as gl
        
        w, h, d = dimensions[0]/2, dimensions[1]/2, dimensions[2]/2
        
        gl.glBegin(gl.GL_QUADS)
        
        # Front face
        gl.glNormal3f(0, 0, 1)
        gl.glVertex3f(-w, -h, d)
        gl.glVertex3f(w, -h, d)
        gl.glVertex3f(w, h, d)
        gl.glVertex3f(-w, h, d)
        
        # Back face
        gl.glNormal3f(0, 0, -1)
        gl.glVertex3f(-w, -h, -d)
        gl.glVertex3f(-w, h, -d)
        gl.glVertex3f(w, h, -d)
        gl.glVertex3f(w, -h, -d)
        
        # Left face
        gl.glNormal3f(-1, 0, 0)
        gl.glVertex3f(-w, -h, -d)
        gl.glVertex3f(-w, -h, d)
        gl.glVertex3f(-w, h, d)
        gl.glVertex3f(-w, h, -d)
        
        # Right face
        gl.glNormal3f(1, 0, 0)
        gl.glVertex3f(w, -h, -d)
        gl.glVertex3f(w, h, -d)
        gl.glVertex3f(w, h, d)
        gl.glVertex3f(w, -h, d)
        
        # Top face
        gl.glNormal3f(0, 1, 0)
        gl.glVertex3f(-w, h, -d)
        gl.glVertex3f(-w, h, d)
        gl.glVertex3f(w, h, d)
        gl.glVertex3f(w, h, -d)
        
        # Bottom face
        gl.glNormal3f(0, -1, 0)
        gl.glVertex3f(-w, -h, -d)
        gl.glVertex3f(w, -h, -d)
        gl.glVertex3f(w, -h, d)
        gl.glVertex3f(-w, -h, d)
        
        gl.glEnd()
    
    def handle_events(self) -> bool:
        """Handle pygame events, return False if window should close"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # Left click
                    self.last_mouse_pos = pygame.mouse.get_pos()
            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:  # Left click
                    self.last_mouse_pos = None
            elif event.type == pygame.MOUSEMOTION:
                if self.last_mouse_pos and event.buttons[0]:  # Left mouse button held
                    dx = event.pos[0] - self.last_mouse_pos[0]
                    dy = event.pos[1] - self.last_mouse_pos[1]
                    self.camera.phi += dx * self.mouse_sensitivity
                    self.camera.theta += dy * self.mouse_sensitivity
                    self.camera.theta = max(0.1, min(math.pi - 0.1, self.camera.theta))
                    self.last_mouse_pos = event.pos
        
        return True
    
    def update(self, dt: float):
        """Update world state"""
        # Update camera based on keyboard input
        keys_pressed = pygame.key.get_pressed()
        mouse_delta = (0, 0)  # Could be enhanced for mouse look
        self.camera.update(keys_pressed, mouse_delta)
        
        # Update robot physics if present
        if self.robot:
            # Simple physics update
            self.robot.position = (
                self.robot.position[0] + self.robot.velocity[0] * dt,
                self.robot.position[1] + self.robot.velocity[1] * dt,
                self.robot.position[2] + self.robot.velocity[2] * dt
            )
            self.robot.orientation += self.robot.angular_velocity * dt
    
    def run_simulation(self, max_fps: int = 60):
        """Run the 3D simulation loop"""
        clock = pygame.time.Clock()
        running = True
        
        while running:
            dt = clock.tick(max_fps) / 1000.0  # Convert to seconds
            
            # Handle events
            running = self.handle_events()
            
            # Update world
            self.update(dt)
            
            # Render
            self.render()
        
        pygame.quit()
    
    def close(self):
        """Clean up resources"""
        pygame.quit() 