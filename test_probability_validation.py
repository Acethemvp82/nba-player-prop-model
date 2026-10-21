import unittest
from probability_validation import evaluate_frozen_probabilities


def row(game_id, probability, actual, line=20.5):
    return {"game_id": str(game_id), "player_id": "1", "prop": "points",
            "over_probability": probability, "actual": actual,
            "line": line, "is_final": True}


class FrozenProbabilityValidationTests(unittest.TestCase):
    def test_brier_and_buckets(self):
        report = evaluate_frozen_probabilities([row(1, .8, 25), row(2, .2, 15)], 2)[0]
        self.assertEqual(report["status"], "research_only")
        self.assertAlmostEqual(report["brier_score"], .04)
        self.assertEqual(report["evaluated"], 2)

    def test_push_and_duplicates(self):
        report = evaluate_frozen_probabilities(
            [row(1, .8, 20), row(1, .8, 20), row(2, .5, 20.5)], 2)[0]
        self.assertEqual(report["exclusions"]["duplicate"], 1)
        self.assertEqual(report["exclusions"]["push"], 1)
        self.assertIsNone(report["brier_score"])

    def test_invalid_and_sample_gate(self):
        report = evaluate_frozen_probabilities(
            [row(1, 1.1, 30), row(2, .8, 30)], 2)[0]
        self.assertEqual(report["exclusions"]["invalid"], 1)
        self.assertEqual(report["status"], "insufficient_data")

    def test_rejects_bad_min_samples(self):
        with self.assertRaises(ValueError):
            evaluate_frozen_probabilities([], True)


if __name__ == "__main__":
    unittest.main()
