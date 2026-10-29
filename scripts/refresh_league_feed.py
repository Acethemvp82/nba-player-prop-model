"""Refresh the data-only board and reuse already verified final boxscores."""
import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import gzip
from espn_schedule import espn_games_on
from league_feed import collect_league_feed,build_data_board


def refresh(root=Path('data'),day=None):
    day=day or datetime.now(ZoneInfo('America/New_York')).date().isoformat()
    slate=espn_games_on(day)
    if not slate:
        print('No slate today; saved feed retained.');return
    cache_path=root/'league-boxscores.json.gz'
    try: cache=json.loads(gzip.decompress(cache_path.read_bytes()).decode())
    except (OSError,ValueError): cache={}
    feed,records=collect_league_feed(day,slate,cache)
    if not feed['current_games'] or len(feed['positions'].get(str(feed['season_year']),{}))<300:
        raise ValueError('Current-season evidence or primary positions unavailable; saved feed retained')
    board=build_data_board(feed,slate)
    print(f"{len(feed['teams'])} teams; {feed['games_loaded']} verified games; {feed['current_games']} current-season games; {len(board)} roster players; {sum(r['Projected starter'] for r in board)} projected starters; {len(feed['failures'])} source issues")
    if feed['failures']:
        for error in feed['failures'][:12]: print(error)
    root.mkdir(parents=True,exist_ok=True)
    for path,value in [(cache_path,records),(root/'league-feed.json.gz',feed)]:
        temp=path.with_suffix('.tmp');temp.write_bytes(gzip.compress((json.dumps(value,separators=(',',':'),allow_nan=False)+'\n').encode(),mtime=0));temp.replace(path)


if __name__=='__main__': refresh()
