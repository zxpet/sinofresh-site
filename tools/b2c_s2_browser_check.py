#!/usr/bin/env python3
"""Batch2C Step2 sub-item 4 — browser-side checks for the /formulas/ filter.

Drives agent-browser against the header-gated pre-flight theme:

    python3 tools/b2c_s2_browser_check.py [--shots DIR]

What it proves, in the order a visitor meets it:
  desktop 1440 — the bar renders, the rail is a wrapping row, 4 grid columns,
                 all 21 cards visible before any click
  filtered     — a real click on "Soft Chews" leaves 4 cards visible and 17
                 hidden, moves aria-pressed and the role="status" count
  reset        — clicking "All" brings all 21 back
  no-JS        — with the head marker removed the bar hides itself and all 21
                 cards stay visible (no dead buttons, no reflow of the grid)
  mobile 375   — the rail turns into a nowrap scroller and the grid drops to a
                 single column

Screenshots land in --shots (default ./docs/b2c-step2-shots).
"""

import argparse
import json
import os
import subprocess
import sys

URL = "https://dev.zxpet.com/formulas/"
HEADERS = '{"X-SF-Preflight":"1"}'
SESSION = "sfstep2"

STATE = """
(() => {
  const wrap = document.querySelector('.sf-fchips-wrap');
  const bar = document.querySelector('.sf-fchips');
  const grid = document.querySelector('.sf-fgrid');
  const cards = Array.from(document.querySelectorAll('.sf-fgrid .sf-fcard'));
  const chips = Array.from(document.querySelectorAll('.sf-fchip'));
  const vis = cards.filter(c => c.offsetParent !== null);
  const status = document.querySelector('.sf-fchips-status');
  return JSON.stringify({
    sfJs: document.documentElement.classList.contains('sf-js'),
    wrapDisplay: wrap ? getComputedStyle(wrap).display : 'MISSING',
    chipCount: chips.length,
    chipLabels: chips.map(c => c.textContent.trim()),
    pressed: chips.filter(c => c.getAttribute('aria-pressed') === 'true').map(c => c.dataset.sfForm),
    active: chips.filter(c => c.classList.contains('is-active')).map(c => c.dataset.sfForm),
    cardCount: cards.length,
    visible: vis.length,
    hidden: cards.length - vis.length,
    visibleForms: Array.from(new Set(vis.map(c => c.dataset.sfForm))).sort(),
    status: status ? status.textContent.replace(/\\s+/g, ' ').trim() : 'MISSING',
    railWrap: bar ? getComputedStyle(bar).flexWrap : '',
    railDisplay: bar ? getComputedStyle(bar).display : '',
    railOverflowX: bar ? getComputedStyle(bar).overflowX : '',
    railScrollable: bar ? (bar.scrollWidth > bar.clientWidth + 1) : false,
    railWidth: bar ? Math.round(bar.getBoundingClientRect().width) : -1,
    cols: grid ? getComputedStyle(grid).gridTemplateColumns.split(' ').filter(Boolean).length : 0,
    docHeight: document.documentElement.scrollHeight,
    gridTop: grid ? Math.round(grid.getBoundingClientRect().top + window.scrollY) : -1
  });
})()
"""

results = []


def check(name, expected, actual, ok=None):
    if ok is None:
        ok = expected == actual
    results.append((ok, name))
    print(f"  [{'PASS' if ok else 'FAIL'}] {name:<54} expect={expected!r} got={actual!r}")


def run(*args, timeout=180):
    cmd = ["agent-browser", *args, "--session", SESSION]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    return out.stdout.strip(), out.stderr.strip()


def state():
    out, err = run("eval", STATE)
    if not out:
        raise RuntimeError(f"eval returned nothing; stderr={err}")
    return json.loads(json.loads(out))


