"""Validate imported pregame snapshots as a batch before result collection.

Reject entire imports with duplicate keys or invalid rows; this avoids
quietly dropping predictions from accuracy tracking.
"""
from pregame_snapshot import snapshot_key, validate_pregame_snapshot


def validate_snapshot_batch(rows, max_rows=100000):
    if not isinstance(rows, list):
        raise ValueError("Snapshots must be a JSON array")
    if len(rows) > max_rows:
        raise ValueError("Too many snapshots")
    seen = set()
    for index, row in enumerate(rows):
        valid, reason = validate_pregame_snapshot(row)
        if not valid:
            raise ValueError(f"Snapshot {index + 1}: {reason}")
        key = snapshot_key(row)
        if key in seen:
            raise ValueError(f"Snapshot {index + 1}: duplicate game/player/prop/line")
        seen.add(key)
    return rows
