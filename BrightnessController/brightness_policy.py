"""
Battery-aware brightness policy.
"""

from dataclasses import dataclass
from typing import Optional

from battery_provider import BatterySnapshot


@dataclass
class BatteryBrightnessPolicyConfig:
    enabled: bool = True
    low_battery_threshold: int = 20
    critical_battery_threshold: int = 10
    low_battery_cap: int = 40
    critical_battery_cap: int = 25


@dataclass
class PolicyDecision:
    max_brightness_cap: Optional[int]
    reason: str


def evaluate_battery_brightness_policy(
    snapshot: Optional[BatterySnapshot], config: BatteryBrightnessPolicyConfig
) -> PolicyDecision:
    """Compute optional max brightness cap from battery state."""
    if not config.enabled:
        return PolicyDecision(max_brightness_cap=None, reason="Power-aware mode off")
    if snapshot is None:
        return PolicyDecision(max_brightness_cap=None, reason="Battery status unavailable")
    if snapshot.power_plugged:
        return PolicyDecision(max_brightness_cap=None, reason="Plugged in")

    if snapshot.percentage <= config.critical_battery_threshold:
        return PolicyDecision(
            max_brightness_cap=max(1, min(100, config.critical_battery_cap)),
            reason=f"Critical battery ({snapshot.percentage}%)",
        )
    if snapshot.percentage <= config.low_battery_threshold:
        return PolicyDecision(
            max_brightness_cap=max(1, min(100, config.low_battery_cap)),
            reason=f"Low battery ({snapshot.percentage}%)",
        )
    return PolicyDecision(max_brightness_cap=None, reason="Battery healthy")
