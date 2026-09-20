#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch2C Step2 sub-item 5 — targeted evidence for the eight dosage pages.

Reads two captures of the same 34 URLs (a pre-flight render of the theme
WITHOUT the change, and one WITH it) and answers, per page:

  1. the outline button exists, exactly once, points at /formulas/
  2. all eight pages carry the IDENTICAL anchor markup and wording
  3. it sits at the end of the formula section: after the last card, before
     that section's </section>, with no other block between
  4. the card count and card order are unchanged (same data-formula sequence)
  5. the whole page is byte-identical to the baseline once the new paragraph is
     removed (see b2c_s2s5_norm.py) — run separately
  6. every <script type="application/ld+json"> blob is unchanged, and the new
     anchor never lands inside JSON-LD

  python3 tools/b2c_s2s5_check.py <baseline-dir> <candidate-dir>

Exit code = number of failures.
"""

import re
import sys

FORMS = ["soft-chews", "tablets", "powders", "pastes",
         "drops", "liquids", "fish-oil", "dental-chews"]

ANCHOR = re.compile(r'<a class="sf-explore__btn" href="/formulas/">(.*?)</a>')
# on a dosage page the card carries only data-sf-form; the card's identity and
# its position in the grid are read off the K1 button's data-formula.
CARD = re.compile(r'<article class="sf-fcard" data-sf-form="([^"]*)"')
NAME = re.compile(r'data-formula="([^"]*)"')
LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)

fails = []


def check(name, ok, detail=""):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name:<58} {detail}")
    if not ok:
        fails.append(name)


def read(d, slug):
    return open(f"{d}/{slug}.html", encoding="utf-8").read()


base_dir, cand_dir = sys.argv[1], sys.argv[2]
anchors, pages = {}, {}

for form in FORMS:
    slug = f"products-{form}"
    b, c = read(base_dir, slug), read(cand_dir, slug)
    pages[slug] = c

    print(f"\n=== /products/{form}/ ===")
    btns = re.findall(r'<a class="sf-explore__btn" href="([^"]*)">', c)
    check("exactly two outline buttons: /products/ + /formulas/",
          sorted(btns) == ["/formulas/", "/products/"], f"targets={btns}")

    m = ANCHOR.search(c)
    check("anchor found, wording", bool(m), repr(m.group(1) if m else None))
    if m:
        anchors[slug] = m.group(0)

    check("no /formulas/ outline button in the baseline", "/formulas/" not in
          "".join(re.findall(r'<a class="sf-explore__btn" href="([^"]*)">', b)))

    i_anchor = c.find('<a class="sf-explore__btn" href="/formulas/"')
    i_card = c.rindex("</article>")
    i_sect = c.index("</section>", i_card)
    check("anchor sits after the last card, inside that section",
          i_card < i_anchor < i_sect, f"card={i_card} anchor={i_anchor} section={i_sect}")
    between = c[i_card:i_anchor]
    check("nothing but whitespace/markup close between card and anchor",
          "<!-- wp:" not in between and "<article" not in between)

    cb, cc = CARD.findall(b), CARD.findall(c)
    check("card count unchanged", len(cb) == len(cc), f"{len(cb)} -> {len(cc)}")
    check("card order (data-sf-form) unchanged", cb == cc, f"{cc}")

    nb, nc = NAME.findall(b), NAME.findall(c)
    check("card count (K1 data-formula) unchanged", len(nb) == len(nc),
          f"{len(nb)} -> {len(nc)}")
    check("card title order byte-identical", nb == nc, f"{[x[:22] for x in nc]}")

    ldb, ldc = LD.findall(b), LD.findall(c)
    check("JSON-LD blobs count unchanged", len(ldb) == len(ldc), f"{len(ldb)} -> {len(ldc)}")
    check("JSON-LD blobs byte-identical", ldb == ldc)
    check("anchor not inside any JSON-LD blob",
          all('sf-explore__btn' not in blob for blob in ldc))

    types = re.findall(r'"@type"\s*:\s*"([^"]+)"', "".join(ldc))
    check("JSON-LD @types unchanged",
          types == re.findall(r'"@type"\s*:\s*"([^"]+)"', "".join(ldb)), ",".join(types))

print("\n=== 8 页文案与标记完全一致 ===")
uniq = set(anchors.values())
check("one single anchor markup across the eight pages", len(uniq) == 1,
      repr(next(iter(uniq)) if uniq else None))
check("all eight pages recorded an anchor", len(anchors) == 8)

print(f"\n{'PASS' if not fails else 'FAIL'}  sub-item 5: {len(fails)} failure(s)"
      + (f" -> {fails}" if fails else ""))
sys.exit(len(fails))
