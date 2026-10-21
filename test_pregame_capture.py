import tempfile
import unittest
from datetime import datetime, timezone
from pregame_capture import capture_pregame_prediction
from snapshot_storage import load_snapshots


def prediction():
    return {"game_id": "123", "player_id": "456", "prop": "points",
            "line": 20.5, "over_probability": .62,
            "tipoff_at": "2026-10-22T01:00:00Z", "source": "manual research",
            "captured_at": "2000-01-01T00:00:00Z"}


class CaptureTests(unittest.TestCase):
    def test_server_time_replaces_supplied_timestamp(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = datetime(2026, 10, 22, 0, 30, tzinfo=timezone.utc)
            result = capture_pregame_prediction(prediction(), folder, now=clock)
            self.assertTrue(result["created"])
            self.assertEqual(load_snapshots(folder)["snapshots"][0]["captured_at"],
                             "2026-10-22T00:30:00+00:00")

    def test_reject_after_tipoff(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "at or after"):
                capture_pregame_prediction(
                    prediction(), folder,
                    now=datetime(2026, 10, 22, 1, 0, tzinfo=timezone.utc)
                )

    def test_duplicate_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            clock = datetime(2026, 10, 22, 0, 30, tzinfo=timezone.utc)
            self.assertTrue(capture_pregame_prediction(prediction(), folder, clock)["created"])
            self.assertFalse(capture_pregame_prediction(prediction(), folder, clock)["created"])
            self.assertEqual(len(load_snapshots(folder)["snapshots"]), 1)

    def test_naive_clock_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaisesRegex(ValueError, "timezone-aware"):
                capture_pregame_prediction(prediction(), folder,
                                           now=datetime(2026, 10, 22, 0, 30))


if __name__ == "__main__":
    unittest.main()
