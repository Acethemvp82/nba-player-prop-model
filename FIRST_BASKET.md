# First Basket Board

The first-basket system is a separate page in the existing Streamlit app. Open
the sidebar and choose **First Basket Board**, or run it independently:

```bash
python -m pip install -r requirements.txt
python -m streamlit run first_basket_app.py
```

Choose the slate date and settlement market, then press **Build / refresh**.
The first run can take several minutes. It checks every scheduled team, retrieves
current roster identities and up to the selected number of completed regular-season
games per team, and caches validated opening sequences. Failed checks are visible;
an unavailable provider is never represented as a successful empty history.

## Markets and evidence

- **First field goal:** first made two- or three-point field goal in the game.
  Free throws do not settle this selection.
- **First points:** first scoring event in the game, including a made free throw.
- Team-first baskets are supporting evidence, not the same market as game-first baskets.
- ESPN event and athlete IDs stay separate from NBA.com IDs. Scorers are resolved
  using participant IDs and boxscore identities, never name matching or a text guess.
- Historical games must be verified final, explicitly regular season, and dated
  strictly before the slate in Eastern Time. Both teams need five known actual starters.
  The opening play must start at 12:00 with a 0–0 score; opening scoring events must
  reconcile through both teams' first field goals. The last play's score must agree
  with the final summary. Later-period score corrections do not alter parsed opening events.
- Current and previous seasons may contribute, with sample counts by season shown.
  Player evidence only includes starts for the candidate's current roster team.
  Transferred history does not silently become same-team evidence.

## Ranking

At least five same-team historical starts are needed for a research score. For `n`
starts and `g` loaded team games:

```text
basket_rate = (game_first_baskets + 0.5) / (n + 5)
shot_share  = (team_opening_shots + 1.0) / (n + 5)
team_rate   = (team_first_baskets + 2.5) / (g + 5)
research_score = 100 * (0.60*basket_rate + 0.25*shot_share + 0.15*team_rate)
```

These fixed smoothing priors reduce extreme small-sample results. The weights and
score have **not** been calibrated on held-out games. The score is an ordering
index, **not** a predicted hit percentage, expected value, or proven betting edge.
Tip wins and opponent position allowances are descriptive context. No claim of
knowing a team's next opening play is made.

The top list takes at most one candidate from each game and never forces three
selections from insufficient history. Players reported Out or Doubtful are removed.
Questionable, stale, missing or uncertain injury reports remain flagged for review.
Projected lineups use the latest validated final game's starters. They are not
represented as today's confirmed starting five. A user can enter five current
roster players and the lineup source; this confirmation expires after one hour.
Incomplete coverage and builds older than one hour remain research-only in the UI.
Games that have tipped off are excluded from the live board.

## Daily collection and tracking

```bash
python scripts/track_first_baskets.py --date 2026-10-28 --per-team 20
```

The GitHub workflow `first-basket.yml` runs at 07:17, 14:17, 19:17 and 22:17 UTC
(Eastern times vary with daylight saving). The early run also grades prior dates.
Scheduling begins only after the workflow reaches the repository's default branch
and GitHub Actions is enabled. No external subscription or notification is created.

Files under `data/first-basket/` contain the reusable history, dated slate builds,
paper picks and results. The first saved selection for a game/date/market is
immutable; refreshing cannot replace it with a later candidate. Every capture must
precede tipoff. Automatic snapshots include their original availability and lineup
flags, so unconfirmed research cards are not mislabeled as confirmed bets.

There is no automatic first-basket sportsbook feed in this version. The separate
priced paper card accepts manually checked American odds and sportsbook names.
One-unit paper profit is calculated only for records with valid prices. No odds
means no ROI calculation. Nonstarters are flagged for manual settlement because
book rules differ. Missing or mismatched results remain pending or require review.

Automatic and manually priced cards are reported separately to avoid conflating
their records. GitHub workflow data persists in git. User entries saved only by a
hosted Streamlit process may be lost on restart; download the paper-record backup.
Corrupt ledgers raise errors instead of resetting pick history.

## Validation

```bash
python -m pytest -q
python -m compileall -q .
```

Tests cover different FT/FG winners, missing openings, wrong identities, unfinished
games, non-regular games, scoring gaps, duplicate sequences, no same-day leakage,
current roster filtering, insufficient history, injury exclusions, expiring lineup
confirmation, immutable pre-tip captures, market-specific grading, ROI arithmetic,
nonstarter review and Streamlit empty/populated states.

Initial live probe (October 28, 2026, ten games requested per team): all 12 slate
games found; 110 of 147 requested historical games passed validation. The 37
rejections remain visible in the dated report. That is a source-coverage check,
not a demonstrated betting win rate. Live sportsbook prices, automatic confirmed
lineups and prospective probability calibration are still future work.
