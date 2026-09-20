#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D step 5 — geometry of the eight dosage pages, before the change.

Answers, with numbers rather than by reading markup:
  1. what the hero actually contains on screen (breadcrumb / h1 / subtitle /
     buttons) and how tall it is at 1440 and at 375;
  2. how much vertical room sits between the hero's bottom edge and the top of
     the Standard Formulas band — i.e. whether a new band fits "after the hero"
     at all, and whether it would push the card wall below the fold;
  3. where the existing .sf-spectable table sits (it already carries MOQ and
     lead time, so a new facts row has to be argued against it);
  4. how many dots the toc rail draws today and at which y, so the "does the
     dot rail change?" question has a baseline.

Two house rules this file obeys, both learned the hard way on this box:
  * the viewport is asserted in the SAME eval as the measurement — `open` has
    been observed to reset it, and a measurement taken at the wrong width is an
    empty check;
  * the document is reloaded at each width rather than resized between
    measurements, and readyState is asserted, so a stale DOM can never report
    a page that is not there.

    python3 tools/b2d_s5_measure.py [--out DIR] [--widths 1440,375]
"""
import argparse
import json
import os
import subprocess
import sys
import time

BASE = "https://dev.zxpet.com"
_auth = os.environ.get("SF_DEV_AUTH") or "sfdev:VkEws18Kl5V1qp3TpZ6s"
USER, PASS = _auth.split(":", 1)

PAGES = [
    ("soft-chews",    "/products/soft-chews/"),
    ("tablets",       "/products/tablets/"),
    ("powders",       "/products/powders/"),
    ("pastes",        "/products/pastes/"),
    ("drops",         "/products/drops/"),
    ("liquids",       "/products/liquids/"),
    ("fish-oil",      "/products/fish-oil/"),
    ("dental-chews",  "/products/dental-chews/"),
]

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "docs", "b2d-step5-shots")

PROBE = r"""
(function () {
  function box(sel) {
    var el = document.querySelector(sel);
    if (!el) return null;
    var r = el.getBoundingClientRect();
    return { top: Math.round(r.top + scrollY), bottom: Math.round(r.bottom + scrollY),
             h: Math.round(r.height), w: Math.round(r.width) };
  }
  var hero = document.querySelector(".sf-hero-inner");
  var band = document.querySelector("#formulas");
  var spec = document.querySelector(".sf-spectable");
  var h1   = document.querySelector("h1");
  var sub  = hero ? hero.querySelector("p") : null;
  var bc   = hero ? hero.querySelector(".sf-breadcrumb") : null;
  var btns = hero ? hero.querySelector(".wp-block-buttons") : null;
  var dots = [].map.call(document.querySelectorAll(".sf-toc__dot, .sf-toc li, .sf-toc a"),
                         function (d) { var r = d.getBoundingClientRect();
                                        return Math.round(r.top + scrollY); });
  var rail = document.querySelector(".sf-toc");
  var btnBoxes = [];
  if (btns) {
    [].forEach.call(btns.querySelectorAll("a"), function (a) {
      var r = a.getBoundingClientRect();
      btnBoxes.push({ text: (a.textContent || "").trim(), w: Math.round(r.width),
                      h: Math.round(r.height), border: getComputedStyle(a).borderTopWidth });
    });
  }
  return {
    readyState: document.readyState,
    innerWidth: innerWidth,
    innerHeight: innerHeight,
    docH: Math.round(document.documentElement.scrollHeight),
    hScroll: document.documentElement.scrollWidth > innerWidth + 1,
    hero: box(".sf-hero-inner"),
    h1: box("h1"),
    breadcrumb: bc ? box(".sf-hero-inner .sf-breadcrumb") : null,
    subtitle: sub ? { text: (sub.textContent || "").trim().slice(0, 120),
                      fontSize: getComputedStyle(sub).fontSize } : null,
    buttons: btnBoxes,
    band: band ? box("#formulas") : null,
    bandFirstHeading: (function () {
      var b = document.querySelector("#formulas"); if (!b) return null;
      var h = b.querySelector("h2"); if (!h) return null;
      var r = h.getBoundingClientRect();
      return { text: (h.textContent || "").trim(), top: Math.round(r.top + scrollY) };
    })(),
    gapHeroToBand: (hero && band)
      ? Math.round(band.getBoundingClientRect().top + scrollY
                   - (hero.getBoundingClientRect().bottom + scrollY))
      : null,
    spectable: spec ? box(".sf-spectable") : null,
    secOrder: [].map.call(document.querySelectorAll(".wp-site-blocks > .wp-block-group, .wp-site-blocks > section"),
                          function (s) {
                            var r = s.getBoundingClientRect();
                            return (s.id || s.className.split(" ")[0] || s.tagName.toLowerCase())
                                   + "@" + Math.round(r.top + scrollY);
                          }),
    h2s: [].map.call(document.querySelectorAll("h2"), function (h) {
      return { text: (h.textContent || "").replace(/\s+/g, " ").trim().slice(0, 48),
               id: h.id, top: Math.round(h.getBoundingClientRect().top + scrollY) };
    }),
    tocRail: rail ? { display: getComputedStyle(rail).display,
                      count: document.querySelectorAll(".sf-toc a, .sf-toc li").length,
                      dots: dots } : null
  };
})()
"""


def ab(*args, timeout=180):
    p = subprocess.run(["agent-browser", *args], capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0 and p.stderr.strip():
        print("      !! agent-browser %s -> %s" % (" ".join(args), p.stderr.strip()[:200]))
    return p.stdout.strip()


def ev(js):
    out = ab("eval", js)
    try:
        return json.loads(out)
    except Exception:
        return {"_raw": out[:600]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=SHOTS)
    ap.add_argument("--widths", default="1440,375")
    ap.add_argument("--pages", default="")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    widths = [int(w) for w in args.widths.split(",")]
    pages = PAGES
    if args.pages:
        want = set(args.pages.split(","))
        pages = [p for p in PAGES if p[0] in want]

    ab("close", "--all")
    ab("set", "credentials", USER, PASS)
    ab("set", "viewport", "1440", "900")

    report = {}
    for slug, path in pages:
        report[slug] = {}
        for w in widths:
            ab("close", "--all")
            ab("set", "credentials", USER, PASS)
            ab("open", BASE + path)
            ab("set", "viewport", str(w), "900")
            time.sleep(2)
            ab("open", BASE + path)          # reload at the new width
            time.sleep(2)
            data = ev(PROBE)
            report[slug][str(w)] = data
            ok = data.get("readyState") == "complete" and data.get("innerWidth") == w
            print("%-14s w=%-5s readyState=%s innerWidth=%s docH=%s heroH=%s gap=%s hScroll=%s"
                  % (slug, w, data.get("readyState"), data.get("innerWidth"), data.get("docH"),
                     (data.get("hero") or {}).get("h"), data.get("gapHeroToBand"),
                     data.get("hScroll")))
            if not ok:
                print("      !! viewport/readyState assertion failed — measurement is void")

    out = os.path.join(args.out, "geometry.json")
    with open(out, "w", encoding="utf-8") as fh:
        json.dump(report, fh, ensure_ascii=False, indent=2)
    print("\n-> %s" % out)

    # human summary
    print("\n%-14s %-9s %-9s %-9s %-9s %-9s %s"
          % ("page", "heroTop", "heroBot", "bandTop", "gap", "specTop", "h2 count"))
    for slug, _ in pages:
        d = report[slug]["1440"]
        print("%-14s %-9s %-9s %-9s %-9s %-9s %s"
              % (slug, (d.get("hero") or {}).get("top"), (d.get("hero") or {}).get("bottom"),
                 (d.get("band") or {}).get("top"), d.get("gapHeroToBand"),
                 (d.get("spectable") or {}).get("top"), len(d.get("h2s") or [])))

    ab("close", "--all")
    return 0


if __name__ == "__main__":
    sys.exit(main())
