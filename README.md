# Toponymy Study — Bengaluru pilot

Interactive map of Bengaluru neighbourhood names, classified by the linguistic and semantic
origin of their suffixes. **Geometry is points** — the polygon/shapefile work is deliberately
deferred to the next phase.

## Run it

```bash
cd "04_App"
python3 -m http.server 8777
# open http://localhost:8777
```
It must be served over HTTP — opening `index.html` from the filesystem will fail, because the
browser blocks `fetch()` on `file://` URLs.

Linkable views: `?view=language|semantic` and `?theme=light|dark`.

## Rebuild the data

```bash
python3 02_Scripts/build_lexicon.py      # Suffixes.csv       -> Suffixes/Suffixes_v2.csv
python3 02_Scripts/make_palette.py       #                    -> 03_Build/palette.json
python3 02_Scripts/classify.py Bengaluru Mumbai   # -> 03_Build/data.json + audit CSVs
python3 02_Scripts/build_polygons.py Bengaluru Mumbai  # -> 03_Build/polygons_<City>.geojson
cp 03_Build/{data,lexicon,palette}.json 03_Build/polygons_*.geojson .
```

## Cities

| | points | unresolved | simplex | distinct lemmas | polygon coverage |
|---|---|---|---|---|---|
| Bengaluru | 1,036 | 3.67% | 0.00% | 67 | **27.0%** |
| Mumbai | 630 | 3.33% | 6.03% | 65 | **2.5%** |

Two structural contrasts fall straight out of this, and they are the finding, not a defect:

**Mumbai's toponymy is partly simplex.** Worli, Parel, Mahim, Colaba, Juhu, Dharavi, Powai and
about forty others are single morphemes with no productive suffix — names predating the suffixing
patterns that dominate Bengaluru. Bengaluru has **zero**. These are reported as `simplex`, a
distinct outcome from `unresolved`; forcing them under a coverage target would mean inventing
etymologies. `Suffixes/never_match.txt` is the list, and it is also what stops the matcher reading
Chembur as Dravidian `-ur` or Bandra as `-andra`.

**Mumbai has almost no boundary data.** Bengaluru reaches 27% because Karnataka publishes 2,769
revenue-village polygons and OSM carries 421 admin relations with vernacular names. Maharashtra's
equivalent village dataset contains **6 features** for Mumbai, mostly unnamed corporation
fragments, and BMC's 24 wards are lettered A/B/C with no name to match on. Mumbai is fully
urbanised, so the historic-village cadastral layer that carries Bengaluru simply does not exist.

## Results (Bengaluru, v8 rebuild)

| | before | after |
|---|---|---|
| Unclassified | 10.32% | **3.67%** |
| Distinct suffixes assigned | 31 | **67** |
| Lexicon entries | 191 rows / 183 unique | **236 entries, 201 lemmas** |

The dominant fix was not the lexicon — it was the matcher. The old pipeline matched raw character
suffixes, so the commonest Bengaluru naming pattern (initials + suffix word: *JP Nagar*, *NR Colony*,
*Sector 4*, *MS Palaya*) never matched. **706 of 1,011 matches now come from whole-word matching.**

Also fixed: 7 data-bug records removed (4 empty names, 3 from the CSV-quoting corruption).
53 builder-branded entries (*Prestige Shantiniketan*, *Sobha Ayana*, …) are **flagged, not removed** —
the inclusion decision is still open.

35–38 names remain unresolved and are genuinely opaque Old Kannada toponyms needing scholarly
sourcing: *Yelahanka, Hebbal, Peenya, Hoodi, Sarakki, Kogilu, Madiwala, Agara, Kudlu, Banashankari*.

## The lexicon — `Suffixes/Suffixes_v2.csv`

| column | purpose |
|---|---|
| `lemma` | canonical morpheme; variants collapse onto it (`nagara`→`nagar`, `alli`→`halli`) |
| `variant` | surface form as it appears in names |
| `language`, `language_family` | origin; family drives the Language view's hue |
| `colour_family` | yellow / red / blue / purple / grey |
| `semantic_category` | 11 fine categories |
| `semantic_group` | 5 groups the map colours use |
| `meaning`, `confidence` | `attested` / `probable` / `speculative` |
| **`source`** | **intentionally blank — populate as research proceeds** |
| `notes` | disambiguation, sandhi behaviour |

