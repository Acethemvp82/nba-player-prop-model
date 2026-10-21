"""Per-team player-source visibility for an incomplete NBA slate.

Counts are candidate listings, never confirmed active players.
"""


def team_source_coverage(listings, scheduled_teams):
    teams = sorted({team for team in scheduled_teams if isinstance(team, str) and team})
    output = []
    for team in teams:
        players = {}
        for row in listings:
            if not isinstance(row, dict) or row.get("team") != team:
                continue
            identifier = row.get("player_id")
            if not isinstance(identifier, (str, int)) or isinstance(identifier, bool):
                continue
            identifier = str(identifier)
            if not identifier:
                continue
            source = row.get("source") or "Unknown"
            players.setdefault(identifier, set()).add(source)
        sources = sorted({source for values in players.values() for source in values})
        output.append({
            "Team": team,
            "Listed players": len(players),
            "Data sources": ", ".join(sources) if sources else "None",
            "Status": "No listings" if not players else "Unconfirmed roster coverage",
        })
    return output
