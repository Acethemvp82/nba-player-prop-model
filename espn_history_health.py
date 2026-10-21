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
    limit_reached = history.get("request_limit_reached", False)
    omitted = history.get("eligible_games_omitted", 0)
    if type(limit_reached) is not bool:
        raise ValueError("Invalid ESPN request-limit flag")
    if type(omitted) is not int or omitted < 0:
        raise ValueError("Invalid ESPN omitted-game count")
    truncated = history.get("history_truncated", omitted > 0)
    if type(truncated) is not bool or truncated != (omitted > 0):
        raise ValueError("Inconsistent ESPN truncation flag")
    schedule_failures = sum("event_id" not in item for item in failures)
    boxscore_failures = sum("event_id" in item for item in failures)
    # Distinguish scanned dates from dates whose scoreboard failed.
    # Boxscore failures are already represented in requested/loaded counts.
    failed_schedule_dates = {
        item.get("date") for item in failures
        if "event_id" not in item and isinstance(item.get("date"), str)
    }
    unassigned_schedule_failures = sum(
        "event_id" not in item and not isinstance(item.get("date"), str)
        for item in failures
    )
    # An undated schedule error makes the exact number of affected dates
    # unknowable. Do not present an unjustified schedule coverage percentage.
    usable_schedule_dates = (
        scanned - len(failed_schedule_dates)
        if not unassigned_schedule_failures else None
    )
    if usable_schedule_dates is not None and usable_schedule_dates < 0:
        raise ValueError("More failed schedule dates than dates checked")
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
        "Schedule dates usable": usable_schedule_dates,
        "Schedule coverage %": round(100 * usable_schedule_dates / scanned, 1) if scanned and usable_schedule_dates is not None else None,
        "Request limit reached": limit_reached,
        "Eligible games omitted by limit": omitted,
        "History truncated by limit": truncated,
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
                   else "Historical sample truncated by request limit" if truncated
                   else "Request limit reached; no eligible games omitted" if limit_reached
                   else "All requested finals loaded"),
    }
