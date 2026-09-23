#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7j evidence frames.

Twelve frames, one per claim worth looking at, written to docs/batchH7j-shots/.

Two mechanics that are not obvious and are why this is a script rather than a
handful of CLI calls:

  * Every frame is a FULL-PAGE capture cropped afterwards by the target's
    absolute page rect x devicePixelRatio. Element-clipped screenshots come back
    pure white once the page is scrolled, so "clip to the element" silently
    produces a blank file that looks like a CSS bug.
  * Every crop is checked for being non-flat before it is written: at least 9
    distinct colours. A crop that is one colour is a failed capture, not a
    finding, and the check is what tells the two apart.

Run against the PREFLIGHT copy (2.10.71) — batch C pushes and does not pull.

    tools/b2d_h7j_shots.py
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
OUT = "docs/batchH7j-shots"
TMP = "_backup/_h7j_shots_tmp"

ABOUT = "/about/"
CHEWS = "/products/soft-chews/"


def ab(*a, timeout=180):
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


def at(path, w, h=900, settle=2.2):
    ab("open", BASE + path)
    time.sleep(settle)
    for _ in range(4):
        ab("set", "viewport", str(w), str(h))
        time.sleep(0.8)
        got = ev("JSON.stringify({w: innerWidth, dpr: devicePixelRatio, "
                 "p: location.pathname, t: document.title})")
        if isinstance(got, dict) and got.get("w") == w and got.get("p") == path:
            return got
        time.sleep(0.5)
    raise SystemExit("viewport %d did not take on %s" % (w, path))


def rect(sel):
    """Absolute page rect of the first match, plus the document's own size."""
    return ev("""(() => {
      const e = document.querySelector(%s);
      if (!e) return null;
      const r = e.getBoundingClientRect();
      return { x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height,
               dpr: devicePixelRatio,
               docW: document.documentElement.scrollWidth,
               docH: document.documentElement.scrollHeight }; })()""" % json.dumps(sel))


FRAMES = []


def shoot(name, sel, pad=0, mincolours=9):
    """One full-page capture, cropped to `sel` (+pad), checked, written."""
    r = rect(sel)
    if not r:
        print("FAIL %-40s no element %s" % (name, sel))
        return False
    dpr = r["dpr"] or 1
    full = os.path.join(TMP, name + "-full.png")
    ab("screenshot", "--full", full)
    if not os.path.exists(full):
        print("FAIL %-40s no capture" % name)
        return False
    im = Image.open(full)
    sx, sy = im.width / float(r["docW"]), im.height / float(r["docH"])
    box = (max(0, int((r["x"] - pad) * sx)),
           max(0, int((r["y"] - pad) * sy)),
           min(im.width, int((r["x"] + r["w"] + pad) * sx)),
           min(im.height, int((r["y"] + r["h"] + pad) * sy)))
    crop = im.crop(box).convert("RGB")
    cols = crop.getcolors(maxcolors=1 << 20) or []
    names = len(cols)
    ok = names >= mincolours
    out = os.path.join(OUT, name + ".png")
    crop.save(out)
    FRAMES.append((name, crop.width, crop.height, names, ok))
    print("%s %-42s %4dx%-5d colours=%-6d %s"
          % ("OK  " if ok else "FLAT", name, crop.width, crop.height, names,
             "dpr=%.0f" % dpr))
    return ok


def setclass(slug):
    ev("window.__sfBase = window.__sfBase || document.querySelector('header.sf-header').className;"
       "(()=>{const H=document.querySelector('header.sf-header');"
       "const c=window.__sfBase.split(/\\s+/).filter(t=>t&&!/^sf-header--nav-/.test(t));"
       "if(%s!=='none')c.push('sf-header--nav-'+%s);H.className=c.join(' ');})()"
       % (json.dumps(slug), json.dumps(slug)))


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    session()

    # ---- 待办10 — the gap, at the two widths it shows at ----------------
    at(ABOUT, 1440)
    shoot("h7j-01-desktop-bar-gap-20px", ".sf-header", pad=0)
    at(ABOUT, 768)
    shoot("h7j-02-tablet-bar-768", ".sf-header", pad=0)

    # ---- 待办20 — the six marks, same crop each time --------------------
    at(ABOUT, 1440)
    for i, slug in enumerate(["underline", "bg", "thick-line", "color",
                              "left-line", "pill"], start=3):
        setclass(slug)
        time.sleep(0.5)
        shoot("h7j-%02d-desktop-mark-%s" % (i, slug),
              ".sf-header .wp-block-navigation", pad=8)

    # The owner, not the leaf: this is the page whose nav item is marked
    # "true" rather than "page", and the crop has to show the item that owns
    # the dropdown so the claim can be checked by eye.
    at(CHEWS, 1440)
    shoot("h7j-09-desktop-owner-marked", ".sf-header", pad=0)

    # ---- 待办15 — the facts band, at the three widths that matter -------
    for i, w in ((10, 1440), (11, 375)):
        at(CHEWS, w)
        shoot("h7j-%d-facts-gutter-%d" % (i, w), ".sf-facts-mini", pad=0, mincolours=6)
    at(CHEWS, 1200)
    shoot("h7j-12-facts-gutter-1200", ".sf-facts-mini", pad=0, mincolours=6)

    # ---- the drawer, with the mark in it --------------------------------
    # Four of the six marks, not just the default. This is where two of the
    # three defects lived, and a single frame of the shipped default would have
    # "documented" a drawer in which the mark was invisible: before the fix the
    # current row was pixel-identical to an unmarked one. `left-line` is here
    # too — its defect was at every width, and the drawer is the narrowest place
    # to see that its 3px rule is now painted rather than transparent.
    at(CHEWS, 375)
    ev("window.__sfBase = document.querySelector('header.sf-header').className;")
    for i, slug in enumerate(["underline", "color", "left-line", "thick-line"], start=13):
        setclass(slug)
        time.sleep(0.4)
        ev("document.querySelector('.wp-block-navigation__responsive-container-open')"
           ".click();")
        time.sleep(1.0)
        st = ev("document.querySelector('.wp-block-navigation__responsive-container')"
                ".classList.contains('is-menu-open')")
        if not st:
            print("    !! drawer did not open for %s" % slug)
        shoot("h7j-%02d-phone-drawer-%s" % (i, slug),
              ".wp-block-navigation__responsive-container", pad=0)
        ev("document.querySelector('.wp-block-navigation__responsive-container-close')"
           ".click();")
        time.sleep(0.6)

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
