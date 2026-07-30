#!/usr/bin/env python3
"""
classify.py — Toponymy Study

Re-classifies city neighbourhood points against the enriched lexicon (Suffixes_v2.csv)
using a TOKEN-AWARE matcher, and emits the web data.json plus a QA audit CSV.

Why token-aware: the original pipeline matched raw character suffixes, so the single most
common Bengaluru naming pattern -- initials plus a suffix word ("JP Nagar", "NR Colony",
"Sector 4", "MS Palaya") -- never matched and fell into 'Other'. Checking whether the final
whitespace-delimited token is itself a lexicon entry fixes the bulk of it.

Match stages, in order:
  1. word     final token is itself a lexicon entry          "JP Nagar"      -> nagar
  2. lead     first token is a lexicon entry, trailing token is an index/letter
                                                             "Sector 4"      -> sector
  3. agglut   final token ends with a lexicon entry          "Kodihalli"     -> halli
  4. joined   whole name (spaces removed) ends with an entry "Doddabommasandra" -> sandra

Geometry is untouched: points in, points out.

Usage:  python3 02_Scripts/classify.py [city ...]      (default: Bengaluru)
"""
import csv, json, math, os, re, sys
from collections import Counter, defaultdict

ROOT    = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEXICON = os.path.join(ROOT, "Suffixes", "Suffixes_v2.csv")
BUILD   = os.path.join(ROOT, "03_Build")

# Minimum stem length required before a suffix, keyed on suffix length.
# Short suffixes are riskier (a 2-char suffix matches far more names by chance), so they
# demand a longer stem. This is what lets "-ur" work -- Domlur, Jakkur, Hennur, Varthur are
# core Kannada settlement names -- without it firing on every short word ending in 'ur'.
def min_stem(suffix_len):
    if suffix_len >= 4:
        return 2
    if suffix_len == 3:
        return 3
    return 4          # 2-char suffixes: -ur, -em, -im


MIN_AGGLUT_SUFFIX = 2

# Names that are data bugs rather than toponyms. Removed, and listed in the QA report.
def is_data_bug(name):
    n = name.strip()
    if not n:
        return "empty name"
    if n.count('"') >= 2 or n.startswith('"'):
        return "CSV quoting corruption"
    if re.fullmatch(r"[^A-Za-z]+", n):
        return "no alphabetic content"
    return None

# Builder-branded developments. NOT excluded by default -- the owner asked to keep the
# point set as-is -- but flagged so the inclusion decision can be made on evidence later.
BRANDED = re.compile(
    r"(residency|habitat|apartments?\b|towers?\b|shantiniketan|ayana|sunny\s+brooks|bestcounty"
    r"|incity|paradise|freesia|oceanus|prestige|sobha|brigade|purva|godrej|kristal|adarsh"
    r"|vaishnavi|urban\s+ville|orchid|tiara|palm\s+retreat)", re.I)


def load_lexicon():
    with open(LEXICON, newline="", encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh))
    lex = {}
    for r in rows:
        v = r["variant"].strip().lower()
        if v:
            lex[v] = r
    return lex


def tokens(name):
    return [t for t in (re.sub(r"[^a-z]", "", p.lower()) for p in re.split(r"[\s\-_/]+", name)) if t]


def classify(name, lex, ordered):
    tk = tokens(name)
    if not tk:
        return None, None
    # 1. final whole word
    if tk[-1] in lex:
        return lex[tk[-1]], "word"
    # 2. leading word + index  ("Sector 4", "Sector A", "4th Phase")
    if len(tk) > 1:
        if tk[0] in lex and len(tk[-1]) <= 2:
            return lex[tk[0]], "lead"
        for t in tk:
            if t in lex and len(t) >= 4:
                return lex[t], "lead"
    # 3. agglutinated final token
    last = tk[-1]
    for s in ordered:
        if len(s) < MIN_AGGLUT_SUFFIX:
            continue
        if last.endswith(s) and len(last) - len(s) >= min_stem(len(s)):
            return lex[s], "agglut"
    # 4. whole name joined
    joined = "".join(tk)
    for s in ordered:
        if len(s) < MIN_AGGLUT_SUFFIX:
            continue
        if joined.endswith(s) and len(joined) - len(s) >= min_stem(len(s)):
            return lex[s], "joined"
    return None, None


