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
