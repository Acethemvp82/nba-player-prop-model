# NBA Player Prop Model — implementation roadmap

## Scope
All active NBA players; points, rebounds, assists, and made threes; FanDuel-oriented over selections; a unified sortable Streamlit board.

## Build stages
1. Streamlit scaffold and clear empty-state handling.
2. NBA schedule, player directory, game logs, minutes, injury status and team context with caching and source attribution.
3. Projection engine with recency weighting, minute forecasts, opponent adjustments and statistical distributions.
4. Authorized FanDuel prop-line ingestion, timestamped and validated. Never scrape around access controls or fabricate lines.
5. Over probabilities, implied break-even probability, expected value, confidence bands and ranked master board.
6. Backtesting with out-of-sample dates, calibration metrics, and daily result tracking.

## Quality gates
No look-ahead bias; flag questionable and missing data; display odds timestamps; avoid overconfident probabilities; maintain historical evaluation.
