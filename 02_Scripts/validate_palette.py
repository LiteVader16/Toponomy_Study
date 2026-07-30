#!/usr/bin/env python3
"""
validate_palette.py — Python port of the dataviz skill's palette validator.
(The bundled validator is Node; node is not installed in this environment.)

Implements the computable checks:
  2. Lightness band per mode   OKLCH L 0.43-0.77 light / 0.48-0.67 dark
  3. Chroma floor              OKLCH C >= 0.10
  4. CVD separation            OKLab dE x100, protanopia + deuteranopia,
                               Machado-Oliveira-Fernandes 2009 @ severity 1.0
                               target >= 8, floor >= 6; normal-vision floor >= 15
  5. Contrast vs surface       WCAG >= 3:1 for marks

  --ordinal switches to ramp checks: monotone L, adjacent dL >= 0.06,
  light-end contrast >= 2.0:1, single hue.

Usage:
  python3 validate_palette.py "#hex,#hex,..." [--mode light|dark] [--surface #hex]
                              [--pairs adjacent|all] [--ordinal] [--label "name"]
"""
import sys, math, itertools

# ---------------------------------------------------------------- colour maths
def hex2rgb(h):
    h = h.strip().lstrip("#")
    return tuple(int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


def srgb_to_linear(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def linear_to_srgb(c):
    c = max(0.0, min(1.0, c))
    return c * 12.92 if c <= 0.0031308 else 1.055 * (c ** (1 / 2.4)) - 0.055


def linrgb(h):
    return tuple(srgb_to_linear(c) for c in hex2rgb(h))


def oklab(rgb_lin):
    r, g, b = rgb_lin
    l = 0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b
    m = 0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b
    s = 0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b
    l_, m_, s_ = (max(0.0, v) ** (1 / 3) for v in (l, m, s))
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def oklch(h):
    L, a, b = oklab(linrgb(h))
    return L, math.hypot(a, b), math.degrees(math.atan2(b, a)) % 360


# Machado, Oliveira & Fernandes (2009), severity 1.0, applied in linear RGB
CVD = {
    "protanopia":   ((0.152286, 1.052583, -0.204868),
                     (0.114503, 0.786281,  0.099216),
                     (-0.003882, -0.048116, 1.051998)),
    "deuteranopia": ((0.367322, 0.860646, -0.227968),
                     (0.280085, 0.672501,  0.047413),
                     (-0.011820, 0.042940, 0.968881)),
}


def simulate(rgb_lin, kind):
    m = CVD[kind]
    return tuple(sum(m[i][j] * rgb_lin[j] for j in range(3)) for i in range(3))


def dE(c1, c2):
    """Euclidean distance in OKLab x100, on already-linear rgb triples."""
    a, b = oklab(c1), oklab(c2)
    return 100 * math.dist(a, b)


def relative_luminance(h):
    r, g, b = linrgb(h)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = relative_luminance(a), relative_luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


# ---------------------------------------------------------------- checks
def run(palette, mode, surface, pairs, ordinal, label):
    band = (0.43, 0.77) if mode == "light" else (0.48, 0.67)
    print("\n" + "=" * 74)
    print("%s  [%s mode, surface %s, pairs=%s%s]"
          % (label or "palette", mode, surface, pairs, ", ordinal" if ordinal else ""))
    print("=" * 74)
    fails, warns = [], []

    if ordinal:
        Ls = [oklch(h)[0] for h in palette]
        mono = all(Ls[i] > Ls[i + 1] for i in range(len(Ls) - 1)) or \
               all(Ls[i] < Ls[i + 1] for i in range(len(Ls) - 1))
        print("  monotone lightness     : %s" % ("PASS" if mono else "FAIL"))
        if not mono:
            fails.append("monotone L")
        worst_dl = min(abs(Ls[i] - Ls[i + 1]) for i in range(len(Ls) - 1))
        ok = worst_dl >= 0.06
        print("  adjacent dL >= 0.06    : %s (worst %.3f)" % ("PASS" if ok else "FAIL", worst_dl))
        if not ok:
            fails.append("adjacent dL")
        hues = [oklch(h)[2] for h in palette]
        spread = max(hues) - min(hues)
        print("  single hue (spread)    : %s (%.0f deg)"
              % ("PASS" if spread <= 40 else "WARN", spread))
        near = max(palette, key=lambda h: contrast(h, surface)) if mode == "dark" \
            else min(palette, key=lambda h: contrast(h, surface))
        c = contrast(near, surface)
        ok = c >= 2.0
        print("  surface-end contrast   : %s (%.2f:1, %s)" % ("PASS" if ok else "FAIL", c, near))
        if not ok:
            fails.append("light-end contrast")
        print("\n  %s" % ("OK" if not fails else "FAILED: " + ", ".join(fails)))
        return not fails

    print("  %-9s %-7s %-7s %-7s %-7s" % ("hex", "L", "C", "band", "contrast"))
    for h in palette:
        L, C, _ = oklch(h)
        cr = contrast(h, surface)
        bt = "ok" if band[0] <= L <= band[1] else "OUT"
        ct = "ok" if C >= 0.10 else "LOW"
        cc = "ok" if cr >= 3.0 else "warn"
        print("  %-9s %-7.3f %-7.3f %-7s %.2f:1 %s" % (h, L, C, bt, cr, cc))
        if bt == "OUT":
            warns.append("%s L=%.3f outside %s band" % (h, L, mode))
        if ct == "LOW":
            fails.append("%s chroma %.3f < 0.10" % (h, C))
        if cc == "warn":
            warns.append("%s contrast %.2f:1 < 3:1 (needs relief channel)" % (h, cr))

    idx = list(itertools.combinations(range(len(palette)), 2)) if pairs == "all" \
        else [(i, i + 1) for i in range(len(palette) - 1)]

    worst_cvd, worst_cvd_pair, worst_nv, worst_nv_pair = 1e9, None, 1e9, None
    for i, j in idx:
        a, b = linrgb(palette[i]), linrgb(palette[j])
        nv = dE(a, b)
        if nv < worst_nv:
            worst_nv, worst_nv_pair = nv, (palette[i], palette[j])
        for kind in CVD:
            d = dE(simulate(a, kind), simulate(b, kind))
            if d < worst_cvd:
                worst_cvd, worst_cvd_pair = d, (palette[i], palette[j], kind)

    print("\n  worst CVD pair         : dE %.1f  %s vs %s (%s)"
          % (worst_cvd, worst_cvd_pair[0], worst_cvd_pair[1], worst_cvd_pair[2]))
    if worst_cvd >= 8:
        print("                           PASS (>= 8 target)")
    elif worst_cvd >= 6:
        print("                           WARN (6-8 floor; needs secondary encoding)")
        warns.append("CVD dE %.1f in warn band" % worst_cvd)
    else:
        print("                           FAIL (< 6)")
        fails.append("CVD dE %.1f < 6" % worst_cvd)

    print("  worst normal-vision    : dE %.1f  %s vs %s"
          % (worst_nv, worst_nv_pair[0], worst_nv_pair[1]))
    if worst_nv >= 15:
        print("                           PASS (>= 15 floor)")
    else:
        print("                           FAIL (< 15 hard gate)")
        fails.append("normal-vision dE %.1f < 15" % worst_nv)

    print("\n  %s" % ("PASS — no hard failures" if not fails
                      else "FAIL: " + "; ".join(fails)))
    if warns:
        print("  warnings: " + "; ".join(warns))
    return not fails


def main():
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    palette = [c.strip() for c in args[0].split(",") if c.strip()]
    mode, pairs, ordinal, label = "light", "adjacent", False, None
    surface = None
    i = 1
    while i < len(args):
        if args[i] == "--mode":
            mode = args[i + 1]; i += 2
        elif args[i] == "--surface":
            surface = args[i + 1]; i += 2
        elif args[i] == "--pairs":
            pairs = args[i + 1]; i += 2
        elif args[i] == "--label":
            label = args[i + 1]; i += 2
        elif args[i] == "--ordinal":
            ordinal = True; i += 1
        else:
            i += 1
    if surface is None:
        surface = "#fcfcfb" if mode == "light" else "#1a1a19"
    ok = run(palette, mode, surface, pairs, ordinal, label)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
