#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch 2D Step 1 — browser checks (plan items 10, 11, 12).

Drives agent-browser through ONE daemon (open / navigate / close once), in a
fixed order with an explicit python subprocess chain: the shell loop / command
substitution pattern drifts the session (a later `eval` lands on about:blank).

Three things only a real browser can settle:

  10. the configurator still works — the eight dosage pages carry the K1
      formula buttons, and picking one must still reach sessionStorage. The new
      band sits between two sections, so anything that scans the page top-down
      could have been disturbed; this says it was not.
  11. the dot rail — toc-nav.js numbers the page by <h2>, and the new band adds
      one, so the rail goes 6 -> 7 with the new entry third. Its anchor must
      resolve and its click must actually land.
  12. mobile — 375px, no horizontal overflow, pills wrap, and the zh copy of the
      page renders the same band in English (no TP strings registered).

Credentials: dev.zxpet.com answers 401 without them, so the browser is armed
with HTTP Basic credentials BEFORE the first navigation.

    python3 tools/b2d_s1_browser.py
"""

import json
import os
import re
import subprocess
import sys
import time

BASE = "https://dev.zxpet.com"
USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
SHOTS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "docs", "b2d-step1-shots")

results = []


def ab(*args, timeout=120):
    p = subprocess.run(["agent-browser", *args], capture_output=True, text=True,
                       timeout=timeout)
    if p.returncode != 0 and p.stderr.strip():
        print("      !! agent-browser %s -> %s" % (" ".join(args), p.stderr.strip()[:200]))
    return p.stdout.strip()


def ev(js):
    """eval, then unwrap agent-browser's own JSON encoding of the result.

    The CLI prints the JS return value JSON-encoded, so a `JSON.stringify(...)`
    payload arrives quoted a second time ("\\"[{\\"a\\":1}]\\""). One parse
    removes the transport layer; a second, applied only when the payload is
    itself JSON, recovers the value. Without this `len(rail)` is the length of
    a string and every structural assertion silently compares the wrong type.
    """
    out = (ab("eval", js) or "").strip()
    if not out:
        return None
    out = out.splitlines()[-1].strip()
    try:
        out = json.loads(out)
    except Exception:
        return out
    if isinstance(out, str):
        s = out.strip()
        if s[:1] in '{["':
            try:
                out = json.loads(s)
            except Exception:
                pass
    return out


def check(name, expected, actual, ok=None):
    if ok is None:
        ok = expected == actual
    results.append(ok)
    print("  [%s] %-58s expect=%r got=%r"
          % ("PASS" if ok else "FAIL", name, expected, actual))


def main():
    os.makedirs(SHOTS, exist_ok=True)

    # ---------------------------------------------------------------- arm
    ab("set", "credentials", USER, PASS)
    ab("open", BASE + "/products/soft-chews/")
    ab("wait", "--load", "networkidle")
    ab("set", "viewport", "1440", "900")
    time.sleep(1.0)

    print("=== 11) dot rail (toc-nav.js) ===")
    title = ev("document.title")
    check("page loaded", True, "Soft Chews" in str(title))
    rail = ev("JSON.stringify([].slice.call(document.querySelectorAll('nav.sf-toc li a'))"
              ".map(function(a){return {href:a.getAttribute('href'),"
              "text:(a.querySelector('.sf-toc__label')||a).textContent.trim()}}))")
    print("       rail:", json.dumps(rail, ensure_ascii=False))
    check("rail item count", 7, len(rail))
    check("new item is 3rd", "Active Ingredients & Guaranteed Analysis",
          rail[2]["text"] if len(rail) > 2 else None)
    check("new item href", "#sf-sec-2", rail[2]["href"] if len(rail) > 2 else None)
    check("other entries unchanged",
          ["Standard Formulas", "Build Your Soft Chews Formula", "How We Work",
           "Frequently Asked Questions", "Related Dosage Forms",
           "Request a Soft Chews Quote"],
          [r["text"] for i, r in enumerate(rail) if i != 2])

    anchors = ev("JSON.stringify({actives: !!document.getElementById('actives'),"
                 "formulas: !!document.getElementById('formulas'),"
                 "configurator: !!document.getElementById('configurator'),"
                 "inquiry: !!document.getElementById('inquiry-form'),"
                 "sec2: (document.getElementById('sf-sec-2')||{}).textContent||null,"
                 "activesSection: (document.getElementById('actives')||{}).className||null})")
    print("       anchors:", json.dumps(anchors, ensure_ascii=False))
    check("anchor ids present", {"actives": True, "formulas": True,
                                 "configurator": True, "inquiry": True},
          {k: anchors[k] for k in ("actives", "formulas", "configurator", "inquiry")})
    check("#sf-sec-2 is the band's own heading", "Active Ingredients & Guaranteed Analysis",
          anchors["sec2"])
    check("#actives carries the group classes", True,
          "sf-actives" in anchors["activesSection"])

    # The rail is `opacity:0; pointer-events:none` above 200px of scroll
    # (.sf-toc--hidden), so a real click only lands once the page is scrolled.
    def arm_rail():
        ab("scroll", "up", "100000")
        ab("scroll", "down", "900")
        time.sleep(0.8)

    arm_rail()
    before = ev("Math.round(scrollY)")
    ab("click", "nav.sf-toc li:nth-child(3) a")
    time.sleep(2.0)
    after = ev("JSON.stringify({y:Math.round(scrollY),"
               "sec2Top:Math.round(document.getElementById('sf-sec-2')"
               ".getBoundingClientRect().top),"
               "hash:location.hash})")
    print("       scroll:", json.dumps(after, ensure_ascii=False), " (was", before, ")")
    check("rail click moved the page", True, after["y"] > before + 200)
    check("clicked item is at the header line", True, -40 <= after["sec2Top"] <= 130)
    check("hash updated", "#sf-sec-2", after["hash"])

    # Every rail entry must still land its own heading — walk all seven rather
    # than spot-check: toc-nav renumbers by document order, so an insertion
    # shifts every id after it, and only a full walk proves none of them broke.
    for i in range(len(rail)):
        arm_rail()
        ab("click", "nav.sf-toc li:nth-child(%d) a" % (i + 1))
        time.sleep(1.8)
        got = ev("JSON.stringify({y:Math.round(scrollY),"
                 "top:Math.round(document.getElementById('sf-sec-%d')"
                 ".getBoundingClientRect().top)})" % i)
        check("rail #%d lands #sf-sec-%d (%s)" % (i + 1, i, rail[i]["text"]),
              True, got["y"] > 60 and -40 <= got["top"] <= 130)

    ab("scroll", "up", "100000")
    time.sleep(0.5)
    ab("screenshot", os.path.join(SHOTS, "01-soft-chews-band-1440.png"))

    print("=== 10) configurator ===")
    n_cta = ev("document.querySelectorAll('.sf-formula__cta').length")
    check("K1 buttons on the page", 4, n_cta)
    ab("eval", "document.querySelector('.sf-formula__cta').scrollIntoView({block:'center'})")
    time.sleep(0.6)
    ab("click", ".sf-formula__cta")
    time.sleep(1.2)
    st = ev("JSON.stringify({formula:sessionStorage.getItem('sinofresh_formula_soft-chews'),"
            "toast:(document.querySelector('.sf-toast')||{}).textContent||null})")
    print("       sessionStorage:", json.dumps(st, ensure_ascii=False))
    check("formula pushed to sessionStorage", "Joint Support Soft Chews", st["formula"])
    check("a toast confirmed the pick", True,
          bool(str(st["toast"] or "").strip()))

    # The configurator's option buttons are .configurator__item inside a
    # .configurator__group[data-group]; picking one must reach the matching
    # .configurator__summary-row[data-group] value.
    n_opt = ev("document.querySelectorAll('.configurator__group[data-group=\"shape\"] .configurator__item').length")
    check("shape group offers options", True, isinstance(n_opt, int) and n_opt > 0)
    ab("eval", "document.querySelector('.configurator__group[data-group=\"shape\"] "
               ".configurator__item').scrollIntoView({block:'center'})")
    time.sleep(0.6)
    ab("click", ".configurator__group[data-group=\"shape\"] .configurator__item")
    time.sleep(1.0)
    filled = ev("JSON.stringify({shape:(document.querySelector("
                "'.configurator__summary-row[data-group=\"shape\"] .configurator__summary-value')"
                "||{}).textContent||null,"
                "selected:document.querySelectorAll('.configurator__item.is-selected').length,"
                "state:sessionStorage.getItem('sinofresh_config_soft-chews')})")
    print("       after picking a shape:", json.dumps(filled, ensure_ascii=False)[:260])
    check("summary card shows the picked value", "Bone", (filled["shape"] or "").strip())
    check("the button is marked selected", True, filled["selected"] >= 1)
    check("configuration persisted to sessionStorage", True, bool(filled["state"]))
    ab("screenshot", os.path.join(SHOTS, "02-configurator-1440.png"))

    print("=== 12) 375px + zh ===")
    ab("set", "viewport", "375", "812")
    ab("open", BASE + "/products/soft-chews/")
    ab("wait", "--load", "networkidle")
    time.sleep(1.2)
    ab("scroll", "down", "100000")
    time.sleep(1.2)
    m = ev("JSON.stringify({sw:document.documentElement.scrollWidth,"
           "cw:document.documentElement.clientWidth,"
           "items:document.querySelectorAll('.sf-actives__item').length,"
           "pills:document.querySelectorAll('.sf-actives__pill').length,"
           "rows:document.querySelectorAll('#actives .sf-spec-row').length,"
           "pillLines:(function(){var p=document.querySelectorAll('.sf-actives__pill');"
           "if(!p.length)return 0;var t=p[0].getBoundingClientRect().top,n=1;"
           "for(var i=1;i<p.length;i++){if(p[i].getBoundingClientRect().top>t+4){n++}}"
           "return n})()})")
    print("       mobile:", json.dumps(m, ensure_ascii=False))
    check("no horizontal overflow at 375", True, m["sw"] <= m["cw"] + 1)
    check("band present on mobile", (4, 24, 8), (m["items"], m["pills"], m["rows"]))
    check("pills wrap to more than one line", True, m["pillLines"] > 1)
    ab("eval", "document.getElementById('actives').scrollIntoView()")
    time.sleep(0.8)
    ab("screenshot", os.path.join(SHOTS, "03-soft-chews-band-375.png"))

    ab("open", BASE + "/zh/products/soft-chews/")
    ab("wait", "--load", "networkidle")
    time.sleep(1.0)
    z = ev("JSON.stringify({lang:document.documentElement.lang,"
           "items:document.querySelectorAll('.sf-actives__item').length,"
           "title:(document.querySelector('.sf-actives__title')||{}).textContent||null})")
    print("       zh:", json.dumps(z, ensure_ascii=False))
    check("/zh/ band renders too", (4, "Active Ingredients & Guaranteed Analysis"),
          (z["items"], z["title"]))
    ab("screenshot", os.path.join(SHOTS, "04-zh-soft-chews-band-375.png"))

    print("=== console / page errors ===")
    errs = ab("errors")
    cons = ab("console")
    print("       errors:", (errs or "(none)")[:300])
    print("       console:", (cons or "(none)")[:300])
    check("no page errors", True, not re.search(r"Error|error:", errs or ""))

    ab("close")
    print("\n%d/%d browser checks passed" % (sum(results), len(results)))
    return 0 if all(results) else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    finally:
        subprocess.run(["agent-browser", "close"], capture_output=True)
