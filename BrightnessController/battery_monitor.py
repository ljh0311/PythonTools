"""
OOP battery monitor facade for brightness and UI modules.
"""

from typing import Optional

from battery_provider import BatteryProvider, BatterySnapshot


class BatteryMonitor:
    """High-level battery monitor service."""

    def __init__(self, poll_interval_seconds: float = 5.0):
        self._provider = BatteryProvider(poll_interval_seconds=poll_interval_seconds)

    def get_snapshot(self, force_refresh: bool = False) -> Optional[BatterySnapshot]:
        """Return current battery snapshot, if available."""
        return self._provider.get_snapshot(force_refresh=force_refresh)

    @property
    def provider(self) -> BatteryProvider:
        """Expose provider for composition where needed."""
        return self._provider
