import json
import tempfile
import unittest
from pathlib import Path

from snapshot_storage import save_snapshot
from tracking_report import load_final_players, main


class ReportTests(unittest.TestCase):
    def test_reject_espn_identifiers(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "final.json"
            path.write_text(json.dumps([{"game_id": "espn:123",
                                         "player_id": "espn:456",
                                         "is_final": True}]))
            with self.assertRaisesRegex(ValueError, "numeric NBA IDs"):
                load_final_players(path)

    def test_cli_end_to_end(self):
        with tempfile.TemporaryDirectory() as folder:
            row = {"game_id": "123", "player_id": "456", "prop": "points",
                   "line": 20.5, "over_probability": .7,
                   "captured_at": "2026-10-21T22:00:00Z",
                   "tipoff_at": "2026-10-21T23:00:00Z", "source": "research"}
            save_snapshot(row, Path(folder) / "snapshots")
            final_path = Path(folder) / "final.json"
            final_path.write_text(json.dumps([
                {"game_id": "123", "player_id": "456",
                 "points": 23, "is_final": True}
            ]))
            self.assertEqual(main(["--snapshots", str(Path(folder) / "snapshots"),
                                   "--finals", str(final_path),
                                   "--min-samples", "2"]), 0)

    def test_bad_final_shape(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "final.json"
            path.write_text("{}")
            with self.assertRaisesRegex(ValueError, "must be a list"):
                load_final_players(path)


if __name__ == "__main__":
    unittest.main()
