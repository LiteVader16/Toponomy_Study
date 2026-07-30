# Bengaluru Pilot — Plan
**Toponymy of Indian Cities · Phase 1 (Bengaluru) → Phase 3 (multi-city)**
Companion to `BRIEF.md`, which records the measured defects. Everything below is grounded in
numbers actually pulled from the project files and the live Overpass API, not estimates.

---

## 0. The finding that reframes the project

**Every GeoJSON file in this project has zero features.**
`Archive/data_v10.json`, `Version 7_20260701/data.json`, `GitHub/data.json` — all
`{"type":"FeatureCollection","features":[]}`. The v2.0 documentation describes polygon rendering,
and `GitHub/index.html` really does contain working `L.geoJSON` code. The sample polygon in that
documentation is a hand-typed rectangle with five round coordinates — a placeholder, not data.

So the polygon migration has been attempted at least three times and failed at the same step every
time: **not the rendering, the data acquisition.** The documentation's own "Workflow for Non-Coders"
says step 1 is "Download or create neighborhood shapefiles using free GIS resources or municipal
portals" — that one line is the entire hard problem, and it has never actually been completed.

This plan therefore front-loads data acquisition and treats the frontend as the easy part. Do not
start by rewriting `index.html`.

---

## 1. What polygon data actually exists for Bengaluru — measured

Queried live against Overpass on 2026-07-29.

### 1a. Place features (the current data source)
| OSM type | Count | Share |
|---|---|---|
| `node` (point only) | 1,091 | 91.2% |
| `way` (polygon) | 58 | 4.8% |
| `relation` (polygon) | 47 | 3.9% |
| **Total `place=*`** | **1,196** | |

Only **8.8%** of Bengaluru place features carry polygon geometry. Tag breakdown:
`neighbourhood` 843, `quarter` 208, `suburb` 88, `locality` 33, `village` 23, `hamlet` 1.

### 1b. Administrative boundaries — the source that was never tried
| admin_level | Count | What it is |
|---|---|---|
| 4 | 1 | Karnataka |
| 5 | 2 | Bengaluru Urban, Bengaluru North |
| 6 | 6 | Taluks (Bangalore North/East/South, Yelahanka, Anekal, Hosakote) |
| 7 | 1 | Bengaluru |
| 8 | 5 | The five new City Corporations (post-2024 Greater Bengaluru restructure) |
| **9** | **51** | **Revenue villages** |
| **10** | **369** | **Wards** |
| 11 | 1 | Defence Colony |

Level 9 names are exactly the historic village stratum the project cares about: *Ramasandra,
Challagatta, Kommagatta, Doddabele, Kengeri Gollarahalli, Ramagondanahalli, Avalahalli,
Muddhanahalli, Gantiganahalli, Hunasamaranahalli.* Level 10 ward names are largely vernacular too
(*Doddabommasandra, Thanisandra, Hegganahalli, Kalkere, Jakkur*), though some are commemorative
(*Da.Ra. Bendre Ward, Jaya Chamarajendra Nagara*) — ward naming is not identical to neighbourhood
naming and this must be stated, not smoothed over.

**Total polygon-capable named features: 524** (421 admin L9/10/11 + 103 named place polygons).

### 1c. Match rate against the existing 1,095 named neighbourhoods
| Outcome | Count | Share |
|---|---|---|
| Exact normalised name match to a polygon | 326 | 29.8% |
| Additional fuzzy/containment match | 118 | 10.8% |
| **No polygon available by name** | **651** | **59.5%** |

### 1d. ⚠ The selection bias — the most important number in this document

Polygon availability is **not uniform across suffixes**:

| Suffix | Has real polygon | Suffix | Has real polygon |
|---|---|---|---|
| `-sector` | **92.0%** | `-nagar` | 32.7% |
| `-sandra` | **56.0%** | `-ur` | 28.6% |
| `-halli` | **48.8%** | `-stage` | 20.0% |
| `-block` | 44.4% | `-palya` | 18.8% |
| `-pura` | 40.0% | `-colony` | 18.1% |
| `-nagara` | 10.6% | `-layout` | **15.3%** |
| | | `-garden` | **5.9%** |

Historic village names survive as revenue villages and ward names, so they are **~3× more likely to
have a real boundary** than modern private layouts. `-halli` 48.8% vs `-layout` 15.3%.

