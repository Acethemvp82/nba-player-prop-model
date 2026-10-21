"""Evaluate stored pregame snapshots using NBA verified final box scores.

Only a user-invoked call triggers network requests. Failed or unavailable
final games remain unscored, and ESPN IDs are never substituted for NBA IDs.
"""
from snapshot_storage import load_snapshots
from snapshot_final_collection import collect_snapshot_finals
from tracking_pipeline import evaluate_tracked_slate


def refresh_saved_tracking(directory, max_games=20, min_samples=30, loader=None):
    """Read local snapshots, fetch final NBA games, and evaluate matched props."""
    if type(min_samples) is not int or min_samples < 2:
        raise ValueError("min_samples must be at least 2")
    loaded = load_snapshots(directory)
    if loader is None:
        collected = collect_snapshot_finals(loaded["snapshots"], max_games=max_games)
    else:
        collected = collect_snapshot_finals(
            loaded["snapshots"], loader=loader, max_games=max_games
        )
    report = evaluate_tracked_slate(
        loaded["snapshots"], collected["final_players"], min_samples=min_samples
    )
    report["storage_audit"] = {
        "loaded_snapshots": len(loaded["snapshots"]),
        "invalid_files": len(loaded["invalid_files"]),
        "invalid_filenames": loaded["invalid_files"],
    }
    report["collection_audit"] = {
        key: collected[key] for key in (
            "games_requested", "games_loaded", "games_omitted_by_limit", "failures"
        )
    }
    return report
