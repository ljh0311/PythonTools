"""
Speed Verification Test
Verifies that the robot moves at 3 km/h (0.83 m/s) in normal conditions
"""

import sys
import os
import time
import math

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.navigation.autonomous_controller import AutonomousController, NavigationGoal
from src.core.robot_state import RobotState, Position
from src.hardware.motor_controller import MotorController
from src.hardware.sensor_manager import SensorManager
from src.navigation.pathfinder import Pathfinder

class SpeedVerificationTester:
    """Test class for speed verification"""
    
    def __init__(self):
        # Create configuration
        config_dict = {
            'navigation': {
                'grid_size': 0.2,
                'map_width': 10.0,
                'map_height': 10.0
            },
            'robot': {
                'width': 0.3,
                'length': 0.4,
                'max_speed': 0.83,  # 3 km/h
                'turn_speed': 0.3,
                'safety_distances': {
                    'comfortable': 0.8,
                    'warning': 0.4,
                    'critical': 0.15
                }
            },
            'control': {
                'gui_update_rate': 20
            },
            'hardware': {
                'sensors': {
                    'ultrasonic_front': 17,
                    'ultrasonic_left': 18,
                    'ultrasonic_right': 19,
                    'infrared_left': 20,
                    'infrared_right': 21,
                    'bumper_left': 22,
                    'bumper_right': 23
                }
            }
        }
        
        # Initialize components
        self.robot_state = RobotState(config_dict)
        self.motor_controller = MockMotorController()
        self.sensor_manager = MockSensorManager()
        self.pathfinder = Pathfinder(config_dict)
        self.autonomous_controller = AutonomousController(
            self.robot_state, self.motor_controller, 
            self.sensor_manager, self.pathfinder
        )
        
    def test_normal_speed(self):
        """Test that robot moves at normal speed (3 km/h) when no obstacles are present"""
        print("Testing Normal Speed (3 km/h)")
        print("=" * 40)
        
        # Set robot in open area with no obstacles
        self.robot_state.reset_position(1.0, 5.0, 0.0)
        self.sensor_manager.set_robot_pose(1.0, 5.0, 0.0)
        self.sensor_manager.set_obstacles([])  # No obstacles
        
        # Start the autonomous controller
        self.autonomous_controller.start()
        
        # Start wandering
        self.autonomous_controller.start_exploration()
        
        # Run for a few seconds and measure speed
        start_time = time.time()
        start_pos = self.robot_state.get_position()
        
        print("Starting speed measurement...")
        print("Time | Position | Speed (m/s) | Speed (km/h) | Speed Scale")
        print("-" * 60)
        
        for i in range(20):  # 2 seconds at 10Hz
            time.sleep(0.1)
            
            # Update robot physics
            self._update_robot_physics()
            
            # Get current status
            nav_status = self.autonomous_controller.get_navigation_status()
            current_pos = self.robot_state.get_position()
            
            # Calculate speed
            elapsed = time.time() - start_time
            distance = math.hypot(current_pos.x - start_pos.x, current_pos.y - start_pos.y)
            speed_mps = distance / elapsed if elapsed > 0 else 0
            speed_kmh = speed_mps * 3.6
            
            # Get speed scale
            adaptive_speed = nav_status.get('adaptive_speed', {})
            speed_scale = adaptive_speed.get('current_scale', 1.0)
            
            print(f"{elapsed:.1f}s | ({current_pos.x:.2f}, {current_pos.y:.2f}) | {speed_mps:.3f} | {speed_kmh:.1f} | {speed_scale:.2f}")
            
            # Update start position for next iteration
            start_pos = current_pos
            start_time = time.time()
        
        # Stop
        self.autonomous_controller.stop()
        
        print("\nSpeed Test Results:")
        print(f"Target speed: 0.83 m/s (3.0 km/h)")
        print(f"Expected speed scale: 1.0 (no obstacles)")
        
    def test_adaptive_speed(self):
        """Test adaptive speed control with obstacles"""
        print("\nTesting Adaptive Speed Control")
        print("=" * 40)
        
        # Set robot with obstacles on the sides
        self.robot_state.reset_position(1.0, 5.0, 0.0)
        self.sensor_manager.set_robot_pose(1.0, 5.0, 0.0)
        
        # Add obstacles on the sides
        obstacles = [
            (1.5, 4.0, 0.3),  # Left side obstacle
            (1.5, 6.0, 0.3),  # Right side obstacle
        ]
        self.sensor_manager.set_obstacles(obstacles)
        
        # Start the autonomous controller
        self.autonomous_controller.start()
        
        # Start wandering
        self.autonomous_controller.start_exploration()
        
        print("Testing adaptive speed with side obstacles...")
        print("Time | Position | Speed Scale | L Dist | R Dist | F Dist")
        print("-" * 65)
        
        for i in range(15):  # 1.5 seconds at 10Hz
            time.sleep(0.1)
            
            # Update robot physics
            self._update_robot_physics()
            
            # Get current status
            nav_status = self.autonomous_controller.get_navigation_status()
            current_pos = self.robot_state.get_position()
            
            # Get sensor data and speed scale
            adaptive_speed = nav_status.get('adaptive_speed', {})
            speed_scale = adaptive_speed.get('current_scale', 1.0)
            left_dist = adaptive_speed.get('left_distance', 0.0)
            right_dist = adaptive_speed.get('right_distance', 0.0)
            front_dist = adaptive_speed.get('front_distance', 0.0)
            
            print(f"{i*0.1:.1f}s | ({current_pos.x:.2f}, {current_pos.y:.2f}) | {speed_scale:.2f} | {left_dist:.2f}m | {right_dist:.2f}m | {front_dist:.2f}m")
        
        # Stop
        self.autonomous_controller.stop()
        
        print("\nAdaptive Speed Test Results:")
        print(f"Safe distance: {self.autonomous_controller.safe_distance}m")
        print(f"Min safe distance: {self.autonomous_controller.min_safe_distance}m")
        print(f"Min speed scale: {self.autonomous_controller.min_speed_scale}")
        
    def _update_robot_physics(self):
        """Update robot position based on motor commands"""
        left_speed, right_speed = self.motor_controller.get_speeds()
        
        if abs(left_speed) < 0.01 and abs(right_speed) < 0.01:
            return  # Robot is stopped
        
        # Simple physics simulation
        current_pos = self.robot_state.get_position()
        
        # Convert wheel speeds to linear and angular velocities
        wheel_base = 0.25  # Distance between wheels
        linear_vel = (left_speed + right_speed) / 100.0  # Convert from percentage to m/s (divide by 100, not 200)
        angular_vel = (right_speed - left_speed) / (100.0 * wheel_base)  # Angular velocity
        
        # Update position
        dt = 0.1  # Time step
        new_x = current_pos.x + linear_vel * math.cos(current_pos.theta) * dt
        new_y = current_pos.y + linear_vel * math.sin(current_pos.theta) * dt
        new_theta = current_pos.theta + angular_vel * dt
        
        # Keep theta in [-pi, pi]
        new_theta = math.atan2(math.sin(new_theta), math.cos(new_theta))
        
        # Update robot state
        self.robot_state.update_position(new_x - current_pos.x, new_y - current_pos.y, new_theta - current_pos.theta)
        
        # Update sensor manager
        self.sensor_manager.set_robot_pose(new_x, new_y, new_theta)


