#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ---------------------------------------------------------------------------
# ARCHIVED 2026-09-22 (batch H7a) — DO NOT MAINTAIN.
#
# This tool reads the gallery band's heading (line ~181) as part of its data-
# layer regression. Batch H7a deleted that heading, so this tool now fails on
# any capture taken from H7a onward. That failure is expected and is not a
# regression.
#
# It is left byte-for-byte as it was, on purpose. A gate edited to agree with
# the change it was written to validate stops being a gate; the assertion it
# made at the time is the honest record, and it is the assertion that dates it.
# Its job belongs to tools/b2d_h7_gate.py from batch H7a on.
# ---------------------------------------------------------------------------
"""Batch 2D Step 2 — data-layer regression (items 4, 5, 6 of the plan).

The confinement proof already makes a byte-level claim about everything
outside the gallery band. This checks the consumers that could plausibly have
been disturbed, by name, so a failure points at the thing that broke:

  4. JSON-LD — every <script type="application/ld+json"> block on all 47 pages
     is parsed and compared as data. The dosage pages' Product schema must
     still carry no `additionalProperty`; the gallery emits no JSON-LD at all.
  5. K2 — the `.sf-formulas-data` mirror is parsed and compared value by value
     plus its three labelled sections. The gallery deliberately emits no K2.
  6. Render counts — figure.sf-gallery__slide / [hidden] frames /
     .sf-gallery__thumb (must be 0 server-side: JS derives it) / <h2> count,
     and the Batch 2D Step 1 actives totals, which must not move.

    python3 tools/b2d_s2_check.py <baseline-dir> <candidate-dir>
"""

import json
import os
import re
import sys

SLUGS = ["soft-chews", "tablets", "powders", "pastes",
         "drops", "liquids", "fish-oil", "dental-chews"]

# From tools/b2d1_parser_dryrun.php §4 — Batch 2D Step 1's own numbers, which
# the gallery batch must leave alone.
ACTIVES = {
    "soft-chews":   (4, 24, 8),
    "tablets":      (3, 18, 7),
    "powders":      (3, 10, 3),
    "pastes":       (2, 9, 4),
    "drops":        (2, 6, 2),
    "liquids":      (2, 11, 6),
    "fish-oil":     (2, 6, 8),
    "dental-chews": (3, 15, 5),
}

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                            "sinofresh-theme", "templates")

LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
K2 = re.compile(r'<script type="application/json" class="sf-formulas-data">(.*?)</script>', re.S)

results = []


def walk_typed(node, out):
    """Collect every dict carrying an @type, at any nesting depth.

    A JSON-LD block is not always a bare list of nodes: the site also emits the
    `{"@context":…, "@graph":[…]}` wrapper, and one block may hold several
    independent nodes. Iterating `parsed[0]` therefore sometimes iterates a
    dict's keys, which silently turns strings into "nodes".
    """
    if isinstance(node, list):
        for x in node:
            walk_typed(x, out)
    elif isinstance(node, dict):
        if node.get("@type"):
            out.append(node)
        for v in node.values():
            walk_typed(v, out)
    return out


def products_on(page):
    """Every Product node on a rendered page, in document order."""
    out = []
    for blob in LD.findall(page):
        walk_typed(json.loads(blob), out)
    return [o for o in out if o.get("@type") == "Product"]


def check(name, expected, actual, ok=None):
    if ok is None:
        ok = expected == actual
    results.append(ok)
    print("  [%s] %-58s expect=%r got=%r"
          % ("PASS" if ok else "FAIL", name, expected, actual))


def read(d, name):
    return open(os.path.join(d, name + ".html"), encoding="utf-8", errors="replace").read()


def pages(d):
    return sorted(f[:-5] for f in os.listdir(d) if f.endswith(".html"))


# The fetcher names a render after its URL path: /products/soft-chews/ becomes
# products-soft-chews.html. Slug alone ("soft-chews") is not a filename.
def page_of(slug):
    return "products-%s" % slug


