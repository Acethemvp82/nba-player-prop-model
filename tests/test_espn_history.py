"""Offline tests for bounded ESPN history retrieval and final-only observations."""
from nba_data import NBADataError
from espn_history import collect_espn_history


def game(event_id):
    return {"espnEventId": event_id}


def player():
    return {"player_id": "espn:9", "player": "Example", "team": "BOS",
            "points": 22, "rebounds": 7, "assists": 4, "threes": 2,
            "source": "ESPN verified final boxscore"}


def test_history_excludes_slate_day_and_caps_requests():
    checked = []
    def schedule(day):
        checked.append(day)
        return [game("100"), game("101")]
    fetched = []
    def boxscore(event_id):
        fetched.append(event_id)
        return [player()]
    result = collect_espn_history("2026-10-21", days=3, max_games=1,
                                  schedule_loader=schedule, boxscore_loader=boxscore)
    assert checked == ["2026-10-20"]
    assert fetched == ["100"]
    assert result["games_loaded"] == 1
    assert result["dates_checked"] == 1
    assert result["observations"][0]["game_date"] == "2026-10-20"
    assert result["observations"][0]["game_id"] == "espn:100"


def test_history_reports_failed_boxscore_without_inventing_zero_stats():
    result = collect_espn_history("2026-10-21", days=1, max_games=2,
                                  schedule_loader=lambda _: [game("100"), game("101")],
                                  boxscore_loader=lambda eid: (_ for _ in ()).throw(
                                      NBADataError("not final")) if eid == "100" else [player()])
    assert result["games_requested"] == 2
    assert result["games_loaded"] == 1
    assert len(result["failures"]) == 1
    assert len(result["observations"]) == 1


def test_history_deduplicates_events_across_dates():
    result = collect_espn_history("2026-10-21", days=3, max_games=5,
                                  schedule_loader=lambda _: [game("100")],
                                  boxscore_loader=lambda _: [player()])
    assert result["games_requested"] == 1
    assert len(result["observations"]) == 1
