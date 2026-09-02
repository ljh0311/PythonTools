import unittest

from components.collection_location import (
    ensure_collection_columns,
    format_rating_choice,
    parse_rating_choice,
    rating_choice_labels,
)
import pandas as pd


class CollectionLocationTests(unittest.TestCase):
    def test_rating_labels_cover_0_to_5(self):
        labels = rating_choice_labels()
        self.assertEqual("", labels[0])
        self.assertTrue(labels[1].startswith("0 —"))
        self.assertTrue(labels[-1].startswith("5 —"))

    def test_parse_rating_choice(self):
        ok, value, err = parse_rating_choice("3 — Acceptable by bus/MRT")
        self.assertTrue(ok)
        self.assertEqual(3, value)
        self.assertIsNone(err)
        ok, value, err = parse_rating_choice("")
        self.assertTrue(ok)
        self.assertIsNone(value)
        ok, value, err = parse_rating_choice("9")
        self.assertFalse(ok)

    def test_ensure_columns(self):
        df = ensure_collection_columns(pd.DataFrame({"Date": ["2026-01-01"]}))
        self.assertIn("Collection location", df.columns)
        self.assertIn("Distance rating", df.columns)
        self.assertEqual("3 — Acceptable by bus/MRT", format_rating_choice(3))


if __name__ == "__main__":
    unittest.main()
