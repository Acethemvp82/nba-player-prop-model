"""Streamlit entrypoint; refresh stale imported modules once per release."""
import importlib
import sys
import dashboard_v2

RELEASE = "schedule-recovery-v1"
if getattr(dashboard_v2, "BOARD_RELEASE", None) != RELEASE:
    # Long-running Streamlit processes may retain imported modules after a deploy.
    for name in ("schedule_recovery", "espn_schedule", "role_checks", "projection_core", "role_validation", "matchup_board", "prop_signal", "prospective_probability", "live_sources", "market_validation", "forecast_tracking",
                 "market_capture", "validation_panel", "defensive_table"):
        if name in sys.modules:
            importlib.reload(sys.modules[name])
    importlib.reload(dashboard_v2)

if __name__ == "__main__":
    dashboard_v2.render_dashboard()
