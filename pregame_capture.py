"""Capture pre-tipoff research probabilities using the actual server clock.

No backdating is allowed through this helper. Local JSON persistence is
append-only but not durable across ephemeral Streamlit deployments.
"""
from datetime import datetime, timezone

from pregame_snapshot import _utc, validate_pregame_snapshot
from snapshot_storage import save_snapshot


def capture_pregame_prediction(row, directory, now=None):
    """Validate and atomically save one prediction before tipoff.

    Callers provide numeric NBA IDs, a sourced line and independently
    estimated OVER probability. This does not create model probabilities.
    """
    if not isinstance(row, dict):
        raise ValueError("Prediction must be an object")
    instant = datetime.now(timezone.utc) if now is None else now
    if not isinstance(instant, datetime) or instant.tzinfo is None or instant.utcoffset() is None:
        raise ValueError("Capture clock must be timezone-aware")
    instant = instant.astimezone(timezone.utc)
    tipoff = _utc(row.get("tipoff_at"))
    if tipoff is None or instant >= tipoff:
        raise ValueError("Cannot capture at or after tipoff")
    # Ignore any user-supplied captured_at: the capture clock owns this field.
    frozen = {**row, "captured_at": instant.isoformat()}
    valid, reason = validate_pregame_snapshot(frozen)
    if not valid:
        raise ValueError(reason)
    created, path = save_snapshot(frozen, directory)
    return {"created": created, "path": str(path), "snapshot": frozen if created else None}
