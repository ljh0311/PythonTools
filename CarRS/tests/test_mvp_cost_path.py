import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from components.provider_pricing import (
    coerce_predicted_rental_total,
    estimate_provider_cost,
    normalize_provider,
)
from mvp_cost_engine import (
    format_predicted_rental_display,
    get_mvp_recommendations,
    safe_predicted_rental_total,
)


class MVPricingPathTests(unittest.TestCase):
    def test_normalizes_getgo_ev_alias(self):
        self.assertEqual("Getgo(EV)", normalize_provider("Getgo EV"))
        self.assertEqual("Getgo(EV)", normalize_provider("Getgo(EV)"))

    def test_getgo_ev_cost_is_available_for_aliases(self):
        for provider in ("Getgo(EV)", "Getgo EV"):
            cost = estimate_provider_cost(40, 4, provider)
            self.assertIsNotNone(cost)
            self.assertGreater(cost["total_cost"], 0)

    def test_mvp_facade_returns_non_zero_singapore_costs(self):
        recommendations = get_mvp_recommendations(40, 4, False)
        self.assertGreaterEqual(len(recommendations), 3)
        self.assertIn("Getgo(EV)", {item["provider"] for item in recommendations})
        self.assertTrue(all(item["total_cost"] > 0 for item in recommendations))

    def test_non_zero_probability_cannot_round_to_zero_rentals(self):
        self.assertEqual(1, coerce_predicted_rental_total(0.4, [0.4]))
        self.assertEqual(1, safe_predicted_rental_total(0.4, [{"rental_probability": 0.4}]))

    def test_predicted_rental_display_never_fakes_zero(self):
        self.assertIn("shown as 1", format_predicted_rental_display(0, 0.4))
        self.assertIn("0.4", format_predicted_rental_display(1, 0.4))
        self.assertEqual("0", format_predicted_rental_display(0, 0))


if __name__ == "__main__":
    unittest.main()
