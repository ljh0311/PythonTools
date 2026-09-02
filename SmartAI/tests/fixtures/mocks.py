"""Mock hardware components for navigation tests."""

import math
import time

import numpy as np

from src.hardware.sensor_manager import SensorReading

from .config import TestConfig


class EnhancedMockMotorController:
    """Enhanced mock motor controller with realistic response curves and calibration."""

    def __init__(self, config: TestConfig):
        self.config = config
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.left_target = 0.0
        self.right_target = 0.0
        self.is_running = False

        self.max_acceleration = 0.5
        self.max_deceleration = 0.8
        self.response_time = 0.1
        self.wheel_base = 0.25

        self.left_calibration = 1.0
        self.right_calibration = 1.0
        self.speed_noise = 0.02

        self.command_history = []
        self.last_update_time = time.time()

    def set_speeds(self, left: float, right: float):
        self.left_target = np.clip(left, -100.0, 100.0)
        self.right_target = np.clip(right, -100.0, 100.0)
        self.is_running = True
        self.last_update_time = time.time()

    def _update_speeds(self, dt: float):
        left_diff = self.left_target - self.left_speed
        right_diff = self.right_target - self.right_speed

        max_change = self.max_acceleration * dt * 100
        if abs(left_diff) > max_change:
            left_diff = np.sign(left_diff) * max_change
        if abs(right_diff) > max_change:
            right_diff = np.sign(right_diff) * max_change

        if abs(self.left_target) < abs(self.left_speed):
            max_change = self.max_deceleration * dt * 100
            if abs(left_diff) > max_change:
                left_diff = np.sign(left_diff) * max_change
        if abs(self.right_target) < abs(self.right_speed):
            max_change = self.max_deceleration * dt * 100
            if abs(right_diff) > max_change:
                right_diff = np.sign(right_diff) * max_change

        self.left_speed += left_diff * self.left_calibration
        self.right_speed += right_diff * self.right_calibration

        if abs(self.left_target - self.right_target) < 0.1:
            noise = np.random.normal(0, self.speed_noise)
            self.left_speed += noise
            self.right_speed += noise
        else:
            self.left_speed += np.random.normal(0, self.speed_noise)
            self.right_speed += np.random.normal(0, self.speed_noise)

        self.left_speed = np.clip(self.left_speed, -100.0, 100.0)
        self.right_speed = np.clip(self.right_speed, -100.0, 100.0)

        self.command_history.append((time.time(), self.left_speed, self.right_speed))
        if len(self.command_history) > 1000:
            self.command_history.pop(0)

    def stop(self):
        self.left_target = 0.0
        self.right_target = 0.0
        self.is_running = False

    def get_speeds(self):
        current_time = time.time()
        dt = current_time - self.last_update_time
        if dt > 0:
            self._update_speeds(dt)
            self.last_update_time = current_time
        return self.left_speed, self.right_speed

    def get_current_speeds(self):
        return self.left_speed, self.right_speed

    def emergency_stop(self):
        self.left_speed = 0.0
        self.right_speed = 0.0
        self.left_target = 0.0
        self.right_target = 0.0
        self.is_running = False

    def get_status(self):
        return {
            'left_speed': self.left_speed,
            'right_speed': self.right_speed,
            'left_target': self.left_target,
            'right_target': self.right_target,
            'running': self.is_running,
            'left_calibration': self.left_calibration,
            'right_calibration': self.right_calibration,
        }

    def calibrate(self, left_multiplier: float = 1.0, right_multiplier: float = 1.0):
        self.left_calibration = left_multiplier
        self.right_calibration = right_multiplier


MockMotorController = EnhancedMockMotorController


class MockSensorManager:
    """Mock sensor manager with simulated obstacle detection and LIDAR scan."""

    def __init__(self):
        self.robot_pose = (0.0, 0.0, 0.0)
        self.obstacles = []
        self.sensor_angles = {
            'front': 0.0,
            'left': math.pi / 2,
            'right': -math.pi / 2,
        }
        self.max_range = 2.0
        self.lidar_num_rays = 72
        self.lidar_angle_step = 5

    def set_robot_pose(self, x, y, theta):
        self.robot_pose = (x, y, theta)

    def set_obstacles(self, obstacles):
        self.obstacles = obstacles

    def _distance_to_obstacle(self, angle_offset):
        x, y, theta = self.robot_pose
        angle = theta + angle_offset
        min_dist = self.max_range
        for ox, oy, r in self.obstacles:
            dx = math.cos(angle)
            dy = math.sin(angle)
            fx = ox - x
            fy = oy - y
            proj = fx * dx + fy * dy
            if proj < 0:
                continue
            closest_x = x + proj * dx
            closest_y = y + proj * dy
            dist_to_center = math.hypot(closest_x - ox, closest_y - oy)
            if dist_to_center < r:
                dist = proj - math.sqrt(r**2 - dist_to_center**2)
                if 0 < dist < min_dist:
                    min_dist = dist
        return min_dist

    def get_lidar_scan(self):
        scan = []
        for i in range(self.lidar_num_rays):
            angle_deg = i * self.lidar_angle_step
            angle_rad = math.radians(angle_deg)
            dist = self._distance_to_obstacle(angle_rad)
            scan.append((angle_deg, dist))
        return scan

    def get_sensor_data(self):
        readings = {}
        for name, angle in self.sensor_angles.items():
            dist = self._distance_to_obstacle(angle)
            readings[name] = SensorReading(value=dist, timestamp=time.time(), valid=True)
        lidar_scan = self.get_lidar_scan()
        return {
            'ultrasonic': readings,
            'infrared': {'left': False, 'right': False},
            'bumper': {'left': False, 'right': False},
            'lidar_scan': lidar_scan,
        }

    def collect(self):
        pass
