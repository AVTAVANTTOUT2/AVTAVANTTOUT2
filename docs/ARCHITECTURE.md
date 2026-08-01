# Architecture — animated GitHub profile art

## Decision: push motion into committed SVGs

GitHub sanitizes README HTML (no `<script>`, almost no inline CSS) but renders
SVGs referenced via `<img>` and runs their SMIL / CSS-keyframe animations.
Therefore every animation lives inside a self-contained SVG; the README only
places images.

## Decision: scrape public contributions HTML (no token)

The GraphQL API needs a PAT. The profile calendar fragment at
`/users/<user>/contributions` is public HTML. Scraping it with `requests` +
BeautifulSoup keeps the daily workflow secret-free and matches what the
profile page itself uses.

## Decision: split static art from daily refresh

- `avi-ascii.svg` / `info-card.svg` change only when photo or bio changes.
- `contrib-heatmap.svg` + `data/contributions.json` refresh on a cron.

The Actions workflow installs only `requirements-ci.txt` so portrait deps
(`rembg`, OpenCV) never run in CI.

## Decision: environment-variable configuration

Username, display name, info-card copy, timeouts, and animation knobs are all
overridable via env vars (`GH_PROFILE_*`, `STATIC`, etc.) with safe defaults
for `AVIVASHISHTA29`.

## Module graph

```
prep_photo.py        -> source-prepped.png
make_ascii_svg.py    -> avi-ascii.svg
make_info_card.py    -> info-card.svg
fetch_contributions.py -> data/contributions.json
render_heatmap_svg.py  -> contrib-heatmap.svg
README.md embeds the three SVGs
```

No circular imports. Shared knobs live in `scripts/config.py`.