**Consequence:** a map that renders "polygons where they exist" would silently inflate the historic
Kannada stratum threefold against the modern planned stratum — an artefact that points directly at
the article's headline claim. Any polygon strategy must either achieve complete coverage or
disclose this bias prominently. This is the single strongest argument against the tempting
"just use what OSM has" shortcut.

---

## 2. Geometry strategy — the central decision

Three coherent options. They are genuinely different products, not degrees of effort.

### Option A — Ward choropleth
Map the 369 ward polygons + 51 revenue villages; classify each by *its own* name's suffix.
- ✅ Complete, honest, real boundaries. No fabricated geometry. Ships fastest.
- ✅ Revenue villages give a clean historic layer.
- ❌ Wards ≠ neighbourhoods. Loses ~700 vernacular names including most `-layout`/`-colony`.
- ❌ Commemorative ward renaming injects its own bias.

### Option B — Per-neighbourhood polygons, Voronoi-filled
Keep all 1,095 names. Real polygon for the 40% that have one; Thiessen/Voronoi cells clipped to the
city boundary for the other 60%.
- ✅ Preserves the full vernacular name set and complete coverage — kills the §1d bias.
- ❌ 60% of the map is fabricated geometry. Voronoi cells in sparsely-named peripheries become
  enormous, which re-introduces area bias in a new form.
- ❌ Cartographically dishonest unless the derived cells are visually marked as derived.

### Option C — Tiered hybrid *(recommended)*
Every feature carries a `geom_source` provenance tier:
1. `osm_place_polygon` — true mapped boundary (103)
2. `admin_ward` / `admin_village` — administrative polygon matched by name (~421)
3. `voronoi_derived` — Thiessen cell, clipped to the BBMP/GBA boundary and to its parent ward
4. `point_only` — no polygon; rendered as a dot, never as an area

Render tiers 1–2 with solid fill and crisp edges, tier 3 with soft/hatched edges at lower opacity,
tier 4 as centroid dots. The map then shows its own confidence, and every statistic can be
recomputed tier-by-tier to prove the headline finding is not an artefact of coverage.
- ✅ Complete coverage *and* honest about provenance. Directly answers §1d.
- ❌ Most work. Needs a real visual language for uncertainty (§4).

**Recommendation: C, with A shipped first as an intermediate deliverable.** Option A is a genuine
publishable map on its own and requires no fabricated geometry — it de-risks the whole project. Then
layer B's coverage on top to reach C.

---

## 3. Lexicon and classification

### 3a. Fix the classifier before touching the lexicon
Only 31 of the 183 available suffixes are ever assigned. Re-matching the 117 `Other` names against
the **existing, unchanged** list by longest-suffix immediately recovers **52 of them**
(`-gardens` 6, `-palaya` 6, `-agrahara` 4, `-mangala` 3, `-godi`, `-wadi`, `-guppe`, `-orchard`,
`-quarters`, `-mohalla`, `-palyam`, `-kundi`, `-eri`, `-mahal`, `-market` …). Koramangala, Adugodi,
Kalasipalyam, Banaswadi, Katriguppe, Konena Agrahara, Darga Mohalla and MS Palaya are all sitting in
`Other` for no reason at all. **This is the highest-value hour in the project** — it is a bug fix,
not research, and it cuts unclassified from 10.6% to ~5.9% before any new research happens.

### 3b. Then expand the lexicon
The 65 genuinely-unmatched names cluster into real Kannada morphemes absent from the list:
`-katte` (Sunkadakatte), `-kaval`/`-kavalu` (Vyalikaval, Srigandhakavalu), `-kunte`/`-gunte`/`-gunta`
(Konanakunte, Bagalagunte, Doddigunta, Yellukunte), `-bande` (LR Bande, Byrathi Bande), `-hatti`
(Gollarahatti), `-doddi` (Javaranadoddi), `-kallu` (Doddabidarakallu), `-ghatta` (Challaghatta),
`-mavu` (Hulimavu, Horamavu), `-madu` (Ittamadu), `-vara` (Nagavara), `-alli` (Doddakannalli — a
`-halli` sandhi variant), `-hal`/`-bal` (Hebbal), `-ala`/`-gala` (Malagala).

Source these properly — Epigraphia Carnatica, B.L. Rice, Karnataka gazetteers, published Kannada
toponymy scholarship — and record a citation per suffix. Mark each addition well-attested vs
speculative.

