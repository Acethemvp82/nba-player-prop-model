# FanDuel line snapshots

The live board reads `data/propfinder-fanduel.json`. NBA averages and defensive data still come from the existing NBA pipeline. Lines and historical over counts come from a PropFinder research export captured with only FanDuel enabled and alternate lines disabled. No login information, saved props, or account identifiers are stored in the repository.

This is an export snapshot, not an automatic sportsbook connection. The app displays the capture time. A new browser export must be published to refresh it; the NBA refresh workflow does not refresh these lines.

To publish another snapshot:

1. In the signed-in research UI, verify FanDuel is the only enabled sportsbook and alternate lines are off.
2. Check the Games selector for actual dates, teams and tipoffs. Limit the selection to the desired slate. Export the research CSV with Over selected.
3. Pass the CSV bytes, explicit verified game manifest (`away`, `home`, timezone-aware `start`), actual export timestamp, and `fanduel_only=True` to `propfinder_lines.export_snapshot`. Save its returned JSON to the data path above. The CSV itself omits book and game identity, so never assign those automatically without verified UI context.
4. Run the tests and publish the updated data file. Verify the live board on the corresponding date and stat.

The importer accepts full-game points, rebounds, assists, three-pointers, steals and blocks only. Duplicate conflicting lines, wrong matchups, unsupported markets, malformed counts, and missing data are excluded. The runtime removes lines after tipoff or after 24 hours, and never carries a line to another date or stat. Exported over counts are descriptive history at that line, not model probabilities; under counts are not inferred because push counts are absent.
