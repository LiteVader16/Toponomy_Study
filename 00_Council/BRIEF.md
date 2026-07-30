# Toponymy Study — Council Brief (Bengaluru Pilot)

**Project owner:** Mitali Vadher (asiwalkcities.substack.com)
**Project root:** `/Users/dilipvadher/Library/CloudStorage/GoogleDrive-mitalivadher@gmail.com/My Drive/Mac Dump 2026 Feb/Desktop/01_Toponomy Study`
**Published article:** https://asiwalkcities.substack.com/p/mapping-the-toponomy-of-indian-cities

## What exists today

An interactive Leaflet map that plots Indian city neighbourhoods as **coloured point markers**,
coloured by the **linguistic origin of the place-name suffix** (Kannada `-halli` = village,
Persian `-abad`, Sanskrit `-pur`, English `-layout`, etc.). Built with Gemini Pro assistance.
Data extracted from OpenStreetMap.

### Files
| Path | What it is |
|---|---|
| `Suffixes/Suffixes.csv` | Master lexicon. 191 rows, 183 unique suffixes. Columns: `Suffix, Language, Meaning` |
| `Cities/Bengaluru/data.json` | Live Bengaluru dataset. 1,099 neighbourhoods, point geometry |
| `Cities/Mumbai/data.json` | Mumbai dataset (same schema) |
| `Version 7_20260701/index.html` | Current app (Leaflet + Chart.js, single file, CDN deps) |
| `GitHub/index.html` | Variant that reads GeoJSON — an abandoned attempt at polygons; its `data.json` is an empty FeatureCollection |
| `Archive/data_v1..v10.json` | All empty FeatureCollections — dead ends |
| `Version 6/*.xlsx` | Per-city spreadsheets (Bengaluru, Mumbai, Hyderabad, Kochi) |

### Current data schema (`data.json`)
```json
{"cities": [{"name": "Bengaluru", "coords": [12.9716, 77.5946], "zoom": 11,
  "neighborhoods": [
    {"n": "Kodihalli", "s": "-halli", "m": "Village", "l": "Dravidian",
     "lat": 12.9628452, "lon": 77.6479018}
  ]}]}
```
`n`=name, `s`=suffix, `m`=meaning, `l`=language group, `lat`/`lon`=point.

### Current Bengaluru numbers
- 1,099 neighbourhoods, **31 distinct suffixes used** (out of 183 available in the lexicon)
- Language groups collapsed to only 5: English 447, Sanskrit 309, Dravidian 224, Other 117, Persian 2
- Top suffixes: `-layout` 216, `-nagar` 196, **`Other` 117 (10.6% unclassified)**, `-halli` 84,
  `-colony` 72, `-block` 54, `-pura` 50, `-palya` 48, `-nagara` 47, `-ur` 28, `-sandra` 25

## Verified defects (measured, not speculated)

### D1 — The classifier ignores most of its own lexicon
Only 31 of 183 lexicon suffixes are ever assigned. Re-matching the 117 `Other` names against the
**existing, unchanged** master list by longest-suffix recovers **52 of them immediately**:
`-gardens`(6) `-palaya`(6) `-agrahara`(4) `-mangala`(3) `-field`(2) `-byrathi`(2) `-aram`(2)
`-godi`(2) `-wadi`(2) `-orchard`(2) `-guppe`(2) `-block`(2) `-quarters`(2) `-palyam` `-gudi`
`-kundi` `-eri` `-mohalla` `-mahal` `-market`.
So Koramangala, Adugodi, Kalasipalyam, Banaswadi, Katriguppe, Konena Agrahara, Darga Mohalla,
Langford Gardens, MS Palaya etc. are all sitting in `Other` for no reason.

