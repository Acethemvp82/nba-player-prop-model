"""Summarize ESPN historical collection reliability without inferring missing stats."""

from datetime import date


def espn_history_health(history):
    """Descriptive completeness metrics from a bounded ESPN collection result."""
    if not isinstance(history, dict):
        raise ValueError("Invalid ESPN history result")
    requested = history.get("games_requested")
    loaded = history.get("games_loaded")
    scanned = history.get("dates_checked")
    failures = history.get("failures")
    observations = history.get("observations")
    if (any(type(value) is not int or value < 0 for value in (requested, loaded, scanned))
            or loaded > requested or not isinstance(failures, list)
            or not isinstance(observations, list)):
        raise ValueError("Invalid ESPN history counters")
    if any(not isinstance(item, dict) for item in failures):
        raise ValueError("Invalid ESPN failure details")
    schedule_failures = sum("event_id" not in item for item in failures)
    boxscore_failures = sum("event_id" in item for item in failures)
    verified_dates = []
    for observation in observations:
        if not isinstance(observation, dict):
            continue
        played = observation.get("game_date")
        if not isinstance(played, str):
            continue
        try:
            parsed = date.fromisoformat(played)
        except ValueError:
            continue
        if parsed.isoformat() == played:
            verified_dates.append(played)
    return {
        "Oldest verified game": min(verified_dates) if verified_dates else None,
        "Newest verified game": max(verified_dates) if verified_dates else None,
        "Schedule dates checked": scanned,
        "Final games requested": requested,
        "Verified final games": loaded,
        "Failed final-game requests": requested - loaded,
        "Schedule or boxscore errors": len(failures),
        "Failed schedule dates": schedule_failures,
        "Failed boxscore validations": boxscore_failures,
        "Verified player-game records": len(observations),
        "Final-game success %": round(100 * loaded / requested, 1) if requested else None,
        "Status": ("Schedule retrieval errors; no finals requested"
                   if not requested and schedule_failures
                   else "No final games requested" if not requested
                   else "Partial historical retrieval" if loaded < requested or failures
                   else "All requested finals loaded"),
    }
