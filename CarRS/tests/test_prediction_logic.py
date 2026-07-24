import sys
import unittest
from pathlib import Path

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from car_rental_recommender_core import (
    predict_rental_patterns,
    predict_rental_possibility,
)


class PredictionLogicTests(unittest.TestCase):
    def test_positive_expected_rentals_never_display_as_zero(self):
        history = pd.DataFrame(
            {
                "Date": ["2026-01-03", "2026-01-10", "2026-01-17", "2026-01-24"],
                "Car Cat": ["Getgo", "Getgo", "Tribecar", "Getgo"],
            }
        )

        result = predict_rental_patterns(
            history, "2026-02-01", "2026-02-28", granularity="weekly"
        )

        frequency = result["rental_frequency"]
        self.assertGreater(frequency["expected"], 0)
        self.assertGreaterEqual(frequency["total"], 1)
        self.assertIn("expected", result["spending"])

    def test_possibility_percentage_is_bounded_without_optional_fields(self):
        history = pd.DataFrame(
            {
                "Date": ["2026-01-03", "2026-01-10", "2026-01-17", "2026-01-24"],
                "Car Cat": ["Getgo", "Getgo", "Tribecar", "Getgo"],
            }
        )

        result = predict_rental_possibility(history, "2026-02-07")

        self.assertGreaterEqual(result["possibility_percentage"], 0)
        self.assertLessEqual(result["possibility_percentage"], 100)
        self.assertEqual(2, len(result["expected_cost_range"]))

    def test_sparse_history_stays_statistical_and_reports_history_provider(self):
        history = pd.DataFrame(
            {
                "Date": ["2026-01-03", "2026-01-10", "2026-01-17"],
                "Car model": ["Honda", "Honda", "Calculator Generated"],
                "Car Cat": ["Car Club", "Car Club", "Getgo"],
                "Total": [48, 52, 999],
                "Distance (KM)": [20, 25, 0],
                "Rental hour": [2, 3, 0],
            }
        )

        result = predict_rental_possibility(history, "2026-02-07")

        self.assertEqual("Statistical", result["method"])
        self.assertEqual("Car Club", result["recommended_provider"])
        self.assertLess(result["confidence"], 0.1)
        self.assertGreater(result["expected_cost_range"][0], 0)

    @patch("car_rental_recommender_core.create_time_series_model")
    @patch("car_rental_recommender_core.analyze_historical_patterns")
    @patch("car_rental_recommender_core.predict_with_ml_patterns")
    def test_expected_rentals_keep_nonzero_spending_when_display_is_coerced(
        self, mock_ml, mock_patterns, mock_time_series
    ):
        history = pd.DataFrame(
            {
                "Date": ["2026-01-01"],
                "Car model": ["Honda"],
                "Car Cat": ["Car Club"],
                "Total": [100],
                "Distance (KM)": [20],
            }
        )
        mock_ml.return_value = {"error": "ML unavailable"}
        mock_patterns.return_value = {"provider_patterns": {}}
        mock_time_series.return_value = {
            "avg_daily_rentals": 0.1,
            "avg_weekly_rentals": 0.4,
            "avg_monthly_rentals": 1.7,
        }

        result = predict_rental_patterns(history, "2026-02-01", "2026-02-08", "weekly")

        self.assertEqual("Statistical", result["method"])
        self.assertEqual(1, result["rental_frequency"]["total"])
        self.assertGreater(result["rental_frequency"]["expected"], 0)
        self.assertLess(result["rental_frequency"]["expected"], 1)
        self.assertGreater(result["total_spending"], 0)


if __name__ == "__main__":
    unittest.main()
