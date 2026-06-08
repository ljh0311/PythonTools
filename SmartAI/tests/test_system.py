#!/usr/bin/env python3
"""
Test Script for Smart Robot System
Tests all components in simulation mode
"""

import sys
import os
import time
import yaml
from loguru import logger

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.core.robot_state import RobotState, RobotMode, Position
from src.hardware.motor_controller import MotorController
from src.hardware.sensor_manager import SensorManager
from src.navigation.pathfinder import Pathfinder
from src.navigation.autonomous_controller import AutonomousController


def test_robot_state():
    """Test robot state management"""
    logger.info("Testing Robot State...")
    
    # Load config
    with open("config/robot_config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # Create robot state
    robot_state = RobotState(config)
    
    # Test position updates
    robot_state.update_position(10, 20, 0.5)
    assert robot_state.position.x == 10
    assert robot_state.position.y == 20
    assert robot_state.position.theta == 0.5
    
    # Test mode changes
    robot_state.set_mode(RobotMode.MANUAL)
    assert robot_state.mode == RobotMode.MANUAL
    
    # Test status summary
    status = robot_state.get_status_summary()
    assert 'mode' in status
    assert 'position' in status
    
    logger.info("✓ Robot State tests passed")


def test_motor_controller():
    """Test motor controller"""
    logger.info("Testing Motor Controller...")
    
    # Load config
    with open("config/robot_config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # Create motor controller
    motor_controller = MotorController(config)
    
    # Test speed setting
    motor_controller.set_speeds(50, 50)
    left_speed, right_speed = motor_controller.get_current_speeds()
    assert left_speed == 50
    assert right_speed == 50
    
    # Test movement commands
    motor_controller.move_forward(30)
    left_speed, right_speed = motor_controller.get_current_speeds()
    assert left_speed == 30
    assert right_speed == 30
    
    motor_controller.stop_motors()
    left_speed, right_speed = motor_controller.get_current_speeds()
    assert left_speed == 0
    assert right_speed == 0
    
    logger.info("✓ Motor Controller tests passed")


def test_sensor_manager():
    """Test sensor manager"""
    logger.info("Testing Sensor Manager...")
    
    # Load config
    with open("config/robot_config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # Create sensor manager
    sensor_manager = SensorManager(config)
    
    # Test sensor data
    sensor_data = sensor_manager.get_sensor_data()
    assert 'ultrasonic' in sensor_data
    assert 'infrared' in sensor_data
    assert 'bumper' in sensor_data
    
    # Test individual sensor readings
    distance = sensor_manager.get_ultrasonic_distance('front')
    assert isinstance(distance, float)
    
    obstacle = sensor_manager.get_infrared_obstacle('left')
    assert isinstance(obstacle, bool)
    
    logger.info("✓ Sensor Manager tests passed")


def test_pathfinder():
    """Test pathfinding system"""
    logger.info("Testing Pathfinder...")
    
    # Load config
    with open("config/robot_config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # Create pathfinder
    pathfinder = Pathfinder(config)
    
    # Test coordinate conversion
    grid_x, grid_y = pathfinder.world_to_grid(100, 200)
    world_x, world_y = pathfinder.grid_to_world(grid_x, grid_y)
    assert abs(world_x - 100) < 10  # Within grid resolution
    assert abs(world_y - 200) < 10
    
    # Test path finding
    path = pathfinder.find_path(0, 0, 100, 100)
    assert isinstance(path, list)
    
    # Test grid status
    status = pathfinder.get_grid_status()
    assert 'grid' in status
    assert 'exploration_percentage' in status
    
    logger.info("✓ Pathfinder tests passed")


def test_autonomous_controller():
    """Test autonomous controller"""
    logger.info("Testing Autonomous Controller...")
    
    # Load config
    with open("config/robot_config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # Create components
    robot_state = RobotState(config)
    motor_controller = MotorController(config)
    sensor_manager = SensorManager(config)
    pathfinder = Pathfinder(config)
    
    # Create autonomous controller
    autonomous_controller = AutonomousController(
        robot_state, motor_controller, sensor_manager, pathfinder
    )
    
    # Test navigation commands
    autonomous_controller.navigate_to(200, 300)
    status = autonomous_controller.get_status()
    assert status['navigation_state'] == 'planning'
    
    # Test exploration
    autonomous_controller.start_exploration()
    status = autonomous_controller.get_status()
    assert status['exploration_mode'] == True
    
    logger.info("✓ Autonomous Controller tests passed")


def test_integration():
    """Test system integration"""
    logger.info("Testing System Integration...")
    
    # Load config
    with open("config/robot_config.yaml", 'r') as f:
        config = yaml.safe_load(f)
    
    # Create all components
    robot_state = RobotState(config)
    motor_controller = MotorController(config)
    sensor_manager = SensorManager(config)
    pathfinder = Pathfinder(config)
    autonomous_controller = AutonomousController(
        robot_state, motor_controller, sensor_manager, pathfinder
    )
    
    # Test component interaction
    robot_state.set_mode(RobotMode.AUTONOMOUS)
    autonomous_controller.navigate_to(500, 500)
    
    # Simulate some sensor updates
    for i in range(5):
        sensor_data = sensor_manager.get_sensor_data()
        robot_state.update_sensors(sensor_data['ultrasonic']['front'])
        time.sleep(0.1)
    
    # Check system status
    status = autonomous_controller.get_status()
    assert status['navigation_state'] in ['planning', 'following_path', 'idle']
    
    logger.info("✓ Integration tests passed")


def main():
    """Run all tests"""
    logger.info("Starting Smart Robot System Tests...")
    
    try:
        # Test individual components
        test_robot_state()
        test_motor_controller()
        test_sensor_manager()
        test_pathfinder()
        test_autonomous_controller()
        
        # Test integration
        test_integration()
        
        logger.info("🎉 All tests passed! System is ready for use.")
        
    except Exception as e:
        logger.error(f"❌ Test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 