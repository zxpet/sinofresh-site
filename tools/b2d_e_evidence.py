#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D step E — rendered evidence for the three-section deletion.

The gates settle the bytes: 58 pages differ, and undoing the batch reproduces
the base byte-for-byte. Bytes cannot settle what a reader sees. This file
answers the rendered questions, after the pull, against the LIVE theme:

  * that the render under test really is the live one. Every number below
    describes the wrong bytes if the page was served by the pre-flight copy,
    so the stylesheet URL is asserted to contain 'sinofresh-theme/' (and NOT
    '-preflight') and ver=2.10.52.

  * that the three sections are gone from the DOM, not merely renamed: the
    .sf-facts band, the .sf-spectable table and the .sf-actives wrapper, plus
    the #actives anchor and both author-comment markers.

  * that the page still has its spine, in order, with nothing left behind.
    "still present" is not the claim — "in this order and not separated by an
    orphan band" is. Each heading's section top is compared, and the gap the
    deletion left between the hero and the card wall is measured.

  * what the number of dots on the point rail did. toc-nav.js builds one dot
    per h2, so deleting a section that carries a heading MUST cost one dot.
    This is measured and reported rather than assumed; the rail is also
    checked to be self-consistent (dots == h2 count), which is the property
    that actually matters — an orphan dot pointing at a section that no
    longer exists is the failure, a smaller rail is not.

  * that the JavaScript on the page really ran, so "no JS errors" is a
    statement about a working page rather than about a page where nothing
    executed: dots > 0, formula cards > 0, the configurator's groups > 0.

  * no horizontal scroll at either width.

The expected h2 order is derived from the BASE CAPTURE's bytes (the old
baseline, an independent source) with the actives heading removed — and the
tool first asserts that heading WAS in the base, so "minus one" is a real
deletion and not a typo that cancels itself out.

usage:
    python3 tools/b2d_e_evidence.py [--out DIR] [--live] [--pages ...]
