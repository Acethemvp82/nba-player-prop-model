# NBA model core rebuild

The active model keeps the verified ESPN schedule/history, injury feed, line
connector and test infrastructure. The old team-wide 0–100 matchup formula is
retired from the active board. Legacy modules remain for comparison and tests.

## Active workflow

- One row per historical slate player. The first column is the opposing defense.
- Line and L10/L5/H2H follow the selected prop. H2H is limited to loaded history.
- Projection = median recent-five minutes × recency-weighted per-minute output
  over at most ten recent current-team games (weight 0.85^age-in-games).
  Five valid current-team appearances are required. No default betting tier.
- Defensive cells show per-game totals allowed to the source position group:
  all Guards, all Forwards, or all Centers. Explicit PG/SG map to Guard; SF/PF
  map to Forward. Broad G/F never becomes a guessed specific position.
- A defensive game requires at least eight observed players, unambiguous
  positions for every observed player, and complete numeric values for the
  relevant stat. Conflicting duplicates exclude that offense/game.
- Five screened games are required for an allowance value. Three qualified
  defenses are required for a rank. Rank 1 means most allowed; badge denominator
  is the actual number of qualified teams. Ties share competition rank. A cohort
  with no allowance variation has neutral color. These are descriptive samples,
  not pace/opponent-strength-adjusted defensive ratings.
- Stat columns and rank badges support points/rebounds/assists/threes and
  source-supplied steals/blocks. Missing stats remain unavailable.
- Out-of-sample dates compare the new minutes model against the previous blend
  on the same scored results. The comparison does not auto-select weights.

## Remaining evidence and access limits

The retrieved window can include preseason. The app does not claim confirmed
starters, precise five-position defense, full-season history, calibrated win
probabilities or expected betting value. FanDuel quote retrieval needs a provider
key configured securely in Streamlit Secrets. More results are required before
claims about predictive improvement or calibration.


## Regular-season evidence release
The active board now reads current and previous regular-season team schedules (season type 2 explicitly required), with at most 15 latest games per slate team under the retrieval cap. Current roster athlete IDs filter membership without relabeling historical teams. Roster listing does not establish active status. Unknown/preseason/postseason events are excluded by the live collector.

Five current-season same-team appearances are required for a current-season estimate. Otherwise, five previous-season same-team appearances produce only a labeled prior-season reference. The two seasons' minutes and production are not blended. Median last-five historical minutes and variability are disclosed; these do not confirm the current role. Recent L5/L10 descriptive averages may cross regular seasons. Defensive evidence season is separately selected and labeled; ranks remain sample ranks for broad G/F/C groups.

A dedicated workflow captures first pre-tip references three times daily, commits records under data/forecasts, and scores verified finals separately by evidence class against a last-five mean. It refuses started/unknown-status games. DNP/missing results are not zero. Capture timestamps are repository records, not tamper-proof sportsbook records; no hit-probability or profitability claim is made.

NBA.com cross-checks use separate NBA IDs. Local official schedule probe returned HTTP 403 and stats probe timed out; ESPN remains the functioning statistical source. No NBA.com statistical integration is claimed.

## Prospective market validation (line-gap-v1)
A separate paper ledger freezes the scheduled event/player/prop, model and reference estimates, line, both American prices, observation/source timestamp, signal eligibility, side, and model/rule version before tipoff. The first record per source/event/player/prop/version is retained. New current-season estimates require ten appearances and a last-five minutes range no greater than 12 for paper eligibility; older-season references and uncertain availability remain research-only passes. Model and last-five benchmark use the same gate; each independently chooses over, under or pass relative to the frozen line and uses that side's captured price.

One unit is risked on each simulated bet. A win earns the captured American-price profit; loss −1, push 0; ROI is net divided by total units risked including pushes. Absent/DNP or unavailable finals remain unresolved. No sportsbook-specific void/retirement rules or actual bets are assumed. Reports split quote source, evidence class, prop, model and policy versions, and show unique games/dates because multiple props are correlated. Positive sample ROI or a minimum sample count never automatically sets a "proven" badge. Formula changes require a new model/policy version and later prospective observations, rather than regrading old decisions using new rules.

Manual captures are temporary session records until the user downloads their JSON; they can be reimported for grading. Imports are always manual/unverified, even if a file claims provider provenance. SHA-256 checksums detect inconsistent records but are not signatures or proof of authenticity. Provider ledgers can persist through the scheduled GitHub workflow only when the repository variable NBA_CAPTURE_QUOTES is explicitly true and the repository secret ODDS_API_KEY exists. This opt-in can consume provider credits and defaults off; a Streamlit secret is not automatically a GitHub secret. No API key or opt-in has been configured by this change. Existing forecast-only archives cannot establish historical betting ROI.

## Current-role and prospective probability release — October 27, 2026

The baseline formula is preserved. Each forecast now carries the median minutes of up to three latest same-team current-season appearances. With three appearances, a prior-season reference compares that median with its historical model minutes; a current-season estimate requires six appearances to compare the latest three with the preceding three. A shift needs both six minutes and 20% of the reference minutes. These are observed usage checks, never confirmation of future minutes or starters.

Changed or insufficient role comparisons cannot receive a green/red directional line signal. A fresh injury-report status must also be one of Not listed/unconfirmed, Available, Active or Probable; other or conflicting statuses stay uncertain. The new `line-gap-role-v2` paper policy freezes the role and availability inputs and rechecks the stored gate. Existing v1 records retain their original decisions and remain separate. Model production/minute weights are unchanged.

A paired walk-forward report tests an explicitly experimental current-three-minutes scenario, holding production per minute constant, against the original model and its same-source last-five reference. Only the selected slate season is scored; all inputs precede each result date. The report does not select weights or change the main board.

### Experimental probability evidence

`empirical-residual-v1` may freeze an estimate only for an otherwise eligible market record and only from current-season, stable-role, ten-appearance frozen forecasts that were later matched to verified played finals. The same prop and `regular-roster-v2` model are required. Prior-season records, conflicting duplicates, same-day/future outcomes and records over 90 days old are excluded.

The engineering minimum is 100 residuals, 20 distinct games, 10 dates and 20 players. These gates prevent unsupported tiny distributions; they do not establish calibration. The method rounds target projection plus sampled residual to a nonnegative integer and adds one pseudo-observation per possible outcome: Over/Under on half lines, Over/Under/Push on whole lines. Its distribution assumptions remain experimental. No validated win probability, proven tier or EV is displayed.

New market records freeze the method version, training cutoff, sample coverage and experimental outcome probabilities when available; otherwise they freeze an explicit unavailable reason. Subsequent market results report conditional Over Brier scores excluding pushes, grouped by quote source, evidence, model, rule and method version. Positive returns, low Brier score or minimum counts never automatically promote an estimate to validated.

### FanDuel workflow

The interactive feed now requires a fresh, same-line Over/Under pair and can freeze it directly into the session paper ledger. The provider response must agree with the requested matchup and tipoff; freezing also checks the ESPN scheduled matchup/tipoff. Copying a pair fills both prices. User-entered line/odds values are scoped to player, prop and slate date. A downloaded/reimported session remains manual/unverified; only the opted-in repository workflow can preserve canonical provider ledgers. Scheduled provider spending remains disabled without the existing explicit opt-in and secure provider key.