### D2 — The lexicon is missing common Kannada/Bengaluru suffixes
The 65 genuinely-unmatched names cluster into recognisable morphemes absent from the list:
`-katte` (Sunkadakatte), `-kaval`/`-kavalu` (Vyalikaval, Srigandhakavalu), `-kunte`/`-gunte`/`-gunta`
(Konanakunte, Bagalagunte, Doddigunta, Yellukunte), `-bande` (LR Bande, Byrathi Bande),
`-hatti` (Gollarahatti), `-doddi` (Javaranadoddi), `-kallu` (Doddabidarakallu), `-ghatta`
(Challaghatta), `-mavu` (Hulimavu, Horamavu), `-madu` (Ittamadu), `-vara` (Nagavara),
`-alli` (Doddakannalli — a `-halli` sandhi variant), `-hal`/`-bal` (Hebbal), `-ala`/`-gala` (Malagala).

### D3 — Variant/lemma collapse is missing
`-nagar`(196) and `-nagara`(47) are the same morpheme. So are `-pura`(50)/`-puram`(15)/`-pore`(1),
`-pet`(3)/`-pete`(8), `-palya`(48)/`-palaya`/`-palyam`, `-ur`(28)/`-uru`(10).
`-sandra`(25) and `-andra`(3) are both mis-segmentations of *samudra* (tank/lake).
This fragments the statistics and the legend.

### D4 — OSM noise is being counted as toponymy
The dataset includes gated apartment complexes and commercial estates as "neighbourhoods":
*Prestige Shantiniketan, Sobha Ayana, Rainbow Residency, Sunny Brooks, Ferns Habitat, Bestcounty2,
Brooke Bond, Karishma Hills, Mount Joy, Palm Grove*. Also present: **3 empty-string names**, a
CSV-quoting bug producing the literal record `""AECS Layout"," A block""`, and "Varanasi"
(likely a spurious OSM node).

### D5 — Duplicate / contradictory lexicon rows
`godi` appears twice (both Kannada); `wara` appears under both Marathi and Rajasthani; `dam`
appears twice under Malayalam with different meanings; `pada` under both Marathi and Sanskrit;
`ur` under both Kannada and Malayalam; `cheri`/`Cheri` differ only in case. The header row
`Suffix,Language,Meaning` is repeated mid-file at line 84. ~20 rows have Meaning = "Unknown".

### D6 — Language taxonomy is lossy and geographically wrong
The lexicon records real languages (Kannada, Tamil, Telugu, Malayalam, Marathi, Konkani, Gujarati,
Persian, Urdu, Sanskrit…) but `data.json` collapses them into 5 buckets, mapping all four Dravidian
languages to one "Dravidian" colour and lumping Hindi/Marathi/Gujarati under "Sanskrit". For a
Bengaluru map this erases the thing most worth showing — the Kannada substrate versus the
Sanskritic and English overlays.

### D7 — Colour is assigned by character-code hash
`getColor()` sums `charCodeAt` over the suffix and takes it modulo a 5-colour palette. Colours are
therefore arbitrary, unstable across cities, and collide. Palettes are not colour-blind safe.

### D8 — Points misrepresent neighbourhoods
A neighbourhood is an area. Rendering it as a fixed 6px circle means a 12 km² area and a single
apartment block look identical, and no spatial pattern (clustering of `-halli` on the periphery vs
`-nagar` in the planned core) can be read off the map.

## What the owner wants

1. **Most comprehensive suffix lexicon possible** — fix D1, D2, D3, D5, D6.
2. **Visual fixes** — D7 and general cartographic quality.
3. **Neighbourhoods as polygons (shapefiles), not points** — D8.
4. **Bengaluru as the pilot.** Other cities integrate in Phase 3.

## Environment constraints (verified)

- macOS, `python3` = **3.9.6 system Python**. Installed: `pandas`, `openpyxl`. **Nothing else.**
- **Missing:** geopandas, shapely, fiona, pyproj, osmnx, requests, folium, matplotlib
- **Missing CLI:** node, npm, gh, ogr2ogr/GDAL, osmium, tippecanoe, duckdb
- `git` is present. Project directory is **not** a git repo and lives on **Google Drive File Stream**
  (syncing; beware of large binary churn and of `.DS_Store` / `~$*.xlsx` lock files).
- Assume any install must be requested and justified; prefer few, well-chosen dependencies.
