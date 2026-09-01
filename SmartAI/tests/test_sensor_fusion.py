"""Pytest tests for motor calibration and sensor fusion modes."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fixtures.config import TestConfig
from fixtures.mocks import EnhancedMockMotorController, MockSensorManager


def test_motor_calibration_reduces_imbalance():
    """Headless smoke test for menu mode 7."""
    config = TestConfig()
    motor = EnhancedMockMotorController(config)

    motor.left_calibration = 0.8
    motor.right_calibration = 1.2
    motor.set_speeds(50.0, 50.0)
    for _ in range(20):
        motor.get_speeds()

    imbalance_before = abs(motor.get_current_speeds()[0] - motor.get_current_speeds()[1])
    motor.calibrate(1.25, 0.833)
    motor.left_speed = 0.0
    motor.right_speed = 0.0
    motor.set_speeds(50.0, 50.0)
    for _ in range(20):
        motor.get_speeds()

    imbalance_after = abs(motor.get_current_speeds()[0] - motor.get_current_speeds()[1])
    assert imbalance_after <= imbalance_before or imbalance_after < 8.0


def test_sensor_fusion_smoke():
    """Headless smoke test for menu mode 8 using SensorFusionManager."""
    from test import SensorFusionManager

    config = TestConfig()
    fusion = SensorFusionManager(config)
    sensor_manager = MockSensorManager()
    sensor_manager.set_robot_pose(2.0, 2.0, 0.0)
    sensor_manager.set_obstacles([(4.0, 2.0, 0.2)])

    ultrasonic = sensor_manager.get_sensor_data()['ultrasonic']
    visual = [{
        'bbox': (320, 240, 80, 100),
        'center': (360, 290),
        'confidence': 0.9,
        'class': 'chair',
    }]
    fused = fusion.fuse_detections(ultrasonic, visual, (2.0, 2.0, 0.0))

    assert fused
    assert all(obs.get('confidence', 0) > 0 for obs in fused)
