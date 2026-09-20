#!/usr/bin/env python3
"""Report exactly which enqueued asset versions moved between two renders.

Bumping a stylesheet's enqueue version rewrites its <link href> on EVERY page,
so a whole-site byte comparison can never be SAME after a version bump — and
blanket-masking "?ver=" would also hide an accidental version change on some
other asset. This tool answers the narrow question instead: on which pages did
which asset's cache token change, and did anything else change?

    b2c_s2_ver_inventory.py <dirLive> <dirNew>

Prints one line per asset whose token moved (with the pages it moved on), then
a summary. Exit code 0 when at least one token moved and every moved token is
listed (i.e. the report is non-empty), 1 when nothing moved — so the caller
notices if the check silently matched nothing.
"""

import os
import re
import sys
from collections import defaultdict

# WordPress quotes this markup with single quotes (<link rel='stylesheet'
# href='…?ver=2.10.44' />), so both quote styles have to be matched.
PAIR = re.compile(r'''(?:href|src)=["']([^"']+?)\?ver=([^"'&]+)''')


def inventory(directory):
    """{page: {(asset, ver), ...}} and {asset: {ver: [pages]}}"""
    pages = {}
    versions = defaultdict(lambda: defaultdict(list))
    for name in sorted(os.listdir(directory)):
        if not name.endswith(".html"):
            continue
        text = open(os.path.join(directory, name), encoding="utf-8", errors="replace").read()
        found = set()
        for url, ver in PAIR.findall(text):
            asset = url.rstrip("/").rsplit("/", 1)[-1] or url
            found.add((asset, ver))
            versions[asset][ver].append(name[:-5])
        pages[name[:-5]] = found
    return pages, versions


def main():
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    live, new = sys.argv[1], sys.argv[2]
    live_pages, live_ver = inventory(live)
    new_pages, new_ver = inventory(new)

    assets = sorted(set(live_ver) | set(new_ver))
    moved = []
    for asset in assets:
        lv = ",".join(sorted(live_ver.get(asset, {}))) or "-"
        nv = ",".join(sorted(new_ver.get(asset, {}))) or "-"
        if lv != nv:
            pages_live = set()
            pages_new = set()
            for ver, ps in live_ver.get(asset, {}).items():
                pages_live |= {p for p in ps}
            for ver, ps in new_ver.get(asset, {}).items():
                pages_new |= {p for p in ps}
            where = sorted(pages_new | pages_live)
            moved.append(asset)
            print(f"  {asset:<28} {lv:>10} -> {nv:<10} on {len(where)} page(s): "
                  f"{', '.join(where[:4])}{' …' if len(where) > 4 else ''}")

    # Pages whose ASSET SET (ignoring versions) differs = a script/style
    # appearing or disappearing, which no version bump explains.
    structural = []
    for page in sorted(set(live_pages) | set(new_pages)):
        la = {a for a, _ in live_pages.get(page, set())}
        na = {a for a, _ in new_pages.get(page, set())}
        if la != na:
            structural.append((page, sorted(na - la), sorted(la - na)))

    print(f"\n  assets compared: {len(assets)}   tokens moved: {len(moved)}")
    if structural:
        print("  !! asset set changed (not explained by a version bump):")
        for page, added, removed in structural:
            print(f"     {page}: +{added} -{removed}")
    else:
        print("  asset set identical on every page")
    return 0 if moved else 1


if __name__ == "__main__":
    sys.exit(main())
