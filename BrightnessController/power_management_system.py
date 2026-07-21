"""
Unified OOP system that combines battery monitoring and brightness control.
"""

from dataclasses import dataclass
from typing import Any, Callable, Dict, Optional

from battery_analytics import BatteryAnalytics, BatteryInsights
from battery_cycle_tracker import BatteryCycleTracker
from battery_monitor import BatteryMonitor
from battery_provider import BatterySnapshot
from charge_cycle_repository import ChargeCycleRepository
from brightness_controller import BrightnessController
from brightness_policy import BatteryBrightnessPolicyConfig
from desk_presence import PresenceState
from power_aware_controller import PowerAwareBrightnessController, PowerAwareResult


@dataclass
class PowerManagementStatus:
    snapshot: Optional[BatterySnapshot]
    policy_enabled: bool


class PowerManagementSystem:
    """Facade that exposes one cohesive power + brightness API."""

    def __init__(
        self,
        brightness_controller: BrightnessController,
        on_battery_data_changed: Optional[Callable[[], None]] = None,
    ):
        self.brightness_controller = brightness_controller
        self.battery_monitor = BatteryMonitor()
        self.charge_cycle_repository = ChargeCycleRepository()
        self.analytics = BatteryAnalytics()
        self.cycle_tracker = BatteryCycleTracker(
            repository=self.charge_cycle_repository,
            provider=self.battery_monitor.provider,
            analytics=self.analytics,
            on_data_changed=on_battery_data_changed,
        )
        self.power_aware_controller = PowerAwareBrightnessController(
            brightness_controller=self.brightness_controller,
            battery_provider=self.battery_monitor.provider,
        )

    def set_policy(self, config: BatteryBrightnessPolicyConfig) -> None:
        self.power_aware_controller.update_policy_config(config)

    def apply_brightness(
        self,
        raw_brightness: float,
        presence_state: Optional[PresenceState] = None,
    ) -> PowerAwareResult:
        return self.power_aware_controller.adjust_screen_brightness(
            raw_brightness, presence_state
        )

    def get_status(self) -> PowerManagementStatus:
        return PowerManagementStatus(
            snapshot=self.battery_monitor.get_snapshot(),
            policy_enabled=self.power_aware_controller.policy_config.enabled,
        )

    def get_charge_cycle_data(self) -> Dict[str, Any]:
        """Return persisted charge/discharge history."""
        return self.charge_cycle_repository.load()

    def start_battery_tracking(self) -> None:
        self.cycle_tracker.start()

    def stop_battery_tracking(self) -> None:
        self.cycle_tracker.stop()

    def get_battery_insights(self) -> BatteryInsights:
        status = self.cycle_tracker.get_live_status()
        return status["insights"]

    def get_battery_live_status(self) -> Dict[str, Any]:
        return self.cycle_tracker.get_live_status()

    def set_full_battery_percent(self, percent: int) -> None:
        self.cycle_tracker.set_full_battery_percent(percent)

    def apply_learned_full_battery_percent(self) -> Optional[int]:
        return self.cycle_tracker.apply_learned_full_percent()
