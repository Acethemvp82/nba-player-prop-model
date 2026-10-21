"""Restore exported snapshot JSON to local append-only storage.

Imported timestamps are claims and cannot be independently authenticated.
Validate the entire batch before writing any files.
"""
from snapshot_batch import validate_snapshot_batch
from snapshot_storage import save_snapshot


def restore_snapshot_backup(rows, directory):
    validated = validate_snapshot_batch(rows)
    created = 0
    duplicates = 0
    for row in validated:
        was_created, _ = save_snapshot(row, directory)
        if was_created:
            created += 1
        else:
            duplicates += 1
    return {"imported": created, "already_present": duplicates,
            "total": len(validated), "timestamps_verified": False}
