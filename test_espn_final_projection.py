"""Offline ESPN final-boxscore parser and projection integration tests."""
import unittest

from nba_data import NBADataError
from espn_final_stats import parse_final_espn_boxscore, _minutes
from pregame_baseline_board import build_pregame_baseline_board


def payload(event_id="401001", minutes="31:30", completed=True):
    return {
        "header": {"competitions": [{
            "id": event_id, "status": {"type": {"completed": completed}}
        }]},
        "boxscore": {"players": [{
            "team": {"abbreviation": "BOS"},
            "statistics": [{
                "labels": ["MIN", "PTS", "REB", "AST", "3PT"],
                "athletes": [{
                    "athlete": {"id": "55", "displayName": "Sample Player"},
                    "stats": [minutes, "24", "8", "6", "3-7"]
                }]
            }]
        }]}
    }


class ESPNFinalProjectionTests(unittest.TestCase):
    def test_minutes_parsing(self):
        self.assertEqual(_minutes("31:30"), 31.5)
        self.assertEqual(_minutes("28"), 28.0)
        for value in ("DNP", "10:99", "-5", "61:00", True):
            self.assertIsNone(_minutes(value))

    def test_final_game_fields(self):
        result = parse_final_espn_boxscore(payload(), "401001")
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["minutes"], 31.5)
        self.assertTrue(result[0]["is_final"])
        self.assertEqual(result[0]["player_id"], "espn:55")
        self.assertEqual(result[0]["threes"], 3)

    def test_unfinished_game_rejected(self):
        with self.assertRaises(NBADataError):
            parse_final_espn_boxscore(payload(completed=False), "401001")

    def test_zero_minutes_not_counted(self):
        with self.assertRaises(NBADataError):
            parse_final_espn_boxscore(payload(minutes="0"), "401001")

    def test_parser_to_baseline_end_to_end(self):
        observations = []
        for i in range(5):
            game_id = str(401001 + i)
            parsed = parse_final_espn_boxscore(payload(event_id=game_id), game_id)
            observations.extend({
                **player, "game_id": f"espn:{game_id}",
                "game_date": f"2026-10-{i+1:02d}"
            } for player in parsed)
        forecasts = build_pregame_baseline_board(observations, "2026-10-21")
        self.assertEqual(len(forecasts), 4)
        self.assertEqual(next(row for row in forecasts if row["prop"] == "points")["baseline"], 24)


if __name__ == "__main__":
    unittest.main()
