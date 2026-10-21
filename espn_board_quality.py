"""Explain verified ESPN historical sample sufficiency without betting tiers."""


def history_sample_status(sample_games, last_five_games, last_ten_games):
    """Return a descriptive coverage label; never a prediction or bet grade."""
    values = (sample_games, last_five_games, last_ten_games)
    if any(isinstance(v, bool) or (v is not None and
           (not isinstance(v, (int, float)) or v < 0 or int(v) != v))
           for v in values):
        return "Invalid history metadata"
    total = 0 if sample_games is None else int(sample_games)
    last5 = 0 if last_five_games is None else int(last_five_games)
    last10 = 0 if last_ten_games is None else int(last_ten_games)
    if last5 > min(total, 5) or last10 > min(total, 10) or last5 > last10:
        return "Invalid history metadata"
    if total == 0:
        return "No verified history"
    if last10 >= 10:
        return "10+ verified games"
    if last5 >= 5:
        return "5–9 verified games"
    return "Limited verified history"
