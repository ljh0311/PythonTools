"""Smoke tests for statistical peak full-percent learning."""

from __future__ import annotations

from battery_analytics import BatteryAnalytics


def _cycle(
    end_percent: int,
    *,
    duration: float = 15.0,
    start_percent: int = 20,
    rate_per_hour: float = 12.0,
) -> dict:
    return {
        "start": "2026-07-21T10:00:00",
        "end": "2026-07-21T10:15:00",
        "duration": duration,
        "percent": end_percent,
        "start_percent": start_percent,
        "percent_change": end_percent - start_percent,
        "rate_per_hour": rate_per_hour,
    }


def main() -> None:
    analytics = BatteryAnalytics()

    data_80 = {"charge_cycles": [_cycle(80, start_percent=65)]}
    assert analytics.learn_full_percent(data_80) == 80

    data_72 = {"charge_cycles": [_cycle(72, start_percent=55)]}
    assert analytics.learn_full_percent(data_72) == 72

    data_conservation = {
        "charge_cycles": [
            _cycle(80, start_percent=65),
            _cycle(80, start_percent=70),
            _cycle(79, start_percent=68),
            _cycle(72, start_percent=60),
        ]
    }
    learned = analytics.learn_full_percent(data_conservation)
    assert learned is not None and 78 <= learned <= 82

    data_full = {"charge_cycles": [_cycle(100, start_percent=80, rate_per_hour=8.0)]}
    assert analytics.learn_full_percent(data_full) == 100

    insights = analytics.compute_insights(data_conservation)
    assert insights.learned_full_percent is not None
    assert "Smart charging appears to full at" in insights.habit_summary

    print("test_battery_plateau_learning: all assertions passed")


if __name__ == "__main__":
    main()
