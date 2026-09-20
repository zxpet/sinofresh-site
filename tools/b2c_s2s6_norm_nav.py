#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch2C Step2 sub-item 6 — normalise the one live-only difference.

The Products dropdown gained an item:

  <!-- wp:navigation-link {"label":"All Formulas","url":"/formulas/","kind":"custom"} /-->

That item lives in the DATABASE (`wp_navigation` post 16, edited in the Site
Editor), not in the theme. A pre-flight theme swap therefore cannot carry it:
the pre-flight capture was taken before the edit, so every live page is ~196
bytes longer than its pre-flight twin — in the header, dozens of kilobyte
before anything this batch touched.

Removing it here is the same kind of move as folding the theme directory name:
it accounts for a difference that has nothing to do with the change under test.
The tool refuses to guess — it deletes the exact <li> and reports how many times
it fired, so a page that silently lost its navigation is a FAIL, not a SAME.

  python3 tools/b2c_s2s6_norm_nav.py <in-dir> <out-dir>
"""

import os
import re
import sys

# The rendered <li> as WordPress prints it (note the double space before href —
# it comes from the block's serialised attributes). On /zh/ pages TranslatePress
# rewrites the href to /zh/formulas/, so the path is matched with the optional
# language prefix.
LI = (r'<li class="wp-block-navigation-item wp-block-navigation-link">'
      r'<a class="wp-block-navigation-item__content"  href="/(?:zh/)?formulas/">'
      r'<span class="wp-block-navigation-item__label">All Formulas</span></a></li>')
PATTERN = re.compile(LI)

# Also seen on /zh/ pages: TranslatePress adds no wrapper here, but the trailing
# whitespace WordPress emits around a block can differ, so eat an optional run.
TRAILING = re.compile(LI + r'\n?')


def main():
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    src, dst = sys.argv[1], sys.argv[2]
    os.makedirs(dst, exist_ok=True)
    bad = 0
    names = [n for n in sorted(os.listdir(src)) if n.endswith(".html")]
    for name in names:
        raw = open(os.path.join(src, name), encoding="utf-8").read()
        out, hits = TRAILING.subn("", raw)
        ok = hits == 1
        if not ok:
            bad += 1
        print(f"  [{'PASS' if ok else 'FAIL'}] {name[:-5]:<42} nav item removed x{hits}")
        open(os.path.join(dst, name), "w", encoding="utf-8").write(out)
    print(f"\n{'PASS' if bad == 0 else 'FAIL'}  {len(names)} pages, {bad} page(s) without exactly one item")
    return 0 if bad == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