### 3c. Revised lexicon schema
Replace `Suffix, Language, Meaning` with:

| Column | Why |
|---|---|
| `lemma` | Canonical morpheme — `halli` |
| `variant` | Surface form — `halli`, `alli`, `ahalli` |
| `script_native` | ಹಳ್ಳಿ — needed for credibility and for bilingual labels |
| `lang_origin` / `lang_borrowing` | Persian `-abad` enters via Urdu; these differ |
| `semantic_category` | Drives map colour (§3d) |
| `meaning_short` / `meaning_long` | Legend vs popup |
| `period` | Old Kannada / medieval / colonial / post-1947 |
| `confidence` | attested / probable / speculative |
| `source_citation` | Required for anything published as research |
| `notes` | Disambiguation, sandhi behaviour, false-positive traps |
| `min_stem_len` | Guards against matching `-ur` inside short names |

### 3d. Colour by semantic category, not language
Proposed categories: **settlement type** (halli, ur, pura, gaon) · **hydrology** (kere, sandra, katte,
kunte) · **topography** (giri, betta, bande, gudda) · **flora/agriculture** (mavu, thota, kadu) ·
**administrative/planned** (layout, sector, block, stage, phase) · **commemorative/institutional**
(nagar after a person, PSU townships) · **commercial** (pete, bazaar, ganj, market) ·
**religious/sacred** (agrahara, gudi, matha).

For a Bengaluru readership this is strictly more informative than language alone, because it makes
the actual historical argument legible: a hydrological substrate (`-kere`, `-sandra`, `-katte` — the
tank system) overlaid by an administrative-planned stratum (`-layout`, `-block`, `-stage`). Colouring
by language cannot show that; it just says "Kannada" for both `-kere` and `-halli`. Keep language as
a **secondary encoding** (a filter, and a toggleable second view) rather than the primary hue.

### 3e. Variant collapse
`-nagar`(196) + `-nagara`(47) are one morpheme. So are `-pura`/`-puram`/`-pore`, `-pet`/`-pete`,
`-palya`/`-palaya`/`-palyam`, `-ur`/`-uru`. `-sandra`(25) and `-andra`(3) are both mis-segmentations
of *samudra*. Report at lemma level; keep variant in the data.

### 3f. Lexicon hygiene
Remove the repeated header row at line 84. Deduplicate `godi` (twice), `wara` (Marathi/Rajasthani),
`dam` (twice, Malayalam), `pada` (Marathi/Sanskrit), `ur` (Kannada/Malayalam), `cheri`/`Cheri`.
Resolve the ~20 rows with Meaning = "Unknown" or drop them with a note. Normalise case throughout.

---

## 4. Visual design

### 4a. Kill the hash-based colour function
```js
for (let i=0;i<suffix.length;i++) hash += suffix.charCodeAt(i);
return palette[hash % palette.length];
```
Colours are arbitrary, collide, and change meaning between cities. Replace with an **explicit lookup
table** keyed on `semantic_category` → hue, with lightness steps distinguishing lemmas inside a
category. Fixed, documented, colour-blind-checked, stable across all cities.

### 4b. Polygon cartography
- Fill ~0.55 opacity over a desaturated basemap; stroke in a darker value of the same hue.
- **Area bias is real and must be managed** — peripheral revenue villages are physically large and
  will dominate the visual field. Pair every area statistic with a count statistic, and consider a
  centroid-dot overlay so small dense central neighbourhoods remain visible.
- Provenance tiers get distinct edge treatment: solid (real) / dashed or hatched (Voronoi) /
  dot only (point-only).

### 4c. Charts
Drop the 31-slice doughnut — it is unreadable at that cardinality. Replace with:
1. Ranked horizontal bars grouped by semantic category.
2. **A distance-from-centre plot** — suffix share binned by km from the historic core. This would
   directly visualise the historic-village → planned-layout gradient and is, on the evidence in
   §1d, the most interesting finding this dataset can support.
3. A coverage/provenance panel so readers can see how much geometry is derived.

### 4d. Other fixes
`location.reload()` for "Back to India Map"; three empty-string names rendering as blank popups; the
literal corrupted record `""AECS Layout"," A block""` from a CSV-quoting bug; permanent tooltips
that collide at low zoom.

---

## 5. Methodology and validity