# Two OSM nodes carrying the same name a few hundred metres apart are the same place
# mapped twice (HSR Layout, the Jayanagar blocks, the JP Nagar phases). Two carrying the
# same name 25 km apart are different places sharing a generic name -- Bengaluru has five
# unrelated "Vinayaka Layout"s. The measured distribution is cleanly bimodal: 42 pairs
# under 300 m, a gap, then 80 pairs over 5 km. 1.5 km sits in the gap.
DEDUP_KM = 1.5


def haversine_km(a, b):
    R = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = p2 - p1
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def dedupe(features):
    """Collapse same-named points that sit within DEDUP_KM of each other.

    Clusters rather than deleting pairwise: a name appearing five times in one spot
    collapses to one record, not to an arbitrary survivor of ten pair comparisons.
    """
    groups = defaultdict(list)
    for f in features:
        groups[re.sub(r"\s+", " ", f["n"].strip().lower())].append(f)

    keep, removed = [], []
    for name, items in groups.items():
        if len(items) == 1:
            keep.append(items[0])
            continue
        clusters = []                      # each: [representative, [members...]]
        for f in items:
            for rep, members in clusters:
                if haversine_km((rep["lat"], rep["lon"]), (f["lat"], f["lon"])) <= DEDUP_KM:
                    members.append(f)
                    break
            else:
                clusters.append((f, []))
        for rep, members in clusters:
            keep.append(rep)
            for m in members:
                removed.append((m["n"], round(haversine_km((rep["lat"], rep["lon"]),
                                                           (m["lat"], m["lon"])) * 1000)))
    keep.sort(key=lambda f: (f["n"].lower(), f["lat"]))
    return keep, removed


def find_city(city):
    for cand in (os.path.join(ROOT, "Cities", city, "data.json"),
                 os.path.join(ROOT, "Archive", "data_v1.json")):
        if os.path.exists(cand):
            with open(cand, encoding="utf-8") as fh:
                blob = json.load(fh)
            for c in blob.get("cities", []):
                if c["name"].lower() == city.lower():
                    return c, cand
    return None, None


def run(city):
    lex = load_lexicon()
    ordered = sorted(lex, key=len, reverse=True)

    src, path = find_city(city)
    if not src:
        print("  !! no source data for %s" % city)
        return None
    print("\n%s  <- %s" % (city, os.path.relpath(path, ROOT)))

    out, audit, dropped = [], [], []
    stages = Counter()

    for n in src["neighborhoods"]:
        name = (n.get("n") or "").strip()
        bug = is_data_bug(name)
        if bug:
            dropped.append((name, bug))
            continue
        rec, stage = classify(name, lex, ordered)
        stages[stage or "UNMATCHED"] += 1
        feature = {
            "n": name,
            "lat": round(float(n["lat"]), 6),
            "lon": round(float(n["lon"]), 6),
        }
        if rec:
            feature.update({
                "s":  rec["variant"],
                "lem": rec["lemma"],
                "m":  rec["meaning"] or "—",
                "l":  rec["language"],
                "lf": rec["language_family"],
                "cf": rec["colour_family"],
                "sc": rec["semantic_category"],
                "sg": rec["semantic_group"],
                "cn": rec["confidence"],
            })
        else:
            feature.update({"s": "Other", "lem": "Other", "m": "Unresolved",
                            "l": "Unknown", "lf": "Other", "cf": "grey",
                            "sc": "other", "sg": "unresolved", "cn": "unresolved"})
        feature["brand"] = 1 if BRANDED.search(name) else 0
        out.append(feature)
        audit.append({"name": name, "suffix": feature["s"], "lemma": feature["lem"],
                      "language": feature["l"], "language_family": feature["lf"],
                      "semantic_category": feature["sc"], "semantic_group": feature["sg"],
                      "meaning": feature["m"],
                      "confidence": feature["cn"], "match_stage": stage or "UNMATCHED",
                      "builder_branded": feature["brand"]})

    out, dupes = dedupe(out)
    audit = [a for a in audit
             if any(a["name"] == f["n"] and a["suffix"] == f["s"] for f in out)]

    total = len(out)
    unres = sum(1 for f in out if f["s"] == "Other")
    pct = 100.0 * unres / total if total else 0
    print("  %d points  |  unresolved %d (%.2f%%)  |  distinct lemmas %d"
          % (total, unres, pct, len({f["lem"] for f in out if f["lem"] != "Other"})))
    print("  match stages: %s" % dict(stages))
    if dropped:
        print("  dropped %d data-bug records: %s" % (len(dropped), Counter(b for _, b in dropped)))
    if dupes:
        print("  de-duplicated %d records (same name within %.1f km)" % (len(dupes), DEDUP_KM))
    brand = sum(f["brand"] for f in out)
    print("  builder-branded (flagged, NOT removed): %d" % brand)
    print("  %s target <5%% unresolved" % ("PASS" if pct < 5 else "FAIL"))

    return {"city": {"name": city, "coords": src["coords"], "zoom": src.get("zoom", 11),
                     "neighborhoods": out},
            "audit": audit, "dropped": dropped, "dupes": dupes, "pct": pct}


