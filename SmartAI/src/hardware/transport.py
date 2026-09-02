"""Hardware transport interfaces for plug-and-play motor/sensor backends."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Tuple


class MotorTransport(ABC):
    """Abstract motor control surface — LLM/tools must never bypass this."""

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def set_speeds(self, left: float, right: float) -> None: ...

    @abstractmethod
    def move_forward(self, speed: float = 50.0) -> None: ...

    @abstractmethod
    def move_backward(self, speed: float = 50.0) -> None: ...

    @abstractmethod
    def turn_left(self, speed: float = 30.0) -> None: ...

    @abstractmethod
    def turn_right(self, speed: float = 30.0) -> None: ...

    @abstractmethod
    def stop_motors(self) -> None: ...

    @abstractmethod
    def differential_drive(self, linear_speed: float, angular_speed: float) -> None: ...

    @abstractmethod
    def emergency_stop(self) -> None: ...

    @abstractmethod
    def get_status(self) -> Dict[str, Any]: ...


class SensorTransport(ABC):
    """Abstract sensor read surface."""

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def get_sensor_data(self) -> dict: ...

    @abstractmethod
    def get_sensor_status(self) -> Dict[str, Any]: ...


class HardwareTransport(ABC):
    """Combined hardware backend (motors + sensors)."""

    @property
    @abstractmethod
    def motors(self) -> MotorTransport: ...

    @property
    @abstractmethod
    def sensors(self) -> SensorTransport: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def get_backend_name(self) -> str: ...
