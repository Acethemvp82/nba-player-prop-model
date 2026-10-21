import json
import tempfile
import unittest

from snapshot_storage import save_snapshot, load_snapshots


def snapshot():
    return {"game_id": "123", "player_id": "456", "prop": "points",
            "line": 20.5, "over_probability": .55,
            "captured_at": "2026-10-21T22:00:00Z",
            "tipoff_at": "2026-10-21T23:00:00Z",
            "source": "research"}


class StorageTests(unittest.TestCase):
    def test_round_trip_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            created, path = save_snapshot(snapshot(), directory)
            self.assertTrue(created)
            self.assertTrue(path.exists())
            altered = snapshot()
            altered["over_probability"] = .99
            created_again, _ = save_snapshot(altered, directory)
            self.assertFalse(created_again)
            records = load_snapshots(directory)
            self.assertEqual(records["snapshots"][0]["over_probability"], .55)
            self.assertEqual(records["invalid_files"], [])

    def test_corruption_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            _, path = save_snapshot(snapshot(), directory)
            path.write_text("{bad json", encoding="utf-8")
            result = load_snapshots(directory)
            self.assertEqual(result["snapshots"], [])
            self.assertEqual(result["invalid_files"], [path.name])

    def test_invalid_snapshot_not_written(self):
        with tempfile.TemporaryDirectory() as directory:
            row = snapshot()
            row["captured_at"] = row["tipoff_at"]
            with self.assertRaises(ValueError):
                save_snapshot(row, directory)
            self.assertEqual(load_snapshots(directory)["snapshots"], [])


if __name__ == "__main__":
    unittest.main()
