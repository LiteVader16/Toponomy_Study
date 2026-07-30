#!/usr/bin/env python3
"""
build_polygons.py — attach real polygon geometry to classified neighbourhoods.

TIERS (every feature records which one it came from, in `gsrc`)
  1 osm_place        OSM place=* closed way, matched by name        most precise
  2 bbmp_ward        Datameet BBMP ward polygon, matched by name    CC BY 4.0
  3 revenue_village  Karnataka revenue village, matched by name     CC BY 4.0, Census 2011 attrs
  4 point            no polygon found -- stays a Point

Nothing is fabricated. There is no Voronoi fill: a derived cell would look identical to a
surveyed boundary at a glance, and 60% of the map would be invention. Unmatched names stay
points and say so.

READ THIS BEFORE QUOTING ANY POLYGON STATISTIC
Polygon availability is NOT uniform across suffixes. Historic village names survive as
revenue villages and ward names; modern private layouts mostly do not. Measured on the
point set: -halli ~49% has a polygon, -layout ~15%, -garden ~6%. So "share of the mapped
AREA that is -halli" overstates -halli badly. Counts stay the honest denominator; the
per-tier coverage table printed at the end is what to publish alongside any area claim.

Usage: python3 02_Scripts/build_polygons.py
"""
import json, math, os, re, sys, time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "01_Data_Raw")
BUILD = os.path.join(ROOT, "03_Build")
MAX_SNAP_KM = 4.0        # matched polygon must be this close to the point, else reject


# ------------------------------------------------------------------ helpers
def norm(s):
    s = (s or "").lower()
    s = re.sub(r"\b(ward|no|number|layout|village|gram|panchayat)\b", " ", s)
    return re.sub(r"[^a-z]", "", s)


def ring_centroid(ring):
    a = cx = cy = 0.0
    for i in range(len(ring) - 1):
        x0, y0 = ring[i][0], ring[i][1]
        x1, y1 = ring[i + 1][0], ring[i + 1][1]
        cr = x0 * y1 - x1 * y0
        a += cr
        cx += (x0 + x1) * cr
        cy += (y0 + y1) * cr
    if abs(a) < 1e-12:
        xs = [p[0] for p in ring]
        ys = [p[1] for p in ring]
        return sum(xs) / len(xs), sum(ys) / len(ys)
    a *= 0.5
    return cx / (6 * a), cy / (6 * a)


def outer_ring(geom):
    if geom["type"] == "Polygon":
        return geom["coordinates"][0]
    if geom["type"] == "MultiPolygon":
        return max(geom["coordinates"], key=lambda p: len(p[0]))[0]
    return None


def centroid_of(geom):
    r = outer_ring(geom)
    return ring_centroid(r) if r else None


def point_in_ring(lon, lat, ring):
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        xi, yi = ring[i][0], ring[i][1]
        xj, yj = ring[j][0], ring[j][1]
        if (yi > lat) != (yj > lat):
            if lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-18) + xi:
                inside = not inside
        j = i
    return inside


def point_in_geom(lon, lat, geom):
    if geom["type"] == "Polygon":
        return point_in_ring(lon, lat, geom["coordinates"][0])
    if geom["type"] == "MultiPolygon":
        return any(point_in_ring(lon, lat, p[0]) for p in geom["coordinates"])
    return False


def km(a, b):
    R = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp = p2 - p1
    dl = math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(h))


def round_geom(geom, nd=5):
    """5 decimal places is ~1 m at this latitude — far finer than the boundaries warrant,
    and it roughly halves the payload."""
    def rr(ring):
        out = []
        for x, y in ring:
            p = [round(x, nd), round(y, nd)]
            if not out or p != out[-1]:
                out.append(p)
        if len(out) > 2 and out[0] != out[-1]:
            out.append(out[0])
        return out
    if geom["type"] == "Polygon":
        return {"type": "Polygon", "coordinates": [rr(r) for r in geom["coordinates"]]}
    return {"type": "MultiPolygon",
            "coordinates": [[rr(r) for r in poly] for poly in geom["coordinates"]]}


