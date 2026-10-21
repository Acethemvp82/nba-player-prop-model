import tempfile
import unittest

from snapshot_storage import save_snapshot
from automatic_tracking import refresh_saved_tracking
from nba_data import NBADataError


def snapshot(gid):
    return {"game_id": str(gid), "player_id": "456", "prop": "points",
            "line": 20.5, "over_probability": .8,
            "captured_at": "2026-10-21T22:00:00Z",
            "tipoff_at": "2026-10-21T23:00:00Z", "source": "research"}


def player():
    return {"player_id": "456", "player": "Test Player",
            "team": "NYK", "opponent": "BOS",
            "statistics": {"points": 25, "reboundsTotal": 5,
                           "assists": 3, "threePointersMade": 2,
                           "minutes": "PT28M"}}


class AutomaticTrackingTests(unittest.TestCase):
    def test_saved_to_fetched_to_scored(self):
        with tempfile.TemporaryDirectory() as directory:
            save_snapshot(snapshot(123), directory)
            result = refresh_saved_tracking(
                directory, loader=lambda _: [player()], min_samples=2
            )
            self.assertEqual(result["collection_audit"]["games_loaded"], 1)
            self.assertEqual(result["audit"]["matched"], 1)
            self.assertEqual(result["scored"][0]["result"], "over")

    def test_unavailable_game_not_loss(self):
        with tempfile.TemporaryDirectory() as directory:
            save_snapshot(snapshot(123), directory)
            def unavailable(_):
                raise NBADataError("not final")
            result = refresh_saved_tracking(
                directory, loader=unavailable, min_samples=2
            )
            self.assertEqual(result["collection_audit"]["games_loaded"], 0)
            self.assertEqual(result["audit"]["missing_final"], 1)
            self.assertEqual(result["calibration"][0]["evaluated"], 0)

    def test_invalid_game_budget(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                refresh_saved_tracking(directory, max_games=0)


if __name__ == "__main__":
    unittest.main()