def shot(path):
    run("screenshot", "--full", path)
    return os.path.exists(path) and os.path.getsize(path) > 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shots", default=os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "docs", "b2c-step2-shots"))
    args = ap.parse_args()
    os.makedirs(args.shots, exist_ok=True)

    print("=== 0) desktop 1440 — before any click ===")
    run("open", URL, "--headers", HEADERS)
    run("wait", "--load", "networkidle")
    run("set", "viewport", "1440", "900")
    run("open", URL)          # re-navigate so the new viewport is in effect
    run("wait", "--load", "networkidle")
    s = state()
    check("preflight active (21 cards)", 21, s["cardCount"])
    check("sf-js marker present", True, s["sfJs"])
    check("filter bar visible (wrap not display:none)", True, s["wrapDisplay"] != "none")
    check("chip rail is a flex row", "flex", s["railDisplay"])
    check("chips", 9, s["chipCount"])
    check("chip order", ["All", "Soft Chews", "Tablets", "Powders", "Pastes",
                         "Drops", "Liquids", "Fish Oil", "Dental Chews"], s["chipLabels"])
    check("All pressed by default", ["all"], s["pressed"])
    check("All active by default", ["all"], s["active"])
    check("all 21 visible, none hidden", (21, 0), (s["visible"], s["hidden"]))
    check("status line", "Showing 21 of 21 formulas", s["status"])
    check("grid columns @1440", 4, s["cols"])
    check("rail wraps on desktop", "wrap", s["railWrap"])
    base_top, base_h = s["gridTop"], s["docHeight"]
    print(f"       grid top={base_top}px  document height={base_h}px")
    shot(os.path.join(args.shots, "formulas-desktop-1440.png"))

    print("=== 1) click Soft Chews (real click) ===")
    run("click", '.sf-fchip[data-sf-form="soft-chews"]')
    s = state()
    check("visible cards", 4, s["visible"])
    check("hidden cards", 17, s["hidden"])
    check("visible forms", ["soft-chews"], s["visibleForms"])
    check("aria-pressed = soft-chews only", ["soft-chews"], s["pressed"])
    check("is-active = soft-chews only", ["soft-chews"], s["active"])
    check("status line", "Showing 4 of 21 formulas", s["status"])
    check("document height shrinks (no ghost rows)", True, s["docHeight"] < base_h)
    shot(os.path.join(args.shots, "formulas-filtered-soft-chews.png"))

    print("=== 2) click All to reset ===")
    run("click", '.sf-fchip[data-sf-form="all"]')
    s = state()
    check("all 21 visible again", (21, 0), (s["visible"], s["hidden"]))
    check("aria-pressed back to All", ["all"], s["pressed"])
    check("status line", "Showing 21 of 21 formulas", s["status"])

    print("=== 3) no-JS degradation (head marker removed) ===")
    run("eval", "document.documentElement.classList.remove('sf-js'); 'ok'")
    s = state()
    check("filter bar hidden", "none", s["wrapDisplay"])
    check("all 21 cards still visible", (21, 0), (s["visible"], s["hidden"]))
    check("no dead buttons reachable", True, s["wrapDisplay"] == "none")
    check("grid still 4 columns", 4, s["cols"])
    print(f"       grid top={s['gridTop']}px  document height={s['docHeight']}px "
          f"(band collapses to its own padding: {base_h - s['docHeight']}px)")
    shot(os.path.join(args.shots, "formulas-nojs-marker-removed.png"))
    run("eval", "document.documentElement.classList.add('sf-js'); 'ok'")

    print("=== 4) mobile 375 ===")
    run("set", "viewport", "375", "812")
    run("open", URL)
    run("wait", "--load", "networkidle")
    s = state()
    check("preflight still active", 21, s["cardCount"])
    check("chips still 9", 9, s["chipCount"])
    check("rail is a nowrap scroller", ("nowrap", "auto"), (s["railWrap"], s["railOverflowX"]))
    check("rail actually overflows (swipeable)", True, s["railScrollable"],
          s["railScrollable"])
    check("single grid column @375", 1, s["cols"])
    check("all 21 visible", 21, s["visible"])
    print(f"       rail width={s['railWidth']}px")
    shot(os.path.join(args.shots, "formulas-mobile-375.png"))
    run("click", '.sf-fchip[data-sf-form="tablets"]')
    s = state()
    check("filter works on mobile too", (3, 18), (s["visible"], s["hidden"]))
    shot(os.path.join(args.shots, "formulas-mobile-375-filtered.png"))

    print("=== 5) console errors ===")
    out, _ = run("errors")
    check("no page errors", True, out.strip() in ("", "No errors", "✓ No errors"))
    if out.strip() not in ("", "No errors", "✓ No errors"):
        print(f"       {out.strip()[:400]}")

    run("close")
    failed = [n for ok, n in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    for name in failed:
        print(f"  FAILED: {name}")
    return len(failed)


if __name__ == "__main__":
    sys.exit(main())
