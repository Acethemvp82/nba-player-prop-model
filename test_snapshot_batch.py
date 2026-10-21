import unittest
from snapshot_batch import validate_snapshot_batch


def record():
    return {"game_id": "123", "player_id": "456", "prop": "points",
            "line": 20.5, "over_probability": .6,
            "captured_at": "2026-10-21T22:00:00Z",
            "tipoff_at": "2026-10-21T23:00:00Z", "source": "research"}


class SnapshotBatchTests(unittest.TestCase):
    def test_valid(self):
        rows = [record()]
        self.assertIs(validate_snapshot_batch(rows), rows)

    def test_duplicate_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate"):
            validate_snapshot_batch([record(), record()])

    def test_post_tipoff_rejected(self):
        row = record()
        row["captured_at"] = "2026-10-22T00:00:00Z"
        with self.assertRaisesRegex(ValueError, "not_pregame"):
            validate_snapshot_batch([row])

    def test_non_array_rejected(self):
        with self.assertRaisesRegex(ValueError, "JSON array"):
            validate_snapshot_batch({})

    def test_cap(self):
        with self.assertRaisesRegex(ValueError, "Too many"):
            validate_snapshot_batch([record()], max_rows=0)


if __name__ == "__main__":
    unittest.main()