# ------------------------------------------------------------------ sources
def fetch_osm_place_polygons():
    cache = os.path.join(RAW, "osm_place_polygons.json")
    if os.path.exists(cache):
        with open(cache) as fh:
            return json.load(fh)
    q = """[out:json][timeout:180];
area["name"="Bengaluru"]["boundary"="administrative"]->.a;
way["place"~"^(suburb|neighbourhood|quarter|village|town|hamlet|locality)$"](area.a);
out geom;"""
    data = None
    for attempt in range(4):
        for ep in ("https://overpass-api.de/api/interpreter",
                   "https://overpass.kumi.systems/api/interpreter"):
            try:
                req = urllib.request.Request(
                    ep, data=urllib.parse.urlencode({"data": q}).encode(),
                    headers={"User-Agent": "toponymy-study/0.1 (research)"})
                data = json.load(urllib.request.urlopen(req, timeout=300))
                break
            except Exception as e:
                print("    overpass %s: %s" % (ep.split("/")[2], e))
        if data:
            break
        time.sleep(20)
    if not data:
        print("  !! Overpass unavailable — continuing without tier 1")
        return {"elements": []}
    os.makedirs(RAW, exist_ok=True)
    with open(cache, "w") as fh:
        json.dump(data, fh)
    return data


def fetch_osm_admin():
    """admin_level 9/10 relations — revenue villages and wards, with vernacular names."""
    cache = os.path.join(RAW, "osm_admin_geom.json")
    if os.path.exists(cache):
        with open(cache) as fh:
            return json.load(fh)
    q = """[out:json][timeout:300];
area["name"="Bengaluru"]["boundary"="administrative"]->.a;
relation["boundary"="administrative"]["admin_level"~"^(9|10|11)$"](area.a);
out geom;"""
    data = None
    for attempt in range(4):
        for ep in ("https://overpass-api.de/api/interpreter",
                   "https://overpass.kumi.systems/api/interpreter"):
            try:
                req = urllib.request.Request(
                    ep, data=urllib.parse.urlencode({"data": q}).encode(),
                    headers={"User-Agent": "toponymy-study/0.1 (research)"})
                data = json.load(urllib.request.urlopen(req, timeout=600))
                break
            except Exception as e:
                print("    overpass %s: %s" % (ep.split("/")[2], e))
        if data:
            break
        time.sleep(20)
    if not data:
        print("  !! Overpass unavailable — continuing without OSM admin tier")
        return {"elements": []}
    os.makedirs(RAW, exist_ok=True)
    with open(cache, "w") as fh:
        json.dump(data, fh)
    return data


def stitch(members):
    """Assemble a boundary relation's outer ways into closed rings.

    Overpass returns a relation as an unordered bag of ways; a ring only exists once
    they are joined end-to-end. Ways also arrive in arbitrary direction, so each
    candidate has to be tried forwards and reversed.
    """
    segs = []
    for m in members:
        if m.get("type") != "way" or m.get("role") not in ("outer", "", None):
            continue
        g = m.get("geometry") or []
        if len(g) >= 2:
            segs.append([[p["lon"], p["lat"]] for p in g if p])
    rings = []
    while segs:
        cur = segs.pop(0)
        changed = True
        while changed and cur[0] != cur[-1]:
            changed = False
            for i, s in enumerate(segs):
                if s[0] == cur[-1]:
                    cur += s[1:]
                elif s[-1] == cur[-1]:
                    cur += s[::-1][1:]
                elif s[-1] == cur[0]:
                    cur = s[:-1] + cur
                elif s[0] == cur[0]:
                    cur = s[::-1][:-1] + cur
                else:
                    continue
                segs.pop(i)
                changed = True
                break
        if len(cur) >= 4:
            if cur[0] != cur[-1]:
                cur.append(cur[0])
            rings.append(cur)
    if not rings:
        return None
    rings.sort(key=len, reverse=True)
    if len(rings) == 1:
        return {"type": "Polygon", "coordinates": [rings[0]]}
    return {"type": "MultiPolygon", "coordinates": [[r] for r in rings]}


