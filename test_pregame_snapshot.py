import unittest
from pregame_snapshot import validate_pregame_snapshot, snapshot_key


def example():
    return {"game_id": "123", "player_id": "456", "prop": "points",
            "line": 20.5, "over_probability": .57,
            "captured_at": "2026-10-21T22:00:00Z",
            "tipoff_at": "2026-10-21T23:00:00+00:00",
            "source": "research-baseline"}


class SnapshotTests(unittest.TestCase):
    def test_valid(self):
        self.assertEqual(validate_pregame_snapshot(example()), (True, "valid"))
        self.assertEqual(snapshot_key(example()), ("123", "456", "points", 20.5))

    def test_tipoff_and_later_rejected(self):
        for captured in ("2026-10-21T23:00:00Z", "2026-10-22T00:00:00Z"):
            row = example()
            row["captured_at"] = captured
            self.assertEqual(validate_pregame_snapshot(row)[1], "not_pregame")

    def test_timezone_required(self):
        row = example()
        row["captured_at"] = "2026-10-21T22:00:00"
        self.assertEqual(validate_pregame_snapshot(row)[1], "invalid_timestamp")

    def test_invalid_numeric(self):
        for value in (True, float("nan"), -1, 1.2):
            row = example()
            row["over_probability"] = value
            self.assertEqual(validate_pregame_snapshot(row)[1], "invalid_numeric")

    def test_missing_source(self):
        row = example()
        row["source"] = " "
        self.assertEqual(validate_pregame_snapshot(row)[1], "missing_source")


if __name__ == "__main__":
    unittest.main()
