# NBA player prop simulator

On the live board, check **Open 10,000-run prop simulator** above the matchup table.
Choose a player, Points/Rebounds/Assists/Threes, 5/10/15 recent games and enter a
current whole or half-point line. Press **Run 10,000 simulations**. A valid,
matching board line can optionally be used when available; expired or started
snapshot lines are never offered. The scheduled PropFinder refresh stays paused.

Each draw uniformly resamples one verified completed regular-season appearance
for the player's current team before the selected slate date. DNPs, invalid stats,
conflicting duplicate games, other teams and future games are excluded. At least
five appearances are required. The UI reports incomplete windows and old history,
and exposes dates, opponents, minutes and totals for every sampled game.

Over/under/push use strict greater/less/equal comparison to the supplied line;
pushes remain separate. The fixed random seed makes repeated runs reproducible.
Results persist through reruns only while the player, stat, date, line, history
and window are unchanged. Results have no effect on table rankings or hammers.

This is an empirical Monte Carlo research baseline, not a calibrated predictive
model. Its frequencies approximate the selected sample's hit rates. It assumes
past appearances are equally representative, does not adjust for opponent,
minutes, injuries, pace or role, and cannot generate totals outside the sample.
The middle 80% interval describes resampled outcomes, not future uncertainty.
10,000 draws do not provide 10,000 independent real games or establish an edge.
It requires prospective evaluation before predictive claims can be made.
