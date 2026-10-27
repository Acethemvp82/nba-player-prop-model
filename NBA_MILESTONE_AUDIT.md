# NBA milestone audit — October 27, 2026

The current board is a functioning research application. This audit does not assign a completion percentage or claim betting readiness.

## Verified in this audit

- Upstream starting revision: `81b525b5868a2c1355a42a76cb6d6b6b3df44985`.
- Existing suite: 442 passing tests. Updated suite: 465 passing tests, including grading rejection, retries, active-model residuals and saved-results UI.
- Live ESPN probe: October 26 final, event `401909868`, 21 validated player rows.
- Rebuilt 1,844 prop grades from 2,472 frozen records, using 855 played-player observations from 38 verified final games. Scored forecasts span five dates and 214 players; all belong to the prior-season-reference cohort. Missing or DNP players remain ungraded.
- Hosted app woke successfully and displayed four October 27 games, eight of eight roster teams checked, and the existing board. This initial inspection preceded the patch; a GitHub commit alone does not establish hosted deployment.
- The market ledger has no records. No prospective sportsbook ROI or calibrated OVER probability is established.

## Descriptive accuracy after final-boxscore revalidation

Each prop has 461 matched forecasts. Lower MAE is better. These correlated samples are small and describe prior-season references, not validated current-season betting signals.

| Prop | Model MAE | Frozen last-five MAE |
| --- | ---: | ---: |
| Points | 5.852 | 5.866 |
| Rebounds | 2.198 | 2.255 |
| Assists | 1.723 | 1.769 |
| Threes | 0.953 | 0.963 |

These small differences do not establish a reliable predictive or profitable advantage. No model weights were tuned to this sample.

## Corrections

1. Forecast grading now requires explicit finality, finite nonnegative values, positive valid played minutes, valid pre-tip timestamps and matching event identity when supplied. Duplicate forecasts cannot inflate counts.
2. The scheduled tracker rebuilds grades from frozen forecasts and screened final-boxscore observations. It no longer appends blindly to legacy error summaries or declares an entire game permanently finished after a partial market grade. Empty/failed final responses stay retryable.
3. Residual diagnostics now use the board's current minutes model, support ESPN event IDs, reject conflicting/preseason observations and exclude the first game after a team change. Model/evidence labels and training cutoffs are retained. Diagnostics do not enable displayed win probabilities.
4. Saved-results reporting separates model version, evidence and prop, shows unique game/date/player coverage, and compares MAE with the same frozen benchmark. Legacy grades await revalidation instead of being called verified accuracy.
5. Frozen forecast inputs and the projection formula remain unchanged. Rebuilt grades carry `grading_version: 2`, actual minutes and explicit result status.

## Next work

- Continue accumulating independently frozen current-season estimates and compare them with the benchmark by prop, player role, game and date before changing projection weights.
- Verify authorized FanDuel access with the provider key in secure app settings. The existing adapter is not evidence of a functioning live line feed. Do not enable credit-consuming scheduled quote requests without the configured opt-in.
- Freeze probabilities with real lines before tipoff, then evaluate held-out calibration and betting returns separately. Historical hit rates or the normal approximation alone cannot supply a proven OVER percentage.
- Current-season defensive cells may be blank before the five-game sample gate is met. Preserve broad G/F/C groups; do not infer unavailable PG/SG/SF/PF positions.

## Follow-up build: current-role checks and prospective estimates

The `role-checks-v1.1` release adds observed minutes-shift flags, current-role comparison diagnostics, stricter availability handling, and `line-gap-role-v2` frozen paper eligibility without changing the production projection weights. The FanDuel workflow now uses two-sided quotes with schedule/tipoff checks and supports direct session capture. Lines and odds are separated by slate date.

The experimental residual probability method freezes only after explicit current-season coverage gates; future Brier checks preserve source/model/policy/method cohorts. The current prior-season archive cannot satisfy those gates.

Validation: 481 passing tests, compilation/diff checks, and a live retrieval of 88 verified finals with zero failures. The 63 projected roster players included 10 with observed substantial minutes shifts. No candidate improvement or authenticated odds success is inferred from this check.
