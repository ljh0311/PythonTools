"""
Unified power-management package.

Combines battery monitoring and brightness control with modular OOP components.
"""

from battery_monitor import BatteryMonitor
from brightness_controller import BrightnessController, HumanDetector
from charge_cycle_repository import ChargeCycleRepository
from brightness_policy import BatteryBrightnessPolicyConfig, PolicyDecision
from power_aware_controller import PowerAwareBrightnessController, PowerAwareResult
from power_management_system import PowerManagementSystem

__all__ = [
    "BatteryMonitor",
    "BrightnessController",
    "HumanDetector",
    "ChargeCycleRepository",
    "BatteryBrightnessPolicyConfig",
    "PolicyDecision",
    "PowerAwareBrightnessController",
    "PowerAwareResult",
    "PowerManagementSystem",
]
