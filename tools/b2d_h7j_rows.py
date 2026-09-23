#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""H7j header-row probe — what the 20px gap did to the header's own flex lines.

The gap measurement showed one number that needs explaining before it can be
asserted:

    width   build           navBox        headerH
    900     live 2.10.69    382..862      139
    900     pre  2.10.71    320..862      139
    820     live 2.10.69    302..782      139
    820     pre  2.10.71     38..580      139

At 900 the nav grows leftwards with its right edge pinned to the container's
right edge (782 -> 862 is the content box), which is what a `space-between`
header does when the middle item grows. At 820 the preflight nav sits at the
gutter instead, i.e. it is no longer sharing the line with the logo and the CTA.
The header height is 139 in both builds, so nothing got taller — but "the same
height" is not the same as "the same arrangement", and asserting the arrangement
without knowing it would be asserting a guess.

This probe reports, per header child, its flex line (grouped by rounded top),
so the wrap point is read rather than inferred. Run for both builds:

    tools/b2d_h7j_rows.py --mode live
    tools/b2d_h7j_rows.py --mode pre
"""
import argparse
import base64
import json
import subprocess
import sys
import time

USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
BASE = "https://dev.zxpet.com"
B64 = base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()

PATH = "/products/soft-chews/"
WIDTHS = [1440, 1100, 1024, 1000, 960, 900, 860, 820, 800, 768, 600, 375]
HEIGHT = 900

ROWS = """(() => {
  const H = document.querySelector('header.sf-header');
  if (!H) return { present: false };
  const R = e => { const b = e.getBoundingClientRect();
    return { t: Math.round(b.top), l: Math.round(b.left), r: Math.round(b.right),
             w: Math.round(b.width), h: Math.round(b.height) }; };
  const cs = getComputedStyle(H);
  const kids = Array.from(H.children).map(k => ({
    cls: (k.className || k.tagName).toString().slice(0, 60),
    disp: getComputedStyle(k).display, box: R(k),
    text: (k.textContent || '').trim().slice(0, 24) }));
  const nav = H.querySelector('nav');
  const navUL = nav ? nav.querySelector('ul') : null;
  const items = navUL ? Array.from(navUL.children) : [];
  const headerBox = R(H);
  return { present: true, vw: innerWidth,
           header: headerBox, padL: cs.paddingLeft, padR: cs.paddingRight,
           flexWrap: cs.flexWrap, justify: cs.justifyContent,
           overflow: document.documentElement.scrollWidth > innerWidth,
           kids,
           navBox: nav ? R(nav) : null,
           navULBox: navUL ? R(navUL) : null,
           navGap: navUL ? getComputedStyle(navUL).columnGap : null,
           nItems: items.length,
           hamburger: !!H.querySelector('.wp-block-navigation__responsive-container-open'),
           openVisible: (() => { const b = H.querySelector('.wp-block-navigation__responsive-container-open');
             if (!b) return null; const s = getComputedStyle(b);
             return s.display !== 'none' && b.getBoundingClientRect().width > 0; })(),
           containerVisible: (() => { const c = H.querySelector('.wp-block-navigation__responsive-container');
             if (!c) return null; const b = c.getBoundingClientRect();
             return getComputedStyle(c).display !== 'none' && b.width > 0; })() };
})()"""


def ab(*a, timeout=180):
    p = subprocess.run(["agent-browser", *a], capture_output=True, text=True, timeout=timeout)
    return p.stdout.strip()


def ev(js):
    p = subprocess.run(["agent-browser", "eval", js], capture_output=True, text=True, timeout=180)
    raw = p.stdout.strip()
    if not raw:
        raise RuntimeError("eval returned nothing; stderr=%s" % p.stderr.strip()[:400])
    try:
        once = json.loads(raw)
    except Exception:
        return raw
    if isinstance(once, str):
        try:
            return json.loads(once)
        except Exception:
            return once
    return once


def session(mode):
    ab("close", "--all")
    time.sleep(1.0)
    ab("open", BASE + "/")
    time.sleep(2.2)
    if mode == "pre":
        ab("set", "headers", json.dumps({"X-SF-Preflight": "1",
                                         "Authorization": "Basic " + B64}))
        time.sleep(0.6)
        ab("reload")
        time.sleep(2.5)
    else:
        ab("set", "credentials", USER, PASS)
        time.sleep(0.6)
        ab("open", BASE + "/")
        time.sleep(2.2)


def set_viewport(w, h):
    for _ in range(4):
        ab("set", "viewport", str(w), str(h))
        time.sleep(0.7)
        got = ev("JSON.stringify({w: innerWidth})")
        if isinstance(got, dict) and got.get("w") == w:
            return True
        time.sleep(0.5)
    return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["live", "pre"], required=True)
    ap.add_argument("--path", default=PATH)
    ap.add_argument("--widths", default="")
    args = ap.parse_args()

    widths = [int(x) for x in args.widths.split(",") if x.strip()] or WIDTHS
    session(args.mode)

    out = []
    for w in widths:
        ab("open", BASE + args.path)
        time.sleep(2.0)
        if not set_viewport(w, HEIGHT):
            print("viewport %d did not take" % w, file=sys.stderr)
            continue
        r = ev(ROWS)
        out.append(r)
        lines = {}
        for k in r["kids"]:
            lines.setdefault(k["box"]["t"], []).append(k)
        print("== %-5d header=%sx%s pad=%s/%s wrap=%s justify=%s hamburger=%s(vis=%s) "
              "navGap=%s items=%s overflow=%s"
              % (w, r["header"]["w"], r["header"]["h"], r["padL"], r["padR"],
                 r["flexWrap"], r["justify"], r["hamburger"], r["openVisible"],
                 r["navGap"], r["nItems"], r["overflow"]))
        for top in sorted(lines):
            row = lines[top]
            print("     line y=%-5s %s" % (top, "  ".join(
                "%s[%s..%s]" % (k["disp"], k["box"]["l"], k["box"]["r"]) for k in row)))
        print("     %s" % "  ".join("%s '%s'" % (k["cls"][:26], k["text"])
                                    for k in r["kids"]))

    fn = "_backup/b2d-h7j-rows-%s.json" % args.mode
    with open(fn, "w", encoding="utf-8") as fh:
        json.dump({"mode": args.mode, "path": args.path, "rows": out}, fh, indent=1)
    print("\nwrote", fn)


if __name__ == "__main__":
    main()
