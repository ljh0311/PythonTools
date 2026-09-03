"""
Multi-pass ML training for CarRS cost predictions.

Pass 1 — baseline CV MAPE with default RandomForest
Pass 2 — try several hyperparameter sets; keep the lowest MAPE
Pass 3 — rebuild calibration buckets with the winning model; save meta
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

import numpy as np
import pandas as pd

from components.ml_calibration import (
    ErrorSample,
    PROVIDER_ENCODE,
    _extract_training_rows,
    _features_for_row,
    apply_calibration,
    build_calibration,
    calibration_path,
    ensure_calibration,
    load_calibration,
    save_calibration,
    summarize_calibration,
)

DEFAULT_META_PATH = "ml_model_meta.json"
_cached_meta: Optional[dict[str, Any]] = None

PARAM_GRID = [
    {"n_estimators": 50, "max_depth": None, "min_samples_leaf": 1},
    {"n_estimators": 100, "max_depth": 8, "min_samples_leaf": 2},
    {"n_estimators": 120, "max_depth": 12, "min_samples_leaf": 2},
    {"n_estimators": 150, "max_depth": 10, "min_samples_leaf": 1},
    {"n_estimators": 80, "max_depth": 6, "min_samples_leaf": 3},
]


def _carrs_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def meta_path(path: Optional[str] = None) -> str:
    if path:
        return path if os.path.isabs(path) else os.path.join(_carrs_root(), path)
    return os.path.join(_carrs_root(), DEFAULT_META_PATH)


def load_model_meta(path: Optional[str] = None, *, force_reload: bool = False) -> dict[str, Any]:
    global _cached_meta
    if _cached_meta is not None and not force_reload:
        return _cached_meta
    out = meta_path(path)
    if not os.path.exists(out):
        _cached_meta = {
            "version": 1,
            "best_params": PARAM_GRID[0],
            "passes": [],
        }
        return _cached_meta
    with open(out, encoding="utf-8") as fh:
        _cached_meta = json.load(fh)
    return _cached_meta


def save_model_meta(meta: dict[str, Any], path: Optional[str] = None) -> str:
    global _cached_meta
    out = meta_path(path)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    _cached_meta = meta
    return out


def _cv_errors(rows: list[dict[str, Any]], params: dict[str, Any], n_folds: int = 5) -> list[ErrorSample]:
    from sklearn.ensemble import RandomForestRegressor
    from sklearn.model_selection import KFold
    from sklearn.preprocessing import StandardScaler

    if len(rows) < 10:
        return []

    X = np.array([_features_for_row(r) for r in rows])
    y = np.array([r["actual"] for r in rows])
    n_folds = min(n_folds, len(rows))
    if n_folds < 2:
        return []

    kf = KFold(n_splits=n_folds, shuffle=True, random_state=42)
    errors: list[ErrorSample] = []
    model_kwargs = {
        "n_estimators": int(params.get("n_estimators", 50)),
        "max_depth": params.get("max_depth"),
        "min_samples_leaf": int(params.get("min_samples_leaf", 1)),
        "random_state": 42,
    }

    for train_idx, test_idx in kf.split(X):
        scaler = StandardScaler()
        X_train = scaler.fit_transform(X[train_idx])
        X_test = scaler.transform(X[test_idx])
        model = RandomForestRegressor(**model_kwargs)
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


def _metrics_from_errors(errors: list[ErrorSample]) -> dict[str, float]:
    if not errors:
        return {"mape_pct": 999.0, "median_abs_pct_error": 999.0, "within_25pct": 0.0}
    abs_pct = [abs(e.pct_error) for e in errors]
    return {
        "mape_pct": round(float(pd.Series(abs_pct).mean()), 2),
        "median_abs_pct_error": round(float(pd.Series(abs_pct).median()), 2),
        "within_25pct": round(sum(1 for e in abs_pct if e <= 25) / len(abs_pct) * 100, 1),
    }


def evaluate_with_calibration(
    errors: list[ErrorSample], calibration: dict[str, Any]
) -> dict[str, float]:
    """MAPE after applying bucket calibration factors."""
    if not errors:
        return {"mape_pct": 999.0, "median_abs_pct_error": 999.0, "within_25pct": 0.0}
    adj_abs = []
    for err in errors:
        adj = apply_calibration(
            err.predicted,
            calibration,
            err.provider,
            err.distance,
            err.duration,
            err.is_weekend,
        )["total_cost"]
        if err.actual <= 0:
            continue
        adj_abs.append(abs(adj - err.actual) / err.actual * 100.0)
    if not adj_abs:
        return {"mape_pct": 999.0, "median_abs_pct_error": 999.0, "within_25pct": 0.0}
    return {
        "mape_pct": round(float(pd.Series(adj_abs).mean()), 2),
        "median_abs_pct_error": round(float(pd.Series(adj_abs).median()), 2),
        "within_25pct": round(sum(1 for e in adj_abs if e <= 25) / len(adj_abs) * 100, 1),
    }


def run_training_passes(df: pd.DataFrame, passes: int = 3) -> dict[str, Any]:
    """
    Run up to `passes` training rounds and persist best params + calibration.
    """
    rows = _extract_training_rows(df)
    if len(rows) < 10:
        raise ValueError(f"Need >=10 training rows, got {len(rows)}")

    history: list[dict[str, Any]] = []
    best_params = PARAM_GRID[0]
    best_raw = _metrics_from_errors(_cv_errors(rows, best_params))
    best_calibrated = best_raw
    best_calibration = build_calibration(_cv_errors(rows, best_params))

    # Pass 1 — baseline
    p1_errors = _cv_errors(rows, PARAM_GRID[0])
    p1_raw = _metrics_from_errors(p1_errors)
    p1_cal = build_calibration(p1_errors)
    p1_adj = evaluate_with_calibration(p1_errors, p1_cal)
    history.append(
        {
            "pass": 1,
            "name": "baseline",
            "params": PARAM_GRID[0],
            "raw": p1_raw,
            "calibrated": p1_adj,
        }
    )
    best_params, best_raw, best_calibrated, best_calibration = (
        PARAM_GRID[0],
        p1_raw,
        p1_adj,
        p1_cal,
    )

    if passes >= 2:
        # Pass 2 — hyperparameter search
        grid_results = []
        for params in PARAM_GRID:
            errors = _cv_errors(rows, params)
            raw = _metrics_from_errors(errors)
            cal = build_calibration(errors)
            adj = evaluate_with_calibration(errors, cal)
            grid_results.append(
                {"params": params, "raw": raw, "calibrated": adj, "calibration": cal, "errors": errors}
            )
        winner = min(grid_results, key=lambda g: g["calibrated"]["mape_pct"])
        history.append(
            {
                "pass": 2,
                "name": "hyperparam_search",
                "candidates": len(PARAM_GRID),
                "params": winner["params"],
                "raw": winner["raw"],
                "calibrated": winner["calibrated"],
            }
        )
        best_params = winner["params"]
        best_raw = winner["raw"]
        best_calibrated = winner["calibrated"]
        best_calibration = winner["calibration"]

    if passes >= 3:
        # Pass 3 — refit calibration on winning params (fresh CV seed stability)
        errors = _cv_errors(rows, best_params, n_folds=5)
        cal = build_calibration(errors)
        adj = evaluate_with_calibration(errors, cal)
        # Blend factors gently toward previous if both exist (stability)
        if best_calibration.get("buckets") and cal.get("buckets"):
            blended_buckets = dict(best_calibration.get("buckets") or {})
            for key, entry in (cal.get("buckets") or {}).items():
                prev = blended_buckets.get(key)
                if prev:
                    entry = dict(entry)
                    entry["factor"] = round(
                        (float(prev["factor"]) + float(entry["factor"])) / 2.0, 4
                    )
                    entry["samples"] = max(int(prev.get("samples", 0)), int(entry.get("samples", 0)))
                blended_buckets[key] = entry
            cal["buckets"] = blended_buckets
            cal["global_factor"] = round(
                (
                    float(best_calibration.get("global_factor", 1.0))
                    + float(cal.get("global_factor", 1.0))
                )
                / 2.0,
                4,
            )
            adj = evaluate_with_calibration(errors, cal)
        history.append(
            {
                "pass": 3,
                "name": "recalibrate_blend",
                "params": best_params,
                "raw": _metrics_from_errors(errors),
                "calibrated": adj,
            }
        )
        best_calibrated = adj
        best_calibration = cal
        best_raw = _metrics_from_errors(errors)

    save_calibration(best_calibration)
    meta = {
        "version": 1,
        "updated_at": datetime.now(timezone.utc).isoformat(),
        "rows_trained": len(rows),
        "best_params": best_params,
        "baseline_mape_pct": history[0]["calibrated"]["mape_pct"],
        "best_mape_pct": best_calibrated["mape_pct"],
        "best_within_25pct": best_calibrated["within_25pct"],
        "best_raw_mape_pct": best_raw["mape_pct"],
        "passes": history,
        "calibration_path": os.path.basename(calibration_path()),
    }
    save_model_meta(meta)
    return meta


def format_training_report(meta: dict[str, Any]) -> str:
    lines = [
        "CarRS ML training",
        f"Rows: {meta.get('rows_trained')}",
        f"Best params: {meta.get('best_params')}",
        f"MAPE: {meta.get('baseline_mape_pct')}% -> {meta.get('best_mape_pct')}%",
        f"Within 25%: {meta.get('best_within_25pct')}%",
        "",
        "Passes:",
    ]
    for p in meta.get("passes") or []:
        cal = p.get("calibrated") or {}
        lines.append(
            f"  Pass {p.get('pass')} ({p.get('name')}): "
            f"MAPE {cal.get('mape_pct')}%, within25 {cal.get('within_25pct')}%"
        )
    return "\n".join(lines)
