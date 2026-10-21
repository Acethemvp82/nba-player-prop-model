"""Summarize ESPN historical collection reliability without inferring missing stats."""


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
    return {
        "Schedule dates checked": scanned,
        "Final games requested": requested,
        "Verified final games": loaded,
        "Failed final-game requests": requested - loaded,
        "Schedule or boxscore errors": len(failures),
        "Verified player-game records": len(observations),
        "Final-game success %": round(100 * loaded / requested, 1) if requested else None,
        "Status": ("No final games requested" if not requested
                   else "Partial historical retrieval" if loaded < requested or failures
                   else "All requested finals loaded"),
    }
