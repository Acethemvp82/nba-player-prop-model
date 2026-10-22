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
