import sys
import unittest
import warnings
from pathlib import Path

import matplotlib
import pandas as pd
from matplotlib.figure import Figure

matplotlib.use("Agg")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from components.ev_traditional_analysis import (
    DEFAULT_EV_EFFICIENCY_KM_PER_KWH,
    ELECTRIC,
    TRADITIONAL,
    build_comparison_figure,
    classify_vehicle_type,
    compute_ev_traditional_stats,
)


class EVTraditionalGraphTests(unittest.TestCase):
    def setUp(self):
        self.df = pd.DataFrame(
            [
                {
                    "Car Cat": "Getgo(EV)",
                    "kWh Used": None,
                    "Distance (KM)": 60,
                    "Total": 30,
                    "Cost per KM": 0.5,
                },
                {
                    "Car Cat": "Getgo",
                    "Distance (KM)": 40,
                    "Fuel pumped": 4,
                    "Total": 40,
                    "Cost per KM": 1.0,
                },
            ]
        )

    def test_classifies_ev_provider_without_kwh(self):
        self.assertEqual(
            [ELECTRIC, TRADITIONAL], classify_vehicle_type(self.df).tolist()
        )

    def test_missing_ev_kwh_uses_default_efficiency_for_co2(self):
        stats = compute_ev_traditional_stats(self.df, fuel_price=2.51, cost_per_kwh=0.45)

        self.assertAlmostEqual(
            60 / DEFAULT_EV_EFFICIENCY_KM_PER_KWH,
            stats["ev"]["total_kwh"],
        )

    def test_renders_six_comparison_charts_without_layout_warning(self):
        stats = compute_ev_traditional_stats(self.df, fuel_price=2.51, cost_per_kwh=0.45)
        figure = Figure(figsize=(10, 6))

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            axes = build_comparison_figure(
                figure, stats, stats["ev_df"], stats["traditional_df"]
            )
            figure.canvas.draw()

        self.assertEqual(6, len(figure.axes))
        self.assertEqual(
            [
                "Average Cost",
                "Trip Count",
                "Energy Efficiency",
                "Cost per km",
                "Distance Distribution",
                "CO2 per km",
            ],
            [axis.get_title() for axis in axes.flat],
        )
        self.assertFalse(
            any("tight_layout" in str(warning.message) for warning in caught)
        )


if __name__ == "__main__":
    unittest.main()
