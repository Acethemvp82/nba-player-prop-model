"""Focused NBA board with imported-module refresh on deployment."""
import importlib
import sys

RELEASE='clean-matchup-v4'
# Streamlit may reuse imported modules when its entrypoint is rerun after deploy.
if 'matchup_dashboard' in sys.modules and getattr(sys.modules['matchup_dashboard'],'BOARD_RELEASE',None)!=RELEASE or 'defensive_table' in sys.modules and getattr(sys.modules['defensive_table'],'TABLE_RELEASE',None)!=RELEASE:
    for name in ('team_identity','matchup_csv','defensive_table','matchup_dashboard'):
        if name in sys.modules: importlib.reload(sys.modules[name])

from matchup_dashboard import render_dashboard

if __name__=='__main__':
    render_dashboard()
