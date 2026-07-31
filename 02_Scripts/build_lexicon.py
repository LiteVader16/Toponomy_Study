#!/usr/bin/env python3
"""
build_lexicon.py — Toponymy Study
Builds the enriched suffix lexicon (Suffixes_v2.csv) from the original Suffixes.csv.

Adds, per suffix:
  lemma              canonical morpheme (variants collapse onto this)
  variant            the surface form as it appears in names
  language           language of origin, as given in the source list
  language_family    Dravidian / Indo-Aryan / Perso-Arabic / English / Other
  colour_family      red / blue / yellow / purple / grey   (drives the Language view)
  semantic_category  drives the Semantic view
  meaning
  confidence         attested | probable | speculative
  source             <-- INTENTIONALLY BLANK. Populate as research proceeds.
  notes

Usage:  python3 02_Scripts/build_lexicon.py
"""
import csv, os, re, sys
from collections import OrderedDict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC  = os.path.join(ROOT, "Suffixes", "Suffixes.csv")
OUT  = os.path.join(ROOT, "Suffixes", "Suffixes_v2.csv")

# ---------------------------------------------------------------- language → family → colour
FAMILY = {
    "kannada": "Dravidian", "tamil": "Dravidian", "telugu": "Dravidian", "malayalam": "Dravidian",
    "sanskrit": "Indo-Aryan", "hindi": "Indo-Aryan", "marathi": "Indo-Aryan",
    "gujarati": "Indo-Aryan", "bengali": "Indo-Aryan", "assamese": "Indo-Aryan",
    "konkani": "Indo-Aryan", "rajasthani": "Indo-Aryan", "odia": "Indo-Aryan",
    "persian": "Perso-Arabic", "urdu": "Perso-Arabic", "arabic": "Perso-Arabic",
    "english": "English",
}
COLOUR_FAMILY = {
    "Dravidian": "yellow",     # golds/yellows  — the Kannada substrate
    "Indo-Aryan": "red",       # reds/oranges   — Sanskritic & north-Indian overlay
    "English": "blue",         # blues          — colonial & planned
    "Perso-Arabic": "purple",  # purples        — Deccan sultanate / Mughal
    "Other": "grey",
}

# ---------------------------------------------------------------- semantic categories
# Ten categories. Keyed on normalised suffix; anything unmapped falls to "other".
CATEGORY = {}
def _cat(name, keys):
    for k in keys.split():
        CATEGORY[k] = name

_cat("settlement", """
 halli alli ahalli hatti doddi palya palaya palyam pallya ur uru oor ooru pura puram pur puri pore
 nagar nagara nagari gaon gaothan gam village town township city khera basti basthi para tola tuli
 vaddo guda gudem cheri cherry sery sherry pady akkam pakkam kuppam patnam pattanam em im lim oli
 pada pakhadi vas budruk kalan khurd vali ner alam vattom agrahara mangala vara hosur bele chuk
 chukdanga""")

_cat("hydrology", """
 kere sandra andra katte kunte gunte gunta kunta eri ere kulam pukur pukhuri thangal puzha chira
 hauz bowli sar ghat juli mukh dam bhavi kuva amanikere samudra""")

_cat("topography", """
 giri betta gudda bande gutta met malai tekdi hill hills khind danga guppe kallu ghatta gatta madu
 mound""")

_cat("flora_agriculture", """
 bagh baug van kunj garden gardens orchard plantation thota kadu mavu vad gachhi pathar bhat
 paramba mattom field kara""")

_cat("planned_administrative", """
 layout sector block stage phase scheme extension zone colony enclave society quarters complex
 compound area estate point circle square lines camp""")

_cat("commerce", """
 pete pet pettai bazaar bazar ganj gunj market hat naka chowk chok peth""")

_cat("religious", """
 gudi mandir dham devi eshwar pally pilly matha kendra puja""")

_cat("fortification", """
 garh qila kote fort gate darwaza darwaja""")

