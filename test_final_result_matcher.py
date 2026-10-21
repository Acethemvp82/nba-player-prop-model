import unittest
from final_result_matcher import match_final_results


def snap(**updates):
    row = {"game_id": "123", "player_id": "456", "prop": "points",
           "line": 20.5, "over_probability": .55,
           "captured_at": "2026-10-21T22:00:00Z",
           "tipoff_at": "2026-10-21T23:00:00Z", "source": "research"}
    row.update(updates)
    return row


def final(**updates):
    row = {"game_id": "123", "player_id": "456", "is_final": True, "points": 25}
    row.update(updates)
    return row


class MatcherTests(unittest.TestCase):
    def test_over(self):
        result = match_final_results([snap()], [final()])
        self.assertEqual(result["scored"][0]["result"], "over")
        self.assertEqual(result["audit"]["matched"], 1)

    def test_missing_final(self):
        self.assertEqual(match_final_results([snap()], [])["audit"]["missing_final"], 1)

    def test_push(self):
        result = match_final_results([snap(line=25)], [final()])
        self.assertEqual(result["scored"][0]["result"], "push")

    def test_duplicate_snapshot(self):
        result = match_final_results([snap(), snap()], [final()])
        self.assertEqual(result["audit"]["duplicate_snapshot"], 1)

    def test_ambiguous_final(self):
        result = match_final_results([snap()], [final(), final(points=10)])
        self.assertEqual(result["audit"]["ambiguous_final"], 1)
        self.assertEqual(result["scored"], [])

    def test_missing_stat_not_zero(self):
        result = match_final_results([snap()], [final(points=None)])
        self.assertEqual(result["audit"]["missing_stat"], 1)
        self.assertEqual(result["scored"], [])


if __name__ == "__main__":
    unittest.main()