### 5a. Inclusion protocol — decide by rule, not case by case
The dataset currently counts gated apartment complexes as neighbourhoods: *Prestige Shantiniketan,
Sobha Ayana, Rainbow Residency, Sunny Brooks, Ferns Habitat, Bestcounty2, Brooke Bond, Karishma
Hills, Mount Joy, Palm Grove*, plus *ITI Industrial Estate*, *EPIP Zone*, *Commercial Street Market*,
*Arab Lines*, a spurious *Varanasi*, and 3 empty names.

Write explicit rules covering: private/gated developments, industrial estates, commercial districts,
defunct historical names, and OSM entries with no independent attestation. A builder-branded
apartment complex is a marketing name, not a toponym — but the rule must say so in advance, because
excluding them case-by-case after seeing the results is p-hacking.

### 5b. Threats to validity to state publicly
- **Coverage bias (§1d)** — quantified, directional, and cuts against the headline finding. Must be
  disclosed with the numbers.
- **OSM completeness bias** — informal and peripheral settlements are plausibly under-mapped
  relative to affluent planned layouts. Direction unknown; test it.
- **The denominator problem** — "8.5% of neighbourhoods are `-halli`" is a share of *mapped features*,
  not of area, and certainly not of population. State which denominator every figure uses.
- **Classification circularity** — expanding the lexicon until everything matches raises coverage
  without adding truth. Guard with §5c.
- **Renaming and survivorship** — official renaming, Bangalore↔Bengaluru, `-pete` areas renamed.

### 5c. Validation
Draw a **stratified random sample of ~100 classified names** (stratified by suffix frequency and by
provenance tier), verify each against an independent source, and publish the accuracy rate with a
confidence interval. Without this the coverage number is unfalsifiable. Report accuracy alongside
coverage everywhere — coverage without accuracy is the metric that got the project here.

### 5d. Ethics
Karnataka language politics, renaming campaigns, and caste-associated toponyms (`-agrahara`,
`-palya`, `-hatti` and similar carry caste-settlement history) are live and sensitive. Report
etymology descriptively, cite sources, and avoid framing any naming stratum as more authentic than
another. Decide deliberately how — or whether — to surface caste-associated categories.

---

## 6. Engineering

### 6a. Environment (verified)
Python **3.9.6** system Python. Installed: `pandas`, `openpyxl`. Nothing else. No node/npm, no gh,
no GDAL/ogr2ogr, no osmium, no duckdb, no geopandas/shapely.

Minimum viable install: `shapely` (polygon ops, Voronoi, clipping) and `pyproj` (equal-area CRS for
honest area stats). `geopandas` is convenient but heavy — Shapely + the stdlib `json` is sufficient
and keeps the pipeline debuggable. **Use a venv**; do not install into system Python 3.9.

### 6b. Output formats
The owner said "shapefiles". Shapefile is a poor fit — binary, multi-file, 10-char field-name limit,
no UTF-8 guarantee (fatal for Kannada script). Recommend **GeoJSON for the web** and **GeoPackage for
archival/QGIS**, and offer a Shapefile export only if a collaborator specifically demands it.
Estimated web payload for ~1,100 simplified polygons: 1.5–3 MB, → ~400–800 KB with coordinate
rounding to 5 decimals and property-name compression. Acceptable for a single GeoJSON on GitHub
Pages; revisit vector tiles only in Phase 3.

### 6c. Repository hygiene
The project has `Version 6/`, `Version 7_20260701/`, `GitHub/`, `Cities/`, ten archived JSONs (all
empty), `.DS_Store`, and `~$*.xlsx` Office lock files. Move to a git repo with a real structure
(`data/raw`, `data/interim`, `data/final`, `src/`, `web/`, `docs/`) and a `.gitignore`.

⚠ **The project lives on Google Drive File Stream.** Git repos on Drive sync are a known source of
`.git` corruption and sync conflicts. Recommend the working repo live in a local path
(`~/Projects/toponymy`) with GitHub as the backup, and Drive used only for source documents.

