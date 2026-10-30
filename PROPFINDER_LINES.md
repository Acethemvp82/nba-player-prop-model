# FanDuel line snapshots

The live board reads `data/propfinder-fanduel.json`. NBA averages and defensive data still come from the existing NBA pipeline. Lines and historical over counts come from a PropFinder research export captured with only FanDuel enabled and alternate lines disabled. No login information, saved props, or account identifiers are stored in the repository.

This is an export snapshot, not an automatic sportsbook connection. The app displays the capture time. A new browser export must be published to refresh it; the NBA refresh workflow does not refresh these lines.

To publish another snapshot:

1. In the signed-in research UI, verify FanDuel is the only enabled sportsbook and alternate lines are off.
2. Check the Games selector for actual dates, teams and tipoffs. Limit the selection to the desired slate. Export the research CSV with Over selected.
3. Pass the CSV bytes, explicit verified game manifest (`away`, `home`, timezone-aware `start`), actual export timestamp, and `fanduel_only=True` to `propfinder_lines.export_snapshot`. Save its returned JSON to the data path above. The CSV itself omits book and game identity, so never assign those automatically without verified UI context.
4. Run the tests and publish the updated data file. Verify the live board on the corresponding date and stat.

The importer accepts full-game points, rebounds, assists, three-pointers, steals and blocks only. Duplicate conflicting lines, wrong matchups, unsupported markets, malformed counts, and missing data are excluded. The runtime removes lines after tipoff or after 24 hours, and never carries a line to another date or stat. Exported over counts are descriptive history at that line, not model probabilities; under counts are not inferred because push counts are absent.

## Scheduled refresh handoff

A ChatGPT task can perform the signed-in browser export and publish a new snapshot. This depends on browser access and an active PropFinder session; if sign-in expires or a download fails, it must report the blocker and leave existing data untouched. It must not store or transfer login credentials into GitHub or Streamlit. The task should fetch this repository's current files instead of depending on a previous scratch directory.

Use `python scripts/import_propfinder_lines.py --csv EXPORT.csv --games VERIFIED_GAMES.json --captured-at TIMESTAMP --verified-fanduel-only` after verifying the UI settings, selected games and timestamp. The game manifest is a JSON list of `away`, `home`, `start` (timezone-aware ISO timestamp) objects observed in PropFinder's Games selector. Cross-check against the current NBA schedule; skip ambiguous games. The script excludes already-started games and refuses to overwrite a snapshot with no supported records. Commit only `data/propfinder-fanduel.json` after validation. Preserve automated stats/tracker changes by fetching the current branch head before publishing.
