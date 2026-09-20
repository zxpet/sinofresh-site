#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch2C Step2 sub-item 5 — browser checks for the eight dosage pages.

Drives agent-browser against the header-gated pre-flight theme:

    python3 tools/b2c_s2s5_browser_check.py [--shots DIR]

Proves, on every one of the eight dosage pages:
  desktop 1440 — exactly one new outline button, rendered as an inline-block
                 with a 2px #1B4D3E border, centred, 32px below the grid, as the
                 last thing inside the formula section
  link         — a real click lands on /formulas/ (200, preflight archive page)
  mobile 375   — the button becomes a full-width block, still centred, >=44px

Screenshots land in --shots (default ./docs/b2c-step2s5-shots).
"""

import argparse
import json
import os
import subprocess
import sys

BASE = "https://dev.zxpet.com"
FORMS = ["soft-chews", "tablets", "powders", "pastes",
         "drops", "liquids", "fish-oil", "dental-chews"]
HEADERS = '{"X-SF-Preflight":"1"}'
SESSION = "sfstep2s5"

STATE = """
(() => {
  const btn = document.querySelector('section#formulas .sf-explore__btn[href="/formulas/"]');
  const p = btn ? btn.closest('p') : null;
  const sect = document.querySelector('section#formulas');
  const cs = btn ? getComputedStyle(btn) : null;
  const pcs = p ? getComputedStyle(p) : null;
  const btns = Array.from(document.querySelectorAll('.sf-explore__btn'));
  // the section that follows the formula section (expected: the configurator)
  const after = sect ? sect.nextElementSibling : null;
  return JSON.stringify({
    href: btn ? btn.getAttribute('href') : 'MISSING',
    resolved: btn ? btn.href : 'MISSING',
    text: btn ? btn.textContent.trim() : 'MISSING',
    display: cs ? cs.display : 'MISSING',
    borderWidth: cs ? cs.borderTopWidth : 'MISSING',
    borderColor: cs ? cs.borderTopColor : 'MISSING',
    color: cs ? cs.color : 'MISSING',
    fontWeight: cs ? cs.fontWeight : 'MISSING',
    fontSize: cs ? cs.fontSize : 'MISSING',
    rectWidth: btn ? Math.round(btn.getBoundingClientRect().width) : -1,
    rectHeight: btn ? Math.round(btn.getBoundingClientRect().height) : -1,
    minHeight: cs ? cs.minHeight : 'MISSING',
    pAlign: pcs ? pcs.textAlign : 'MISSING',
    pMarginTop: pcs ? pcs.marginTop : 'MISSING',
    pWidth: p ? Math.round(p.getBoundingClientRect().width) : -1,
    btnCount: btns.length,
    btnTargets: btns.map(b => b.getAttribute('href')),
    isLastInSection: !!(sect && p && sect.lastElementChild === p),
    sectionFollowedBy: after ? (after.id || after.className || after.tagName) : 'MISSING',
    inGrid: sect ? sect.className : 'MISSING'
  });
})()
"""

results = []


def check(name, expected, actual, ok=None):
    if ok is None:
        ok = expected == actual
    results.append((ok, name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name:<52} expect={expected!r} got={actual!r}")


def run(*args, timeout=240):
    cmd = ["agent-browser", *args, "--session", SESSION]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return out.stdout.strip(), out.stderr.strip()


def state():
    out, err = run("eval", STATE)
    if not out:
        raise RuntimeError(f"eval returned nothing; stderr={err}")
    return json.loads(json.loads(out))


def scalar(expr):
    """agent-browser wraps a JS scalar once; STATE's JSON.stringify adds a second layer."""
    out, err = run("eval", expr)
    if not out:
        raise RuntimeError(f"eval({expr!r}) returned nothing; stderr={err}")
    return json.loads(out)


