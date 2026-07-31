# Version archive

One folder per published version of the site: `v<N>_<YYYYMMDD>/`.

Each holds the full runtime set — `index.html`, `data.json`, `palette.json`, `lexicon.json`.
`index.html` and `data.json` are the two that matter most; the other two are included because
an archived `index.html` will not render without them.

Cut a new version with:

```bash
python3 02_Scripts/release.py --from /path/to/04_App
```

It copies to the repo root (what GitHub Pages serves) and snapshots the same files here.

| version | date | notes |
|---|---|---|
| v7 | 2026-07-01 | Multi-city point map. Hash-based colours, 31-slice doughnut. `data.json` is an empty FeatureCollection — the polygon attempt that never got data. |
| v10 | 2026-07-31 | Adds Mumbai (630 points) with a Marathi/Konkani lexicon expansion and a city switcher. Introduces `simplex` as a distinct classification for single-morpheme names with no suffix. Mumbai polygon coverage is only 3% — Maharashtra has no revenue-village layer for the city. |
| v9 | 2026-07-31 | Adds real polygon boundaries for 27% of names (280 of 1036) across four provenance tiers; nothing derived or invented. De-duplicates 56 co-located records. Polygons render as light context, dots stay the primary mark. |
| v8 | 2026-07-31 | Bengaluru only. Token-aware classifier (unclassified 10.32% → 3.48%), enriched lexicon with `source` column, two validated colour views (language / meaning), ranked bars replace the doughnut. |