"""
import argparse
import base64
from html import unescape as html_unescape
import json
import os
import re
import subprocess
import sys
import time

BASE = "https://dev.zxpet.com"
_auth = os.environ.get("SF_DEV_AUTH") or "sfdev:VkEws18Kl5V1qp3TpZ6s"
USER, PASS = _auth.split(":", 1)
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_OUT = os.path.join(ROOT, "docs", "b2d-stepE-shots")
BASELINE_DIR = os.path.join(ROOT, "_backup", "b2d-stepE-baselines", "base")

# deleted from all eight dosage templates; none of these may appear in a render
GONE_SELECTORS = [".sf-facts", ".sf-spectable", ".sf-actives", "#actives"]
GONE_MARKERS = ["B2D-S5: core facts", "B2D-S1: actives"]

ACTIVES_H2 = "Active Ingredients & Guaranteed Analysis"

# live theme version this batch ships
VER = "2.10.52"

PROBE = r"""
(function () {
  function r(el) {
    if (!el) return null;
    var b = el.getBoundingClientRect();
    return {top: Math.round(b.top + scrollY), bottom: Math.round(b.bottom + scrollY),
            left: Math.round(b.left), right: Math.round(b.right),
            width: Math.round(b.width), height: Math.round(b.height)};
  }
  function n(sel) { return document.querySelectorAll(sel).length; }
  var h2 = [], hs = document.querySelectorAll('h2');
  for (var i = 0; i < hs.length; i++) h2.push((hs[i].textContent || '').trim());

  // the section each heading belongs to, so the spine is measured from the
  // headings themselves rather than from a guessed class list. The section's
  // INDEX is kept as its identity: several spine sections carry no id and the
  // same generated class list, so the class name cannot tell two apart.
  var allSecs = document.querySelectorAll('section');
  var headSecs = [];
  for (var j = 0; j < hs.length; j++) {
    var sec = hs[j].closest('section');
    headSecs.push({text: h2[j],
                   idx: sec ? Array.prototype.indexOf.call(allSecs, sec) : null,
                   cls: sec ? (sec.className.split(' ')[1] || sec.className.split(' ')[0]) : null,
                   top: sec ? r(sec).top : null, bottom: sec ? r(sec).bottom : null});
  }

  var link = document.querySelector("link[rel='stylesheet'][href*='sinofresh-theme']");
  var cfg = document.querySelector('.configurator');
  var cfgSec = document.querySelector('section#configurator');
  var wall = document.querySelector('section#formulas');
  var faq = document.querySelector('.sf-faq');
  var rel = document.querySelector('.sf-related-grid');
  var cta = document.querySelector('section#inquiry-form');
  var hero = document.querySelector('section.sf-hero-inner');
  var toc = document.querySelector('.sf-toc');
  var gone = {};
  var gs = %s;
  for (var k = 0; k < gs.length; k++) gone[gs[k]] = n(gs[k]);
  var body = document.documentElement.outerHTML;
  var markers = [];
  var ms = %s;
  for (var m = 0; m < ms.length; m++) if (body.indexOf(ms[m]) !== -1) markers.push(ms[m]);

  return JSON.stringify({
    rs: document.readyState, w: innerWidth, h: innerHeight,
    sheet: link ? link.getAttribute('href') : null,
    gone: gone, markers: markers,
    h2: h2, dots: n('.sf-toc__dot'), tocLabels: n('.sf-toc__label'),
    tocDisplay: toc ? getComputedStyle(toc).display : null,
    tocHrefs: (function () {
      var out = [], as = document.querySelectorAll('.sf-toc a');
      for (var x = 0; x < as.length; x++) out.push(as[x].getAttribute('href'));
      return out;
    })(),
    headSecs: headSecs,
    hero: r(hero), wall: r(wall), cfg: r(cfg), cfgSec: r(cfgSec),
    faq: r(faq), rel: r(rel), cta: r(cta),
    cfgGroups: n('.configurator__group'),
    cards: wall ? wall.querySelectorAll('.sf-fcard').length : null,
    faqItems: n('.sf-faq__item'),
    relItems: rel ? rel.children.length : null,
    heroH1: (function () {
      var e = document.querySelector('h1');
      return e ? (e.textContent || '').trim() : null;
    })(),
    hScroll: document.documentElement.scrollWidth > innerWidth + 1,
    scrollW: document.documentElement.scrollWidth,
    scrollH: document.documentElement.scrollHeight
  });
})()
""" % (json.dumps(GONE_SELECTORS), json.dumps(GONE_MARKERS))


def ab(*args, timeout=180):
    p = subprocess.run(["agent-browser", *args], capture_output=True,
                       text=True, timeout=timeout)
    if p.returncode != 0 and p.stderr.strip():
        print("      !! agent-browser %s -> %s" % (" ".join(args), p.stderr.strip()[:200]))
    return p.stdout.strip()


def ev(js):
    """agent-browser eval prints a JSON string literal; decode it twice."""
    out = ab("eval", js)
    try:
        first = json.loads(out)
    except Exception:
        return {"_raw": out[:400]}
    if isinstance(first, str):
        try:
            return json.loads(first)
        except Exception:
            return {"_raw": first[:400]}
    return first


def base_h2_order(slug):
    """The base capture's h2 texts in document order — read from bytes, not
    from the page being tested. Entities are decoded: the capture holds
    `&amp;` where the DOM holds `&`."""
    html = open(os.path.join(BASELINE_DIR, slug + ".html"), encoding="utf-8").read()
    out = []
    for m in re.finditer(r'<h2[^>]*>(.*?)</h2>', html, re.S):
        t = re.sub(r'<[^>]+>', '', m.group(1))
        out.append(re.sub(r'\s+', ' ', html_unescape(t)).strip())
    return out


def slug_for(path):
    s = path.strip("/").replace("/", "__")
    return s if s else "root"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=DEFAULT_OUT)
    ap.add_argument("--live", action="store_true",
                    help="drop the pre-flight header (the post-pull state)")
    ap.add_argument("--pages", nargs="*", default=None,
                    help="paths; default is the full dosage set at 1440")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    cases = []
    if args.pages:
        for p in args.pages:
            cases.append((p, 1440, True))
    else:
        for p in ["/products/soft-chews/", "/products/tablets/", "/products/powders/",
                  "/products/pastes/", "/products/drops/", "/products/liquids/",
                  "/products/fish-oil/", "/products/dental-chews/"]:
            cases.append((p, 1440, True))
        cases.append(("/products/soft-chews/", 375, True))
        cases.append(("/zh/products/soft-chews/", 1440, True))
        cases.append(("/zh/products/powders/", 1440, True))

    results = []

    def check(scope, name, ok, expected, actual):
        results.append((scope, name, ok))
        print("  %-4s %-20s %-46s exp=%-24s act=%s"
              % ("PASS" if ok else "FAIL", scope, name, expected, actual))

    def fresh(path, w):
        """close --all -> set credentials -> open -> reload -> set viewport.

        Credentials go through `set credentials` and no custom header is set
        afterwards: the two are mutually exclusive in this CLI, each rebuilds
        the browser context."""
        ab("close", "--all")
        time.sleep(1)
        ab("set", "credentials", USER, PASS)
        ab("open", BASE + path)
        time.sleep(1)
        if not args.live:
            _BASIC = base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()
            ab("set", "headers", json.dumps({"X-SF-Preflight": "1",
                                             "Authorization": "Basic " + _BASIC}))
        ab("reload")
        time.sleep(1)
        ab("set", "viewport", str(w), "900")
        time.sleep(1)

    print("=" * 96)
    print("Batch 2D step E — rendered evidence  (live: %s)" % args.live)
    print("=" * 96)

    for path, w, shot in cases:
        slug = slug_for(path)
        scope = "%s@%d" % (slug.replace("products__", "p__").replace("zh__", "zh/"), w)
        print("\n[%s]" % scope)
        fresh(path, w)

        # --- identity of the render -------------------------------------
        js = ("(function(){var l=document.querySelector(\"link[rel='stylesheet']"
              "[href*='sinofresh-theme']\");return l?l.getAttribute('href'):'NONE'})()")
        raw = ab("eval", js).strip()
        try:
            sheet = json.loads(raw)
        except Exception:
            sheet = raw
        if not isinstance(sheet, str):
            sheet = str(sheet)
        want_dir = "sinofresh-theme/"
        check(scope, "stylesheet is the live theme", want_dir in sheet
              and "-preflight" not in sheet, "href has %s, no -preflight" % want_dir, sheet)
        check(scope, "stylesheet version is %s" % VER, ("ver=" + VER) in sheet,
              "ver=%s" % VER, sheet)

        a = ev(PROBE)
        if a.get("_raw"):
            check(scope, "probe returned JSON", False, "json", a.get("_raw"))
            continue

        print("      readyState=%s viewport=%sx%s scrollH=%s scrollW=%s"
              % (a.get("rs"), a.get("w"), a.get("h"), a.get("scrollH"), a.get("scrollW")))
        print("      h1=%r" % a.get("heroH1"))

        # --- the three sections are gone --------------------------------
        print("      gone: %s   markers: %s" % (json.dumps(a.get("gone")), a.get("markers")))
        for sel in GONE_SELECTORS:
            check(scope, "deleted: %s" % sel, a["gone"].get(sel) == 0, "0", a["gone"].get(sel))
        check(scope, "deleted: both markers", a.get("markers") == [], "[]", a.get("markers"))

        # --- headings: exactly the base order minus the actives one ------
        base = base_h2_order(slug)
        check(scope, "base carried the actives h2", ACTIVES_H2 in base,
              "present in base capture", base)
        expected = [h for h in base if h != ACTIVES_H2]
        check(scope, "h2 order == base minus actives", a.get("h2") == expected,
              "%d heading(s)" % len(expected), a.get("h2"))
        print("      h2: %s" % json.dumps(a.get("h2")))

        # --- the point rail --------------------------------------------
        check(scope, "rail is self-consistent (dots == h2)",
              a.get("dots") == len(a.get("h2") or []), "dots == %d" % len(a.get("h2") or []),
              a.get("dots"))
        check(scope, "rail count is base minus one",
              a.get("dots") == len(base) - 1, "%d" % (len(base) - 1), a.get("dots"))
        check(scope, "no dot points at a deleted anchor",
              not any("actives" in (h or "") for h in a.get("tocHrefs") or []),
              "no #actives in the rail", a.get("tocHrefs"))
        check(scope, "rail labels match dots", a.get("tocLabels") == a.get("dots"),
              "labels == dots", "%s / %s" % (a.get("tocLabels"), a.get("dots")))

        # --- the spine, in order ----------------------------------------
        hs_rows = a.get("headSecs") or []
        tops = [row["top"] for row in hs_rows if row.get("top") is not None]
        check(scope, "spine heading sections strictly increase",
              all(tops[i] < tops[i + 1] for i in range(len(tops) - 1)),
              "strictly increasing (%d sections)" % len(tops), tops)
        check(scope, "each heading still owns its own section",
              len(set(r["idx"] for r in hs_rows)) == len(hs_rows),
              "%d distinct sections" % len(hs_rows),
              ["#%s.%s" % (r["idx"], r["cls"]) for r in hs_rows])
        check(scope, "hero h1 present", bool(a.get("heroH1")), "non-empty", a.get("heroH1"))

        # --- the deletion left no orphan band ---------------------------
        hero, wall = a.get("hero"), a.get("wall")
        if hero and wall:
            gap = wall["top"] - hero["bottom"]
            check(scope, "hero -> card wall gap under 300px", gap < 300,
                  "< 300", "%d px" % gap)
        cfgsec = a.get("cfgSec")
        if wall and cfgsec:
            gap2 = cfgsec["top"] - wall["bottom"]
            print("      card wall %s" % json.dumps(wall))
            print("      configurator section %s" % json.dumps(cfgsec))
            check(scope, "card wall -> configurator gap under 300px", gap2 < 300,
                  "< 300", "%d px" % gap2)

        # --- survivors --------------------------------------------------
        check(scope, "card wall present", wall is not None, "present", wall is not None)
        check(scope, "configurator present", a.get("cfg") is not None,
              "present", a.get("cfg") is not None)
        check(scope, "faq present", a.get("faq") is not None, "present", a.get("faq") is not None)
        check(scope, "related present", a.get("rel") is not None, "present", a.get("rel") is not None)
        check(scope, "cta present", a.get("cta") is not None, "present", a.get("cta") is not None)
        check(scope, "faq items > 0", (a.get("faqItems") or 0) > 0, "> 0", a.get("faqItems"))
        check(scope, "related items > 0", (a.get("relItems") or 0) > 0, "> 0", a.get("relItems"))

        # --- the page's JS actually ran ---------------------------------
        check(scope, "toc-nav.js ran", (a.get("dots") or 0) > 0, "> 0", a.get("dots"))
        check(scope, "formula cards rendered", (a.get("cards") or 0) > 0, "> 0", a.get("cards"))
        check(scope, "configurator groups rendered", (a.get("cfgGroups") or 0) > 0,
              "> 0", a.get("cfgGroups"))
        if w <= 1100:
            check(scope, "rail hidden at this width", a.get("tocDisplay") == "none",
                  "none", a.get("tocDisplay"))

        # --- layout -----------------------------------------------------
        check(scope, "no horizontal scroll", a.get("hScroll") is False,
              "scrollW == viewport", "%s vs %s" % (a.get("scrollW"), a.get("w")))

        # --- console + errors -------------------------------------------
        errs = ab("errors", "--json") or ""
        cons = ab("console", "--json") or ""
        try:
            ejson = json.loads(errs)
        except Exception:
            ejson = errs
        try:
            cjson = json.loads(cons)
        except Exception:
            cjson = cons
        elist = ejson if isinstance(ejson, list) else (ejson.get("errors") if isinstance(ejson, dict) else [])
        clist = cjson if isinstance(cjson, list) else (cjson.get("logs") if isinstance(cjson, dict) else [])
        elist = elist or []
        clist = clist or []
        errlevel = [c for c in clist if isinstance(c, dict)
                    and str(c.get("type", c.get("level", ""))).lower() in ("error", "severe")]
        check(scope, "no JS page errors", len(elist) == 0, "0", len(elist))
        check(scope, "no console error lines", len(errlevel) == 0, "0", len(errlevel))
        if elist:
            print("      errors: %s" % json.dumps(elist)[:600])
        if errlevel:
            print("      console errors: %s" % json.dumps(errlevel)[:600])
        print("      console lines (for the record): %d" % len(clist))
        ab("errors", "--clear")
        ab("console", "--clear")

        # --- screenshots ------------------------------------------------
        if shot:
            name = "%s-%d" % (slug.replace("__", "-"), w)
            p1 = os.path.join(args.out, "%s-viewport.png" % name)
            p2 = os.path.join(args.out, "%s-full.png" % name)
            ab("screenshot", p1)
            ab("screenshot", "--full", p2)
            for p in (p1, p2):
                print("      shot %s  %s bytes" % (os.path.basename(p),
                                                   os.path.getsize(p) if os.path.exists(p) else "MISSING"))

    ab("close", "--all")

    bad = [r for r in results if not r[2]]
    print("\n" + "=" * 96)
    print("%s  %d check(s), %d failed" % ("PASS" if not bad else "FAIL", len(results), len(bad)))
    for scope, name, _ in bad:
        print("   FAIL %s — %s" % (scope, name))
    with open(os.path.join(args.out, "e2e.json"), "w", encoding="utf-8") as fh:
        json.dump([{"scope": s, "check": n, "ok": o} for s, n, o in results], fh, indent=2)
    print("=" * 96)
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
