"""Date-bound last-successful slate fallback; stale events cannot authorize capture."""
from datetime import datetime
from copy import deepcopy


def recover_schedule(day,fresh,prior,now,error=None):
    if isinstance(fresh,dict) and fresh.get('day')==day and isinstance(fresh.get('games'),list):
        return fresh['games'],{'fresh':True,'retrieved_at':fresh.get('retrieved_at'),'message':'Schedule source available'}
    if isinstance(prior,dict) and prior.get('day')==day and isinstance(prior.get('games'),list):
        try:
            stamp=datetime.fromisoformat(prior['retrieved_at'].replace('Z','+00:00'))
            valid=stamp.tzinfo is not None and 0<=(now-stamp).total_seconds()<=86400
        except (KeyError,TypeError,ValueError,AttributeError):valid=False
        if valid:
            games=deepcopy(prior['games'])
            for game in games:
                game.update(espnCompleted=None,gameStatusText='Cached schedule — status unverified')
            return games,{'fresh':False,'retrieved_at':prior['retrieved_at'],
                'message':'Schedule refresh failed. Showing the last successful slate from '+prior['retrieved_at']+'. Game status is unverified; pregame capture is disabled until refresh succeeds.'}
    return None,{'fresh':False,'message':'Schedule source unavailable; no saved schedule for this date. Use Build / refresh projections to retry.','error':error}
