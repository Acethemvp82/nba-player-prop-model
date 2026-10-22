from datetime import datetime, timezone
import pytest
from unittest.mock import patch
from live_sources import parse_injuries,reported_status,select_quote,fetch_event_odds,_odds_get
NOW = datetime(2026,10,21,20,tzinfo=timezone.utc)


def test_injury_unknown_is_not_active_and_report_age_is_checked():
    payload={'injuries':[{'injuries':[{'athlete':{'displayName':'Test Player','team':{'abbreviation':'NY'}},'status':'Out','date':'2026-10-21T19:00Z'}]}]}
    feed={'reports':parse_injuries(payload),'feed_timestamp':'2026-10-21T19:50Z'}
    assert reported_status(feed,'Test Player','NYK',NOW) == 'Out'
    assert reported_status(feed,'Another','NYK',NOW) == 'Not listed — unconfirmed'
    assert reported_status({**feed,'feed_timestamp':'2026-10-20T19:50Z'},'Test Player','NYK',NOW) == 'Report stale / unavailable'
    with pytest.raises(ValueError): parse_injuries({})


def quote():
    return {'id':'abc','commence_time':'2026-10-21T23:00Z','bookmakers':[{'key':'fanduel','markets':[{'key':'player_points','last_update':'2026-10-21T19:50Z','outcomes':[{'name':'Over','description':'Test Player','point':20.5,'price':-110}]}]}]}


def test_quotes_require_matching_player_market_freshness_and_unstarted_game():
    q=quote()
    assert select_quote(q,'Test Player','points',NOW)['line'] == 20.5
    assert select_quote(q,'Other','points',NOW) is None
    assert select_quote(q,'Test Player','rebounds',NOW) is None
    q['bookmakers'][0]['markets'][0]['last_update']='2026-10-20T19:50Z'
    assert select_quote(q,'Test Player','points',NOW) is None
    q=quote(); q['commence_time']='2026-10-21T19:00Z'
    assert select_quote(q,'Test Player','points',NOW) is None


def test_ambiguous_quotes_and_invalid_odds_are_not_selected():
    q=quote(); market=q['bookmakers'][0]['markets'][0]
    market['outcomes'].append({**market['outcomes'][0],'point':21.5})
    assert select_quote(q,'Test Player','points',NOW) is None
    market['outcomes']=market['outcomes'][:1]; market['outcomes'][0]['price']=0
    assert select_quote(q,'Test Player','points',NOW) is None


def test_api_errors_do_not_leak_keys():
    import requests
    with patch('live_sources.requests.get',side_effect=requests.RequestException('secret-api-key')):
        with pytest.raises(ValueError) as error: _odds_get('/events','secret-api-key')
    assert 'secret-api-key' not in str(error.value)


def test_event_matching_checks_slate_and_teams_before_odds_request():
    event={'id':'abc','home_team':'New York Knicks','away_team':'Boston Celtics','commence_time':'2026-10-21T23:00Z'}
    with patch('live_sources._odds_get',side_effect=[[event],quote()]) as get:
        assert fetch_event_odds('key','NYK','BOS','2026-10-21',NOW)['id']=='abc'
        assert get.call_count==2
    with patch('live_sources._odds_get',return_value=[event]) as get:
        with pytest.raises(ValueError): fetch_event_odds('key','NYK','MIA','2026-10-21',NOW)
        assert get.call_count==1
