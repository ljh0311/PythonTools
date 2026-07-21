"""
Battery analytics: estimates, habit summaries, and learned full-capacity percent.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from statistics import median
from typing import Any, Dict, List, Optional, Tuple

from battery_provider import BatterySnapshot


def _parse_iso(value: str) -> Optional[datetime]:
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def format_duration_minutes(minutes: float) -> str:
    """Format minutes as human-readable duration."""
    if minutes <= 0 or minutes != minutes:  # NaN guard
        return "—"
    total_minutes = int(round(minutes))
    hours, mins = divmod(total_minutes, 60)
    if hours and mins:
        return f"{hours}h {mins}m"
    if hours:
        return f"{hours}h"
    return f"{mins}m"


@dataclass
class BatteryInsights:
    """Computed battery metrics for UI and logging."""

    effective_full_percent: int
    learned_full_percent: Optional[int]
    avg_charge_minutes: Optional[float]
    avg_discharge_minutes: Optional[float]
    time_to_full_minutes: Optional[float]
    estimated_runtime_minutes: Optional[float]
    charge_sessions: int
    discharge_sessions: int
    habit_summary: str
    auto_apply_learned_full: bool = True
    trickle_plateau_percent: Optional[int] = None


@dataclass
class LearnFullResult:
    """Outcome of statistical full-percent learning."""

    value: int
    sample_count: int
    confident: bool


class BatteryAnalytics:
    """Derive estimates and learned capacity from persisted cycle data."""

    MIN_CHARGE_LEARN_MINUTES = 10.0
    MIN_CHARGE_LEARN_END = 65
    LEARN_SAMPLE_LIMIT = 15
    LEARN_BIN_SIZE = 5
    LEARN_VARIANCE_MAX = 5
    LEARN_RECENCY_HALF_LIFE = 3.0
    LEARN_MODE_DOMINANCE = 0.4
    AUTO_APPLY_MIN_DIFF = 3
    AUTO_APPLY_MIN_SAMPLES = 3
    FULL_PERCENT_MIN = 65
    FULL_PERCENT_MAX = 100

    def __init__(self, default_full_percent: int = 100):
        self.default_full_percent = default_full_percent

    def get_metadata(self, data: Dict[str, Any]) -> Dict[str, Any]:
        metadata = dict(data.get("metadata") or {})
        metadata.setdefault("full_battery_percent", self.default_full_percent)
        metadata.setdefault("full_battery_percent_learned", None)
        metadata.setdefault("auto_apply_learned_full", True)
        metadata.setdefault("version", 2)
        return metadata

    def get_effective_full_percent(self, data: Dict[str, Any]) -> int:
        value = self.get_metadata(data).get("full_battery_percent", self.default_full_percent)
        try:
            return max(
                self.FULL_PERCENT_MIN,
                min(self.FULL_PERCENT_MAX, int(round(float(value)))),
            )
        except (TypeError, ValueError):
            return self.default_full_percent

    def _clamp_learned_full(self, value: float) -> int:
        return max(
            self.FULL_PERCENT_MIN,
            min(self.FULL_PERCENT_MAX, int(round(value))),
        )

    @staticmethod
    def _bin_end_percent(end_percent: int, bin_size: int = 5) -> int:
        """Snap end percent to 5% bins (70/75/80/85/90/95/100)."""
        return int(round(end_percent / bin_size) * bin_size)

    def _is_learn_eligible_cycle(self, cycle: Dict[str, Any]) -> bool:
        duration = float(cycle.get("duration") or 0)
        end_percent = int(cycle.get("percent") or 0)
        percent_change = int(cycle.get("percent_change") or 0)
        start_percent = int(cycle.get("start_percent") or 0)
        if duration < self.MIN_CHARGE_LEARN_MINUTES:
            return False
        if end_percent < self.MIN_CHARGE_LEARN_END:
            return False
        if percent_change > 0:
            return True
        # Plateau/cap sessions: held at end (local max) without further rise.
        return percent_change == 0 and end_percent >= start_percent

    def _cycle_learn_quality(self, cycle: Dict[str, Any]) -> float:
        """Prefer cycles where charging slowed near end or end is session peak."""
        start_percent = int(cycle.get("start_percent") or 0)
        end_percent = int(cycle.get("percent") or 0)
        percent_change = int(cycle.get("percent_change") or 0)
        rate = float(cycle.get("rate_per_hour") or 0)

        score = 1.0
        session_peak = max(start_percent, end_percent)
        if end_percent >= session_peak - 1:
            score *= 1.35
        if percent_change == 0 and end_percent >= start_percent:
            score *= 1.25
        elif percent_change > 0 and rate > 0 and rate < 18.0:
            score *= 1.15
        return score

    def collect_plateau_weighted_samples(
        self, data: Dict[str, Any]
    ) -> List[Tuple[int, float]]:
        """Recent live-detected charge plateaus (smart/trickle full)."""
        samples: List[Tuple[int, float]] = []
        cycles = list(reversed(data.get("charge_cycles") or []))
        for index, cycle in enumerate(cycles):
            if not isinstance(cycle, dict):
                continue
            plateau = cycle.get("plateau_percent")
            if plateau is None:
                continue
            duration = float(cycle.get("duration") or 0)
            if duration < self.MIN_CHARGE_LEARN_MINUTES:
                continue
            try:
                plateau_percent = int(round(float(plateau)))
            except (TypeError, ValueError):
                continue
            if not (self.MIN_CHARGE_LEARN_END <= plateau_percent <= self.FULL_PERCENT_MAX):
                continue
            recency = math.exp(
                -index * math.log(2) / max(0.5, self.LEARN_RECENCY_HALF_LIFE)
            )
            samples.append((plateau_percent, recency * 1.5))
            if len(samples) >= self.LEARN_SAMPLE_LIMIT:
                break
        return samples

    def recent_trickle_plateau_percent(self, data: Dict[str, Any]) -> Optional[int]:
        """Median of recent trickle/full plateaus for UI hints."""
        samples = [value for value, _ in self.collect_plateau_weighted_samples(data)]
        if not samples:
            return None
        return self._clamp_learned_full(median(samples))

    def collect_full_samples(self, data: Dict[str, Any]) -> List[Tuple[int, float]]:
        """Gather weighted charge-end samples for statistical peak learning."""
        samples: List[Tuple[int, float]] = []
        cycles = list(reversed(data.get("charge_cycles") or []))
        for index, cycle in enumerate(cycles):
            if not isinstance(cycle, dict):
                continue
            if not self._is_learn_eligible_cycle(cycle):
                continue
            end_percent = int(cycle.get("percent") or 0)
            recency = math.exp(
                -index * math.log(2) / max(0.5, self.LEARN_RECENCY_HALF_LIFE)
            )
            weight = recency * self._cycle_learn_quality(cycle)
            samples.append((end_percent, weight))
            if len(samples) >= self.LEARN_SAMPLE_LIMIT:
                break
        return samples

    @staticmethod
    def _weighted_median(values: List[Tuple[int, float]]) -> float:
        if not values:
            return 0.0
        ordered = sorted(values, key=lambda item: item[0])
        total = sum(weight for _, weight in ordered)
        if total <= 0:
            return float(median(end for end, _ in ordered))
        midpoint = total / 2.0
        cumulative = 0.0
        for end, weight in ordered:
            cumulative += weight
            if cumulative >= midpoint:
                return float(end)
        return float(ordered[-1][0])

    def _aggregate_learned_full(self, weighted_samples: List[Tuple[int, float]]) -> int:
        """
        Weighted mode of 5% bins when a bin clearly dominates; otherwise weighted median.
        Mode is preferred for conservation caps (e.g. repeated 80% ends).
        """
        bin_weights: Dict[int, float] = {}
        bin_counts: Dict[int, int] = {}
        for end_percent, weight in weighted_samples:
            binned = self._bin_end_percent(end_percent, self.LEARN_BIN_SIZE)
            bin_weights[binned] = bin_weights.get(binned, 0.0) + weight
            bin_counts[binned] = bin_counts.get(binned, 0) + 1

        total_weight = sum(bin_weights.values())
        if total_weight <= 0:
            return self._clamp_learned_full(self._weighted_median(weighted_samples))

        top_bin = max(bin_weights, key=bin_weights.get)
        top_weight = bin_weights[top_bin]
        if (
            top_weight >= self.LEARN_MODE_DOMINANCE * total_weight
            and bin_counts.get(top_bin, 0) >= 2
        ):
            return self._clamp_learned_full(top_bin)
        return self._clamp_learned_full(self._weighted_median(weighted_samples))

    def learn_full_percent_with_confidence(self, data: Dict[str, Any]) -> Optional[LearnFullResult]:
        """Estimate practical 100% from completed charge cycle peaks."""
        weighted_samples = self.collect_full_samples(data)
        if not weighted_samples:
            return None

        value = self._aggregate_learned_full(weighted_samples)
        raw_values = [end for end, _ in weighted_samples]
        spread = max(raw_values) - min(raw_values) if raw_values else 999
        bin_weights: Dict[int, float] = {}
        for end_percent, weight in weighted_samples:
            binned = self._bin_end_percent(end_percent, self.LEARN_BIN_SIZE)
            bin_weights[binned] = bin_weights.get(binned, 0.0) + weight
        total_weight = sum(bin_weights.values())
        top_weight = max(bin_weights.values()) if bin_weights else 0.0
        mode_confident = (
            total_weight > 0 and top_weight >= self.LEARN_MODE_DOMINANCE * total_weight
        )
        variance_confident = spread <= self.LEARN_VARIANCE_MAX
        confident = len(weighted_samples) >= self.AUTO_APPLY_MIN_SAMPLES and (
            mode_confident or variance_confident
        )
        return LearnFullResult(
            value=value,
            sample_count=len(weighted_samples),
            confident=confident,
        )

    def learn_full_percent(self, data: Dict[str, Any]) -> Optional[int]:
        """Return learned full percent from recent charge cycle peaks."""
        result = self.learn_full_percent_with_confidence(data)
        if result is None:
            return None
        return result.value

    def should_auto_apply_learned(self, data: Dict[str, Any], result: LearnFullResult) -> bool:
        metadata = self.get_metadata(data)
        if not metadata.get("auto_apply_learned_full", True):
            return False
        if not result.confident or result.sample_count < self.AUTO_APPLY_MIN_SAMPLES:
            return False
        effective = self.get_effective_full_percent(data)
        return abs(result.value - effective) >= self.AUTO_APPLY_MIN_DIFF

    def maybe_auto_apply_learned(self, data: Dict[str, Any]) -> Optional[int]:
        """Apply learned full percent when confidence and diff thresholds are met."""
        result = self.learn_full_percent_with_confidence(data)
        if result is None:
            return None

        metadata = self.get_metadata(data)
        if result.confident:
            metadata["full_battery_percent_learned"] = result.value
        else:
            metadata["full_battery_percent_learned"] = result.value

        applied: Optional[int] = None
        if self.should_auto_apply_learned(data, result):
            metadata["full_battery_percent"] = result.value
            applied = result.value

        data["metadata"] = metadata
        return applied

    def average_charge_minutes(self, data: Dict[str, Any]) -> Optional[float]:
        full = self.get_effective_full_percent(data)
        durations: List[float] = []
        for cycle in data.get("charge_cycles") or []:
            if not isinstance(cycle, dict):
                continue
            end_percent = int(cycle.get("percent") or 0)
            start_percent = int(cycle.get("start_percent") or 0)
            duration = float(cycle.get("duration") or 0)
            if duration <= 0:
                continue
            if end_percent >= full - 2 or start_percent <= 15:
                durations.append(duration)
        if not durations:
            return None
        recent = durations[-10:]
        return sum(recent) / len(recent)

    def average_discharge_minutes(self, data: Dict[str, Any]) -> Optional[float]:
        full = self.get_effective_full_percent(data)
        durations: List[float] = []
        for cycle in data.get("discharge_cycles") or []:
            if not isinstance(cycle, dict):
                continue
            start_percent = int(cycle.get("start_percent") or 0)
            duration = float(cycle.get("duration") or 0)
            if duration <= 0:
                continue
            if start_percent >= full - 10:
                durations.append(duration)
        if not durations:
            return None
        recent = durations[-10:]
        return sum(recent) / len(recent)

    def estimate_time_to_full(
        self,
        snapshot: Optional[BatterySnapshot],
        data: Dict[str, Any],
        session_rate_per_hour: Optional[float] = None,
    ) -> Optional[float]:
        if snapshot is None or not snapshot.power_plugged:
            return None
        full = self.get_effective_full_percent(data)
        if snapshot.percentage >= full - 1:
            return 0.0
        remaining = max(0, full - snapshot.percentage)
        if remaining <= 0:
            return 0.0

        rate = session_rate_per_hour
        if rate is None or rate <= 0:
            rate = self._average_charge_rate(data)
        if rate is None or rate <= 0:
            return None
        return (remaining / rate) * 60.0

    def estimate_runtime_minutes(
        self,
        snapshot: Optional[BatterySnapshot],
        data: Dict[str, Any],
        session_rate_per_hour: Optional[float] = None,
    ) -> Optional[float]:
        if snapshot is None or snapshot.power_plugged:
            return None

        avg_discharge = self.average_discharge_minutes(data)
        if avg_discharge is not None:
            full = self.get_effective_full_percent(data)
            scale = snapshot.percentage / full if full > 0 else 1.0
            return max(0.0, avg_discharge * scale)

        rate = session_rate_per_hour
        if rate is None or rate >= 0:
            rate = self._average_discharge_rate(data)
        if rate is None or rate >= 0:
            return None
        return (snapshot.percentage / abs(rate)) * 60.0

    def build_habit_summary(self, data: Dict[str, Any]) -> str:
        charge_count = len(data.get("charge_cycles") or [])
        discharge_count = len(data.get("discharge_cycles") or [])
        avg_charge = self.average_charge_minutes(data)
        avg_discharge = self.average_discharge_minutes(data)
        metadata = self.get_metadata(data)

        parts: List[str] = []
        parts.append(f"{charge_count} charge and {discharge_count} discharge sessions recorded.")

        learned = metadata.get("full_battery_percent_learned")
        if learned is None:
            learned = self.learn_full_percent(data)
        if learned is not None and learned < self.FULL_PERCENT_MAX:
            parts.append(f"Smart charging appears to full at ~{learned}%.")

        if avg_charge is not None:
            parts.append(f"Typical full charge takes about {format_duration_minutes(avg_charge)}.")
        if avg_discharge is not None:
            parts.append(
                f"A full charge usually lasts about {format_duration_minutes(avg_discharge)} on battery."
            )

        range_stats = data.get("charge_range_stats") or {}
        top_range = None
        top_rate = 0.0
        for label, stats in range_stats.items():
            if not isinstance(stats, dict):
                continue
            rate = float(stats.get("avg_rate") or 0)
            if rate > top_rate:
                top_rate = rate
                top_range = label
        if top_range and top_rate > 0:
            parts.append(f"Fastest charging observed in the {top_range}% range.")

        return " ".join(parts) if parts else "No charging habits recorded yet."

    def compute_insights(
        self,
        data: Dict[str, Any],
        snapshot: Optional[BatterySnapshot] = None,
        session_rate_per_hour: Optional[float] = None,
    ) -> BatteryInsights:
        metadata = self.get_metadata(data)
        result = self.learn_full_percent_with_confidence(data)
        learned = result.value if result else metadata.get("full_battery_percent_learned")
        if learned is not None:
            try:
                learned = int(round(float(learned)))
            except (TypeError, ValueError):
                learned = None

        return BatteryInsights(
            effective_full_percent=self.get_effective_full_percent(data),
            learned_full_percent=learned,
            avg_charge_minutes=self.average_charge_minutes(data),
            avg_discharge_minutes=self.average_discharge_minutes(data),
            time_to_full_minutes=self.estimate_time_to_full(
                snapshot, data, session_rate_per_hour
            ),
            estimated_runtime_minutes=self.estimate_runtime_minutes(
                snapshot, data, session_rate_per_hour
            ),
            charge_sessions=len(data.get("charge_cycles") or []),
            discharge_sessions=len(data.get("discharge_cycles") or []),
            habit_summary=self.build_habit_summary(data),
            auto_apply_learned_full=bool(metadata.get("auto_apply_learned_full", True)),
            trickle_plateau_percent=self.recent_trickle_plateau_percent(data),
        )

    def _average_charge_rate(self, data: Dict[str, Any]) -> Optional[float]:
        rates: List[float] = []
        for cycle in data.get("charge_cycles") or []:
            if not isinstance(cycle, dict):
                continue
            rate = float(cycle.get("rate_per_hour") or 0)
            if rate > 0:
                rates.append(rate)
        if not rates:
            range_stats = data.get("charge_range_stats") or {}
            for stats in range_stats.values():
                if isinstance(stats, dict):
                    rate = float(stats.get("avg_rate") or 0)
                    if rate > 0:
                        rates.append(rate)
        return sum(rates[-10:]) / len(rates[-10:]) if rates else None

    def _average_discharge_rate(self, data: Dict[str, Any]) -> Optional[float]:
        rates: List[float] = []
        for cycle in data.get("discharge_cycles") or []:
            if not isinstance(cycle, dict):
                continue
            rate = float(cycle.get("rate_per_hour") or 0)
            if rate < 0:
                rates.append(rate)
        return sum(rates[-10:]) / len(rates[-10:]) if rates else None
