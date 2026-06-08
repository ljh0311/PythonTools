"""
Wrapper for applying battery-aware policy to brightness controller.
"""

from dataclasses import dataclass
from typing import Optional

from battery_provider import BatteryProvider, BatterySnapshot
from brightness_controller import BrightnessController
from brightness_policy import (
    BatteryBrightnessPolicyConfig,
    PolicyDecision,
    evaluate_battery_brightness_policy,
)


@dataclass
class PowerAwareResult:
    decision: PolicyDecision
    snapshot: Optional[BatterySnapshot]


class PowerAwareBrightnessController:
    """Applies battery-based caps before delegating to BrightnessController."""

    def __init__(
        self,
        brightness_controller: BrightnessController,
        battery_provider: Optional[BatteryProvider] = None,
    ):
        self.brightness_controller = brightness_controller
        self.battery_provider = battery_provider or BatteryProvider()
        self.policy_config = BatteryBrightnessPolicyConfig()

    def update_policy_config(self, config: BatteryBrightnessPolicyConfig) -> None:
        self.policy_config = config

    def adjust_screen_brightness(self, brightness: float) -> PowerAwareResult:
        snapshot = self.battery_provider.get_snapshot()
        decision = evaluate_battery_brightness_policy(snapshot, self.policy_config)

        default_max = self.brightness_controller.max_brightness
        try:
            if decision.max_brightness_cap is not None:
                # Temporarily clamp while preserving existing transition behavior.
                self.brightness_controller.max_brightness = min(
                    self.brightness_controller.max_brightness, decision.max_brightness_cap
                )
            self.brightness_controller.adjust_screen_brightness(brightness)
        finally:
            self.brightness_controller.max_brightness = default_max

        return PowerAwareResult(decision=decision, snapshot=snapshot)