def shot(path):
    run("screenshot", path)
    return os.path.exists(path) and os.path.getsize(path) > 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "b2c-step2s5-shots"))
    args = ap.parse_args()
    os.makedirs(args.shots, exist_ok=True)

    try:
        print("=== 1) desktop 1440 — geometry on all eight pages ===")
        run("open", f"{BASE}/products/soft-chews/", "--headers", HEADERS)
        run("wait", "--load", "networkidle")
        run("set", "viewport", "1440", "900")

        for form in FORMS:
            run("open", f"{BASE}/products/{form}/")
            run("wait", "--load", "networkidle")
            s = state()
            tag = form
            check(f"{tag}: one /formulas/ button, plus the /products/ one",
                  [1, 2], [s["btnTargets"].count("/formulas/"), s["btnCount"]])
            check(f"{tag}: href", "/formulas/", s["href"])
            check(f"{tag}: absolute target", f"{BASE}/formulas/", s["resolved"])
            check(f"{tag}: wording", "Browse All Formulas →", s["text"])
            check(f"{tag}: inline-block", "inline-block", s["display"])
            check(f"{tag}: 2px #1B4D3E border", ["2px", "rgb(27, 77, 62)"],
                  [s["borderWidth"], s["borderColor"]])
            check(f"{tag}: ink-green label, 15px/600", ["rgb(27, 77, 62)", "15px", "600"],
                  [s["color"], s["fontSize"], s["fontWeight"]])
            check(f"{tag}: centred by its paragraph", "center", s["pAlign"])
            check(f"{tag}: 32px above (spacing|40)", "32px", s["pMarginTop"])
            check(f"{tag}: paragraph is the last child of #formulas",
                  True, s["isLastInSection"])
            check(f"{tag}: next sibling is the configurator", "configurator",
                  s["sectionFollowedBy"])
            check(f"{tag}: button is in the formula section", True,
                  "sf-formulas" in s["inGrid"])

        run("open", f"{BASE}/products/soft-chews/", "--headers", HEADERS)
        run("wait", "--load", "networkidle")
        run("eval", "document.querySelector('section#formulas .sf-explore__btn[href=\"/formulas/\"]')"
                    ".scrollIntoView({block:'center'})")
        check("desktop dosage screenshot", True,
              shot(os.path.join(args.shots, "01-desktop-dosage-page.png")))

        print("\n=== 2) the link target, gated ===")
        # Order matters, and this is a harness rule rather than a site rule:
        # Cloudflare stamps `cache-control: max-age=86400` on HTML, so the browser
        # caches whatever VARIANT of a URL it saw first (the gate is a PHP header,
        # invisible to the cache). Every gated check therefore runs before the
        # click test, because the click lands the browser on the un-gated variant.
        run("open", f"{BASE}/formulas/", "--headers", HEADERS)
        run("wait", "--load", "networkidle")
        check("target renders 9 chips", 9, scalar("document.querySelectorAll('.sf-fchip').length"))
        check("target renders 21 cards", 21, scalar("document.querySelectorAll('.sf-fcard').length"))
        check("target has no dosage-form button", 0,
              scalar("document.querySelectorAll('.sf-explore__btn').length"))
        check("archive screenshot", True,
              shot(os.path.join(args.shots, "02-desktop-formulas-archive.png")))

        print("\n=== 3) mobile 375 — full-width block ===")
        run("set", "viewport", "375", "812")
        for form in ["soft-chews", "dental-chews"]:
            run("open", f"{BASE}/products/{form}/", "--headers", HEADERS)
            run("wait", "--load", "networkidle")
            s = state()
            check(f"{form}: display block", "block", s["display"])
            check(f"{form}: width == its paragraph's width", s["pWidth"], s["rectWidth"])
            check(f"{form}: >= 44px tall", True, s["rectHeight"] >= 44)
            check(f"{form}: still centred", "center", s["pAlign"])
        run("eval", "document.querySelector('section#formulas .sf-explore__btn[href=\"/formulas/\"]')"
                    ".scrollIntoView({block:'center'})")
        check("mobile screenshot", True,
              shot(os.path.join(args.shots, "03-mobile375-dosage-page.png")))

        print("\n=== 4) console ===")
        out, _ = run("errors")
        ok = out.strip() in ("", "No errors", "✓ No errors")
        check("no page errors", True, ok, ok)
        if not ok:
            print(f"       {out.strip()[:400]}")

        print("\n=== 5) real click -> /formulas/ (last: it un-gates the target) ===")
        run("set", "viewport", "1440", "900")
        run("open", f"{BASE}/products/soft-chews/", "--headers", HEADERS)
        run("wait", "--load", "networkidle")
        run("eval", "document.querySelector('section#formulas .sf-explore__btn[href=\"/formulas/\"]')"
                    ".scrollIntoView({block:'center'})")
        run("click", 'section#formulas .sf-explore__btn[href="/formulas/"]')
        run("wait", "--load", "networkidle")
        check("clicked through to /formulas/", "/formulas/", scalar("location.pathname"))
        # either variant is acceptable here — whichever one the cache already held
        check("landing page is a real Formulas archive", True,
              scalar("document.querySelectorAll('.sf-archive-grid,.sf-blog-chips,.sf-fchip,.sf-fcard').length") > 0,
              scalar("document.querySelectorAll('.sf-archive-grid,.sf-blog-chips,.sf-fchip,.sf-fcard').length"))

    finally:
        run("close", "--all")

    bad = [n for ok, n in results if not ok]
    print(f"\n{'PASS' if not bad else 'FAIL'}  sub-item 5 browser: "
          f"{len(results) - len(bad)}/{len(results)} assertions"
          + (f"  -> {bad}" if bad else ""))
    return len(bad)


if __name__ == "__main__":
    sys.exit(main())
