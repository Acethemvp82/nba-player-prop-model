"""Conservative normal-approximation OVER probability utilities.

These functions are research helpers, not calibrated sportsbook predictions.
Do not display them as betting probabilities until validated on held-out games.
"""
from math import erf, isfinite, sqrt


def normal_over_probability(projection, line, residual_std):
    """Return P(actual > line) under a continuous normal residual model.

    None indicates missing/invalid inputs. No artificial confidence floor or cap.
    """
    values = (projection, line, residual_std)
    if any(not isinstance(x, (int, float)) or isinstance(x, bool)
           or not isfinite(x) for x in values):
        return None
    if projection < 0 or line < 0 or residual_std <= 0:
        return None
    z = (float(projection) - float(line)) / (float(residual_std) * sqrt(2))
    return max(0.0, min(1.0, 0.5 * (1.0 + erf(z))))


def american_odds_break_even(odds):
    """Return implied break-even probability, excluding vig adjustments."""
    if not isinstance(odds, int) or isinstance(odds, bool) or -100 < odds < 100:
        return None
    return 100 / (odds + 100) if odds > 0 else -odds / (-odds + 100)


def probability_edge(probability, american_odds):
    """Probability-point edge vs raw implied break-even probability."""
    implied = american_odds_break_even(american_odds)
    if implied is None or not isinstance(probability, (int, float)) or isinstance(probability, bool):
        return None
    if not isfinite(probability) or not 0 <= probability <= 1:
        return None
    return probability - implied
