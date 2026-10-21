"""Immutable-in-practice pregame probability snapshot validation.

Create records before tipoff and store them in an append-only external store.
This module validates shape and time ordering; it cannot prove a record was
actually captured at the declared time or prevent storage tampering.
"""
from datetime import datetime, timezone
from math import isfinite


def _utc(value):
    if not isinstance(value, str):
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None or dt.utcoffset() is None:
        return None
    return dt.astimezone(timezone.utc)


def validate_pregame_snapshot(row):
    """Return (valid, reason); require captured_at strictly before tipoff."""
    if not isinstance(row, dict):
        return False, "not_a_record"
    required = ("game_id", "player_id", "prop", "line", "over_probability",
                "captured_at", "tipoff_at", "source")
    if any(k not in row for k in required):
        return False, "missing_field"
    if not str(row["game_id"]).isdigit() or not str(row["player_id"]).isdigit():
        return False, "invalid_identifier"
    if row["prop"] not in ("points", "rebounds", "assists", "threes"):
        return False, "invalid_prop"
    line, prob = row["line"], row["over_probability"]
    if (type(line) not in (int, float) or type(prob) not in (int, float)
            or not isfinite(line) or not isfinite(prob)
            or line < 0 or not 0 <= prob <= 1):
        return False, "invalid_numeric"
    if not isinstance(row["source"], str) or not row["source"].strip():
        return False, "missing_source"
    captured, tipoff = _utc(row["captured_at"]), _utc(row["tipoff_at"])
    if captured is None or tipoff is None:
        return False, "invalid_timestamp"
    if captured >= tipoff:
        return False, "not_pregame"
    return True, "valid"


def snapshot_key(row):
    """Identify one player/prop/line/game pregame market observation."""
    valid, reason = validate_pregame_snapshot(row)
    if not valid:
        raise ValueError(reason)
    return (str(row["game_id"]), str(row["player_id"]),
            row["prop"], float(row["line"]))
