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

Public app URL: https://nba-player-prop-model-khyfkxphyrocqpsqpk4vsh.streamlit.app/

Hosted inspection after milestone 1 found the old `NBA feed preview v0.2` UI,
while its source button pointed at this repository, `main`, `app.py`. The public
page did not expose owner reboot controls. Do not count this deployment as updated
until the rebuild milestone marker is visibly present.

## Rebuild milestone 2 — slate coverage

The hosted milestone-1 board was subsequently verified at the public URL with
240 baseline rows after increasing the history cap to 100. Those rows represented
only nine scheduled teams, so a populated board alone did not imply full coverage.

Milestone 2 accounts for every scheduled team before search/category filters:
observed players, players with baselines, baseline row counts, most appearances,
and the reason a team has no baseline rows. Separate downloadable short-history
averages expose players with one to four pre-slate appearances without lowering
the five-game projection minimum or assigning matchup forecasts to these rows.
Historical team membership still does not establish today's player availability.

Validation includes duplicate and future-game exclusion, latest-team assignment,
missing teams, distinct player counts across props, and Streamlit checks that
short-history averages remain separate from forecasts.

## Rebuild milestone 3 — prediction validation

The active board now runs a walk-forward evaluation against loaded verified finals.
The evaluator accepts numeric NBA IDs and namespaced ESPN IDs. Every scored
forecast trains strictly before the result date, uses five or more appearances,
and skips results whose team differs from the historical forecast's team.
The existing blend and simple last-five average are scored on identical results.

The validation table reports MAE, RMSE, signed bias, player/date counts, eligible
appearance coverage and the paired MAE difference. The audit lists each forecast,
actual result, training sample and last training date, with CSV download. These
are reconstructed historical forecasts, not independently recorded pregame snapshots.
Feed gaps, preseason inclusion and small samples still limit conclusions. This
release does not change projection weights or claim calibrated betting probabilities.

Validation tests cover ESPN IDs, identical benchmark samples, training cutoff,
team changes, malformed IDs, and the rendered Streamlit accuracy/audit tables.

## Player line research release

The deployed research workflow now includes a player/prop selector, last-ten
verified completed results strictly before the slate date, manually entered line
and optional American over odds, separate over/under/push counts, and break-even
probability from those odds. Inputs are scoped per player/prop. A minutes-only
scenario scales the baseline without changing the main board. The CSV export
records manual source provenance, recorded-at time, inputs and research outputs.
Historical overs and odds break-even are not model win probabilities.

The research board, coverage accounting, matchup context, historical validation
and manual line comparison form the current usable release. Outstanding betting
release requirements remain: authorized live sportsbook data, confirmed player
availability, sufficiently broad held-out evaluation, calibrated probabilities,
and validated opponent/minutes adjustments. No auto-generated betting tier or
expected value is supplied in their absence.

## Live source integration

ESPN's public injury feed is cached for five minutes and matched by team and
normalized full player name. Feed timestamps older than one hour remain stale,
unlisted players remain unconfirmed, and current reports are not attached to
historical slate dates. Reported Out/Doubtful players can be hidden from the main
board (default enabled). This is an injury-report flag, not confirmation of starters.

The Odds API adapter uses the documented v4 events/event-odds endpoints,
FanDuel only, and points/rebounds/assists/threes markets. A selected-matchup fetch
requires `ODDS_API_KEY` in Streamlit Secrets or the server environment. There is
no signup, payment, automatic quota polling or embedded key. Credentials are
excluded from displayed exception messages. Event date/team matching, ambiguous
quotes, stale/future timestamps, prices and already-started games are checked.
The user can copy one fresh quote into the research comparison.

Setup: obtain a key directly at https://the-odds-api.com/ and put
`ODDS_API_KEY = "your-key"` in Streamlit's app Secrets, never in GitHub or chat.
Provider access/coverage and quotas must be checked on the user's plan. No live
authenticated odds request was verified without that credential.

A validated probability feed is still not available. The 13 evaluated player
appearances and absence of independently frozen market forecasts do not support
claiming calibrated win probabilities. The app states this rather than presenting
historical hit counts or an unvalidated normal approximation as model probabilities.

## Reference-led matchup board layout

The default screen is now a dark, compact cheatsheet with one row per historical
player rather than four rows per player. Above-table controls select prop,
position (only when supplied), teams, player search, sort and availability filter.
Line/L10/L5/H2H/Proj follow the selected prop; the four stat baselines remain
side by side. H2H sample count is shown, unknown values stay blank, and sparse
players remain visible without qualifying baseline values. CSV follows filters.
The selected prop's manual comparison line appears on the board after entry.

