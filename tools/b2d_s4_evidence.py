#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D Step 4 — evidence for the two edits, as the page renders them.

The gates compare bytes; this reads the live DOM, because three of the claims
are about what a visitor gets rather than about markup:

  * the gallery heading is the formula's name and is the same string the hero
    h1 carries, so the band no longer speaks about the dosage form,
  * the Specification band holds exactly one card, and the Ingredients and
    Guaranteed Analysis that left it are still on the page — inside the
    "Formula & nutrition" band, read back against the pre-change capture so
    "still there" means the same values, not merely some values,
  * the --solo cap is doing something: 560px at 1440, and it does not push the
    page wide at 375.

The browser helpers are the ones b2d_s3_quickcheck.py already uses (ab / ev /
check), so this reads the page the same way the quick check does.

    python3 tools/b2d_s4_evidence.py [--out DIR]
"""
import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2d_s4_confine as S4          # noqa: E402  (the batch's own card parser)
import b2d_s3_confine as S3          # noqa: E402
import b2d_s3_quickcheck as Q        # noqa: E402  (ab / ev / check, one instrument)
import b2d_s2_browser as B2          # noqa: E402  (the consent-banner dismissal)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PAGE = "/formulas/ear-care-drops/"
BASE_CAPTURE = os.path.join(ROOT, "_backup", "b2d-step4-baselines", "base",
                            "formulas__ear-care-drops.html")

MEASURE = """JSON.stringify((function(){
  var h1=document.querySelector('.sf-formula-hero__title');
  var h2=document.querySelector('.sf-gallery__title');
  var sec=document.querySelector('.sf-fdetail');
  var grid=sec?sec.querySelector('.sf-fdetail__grid'):null;
  var cards=sec?sec.querySelectorAll('.sf-fdetail__card'):[];
  var labels=[].slice.call(cards).map(function(c){
      var l=c.querySelector('.sf-fdetail__label'); return l?l.textContent.trim():'?';});
  var vals=[].slice.call(cards).map(function(c){
      var v=c.querySelector('.sf-fdetail__value'); return v?v.textContent.trim():'';});
  var band=document.querySelector('.sf-fdetail-actives');
  var pills=band?[].slice.call(band.querySelectorAll('.sf-actives__pill'))
                  .map(function(e){return e.textContent.trim();}):[];
  var terms=band?[].slice.call(band.querySelectorAll('.sf-spec-term'))
                  .map(function(e){return e.textContent.trim();}):[];
  var dds=band?[].slice.call(band.querySelectorAll('.sf-spec-value'))
                .map(function(e){return e.textContent.trim();}):[];
  var r=grid?grid.getBoundingClientRect():null;
  return {h1:h1?h1.textContent.trim():null, h2:h2?h2.textContent.trim():null,
          gridClass:grid?grid.className:null, nCards:cards.length,
          labels:labels, vals:vals,
          gridWidth:r?Math.round(r.width):null,
          bandPills:pills, bandTerms:terms, bandValues:dds,
          secText:sec?sec.textContent.replace(/\\s+/g,' ').trim():null,
          ready:document.readyState,
          docScrollW:document.documentElement.scrollWidth,
          docClientW:document.documentElement.clientWidth};
})())"""


def base_cards():
    """The two cards' values as the pre-change page printed them."""
    html = S3.normalize(open(BASE_CAPTURE, encoding="utf-8", errors="replace").read())
    grid = S4.GRID_RE.search(html)
    return {lab: val for lab, val, _ in S4.cards_of(grid.group(1))}


