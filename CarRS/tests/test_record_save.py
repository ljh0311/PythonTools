"""Tests for record dict build and append semantics."""

import os
import sys

import pandas as pd
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from car_rental_recommender_core import build_record_dict, create_trip_record
from components.collection_location import COLLECTION_LOCATION_COL, DISTANCE_RATING_COL
from components.rental_dates import RENTAL_END_DATE_COL, compute_rental_hours_from_dates


def test_build_record_dict_same_day():
    record = build_record_dict(
        region="Singapore",
        start_date="2024-06-01",
        end_date="2024-06-01",
        car_model="Honda Fit",
        provider="Getgo",
        distance=25,
        rental_hour=3,
        total=40,
        weekend="weekday",
        collection_location="Tampines Hub",
        distance_rating=4,
    )
    assert record["Rental hour"] == 3
    assert record[COLLECTION_LOCATION_COL] == "Tampines Hub"
    assert record[DISTANCE_RATING_COL] == 4


def test_build_record_dict_multi_day_hours():
    record = build_record_dict(
        region="Singapore",
        start_date="2024-06-01",
        end_date="2024-06-03",
        car_model="Honda Fit",
        provider="Getgo",
        distance=100,
        rental_hour=3,
        total=120,
    )
    assert record["Rental hour"] == 72


def test_compute_rental_hours_multi_day():
    hours = compute_rental_hours_from_dates("2024-01-01", "2024-01-03", fallback_hours=3)
    assert hours == 72


def test_dataframe_append_from_record_dict():
    record = build_record_dict(
        region="Singapore",
        start_date="2024-06-01",
        car_model="Test",
        provider="Getgo",
        distance=10,
        rental_hour=2,
        total=25,
    )
    df = pd.DataFrame([record])
    assert len(df) == 1
    assert df.at[0, "Distance (KM)"] == 10


def test_create_trip_record_includes_end_date():
    record = create_trip_record(
        distance=50,
        duration=4,
        provider="Getgo",
        total_cost=60,
        start_date="2024-07-01",
        end_date="2024-07-02",
        collection_location="Airport",
        distance_rating=5,
    )
    assert RENTAL_END_DATE_COL in record
    assert record[COLLECTION_LOCATION_COL] == "Airport"
    assert record["Rental hour"] == 48