The stat colors reflect existing **team-wide** allowance context. They are not
position-specific defensive ranks, league ranks, or hit probabilities. H2H only
covers retrieved history. Source-supplied positions are preserved from ESPN
finals; missing positions remain unknown. Cached older boxscores need a refresh
before newly added position metadata can be available.

Coverage, short-history averages and validation are below the table in a closed
expander. Player line tools remain in a separate expander. Streamlit theme settings
live in `.streamlit/config.toml`; a hosted restart may be needed for the theme.
Validation checks one-row pivoting, zero/missing handling, L10/L5/H2H cutoff and
deduplication, provider positions, and all previous Streamlit interactions.

## Core rebuild — positional defense and minutes model

The active dashboard no longer imports the retired team-wide matchup-score
engine. It uses `position_defense.py`, `projection_core.py` and the escaped HTML
renderer `defensive_table.py`. Defensive stat cells now contain allowance values,
not player forecasts; the team column is the defense. Rank badges always include
the sample denominator. Player projections and model minutes remain separate.
See MODEL_PLAN.md for exact sample gates, grouping and projection math.

History/boxscore cache schemas were bumped so old snapshots missing position,
steals or blocks fields are refreshed. Missing positions and optional stats are
never zero-filled. Tests cover projection math, future filtering, traded-player
history, conflicting duplicates, positional rank direction/ties/coverage,
HTML escaping, rank visibility, and parity of walk-forward comparison dates.
The new projection formula is a research model, not a demonstrated improvement.


Regular-roster v2: Live October 22, 2026 audit retrieved 57 verified regular-season games, no collection failures, 68 current roster entries, 152 labeled prop references for 38 players. McCain 3PM previous-season reference 0.90 at 16 historical minutes replaces the preseason-derived 3.8. First 152 pre-tip records saved before scheduled games. No scored future results exist. NBA.com schedule returned 403; stats endpoint timed out locally. Offline suite: 430 tests, including season isolation, roster exclusion, pre-tip capture, append-only records and missing/DNP handling.


Prospective market validation: fixed line-gap-v1 rules, two-sided American prices, strict pre-tip capture, source-separated cohorts and one-unit paper returns compared with a frozen last-five benchmark. Tests cover unequal Over/Under prices, wins/losses/pushes/passes, missing/DNP/finality, stale quotes, post-tip and wrong-game rejection, first-record retention, checksum corruption and a Streamlit freeze→grade flow. Provider requests remain disabled unless NBA_CAPTURE_QUOTES=true and ODDS_API_KEY is configured in GitHub; no live authenticated odds access or positive betting results are claimed. Manual session ledgers must be downloaded/imported and are unverified, not tamper-proof.

## Current-role release — October 27, 2026

Role metadata, fail-closed availability checks, the versioned `line-gap-role-v2` policy, paired current-minutes scenario evaluation, two-sided direct quote freezing and an experimental prospective probability pipeline are implemented. All numerical baseline weights remain unchanged. Legacy v1 ledgers retain their frozen rules. Historical test comparisons do not automatically replace the production formula.

The existing archive contains only prior-season scored references, which cannot fit the new probability distribution. A lack of current-season residual evidence leaves percentages unavailable. Synthetic tests exercise count/coverage thresholds, duplicate/conflict handling, pre-tip and earlier-date cutoffs, separate seasons/props, discrete pushes, checksum validation, later Brier scoring, policy compatibility and Streamlit quote freeze/download controls. Synthetic test success does not verify authenticated FanDuel access.

Release verification: 481 tests pass locally, compilation and diff checks pass. A live October 27 slate retrieval loaded 88 verified regular-season finals with zero collection failures. Current roster filtering produced 252 prop rows for 63 players; 40 prop rows (10 players) had a substantial observed minutes shift. The reconstructed current-role scenario comparison abstained because this loaded window did not provide enough strictly earlier current-season usage before the scored outcomes. No authenticated FanDuel request or calibrated probability is claimed.

## Schedule recovery and connection setup — October 27, 2026

A hosted check observed intermittent non-JSON schedule responses that replaced the board's opponent map with an empty slate despite loaded player history. The ESPN adapter now retries one transient/invalid response once, then reports failure instead of an empty slate. The UI retains only a last-successful snapshot for the same slate date and at most 24 hours. Cached event status is explicitly unverified, capture is rejected and directional availability gates remain closed until fresh retrieval succeeds. A successful empty slate replaces old games. No cross-date fallback is allowed.

Live-feed connection status is now available independently of eligible player forecasts, so missing credentials remain visible during source outages. The app never displays the configured key. Local verification: 490 tests pass, compilation and diff checks pass; a fresh live request returned the four October 27 matchups. Provider key presence alone is not proof of authorized market access or functioning live quotes.
