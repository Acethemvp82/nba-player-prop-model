"""Offline end-to-end check of ESPN final summary through dashboard statistics."""
from espn_final_stats import parse_final_espn_boxscore
from espn_history import collect_espn_history
from espn_averages import espn_player_averages
from espn_trends import espn_recent_trends
from espn_history_coverage import espn_history_coverage


def final_summary(event_id, points):
    return {
        "header": {"competitions": [
            {"id": event_id, "status": {"type": {"completed": True}}}
        ]},
        "boxscore": {"players": [{
            "team": {"abbreviation": "NY"},
            "statistics": [{
                "names": ["MIN", "FG", "3PT", "REB", "AST", "PTS"],
                "athletes": [{
                    "athlete": {"id": "22", "displayName": "Sample Guard"},
                    "stats": ["33", "8-17", "3-7", "8", "6", str(points)],
                }],
            }],
        }]},
    }


def test_final_summary_flows_into_history_averages_trends_and_coverage():
    # Simulate two scoreboard dates and actual summary-shaped payloads.
    schedule = {
        "2026-10-20": [{"espnEventId": "4012", "espnCompleted": True,
                        "homeTeam": {"teamTricode": "NYK"},
                        "awayTeam": {"teamTricode": "BOS"}}],
        "2026-10-19": [{"espnEventId": "4011", "espnCompleted": True,
                        "homeTeam": {"teamTricode": "NYK"},
                        "awayTeam": {"teamTricode": "BOS"}}],
    }
    summaries = {"4012": final_summary("4012", 24),
                 "4011": final_summary("4011", 16)}
    result = collect_espn_history(
        "2026-10-21", days=2, max_games=2,
        schedule_loader=lambda day: schedule.get(day, []),
        boxscore_loader=lambda eid: parse_final_espn_boxscore(summaries[eid], eid),
    )
    assert result["failures"] == []
    assert result["games_loaded"] == 2
    assert len(result["observations"]) == 2

    averages = espn_player_averages(result["observations"], "2026-10-21")
    assert len(averages) == 1
    assert averages[0]["Player"] == "Sample Guard"
    assert averages[0]["Team"] == "NYK"
    assert averages[0]["Sample games"] == 2
    assert averages[0]["Latest verified game"] == "2026-10-20"
    assert averages[0]["Points avg"] == 20

    trends = espn_recent_trends(result["observations"], "2026-10-21")
    assert trends[("espn:22", "NYK")]["points L5 avg"] == 20
    assert trends[("espn:22", "NYK")]["Available last 5 games"] == 2

    coverage = espn_history_coverage(result["observations"], {"NYK", "BOS"})
    assert coverage[0]["Status"] == "No verified history"
    assert coverage[1]["Player-game records"] == 2
