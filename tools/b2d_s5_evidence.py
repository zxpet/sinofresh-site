#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D step 5 — rendered evidence for the core-facts band.

Bytes can say the band is present and that nothing else moved. They cannot say
where it lands: whether it really sits between the hero and the card wall,
whether it is inside the first screen, whether the phone layout stacks it, or
whether the toc rail still counts seven dots. Those are the claims this file
settles, and it settles them against the PRE-FLIGHT copy so they are known
before the change reaches the live theme.

What it refuses to take on faith, and why each is a check:

  * that the render is the copy under test. Every number below describes the
    wrong bytes if the header never reached the theme, so the stylesheet URL is
    asserted to contain the `-preflight` directory and `ver=2.10.51`.
  * that the band is between the hero and #formulas rather than merely present.
    The band's top is compared with the hero's bottom AND #formulas' top; a
    band appended at the end of the page would pass a "the band exists" test.
  * that the band is in the first screen. Reported as the number of the five
    fact rows whose top is above the fold at 1440x900, plus the band's own
    bottom, because "the band starts on screen" and "the facts are readable on
    screen" are different claims.
  * that the measurement can see the band at all. The band is pushed 1400px
    down in-page and the first-screen count must collapse; if it does not, the
    measurement is not live and the run fails.
  * that the toc rail is untouched. The dot count and the h2 order are compared
    with the h2 order read out of the BASE capture — old baseline bytes against
    the new rendered page, so the two sides of the comparison are independent.
  * that the band carries no heading, and that the Direct Answer is 50-80 words
    as rendered (not as written).

    python3 tools/b2d_s5_evidence.py [--page PATH] [--out DIR] [--live]
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
PAGE = "/products/soft-chews/"
SLUG = "soft-chews"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "docs", "b2d-step5-shots")
BASE_CAPTURE = os.path.join(ROOT, "_backup", "b2d-step5-baselines", "base",
                            "products__%s.html" % SLUG)

# `set headers` and `set credentials` are mutually exclusive in this CLI: each
# rebuilds the browser context and drops the other, so the credential travels
# INSIDE the headers call and `set credentials` is never called afterwards.
_BASIC = base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()
PREFLIGHT_HEADERS = json.dumps({
    "X-SF-Preflight": "1",
    "Authorization": "Basic " + _BASIC,
})

PROBE = r"""
(function () {
  function r(el) {
    if (!el) return null;
    var b = el.getBoundingClientRect();
    return {top: Math.round(b.top), bottom: Math.round(b.bottom),
            left: Math.round(b.left), right: Math.round(b.right),
            width: Math.round(b.width), height: Math.round(b.height)};
  }
  var band = document.querySelector('.sf-facts');
  var hero = document.querySelector('.sf-hero-inner');
  var wall = document.querySelector('#formulas');
  var table = document.querySelector('.sf-facts__table');
  var cap = document.querySelector('.sf-facts__caption');
  var ans = document.querySelector('.sf-facts__answer');
  var rows = document.querySelectorAll('.sf-facts__table tbody tr');
  var labels = [], values = [], rowTops = [];
  for (var i = 0; i < rows.length; i++) {
    var th = rows[i].querySelector('th'), td = rows[i].querySelector('td');
    labels.push(th ? (th.textContent || '').trim() : '');
    values.push(td ? (td.textContent || '').trim() : '');
    rowTops.push(r(rows[i]).top);
  }
  // the toc rail is built by toc-nav.js from every h2 in document order
  var dots = document.querySelectorAll('.sf-toc__dot');
  var tocLabels = document.querySelectorAll('.sf-toc__label');
  var h2 = [], hs = document.querySelectorAll('h2');
  for (var j = 0; j < hs.length; j++) h2.push((hs[j].textContent || '').trim());
  var link = document.querySelector("link[rel='stylesheet'][href*='sinofresh-theme']");
  var o = {found: !!band, rs: document.readyState, w: innerWidth, h: innerHeight,
           sheet: link ? link.getAttribute('href') : null,
           hero: r(hero), band: r(band), wall: r(wall),
           tableLeft: table ? r(table).left : null,
           capText: cap ? (cap.textContent || '').trim() : null,
           capLeft: cap ? r(cap).left : null,
           rows: rows.length, labels: labels, values: values, rowTops: rowTops,
           answerText: ans ? (ans.textContent || '').trim() : null,
           answerLeft: ans ? r(ans).left : null,
           answerTop: ans ? r(ans).top : null,
           answerBottom: ans ? r(ans).bottom : null,
           h2InsideBand: band ? band.querySelectorAll('h2').length : null,
           dots: dots.length, tocLabels: tocLabels.length,
           h2: h2, tocHrefs: (function () {
             var out = [], as = document.querySelectorAll('.sf-toc a');
             for (var k = 0; k < as.length; k++) out.push(as[k].getAttribute('href'));
             return out;
           })(),
           thDisplay: rows.length ? getComputedStyle(rows[0].querySelector('th')).display : null,
           tdDisplay: rows.length ? getComputedStyle(rows[0].querySelector('td')).display : null,
           hScroll: document.documentElement.scrollWidth > innerWidth + 1,
           scrollW: document.documentElement.scrollWidth};
  return JSON.stringify(o);
})()
"""

