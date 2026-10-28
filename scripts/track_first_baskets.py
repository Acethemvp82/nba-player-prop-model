"""Build today's research board and grade saved pregame selections."""
import argparse
import sys
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from first_basket_pipeline import build_slate


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--date', default=datetime.now(ZoneInfo('America/New_York')).date().isoformat())
    parser.add_argument('--per-team', type=int, default=20)
    args = parser.parse_args()
    result = build_slate(args.date, args.per_team)
    print(f"{args.date}: {len(result['slate'])} games, {result['loaded']}/{result['requested']} historical games, {len(result['failures'])} source failures")
