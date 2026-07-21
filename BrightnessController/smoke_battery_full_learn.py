"""
Smoke tests for statistical peak full-percent learning (Approach B).
"""

from __future__ import annotations

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from battery_analytics import BatteryAnalytics
from battery_provider import BatterySnapshot


def _charge_cycle(
    end_percent: int,
    *,
    start_percent: int = 50,
    duration: float = 20.0,
    rate_per_hour: float = 12.0,
) -> dict:
    percent_change = end_percent - start_percent
    return {
        "start": "2026-07-21T10:00:00",
        "end": "2026-07-21T10:20:00",
        "duration": duration,
        "percent": end_percent,
        "start_percent": start_percent,
        "percent_change": percent_change,
        "rate_per_hour": rate_per_hour if percent_change > 0 else 0.0,
    }


def _plateau_cycle(end_percent: int, *, duration: float = 25.0) -> dict:
    return {
        "start": "2026-07-21T10:00:00",
        "end": "2026-07-21T10:25:00",
        "duration": duration,
        "percent": end_percent,
        "start_percent": end_percent,
        "percent_change": 0,
        "rate_per_hour": 0.0,
    }


def main() -> int:
    analytics = BatteryAnalytics()
    failures: list[str] = []

    conservation = {
        "charge_cycles": [
            _charge_cycle(80, start_percent=65),
            _charge_cycle(80, start_percent=70),
            _charge_cycle(79, start_percent=68),
            _charge_cycle(72, start_percent=60),
        ]
    }
    learned = analytics.learn_full_percent(conservation)
    if learned is None or not (78 <= learned <= 82):
        failures.append(f"expected ~80 for conservation history, got {learned}")

    high_ends = {
        "charge_cycles": [
            _charge_cycle(99, start_percent=85, rate_per_hour=8.0),
            _charge_cycle(99, start_percent=88, rate_per_hour=7.0),
            _charge_cycle(98, start_percent=90, rate_per_hour=6.0),
            _charge_cycle(97, start_percent=87, rate_per_hour=7.5),
        ]
    }
    learned_high = analytics.learn_full_percent(high_ends)
    if learned_high is None or learned_high < 95:
        failures.append(f"expected ~99 from high ends, got {learned_high}")

    plateau_80 = {"charge_cycles": [_plateau_cycle(80), _plateau_cycle(80)]}
    if analytics.learn_full_percent(plateau_80) != 80:
        failures.append("expected 80 from repeated plateau caps")

    data = {"metadata": {"full_battery_percent": 80}}
    snap = BatterySnapshot(
        percentage=79,
        power_plugged=True,
        secsleft=-1,
        updated_at=time.time(),
    )
    if analytics.estimate_time_to_full(snap, data) != 0.0:
        failures.append("expected time_to_full=0 at effective_full-1")

    snap_at_cap = BatterySnapshot(
        percentage=80,
        power_plugged=True,
        secsleft=-1,
        updated_at=time.time(),
    )
    if analytics.estimate_time_to_full(snap_at_cap, data) != 0.0:
        failures.append("expected time_to_full=0 at effective full")

    if failures:
        for msg in failures:
            print(f"FAIL: {msg}")
        return 1

    print("smoke_battery_full_learn: all checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
