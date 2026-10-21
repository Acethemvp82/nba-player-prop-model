"""Generate date-frozen NBA player baseline forecasts for research.

Uses completed NBA player games strictly before the slate date. Does not
invent sportsbook lines, opponent adjustments, or calibrated probabilities.
"""
from historical_stats import _day, player_history_summaries
from projection_baseline import baseline_projections


def build_pregame_baseline_board(observations, slate_date, min_games=5, player_ids=None):
    """Return available research baselines with strict as-of date filtering."""
    cutoff = _day(slate_date)
    if cutoff is None:
        raise ValueError("slate_date must be a valid date")
    if type(min_games) is not int or min_games < 1:
        raise ValueError("min_games must be a positive integer")
    if player_ids is not None:
        player_ids = {str(pid) for pid in player_ids}
    summaries = player_history_summaries(observations, as_of=cutoff)
    forecasts = baseline_projections(summaries, min_games=min_games)
    if player_ids is not None:
        forecasts = [row for row in forecasts if str(row["player_id"]) in player_ids]
    summary_by_id = {str(row["player_id"]): row for row in summaries}
    return [{**row, "last_game_date": summary_by_id[str(row["player_id"])]["last_game_date"],
             "days_since_last_game": (cutoff - _day(summary_by_id[str(row["player_id"])]["last_game_date"])).days,
             "history_coverage": ("limited" if row["sample_games"] < 10 else "established"),
             "slate_date": cutoff.isoformat(),
             "projection_status": "unadjusted_research_baseline",
             "over_probability": None, "sportsbook_line": None,
             "bet_tier": None} for row in forecasts]