def main():
    cities = sys.argv[1:] or ["Bengaluru"]
    os.makedirs(BUILD, exist_ok=True)
    results, payload = [], []

    for c in cities:
        r = run(c)
        if r:
            results.append(r)
            payload.append(r["city"])

    if not payload:
        sys.exit("nothing built")

    # Freeze lemma -> shade index, computed ONCE from whole-dataset frequency.
    # The dataviz rule is that colour follows the entity, never its rank: if the shade
    # were recomputed per filter, hiding a suffix would repaint every survivor. Baking
    # it here means a filtered map keeps every colour exactly where the reader left it.
    SHADES = 6
    by_family = defaultdict(Counter)
    for city in payload:
        for f in city["neighborhoods"]:
            if f["lem"] != "Other":
                by_family[f["cf"]][f["lem"]] += 1
    shade_of = {}
    for fam, counter in by_family.items():
        for rank, (lemma, _) in enumerate(counter.most_common()):
            shade_of[lemma] = min(rank, SHADES - 1)
    for city in payload:
        for f in city["neighborhoods"]:
            f["sh"] = shade_of.get(f["lem"], SHADES - 1)

    with open(os.path.join(BUILD, "data.json"), "w", encoding="utf-8") as fh:
        json.dump({"cities": payload, "shade_of": shade_of},
                  fh, ensure_ascii=False, separators=(",", ":"))

    # lexicon travels with the build so the legend can render meanings without a second fetch
    with open(LEXICON, newline="", encoding="utf-8-sig") as fh:
        lexrows = list(csv.DictReader(fh))
    with open(os.path.join(BUILD, "lexicon.json"), "w", encoding="utf-8") as fh:
        json.dump(lexrows, fh, ensure_ascii=False, separators=(",", ":"))

    for r in results:
        name = r["city"]["name"]
        with open(os.path.join(BUILD, "audit_%s.csv" % name), "w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(r["audit"][0].keys()))
            w.writeheader()
            w.writerows(r["audit"])
        if r["dupes"]:
            with open(os.path.join(BUILD, "duplicates_%s.csv" % name), "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh); w.writerow(["removed_name", "metres_from_kept_point"]); w.writerows(r["dupes"])
        if r["dropped"]:
            with open(os.path.join(BUILD, "dropped_%s.csv" % name), "w", newline="", encoding="utf-8") as fh:
                w = csv.writer(fh)
                w.writerow(["name", "reason"])
                w.writerows(r["dropped"])

    print("\nwrote %s/{data.json,lexicon.json,audit_*.csv}" % os.path.relpath(BUILD, ROOT))


if __name__ == "__main__":
    main()
