import unittest

from car_rental_recommender_core import enhance_dataframe, load_data


class TankCapacitySeedTests(unittest.TestCase):
    def test_csv_has_models_to_seed(self):
        df = enhance_dataframe(load_data("22 - Sheet1.csv"))
        models = df[
            (df["Car model"].notna()) & (df["Car model"] != "Calculator Generated")
        ]["Car model"].nunique()
        self.assertGreaterEqual(models, 1)


if __name__ == "__main__":
    unittest.main()
