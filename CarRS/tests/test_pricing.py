"""Tests for pricing and cost calculation."""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from car_rental_recommender_core import (
    calculate_estimated_cost,
    calculate_traditional_rental_cost,
    get_recommendations,
    create_complete_cost_analysis,
)


@pytest.fixture
def pricing_config():
    path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pricing_config.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_calculate_estimated_cost_getgo_mileage(pricing_config):
    result = calculate_estimated_cost(
        distance=50,
        duration=3,
        provider="Getgo",
        is_weekend=False,
        pricing_config=pricing_config,
    )
    assert result is not None
    assert result["total_cost"] > 0
    assert result["mileage_cost"] == pytest.approx(50 * 0.39, rel=0.01)


def test_calculate_traditional_rental_cost():
    breakdown = calculate_traditional_rental_cost(
        rental_duration_cost=100,
        malaysia_usage_addon=20,
        deposit=50,
        fuel_topped_up=15,
    )
    assert breakdown["total_cost"] == pytest.approx(185.0)


def test_get_recommendations_returns_sorted(pricing_config):
    import pandas as pd

    df = pd.DataFrame(
        [
            {
                "Car Cat": "Getgo",
                "Car model": "Test",
                "Distance (KM)": 40,
                "Rental hour": 2,
                "Total": 30,
                "Cost per KM": 0.5,
                "Cost/HR": 10,
                "Consumption (KM/L)": 12,
                "Region": "Singapore",
            }
        ]
    )
    analysis = create_complete_cost_analysis(df, region="Singapore")
    recs = get_recommendations(30, 2, analysis, is_weekend=False, top_n=3)
    assert len(recs) >= 1
    costs = [r["total_cost"] for r in recs]
    assert costs == sorted(costs)