def main():
    if len(sys.argv) < 3:
        print(__doc__)
        return 2
    base, cand = sys.argv[1], sys.argv[2]

    names = pages(cand)
    print("  pages: %d in %s / %d in %s" % (len(names), cand, len(pages(base)), base))
    print()

    # ---------------------------------------------------------------- 4. JSON-LD
    types = {}
    ld_diff = []
    for n in names:
        a, b = read(base, n), read(cand, n)
        la = [json.loads(x) for x in LD.findall(a)]
        lb = [json.loads(x) for x in LD.findall(b)]
        if la != lb:
            ld_diff.append(n)
        for it in walk_typed(lb, []):
            t = it["@type"]
            t = t[0] if isinstance(t, list) else t
            types[t] = types.get(t, 0) + 1
    check("JSON-LD deep-equal on every page (%d pages)" % len(names), [], ld_diff)
    print("       @type inventory: %s" % ", ".join(
        "%s x%d" % (k, v) for k, v in sorted(types.items())))

    # --------------------------------------------------- 4b. K6 four-tuple
    print()
    for slug in SLUGS:
        page = read(cand, page_of(slug))
        tpl = open(os.path.join(TEMPLATE_DIR, "page-%s.html" % slug),
                   encoding="utf-8").read()
        products = products_on(page)
        tup = (
            len(products),
            # Step 1's table emits <dt>/<dd>; the K6 parser reads the template
            # file and matches <span class="sf-spec-term">, so it must stay empty
            any("additionalProperty" in p for p in products),
            'class="sf-spec-term"' in page,
            '<span class="sf-spec-term">' in page,
            "sf-spec-term" in tpl,
        )
        check("K6 product schema tuple %s" % slug, (1, False, True, False, False), tup)

    # -------------------------------------------------------------------- 5. K2
    print()
    k2_bad, k2_sections = [], {}
    for n in names:
        ma, mb = K2.search(read(base, n)), K2.search(read(cand, n))
        if (ma is None) != (mb is None):
            k2_bad.append(n + ":presence")
            continue
        if ma is None:
            continue
        da, db = json.loads(ma.group(1)), json.loads(mb.group(1))
        if da != db:
            k2_bad.append(n + ":value")
            continue
        secs = db.get("sections") if isinstance(db, dict) else None
        if isinstance(secs, list):
            labels = [s.get("label") for s in secs]
            empties = [s.get("label") for s in secs if not str(s.get("value", "")).strip()]
            k2_sections[n] = (len(secs), labels, empties)
    check("K2 .sf-formulas-data identical value-by-value", [], k2_bad)
    with_k2 = [n for n, v in k2_sections.items() if v[1]]
    if with_k2:
        n0 = with_k2[0]
        check("K2 labelled sections on %s" % n0, (3, True),
              (k2_sections[n0][0], not k2_sections[n0][2]))
        print("       labels: %s" % k2_sections[n0][1])

    # --------------------------------------------------------- 6. render counts
    print()
    gallery_rows = []
    for slug in SLUGS + ["zh-products-soft-chews"]:
        h = read(cand, slug if slug.startswith("zh-") else page_of(slug))
        slides = len(re.findall(r'<figure class="sf-gallery__slide"', h))
        hidden = len(re.findall(r'<figure class="sf-gallery__slide"[^>]*\shidden>', h))
        thumbs = len(re.findall(r"sf-gallery__thumb", h))
        h2 = len(re.findall(r"<h2\b", h))
        title = re.search(r'<h2 class="sf-gallery__title">(.*?)</h2>', h)
        gallery_rows.append((slug, slides, hidden, thumbs, h2,
                             title.group(1) if title else "-"))
    slides_ok = all(r[1] == 4 for r in gallery_rows)
    hidden_ok = all(r[2] == 3 for r in gallery_rows)
    thumbs_ok = all(r[3] == 0 for r in gallery_rows)
    h2_base = {n: len(re.findall(r"<h2\b", read(base, page_of(n)))) for n in SLUGS}
    h2_ok = all(r[4] == h2_base[r[0].replace("zh-products-", "")] + 1
                for r in gallery_rows)
    check("figure.sf-gallery__slide == 4 on all 9 pages", True, slides_ok)
    check("hidden frames == 3 on all 9 pages", True, hidden_ok)
    check("sf-gallery__thumb == 0 server-side (JS-derived)", True, thumbs_ok)
    check("<h2> count == baseline + 1", True, h2_ok)
    for r in gallery_rows:
        print("       %-26s slides=%d hidden=%d thumbs=%d h2=%d  h2#1=%s"
              % (r[0], r[1], r[2], r[3], r[4], r[5]))

    print()
    for slug in SLUGS:
        h = read(cand, page_of(slug))
        seg = h[h.index('id="actives"'):] if 'id="actives"' in h else ""
        got = (len(re.findall(r'sf-actives__item', seg)),
               len(re.findall(r'sf-actives__pill', seg)),
               len(re.findall(r'sf-spec-row', seg)))
        check("Step 1 actives counts %s (items,pills,rows)" % slug, ACTIVES[slug], got)

    print()
    totals = (sum(v[0] for v in ACTIVES.values()),
              sum(v[1] for v in ACTIVES.values()),
              sum(v[2] for v in ACTIVES.values()))
    check("Step 1 totals across the eight pages", (21, 99, 43), totals)

    print("\n%s  data layer: %d/%d checks passed"
          % ("PASS" if all(results) else "FAIL", sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