### 6d. Pipeline
Reproducible, cached, re-runnable:
```
01_fetch_osm.py      → data/raw/osm_bengaluru.json     (Overpass, cached)
02_clean_names.py    → applies §5a inclusion rules, logs every exclusion
03_classify.py       → longest-lemma match + sandhi rules → suffix, category
04_geometry.py       → tier assignment, name matching, Voronoi, clipping
05_export.py         → web GeoJSON + GeoPackage + CSV
06_validate.py       → schema, geometry validity, coverage floor, golden-file diff
```
`06` should **fail the build** if unclassified exceeds a threshold or if classifications change for
more than N features without an explicit lexicon-version bump. That single guard prevents the silent
regressions that produced ten empty archive files.

---

## 7. Sequencing

### Phase 1 — Bengaluru pilot
**Stage 1 · Fix what is already broken (highest value per hour, no new research)**
1. Re-run classification against the *full existing* 183-suffix lexicon → recovers 52 names (§3a)
2. Apply the inclusion protocol; purge apartment complexes, empty names, the CSV-quoting bug
3. Collapse variants to lemmas
→ *Deliverable: a corrected point map with unclassified down from 10.6% to ~6%. Publishable alone.*

**Stage 2 · Lexicon**
4. Research and add the ~16 missing Kannada morphemes with citations (§3b)
5. Migrate to the new schema with semantic categories (§3c–3d)
6. Lexicon hygiene (§3f)

**Stage 3 · Geometry — the hard part**
7. Pull admin L9/L10 polygons; ship **Option A** (ward + revenue-village choropleth)
8. Name-match place polygons; build the tier model
9. Voronoi for the remainder; clip to city and parent ward → **Option C**

**Stage 4 · Visual rebuild**
10. Explicit colour system; polygon cartography; provenance visual language
11. Replace the doughnut; build the distance-from-centre plot

**Stage 5 · Methodology & validation**
12. 100-name stratified audit with published accuracy (§5c)
13. Public methodology document — the one already promised to readers

### Phase 2 — consolidate
Repo restructure, pipeline scripts, validation gates, GitHub Pages deploy.

### Phase 3 — multi-city
Archives already hold point data for **11 cities**: Bengaluru 1,099 · Jaipur 1,484 · Hyderabad 1,033 ·
Pune 865 · Delhi 680 · Mumbai 650 · Chennai 439 · Ahmedabad 188 · Kochi 107 · Kolkata 111 ·
Lucknow 91. Per city the pipeline is identical; what changes is the lexicon subset, the admin-level
mapping (every state numbers wards differently — this will be the recurring cost), and the city
boundary.

---

## 7b. ADDENDUM (2026-07-29) — verified open polygon sources, and why not Google

### Google Maps boundaries: not usable
The red outline Google draws around a neighbourhood cannot be used as a source here, for three
independent reasons, any one of which is disqualifying:
1. **No API exposes it.** Google Places API returns a `viewport` — a rectangular bounding box — not
   the outline. The red boundary is rendered inside Google's own vector tiles and is not published
   as geometry. There is no legitimate endpoint to call.
2. **The Maps Platform terms prohibit it.** Extracting, scraping or caching Maps content to build a
   derivative dataset is barred, and re-publishing it as downloadable GeoJSON/Shapefile is squarely
   what the terms exclude.
3. **Licence contamination — the one that actually bites this project.** The dataset is OSM-derived
   and is published with a CSV/GeoJSON download button. Mixing Google-derived geometry in would make
   the combined product non-redistributable and would put the OSM-derived portion in breach of ODbL.
   It would also make the data unusable by anyone else, which defeats the point of publishing it.

### What to use instead — all verified live on 2026-07-29
| Source | Content | Licence | Size |
|---|---|---|---|
| Datameet `Municipal_Spatial_Data/Bangalore/BBMP.geojson` | BBMP ward boundaries | CC BY 4.0 | 2.0 MB |
| Datameet `…/BBMP_oldWards.geojson` (+ `.kml`) | Previous ward delimitation | CC BY 4.0 | 1.8 MB |
| Datameet `indian_village_boundaries/ka/ka.geojson` | **29,731 Karnataka revenue villages** | CC BY 4.0 | 84 MB |
| OSM admin_level 9/10/11 | 421 wards + revenue villages | ODbL | via Overpass |
| OSM `place=*` ways/relations | 103 named polygons | ODbL | via Overpass |
| OpenCity (data.opencity.in) | BBMP 243-ward (2022) & 225-ward (2023) delimitations | ODbL | GeoJSON/SHP/KML |

