"""Evaluate frozen pregame OVER probabilities against final box scores.

Research diagnostics only. A low Brier score does not establish profitability.
Input rows must be independently captured pregame; this module cannot verify
capture timestamps or prevent retrospective odds substitution.
"""
from math import isfinite

PROPS = ("points", "rebounds", "assists", "threes")


def evaluate_frozen_probabilities(rows, min_samples=30):
    """Report Brier score and calibration buckets by prop, without fabrication.

    Rows require unique (game_id, player_id, prop, line) keys, a frozen
    probability, and a final actual. Pushes are excluded from binary scoring.
    """
    if type(min_samples) is not int or min_samples < 2:
        raise ValueError("min_samples must be at least 2")
    seen = set()
    grouped = {p: [] for p in PROPS}
    excluded = {"invalid": 0, "duplicate": 0, "push": 0}
    for row in rows:
        if not isinstance(row, dict) or row.get("is_final") is not True:
            excluded["invalid"] += 1
            continue
        prop = row.get("prop")
        gid, pid = str(row.get("game_id") or ""), str(row.get("player_id") or "")
        prob, line, actual = (row.get(k) for k in ("over_probability", "line", "actual"))
        if (prop not in grouped or not gid.isdigit() or not pid
                or any(type(v) not in (int, float) or not isfinite(v)
                       for v in (prob, line, actual))
                or not 0 <= prob <= 1 or line < 0 or actual < 0):
            excluded["invalid"] += 1
            continue
        key = (gid, pid, prop, float(line))
        if key in seen:
            excluded["duplicate"] += 1
            continue
        seen.add(key)
        if actual == line:
            excluded["push"] += 1
            continue
        grouped[prop].append((float(prob), int(actual > line)))
    report = []
    for prop, values in grouped.items():
        n = len(values)
        buckets = []
        for low in range(0, 100, 10):
            subset = [(p, y) for p, y in values
                      if low / 100 <= p < (low + 10) / 100
                      or (low == 90 and p == 1)]
            buckets.append({"range": f"{low}-{low+10}%",
                            "count": len(subset),
                            "predicted_avg": round(sum(p for p, _ in subset) / len(subset), 4)
                            if subset else None,
                            "observed_over_rate": round(sum(y for _, y in subset) / len(subset), 4)
                            if subset else None})
        report.append({"prop": prop, "evaluated": n,
                       "status": "research_only" if n >= min_samples else "insufficient_data",
                       "brier_score": round(sum((p - y) ** 2 for p, y in values) / n, 4)
                       if n >= min_samples else None,
                       "over_rate": round(sum(y for _, y in values) / n, 4)
                       if n >= min_samples else None,
                       "buckets": buckets, "exclusions": dict(excluded)})
    return report
