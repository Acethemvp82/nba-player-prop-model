import unittest
from prop_probability import normal_over_probability, american_odds_break_even, probability_edge


class ProbabilityHelpersTest(unittest.TestCase):
    def test_even_line(self):
        self.assertAlmostEqual(normal_over_probability(20, 20, 5), 0.5)

    def test_direction(self):
        self.assertGreater(normal_over_probability(25, 20.5, 5), 0.5)
        self.assertLess(normal_over_probability(15, 20.5, 5), 0.5)

    def test_invalid_inputs(self):
        for args in [(20, 20, 0), (20, 20, -1), (float('nan'), 20, 3), (True, 20, 3)]:
            self.assertIsNone(normal_over_probability(*args))

    def test_odds(self):
        self.assertAlmostEqual(american_odds_break_even(-110), 110 / 210)
        self.assertAlmostEqual(american_odds_break_even(150), 100 / 250)
        self.assertIsNone(american_odds_break_even(-50))
        self.assertIsNone(american_odds_break_even(True))

    def test_edge(self):
        self.assertAlmostEqual(probability_edge(0.6, -110), 0.6 - 110 / 210)
        self.assertIsNone(probability_edge(1.1, -110))


if __name__ == "__main__":
    unittest.main()
