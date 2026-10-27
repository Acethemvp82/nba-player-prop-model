"""Observed minutes changes; these checks never confirm starters or future minutes."""
from statistics import median

ROLE_FIELDS = ('role_status','role_note','role_recent_minutes','role_reference_minutes',
               'role_change_minutes','role_current_games','role_last_game_date')


def minutes_role(current, source_minutes, evidence):
    """current contains newest-first same-team, current-season valid appearances.

    Compare the latest three with the preceding three for current estimates.
    Prior-season references compare current minutes with their historical minutes.
    A change needs at least six minutes AND at least 20% of reference minutes.
    """
    sample=current[:3]
    recent=float(median(r['minutes'] for r in sample)) if sample else None
    reference=None
    status='insufficient_current_role'
    note='Fewer than three current-season appearances; current role is unconfirmed'
    if len(sample)==3:
        if evidence=='Prior-season reference': reference=float(source_minutes)
        elif len(current)>=6: reference=float(median(r['minutes'] for r in current[3:6]))
        if reference is None:
            note='Need six current-season appearances to compare consecutive three-game minutes samples'
        else:
            delta=recent-reference
            changed=abs(delta)>=max(6.,reference*.20)
            status='changed' if changed else 'stable'
            note=(f"Recent minutes {'up' if delta>0 else 'down'} {abs(delta):.1f}: "
                  f'{recent:.1f} latest-three median vs {reference:.1f} reference') if changed else (
                  f'No large observed minutes shift: {recent:.1f} latest-three median vs {reference:.1f} reference')
    return {'role_status':status,'role_note':note,'role_recent_minutes':recent,
            'role_reference_minutes':reference,
            'role_change_minutes':round(recent-reference,2) if reference is not None else None,
            'role_current_games':len(sample),'role_last_game_date':current[0]['game_date'] if current else None}
