import unittest
from snapshot_final_collection import collect_snapshot_finals
from nba_data import NBADataError


def snapshot(gid):
    return {"game_id": str(gid), "player_id": "456", "prop": "points",
            "line": 20.5, "over_probability": .6,
            "captured_at": "2026-10-21T22:00:00Z",
            "tipoff_at": "2026-10-21T23:00:00Z", "source": "research"}


def player(pid="456"):
    return {"player_id": pid, "player": "Example", "team": "BUF",
            "opponent": "NYK", "statistics": {"points": 25,
            "reboundsTotal": 8, "assists": 5, "threePointersMade": 3,
            "minutes": "PT30M"}}


class FinalCollectionTests(unittest.TestCase):
    def test_one_request_per_game(self):
        calls = []
        def loader(gid):
            calls.append(gid)
            return [player()]
        result = collect_snapshot_finals([snapshot(1), snapshot(1)], loader)
        self.assertEqual(calls, ["1"])
        self.assertEqual(result["final_players"][0]["points"], 25)
        self.assertTrue(result["final_players"][0]["is_final"])

    def test_failure_is_audited(self):
        def loader(gid):
            raise NBADataError("not final")
        result = collect_snapshot_finals([snapshot(1)], loader)
        self.assertEqual(result["games_loaded"], 0)
        self.assertEqual(len(result["failures"]), 1)

    def test_cap_is_reported(self):
        result = collect_snapshot_finals([snapshot(1), snapshot(2)],
                                         lambda _: [player()], max_games=1)
        self.assertEqual(result["games_omitted_by_limit"], 1)

    def test_missing_statistics_quarantines_game(self):
        empty = player()
        empty["statistics"] = {}
        result = collect_snapshot_finals([snapshot(1)], lambda _: [empty])
        self.assertEqual(result["games_loaded"], 0)
        self.assertEqual(result["final_players"], [])
        self.assertEqual(len(result["failures"]), 1)

    def test_missing_team_quarantines_game(self):
        malformed = player()
        malformed["team"] = None
        result = collect_snapshot_finals([snapshot(1)], lambda _: [malformed])
        self.assertEqual(result["games_loaded"], 0)

    def test_duplicate_player_quarantines_game(self):
        result = collect_snapshot_finals([snapshot(1)],
                                         lambda _: [player(), player()])
        self.assertEqual(result["final_players"], [])
        self.assertEqual(result["games_loaded"], 0)


if __name__ == "__main__":
    unittest.main()
