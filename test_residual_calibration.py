import unittest
from residual_calibration import residual_calibration, walk_forward_residuals


class ResidualCalibrationTest(unittest.TestCase):
    def test_abstains_without_samples(self):
        rows = residual_calibration({"points": [{"error": 2.0}]}, min_samples=2)
        self.assertEqual(rows[0]["status"], "insufficient_data")
        self.assertIsNone(rows[0]["residual_std"])

    def test_rmse_and_sample_gate(self):
        rows = residual_calibration({"points": [{"error": 3.0}, {"error": 4.0}]}, min_samples=2)
        self.assertAlmostEqual(rows[0]["residual_std"], (12.5) ** 0.5, places=4)

    def test_invalid_samples(self):
        self.assertRaises(ValueError, residual_calibration, {}, True)
        rows = residual_calibration({"points": [{"error": float("nan")}, {"error": True}]})
        self.assertEqual(rows[0]["samples"], 0)

    def test_future_games_excluded(self):
        data = [{"is_final": True, "game_date": "2026-10-21",
                 "game_id": "123", "player_id": "99", "minutes": 30, "points": 25}]
        result = walk_forward_residuals(data, "2026-10-21")
        self.assertEqual(result["points"], [])


if __name__ == "__main__":
    unittest.main()
