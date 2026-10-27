from datetime import datetime,timezone,timedelta
from copy import deepcopy
import pytest
from schedule_recovery import recover_schedule
from forecast_tracking import capture_forecasts
from tests.test_regular_evidence import rows

NOW=datetime(2026,10,27,18,tzinfo=timezone.utc)
GAME={'espnEventId':'123','gameTimeUTC':'2026-10-27T23:00Z','espnCompleted':False,'gameStatusText':'Scheduled',
      'homeTeam':{'teamTricode':'NYK'},'awayTeam':{'teamTricode':'BOS'}}
PRIOR={'day':'2026-10-27','retrieved_at':'2026-10-27T17:00Z','games':[GAME]}


def test_cached_same_date_keeps_pairing_but_disables_capture():
    before=deepcopy(PRIOR)
    games,health=recover_schedule('2026-10-27',None,PRIOR,NOW)
    assert not health['fresh'] and games[0]['homeTeam']==GAME['homeTeam']
    assert games[0]['espnCompleted'] is None and PRIOR==before
    history={'observations':rows(),'roster_checked':True,'roster':[{'player_id':'espn:1','team':'NYK'}]}
    assert capture_forecasts(history,games,'2026-10-27',NOW)==[]


@pytest.mark.parametrize('prior',[
    PRIOR|{'day':'2026-10-26'},PRIOR|{'retrieved_at':'2026-10-25T17:00Z'},
    PRIOR|{'retrieved_at':'2026-10-27T19:00Z'},PRIOR|{'retrieved_at':'bad'},None])
def test_wrong_date_expired_future_and_missing_snapshots_never_become_slate(prior):
    games,health=recover_schedule('2026-10-27',None,prior,NOW)
    assert games is None and not health['fresh']


def test_fresh_empty_slate_overrides_old_games():
    fresh=PRIOR|{'games':[],'retrieved_at':NOW.isoformat()}
    assert recover_schedule('2026-10-27',fresh,PRIOR,NOW)[0]==[]
    assert recover_schedule('2026-10-27',fresh,PRIOR,NOW)[1]['fresh']