def scroll_to(sel):
    Q.ab("eval", "(function(){var el=document.querySelector(%s);"
                 "if(el)el.scrollIntoView({block:'center',behavior:'instant'});})()"
         % json.dumps(sel))
    time.sleep(0.8)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", default=os.path.join(ROOT, "docs", "b2d-step4-shots"))
    args = ap.parse_args(argv)
    os.makedirs(args.out, exist_ok=True)

    wish = base_cards()
    Q.ab("set", "credentials", Q.USER, Q.PASS)
    Q.ab("open", Q.BASE + PAGE)
    time.sleep(2.5)
    Q.ab("set", "viewport", "1440", "900")
    time.sleep(1.0)
    B2.dismiss_cookie_banner()

    m = Q.ev(MEASURE) or {}
    print("=== 1440x900 ===")
    print("       measured:",
          json.dumps({k: v for k, v in m.items() if k not in ("secText",)}, ensure_ascii=False))
    Q.check("the page is loaded at 1440", "complete", m.get("ready"))
    Q.check("the hero h1 is the formula name", "Ear Care Drops", m.get("h1"))
    Q.check("the gallery heading names the formula",
            "A Closer Look at Ear Care Drops", m.get("h2"))
    Q.check("the heading is the h1 with one prefix",
            True, m.get("h2") == "A Closer Look at " + (m.get("h1") or ""))
    Q.check("the heading no longer names the dosage form",
            False, "Production" in (m.get("h2") or ""))

    Q.check("the Specification band holds one card", 1, m.get("nCards"))
    Q.check("and it is Standard Specs", ["Standard Specs"], m.get("labels"))
    Q.check("the surviving card is the pre-change Standard Specs value",
            wish.get("Standard Specs"), (m.get("vals") or [None])[0])
    Q.check("the grid carries the --solo modifier",
            ["sf-fdetail__grid", "sf-fdetail__grid--solo"],
            (m.get("gridClass") or "").split())
    Q.check("the --solo cap measures 560px", 560, m.get("gridWidth"))

    Q.check("Ingredients left the Specification band",
            False, "Ingredients" in (m.get("secText") or ""))
    Q.check("Guaranteed Analysis left the Specification band",
            False, "Guaranteed Analysis" in (m.get("secText") or ""))
    want_pills = [x.strip() for x in wish["Ingredients"].split(",") if x.strip()]
    Q.check("the band still lists every ingredient the card held",
            True, bool(want_pills) and all(p in (m.get("bandPills") or []) for p in want_pills))
    pairs = ["%s %s" % (t, v) for t, v in zip(m.get("bandTerms") or [], m.get("bandValues") or [])]
    want_rows = [x.strip() for x in wish["Guaranteed Analysis"].split(",") if x.strip()]
    Q.check("the band still lists every guaranteed figure the card held",
            True, bool(want_rows) and all(r in pairs for r in want_rows))

    scroll_to(".sf-gallery__title")
    Q.ab("screenshot", os.path.join(args.out, "01-gallery-heading-1440.png"))
    scroll_to(".sf-fdetail")
    Q.ab("screenshot", os.path.join(args.out, "02-spec-solo-1440.png"))

    # ---------------------------------------------------------------- 375
    # A fresh load, then the viewport, then a measurement that re-checks the
    # width in the same eval: `open` resets the viewport, and a measurement
    # taken on a page left over from the previous section reads an empty DOM
    # and reports a clean result about nothing.
    print("\n=== 375x667 ===")
    Q.ab("open", Q.BASE + PAGE)
    time.sleep(2.5)
    Q.ab("set", "viewport", "375", "667")
    time.sleep(1.0)
    small = Q.ev(MEASURE) or {}
    print("       solo grid width at 375:", small.get("gridWidth"), "px")
    print("       measured:",
          json.dumps({k: small.get(k) for k in ("ready", "nCards", "gridWidth", "h2",
                                                "docScrollW", "docClientW")},
                     ensure_ascii=False))
    Q.check("375: the page is loaded", "complete", small.get("ready"))
    Q.check("375: the measurement really is at 375", 375, small.get("docClientW"))
    Q.check("375: still one card", 1, small.get("nCards"))
    Q.check("375: no horizontal overflow", True,
            small.get("docScrollW") == small.get("docClientW"))
    Q.check("375: the solo grid fits the viewport", True,
            0 < (small.get("gridWidth") or 0) <= (small.get("docClientW") or 0))
    Q.check("375: the heading still names the formula",
            "A Closer Look at Ear Care Drops", small.get("h2"))
    scroll_to(".sf-fdetail")
    Q.ab("screenshot", os.path.join(args.out, "03-spec-solo-375.png"))
    Q.ab("close")

    bad = Q.results.count(False)
    print("\n" + "=" * 74)
    print("%s  step 4 evidence: %d checks, %d failed"
          % ("PASS" if not bad else "FAIL", len(Q.results), bad))
    print("=" * 74)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
