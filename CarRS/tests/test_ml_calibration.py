"""Tests for ML calibration learning from prediction error."""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from components.ml_calibration import (
    apply_calibration,
    build_calibration,
    bucket_key,
    compute_oos_errors,
    lookup_factor,
    recalibrate,
)
from car_rental_recommender_core import create_ml_recommendations, enhance_dataframe, load_data


def _synthetic_df(n: int = 30) -> pd.DataFrame:
    rows = []
    for i in range(n):
        km = 30 + (i % 5) * 15
        hrs = 1 + (i % 4)
        rows.append(
            {
                "Car model": f"Car{i % 3}",
                "Distance (KM)": km,
                "Rental hour": hrs,
                "Total": 15 + km * 0.4 + hrs * 8 + (i % 7),
                "Car Cat": ["Getgo", "Car Club", "Econ", "Stand"][i % 4],
                "Weekday/weekend": "weekend" if i % 3 == 0 else "weekday",
            }
        )
    return pd.DataFrame(rows)


def test_bucket_key_stable():
    assert bucket_key("Getgo", 40, 1, False).startswith("Getgo|")


def test_build_calibration_has_global_factor():
    errors = compute_oos_errors(_synthetic_df(30))
    assert errors
    cal = build_calibration(errors)
    assert cal["sample_count"] == len(errors)
    assert 0.5 <= cal["global_factor"] <= 2.0
    assert "mape_pct" in cal["metrics"]


def test_apply_calibration_adjusts_cost():
    cal = {"sample_count": 10, "global_factor": 1.2, "buckets": {}}
    out = apply_calibration(100.0, cal, "Getgo", 40, 1, False)
    assert out["total_cost"] == pytest.approx(120.0)
    assert out["calibration_factor"] == 1.2


def test_lookup_prefers_fine_bucket():
    cal = {
        "global_factor": 1.0,
        "buckets": {
            bucket_key("Getgo", 40, 1, False, fine=True): {"factor": 0.9, "samples": 5},
        },
    }
    factor, used = lookup_factor(cal, "Getgo", 40, 1, False)
    assert factor == 0.9
    assert used != "global"


@pytest.mark.skipif(
    not os.path.exists(os.path.join(os.path.dirname(os.path.dirname(__file__)), "22 - Sheet1.csv")),
    reason="Local CSV not present",
)
def test_ml_recommendations_include_calibration_fields():
    csv = os.path.join(os.path.dirname(os.path.dirname(__file__)), "22 - Sheet1.csv")
    df = enhance_dataframe(load_data(csv))
    recalibrate(df)
    recs = create_ml_recommendations(40, 1, df, False, top_n=2)
    assert recs
    assert "calibration_factor" in recs[0]
    assert "raw_total_cost" in recs[0]
