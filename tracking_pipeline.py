"""Research-only pipeline for matching frozen predictions to final outcomes.

This module does not fetch data, schedule jobs, or persist snapshots.
Callers must supply independently saved pre-tipoff snapshots and final box scores.
"""
from final_result_matcher import match_final_results
from probability_validation import evaluate_frozen_probabilities


def evaluate_tracked_slate(snapshots, final_players, min_samples=30):
    """Return scored results, integrity audit and per-prop calibration report.

    Preserve unmatched predictions in the audit rather than treating them as
    losses. Pushes remain in scored results but are excluded from Brier scoring.
    """
    if type(min_samples) is not int or min_samples < 2:
        raise ValueError("min_samples must be at least 2")
    matched = match_final_results(snapshots, final_players)
    validation = evaluate_frozen_probabilities(matched["scored"], min_samples)
    return {
        "scored": matched["scored"],
        "audit": matched["audit"],
        "calibration": validation,
        "status": "research_only",
        "note": ("Results require independently captured pregame snapshots; "
                 "the pipeline does not prove timestamp authenticity or "
                 "validate sportsbook odds."),
    }
