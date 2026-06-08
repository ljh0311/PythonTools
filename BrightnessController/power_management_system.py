"""
Unified OOP system that combines battery monitoring and brightness control.
"""

from dataclasses import dataclass
from typing import Optional

from battery_monitor import BatteryMonitor
from battery_provider import BatterySnapshot
from charge_cycle_repository import ChargeCycleRepository
from brightness_controller import BrightnessController
from brightness_policy import BatteryBrightnessPolicyConfig
from power_aware_controller import PowerAwareBrightnessController, PowerAwareResult


@dataclass
class PowerManagementStatus:
    snapshot: Optional[BatterySnapshot]
    policy_enabled: bool


class PowerManagementSystem:
    """Facade that exposes one cohesive power + brightness API."""

    def __init__(self, brightness_controller: BrightnessController):
        self.brightness_controller = brightness_controller
        self.battery_monitor = BatteryMonitor()
        self.charge_cycle_repository = ChargeCycleRepository()
        self.power_aware_controller = PowerAwareBrightnessController(
            brightness_controller=self.brightness_controller,
            battery_provider=self.battery_monitor.provider,
        )

    def set_policy(self, config: BatteryBrightnessPolicyConfig) -> None:
        self.power_aware_controller.update_policy_config(config)

    def apply_brightness(self, raw_brightness: float) -> PowerAwareResult:
        return self.power_aware_controller.adjust_screen_brightness(raw_brightness)

    def get_status(self) -> PowerManagementStatus:
        return PowerManagementStatus(
            snapshot=self.battery_monitor.get_snapshot(),
            policy_enabled=self.power_aware_controller.policy_config.enabled,
        )

    def get_charge_cycle_data(self):
        """Return persisted charge/discharge history."""
        return self.charge_cycle_repository.load()
