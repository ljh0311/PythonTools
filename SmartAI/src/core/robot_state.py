"""
Robot State Management
Handles position, orientation, and system status tracking
"""

import math
import time
from dataclasses import dataclass
from enum import Enum
from typing import Tuple, Optional
import numpy as np


class RobotMode(Enum):
    """Robot operation modes"""
    IDLE = "idle"
    MANUAL = "manual"
    AUTONOMOUS = "autonomous"
    EMERGENCY_STOP = "emergency_stop"
    RETURN_TO_BASE = "return_to_base"
    EXPLORING = "exploring"


class RobotStatus(Enum):
    """Robot system status"""
    OK = "ok"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Position:
    """Robot position in 2D space"""
    x: float  # cm
    y: float  # cm
    theta: float  # radians (0 = forward, positive = counterclockwise)
    
    def distance_to(self, other: 'Position') -> float:
        """Calculate distance to another position"""
        return math.sqrt((self.x - other.x)**2 + (self.y - other.y)**2)
    
    def angle_to(self, other: 'Position') -> float:
        """Calculate angle to another position"""
        return math.atan2(other.y - self.y, other.x - self.x)


@dataclass
class SensorData:
    """Sensor readings from all robot sensors"""
    ultrasonic_front: float = 0.0  # cm
    ultrasonic_left: float = 0.0   # cm
    ultrasonic_right: float = 0.0  # cm
    infrared_left: bool = False    # True if obstacle detected
    infrared_right: bool = False   # True if obstacle detected
    bumper_left: bool = False      # True if pressed
    bumper_right: bool = False     # True if pressed
    timestamp: float = 0.0
    
    def get_min_distance(self) -> float:
        """Get minimum distance from all ultrasonic sensors"""
        distances = [self.ultrasonic_front, self.ultrasonic_left, self.ultrasonic_right]
        valid_distances = [d for d in distances if d > 0]
        return min(valid_distances) if valid_distances else float('inf')


@dataclass
class MotorState:
    """Motor control state"""
    left_speed: float = 0.0   # -100 to 100
    right_speed: float = 0.0  # -100 to 100
    left_direction: int = 0   # -1, 0, 1
    right_direction: int = 0  # -1, 0, 1
    enabled: bool = False


class RobotState:
    """Main robot state manager"""
    
    def __init__(self, config: dict):
        self.config = config
        self.mode = RobotMode.IDLE
        self.status = RobotStatus.OK
        
        # Position and movement
        self.position = Position(0.0, 0.0, 0.0)
        self.target_position: Optional[Position] = None
        self.velocity = Position(0.0, 0.0, 0.0)  # cm/s
        
        # Sensors and motors
        self.sensors = SensorData()
        self.motors = MotorState()
        
        # System state
        self.battery_level = 100.0  # percentage
        self.is_connected = False
        self.last_update = time.time()
        
        # Safety and control
        self.emergency_stop = False
        self.obstacle_detected = False
        self.safe_to_move = True
        
        # Navigation state
        self.current_path = []
        self.map_data = None
        self.explored_areas = set()
        
        # Performance metrics
        self.total_distance_traveled = 0.0
        self.operation_time = 0.0
        self.start_time = time.time()
        
        # Sensor data caching for performance
        self._sensor_cache = None
        self._sensor_cache_time = 0.0
        self._status_cache = None
        self._status_cache_time = 0.0
        self._cache_timeout = 0.05  # 50ms cache timeout
    
    def update_position(self, delta_x: float, delta_y: float, delta_theta: float):
        """Update robot position based on movement"""
        self.position.x += delta_x
        self.position.y += delta_y
        self.position.theta += delta_theta
        
        # Normalize angle to [-π, π]
        self.position.theta = math.atan2(math.sin(self.position.theta), math.cos(self.position.theta))
        
        # Update total distance traveled
        distance = math.sqrt(delta_x**2 + delta_y**2)
        self.total_distance_traveled += distance
    
    def update_sensors(self, sensor_data: SensorData):
        """Update sensor readings"""
        self.sensors = sensor_data
        self.last_update = time.time()
        
        # Invalidate caches when sensors update
        self._sensor_cache = None
        self._status_cache = None
        
        # Check for obstacles
        min_distance = self.sensors.get_min_distance()
        critical_distance = self.config['robot']['safety_distances']['critical']
        warning_distance = self.config['robot']['safety_distances']['warning']
        
        if min_distance < critical_distance or self.sensors.bumper_left or self.sensors.bumper_right:
            self.obstacle_detected = True
            self.safe_to_move = False
            self.status = RobotStatus.CRITICAL
        elif min_distance < warning_distance:
            self.obstacle_detected = True
            self.safe_to_move = True
            self.status = RobotStatus.WARNING
        else:
            self.obstacle_detected = False
            self.safe_to_move = True
            self.status = RobotStatus.OK
    
    def update_motors(self, left_speed: float, right_speed: float):
        """Update motor states"""
        self.motors.left_speed = max(-100, min(100, left_speed))
        self.motors.right_speed = max(-100, min(100, right_speed))
        
        # Determine directions
        self.motors.left_direction = 1 if self.motors.left_speed > 0 else (-1 if self.motors.left_speed < 0 else 0)
        self.motors.right_direction = 1 if self.motors.right_speed > 0 else (-1 if self.motors.right_speed < 0 else 0)
    
    def set_mode(self, mode: RobotMode):
        """Change robot operation mode"""
        self.mode = mode
        if mode == RobotMode.EMERGENCY_STOP:
            self.emergency_stop = True
            self.motors.left_speed = 0
            self.motors.right_speed = 0
            self.motors.enabled = False
        else:
            self.emergency_stop = False
            self.motors.enabled = True
    
    def is_at_target(self, tolerance: float = 10.0) -> bool:
        """Check if robot has reached target position"""
        if self.target_position is None:
            return True
        return self.position.distance_to(self.target_position) < tolerance
    
    def get_status_summary(self) -> dict:
        """Get comprehensive status summary with caching"""
        current_time = time.time()
        
        # Check cache first
        if (self._status_cache is not None and 
            current_time - self._status_cache_time < self._cache_timeout):
            return self._status_cache
        
        # Generate new status
        status = {
            'mode': self.mode.value,
            'status': self.status.value,
            'position': {
                'x': round(self.position.x, 2),
                'y': round(self.position.y, 2),
                'theta': round(math.degrees(self.position.theta), 1)
            },
            'battery': round(self.battery_level, 1),
            'obstacle_detected': self.obstacle_detected,
            'safe_to_move': self.safe_to_move,
            'emergency_stop': self.emergency_stop,
            'total_distance': round(self.total_distance_traveled, 2),
            'operation_time': round(current_time - self.start_time, 1)
        }
        
        # Update cache
        self._status_cache = status
        self._status_cache_time = current_time
        
        return status
    
    def reset_position(self, x: float = 0.0, y: float = 0.0, theta: float = 0.0):
        """Reset robot position to specified coordinates"""
        self.position = Position(x, y, theta)
        self.total_distance_traveled = 0.0
    
    def update_battery(self, level: float):
        """Update battery level"""
        self.battery_level = max(0.0, min(100.0, level))
        if self.battery_level < 10.0:
            self.status = RobotStatus.WARNING
        elif self.battery_level < 5.0:
            self.status = RobotStatus.CRITICAL 
    
    def get_position(self) -> Position:
        """Return the current position of the robot."""
        return self.position 