PUSH_DOWN = ("var s=document.createElement('style'); s.id='sf-pushdown';"
             "s.textContent='.sf-facts{padding-top:1400px !important}';"
             "document.head.appendChild(s); 'injected';")


def ab(*args, timeout=180):
    p = subprocess.run(["agent-browser", *args], capture_output=True, text=True, timeout=timeout)
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


def base_h2_order():
    """The base capture's h2 texts, in document order — read from bytes, not
    from the page being tested.

    Entities are decoded: the capture holds `&amp;` and the DOM's textContent
    holds `&`, so comparing them raw reports a difference that is only in the
    encoding. The first run of this file did exactly that and failed two
    checks over "Active Ingredients &amp; Guaranteed Analysis".
    """
    html = open(BASE_CAPTURE, encoding="utf-8").read()
    out = []
    for m in re.finditer(r'<h2[^>]*>(.*?)</h2>', html, re.S):
        t = re.sub(r'<[^>]+>', '', m.group(1))
        out.append(re.sub(r'\s+', ' ', html_unescape(t)).strip())
    return out


def words(text):
    return len((text or '').split())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default=PAGE)
    ap.add_argument("--out", default=SHOTS)
    ap.add_argument("--live", action="store_true",
                    help="drop the preflight header — for the post-pull confirmation")
    ap.add_argument("--expect-ver", default=None,
                    help="the enqueue version the render must be serving; defaults to "
                         "the pre-flight candidate 2.10.51 before the pull and must be "
                         "given explicitly for --live once the pull has happened")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    results = []

    def check(name, ok, expected, actual):
        results.append((name, ok))
        print("  %-4s %-54s expected=%-26s actual=%s"
              % ("PASS" if ok else "FAIL", name, expected, actual))

    def fresh(w):
        """close --all -> set credentials -> open -> set headers -> reload -> set viewport."""
        ab("close", "--all")
        time.sleep(1)
        ab("set", "credentials", USER, PASS)
        ab("open", BASE + args.page)
        time.sleep(1)
        if not args.live:
            ab("set", "headers", PREFLIGHT_HEADERS)
        ab("reload")
        time.sleep(1)
        ab("set", "viewport", str(w), "900")
        time.sleep(1)

    def expect_sheet(substr, label, ver):
        js = ("(function(){var l=document.querySelector(\"link[rel='stylesheet']"
              "[href*='sinofresh-theme']\");return l?l.getAttribute('href'):'NONE'})()")
        s = ab("eval", js).strip()
        try:
            sheet = json.loads(s)
        except Exception:
            sheet = s
        if not isinstance(sheet, str):
            sheet = str(sheet)
        check(label, substr in sheet, "href contains %s" % substr, sheet)
        check("the stylesheet served is %s" % ver, ("ver=" + ver) in sheet,
              "ver=%s" % ver, sheet)

    ver = args.expect_ver or "2.10.51"
    print("=" * 84)
    print("Batch 2D step 5 — rendered evidence  (%s, header: %s)"
          % (args.page, "(none — live)" if args.live else "X-SF-Preflight: 1"))
    print("=" * 84)

    base_h2 = base_h2_order()
    print("base capture h2 order: %d heading(s)" % len(base_h2))

    # ---------- 1440 ----------
    print("\n[1] 1440 — where the band lands")
    fresh(1440)
    expect_sheet("sinofresh-theme/" if args.live else "-preflight",
                 "stylesheet is the live theme copy" if args.live
                 else "stylesheet really is the pre-flight copy", ver)
    a = ev(PROBE)
    print("      hero   %s" % json.dumps(a.get("hero")))
    print("      band   %s" % json.dumps(a.get("band")))
    print("      wall   %s" % json.dumps(a.get("wall")))
    check("render is complete at 1440",
          a.get("rs") == "complete" and a.get("w") == 1440,
          "complete / 1440", "%s / %s" % (a.get("rs"), a.get("w")))
    check("the band exists", a.get("found") is True, "True", a.get("found"))
    check("five fact rows", a.get("rows") == 5, "5", a.get("rows"))
    check("the band carries no heading", a.get("h2InsideBand") == 0, "0", a.get("h2InsideBand"))
    band, hero, wall = a.get("band"), a.get("hero"), a.get("wall")
    check("band sits below the hero",
          band and hero and band["top"] >= hero["bottom"],
          "band.top >= hero.bottom", "%s vs %s" % (band["top"], hero["bottom"]))
    check("band sits above #formulas",
          band and wall and band["bottom"] <= wall["top"],
          "band.bottom <= #formulas.top", "%s vs %s" % (band["bottom"], wall["top"]))
    on_screen = sum(1 for t in a.get("rowTops") or [] if t < 900)
    check("all five fact rows are in the first 900px", on_screen == 5, "5", on_screen)
    # The band's own bottom is reported, not asserted against 900: at 1440x900
    # the five fields and the start of the answer are on screen and the last two
    # lines of the prose are not — which is the trade the ordering was chosen
    # for, not a failure. See batch2d-step5.md for the measured numbers.
    check("the Direct Answer starts inside the first screen",
          a.get("answerTop") is not None and a.get("answerTop") < 900,
          "< 900", a.get("answerTop"))
    print("      band bottom %s, answer %s..%s (viewport 900)"
          % (band and band["bottom"], a.get("answerTop"), a.get("answerBottom")))
    check("table left edge == caption left edge",
          a.get("tableLeft") == a.get("capLeft"),
          "tableLeft == capLeft", "%s / %s" % (a.get("tableLeft"), a.get("capLeft")))
    check("band's left edge is the page measure's left edge (120)",
          a.get("capLeft") == 120, "120", a.get("capLeft"))
    check("no horizontal scroll at 1440", a.get("hScroll") is False, "False", a.get("hScroll"))
    check("Direct Answer is 50-80 words as rendered",
          a.get("answerText") is not None and 50 <= words(a.get("answerText")) <= 80,
          "50-80", words(a.get("answerText")))
    check("the caption names the table (no H2 needed)",
          bool(a.get("capText")) and "Core facts" in (a.get("capText") or ""),
          "contains 'Core facts'", a.get("capText"))
    print("      labels: %s" % " | ".join(a.get("labels") or []))
    print("      values: %s" % " || ".join((v or "")[:44] for v in (a.get("values") or [])))
    print("      row tops above 900: %s" % a.get("rowTops"))
    print("      answer %d words: %s" % (words(a.get("answerText")),
                                         (a.get("answerText") or "")[:120] + "..."))
    check("toc rail still has seven dots", a.get("dots") == 7, "7", a.get("dots"))
    check("toc rail labels match its dots",
          a.get("tocLabels") == a.get("dots"),
          "same count", "%s / %s" % (a.get("tocLabels"), a.get("dots")))
    check("h2 order is unchanged from the base capture (old bytes vs new page)",
          a.get("h2") == base_h2, "%d heading(s), same order" % len(base_h2),
          "%d heading(s)%s" % (len(a.get("h2") or []),
                               "" if a.get("h2") == base_h2 else " — DIFFERS"))
    if a.get("h2") != base_h2:
        for i, (x, y) in enumerate(zip(base_h2, a.get("h2") or [])):
            if x != y:
                print("        #%d base=%r new=%r" % (i, x, y))

    # ---------- 1440 negative control ----------
    print("\n[2] 1440 — negative control (push the band 1400px down)")
    print("      %s" % ab("eval", PUSH_DOWN))
    time.sleep(1)
    b = ev(PROBE)
    on_screen_b = sum(1 for t in b.get("rowTops") or [] if t < 900)
    check("the first-screen count collapses when the band moves",
          on_screen_b == 0, "0 rows above 900", on_screen_b)
    # Compare the first ROW's top, not the band's: padding-top grows the box
    # downward without moving its top edge, so a box-top comparison read "0px
    # moved" on a control that had visibly worked.
    moved = ((b.get("rowTops") or [0])[0] - (a.get("rowTops") or [0])[0])
    check("the fact rows really moved down",
          moved > 1200, "> +1200px", "%s px" % moved)

    # ---------- 375 ----------
    print("\n[3] 375 — the same page on a phone")
    fresh(375)
    c = ev(PROBE)
    print("      band   %s" % json.dumps(c.get("band")))
    print("      wall   %s" % json.dumps(c.get("wall")))
    check("render is complete at 375",
          c.get("rs") == "complete" and c.get("w") == 375,
          "complete / 375", "%s / %s" % (c.get("rs"), c.get("w")))
    check("no horizontal scroll at 375", c.get("hScroll") is False, "False", c.get("hScroll"))
    check("the band fits the phone measure",
          (c.get("band") or {}).get("width", 9999) <= 375,
          "<= 375", (c.get("band") or {}).get("width"))
    check("the table stacks: th becomes a block", c.get("thDisplay") == "block",
          "block", c.get("thDisplay"))
    check("the table stacks: td becomes a block", c.get("tdDisplay") == "block",
          "block", c.get("tdDisplay"))
    check("every stacked row still carries its field name",
          all((x or "").strip() for x in (c.get("labels") or [])) and c.get("rows") == 5,
          "5 non-empty labels", "%s rows, %s"
          % (c.get("rows"), [bool((x or "").strip()) for x in (c.get("labels") or [])]))
    check("Direct Answer is 50-80 words at 375 too",
          50 <= words(c.get("answerText")) <= 80, "50-80", words(c.get("answerText")))
    check("toc rail still has seven dots at 375", c.get("dots") == 7, "7", c.get("dots"))
    check("h2 order unchanged at 375", c.get("h2") == base_h2,
          "%d heading(s), same order" % len(base_h2), len(c.get("h2") or []))

    # ---------- screenshots ----------
    tag = "live" if args.live else "preflight"
    for label, w, sel in (("1440", 1440, ".sf-facts"),
                          ("1440-hero", 1440, ".sf-hero-inner"),
                          ("375", 375, ".sf-facts")):
        fresh(w)
        ab("scrollintoview", sel)
        time.sleep(1)
        ab("screenshot", os.path.join(args.out, "01-facts-%s-%s.png" % (tag, label)))
    ab("close", "--all")

    bad = [n for n, ok in results if not ok]
    print("\n" + "=" * 84)
    print("%s — %d/%d checks pass" % ("PASS" if not bad else "FAIL",
                                      len(results) - len(bad), len(results)))
    for n in bad:
        print("  * %s" % n)
    print("=" * 84)
    with open(os.path.join(args.out, "evidence%s.json" % ("-live" if args.live else "")),
              "w", encoding="utf-8") as fh:
        json.dump({"1440": a, "1440_pushed_down": b, "375": c,
                   "base_h2": base_h2,
                   "checks": [{"name": n, "ok": ok} for n, ok in results]},
                  fh, ensure_ascii=False, indent=2)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
