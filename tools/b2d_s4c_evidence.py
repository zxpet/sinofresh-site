#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D step 4c — rendered evidence that the single card sits on the page's
left edge at width 560.

Bytes cannot say where a 560px track lands inside a 1200px measure; that is the
one claim only a render can settle. Run against the PRE-FLIGHT copy (requests
carry `X-SF-Preflight: 1`), so the claim is settled before the change is pulled
onto the live theme — which is the whole point of the order.

What this file refuses to take on faith, and why each refusal is a check rather
than a comment:

  * that the render is really the copy. A capture whose header never reached the
    theme renders the LIVE stylesheet, and every number below then describes
    bytes that do not contain the change. So the stylesheet URL is asserted to
    contain the `-preflight` directory and `ver=2.10.50`. The 4b run of this
    family of scripts measured the live theme while believing it had the copy;
    this assertion is what caught it.
  * that the measurement can see the difference at all. `cardW == 560` on its
    own would read as a pass in a world where the rule did nothing and the card
    happened to be 560 for another reason. So the rule is neutralised in-page
    (the grid is handed back its base `repeat(auto-fit, minmax(280px, 1fr))`)
    and the card must travel out to the full measure; if it does not move, the
    test is empty and the run fails.
  * that the alignment is with THIS page rather than with a hard-coded 120. The
    grid's left edge is compared against the left edge of every h2 on the page,
    and how many of those it shares is reported. 120 is also asserted, but the
    shared-edge count is the claim the change was actually asked for.
  * that the viewport is what we think. `set viewport` is reset by `open`, so
    the document is reloaded at the target width and readyState + innerWidth are
    read in the SAME eval as the numbers.

    python3 tools/b2d_s4c_evidence.py [--page PATH] [--out DIR] [--live]
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
SHOTS = os.path.join(ROOT, "docs", "b2d-step4c-shots")

# `set headers` and `set credentials` are mutually exclusive in this CLI: each
# rebuilds the browser context and drops the other. So the credential travels
# INSIDE the headers call, and `set credentials` is never called afterwards.
_BASIC = base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()
PREFLIGHT_HEADERS = json.dumps({
    "X-SF-Preflight": "1",
    "Authorization": "Basic " + _BASIC,
})

PROBE = r"""
(function () {
  function rect(el) {
    var r = el.getBoundingClientRect();
    return {left: Math.round(r.left), right: Math.round(r.right), width: Math.round(r.width)};
  }
  var grid = document.querySelector('.sf-fdetail__grid');
  var sec  = document.querySelector('.sf-fdetail');
  if (!grid || !sec) return JSON.stringify({found:false, rs:document.readyState, w:innerWidth});
  var specH2 = null;
  var hs = sec.querySelectorAll('h2');
  for (var i = 0; i < hs.length; i++) {
    if ((hs[i].textContent || '').trim() === 'Specification') { specH2 = hs[i]; break; }
  }
  var card = grid.querySelector('.sf-fdetail__card');
  var link = document.querySelector("link[rel='stylesheet'][href*='sinofresh-theme']");
  var gridLeft = rect(grid).left;
  // Every h2 on the page, so the alignment claim can be stated as "shares the
  // left edge with N of them" instead of against a number typed in here.
  var pageH2 = [], shared = 0;
  var all = document.querySelectorAll('h2');
  for (var j = 0; j < all.length; j++) {
    var l = rect(all[j]).left;
    pageH2.push(((all[j].textContent || '').trim().slice(0, 26)) + '@x=' + l);
    if (l === gridLeft) shared++;
  }
  return JSON.stringify({
    found: true, rs: document.readyState, w: innerWidth,
    sheet: link ? link.getAttribute('href') : null,
    cls: grid.className,
    gridLeft: gridLeft, gridW: rect(grid).width,
    specH2Left: specH2 ? rect(specH2).left : null,
    deltaVsSpecH2: specH2 ? gridLeft - rect(specH2).left : null,
    cardCount: grid.querySelectorAll('.sf-fdetail__card').length,
    cardLeft: card ? rect(card).left : null,
    cardW: card ? rect(card).width : null,
    tracks: getComputedStyle(grid).gridTemplateColumns,
    maxWidth: getComputedStyle(grid).maxWidth,
    h2Count: all.length, h2SharedLeft: shared, h2s: pageH2,
    hScroll: document.documentElement.scrollWidth > innerWidth + 1
  });
})()
"""

NEUTRALISE = ("var s=document.createElement('style'); s.id='sf-neutralise';"
              "s.textContent='.sf-fdetail__grid--solo{grid-template-columns:"
              "repeat(auto-fit, minmax(280px, 1fr))}';"
              "document.head.appendChild(s); 'injected';")


def ab(*args, timeout=180):
    p = subprocess.run(["agent-browser", *args], capture_output=True, text=True, timeout=timeout)
    if p.returncode != 0 and p.stderr.strip():
        print("      !! agent-browser %s -> %s" % (" ".join(args), p.stderr.strip()[:200]))
    return p.stdout.strip()


