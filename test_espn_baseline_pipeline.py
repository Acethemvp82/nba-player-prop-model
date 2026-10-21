import unittest
from historical_stats import player_history_summaries, _valid_game_id
from pregame_baseline_board import build_pregame_baseline_board


def row(i, game_id=None):
    return {"game_id": game_id or f"espn:{1000+i}", "player_id": "espn:55",
            "player": "Example", "team": "BOS", "game_date": f"2026-10-{i+1:02d}",
            "is_final": True, "minutes": 30, "points": 20, "rebounds": 7,
            "assists": 4, "threes": 2}


class EspnBaselinePipelineTests(unittest.TestCase):
    def test_namespaced_espn_ids_produce_baselines(self):
        observations = [row(i) for i in range(5)]
        forecasts = build_pregame_baseline_board(observations, "2026-10-21")
        self.assertEqual(len(forecasts), 4)
        points = next(p for p in forecasts if p["prop"] == "points")
        self.assertEqual(points["baseline"], 20)
        self.assertEqual(points["player_id"], "espn:55")

    def test_same_day_results_excluded(self):
        observations = [row(i) for i in range(4)]
        observations.append({**row(4), "game_date": "2026-10-21"})
        self.assertEqual(build_pregame_baseline_board(observations, "2026-10-21"), [])

    def test_reject_malformed_ids(self):
        for bad in ("espn:", "espn:abc", "nba:123", "espn:12x", True, None):
            self.assertFalse(_valid_game_id(bad))
        self.assertTrue(_valid_game_id("0022600001"))
        self.assertTrue(_valid_game_id("espn:401234567"))


if __name__ == "__main__":
    unittest.main()
