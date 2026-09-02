"""Factory for hardware transport backends."""

from typing import Dict, Type

from .adapters import GpioHardwareTransport
from .transport import HardwareTransport

_REGISTRY: Dict[str, Type[HardwareTransport]] = {
    "gpio": GpioHardwareTransport,
    "simulation": GpioHardwareTransport,
    "rpi": GpioHardwareTransport,
}


def register_transport(name: str, cls: Type[HardwareTransport]) -> None:
  _REGISTRY[name.lower()] = cls


def create_hardware_transport(config: dict) -> HardwareTransport:
  backend = config.get("hardware", {}).get("transport", "gpio")
  cls = _REGISTRY.get(backend.lower())
  if cls is None:
    raise ValueError(f"Unknown hardware transport: {backend}. Available: {list(_REGISTRY)}")
  return cls(config)
