"""Tests for multi-pass ML trainer."""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.ml_trainer import format_training_report, run_training_passes


def _synthetic_df(n: int = 40) -> pd.DataFrame:
    rows = []
    for i in range(n):
        km = 25 + (i % 6) * 12
        hrs = 1 + (i % 5)
        provider = ["Getgo", "Car Club", "Econ", "Stand"][i % 4]
        rows.append(
            {
                "Car model": f"Car{i % 4}",
                "Distance (KM)": km,
                "Rental hour": hrs,
                "Total": 12 + km * 0.42 + hrs * 7.5 + (i % 5),
                "Car Cat": provider,
                "Weekday/weekend": "weekend" if i % 4 == 0 else "weekday",
            }
        )
    return pd.DataFrame(rows)


def test_run_training_passes_improves_or_holds(tmp_path, monkeypatch):
    import components.ml_trainer as trainer
    import components.ml_calibration as calib

    monkeypatch.setattr(trainer, "meta_path", lambda path=None: str(tmp_path / "meta.json"))
    monkeypatch.setattr(calib, "calibration_path", lambda path=None: str(tmp_path / "cal.json"))
    monkeypatch.setattr(trainer, "_cached_meta", None)
    monkeypatch.setattr(calib, "_cached_calibration", None)

    meta = run_training_passes(_synthetic_df(40), passes=3)
    assert meta["rows_trained"] >= 40
    assert meta["best_mape_pct"] <= meta["baseline_mape_pct"] + 5
    assert "best_params" in meta
    assert len(meta["passes"]) == 3
    report = format_training_report(meta)
    assert "Pass 1" in report
