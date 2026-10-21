import tempfile
import unittest
from saved_tracking import evaluate_saved_snapshots
from snapshot_storage import save_snapshot


def snap(game, probability):
    return {"game_id": str(game), "player_id": "456", "prop": "points",
            "line": 20.5, "over_probability": probability,
            "captured_at": "2026-10-21T22:00:00Z",
            "tipoff_at": "2026-10-21T23:00:00Z", "source": "research"}


def final(game, points):
    return {"game_id": str(game), "player_id": "456",
            "is_final": True, "points": points}


class SavedTrackingTests(unittest.TestCase):
    def test_saved_snapshots_to_calibration(self):
        with tempfile.TemporaryDirectory() as folder:
            save_snapshot(snap(1, .8), folder)
            save_snapshot(snap(2, .2), folder)
            report = evaluate_saved_snapshots(
                folder, [final(1, 25), final(2, 15)], min_samples=2
            )
            self.assertEqual(report["storage_audit"]["loaded_snapshots"], 2)
            self.assertEqual(report["audit"]["matched"], 2)
            self.assertAlmostEqual(report["calibration"][0]["brier_score"], .04)

    def test_corrupt_file_is_audited(self):
        with tempfile.TemporaryDirectory() as folder:
            _, path = save_snapshot(snap(1, .8), folder)
            path.write_text("{broken", encoding="utf-8")
            report = evaluate_saved_snapshots(folder, [], min_samples=2)
            self.assertEqual(report["storage_audit"]["invalid_files"], 1)
            self.assertEqual(report["audit"]["matched"], 0)

    def test_missing_final_not_scored_as_loss(self):
        with tempfile.TemporaryDirectory() as folder:
            save_snapshot(snap(1, .8), folder)
            report = evaluate_saved_snapshots(folder, [], min_samples=2)
            self.assertEqual(report["audit"]["missing_final"], 1)
            self.assertEqual(report["calibration"][0]["evaluated"], 0)

    def test_invalid_final_input(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(TypeError):
                evaluate_saved_snapshots(folder, None)


if __name__ == "__main__":
    unittest.main()
