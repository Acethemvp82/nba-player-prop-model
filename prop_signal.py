"""Transparent player-level line comparisons, not calibrated betting tiers."""
from math import isfinite
from numbers import Real


def numeric(value):
    return isinstance(value,Real) and not isinstance(value,bool) and isfinite(value) and value>=0


def prop_signal(row):
    status=str(row.get('Status','')).casefold()
    projection,line=row.get('Projection'),row.get('Line')
    if status in ('out','doubtful'):
        return 'Unavailable','red','Reported '+status
    if not numeric(projection):
        return 'No estimate','muted','Insufficient same-team regular-season evidence'
    if row.get('Evidence')!='Current season':
        return 'Research only','amber','Prior-season or unclassified estimate; current role is unconfirmed'
    if status not in ('not listed — unconfirmed','available','active','probable'):
        return 'Availability uncertain','amber','Current availability is unconfirmed: '+(status or 'missing report')
    if row.get('Role status')=='changed':
        return 'Role changed','amber',str(row.get('Role note') or 'Observed recent minutes shifted; review the current role')
    if row.get('Role status')!='stable':
        return 'Role unconfirmed','amber','Insufficient current-season minutes comparison'
    if row.get('Readiness')=='stale_history':
        return 'Old history','amber','Latest appearance is more than fourteen days old'
    if not numeric(row.get('Sample')) or row['Sample']<10:
        return 'Small sample','amber','Fewer than ten current-season observations'
    low,high=row.get('Minutes low'),row.get('Minutes high')
    if not numeric(low) or not numeric(high) or high-low>12:
        return 'Minutes uncertain','amber','Recent minutes vary or minute evidence is missing'
    if not numeric(line):
        return 'Add line','muted','Enter a sportsbook line in Player details to compare'
    gap=round(projection-line,2)
    if gap>0: return 'Above line','green',f'Estimate minus line: {gap:+.2f}; not a validated betting edge'
    if gap<0: return 'Below line','red',f'Estimate minus line: {gap:+.2f}; not a validated betting edge'
    return 'At line','amber','Estimate equals line; no projection gap'
