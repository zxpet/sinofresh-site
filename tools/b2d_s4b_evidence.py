#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D step 4b — rendered evidence that the single card is now left-aligned.

Bytes cannot prove where a 560px block lands inside a 1200px measure: that is
the one claim only a render can settle. This runs against the PRE-FLIGHT copy
(requests carry `X-SF-Preflight: 1`), so the claim is settled before the change
is ever pulled onto the live theme.

Three things this file refuses to take on faith:

  * that the render is really the copy. A preflight capture whose header never
    reached the theme would render the LIVE stylesheet and the check would pass
    while proving nothing. The fetched stylesheet URL is asserted to contain
    the `-preflight` directory, and the version token to read 2.10.49.
  * that the measurement can see the difference at all. A check that prints
    "left-aligned" would print it just as happily if the card had never moved.
    So the rule is then neutralised in-page (`margin-inline: auto`, the value
    core's :where() rule supplies) and the card must travel back to the centre;
    if it does not move, the measurement is an empty test and the run fails.
  * that the viewport is what we think. `set viewport` has been observed to be
    reset by `open`, so the document is reloaded at the target width and
    readyState + innerWidth are asserted in the SAME eval as the numbers.

    python3 tools/b2d_s4b_evidence.py [--page PATH] [--out DIR]
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time

BASE = "https://dev.zxpet.com"
_auth = os.environ.get("SF_DEV_AUTH") or "sfdev:VkEws18Kl5V1qp3TpZ6s"
USER, PASS = _auth.split(":", 1)
PAGE = "/formulas/ear-care-drops/"
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOTS = os.path.join(ROOT, "docs", "b2d-step4b-shots")

# `set headers` and `set credentials` are mutually exclusive in this CLI: each
# one rebuilds the browser context and drops the other. Measured 2026-09-21 —
# with credentials set and headers set afterwards, the reload came back 401;
# with credentials re-set afterwards, the preflight header was gone and the page
# served the LIVE stylesheet, i.e. the run would have "proved" the change on
# bytes that did not contain it. The way through is one single `set headers`
# call carrying both: the preflight flag AND the Basic credential, so nothing
# is dropped on the way in. Headers are also scoped to the origin, so the page
# has to be opened once first — setting them from about:blank scopes them to
# about:blank and they never reach dev.zxpet.com.
_BASIC = base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()
PREFLIGHT_HEADERS = json.dumps({
    "X-SF-Preflight": "1",
    "Authorization": "Basic " + _BASIC,
})

PROBE = r"""
(function () {
  var grid = document.querySelector('.sf-fdetail__grid');
  var sec  = document.querySelector('.sf-fdetail');
  if (!grid || !sec) return JSON.stringify({found:false, rs:document.readyState, w:innerWidth});
  var h2 = null;
  var hs = sec.querySelectorAll('h2');
  for (var i = 0; i < hs.length; i++) {
    if ((hs[i].textContent || '').trim() === 'Specification') { h2 = hs[i]; break; }
  }
  var gr = grid.getBoundingClientRect();
  var hr = h2 ? h2.getBoundingClientRect() : null;
  var card = grid.querySelector('.sf-fdetail__card');
  var cr = card ? card.getBoundingClientRect() : null;
  var cs = getComputedStyle(grid);
  var link = document.querySelector("link[rel='stylesheet'][href*='sinofresh-theme']");
  return JSON.stringify({
    found: true,
    rs: document.readyState,
    w: innerWidth,
    sheet: link ? link.getAttribute('href') : null,
    cls: grid.className,
    gridLeft: Math.round(gr.left), gridRight: Math.round(gr.right), gridW: Math.round(gr.width),
    h2Left: hr ? Math.round(hr.left) : null,
    deltaVsH2: hr ? Math.round(gr.left - hr.left) : null,
    marginInlineStart: cs.marginInlineStart || cs.marginLeft,
    maxWidth: cs.maxWidth,
    cardCount: grid.querySelectorAll('.sf-fdetail__card').length,
    cardLeft: cr ? Math.round(cr.left) : null,
    cardW: cr ? Math.round(cr.width) : null,
    hScroll: document.documentElement.scrollWidth > innerWidth + 1
  });
})()
"""

NEUTRALISE = ("var s=document.createElement('style');"
              "s.id='sf-neutralise';"
              "s.textContent='.sf-fdetail__grid--solo{margin-inline:auto}';"
              "document.head.appendChild(s); 'injected';")


def ab(*args, timeout=180):
    p = subprocess.run(["agent-browser", *args], capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0 and p.stderr.strip():
        print("      !! agent-browser %s -> %s" % (" ".join(args), p.stderr.strip()[:200]))
    return p.stdout.strip()


def ev(js):
    """agent-browser eval prints a JSON string literal; decode it twice.

    The first decode yields the string the evaluator returned, not the object
    it serialised — reading it as a dict then raises 'str has no attribute get'
    several lines later, far from the cause.
    """
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


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--page", default=PAGE)
    ap.add_argument("--out", default=SHOTS)
    ap.add_argument("--live", action="store_true",
                    help="drop the preflight header — for the post-pull confirmation")
    args = ap.parse_args()
    os.makedirs(args.out, exist_ok=True)

    results = []

    def check(name, ok, expected, actual):
        results.append((name, ok))
        print("  %-4s %-46s expected=%-28s actual=%s"
              % ("PASS" if ok else "FAIL", name, expected, actual))

    def fresh(w):
        """Bring the browser to: pre-flight render (or live), at width w.

        The only step order that works, measured 2026-09-21 on this CLI:

            close --all -> set credentials -> open -> set headers -> reload
            -> set viewport

        * `set headers` and `set credentials` each rebuild the context and drop
          the other, so the credential has to travel INSIDE the headers call
          (see PREFLIGHT_HEADERS) — and then `set credentials` must not be
          called again.
        * headers are scoped to the origin, so a document has to be on
          dev.zxpet.com before they are set; setting them from about:blank (or
          before the first open) parks them on the wrong origin and the run
          silently measures the live theme.
        * `open` discards them; `reload` keeps them. Navigating with `open`
          after setting headers is exactly how the first version of this file
          "measured" the fix against the un-fixed stylesheet.
        * `set viewport` is safe anywhere after the reload — it re-lays out
          without dropping the headers — and it has to come last because `open`
          is what resets the width to the 1280 default.
        """
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
        """Assert which theme directory answered, before measuring anything.

        Every number below is worthless if the render came from the other
        theme: the same rule reads as fixed or broken depending on which bytes
        the browser received. This assertion is not decoration — it is what
        caught the first version of this file measuring the live stylesheet
        while believing it had the pre-flight copy.
        """
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
        return sheet

    print("=" * 74)
    print("Batch 2D step 4b — rendered evidence  (%s, header: %s)"
          % (args.page, "(none — live)" if args.live else "X-SF-Preflight: 1"))
    print("=" * 74)

    # ---------- 1440: alignment ----------
    print("\n[1] 1440 — alignment of the single card")
    fresh(1440)
    expect_sheet("-preflight" if not args.live else "sinofresh-theme/",
                 "stylesheet really is the pre-flight copy"
                 if not args.live else "stylesheet is the live theme copy",
                 "2.10.49" if not args.live else "2.10.48")
    a = ev(PROBE)
    print("      %s" % json.dumps(a, ensure_ascii=False))
    check("render is complete at 1440", a.get("rs") == "complete" and a.get("w") == 1440,
          "complete / 1440", "%s / %s" % (a.get("rs"), a.get("w")))
    check("exactly one card (the --solo state)", a.get("cardCount") == 1,
          "1", a.get("cardCount"))
    check("grid carries the --solo modifier",
          "--solo" in (a.get("cls") or ""), "--solo", a.get("cls"))
    check("cap still 560px", a.get("maxWidth") == "560px", "560px", a.get("maxWidth"))
    check("grid left edge == Specification h2 left edge",
          a.get("deltaVsH2") == 0, "0px", "%spx" % a.get("deltaVsH2"))
    check("card left == h2 left (card does not float inside its track)",
          a.get("cardLeft") is not None and a.get("h2Left") == a.get("cardLeft"),
          "cardLeft == h2Left", "%s / %s" % (a.get("cardLeft"), a.get("h2Left")))
    check("no horizontal scroll at 1440", a.get("hScroll") is False, "False", a.get("hScroll"))
    a1440 = a

    # ---------- 1440: negative control ----------
    print("\n[2] 1440 — negative control (neutralise the rule in-page)")
    print("      %s" % ab("eval", NEUTRALISE))
    time.sleep(0.5)
    b = ev(PROBE)
    print("      %s" % json.dumps(b, ensure_ascii=False))
    moved = None
    if a.get("gridLeft") is not None and b.get("gridLeft") is not None:
        moved = b["gridLeft"] - a["gridLeft"]
    check("card travels back to centre when the rule is neutralised",
          moved is not None and moved > 200,
          "> +200px", "%s px (%s -> %s)" % (moved, a.get("gridLeft"), b.get("gridLeft")))
    check("neutralised state is genuinely centred",
          b.get("marginInlineStart") not in (None, "0px"), "non-zero", b.get("marginInlineStart"))

    # ---------- 375 ----------
    print("\n[3] 375 — the same page on a phone")
    fresh(375)
    c = ev(PROBE)
    print("      %s" % json.dumps(c, ensure_ascii=False))
    check("render is complete at 375", c.get("rs") == "complete" and c.get("w") == 375,
          "complete / 375", "%s / %s" % (c.get("rs"), c.get("w")))
    check("no horizontal scroll at 375", c.get("hScroll") is False, "False", c.get("hScroll"))
    check("card fits the phone measure",
          c.get("cardW") is not None and c.get("cardW") <= 375,
          "<= 375px", "%spx" % c.get("cardW"))
    check("grid left edge still on the h2 edge at 375",
          c.get("deltaVsH2") == 0, "0px", "%spx" % c.get("deltaVsH2"))

    # ---------- screenshots ----------
    for label, w in (("1440", 1440), ("375", 375)):
        fresh(w)
        ab("scrollintoview", ".sf-fdetail__grid")
        time.sleep(1)
        p = os.path.join(args.out, "01-solo-left-%s.png" % label)
        ab("screenshot", p)
    ab("close", "--all")

    bad = [n for n, ok in results if not ok]
    print("\n" + "=" * 74)
    print("%s — %d/%d checks pass" % ("PASS" if not bad else "FAIL",
                                      len(results) - len(bad), len(results)))
    if bad:
        for n in bad:
            print("  * %s" % n)
    print("=" * 74)
    with open(os.path.join(args.out, "evidence.json"), "w", encoding="utf-8") as fh:
        json.dump({"1440": a1440, "1440_neutralised": b, "375": c,
                   "checks": [{"name": n, "ok": ok} for n, ok in results]},
                  fh, ensure_ascii=False, indent=2)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
