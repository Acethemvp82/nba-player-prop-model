import tempfile
import unittest
from snapshot_backup import restore_snapshot_backup
from snapshot_storage import load_snapshots


def snapshot():
    return {"game_id": "123", "player_id": "456", "prop": "points",
            "line": 20.5, "over_probability": 0.6,
            "captured_at": "2026-10-21T22:00:00Z",
            "tipoff_at": "2026-10-21T23:00:00Z", "source": "manual research"}


class SnapshotBackupTests(unittest.TestCase):
    def test_restore_and_idempotent_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            first = restore_snapshot_backup([snapshot()], folder)
            second = restore_snapshot_backup([snapshot()], folder)
            self.assertEqual(first["imported"], 1)
            self.assertEqual(second["already_present"], 1)
            self.assertFalse(first["timestamps_verified"])
            self.assertEqual(len(load_snapshots(folder)["snapshots"]), 1)

    def test_invalid_batch_cannot_partially_restore(self):
        with tempfile.TemporaryDirectory() as folder:
            bad = snapshot()
            bad["captured_at"] = "2026-10-22T01:00:00Z"
            with self.assertRaises(ValueError):
                restore_snapshot_backup([snapshot(), bad], folder)
            self.assertEqual(load_snapshots(folder)["snapshots"], [])


if __name__ == "__main__":
    unittest.main()
