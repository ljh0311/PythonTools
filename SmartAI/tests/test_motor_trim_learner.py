"""Tests for adaptive motor trim learning."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fixtures.config import TestConfig
from fixtures.mocks import EnhancedMockMotorController
from src.hardware.motor_calibration import MotorTrimLearner, load_motor_trim, save_motor_trim, MotorTrim


def test_motor_trim_learner_reduces_imbalance():
    config = TestConfig()
    motor = EnhancedMockMotorController(config)
    motor.left_calibration = 0.8
    motor.right_calibration = 1.2

    learner = MotorTrimLearner(motor)
    imbalance_before, _, _ = learner.measure_imbalance()
    trim = learner.learn()
    imbalance_after, _, _ = learner.measure_imbalance()

    assert trim.left_trim != 1.0 or trim.right_trim != 1.0
    assert imbalance_after <= imbalance_before or imbalance_after < 8.0


def test_motor_trim_persistence(tmp_path):
    path = tmp_path / "motor_calibration.json"
    save_motor_trim(MotorTrim(1.1, 0.9), str(path))
    loaded = load_motor_trim(str(path))
    assert loaded.left_trim == 1.1
    assert loaded.right_trim == 0.9
