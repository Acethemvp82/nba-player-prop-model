"""Local append-only pregame snapshot storage.

One JSON file per unique game/player/prop/line. Atomic exclusive creation
prevents accidental overwrite. This is local persistence, NOT tamper-proof
storage; ephemeral Streamlit deployments may lose local files on restart.
"""
import json
import os
from pathlib import Path

from pregame_snapshot import snapshot_key, validate_pregame_snapshot


def save_snapshot(row, directory):
    """Persist one validated snapshot without replacing existing records.

    Returns (created, path). Duplicate keys are intentionally not overwritten.
    """
    valid, reason = validate_pregame_snapshot(row)
    if not valid:
        raise ValueError(reason)
    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    game, player, prop, line = snapshot_key(row)
    # Numeric components are validated; prop is an allowlisted token.
    line_token = float(line).hex().replace("-", "m").replace("+", "p")
    filename = f"{game}_{player}_{prop}_{line_token}.json"
    path = directory / filename
    try:
        with path.open("x", encoding="utf-8") as handle:
            json.dump(row, handle, sort_keys=True, allow_nan=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
    except FileExistsError:
        return False, path
    return True, path


def load_snapshots(directory):
    """Read stored records and report corrupt or invalid files.

    Never silently turn a corrupt file into a prediction.
    """
    directory = Path(directory)
    if not directory.exists():
        return {"snapshots": [], "invalid_files": []}
    records, invalid = [], []
    for path in sorted(directory.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                row = json.load(handle)
            valid, _ = validate_pregame_snapshot(row)
            if not valid or path.name != _expected_name(row):
                raise ValueError("invalid record or mismatched filename")
            records.append(row)
        except (ValueError, OSError, UnicodeError, TypeError):
            invalid.append(path.name)
    return {"snapshots": records, "invalid_files": invalid}


def _expected_name(row):
    game, player, prop, line = snapshot_key(row)
    return f"{game}_{player}_{prop}_{float(line).hex().replace('-', 'm').replace('+', 'p')}.json"