def ev(js):
    """agent-browser eval prints a JSON string literal; decode it twice.

    The first decode yields the string the evaluator returned, not the object it
    serialised — reading that as a dict raises 'str has no attribute get' many
    lines later, far from the cause.
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
        print("  %-4s %-52s expected=%-24s actual=%s"
              % ("PASS" if ok else "FAIL", name, expected, actual))

    def fresh(w):
        """close --all -> set credentials -> open -> set headers -> reload -> set viewport.

        * headers are scoped to the origin, so a document has to be on the host
          before they are set; setting them from about:blank parks them on the
          wrong origin and the run silently measures the live theme.
        * `open` discards them, `reload` keeps them.
        * `set viewport` re-lays out without dropping headers, and has to come
          last because `open` resets the width to 1280.
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

    ver = "2.10.48" if args.live else "2.10.50"
    print("=" * 78)
    print("Batch 2D step 4c — rendered evidence  (%s, header: %s)"
          % (args.page, "(none — live)" if args.live else "X-SF-Preflight: 1"))
    print("=" * 78)

    # ---------- 1440: alignment and width ----------
    print("\n[1] 1440 — the single card's left edge and width")
    fresh(1440)
    expect_sheet("sinofresh-theme/" if args.live else "-preflight",
                 "stylesheet is the live theme copy" if args.live
                 else "stylesheet really is the pre-flight copy", ver)
    a = ev(PROBE)
    print("      %s" % json.dumps(a, ensure_ascii=False))
    check("render is complete at 1440", a.get("rs") == "complete" and a.get("w") == 1440,
          "complete / 1440", "%s / %s" % (a.get("rs"), a.get("w")))
    check("exactly one card (the --solo state)", a.get("cardCount") == 1,
          "1", a.get("cardCount"))
    check("grid carries the --solo modifier", "--solo" in (a.get("cls") or ""),
          "--solo", a.get("cls"))
    check("single track is minmax(0, 560px)",
          (a.get("tracks") or "").replace(" ", "") == "560px",
          "560px", a.get("tracks"))
    check("card width is 560", a.get("cardW") == 560, "560", a.get("cardW"))
    check("card left == grid left (card does not float inside its track)",
          a.get("cardLeft") == a.get("gridLeft"),
          "cardLeft == gridLeft", "%s / %s" % (a.get("cardLeft"), a.get("gridLeft")))
    check("grid left == Specification h2 left", a.get("deltaVsSpecH2") == 0,
          "0px", "%spx" % a.get("deltaVsSpecH2"))
    check("grid left is x=120 (the 1200px measure's left edge)",
          a.get("gridLeft") == 120, "120", a.get("gridLeft"))
    check("grid left is shared with at least half the page's h2s",
          (a.get("h2SharedLeft") or 0) >= max(1, (a.get("h2Count") or 0) // 2),
          ">= half of %s h2" % a.get("h2Count"), a.get("h2SharedLeft"))
    check("no horizontal scroll at 1440", a.get("hScroll") is False, "False", a.get("hScroll"))
    print("      h2 lefts: %s" % " | ".join(a.get("h2s") or []))

    # ---------- 1440: negative control ----------
    print("\n[2] 1440 — negative control (hand the grid back its auto-fit tracks)")
    print("      %s" % ab("eval", NEUTRALISE))
    time.sleep(0.5)
    b = ev(PROBE)
    print("      %s" % json.dumps(b, ensure_ascii=False))
    grew = None
    if a.get("cardW") is not None and b.get("cardW") is not None:
        grew = b["cardW"] - a["cardW"]
    check("card fills the measure once the solo track is removed",
          grew is not None and grew > 400,
          "> +400px", "%s px (%s -> %s)" % (grew, a.get("cardW"), b.get("cardW")))
    check("neutralised track is not the solo one",
          (b.get("tracks") or "") != (a.get("tracks") or ""),
          "a different grid-template-columns",
          "%s vs %s" % (a.get("tracks"), b.get("tracks")))

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
          "<= 375", "%spx" % c.get("cardW"))
    check("track is capped at the available width, not at 560",
          c.get("cardW") is not None and c.get("cardW") < 560,
          "< 560", "%spx" % c.get("cardW"))
    check("grid left still on the Specification h2 edge at 375",
          c.get("deltaVsSpecH2") == 0, "0px", "%spx" % c.get("deltaVsSpecH2"))

    # ---------- screenshots ----------
    tag = "live" if args.live else "preflight"
    for label, w in (("1440", 1440), ("375", 375)):
        fresh(w)
        ab("scrollintoview", ".sf-fdetail__grid")
        time.sleep(1)
        ab("screenshot", os.path.join(args.out, "01-solo-%s-%s.png" % (tag, label)))
    ab("close", "--all")

    bad = [n for n, ok in results if not ok]
    print("\n" + "=" * 78)
    print("%s — %d/%d checks pass" % ("PASS" if not bad else "FAIL",
                                      len(results) - len(bad), len(results)))
    for n in bad:
        print("  * %s" % n)
    print("=" * 78)
    with open(os.path.join(args.out, "evidence%s.json" % ("-live" if args.live else "")),
              "w", encoding="utf-8") as fh:
        json.dump({"1440": a, "1440_neutralised": b, "375": c,
                   "checks": [{"name": n, "ok": ok} for n, ok in results]},
                  fh, ensure_ascii=False, indent=2)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