def load_sources():
    src = []

    osm = fetch_osm_place_polygons()
    n = 0
    for e in osm.get("elements", []):
        name = (e.get("tags") or {}).get("name")
        geo = e.get("geometry")
        if not name or not geo or len(geo) < 4:
            continue
        ring = [[p["lon"], p["lat"]] for p in geo]
        if ring[0] != ring[-1]:
            ring.append(ring[0])
        src.append((norm(name), name, {"type": "Polygon", "coordinates": [ring]}, "osm_place"))
        n += 1
    print("  tier 1 osm_place       : %d polygons" % n)

    adm = fetch_osm_admin()
    n = 0
    for e in adm.get("elements", []):
        name = (e.get("tags") or {}).get("name")
        if not name:
            continue
        g = stitch(e.get("members") or [])
        if g:
            src.append((norm(name), name, g, "osm_admin"))
            n += 1
    print("  tier 2 osm_admin       : %d polygons" % n)

    p = os.path.join(RAW, "BBMP.geojson")
    n = 0
    if os.path.exists(p):
        for f in json.load(open(p))["features"]:
            nm = f["properties"].get("KGISWardName")
            if nm and f.get("geometry"):
                src.append((norm(nm), nm, f["geometry"], "bbmp_ward"))
                n += 1
    print("  tier 3 bbmp_ward       : %d polygons" % n)

    p = os.path.join(RAW, "blr_villages.geojson")
    n = 0
    if os.path.exists(p):
        for f in json.load(open(p))["features"]:
            nm = f["properties"].get("NAME") or f["properties"].get("VILL_NAME")
            if nm and str(nm).strip().lower() != "no data" and f.get("geometry"):
                src.append((norm(nm), nm, f["geometry"], "revenue_village"))
                n += 1
    print("  tier 4 revenue_village : %d polygons" % n)

    return src


# ------------------------------------------------------------------ main
def main():
    data = json.load(open(os.path.join(BUILD, "data.json")))
    city = data["cities"][0]
    feats = city["neighborhoods"]
    print("classified points: %d\n" % len(feats))

    print("polygon sources:")
    sources = load_sources()

    index = {}
    for key, name, geom, tier in sources:
        if key:
            index.setdefault(key, []).append((name, geom, tier))
    for lst in index.values():
        lst.sort(key=lambda x: {"osm_place": 0, "osm_admin": 1,
                                "bbmp_ward": 2, "revenue_village": 3}[x[2]])

    out, tally = [], {}
    for f in feats:
        pt = (f["lat"], f["lon"])
        geom = {"type": "Point", "coordinates": [f["lon"], f["lat"]]}
        tier, matched_name = "point", None

        for name, g, t in index.get(norm(f["n"]), []):
            c = centroid_of(g)
            if not c:
                continue
            inside = point_in_geom(f["lon"], f["lat"], g)
            d = km(pt, (c[1], c[0]))
            if inside or d <= MAX_SNAP_KM:
                geom, tier, matched_name = round_geom(g), t, name
                break

        tally[tier] = tally.get(tier, 0) + 1
        props = {k: v for k, v in f.items() if k not in ("lat", "lon")}
        props.update({"gsrc": tier, "lat": f["lat"], "lon": f["lon"]})
        if matched_name and norm(matched_name) != norm(f["n"]):
            props["gname"] = matched_name
        out.append({"type": "Feature", "properties": props, "geometry": geom})

    fc = {"type": "FeatureCollection",
          "name": "Bengaluru toponymy",
          "city": {"name": city["name"], "coords": city["coords"], "zoom": city.get("zoom", 11)},
          "shade_of": data.get("shade_of", {}),
          "features": out}
    path = os.path.join(BUILD, "polygons.geojson")
    with open(path, "w") as fh:
        json.dump(fc, fh, separators=(",", ":"))

    total = len(out)
    poly = total - tally.get("point", 0)
    print("\ngeometry assigned")
    for t in ("osm_place", "osm_admin", "bbmp_ward", "revenue_village", "point"):
        if t in tally:
            print("  %-16s %4d  %5.1f%%" % (t, tally[t], 100 * tally[t] / total))
    print("  %-16s %4d  %5.1f%%" % ("ANY POLYGON", poly, 100 * poly / total))
    print("\nwrote %s (%.1f MB)" % (os.path.relpath(path, ROOT), os.path.getsize(path) / 1e6))

    # the bias table — publish this next to any area-based claim
    print("\npolygon coverage BY SUFFIX (the selection-bias check):")
    bysfx = {}
    for f in out:
        p = f["properties"]
        d = bysfx.setdefault(p["lem"], [0, 0])
        d[0] += 1
        if p["gsrc"] != "point":
            d[1] += 1
    for lem, (n, g) in sorted(bysfx.items(), key=lambda x: -x[1][0])[:14]:
        print("  %-12s %4d pts  %4d polygons  %5.1f%%" % (lem, n, g, 100 * g / n))


if __name__ == "__main__":
    main()
