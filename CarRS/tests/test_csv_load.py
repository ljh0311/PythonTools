"""Tests for CSV load and cleaning pipeline."""

import os
import sys
import tempfile

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from car_rental_recommender_core import load_data, enhance_dataframe, run_cleaning_pipeline
from components.collection_location import COLLECTION_LOCATION_COL, DISTANCE_RATING_COL
from components.rental_dates import RENTAL_END_DATE_COL


@pytest.fixture
def sample_csv_path():
    csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "22 - Sheet1.csv")
    if not os.path.exists(csv_path):
        pytest.skip("22 - Sheet1.csv not present locally")
    return csv_path


def test_load_data_adds_region(sample_csv_path):
    df = load_data(sample_csv_path)
    assert "Region" in df.columns
    assert len(df) > 0


def test_enhance_dataframe_adds_extended_columns(sample_csv_path):
    df = load_data(sample_csv_path)
    df = enhance_dataframe(df)
    assert RENTAL_END_DATE_COL in df.columns
    assert COLLECTION_LOCATION_COL in df.columns
    assert DISTANCE_RATING_COL in df.columns
    assert pd.api.types.is_datetime64_any_dtype(df["Date"])


def test_cleaning_pipeline_roundtrip():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False, newline="") as src:
        src.write(
            "Car model,Distance (KM),Total,Date,Rental hour,Car Cat,Weekday/weekend\n"
            "Honda Fit,10,20,2024-01-01,2,Getgo,weekday\n"
        )
        src_path = src.name
    out_path = src_path + ".out.csv"
    try:
        df, report = run_cleaning_pipeline(src_path, output_path=out_path)
        assert report["rows_out"] == 1
        assert os.path.exists(out_path)
        assert RENTAL_END_DATE_COL in df.columns
    finally:
        for p in (src_path, out_path):
            if os.path.exists(p):
                os.remove(p)
