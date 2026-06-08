"""
Battery data access helpers for power-aware brightness behavior.
"""

from dataclasses import dataclass
from datetime import timedelta
import time
from typing import Optional

import psutil


@dataclass
class BatterySnapshot:
    """Current battery state."""

    percentage: int
    power_plugged: bool
    secsleft: int
    updated_at: float

    def time_left_text(self) -> str:
        """User-friendly remaining time text."""
        if self.power_plugged:
            return "Charging"
        if self.secsleft in (psutil.POWER_TIME_UNLIMITED, psutil.POWER_TIME_UNKNOWN):
            return "Unknown"
        return str(timedelta(seconds=max(0, int(self.secsleft))))


class BatteryProvider:
    """Cached battery reader to avoid excessive OS polling."""

    def __init__(self, poll_interval_seconds: float = 5.0):
        self.poll_interval_seconds = poll_interval_seconds
        self._last_snapshot: Optional[BatterySnapshot] = None

    def get_snapshot(self, force_refresh: bool = False) -> Optional[BatterySnapshot]:
        """Return the latest battery snapshot or None when unavailable."""
        now = time.time()
        if (
            not force_refresh
            and self._last_snapshot is not None
            and (now - self._last_snapshot.updated_at) < self.poll_interval_seconds
        ):
            return self._last_snapshot

        battery = psutil.sensors_battery()
        if battery is None:
            self._last_snapshot = None
            return None

        self._last_snapshot = BatterySnapshot(
            percentage=int(round(battery.percent)),
            power_plugged=bool(battery.power_plugged),
            secsleft=int(battery.secsleft),
            updated_at=now,
        )
        return self._last_snapshot
