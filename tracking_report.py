"""Read-only CLI for evaluating stored NBA pregame predictions.

Usage:
    python tracking_report.py --snapshots ./snapshots --finals ./final_players.json

The final JSON must be a list of verified final player rows using the SAME
numeric NBA game/player IDs as the saved snapshots. ESPN IDs are incompatible.
"""
import argparse
import json
import sys

from saved_tracking import evaluate_saved_snapshots


def load_final_players(path):
    with open(path, "r", encoding="utf-8") as handle:
        rows = json.load(handle)
    if not isinstance(rows, list):
        raise ValueError("Final player JSON must be a list")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("Every final player must be an object")
        for field in ("game_id", "player_id"):
            identifier = str(row.get(field) or "")
            if not identifier.isascii() or not identifier.isdigit():
                raise ValueError("Final player identifiers must be numeric NBA IDs, not ESPN IDs")
    return rows


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshots", required=True, help="Local snapshot directory")
    parser.add_argument("--finals", required=True, help="JSON file of final NBA player rows")
    parser.add_argument("--min-samples", type=int, default=30)
    args = parser.parse_args(argv)
    try:
        finals = load_final_players(args.finals)
        result = evaluate_saved_snapshots(
            args.snapshots, finals, min_samples=args.min_samples
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError) as exc:
        print(f"Tracking report unavailable: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2, sort_keys=True, allow_nan=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
