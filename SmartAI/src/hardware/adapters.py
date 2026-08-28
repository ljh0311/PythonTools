"""Adapters wrapping existing MotorController / SensorManager to transport interfaces."""

from typing import Any, Dict

from .motor_controller import MotorController
from .sensor_manager import SensorManager
from .transport import HardwareTransport, MotorTransport, SensorTransport


class MotorControllerAdapter(MotorTransport):
  def __init__(self, controller: MotorController):
    self._c = controller

  def start(self) -> None:
    self._c.start()

  def stop(self) -> None:
    self._c.stop()

  def set_speeds(self, left: float, right: float) -> None:
    self._c.set_speeds(left, right)

  def move_forward(self, speed: float = 50.0) -> None:
    self._c.move_forward(speed)

  def move_backward(self, speed: float = 50.0) -> None:
    self._c.move_backward(speed)

  def turn_left(self, speed: float = 30.0) -> None:
    self._c.turn_left(speed)

  def turn_right(self, speed: float = 30.0) -> None:
    self._c.turn_right(speed)

  def stop_motors(self) -> None:
    self._c.stop_motors()

  def differential_drive(self, linear_speed: float, angular_speed: float) -> None:
    self._c.differential_drive(linear_speed, angular_speed)

  def emergency_stop(self) -> None:
    self._c.emergency_stop()

  def get_status(self) -> Dict[str, Any]:
    return self._c.get_status()

  @property
  def raw(self) -> MotorController:
    return self._c


class SensorManagerAdapter(SensorTransport):
  def __init__(self, manager: SensorManager):
    self._m = manager

  def start(self) -> None:
    self._m.start()

  def stop(self) -> None:
    self._m.stop()

  def get_sensor_data(self) -> dict:
    return self._m.get_sensor_data()

  def get_sensor_status(self) -> Dict[str, Any]:
    return self._m.get_sensor_status()

  @property
  def raw(self) -> SensorManager:
    return self._m


class GpioHardwareTransport(HardwareTransport):
  """RPi GPIO or simulation via existing controllers."""

  def __init__(self, config: dict):
    self._motors = MotorControllerAdapter(MotorController(config))
    self._sensors = SensorManagerAdapter(SensorManager(config))

  @property
  def motors(self) -> MotorTransport:
    return self._motors

  @property
  def sensors(self) -> SensorTransport:
    return self._sensors

  def start(self) -> None:
    self._motors.start()
    self._sensors.start()

  def stop(self) -> None:
    self._motors.stop()
    self._sensors.stop()

  def get_backend_name(self) -> str:
    return "gpio"