class MockMotorController:
    """Mock motor controller for testing"""
    
    def __init__(self):
        self.left_speed = 0.0
        self.right_speed = 0.0
    
    def set_speeds(self, left: float, right: float):
        self.left_speed = left
        self.right_speed = right
    
    def stop(self):
        self.left_speed = 0.0
        self.right_speed = 0.0
    
    def get_speeds(self):
        return self.left_speed, self.right_speed


class MockSensorManager:
    """Mock sensor manager for testing"""
    
    def __init__(self):
        self.robot_pose = (0.0, 0.0, 0.0)
        self.obstacles = []
        self.sensor_angles = {
            'front': 0.0,
            'left': math.pi / 2,
            'right': -math.pi / 2
        }
        self.max_range = 2.0
    
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
            if dist_to_center <= r:
                dist = proj - math.sqrt(r*r - dist_to_center*dist_to_center)
                if dist < min_dist:
                    min_dist = dist
        
        return min_dist if min_dist < self.max_range else self.max_range
    
    def get_sensor_data(self):
        timestamp = time.time()
        return {
            'ultrasonic': {
                'front': SensorReading(self._distance_to_obstacle(0.0), timestamp),
                'left': SensorReading(self._distance_to_obstacle(math.pi/2), timestamp),
                'right': SensorReading(self._distance_to_obstacle(-math.pi/2), timestamp)
            },
            'infrared': {
                'left': SensorReading(0.0, timestamp),
                'right': SensorReading(0.0, timestamp)
            },
            'bumper': {
                'left': SensorReading(0.0, timestamp),
                'right': SensorReading(0.0, timestamp)
            },
            'timestamp': timestamp
        }
    
    def is_obstacle_detected(self):
        """Check if any obstacle is detected"""
        min_distance = min([
            self._distance_to_obstacle(0.0),
            self._distance_to_obstacle(math.pi/2),
            self._distance_to_obstacle(-math.pi/2)
        ])
        return min_distance < 0.15  # Critical distance


class SensorReading:
    """Mock sensor reading"""
    def __init__(self, value, timestamp):
        self.value = value
        self.timestamp = timestamp


def main():
    """Main function to run the speed verification test"""
    print("Speed Verification Test")
    print("Verifying robot moves at 3 km/h (0.83 m/s) in normal conditions")
    print()
    
    tester = SpeedVerificationTester()
    
    # Test normal speed
    tester.test_normal_speed()
    
    # Test adaptive speed
    tester.test_adaptive_speed()
    
    print("\nTest completed!")


if __name__ == "__main__":
    main() 