_cat("dwelling", """
 wada wadi wara war chawl pol vihar mahal bungalows mohalla sarai kothi""")

_cat("infrastructure", """
 marg bandar bunder thura chowki naka road""")

# stragglers resolved on review
_cat("settlement", "bad aram")                    # -abad (city); aram (dwelling-place)
_cat("flora_agriculture", "bari park kaval kavalu")
_cat("hydrology", "kundi godi")                   # kundi pit/pond; godi dock/wharf
_cat("religious", "deo")                          # deva — god
_cat("commerce", "ngad")
_cat("planned_administrative", "east west maidan plot reclamation")
_cat("topography", "dongri dongar khadak mati kop")
_cat("hydrology", "khadi talao nala sagar dhara")
_cat("commerce", "mithagar khadan")
_cat("settlement", "koliwada shrushti")
_cat("infrastructure", "galli gully bandar chowky causeway dock docks parade bandstand")
_cat("fortification", "gadh gad")
_cat("flora_agriculture", "green")
# byrathi, ruthy, vathy remain 'other' — genuinely unresolved, flagged for research

# ---------------------------------------------------------------- variant → lemma collapse
LEMMA = {
    "nagara": "nagar", "nagari": "nagar",
    "puram": "pura", "pore": "pura", "puri": "pura", "pur": "pura",
    "pete": "pet", "pettai": "pet", "peth": "pet",
    "palaya": "palya", "palyam": "palya", "pallya": "palya",
    "uru": "ur", "oor": "ur", "ooru": "ur",
    "alli": "halli", "ahalli": "halli",
    "andra": "sandra",
    "gunte": "kunte", "gunta": "kunte", "kunta": "kunte",
    "gatta": "ghatta",
    "gardens": "garden",
    "hills": "hill",
    "bazar": "bazaar",
    "gunj": "ganj",
    "chok": "chowk",
    "baug": "bagh",
    "basthi": "basti",
    "darwaja": "darwaza",
    "cherry": "cheri", "sery": "cheri", "sherry": "cheri",
    "pilly": "pally",
    "wara": "wada", "wadi": "wada",
    "kavalu": "kaval",
    "ere": "eri",
    "bunder": "bandar",
    "town": "town", "township": "township",
}

