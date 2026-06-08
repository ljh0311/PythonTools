#!/usr/bin/env python3
"""
Test script for sensor availability checking functionality
"""

import sys
import os
import time

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.hardware.sensor_manager import SensorManager

def test_sensor_availability():
    """Test the sensor availability checking functionality"""
    
    # Create a minimal config for testing
    config = {
        'hardware': {
            'sensors': {
                'ultrasonic_front': 18,
                'ultrasonic_left': 23,
                'ultrasonic_right': 24,
                'infrared_left': 25,
                'infrared_right': 8,
                'bumper_left': 7,
                'bumper_right': 12
            }
        },
        'control': {
            'gui_update_rate': 10
        },
        'robot': {
            'safety_distances': {
                'critical': 0.15
            }
        }
    }
    
    print("=== Sensor Availability Test ===\n")
    
    try:
        # Initialize sensor manager
        print("Initializing sensor manager...")
        sensor_manager = SensorManager(config)
        
        # Start sensor manager
        print("Starting sensor manager...")
        sensor_manager.start()
        
        # Give sensors time to initialize
        time.sleep(2)
        
        # Test sensor availability checking
        print("\n--- Checking Sensor Availability ---")
        availability = sensor_manager.check_sensor_availability()
        
        print(f"Overall Status: {availability['overall_status']}")
        print(f"Hardware Available: {availability['hardware_available']}")
        
        if 'summary' in availability:
            summary = availability['summary']
            print(f"Total Sensors: {summary['total_sensors']}")
            print(f"Available Sensors: {summary['available_sensors']}")
            print(f"Ultrasonic Available: {summary['ultrasonic_available']}/3")
            print(f"Infrared Available: {summary['infrared_available']}/2")
            print(f"Bumper Available: {summary['bumper_available']}/2")
        
        # Test health message
        print(f"\nHealth Message: {sensor_manager.get_sensor_health_message()}")
        
        # Test system health
        print(f"System Healthy: {sensor_manager.is_system_healthy()}")
        
        # Test unavailable sensors
        unavailable = sensor_manager.get_unavailable_sensors()
        if unavailable:
            print(f"\nUnavailable Sensors: {', '.join(unavailable)}")
        else:
            print("\nAll sensors are available!")
        
        # Test sensor data access
        print("\n--- Testing Sensor Data Access ---")
        sensor_data = sensor_manager.get_sensor_data()
        
        print("Sensor Data Structure:")
        for sensor_type, sensors in sensor_data.items():
            if sensor_type != 'timestamp':
                print(f"  {sensor_type}:")
                for sensor_name, reading in sensors.items():
                    status = "Valid" if reading.valid else "Invalid"
                    print(f"    {sensor_name}: {reading.value} ({status})")
        
        # Test individual sensor access
        print("\n--- Testing Individual Sensor Access ---")
        front_distance = sensor_manager.get_ultrasonic_distance('front')
        left_obstacle = sensor_manager.get_infrared_obstacle('left')
        left_bumper = sensor_manager.get_bumper_pressed('left')
        
        print(f"Front Distance: {front_distance:.1f} cm")
        print(f"Left Infrared Obstacle: {left_obstacle}")
        print(f"Left Bumper Pressed: {left_bumper}")
        
        # Test obstacle detection
        print(f"\nObstacle Detected: {sensor_manager.is_obstacle_detected()}")
        print(f"Minimum Distance: {sensor_manager.get_min_distance():.1f} cm")
        
        # Test sensor status
        print("\n--- Testing Sensor Status ---")
        status = sensor_manager.get_sensor_status()
        print("Sensor Status:")
        for key, value in status.items():
            if key not in ['last_update', 'hardware_available']:
                print(f"  {key}: {value}")
        
        # Stop sensor manager
        print("\nStopping sensor manager...")
        sensor_manager.stop()
        
        print("\n=== Test Completed Successfully ===")
        
    except Exception as e:
        print(f"Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_sensor_availability() 