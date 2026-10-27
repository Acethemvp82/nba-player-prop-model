"""Streamlit entrypoint; refresh stale imported modules once per release."""
import importlib
import sys
import dashboard_v2

RELEASE = "grading-audit-v2"
if getattr(dashboard_v2, "BOARD_RELEASE", None) != RELEASE:
    # Long-running Streamlit processes may retain imported modules after a deploy.
    for name in ("prop_signal", "live_sources", "market_validation", "forecast_tracking",
                 "market_capture", "validation_panel", "defensive_table"):
        if name in sys.modules:
            importlib.reload(sys.modules[name])
    importlib.reload(dashboard_v2)

if __name__ == "__main__":
    dashboard_v2.render_dashboard()
