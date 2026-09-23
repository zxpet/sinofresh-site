#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7k evidence frames.

Fifteen frames, one per claim worth looking at, written to docs/batchH7k-shots/.

Three mechanics that are not obvious, and are why this is a script rather than a
handful of CLI calls:

  * every frame is a FULL-PAGE capture cropped afterwards by the target's
    absolute page rect, scaled by the capture's own ratio to the document size.
    Element-clipped screenshots come back pure white once the page has been
    scrolled — the tool crops by page coordinates and captures by viewport
    coordinates — so "clip to the element" silently writes a blank file that
    looks like a CSS bug.
  * every crop is checked for being non-flat before it is reported, at least 9
    distinct colours. A one-colour crop is a failed capture, not a finding.
  * 待办17's badge renders NOWHERE on this data set — no record carries the
    value, and the batch is forbidden from touching post meta. So the three
    frames for it are taken with a badge INJECTED into the live DOM at the same
    place the renderer would put it (a sibling of the still, inside the figure)
    with the same class the renderer emits. That shows the overlay and its three
    colours; it does not and cannot show that a record reaches that class, which
    is what the render harness and the source claims are for.

Run against the PREFLIGHT copy (2.10.72).

    tools/b2d_h7k_shots.py
"""
import base64
import json
import os
import subprocess
import sys
import time

from PIL import Image

USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
BASE = "https://dev.zxpet.com"
PF = json.dumps({"X-SF-Preflight": "1",
                 "Authorization": "Basic " + base64.b64encode(
                     ("%s:%s" % (USER, PASS)).encode()).decode()})
OUT = "docs/batchH7k-shots"
TMP = "_backup/_h7k_shots_tmp"

FORMULAS = "/formulas/"
DROPS = "/products/drops/"
ZH_DROPS = "/zh/products/drops/"
TOUR = "/factory-tour/"
SERVICES = "/services/"


def ab(*a, timeout=240):
    return subprocess.run(["agent-browser", *a], capture_output=True,
                          text=True, timeout=timeout).stdout.strip()


def ev(js):
    raw = ab("eval", js)
    if not raw:
        raise RuntimeError("eval returned nothing")
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


def session():
    ab("close", "--all")
    time.sleep(1.0)
    ab("open", BASE + "/")
    time.sleep(2.2)
    ab("set", "headers", PF)
    time.sleep(0.6)
    ab("reload")
    time.sleep(2.5)


def prescroll(step=700, pause=0.45, settle=1.3):
    """Walk the page down and back so every section is revealed.

    Sections below the fold are given `.sf-pending` by assets/js/interactions.js
    and hidden by `.sf-motion .wp-site-blocks > .wp-block-group.sf-pending
    { opacity: 0; transform: translateY(20px) }` until an IntersectionObserver
    removes the class. A full-page capture of a page that has never been
    scrolled therefore paints those sections as flat background — which is
    exactly how the three home-page strip frames came back at one colour while
    the zh twin, already revealed, came back with 509 at the same crop size.

    The reveal is one-way, so scrolling back to the top keeps it. The leftover
    count is RETURNED rather than assumed: a frame shot while any section is
    still pending is a blank frame, and the difference between "the CSS is
    broken" and "the capture is blank" is the whole reason this is checked.
    """
    info = ev("JSON.stringify({h: document.documentElement.scrollHeight})") or {}
    total = info.get("h") or 0
    y = 0
    while y < total:
        ab("eval", "window.scrollTo(0, %d)" % y)
        time.sleep(pause)
        y += step
    left = int((ev("JSON.stringify({n: document.querySelectorAll('.sf-pending').length})")
                or {}).get("n") or 0)
    ab("eval", "window.scrollTo(0, 0)")
    time.sleep(settle)
    return left


def at(path, w, h=900, settle=2.2):
    ab("open", BASE + path)
    time.sleep(settle)
    for _ in range(4):
        ab("set", "viewport", str(w), str(h))
        time.sleep(0.8)
        got = ev("JSON.stringify({w: innerWidth, dpr: devicePixelRatio, "
                 "p: location.pathname, t: document.title})")
        if isinstance(got, dict) and got.get("w") == w and got.get("p") == path:
            pending = prescroll()
            if pending:
                print("    !! %d sections still unrevealed on %s" % (pending, path))
            # The cookie banner is `position: fixed`, so a full-page capture
            # paints it wherever the viewport happened to be and it lands
            # across the middle of whatever is being shown. It is a pre-existing
            # site-wide overlay that this batch does not touch, so for a
            # component frame it is noise rather than evidence — hidden here,
            # and said so, rather than left to obscure a card row.
            hid = ev("""(() => { let n = 0;
              document.querySelectorAll('.sf-cookie-banner').forEach(e => {
                e.style.display = 'none'; n++; });
              return JSON.stringify({hidden: n}); })()""")
            if (hid or {}).get("hidden"):
                print("    (hid %s fixed cookie banner(s) for the capture)"
                      % hid.get("hidden"))
            return got
        time.sleep(0.5)
    raise SystemExit("viewport %d did not take on %s" % (w, path))


def whose():
    """Which artifact answered — asserted before anything is shot."""
    return ev("""(() => {
      const l = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(x => x.href);
      const theme = l.find(h => h.includes('sinofresh-theme')) || '';
      return { path: location.pathname, theme,
               pre: theme.includes('-preflight') && !/themes\\/sinofresh-theme\\//.test(theme),
               v72: theme.includes('ver=2.10.72') }; })()""")


def rect(sel):
    return ev("""(() => {
      const e = document.querySelector(%s);
      if (!e) return null;
      const r = e.getBoundingClientRect();
      return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height,
               dpr: devicePixelRatio,
               docW: document.documentElement.scrollWidth,
               docH: document.documentElement.scrollHeight }; })()""" % json.dumps(sel))


FRAMES = []


def shoot(name, sel, pad=0, pad_top=None, mincolours=9):
    r = rect(sel)
    if not r:
        print("FAIL %-44s no element %s" % (name, sel))
        return False
    pt = pad if pad_top is None else pad_top
    full = os.path.join(TMP, name + "-full.png")
    ab("screenshot", "--full", full)
    if not os.path.exists(full):
        print("FAIL %-44s no capture" % name)
        return False
    im = Image.open(full)
    sx, sy = im.width / float(r["docW"]), im.height / float(r["docH"])
    box = (max(0, int((r["x"] - pad) * sx)),
           max(0, int((r["y"] - pt) * sy)),
           min(im.width, int((r["x"] + r["w"] + pad) * sx)),
           min(im.height, int((r["y"] + r["h"] + pad) * sy)))
    crop = im.crop(box).convert("RGB")
    cols = crop.getcolors(maxcolors=1 << 20) or []
    names = len(cols)
    ok = names >= mincolours
    crop.save(os.path.join(OUT, name + ".png"))
    FRAMES.append((name, crop.width, crop.height, names, ok))
    # A flat crop has two possible causes and they are not interchangeable: the
    # CSS really paints nothing, or the capture missed because the section was
    # still hidden by the scroll-reveal. Name which, at the moment it happens.
    why = ""
    if not ok:
        pend = (ev("JSON.stringify({n: document.querySelectorAll('.sf-pending').length,"
                   " y: window.scrollY})") or {})
        why = "  <-- .sf-pending=%s scrollY=%s" % (pend.get("n"), pend.get("y"))
    print("%s %-46s %4dx%-5d colours=%-6d dpr=%.0f%s"
          % ("OK  " if ok else "FLAT", name, crop.width, crop.height, names,
             r["dpr"] or 1, why))
    return ok


def inject_badges():
    """Put the badge where the renderer puts it — a SIBLING of the still, inside
    the figure, not inside the link — using the same class the renderer emits."""
    return ev("""(() => {
      const kinds = [['best-seller', 'Best Seller'], ['hot', 'Hot'], ['new', 'New']];
      const figs = Array.from(document.querySelectorAll('figure.sf-fcard__media')).slice(0, 3);
      figs.forEach((f, i) => {
        const [k, label] = kinds[i % 3];
        const s = document.createElement('span');
        s.className = 'sf-fcard__badge sf-fcard__badge--' + k;
        s.textContent = label;
        f.appendChild(s);
      });
      const a = figs[0] && figs[0].querySelector('a.sf-fcard__imagelink');
      return { injected: figs.length,
               badgeInsideLink: a ? a.querySelectorAll('.sf-fcard__badge').length : null,
               first: figs[0] ? getComputedStyle(figs[0].querySelector('.sf-fcard__badge')).backgroundColor : null };
    })()""")


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    session()

    # ---- 待办14 — the still is a link ------------------------------------
    at(FORMULAS, 1440)
    print("  serving:", json.dumps(whose()))
    shoot("h7k-01-card-wall-formulas-1440", ".sf-fgrid", pad=0)
    shoot("h7k-02-one-card-still-in-link", "article.sf-fcard", pad=6)
    at(DROPS, 1440)
    print("  serving:", json.dumps(whose()))
    shoot("h7k-03-card-wall-drops-1440", ".sf-fgrid", pad=0)
    at(ZH_DROPS, 1440)
    print("  serving:", json.dumps(whose()))
    shoot("h7k-04-zh-twin-card-wall", ".sf-fgrid", pad=0)

    # ---- 待办17 — the badge, injected because no record carries one -------
    at(FORMULAS, 1440)
    print("  serving:", json.dumps(whose()))
    print("  inject:", json.dumps(inject_badges()))
    time.sleep(0.6)
    shoot("h7k-05-three-badges-all-colours", "article.sf-fcard")
    shoot("h7k-06-one-card-badge-closeup", "figure.sf-fcard__media", pad=4)
    at(FORMULAS, 768)
    print("  serving:", json.dumps(whose()))
    print("  inject:", json.dumps(inject_badges()))
    time.sleep(0.6)
    shoot("h7k-07-badge-at-768", "article.sf-fcard", pad=4)

    # ---- 待办18 — the strip, at the three widths it changes at ------------
    for i, w in ((8, 1440), (9, 768), (10, 375)):
        at("/", w)
        print("  serving:", json.dumps(whose()))
        shoot("h7k-%02d-certstrip-%d" % (i, w), ".sf-certstrip", pad=8,
              mincolours=6)
    at("/zh/", 1440)
    print("  serving:", json.dumps(whose()))
    shoot("h7k-11-zh-certstrip-1440", ".sf-certstrip", pad=8, mincolours=6)

    # ---- 待办19 — the checklist, one row or two --------------------------
    at(TOUR, 1440)
    print("  serving:", json.dumps(whose()))
    shoot("h7k-12-tour-columns-1440", ".wp-block-columns.sf-prepare", pad=10)
    at(TOUR, 375)
    print("  serving:", json.dumps(whose()))
    shoot("h7k-13-tour-columns-375", ".wp-block-columns.sf-prepare", pad=10)

    # ---- 待办22 — the table against its heading --------------------------
    at(SERVICES, 1440)
    print("  serving:", json.dumps(whose()))
    shoot("h7k-14-keyfacts-aligned-1440", "table.sf-keyfacts", pad=8, pad_top=76)
    at(SERVICES, 375)
    print("  serving:", json.dumps(whose()))
    shoot("h7k-15-keyfacts-375", "table.sf-keyfacts", pad=8, pad_top=60)

    print("\n%d/%d frames written to %s/" % (sum(1 for f in FRAMES if f[4]),
                                             len(FRAMES), OUT))
    flat = [f[0] for f in FRAMES if not f[4]]
    if flat:
        print("FLAT (failed captures, not findings):")
        for n in flat:
            print("  - " + n)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
