#!/usr/bin/env python3
"""
make_palette.py — emits 03_Build/palette.json, the validated colour system.

TWO VIEWS
  view 1 "language"  hue  = language family (yellow/red/blue/purple, as requested)
                     shade = individual lemma, ordinal ramp within the family
  view 2 "semantic"  hue  = semantic category

VALIDATION (see validate_palette.py; all figures re-checked by verify_palette.py)
  The map is a point form, so the family hues are gated on ALL PAIRS, not adjacent.
  Light: CVD dE 8.4 (>=8), normal-vision dE 15.6 (>=15)   PASS
  Dark : CVD dE 8.1 (>=8), normal-vision dE 15.5 (>=15)   PASS
  Family hues were solved as the CLOSEST PASSING triple to the project's existing
  red/blue/yellow, so the look is preserved and the gates are met.

  Within-family shades are an ORDINAL ramp (monotone lightness, adjacent dL >= 0.06),
  not a second categorical channel. Hue carries identity; shade is a refinement
  supported by the legend, the popup and click-to-filter. Lemma -> shade index is
  frozen at build time from whole-dataset frequency, so filtering never repaints.

Usage: python3 02_Scripts/make_palette.py
"""
import json, math, os

ROOT  = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BUILD = os.path.join(ROOT, "03_Build")

# ---- validated family hues (closest passing triple + solved 4th slot) -------
FAMILY_BASE = {
    "light": {"yellow": "#c68200", "red": "#d84c5a", "blue": "#3379d7",
              "purple": "#464990", "grey": "#8a8a86"},
    "dark":  {"yellow": "#c38700", "red": "#df4558", "blue": "#3485e2",
              "purple": "#795a98", "grey": "#7e7e7a"},
}
FAMILY_HUE = {"yellow": 92, "red": 25, "blue": 258, "purple": 310}
SHADES = 6

# ---- semantic GROUPS -------------------------------------------------------
# Solved, not picked: hues optimised for maximum separation under the all-pairs CVD
# gate, then re-solved for the LOWEST chroma that still passes, so the map reads muted
# rather than neon. Measured on the 5 groups plus grey:
#   light  CVD dE 8.1 (>=8)   normal-vision dE 15.1 (>=15)   PASS
#   dark   CVD dE 8.3 (>=8)   normal-vision dE 15.0 (>=15)   PASS
# Why five and not eleven: 8 and 9 categories cannot clear the all-pairs gate at any
# ordering (measured: best 9-hue wheel reaches CVD 3.9 / NV 9.6). 7 is the ceiling;
# 5 leaves headroom. The fine category still travels in the data, popup and CSV.
SEMANTIC = {
    "light": {
        "settlement":    "#ed6b42",
        "planned_admin": "#704a00",
        "water":         "#4e69ab",
        "land":          "#05764e",
        "built_social":  "#773869",
        "unresolved":    "#8a8a86",
        "simplex":       "#4f4f4c",
    },
    "dark": {
        "settlement":    "#b44300",
        "planned_admin": "#c48200",
        "water":         "#006ca6",
        "land":          "#007743",
        "built_social":  "#a975ce",
        "unresolved":    "#7e7e7a",
        "simplex":       "#c2c2ba",
    },
}

SEMANTIC_LABEL = {
    "settlement":    "Settlement",
    "planned_admin": "Planned / administrative",
    "water":         "Water",
    "land":          "Land & terrain",
    "built_social":  "Built & social",
    "unresolved":    "Unresolved",
    "simplex":       "Simplex (no suffix)",
}

# simplex and unresolved are both neutrals, so they are exempt from the chromatic gate,
# but they must still be told apart from each other:
#   light  #4f4f4c vs #8a8a86  normal-vision dE 20.6  (>=15)  contrast 8.01:1
#   dark   #c2c2ba vs #7e7e7a  normal-vision dE 22.0  (>=15)  contrast 9.72:1

SURFACE = {"light": "#fcfcfb", "dark": "#1a1a19"}


def srgb(c):
    c = max(0.0, min(1.0, c))
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def oklch_hex(L, C, H):
    h = math.radians(H)
    a, b = C * math.cos(h), C * math.sin(h)
    l_ = L + 0.3963377774 * a + 0.2158037573 * b
    m_ = L - 0.1055613458 * a - 0.0638541728 * b
    s_ = L - 0.0894841775 * a - 1.2914855480 * b
    r = 4.0767416621 * l_**3 - 3.3077115913 * m_**3 + 0.2309699292 * s_**3
    g = -1.2684380046 * l_**3 + 2.6097574011 * m_**3 - 0.3413193965 * s_**3
    bb = -0.0041960863 * l_**3 - 0.7034186147 * m_**3 + 1.7076147010 * s_**3
    out = []
    for c in (r, g, bb):
        c = srgb(c)
        if c < -0.002 or c > 1.002:
            return None
        out.append(int(round(max(0.0, min(1.0, c)) * 255)))
    return "#%02x%02x%02x" % tuple(out)


def measured_L(hexstr):
    """OKLCH L of a rendered hex — after gamut clipping and 8-bit quantisation."""
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = (lin(int(hexstr[i:i + 2], 16)) for i in (1, 3, 5))
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (max(0.0, x) ** (1 / 3) for x in (l, m, s))
    return 0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_


def step_at(target_L, hue):
    """Highest-chroma in-gamut colour whose MEASURED L lands on target.

    Naively feeding L,C into the OKLCH->sRGB conversion and clamping produces
    uneven steps, because out-of-gamut requests get clipped and the clipping
    moves lightness. Backing chroma off until the rendered hex actually measures
    the requested L is what keeps the ramp monotone with even spacing.
    """
    best = None
    C = 0.20
    while C >= 0.04:
        hx = oklch_hex(target_L, C, hue)
        if hx is not None and abs(measured_L(hx) - target_L) <= 0.004:
            best = hx
            break
        C -= 0.005
    if best is None:                       # fall back to nearest achievable
        C = 0.06
        best = oklch_hex(target_L, C, hue) or oklch_hex(target_L, 0.04, hue)
    return best


def ramp(hue, mode):
    """Ordinal ramp: even MEASURED lightness steps, adjacent dL >= 0.06."""
    lo, hi = (0.77, 0.40) if mode == "light" else (0.82, 0.44)
    return [step_at(lo + (hi - lo) * i / (SHADES - 1), hue) for i in range(SHADES)]


def main():
    os.makedirs(BUILD, exist_ok=True)
    payload = {
        "surface": SURFACE,
        "family_base": FAMILY_BASE,
        "semantic": SEMANTIC,
        "semantic_label": SEMANTIC_LABEL,
        "shades": {m: {f: ramp(h, m) for f, h in FAMILY_HUE.items()} for m in ("light", "dark")},
        "shade_count": SHADES,
        "note": "family hues gated all-pairs; within-family shades are ordinal, not categorical",
    }
    with open(os.path.join(BUILD, "palette.json"), "w") as fh:
        json.dump(payload, fh, indent=1)
    print("wrote 03_Build/palette.json")
    for m in ("light", "dark"):
        print("\n%s" % m)
        for f in FAMILY_HUE:
            print("  %-7s base %s  ramp %s" % (f, FAMILY_BASE[m][f], " ".join(payload["shades"][m][f])))


if __name__ == "__main__":
    main()
