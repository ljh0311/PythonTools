"""
Background charge/discharge session tracker persisted to charge_cycles.json.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional

from battery_analytics import BatteryAnalytics
from battery_provider import BatteryProvider, BatterySnapshot
from charge_cycle_repository import ChargeCycleRepository


@dataclass
class ActiveBatterySession:
    kind: str  # "charge" or "discharge"
    start_iso: str
    start_percent: int
    last_percent: int
    last_update: float
    crossed_thresholds: Dict[str, float] = field(default_factory=dict)
    plateau_percent: Optional[int] = None
    plateau_since: Optional[float] = None
    last_percent_change_time: float = field(default_factory=time.time)

    def duration_minutes(self, end_time: Optional[float] = None) -> float:
        start = datetime.fromisoformat(self.start_iso)
        end = datetime.fromtimestamp(end_time or time.time())
        return max(0.0, (end - start).total_seconds() / 60.0)


class BatteryCycleTracker:
    """Poll battery state and record completed charge/discharge sessions."""

    POLL_SECONDS = 30.0
    MIN_SESSION_MINUTES = 2.0
    MIN_PERCENT_DELTA = 2
    PLATEAU_SECONDS = 120.0

    CHARGE_THRESHOLDS = (80, 85, 90, 95, 100)
    DISCHARGE_THRESHOLDS = (20, 15, 10, 5, 0)

    def __init__(
        self,
        repository: Optional[ChargeCycleRepository] = None,
        provider: Optional[BatteryProvider] = None,
        analytics: Optional[BatteryAnalytics] = None,
        on_data_changed: Optional[Callable[[], None]] = None,
    ):
        self.repository = repository or ChargeCycleRepository()
        self.provider = provider or BatteryProvider(poll_interval_seconds=5.0)
        self.analytics = analytics or BatteryAnalytics()
        self.on_data_changed = on_data_changed

        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._lock = threading.Lock()
        self._active_session: Optional[ActiveBatterySession] = None
        self._last_plugged: Optional[bool] = None

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True, name="BatteryCycleTracker")
        self._thread.start()

    def stop(self) -> None:
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        with self._lock:
            if self._active_session is not None:
                self._finalize_session(force=True)
        self._thread = None

    def get_live_status(self) -> Dict[str, Any]:
        with self._lock:
            session = self._active_session
            snapshot = self.provider.get_snapshot()
            data = self.repository.load()
            insights = self.analytics.compute_insights(
                data,
                snapshot,
                self._session_rate(session),
            )
            return {
                "snapshot": snapshot,
                "session_kind": session.kind if session else None,
                "session_minutes": session.duration_minutes() if session else 0.0,
                "session_start_percent": session.start_percent if session else None,
                "session_plateau_percent": session.plateau_percent if session else None,
                "session_rate_per_hour": self._session_rate(session),
                "insights": insights,
            }

    def set_full_battery_percent(self, percent: int) -> None:
        percent = max(
            self.analytics.FULL_PERCENT_MIN,
            min(self.analytics.FULL_PERCENT_MAX, int(percent)),
        )
        data = self.repository.load()
        metadata = self.analytics.get_metadata(data)
        metadata["full_battery_percent"] = percent
        data["metadata"] = metadata
        self.repository.save(data)
        self._notify_changed()

    def apply_learned_full_percent(self) -> Optional[int]:
        data = self.repository.load()
        learned = self.analytics.learn_full_percent(data)
        if learned is None:
            return None
        metadata = self.analytics.get_metadata(data)
        metadata["full_battery_percent"] = learned
        metadata["full_battery_percent_learned"] = learned
        data["metadata"] = metadata
        self.repository.save(data)
        self._notify_changed()
        return learned

    def refresh_learned_full_percent(self) -> Optional[int]:
        data = self.repository.load()
        applied = self.analytics.maybe_auto_apply_learned(data)
        self.repository.save(data)
        return applied

    def _loop(self) -> None:
        while self._running:
            try:
                self._tick()
            except Exception:
                pass
            time.sleep(self.POLL_SECONDS)

    def _tick(self) -> None:
        snapshot = self.provider.get_snapshot(force_refresh=True)
        if snapshot is None:
            return

        with self._lock:
            plugged_changed = (
                self._last_plugged is not None
                and self._last_plugged != snapshot.power_plugged
            )
            self._last_plugged = snapshot.power_plugged

            if plugged_changed and self._active_session is not None:
                self._finalize_session(force=True)

            expected_kind = "charge" if snapshot.power_plugged else "discharge"
            if self._active_session is None:
                now = time.time()
                self._active_session = ActiveBatterySession(
                    kind=expected_kind,
                    start_iso=datetime.now().isoformat(),
                    start_percent=snapshot.percentage,
                    last_percent=snapshot.percentage,
                    last_update=now,
                    last_percent_change_time=now,
                )
                return

            if self._active_session.kind != expected_kind:
                self._finalize_session(force=True)
                now = time.time()
                self._active_session = ActiveBatterySession(
                    kind=expected_kind,
                    start_iso=datetime.now().isoformat(),
                    start_percent=snapshot.percentage,
                    last_percent=snapshot.percentage,
                    last_update=now,
                    last_percent_change_time=now,
                )
                return

            self._track_thresholds(self._active_session, snapshot)
            self._update_plateau(self._active_session, snapshot)
            self._active_session.last_percent = snapshot.percentage
            self._active_session.last_update = time.time()

    def _update_plateau(
        self, session: ActiveBatterySession, snapshot: BatterySnapshot
    ) -> None:
        if session.kind != "charge" or not snapshot.power_plugged:
            return

        now = time.time()
        current = snapshot.percentage
        if current > session.last_percent:
            session.last_percent_change_time = now
            session.plateau_since = None
            session.plateau_percent = None
            return

        if current < session.last_percent:
            session.last_percent_change_time = now
            session.plateau_since = None
            session.plateau_percent = None
            return

        if session.plateau_since is None:
            session.plateau_since = session.last_percent_change_time
        if now - session.plateau_since >= self.PLATEAU_SECONDS:
            session.plateau_percent = current

    def _finalize_session(self, force: bool = False) -> None:
        session = self._active_session
        if session is None:
            return

        end_percent = session.last_percent
        delta = abs(end_percent - session.start_percent)
        duration = session.duration_minutes(session.last_update)
        if not force and (
            duration < self.MIN_SESSION_MINUTES or delta < self.MIN_PERCENT_DELTA
        ):
            self._active_session = None
            return

        end_iso = datetime.fromtimestamp(session.last_update).isoformat()
        percent_change = end_percent - session.start_percent
        rate_per_hour = (
            (percent_change / duration) * 60.0 if duration > 0 else 0.0
        )

        data = self.repository.load()
        cycle: Dict[str, Any] = {
            "start": session.start_iso,
            "end": end_iso,
            "duration": duration,
            "percent": end_percent,
            "start_percent": session.start_percent,
            "percent_change": percent_change,
            "rate_per_hour": rate_per_hour,
        }
        if session.plateau_percent is not None:
            cycle["plateau_percent"] = session.plateau_percent
            cycle["is_trickle_full"] = True

        if session.kind == "charge":
            data.setdefault("charge_cycles", []).append(cycle)
            self._update_charge_stats(data, cycle, session)
        else:
            data.setdefault("discharge_cycles", []).append(cycle)
            self._update_discharge_stats(data, cycle, session)

        self.analytics.maybe_auto_apply_learned(data)
        self.repository.save(data)
        self._active_session = None
        self._notify_changed()

    def _track_thresholds(
        self, session: ActiveBatterySession, snapshot: BatterySnapshot
    ) -> None:
        now_minutes = session.duration_minutes()
        if session.kind == "charge":
            for threshold in self.CHARGE_THRESHOLDS:
                key = str(threshold)
                if key in session.crossed_thresholds:
                    continue
                if snapshot.percentage >= threshold:
                    session.crossed_thresholds[key] = now_minutes
        else:
            for threshold in self.DISCHARGE_THRESHOLDS:
                key = str(threshold)
                if key in session.crossed_thresholds:
                    continue
                if snapshot.percentage <= threshold:
                    session.crossed_thresholds[key] = now_minutes

    def _update_charge_stats(
        self,
        data: Dict[str, Any],
        cycle: Dict[str, Any],
        session: ActiveBatterySession,
    ) -> None:
        thresholds = data.setdefault(
            "charge_thresholds",
            {str(t): {"times": [], "average": 0} for t in self.CHARGE_THRESHOLDS},
        )
        for key, minutes in session.crossed_thresholds.items():
            entry = thresholds.setdefault(key, {"times": [], "average": 0})
            times: List[float] = list(entry.get("times") or [])
            times.append(minutes)
            times = times[-10:]
            entry["times"] = times
            entry["average"] = sum(times) / len(times) if times else 0
            thresholds[key] = entry

        start_percent = int(cycle.get("start_percent") or 0)
        if start_percent < 50:
            bucket = "0-49"
        elif start_percent < 80:
            bucket = "50-79"
        else:
            bucket = "80-100"

        range_stats = data.setdefault(
            "charge_range_stats",
            {
                "0-49": {"cycles": [], "avg_rate": 0, "avg_time": 0},
                "50-79": {"cycles": [], "avg_rate": 0, "avg_time": 0},
                "80-100": {"cycles": [], "avg_rate": 0, "avg_time": 0},
            },
        )
        bucket_stats = range_stats.setdefault(
            bucket, {"cycles": [], "avg_rate": 0, "avg_time": 0}
        )
        cycles: List[Dict[str, Any]] = list(bucket_stats.get("cycles") or [])
        cycles.append(
            {
                "start_percent": cycle["start_percent"],
                "end_percent": cycle["percent"],
                "duration": cycle["duration"],
                "rate_per_hour": cycle["rate_per_hour"],
            }
        )
        cycles = cycles[-20:]
        bucket_stats["cycles"] = cycles
        bucket_stats["avg_rate"] = sum(c["rate_per_hour"] for c in cycles) / len(cycles)
        bucket_stats["avg_time"] = sum(c["duration"] for c in cycles) / len(cycles)
        range_stats[bucket] = bucket_stats

    def _update_discharge_stats(
        self,
        data: Dict[str, Any],
        cycle: Dict[str, Any],
        session: ActiveBatterySession,
    ) -> None:
        thresholds = data.setdefault(
            "discharge_thresholds",
            {str(t): {"times": [], "average": 0} for t in self.DISCHARGE_THRESHOLDS},
        )
        for key, minutes in session.crossed_thresholds.items():
            entry = thresholds.setdefault(key, {"times": [], "average": 0})
            times: List[float] = list(entry.get("times") or [])
            times.append(minutes)
            times = times[-10:]
            entry["times"] = times
            entry["average"] = sum(times) / len(times) if times else 0
            thresholds[key] = entry

    def _session_rate(self, session: Optional[ActiveBatterySession]) -> Optional[float]:
        if session is None:
            return None
        duration = session.duration_minutes()
        if duration <= 0:
            return None
        delta = session.last_percent - session.start_percent
        return (delta / duration) * 60.0

    def _notify_changed(self) -> None:
        if self.on_data_changed:
            try:
                self.on_data_changed()
            except Exception:
                pass
