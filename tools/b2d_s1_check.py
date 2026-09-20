#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D Step 1 — data-layer regression (items 7, 8, 9 of the plan).

The confinement proof already makes a byte-level claim about everything
outside the new band. This script checks the three *data* consumers by name,
so a failure names the thing that broke instead of pointing at an offset:

  7. JSON-LD — every <script type="application/ld+json"> block on the page is
     parsed and compared as data. In particular the dosage pages' Product
     schema must STILL have no `additionalProperty`: the new table emits
     <dt>/<dd>, and the Product parser matches on
     `<span class="sf-spec-term">…</span><span class="sf-spec-value">…</span>`
     read from the template file, so it must stay empty.
  8. K2 — the `.sf-formulas-data` JSON mirror is parsed and its per-formula
     name/slug/form/sections are compared value by value.
  9. Render counts — article.sf-actives__item, li.sf-actives__pill and
     .sf-spec-row inside #actives, against the numbers the dry run predicts.

    python3 tools/b2d_s1_check.py <baseline-dir> <candidate-dir>
"""

import json
import os
import re
import sys

ALL_FORMS = ["soft-chews", "tablets", "powders", "pastes",
             "drops", "liquids", "fish-oil", "dental-chews"]

# form -> (items, pills, analysis rows) — from tools/b2d1_parser_dryrun.php §4
EXPECTED = {
    "soft-chews":   (4, 24, 8),
    "tablets":      (3, 18, 7),
    "powders":      (3, 10, 3),
    "pastes":       (2, 9, 4),
    "drops":        (2, 6, 2),
    "liquids":      (2, 11, 6),
    "fish-oil":     (2, 6, 8),
    "dental-chews": (3, 15, 5),
}

LD = re.compile(r'<script type="application/ld\+json">(.*?)</script>', re.S)
K2 = re.compile(r'<script type="application/json" class="sf-formulas-data">(.*?)</script>', re.S)

results = []


def check(name, expected, actual, ok=None):
    if ok is None:
        ok = expected == actual
    results.append(ok)
    print("  [%s] %-56s expect=%r got=%r"
          % ("PASS" if ok else "FAIL", name, expected, actual))


def read(d, name):
    return open(os.path.join(d, name + ".html"), encoding="utf-8", errors="replace").read()


def ld_blocks(text):
    out = []
    for raw in LD.findall(text):
        try:
            out.append(json.loads(raw))
        except Exception as err:
            out.append({"@type": "PARSE-ERROR", "err": str(err), "raw": raw[:200]})
    return out


def k2_payload(text):
    m = K2.search(text)
    return json.loads(m.group(1)) if m else None


def actives_scope(text):
    """The rendered band, from its marker to the next block comment."""
    i = text.find("<!-- B2D-S1: actives -->")
    if i < 0:
        return ""
    j = text.find("<!-- Block 9: How We Work -->", i)
    return text[i:j if j > 0 else len(text)]


def main():
    base, cand = sys.argv[1], sys.argv[2]
    dosage = ["products-" + f for f in ALL_FORMS]

    print("=== 7) JSON-LD (parsed as data, both sides) ===")
    types_base, types_cand = {}, {}
    for n in sorted(f[:-5] for f in os.listdir(cand) if f.endswith(".html")):
        a, b = ld_blocks(read(base, n)), ld_blocks(read(cand, n))
        types_base[n] = [d.get("@type") for d in a]
        types_cand[n] = [d.get("@type") for d in b]
        if a != b:
            check("JSON-LD deep-equal %s" % n, a, b)
            continue
        for d in b:
            if d.get("@type") == "PARSE-ERROR":
                check("JSON-LD parses %s" % n, "no parse error", d["err"])
    same_types = all(types_base[n] == types_cand[n] for n in types_cand)
    check("JSON-LD blocks deep-equal on every page", True, same_types)
    ALLOWED = {"BreadcrumbList", "FAQPage", "ItemList", "Organization", "Product", "Service"}
    uniq = sorted({t for v in types_cand.values() for t in v})
    check("JSON-LD @type inventory (no parser error)", True, set(uniq) <= ALLOWED)
    print("       inventory: %s" % ", ".join(
        "%s x%d" % (t, sum(v.count(t) for v in types_cand.values())) for t in uniq))
    print("       pages: %d   Product blocks: %d   ItemList blocks: %d"
          % (len(types_cand), sum(v.count("Product") for v in types_cand.values()),
             sum(v.count("ItemList") for v in types_cand.values())))

    print("=== 7b) the eight dosage Product schemas still carry no additionalProperty ===")
    for n in dosage:
        text = read(cand, n)
        blocks = [d for d in ld_blocks(text) if d.get("@type") == "Product"]
        prop = [d.get("additionalProperty") for d in blocks if "additionalProperty" in d]
        # The band does put `class="sf-spec-term"` in the page — on a <dt>. The
        # Product parser must (a) read the template file, and (b) require
        # <span class="sf-spec-term">, so either guard alone keeps it out.
        tmpl = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..",
                            "sinofresh-theme", "templates",
                            "page-%s.html" % n.replace("products-", ""))
        tmpl_has = "sf-spec-term" in open(tmpl, encoding="utf-8").read() \
            if os.path.exists(tmpl) else None
        check("%s: Product blocks / additionalProperty / <span> pattern" % n,
              (1, False, True, False, False),
              (len(blocks), bool(prop),
               'class="sf-spec-term"' in text,
               '<span class="sf-spec-term">' in text,
               tmpl_has))
        if blocks:
            print("       Product name:", blocks[0].get("name"))

    print("=== 8) K2 .sf-formulas-data (parsed, value by value) ===")
    for n in dosage + ["zh-products-soft-chews"]:
        ka, kb = k2_payload(read(base, n)), k2_payload(read(cand, n))
        check("K2 identical %s" % n, ka, kb)
    form = ALL_FORMS
    counts = []
    for f in form:
        p = k2_payload(read(cand, "products-" + f))
        counts.append((f, len(p or [])))
    check("K2 items per form", {f: EXPECTED[f][0] for f in form}, dict(counts))
    fields = "Ingredients,Guaranteed Analysis,Standard Specs"
    ok, bad = True, []
    for f in form:
        for item in (k2_payload(read(cand, "products-" + f)) or []):
            sec = item.get("sections") or []
            labels = [s.get("label") for s in sec]
            if labels != fields.split(",") or any(
                    not str(s.get("value", "")).strip() for s in sec):
                ok = False
                bad.append((item.get("slug"), labels))
    check("K2 sections = 3 labelled pairs, all non-empty (%s)" % fields, True, ok)
    for slug, labels in bad:
        print("       !! %s -> %r" % (slug, labels))

    print("=== 9) the band's render counts ===")
    for f in form:
        scope = actives_scope(read(cand, "products-" + f))
        got = (scope.count('class="sf-actives__item"'),
               scope.count('class="sf-actives__pill"'),
               scope.count('class="sf-spec-row"'))
        check("/products/%s/ items/pills/rows" % f, EXPECTED[f], got)
    z = actives_scope(read(cand, "zh-products-soft-chews"))
    check("/zh/products/soft-chews/ carries the same band",
          EXPECTED["soft-chews"],
          (z.count('class="sf-actives__item"'), z.count('class="sf-actives__pill"'),
           z.count('class="sf-spec-row"')))

    print("=== 9b) no empty <li> / <dd>, no entity mismatch in the band ===")
    for f in form:
        scope = actives_scope(read(cand, "products-" + f))
        check("%s: no empty pill/dd" % f, (0, 0),
              (len(re.findall(r'class="sf-actives__pill">\s*</li>', scope)),
               len(re.findall(r'class="sf-spec-value">\s*</dd>', scope))))
        check("%s: every pill/dd carries text" % f, True,
              all(len(re.sub(r"<[^>]+>", "", m).strip()) > 0
                  for m in re.findall(r'class="sf-actives__pill">(.*?)</li>', scope))
              and all(len(re.sub(r"<[^>]+>", "", m).strip()) > 0
                      for m in re.findall(r'class="sf-spec-value">(.*?)</dd>', scope)))

    print("\n%d/%d checks passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