28 Kannada morphemes were added (`-katte`, `-kaval`, `-kunte`, `-bande`, `-hatti`, `-doddi`,
`-kallu`, `-ghatta`, `-mavu`, `-betta`, `-thota`, `-kote`, `-dinne`, …), all marked `probable` or
`speculative` pending a citation. Duplicate rows and the repeated header at line 84 are gone.

## The colour system

Both palettes were **solved and validated**, not chosen by eye. `02_Scripts/validate_palette.py`
is a Python port of the dataviz skill's Node validator (Node isn't installed here); it was
verified to reproduce the reference palette's documented figures exactly before use.

Because the map is a point form where any two marks can sit side by side, hues are gated on
**all pairs**, not just adjacent ones — a stricter test.

**Language view** — hue = language family, shade = individual suffix.
Solved as the *closest passing triple to the project's existing red/blue/yellow*, so the look
carries over. Blue drifted by ΔE 0.7, red by 2.9, gold by 10.6.

| | light | dark |
|---|---|---|
| Dravidian | `#c68200` | `#c38700` |
| Indo-Aryan | `#d84c5a` | `#df4558` |
| English | `#3379d7` | `#3485e2` |
| Perso-Arabic | `#464990` | `#795a98` |
| Unresolved | `#8a8a86` | `#7e7e7a` |

All-pairs: light CVD ΔE 8.4 / normal-vision 15.6; dark 8.1 / 15.5. Both **PASS** (targets ≥8, ≥15).

Within-family shades are an **ordinal** ramp (6 steps, monotone lightness, adjacent ΔL ≥ 0.06) —
a refinement, not a second identity channel. All 8 ramps pass. Lemma→shade is **frozen at build
time** from whole-dataset frequency, so filtering never repaints the survivors.

**Meaning view** — 5 semantic groups + grey, solved for maximum separation then re-solved for the
*lowest chroma that still passes*, so it reads muted rather than neon.
Light CVD 8.1 / NV 15.1; dark 8.3 / NV 15.0. Both **PASS**.

Why five groups and not eleven: measured, 8 and 9 categories cannot clear the all-pairs gate at any
ordering (the best 9-hue wheel reaches CVD 3.9 / NV 9.6 — far below the floor). 7 is the ceiling;
5 leaves headroom. The fine category still travels in the data, the popup, the legend's
"inside each group" breakdown, and the CSV.

## Other visual fixes

- The `charCodeAt`-sum hash colour function is gone — colours are now an explicit, documented,
  stable lookup that means the same thing across cities.
- The 31-slice doughnut is replaced by ranked bars with counts and shares, click-to-filter,
  and keyboard support.
- Light/dark honours both the OS setting and an explicit toggle, with the toggle winning both ways.
- `location.reload()` as a "back" button is gone.
- Basemap switched to `_nolabels` so place labels don't compete with the data.

## Layout

```
00_Council/     BRIEF.md (measured defects) + PLAN.md (full plan, all phases)
01_Data_Raw/    verified open boundary data for the polygon phase (not yet used)
02_Scripts/     build_lexicon.py · make_palette.py · classify.py · validate_palette.py
03_Build/       data.json · lexicon.json · palette.json · audit_Bengaluru.csv · dropped_*.csv
04_App/         the deployable site — index.html + the three json files
Suffixes/       Suffixes.csv (original, untouched) · Suffixes_v2.csv (enriched)
Cities/         source point data per city
```

`03_Build/audit_Bengaluru.csv` has one row per neighbourhood with the suffix, lemma, language,
category, confidence and **which match stage fired** — that's the file to review when checking
classification quality.

## Known limitations

- **Coverage is not accuracy.** 96.5% classified says how often the classifier fired, not how
  often it was right. Nothing here validates correctness — that needs the ~100-name stratified
  audit described in `00_Council/PLAN.md` §5c.
- 28 added suffixes carry no citation yet.
- Builder-branded entries are still counted.
- Points, not polygons. The polygon work and its selection-bias problem are in PLAN.md §1d and §2.
