import unittest
from tracking_pipeline import evaluate_tracked_slate


def snapshot(game, prob, line=20.5):
    return {"game_id": str(game), "player_id": "456", "prop": "points",
            "line": line, "over_probability": prob,
            "captured_at": "2026-10-21T22:00:00Z",
            "tipoff_at": "2026-10-21T23:00:00Z",
            "source": "research"}


def final(game, points):
    return {"game_id": str(game), "player_id": "456",
            "is_final": True, "points": points}


class TrackingPipelineTests(unittest.TestCase):
    def test_end_to_end_brier(self):
        report = evaluate_tracked_slate(
            [snapshot(1, .8), snapshot(2, .2)],
            [final(1, 25), final(2, 15)], min_samples=2)
        self.assertEqual(report["audit"]["matched"], 2)
        self.assertEqual(report["calibration"][0]["brier_score"], .04)
        self.assertEqual(report["status"], "research_only")

    def test_missing_and_push_not_losses(self):
        report = evaluate_tracked_slate(
            [snapshot(1, .5, 20), snapshot(2, .7)],
            [final(1, 20)], min_samples=2)
        self.assertEqual(report["audit"]["missing_final"], 1)
        self.assertEqual(report["audit"]["push"], 1)
        self.assertIsNone(report["calibration"][0]["brier_score"])

    def test_bad_sample_threshold(self):
        with self.assertRaises(ValueError):
            evaluate_tracked_slate([], [], min_samples=True)


if __name__ == "__main__":
    unittest.main()
