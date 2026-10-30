"""Publish a verified browser export locally before committing the data file."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from propfinder_lines import export_snapshot, stamp


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--csv', required=True, type=Path)
    parser.add_argument('--games', required=True, type=Path,
                        help='JSON list of UI-verified away/home/start records')
    parser.add_argument('--captured-at', required=True,
                        help='Actual export timestamp including timezone')
    parser.add_argument('--verified-fanduel-only', required=True, action='store_true',
                        help='Confirm FanDuel only, Over selected, alternate lines disabled')
    parser.add_argument('--output', type=Path,
                        default=Path(__file__).resolve().parents[1]/'data/propfinder-fanduel.json')
    args = parser.parse_args()
    games = json.loads(args.games.read_text())
    if not isinstance(games, list) or not games:
        parser.error('A verified non-empty game manifest is required')
    captured = stamp(args.captured_at)
    games = [g for g in games if stamp(g['start']) > captured]
    snapshot = export_snapshot(args.csv.read_bytes(), games, args.captured_at,
                               fanduel_only=args.verified_fanduel_only)
    if not snapshot['records']:
        parser.error('No supported pregame lines; existing snapshot was not replaced')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temp = args.output.with_suffix('.tmp')
    temp.write_text(json.dumps(snapshot, ensure_ascii=False, separators=(',', ':'))+'\n')
    temp.replace(args.output)
    print(f"Imported {len(snapshot['records'])} verified FanDuel prop records")


if __name__ == '__main__':
    main()
