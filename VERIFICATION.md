# NBA model verification runbook

This dashboard is a **research preview**, not a validated betting board. Missing odds, projections, and OVER probabilities must never be represented as verified betting signals.

## Verify a GitHub revision

1. Open [NBA Model Checks](https://github.com/Acethemvp82/nba-player-prop-model/actions/workflows/model-checks.yml) in GitHub Actions.
2. Open the run for the intended commit and confirm the **validate** job finished successfully. Do not assume a commit passed merely because it was pushed.
3. Download the **nba-pytest-results** artifact and review the JUnit XML. A successful run checks compilation, pytest and module imports.
4. For a real ESPN network check, choose **Run workflow**, enable **live_espn_probe**, and run it. The separate in-season weekly scheduled check also enables the probe. Confirm the **Live ESPN completed-game probe** step passes.
5. Download **nba-espn-live-probe** and inspect `espn-live-probe.log`. A `PASS` means one recent completed ESPN game passed the summary parser, history collector, descriptive averages and recent-trends checks. It does **not** prove complete historical coverage or prediction accuracy.
6. Open the deployed Streamlit app, choose the intended slate, load ESPN completed-game stats, and inspect **ESPN retrieval health**. Note schedule failures, verified final games, request-budget truncation, latest sample date, and player coverage before interpreting historical averages.

## What a failure means

- **Pytest or import failure:** do not treat the revision as verified; inspect the failing test and correct the code.
- **Live probe failure:** ESPN might be unavailable, no recent finals may exist, or its payload may have changed. Read the diagnostic log before changing parsers or weakening validation.
- **Partial ESPN retrieval:** the sample is incomplete. Keep missing values blank, and avoid claims about full-season performance.
- **Successful live probe but incomplete app history:** a one-game smoke check is not a guarantee that all requested games can be collected.
- **No sportsbook data:** do not calculate or display fabricated betting odds or OVER probabilities.

## Release criteria for betting signals

Before enabling betting recommendations, independently confirm live historical-data collection, repeatable automated test success, a working Streamlit deployment, valid authorized sportsbook lines, out-of-sample projection calibration and backtests. Changes to projection formulas, rankings, or betting tiers require separate approval.

## Rebuild milestone 1 — baseline board and opponent context

The active `dashboard_v2.py` now loads history on first open/settings changes,
clears feed caches on manual refresh, preserves the last successful build timestamp,
and displays retrieval diagnostics. The matchup column is descriptive context,
not a projection multiplier or calibrated betting probability. It uses screened
opponent totals from strictly earlier games, a game-weighted loaded-sample reference,
five-game shrinkage and a five-game minimum. At least two qualifying opponents are
needed. Historical samples can include preseason; active rosters are not confirmed.

`python -m pytest -q` includes Streamlit AppTest checks for populated/empty/error
states, player search, sort, refresh and Eastern tipoffs, plus matchup tests for
cutoffs, duplicate rows, coverage, shrinkage and ESPN game-ID/opponent integration.
The schedule fragment checks every minute while open with a five-minute source cache.
Player baselines reload on settings changes or manual refresh; they are not in-game projections.

Deployment target remains branch `main`, entrypoint `app.py`. The dashboard identifies
itself as “Rebuild milestone 1 · Baseline + matchup context”. A successful local
Streamlit health check or GitHub push does not verify the hosted app; confirm this
marker at the deployed URL before claiming the release is live.
