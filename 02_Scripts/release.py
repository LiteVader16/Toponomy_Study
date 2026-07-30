#!/usr/bin/env python3
"""
release.py — cut a new version of the site.

Copies the current runtime files to the repo root (what GitHub Pages serves) and
snapshots the same set into archive/v<N>_<YYYYMMDD>/ so every published version stays
retrievable. Version number is inferred from the highest existing archive folder.

Archived per version: index.html, data.json, palette.json, lexicon.json.
index.html and data.json are the two you asked for; palette.json and lexicon.json come
along because without them an archived index.html will not render -- an archive you
cannot run is not an archive.

Usage:
  python3 02_Scripts/release.py --from ../path/to/04_App      # stage + archive
  python3 02_Scripts/release.py --from ../path/to/04_App -n   # dry run
"""
import argparse, datetime, os, re, shutil, sys

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ARCHIVE = os.path.join(REPO, "archive")
RUNTIME = ["index.html", "data.json", "palette.json", "lexicon.json"]


def next_version():
    if not os.path.isdir(ARCHIVE):
        return 1
    seen = [int(m.group(1)) for d in os.listdir(ARCHIVE)
            for m in [re.match(r"v(\d+)_", d)] if m]
    return (max(seen) + 1) if seen else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--from", dest="src", required=True, help="folder holding the built site")
    ap.add_argument("-n", "--dry-run", action="store_true")
    ap.add_argument("--version", type=int, help="override version number")
    a = ap.parse_args()

    src = os.path.abspath(os.path.expanduser(a.src))
    missing = [f for f in RUNTIME if not os.path.exists(os.path.join(src, f))]
    if missing:
        sys.exit("missing in %s: %s" % (src, ", ".join(missing)))

    v = a.version or next_version()
    stamp = datetime.date.today().strftime("%Y%m%d")
    dest = os.path.join(ARCHIVE, "v%d_%s" % (v, stamp))

    print("version   : v%d" % v)
    print("source    : %s" % src)
    print("archive   : %s" % os.path.relpath(dest, REPO))
    print("root      : %s  (GitHub Pages serves this)" % REPO)
    if a.dry_run:
        print("\n[dry run] nothing written")
        return
    if os.path.exists(dest):
        sys.exit("archive %s already exists — pass --version to override" % dest)

    os.makedirs(dest)
    for f in RUNTIME:
        shutil.copy2(os.path.join(src, f), os.path.join(REPO, f))   # deploy
        shutil.copy2(os.path.join(src, f), os.path.join(dest, f))   # archive
        print("  copied %s" % f)

    print("\nNow commit:")
    print('  git add -A && git commit -m "Release v%d" && git push' % v)


if __name__ == "__main__":
    main()
