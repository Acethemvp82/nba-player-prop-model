"""Join validated pregame predictions to independently collected final box scores.

Research only. Snapshots must have been saved before tipoff in trustworthy storage.
No result is inferred from missing player statistics or unfinished games.
"""
from math import isfinite

from pregame_snapshot import snapshot_key, validate_pregame_snapshot


def match_final_results(snapshots, final_players):
    """Return scored records and an exclusion audit.

    Duplicate snapshots are not silently overwritten. Duplicate/conflicting
    final player records are quarantined. A push is explicitly marked.
    """
    finals = {}
    ambiguous = set()
    for row in final_players:
        if not isinstance(row, dict) or row.get("is_final") is not True:
            continue
        gid, pid = str(row.get("game_id") or ""), str(row.get("player_id") or "")
        if not gid.isdigit() or not pid.isdigit():
            continue
        key = (gid, pid)
        if key in finals:
            ambiguous.add(key)
        else:
            finals[key] = row
    seen = set()
    scored = []
    audit = {"invalid_snapshot": 0, "duplicate_snapshot": 0,
             "missing_final": 0, "ambiguous_final": 0,
             "missing_stat": 0, "matched": 0, "push": 0}
    for snapshot in snapshots:
        valid, _ = validate_pregame_snapshot(snapshot)
        if not valid:
            audit["invalid_snapshot"] += 1
            continue
        key = snapshot_key(snapshot)
        if key in seen:
            audit["duplicate_snapshot"] += 1
            continue
        seen.add(key)
        player_key = key[:2]
        if player_key in ambiguous:
            audit["ambiguous_final"] += 1
            continue
        final = finals.get(player_key)
        if final is None:
            audit["missing_final"] += 1
            continue
        actual = final.get(snapshot["prop"])
        if type(actual) not in (int, float) or not isfinite(actual) or actual < 0:
            audit["missing_stat"] += 1
            continue
        result = "push" if actual == snapshot["line"] else (
            "over" if actual > snapshot["line"] else "under")
        if result == "push":
            audit["push"] += 1
        scored.append({**snapshot, "actual": actual, "is_final": True,
                       "result": result})
        audit["matched"] += 1
    return {"scored": scored, "audit": audit}
