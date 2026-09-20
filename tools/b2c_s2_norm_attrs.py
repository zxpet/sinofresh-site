#!/usr/bin/env python3
"""Normalise the differences a pre-flight run is EXPECTED to introduce.

A pre-flight render can never be byte-identical to the live page, for reasons
that have nothing to do with the change under test:

  * the stylesheet's cache-busting token, when the batch bumps a version
    (style.css 2.10.43 -> 2.10.44 rewrites the <link href> on every page);
  * the pre-flight theme's directory name, which appears in every enqueued
    asset URL, because the copy is installed as its own theme so that the
    assets are actually served from it;
  * the two attributes this sub-item adds on purpose.

    b2c_s2_norm_attrs.py <in-dir> <out-dir> [--theme-dir NAME]

writes a normalised copy of every .html in <in-dir> with those removed, so the
ordinary masked comparator can run over the normalised pair. SAME there is the
proof: the only differences between the two renders were the ones accounted
for. Anything else — a moved element, a changed class, a different count —
survives normalisation and still shows up as DIFF.

Nothing is assumed about which token moved: `b2c_s2_ver_inventory.py` reports
that separately (and flags any asset appearing or disappearing), so masking
"?ver=" here cannot hide an accidental version change.

`data-formula` is left alone: the pattern requires `data-form=` to be followed
immediately by a quote, and in `data-formula="…"` it is followed by `ula`.

Pre-flight-only tool; it is not part of the site.
"""

import argparse
import os
import re

LIVE_THEME = "sinofresh-theme"

# (pattern, replacement) applied to both sides
FIXED = (
    (re.compile(r'\s+data-form="[^"]*"'), ""),
    (re.compile(r'\s+data-sf-form="[^"]*"'), ""),
    # the cache-busting token of an enqueued asset
    (re.compile(r'\?ver=[^"&\']+'), "?ver=X"),
)


def main():
    ap = argparse.ArgumentParser(
        description="Strip expected pre-flight differences before a byte comparison.")
    ap.add_argument("src", help="directory of fetched pages")
    ap.add_argument("dst", help="directory to write the normalised copies to")
    ap.add_argument("--theme-dir", default=None,
                    help="pre-flight theme directory name, folded back onto "
                         "sinofresh-theme (e.g. sinofresh-theme-preflight)")
    args = ap.parse_args()

    pairs = list(FIXED)
    if args.theme_dir:
        # The pre-flight theme name reaches the HTML in more than one shape:
        # the asset URLs (/wp-content/themes/<name>/…) and WordPress'
        # wp-theme-<name> body class. Folding every occurrence back onto the
        # live name covers both and anything else WP derives from it.
        pairs.append((re.compile(re.escape(args.theme_dir)), LIVE_THEME))

    os.makedirs(args.dst, exist_ok=True)
    count = 0
    for name in sorted(os.listdir(args.src)):
        if not name.endswith(".html"):
            continue
        raw = open(os.path.join(args.src, name), "rb").read()
        text = raw.decode("utf-8", "surrogateescape")
        for pattern, repl in pairs:
            text = pattern.sub(repl, text)
        out = text.encode("utf-8", "surrogateescape")
        open(os.path.join(args.dst, name), "wb").write(out)
        count += 1
        print(f"  {name}: {len(raw)} -> {len(out)} bytes")
    print(f"{count} file(s) normalised into {args.dst}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
