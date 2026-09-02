"""Motor trim calibration and adaptive learning for straight-line driving."""

import json
import os
import threading
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional, Tuple

from loguru import logger

DEFAULT_CALIBRATION_PATH = "config/motor_calibration.json"
IMBALANCE_THRESHOLD = 1.0
TRIM_MIN = 0.5
TRIM_MAX = 1.5


@dataclass
class MotorTrim:
    left_trim: float = 1.0
    right_trim: float = 1.0
    auto_calibrate_on_startup: bool = False

    def clamp(self, lo: float = TRIM_MIN, hi: float = TRIM_MAX) -> "MotorTrim":
        self.left_trim = max(lo, min(hi, self.left_trim))
        self.right_trim = max(lo, min(hi, self.right_trim))
        return self


def load_motor_trim(path: str = DEFAULT_CALIBRATION_PATH) -> MotorTrim:
    if not os.path.exists(path):
        return MotorTrim()
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        return MotorTrim(
            left_trim=float(data.get("left_trim", data.get("left_calibration", 1.0))),
            right_trim=float(data.get("right_trim", data.get("right_calibration", 1.0))),
            auto_calibrate_on_startup=bool(data.get("auto_calibrate_on_startup", False)),
        )
    except Exception as exc:
        logger.warning(f"Failed to load motor calibration from {path}: {exc}")
        return MotorTrim()


def save_motor_trim(trim: MotorTrim, path: str = DEFAULT_CALIBRATION_PATH) -> None:
    directory = os.path.dirname(path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(asdict(trim), handle, indent=2)


def should_auto_calibrate(config: Dict[str, Any], path: str = DEFAULT_CALIBRATION_PATH) -> bool:
    """Resolve auto-calibrate flag from persisted JSON, then YAML config."""
    trim = load_motor_trim(path)
    if trim.auto_calibrate_on_startup:
        return True
    cal_config = config.get("motor_calibration", {})
    return bool(cal_config.get("auto_calibrate_on_startup", False))


def _read_speeds(motor) -> Tuple[float, float]:
    if hasattr(motor, "get_actual_speeds"):
        return motor.get_actual_speeds()
    if hasattr(motor, "get_speeds"):
        return motor.get_speeds()
    return motor.get_current_speeds()


class MotorTrimLearner:
    """Learn left/right trim from straight-line speed imbalance."""

    def __init__(
        self,
        motor,
        command_speed: float = 50.0,
        settle_steps: int = 20,
        step_sleep: float = 0.01,
        max_iterations: int = 5,
        imbalance_threshold: float = IMBALANCE_THRESHOLD,
    ):
        self.motor = motor
        self.command_speed = command_speed
        self.settle_steps = settle_steps
        self.step_sleep = step_sleep
        self.max_iterations = max_iterations
        self.imbalance_threshold = imbalance_threshold

    def _get_trim(self) -> MotorTrim:
        if hasattr(self.motor, "left_trim"):
            return MotorTrim(self.motor.left_trim, self.motor.right_trim)
        if hasattr(self.motor, "left_calibration"):
            return MotorTrim(self.motor.left_calibration, self.motor.right_calibration)
        return MotorTrim()

    def _apply_trim(self, trim: MotorTrim) -> None:
        if hasattr(self.motor, "calibrate"):
            self.motor.calibrate(trim.left_trim, trim.right_trim)
        elif hasattr(self.motor, "left_trim"):
            self.motor.left_trim = trim.left_trim
            self.motor.right_trim = trim.right_trim

    def _reset_speeds(self) -> None:
        if hasattr(self.motor, "stop_motors"):
            self.motor.stop_motors()
        elif hasattr(self.motor, "left_speed"):
            self.motor.left_speed = 0.0
            self.motor.right_speed = 0.0

    def measure_imbalance(self) -> Tuple[float, float, float]:
        self.motor.set_speeds(self.command_speed, self.command_speed)
        for _ in range(self.settle_steps):
            if hasattr(self.motor, "get_speeds"):
                self.motor.get_speeds()
            time.sleep(self.step_sleep)
        left, right = _read_speeds(self.motor)
        return abs(left - right), left, right

    def learn(self) -> MotorTrim:
        trim = self._get_trim()
        imbalance = float("inf")

        for _ in range(self.max_iterations):
            imbalance, left, right = self.measure_imbalance()
            if imbalance <= self.imbalance_threshold or left <= 0 or right <= 0:
                break

            avg = (left + right) / 2.0
            trim.left_trim *= avg / left
            trim.right_trim *= avg / right
            trim.clamp()
            self._apply_trim(trim)
            self._reset_speeds()

        logger.info(
            "Motor trim learned: left={:.3f}, right={:.3f}, final imbalance={:.2f}",
            trim.left_trim,
            trim.right_trim,
            imbalance,
        )
        return trim


def run_startup_calibration(motor, config: Dict[str, Any]) -> Optional[MotorTrim]:
    """Run trim learning once at startup when enabled in config."""
    cal_config = config.get("motor_calibration", {})
    path = cal_config.get("calibration_file", DEFAULT_CALIBRATION_PATH)

    if not should_auto_calibrate(config, path):
        return None

    if getattr(motor, "hardware_available", False) and not hasattr(motor, "get_actual_speeds"):
        logger.info(
            "Startup motor calibration skipped: no speed feedback on hardware without encoders"
        )
        return None

    logger.info("Running startup motor trim calibration...")
    learner = MotorTrimLearner(
        motor,
        command_speed=float(cal_config.get("calibration_speed", 50.0)),
        max_iterations=int(cal_config.get("max_calibration_iterations", 5)),
    )
    trim = learner.learn()
    learner._reset_speeds()

    persisted = load_motor_trim(path)
    trim.auto_calibrate_on_startup = persisted.auto_calibrate_on_startup
    save_motor_trim(trim, path)
    return trim


def run_calibration_async(motor, config: Dict[str, Any], on_complete=None) -> threading.Thread:
    """Run calibration in a background thread (for GUI / startup)."""

    def _worker():
        try:
            trim = run_manual_calibration(motor, config)
            if on_complete:
                on_complete(trim, None)
        except Exception as exc:
            logger.error(f"Motor calibration failed: {exc}")
            if on_complete:
                on_complete(None, exc)

    thread = threading.Thread(target=_worker, daemon=True)
    thread.start()
    return thread


def run_manual_calibration(motor, config: Dict[str, Any]) -> MotorTrim:
    """Run trim learning on demand (GUI button / API)."""
    cal_config = config.get("motor_calibration", {})
    path = cal_config.get("calibration_file", DEFAULT_CALIBRATION_PATH)

    if getattr(motor, "hardware_available", False) and not hasattr(motor, "get_actual_speeds"):
        raise RuntimeError(
            "Auto-calibration needs wheel speed feedback. Use manual trim sliders on hardware."
        )

    learner = MotorTrimLearner(
        motor,
        command_speed=float(cal_config.get("calibration_speed", 50.0)),
        max_iterations=int(cal_config.get("max_calibration_iterations", 5)),
    )
    trim = learner.learn()
    learner._reset_speeds()

    persisted = load_motor_trim(path)
    trim.auto_calibrate_on_startup = persisted.auto_calibrate_on_startup
    save_motor_trim(trim, path)
    return trim


def set_auto_calibrate_on_startup(enabled: bool, path: str = DEFAULT_CALIBRATION_PATH) -> MotorTrim:
    trim = load_motor_trim(path)
    trim.auto_calibrate_on_startup = enabled
    save_motor_trim(trim, path)
    return trim