# ---------------------------------------------------------------- additions (Kannada / Bengaluru)
# confidence: 'probable' until a citation lands in the source column.
ADDITIONS = [
    # variant,      language,  meaning,                                    confidence
    ("katte",   "Kannada", "Tank bund / raised stone platform",            "probable"),
    ("kaval",   "Kannada", "Grazing land / reserved pasture",              "probable"),
    ("kavalu",  "Kannada", "Grazing land / reserved pasture",              "probable"),
    ("kunte",   "Kannada", "Pond / small tank",                            "probable"),
    ("gunte",   "Kannada", "Pond / small tank",                            "probable"),
    ("gunta",   "Kannada", "Pond / small tank",                            "probable"),
    ("bande",   "Kannada", "Rock / boulder outcrop",                       "probable"),
    ("hatti",   "Kannada", "Hamlet / cattle settlement",                   "probable"),
    ("doddi",   "Kannada", "Cattle pen / enclosure",                       "probable"),
    ("kallu",   "Kannada", "Stone / rock",                                 "probable"),
    ("ghatta",  "Kannada", "Hill / ridge",                                 "probable"),
    ("gatta",   "Kannada", "Hill / ridge",                                 "probable"),
    ("mavu",    "Kannada", "Mango tree",                                   "probable"),
    ("madu",    "Kannada", "Pool / hollow / low ground",                   "speculative"),
    ("vara",    "Kannada", "Settlement",                                   "speculative"),
    ("alli",    "Kannada", "Village (sandhi variant of -halli)",           "attested"),
    ("betta",   "Kannada", "Hill",                                         "attested"),
    ("gudda",   "Kannada", "Hill / hillock",                               "probable"),
    ("thota",   "Kannada", "Grove / orchard / garden",                     "attested"),
    ("bhavi",   "Kannada", "Well",                                         "probable"),
    ("bele",    "Kannada", "Crop / cultivated field",                      "speculative"),
    ("kote",    "Kannada", "Fort",                                         "attested"),
    ("matha",   "Kannada", "Monastery / religious establishment",          "attested"),
    ("amanikere","Kannada","Rain-fed tank",                                "probable"),
    ("dinne",   "Kannada", "Mound / hillock",                              "probable"),
    ("kodi",    "Kannada", "End / edge / boundary",                        "probable"),
    ("khane",   "Persian", "House / quarter",                              "probable"),
    ("grounds", "English", "Open ground",                                  "attested"),

    # --- Mumbai / Marathi-Konkani expansion (v10) ---------------------------
    # Mumbai's naming is structurally unlike Bengaluru's: fewer productive suffixes,
    # more simplex island-village names inherited from Koli and East Indian settlement,
    # plus a distinct colonial descriptive layer absent from Bengaluru.
    ("dongri",   "Marathi",  "Hillock (from dongar)",                      "attested"),
    ("dongar",   "Marathi",  "Hill",                                       "attested"),
    ("khadi",    "Marathi",  "Creek / tidal inlet",                        "attested"),
    ("khadak",   "Marathi",  "Rock / rocky ground",                        "probable"),
    ("khadan",   "Marathi",  "Quarry",                                     "probable"),
    ("mithagar", "Marathi",  "Salt pan",                                   "attested"),
    ("koliwada", "Marathi",  "Koli fishing settlement",                    "attested"),
    ("talao",    "Marathi",  "Tank / lake",                                "attested"),
    ("galli",    "Marathi",  "Lane",                                       "attested"),
    ("gully",    "Marathi",  "Lane",                                       "probable"),
    ("sagar",    "Sanskrit", "Sea",                                        "attested"),
    ("gadh",     "Marathi",  "Fort",                                       "attested"),
    ("gad",      "Marathi",  "Fort",                                       "probable"),
    ("mati",     "Marathi",  "Earth / soil",                               "probable"),
    ("dhara",    "Marathi",  "Stream / flow",                              "speculative"),
    ("bandar",   "Marathi",  "Harbour / port",                             "attested"),
    ("chowky",   "Marathi",  "Post / station",                             "probable"),
    ("nala",     "Marathi",  "Watercourse / drain",                        "probable"),
    ("kop",      "Marathi",  "Hamlet / cluster",                           "speculative"),
    ("shrushti", "Sanskrit", "Creation / world (modern coinage)",          "probable"),

    # Colonial descriptive layer — a genuine Mumbai naming stratum, not noise.
    ("green",       "English", "Open green / common",                      "attested"),
    ("parade",      "English", "Parade ground / promenade",                "attested"),
    ("reclamation", "English", "Reclaimed land",                           "attested"),
    ("bandstand",   "English", "Bandstand promenade",                      "attested"),
    ("causeway",    "English", "Causeway",                                 "attested"),
    ("dock",        "English", "Dock",                                     "attested"),
    ("docks",       "English", "Dock",                                     "attested"),
    ("plot",        "English", "Surveyed plot",                            "probable"),
]

# Whole names that must NEVER be suffix-matched. Each is a simplex toponym whose ending
# coincides with a real suffix; matching them manufactures a false etymology.
# ("Lal Bahadur Shastri Nagar" is already safe -- the token-aware matcher takes the final
# word -- but a bare "Bahadur" would otherwise be read as Dravidian -ur.)
NEVER_MATCH = {
    "bahadur", "bandra", "chembur", "nahur", "mahur", "sion", "khar", "mahim",
    "worli", "parel", "colaba", "dharavi", "juhu", "madh", "marve", "gorai",
    "danda", "powai", "kalina", "vakola", "wadala", "mahul", "deonar",
}

NON_SUFFIX = {"suffix", "no", "area"}   # header artefacts / too generic to match on