### The Karnataka village layer is the find of this phase
Filtered to Bangalore + Bangalore Rural districts: **2,769 village polygons** (2,727 Polygon,
42 MultiPolygon), carrying **full Census 2011 attributes** — population (`T_P`), households,
SC/ST counts, literacy, area in hectares. Covering **2,229,882 people**.

Two consequences:
- **It solves the denominator problem.** Every statistic can now be reported count-weighted *and*
  population-weighted. "8.5% of neighbourhoods are `-halli`" becomes a claim you can actually
  qualify.
- **It is a publishable finding by itself: 42.0% of the revenue villages Bengaluru was built on
  top of end in `-halli`** (1,162 of 2,769) — far higher than the 7.6% of modern neighbourhood
  names. That gap *is* the story: the city did not inherit its village names, it overwrote them.

### ⚠ But the bias of §1d appears here in its most extreme form
Revenue-village polygon availability by suffix:

| `-halli` | 51.2% | `-layout` | **0.0%** |
|---|---|---|---|
| `-pura` | 34.0% | `-nagar` | **0.0%** |
| `-ur` | 21.4% | `-colony` | **0.0%** |
| | | `-block` | **0.0%** |

Revenue villages are the *pre-urban cadastral layer*; they structurally cannot contain modern layout
names. A map built on villages alone would be 100% historic and 0% modern — the mirror image of the
error in §1d, and equally wrong. **This settles the geometry question: the two layers answer
different questions and must both be present, visually distinguished, never silently merged.**
- Revenue villages (2,769) = the substrate the city absorbed
- Wards (369) + OSM place polygons (103) = the contemporary city

### Revised classification result — measured, not projected
The original classifier did raw character-suffix matching, which fails on the most common Bengaluru
naming pattern: initials plus a suffix word. "JP Nagar", "Sector 4", "NR Colony", "MS Palaya" all
fell through. A **token-aware** classifier — check whether the final whitespace token is itself a
lexicon entry, then fall back to agglutinated matching for single-token names like "Kodihalli" —
changes the outcome completely:

| Stage | Unclassified | % |
|---|---|---|
| Current shipped pipeline | 113 | 10.32% |
| Token-aware + **existing unchanged** lexicon | 42 | **3.84%** |
| + gated-community exclusion rules | 35 | **3.35%** |

Distinct suffixes assigned rises **31 → 74**. Of 1,011 matches, 706 came from the whole-word stage —
i.e. the dominant defect was never the lexicon, it was the matching algorithm.

The 35 names still unresolved are mostly genuinely opaque Old Kannada toponyms that need scholarly
sourcing — *Yelahanka, Hebbal, Peenya, Hoodi, Sarakki, Kogilu, Madiwala, Agara, Kudlu, Banashankari*
— plus residual apartment complexes and the known CSV-quoting bug record. These are the
etymologically interesting cases, and they are exactly the ones a coverage metric cannot help with.

### On the "<8% unclassified" acceptance criterion
It is already met — 3.35% — by a bug fix requiring no new research, no new suffixes and no polygon
work at all. That makes it a poor gate: it passes today regardless of whether the map is any good.

Worse, coverage is trivially gameable in the wrong direction. Adding `-a`, `-i` and `-u` as suffixes
would drive unclassified below 1% while making the data meaningless, because most Kannada toponyms
end in a vowel. Coverage measures how often the classifier *fired*, not how often it was *right*.

Recommended acceptance criteria instead:
1. **Accuracy ≥ 95%** on a 100-name stratified random audit, verified against an independent source
   and published with a confidence interval. *(This is the one that matters.)*
2. **Unclassified ≤ 5%**, retained but demoted to a secondary check.
3. **Geometry provenance disclosed** for 100% of features, with headline statistics reproduced
   per-tier to demonstrate they are not artefacts of coverage.
4. **No suffix admitted without a citation**, so coverage cannot be inflated by invention.

---

## 8. Decisions needed before work starts

1. **Geometry strategy** — A, B, or C? This determines everything downstream. *(Recommend C, ship A first.)*
2. **Primary colour encoding** — semantic category or language? *(Recommend category, language as secondary.)*
3. **Scope** — is Stage 1 alone worth shipping as a correction to the published article, or hold everything until Stage 4?
4. **Gated communities** — in or out? *(Recommend out, by written rule, with the exclusion list published.)*
5. **Repo location** — move off Google Drive to a local git repo? *(Recommend yes.)*
