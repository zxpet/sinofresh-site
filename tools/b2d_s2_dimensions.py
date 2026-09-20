#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D Step 2 — the declared size table against the real pixels (item 7).

Every other image on the dosage pages carries a stale `width="800"
height="600"` on top of a 720x720 file — copied once and never revisited. The
gallery must not repeat that, so its dimensions are declared in
`sinofresh_formula_gallery_slots()` and this script holds them to the
photographs' real sizes, read with getimagesize on the server that stores them.

It compares what the RENDERED page says (`width`/`height` on each gallery
`<img>`) against `getimagesize` for the same file, so the check covers the
whole path — table, shortcode and markup — rather than the table alone.

    python3 tools/b2d_s2_dimensions.py <render-dir> [--ssh root@HOST]

Exit 0 when every slot matches. Needs ssh (the images live on the dev box, not
in the repo) — pass --ssh '' to skip collection and use --dims instead.
"""

import argparse
import json
import os
import re
import subprocess
import sys

SLUGS = ["soft-chews", "tablets", "powders", "pastes",
         "drops", "liquids", "fish-oil", "dental-chews"]

# <figure class="sf-gallery__slide" …><img src="…" alt="…" width="W" height="H" …
SLIDE_IMG = re.compile(
    r'<figure class="sf-gallery__slide"[^>]*>\s*<img\s[^>]*?src="([^"]+)"[^>]*?'
    r'width="(\d+)"\s+height="(\d+)"', re.S)

DEFAULT_SSH = "root@65.49.215.152"

# The program is piped to `php` on stdin with the file list baked into the
# source, so no argument, quote, `$` or `;` has to survive the remote shell.
#
# `ssh host php -r '<code>' '<json>'` cannot work: ssh joins its arguments into
# a single shell word, so the remote shell re-parses the PHP. The symptom is a
# bare "syntax error near unexpected token" from bash, pointing at PHP that was
# never the problem.
REMOTE_PHP = r"""<?php
$d = "/var/www/dev.zxpet.com/public/wp-content/uploads/";
$names = __NAMES__;
$out = [];
foreach ($names as $n) {
    if (!preg_match('#^[A-Za-z0-9._-]+$#', $n)) { $out[$n] = null; continue; }
    $hits = glob($d . "*/*/" . $n);
    if (!$hits) { $hits = glob($d . $n); }
    if (!$hits) { $out[$n] = null; continue; }
    $i = @getimagesize(end($hits));
    $out[$n] = $i ? [$i[0], $i[1]] : null;
}
echo json_encode($out);
"""


def collect_dims(names, host):
    """{basename: [w, h]} straight from getimagesize on the dev box."""
    program = REMOTE_PHP.replace("__NAMES__", json.dumps(sorted(names)))
    res = subprocess.run(["ssh", "-o", "ConnectTimeout=20", host, "php"],
                         input=program, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("ssh failed: %s" % (res.stderr.strip() or res.stdout.strip()))
    return json.loads(res.stdout)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", help="directory of rendered pages")
    ap.add_argument("--ssh", default=DEFAULT_SSH,
                    help="host to read getimagesize from ('' to use --dims)")
    ap.add_argument("--dims", default=None, help="pre-collected JSON {basename: [w,h]}")
    args = ap.parse_args()

    # Every gallery image the render emits, per page.
    found = {}          # basename -> set of (w, h) strings seen in markup
    per_page = {}
    for slug in SLUGS + ["zh-products-soft-chews"]:
        base = slug if slug.startswith("zh-") else "products-%s" % slug
        path = os.path.join(args.dir, base + ".html")
        if not os.path.exists(path):
            print("  [SKIP] %s not in %s" % (base, args.dir))
            continue
        text = open(path, encoding="utf-8", errors="replace").read()
        hits = SLIDE_IMG.findall(text)
        per_page[slug] = [(u.rsplit("/", 1)[-1], w, h) for u, w, h in hits]
        for base_, w, h in per_page[slug]:
            found.setdefault(base_, set()).add((w, h))

    print("  pages scanned: %d   distinct files: %d"
          % (len(per_page), len(found)))

    dims = json.load(open(args.dims)) if args.dims else collect_dims(sorted(found), args.ssh)

    bad = 0
    print("\n  %-26s %-12s %-12s %s" % ("file", "declared", "real", "verdict"))
    for base in sorted(found):
        declared = sorted(found[base])
        real = dims.get(base)
        real_s = "%dx%d" % (real[0], real[1]) if real else "?"
        ok = bool(real) and len(declared) == 1 and declared[0] == (str(real[0]), str(real[1]))
        if not ok:
            bad += 1
        print("  %-26s %-12s %-12s %s"
              % (base, "/".join("%sx%s" % d for d in declared), real_s,
                 "OK" if ok else "*** MISMATCH ***"))

    # Every dosage page must carry exactly four frames, one per slot, and slot
    # 1 must be that page's own photo — that is what makes the band per-page
    # rather than four identical stock frames.
    print()
    for slug in sorted(per_page):
        frames = per_page[slug]
        expected_slot1 = slug.replace("zh-products-", "") + ".webp"
        ok = len(frames) == 4 and frames[0][0] == expected_slot1
        if not ok:
            bad += 1
        print("  [%s] %-26s frames=%d slot1=%s (want %s)"
              % ("PASS" if ok else "FAIL", slug, len(frames),
                 frames[0][0] if frames else "-", expected_slot1))

    print("\n%s  dimension table vs server pixels: %d problem(s)"
          % ("PASS" if bad == 0 else "FAIL", bad))
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