# Map the 11 fine-grained categories onto the 5 groups the MAP COLOURS use.
# Colour can only carry so many categories before they stop being distinguishable
# (measured: 7 is the ceiling under the all-pairs CVD gate, and 5 leaves headroom).
# The fine category is kept in the data, the popup and the CSV; only the hue is grouped.
SEMANTIC_GROUP = {
    "settlement":             "settlement",
    "planned_administrative": "planned_admin",
    "hydrology":              "water",
    "flora_agriculture":      "land",
    "topography":             "land",
    "commerce":               "built_social",
    "dwelling":               "built_social",
    "religious":              "built_social",
    "fortification":          "built_social",
    "infrastructure":         "built_social",
    "other":                  "unresolved",
}


def norm(s):
    return re.sub(r"[^a-z]", "", (s or "").lower())


def family_of(language):
    first = re.split(r"[/,]", (language or "").strip())[0].strip().lower()
    return FAMILY.get(first, "Other")


def main():
    if not os.path.exists(SRC):
        sys.exit("missing source lexicon: %s" % SRC)

    rows = OrderedDict()   # normalised variant -> record

    def add(variant, language, meaning, confidence, notes=""):
        key = norm(variant)
        if not key or key in NON_SUFFIX:
            return
        if key in rows:                      # de-duplicate (D5)
            prev = rows[key]
            if prev["meaning"].lower() in ("", "unknown") and meaning:
                prev["meaning"] = meaning
            if language and language.lower() not in prev["language"].lower():
                prev["notes"] = (prev["notes"] + " | also attested as %s" % language).strip(" |")
            return
        fam = family_of(language)
        rows[key] = {
            "lemma": LEMMA.get(key, key),
            "variant": key,
            "language": (language or "").strip(),
            "language_family": fam,
            "colour_family": COLOUR_FAMILY[fam],
            "semantic_category": CATEGORY.get(LEMMA.get(key, key), CATEGORY.get(key, "other")),
            "semantic_group": SEMANTIC_GROUP.get(
                CATEGORY.get(LEMMA.get(key, key), CATEGORY.get(key, "other")), "unresolved"),
            "meaning": (meaning or "").strip(),
            "confidence": confidence,
            "source": "",           # <-- to populate as research proceeds
            "notes": notes,
        }

    with open(SRC, newline="", encoding="utf-8-sig") as fh:
        for r in csv.DictReader(fh):
            if not r.get("Suffix") or r["Suffix"].strip().lower() == "suffix":
                continue          # skips the repeated header at line 84
            meaning = (r.get("Meaning") or "").strip()
            add(r["Suffix"], r.get("Language", ""), meaning,
                "attested" if meaning.lower() not in ("", "unknown") else "speculative")

    before = len(rows)
    for variant, lang, meaning, conf in ADDITIONS:
        add(variant, lang, meaning, conf, notes="added in v2 lexicon expansion")
    added = len(rows) - before

    ordered = sorted(rows.values(), key=lambda x: (x["semantic_category"], x["lemma"], x["variant"]))
    cols = ["lemma", "variant", "language", "language_family", "colour_family",
            "semantic_category", "semantic_group", "meaning", "confidence", "source", "notes"]
    with open(OUT, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(ordered)

    from collections import Counter
    print("wrote %s" % OUT)
    print("  %d entries (%d from original list, %d added)" % (len(ordered), before, added))
    print("  lemmas: %d" % len({r["lemma"] for r in ordered}))
    print("\n  by colour_family:")
    for k, v in Counter(r["colour_family"] for r in ordered).most_common():
        print("    %-8s %d" % (k, v))
    print("\n  by semantic_category:")
    for k, v in Counter(r["semantic_category"] for r in ordered).most_common():
        print("    %-24s %d" % (k, v))
    unc = [r["variant"] for r in ordered if r["semantic_category"] == "other"]
    if unc:
        print("\n  uncategorised (%d): %s" % (len(unc), ", ".join(unc)))


if __name__ == "__main__":
    main()
