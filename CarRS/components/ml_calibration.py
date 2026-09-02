"""
Learn from ML prediction error vs actual rental costs and apply corrections.

Uses k-fold cross-validation on historical rows, stores bucket corrections locally
in ml_calibration.json (gitignored).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

import pandas as pd

PROVIDER_ENCODE = {"Getgo": 0, "Car Club": 1, "Econ": 2, "Stand": 3}
MIN_ROWS_FOR_CV = 10
MIN_BUCKET_SAMPLES = 2
DEFAULT_CALIB_PATH = "ml_calibration.json"

_cached_calibration: Optional[dict[str, Any]] = None


def _carrs_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def calibration_path(path: Optional[str] = None) -> str:
    if path:
        return path if os.path.isabs(path) else os.path.join(_carrs_root(), path)
    return os.path.join(_carrs_root(), DEFAULT_CALIB_PATH)


def distance_bucket(km: float) -> str:
    if km < 40:
        return "short"
    if km <= 100:
        return "medium"
    return "long"


def duration_bucket(hours: float) -> str:
    if hours < 2:
        return "brief"
    if hours <= 6:
        return "standard"
    return "extended"


def bucket_key(
    provider: str,
    distance_km: float,
    duration_h: float,
    is_weekend: bool,
    *,
    fine: bool = True,
) -> str:
    weekend = "we" if is_weekend else "wd"
    if not fine:
        return f"{provider}|{weekend}"
    return (
        f"{provider}|{distance_bucket(distance_km)}|"
        f"{duration_bucket(duration_h)}|{weekend}"
    )


def _extract_training_rows(df: pd.DataFrame) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        if not (
            pd.notna(row.get("Distance (KM)"))
            and pd.notna(row.get("Rental hour"))
            and pd.notna(row.get("Total"))
        ):
            continue
        provider = str(row.get("Car Cat") or "Getgo")
        if provider not in PROVIDER_ENCODE:
            provider = "Getgo"
        is_weekend = str(row.get("Weekday/weekend", "")).lower() == "weekend"
        rows.append(
            {
                "distance": float(row["Distance (KM)"]),
                "duration": float(row["Rental hour"]),
                "provider": provider,
                "is_weekend": is_weekend,
                "actual": float(row["Total"]),
            }
        )
    return rows


def _features_for_row(row: dict[str, Any]) -> list[float]:
    return [
        row["distance"],
        row["duration"],
        float(PROVIDER_ENCODE.get(row["provider"], 0)),
        1.0 if row["is_weekend"] else 0.0,
    ]


@dataclass
class ErrorSample:
    provider: str
    distance: float
    duration: float
    is_weekend: bool
    actual: float
    predicted: float

    @property
    def ratio(self) -> float:
        if self.predicted <= 0:
            return 1.0
        return self.actual / self.predicted

    @property
    def pct_error(self) -> float:
        if self.actual <= 0:
            return 0.0
        return (self.predicted - self.actual) / self.actual * 100.0


def compute_oos_errors(df: pd.DataFrame, n_folds: int = 5) -> list[ErrorSample]:
    """K-fold out-of-sample errors using the same feature set as ML recommendations."""
    rows = _extract_training_rows(df)
    if len(rows) < MIN_ROWS_FOR_CV:
        return []

    try:
        import numpy as np
        from sklearn.ensemble import RandomForestRegressor
        from sklearn.model_selection import KFold
        from sklearn.preprocessing import StandardScaler
    except ImportError:
        return []

    n_folds = min(n_folds, len(rows))
    if n_folds < 2:
        return []

    X = np.array([_features_for_row(r) for r in rows])
    y = np.array([r["actual"] for r in rows])
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)

    errors: list[ErrorSample] = []
    for train_idx, test_idx in kf.split(X):
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X[train_idx])
        X_test = scaler.transform(X[test_idx])
        model = RandomForestRegressor(n_estimators=50, random_state=42)
        model.fit(X_train, y[train_idx])
        preds = model.predict(X_test)
        for i, pred in zip(test_idx, preds):
            row = rows[i]
            errors.append(
                ErrorSample(
                    provider=row["provider"],
                    distance=row["distance"],
                    duration=row["duration"],
                    is_weekend=row["is_weekend"],
                    actual=row["actual"],
                    predicted=float(max(0.01, pred)),
                )
            )
    return errors


def _median_ratio(samples: list[ErrorSample]) -> Optional[float]:
    if not samples:
        return None
    ratios = [s.ratio for s in samples]
    return float(pd.Series(ratios).median())


def build_calibration(errors: list[ErrorSample]) -> dict[str, Any]:
    """Build correction factors from OOS errors (median actual/predicted per bucket)."""
    if not errors:
        return {
            "version": 1,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "sample_count": 0,
            "global_factor": 1.0,
            "buckets": {},
            "metrics": {},
        }

    global_factor = _median_ratio(errors) or 1.0
    buckets: dict[str, dict[str, Any]] = {}

    # Coarse then fine buckets so sparse data still gets a correction.
    for fine in (False, True):
        grouped: dict[str, list[ErrorSample]] = {}
        for err in errors:
            key = bucket_key(
                err.provider, err.distance, err.duration, err.is_weekend, fine=fine
            )
            grouped.setdefault(key, []).append(err)

        for key, group in grouped.items():
            if len(group) < MIN_BUCKET_SAMPLES:
                continue
            factor = _median_ratio(group)
            if factor is None:
                continue
            buckets[key] = {
                "factor": round(factor, 4),
                "samples": len(group),
                "median_pct_error": round(
                    float(pd.Series([g.pct_error for g in group]).median()), 2
                ),
                "fine": fine,
            }

    abs_pct = [abs(e.pct_error) for e in errors]
    signed_pct = [e.pct_error for e in errors]
    metrics = {
        "mape_pct": round(float(pd.Series(abs_pct).mean()), 2),
        "median_abs_pct_error": round(float(pd.Series(abs_pct).median()), 2),
        "mean_signed_pct_error": round(float(pd.Series(signed_pct).mean()), 2),
        "within_25pct": round(
            sum(1 for e in abs_pct if e <= 25) / len(abs_pct) * 100, 1
        ),
    }

    return {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "sample_count": len(errors),
        "global_factor": round(global_factor, 4),
        "buckets": buckets,
        "metrics": metrics,
    }


def lookup_factor(
    calibration: dict[str, Any],
    provider: str,
    distance_km: float,
    duration_h: float,
    is_weekend: bool,
) -> tuple[float, str]:
    """Return (correction_factor, bucket_key_used)."""
    if not calibration:
        return 1.0, "none"

    buckets = calibration.get("buckets") or {}
    if not buckets and calibration.get("sample_count", 0) == 0:
        return 1.0, "none"

    global_factor = float(calibration.get("global_factor") or 1.0)

    candidates = [
        bucket_key(provider, distance_km, duration_h, is_weekend, fine=True),
        bucket_key(provider, distance_km, duration_h, is_weekend, fine=False),
        f"{provider}|{'we' if is_weekend else 'wd'}",
    ]

    for key in candidates:
        entry = buckets.get(key)
        if entry and entry.get("samples", 0) >= MIN_BUCKET_SAMPLES:
            return float(entry["factor"]), key

    return global_factor, "global"


def apply_calibration(
    raw_cost: float,
    calibration: dict[str, Any],
    provider: str,
    distance_km: float,
    duration_h: float,
    is_weekend: bool,
) -> dict[str, Any]:
    factor, bucket = lookup_factor(
        calibration, provider, distance_km, duration_h, is_weekend
    )
    adjusted = max(0.0, raw_cost * factor)
    return {
        "total_cost": adjusted,
        "raw_total_cost": raw_cost,
        "calibration_factor": round(factor, 4),
        "calibration_bucket": bucket,
    }


def save_calibration(calibration: dict[str, Any], path: Optional[str] = None) -> str:
    global _cached_calibration
    out = calibration_path(path)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(calibration, fh, indent=2)
    _cached_calibration = calibration
    return out


def load_calibration(path: Optional[str] = None, *, force_reload: bool = False) -> dict[str, Any]:
    global _cached_calibration
    if _cached_calibration is not None and not force_reload:
        return _cached_calibration

    out = calibration_path(path)
    if not os.path.exists(out):
        _cached_calibration = {
            "version": 1,
            "sample_count": 0,
            "global_factor": 1.0,
            "buckets": {},
            "metrics": {},
        }
        return _cached_calibration

    with open(out, encoding="utf-8") as fh:
        _cached_calibration = json.load(fh)
    return _cached_calibration


def recalibrate(df: pd.DataFrame, path: Optional[str] = None) -> dict[str, Any]:
    """Recompute calibration from CSV history and persist."""
    errors = compute_oos_errors(df)
    calibration = build_calibration(errors)
    if errors:
        save_calibration(calibration, path)
    return calibration


def recalibrate_if_possible(df: pd.DataFrame, path: Optional[str] = None) -> Optional[dict[str, Any]]:
    if df is None or df.empty or len(_extract_training_rows(df)) < MIN_ROWS_FOR_CV:
        return None
    return recalibrate(df, path)


def ensure_calibration(df: pd.DataFrame, path: Optional[str] = None) -> dict[str, Any]:
    """Load calibration or build it when missing/stale."""
    cal = load_calibration(path)
    if cal.get("sample_count", 0) > 0:
        return cal
    return recalibrate_if_possible(df, path) or cal


def summarize_calibration(calibration: dict[str, Any]) -> dict[str, Any]:
    metrics = calibration.get("metrics") or {}
    return {
        "sample_count": calibration.get("sample_count", 0),
        "global_factor": calibration.get("global_factor", 1.0),
        "updated_at": calibration.get("updated_at"),
        "mape_pct": metrics.get("mape_pct"),
        "median_abs_pct_error": metrics.get("median_abs_pct_error"),
        "mean_signed_pct_error": metrics.get("mean_signed_pct_error"),
        "within_25pct": metrics.get("within_25pct"),
        "bucket_count": len(calibration.get("buckets") or {}),
    }
