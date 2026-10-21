"""Evaluate locally saved pregame snapshots against supplied final player data.

This is a manual, read-only evaluation entrypoint. It does not fetch live
scores, persist final results, or establish authenticity of saved timestamps.
"""
from snapshot_storage import load_snapshots
from tracking_pipeline import evaluate_tracked_slate


def evaluate_saved_snapshots(directory, final_players, min_samples=30):
    """Load snapshots and evaluate; expose invalid-file counts in the audit."""
    if type(min_samples) is not int or min_samples < 2:
        raise ValueError("min_samples must be at least 2")
    if not isinstance(final_players, (list, tuple)):
        raise TypeError("final_players must be a list or tuple")
    loaded = load_snapshots(directory)
    result = evaluate_tracked_slate(
        loaded["snapshots"], final_players, min_samples=min_samples
    )
    result["storage_audit"] = {
        "loaded_snapshots": len(loaded["snapshots"]),
        "invalid_files": len(loaded["invalid_files"]),
        "invalid_filenames": loaded["invalid_files"],
    }
    return result
