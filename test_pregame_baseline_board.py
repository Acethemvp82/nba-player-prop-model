import unittest
from pregame_baseline_board import build_pregame_baseline_board


def game(day, gid, points):
    return {"game_date": day, "game_id": str(gid), "player_id": "456",
            "player": "Test Player", "team": "NYK", "is_final": True,
            "minutes": 30, "points": points, "rebounds": 5,
            "assists": 4, "threes": 2}


class PregameBaselineBoardTests(unittest.TestCase):
    def test_cutoff_excludes_same_day_and_future_results(self):
        rows = [game("2026-10-10", i, 10) for i in range(1, 6)]
        rows += [game("2026-10-21", 6, 100), game("2026-10-22", 7, 200)]
        result = build_pregame_baseline_board(rows, "2026-10-21")
        points = next(row for row in result if row["prop"] == "points")
        self.assertEqual(points["baseline"], 10)
        self.assertIsNone(points["over_probability"])
        self.assertIsNone(points["sportsbook_line"])
        self.assertEqual(points["history_coverage"], "limited")
        self.assertEqual(points["last_game_date"], "2026-10-10")
        self.assertEqual(points["days_since_last_game"], 11)

    def test_no_history_no_forecast(self):
        self.assertEqual(build_pregame_baseline_board([], "2026-10-21"), [])

    def test_player_filter(self):
        rows = [game("2026-10-10", i, 10) for i in range(1, 6)]
        self.assertEqual(build_pregame_baseline_board(rows, "2026-10-21",
                                                      player_ids=["999"]), [])

    def test_invalid_cutoff(self):
        with self.assertRaises(ValueError):
            build_pregame_baseline_board([], "not-a-date")


if __name__ == "__main__":
    unittest.main()
