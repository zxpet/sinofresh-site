#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7l evidence frames — docs/batchH7l-shots/.

Twelve frames, and the first two of them are the BEFORE pair. That pair is not
decoration: this batch's two items are both "the thing is in the wrong place /
the wrong shape", and the fastest way to read whether they landed is to see the
same box twice, once from the artifact dev serves today and once from the one it
will serve after the pull.

    live 2.10.72     the ladder closes the column, under Shape and Container;
                     the cert band is a flat strip of twelve icon+text chips.
    preflight 2.10.73  the ladder heads the column, directly under the intro;
                     the band is six cards.

Two mechanics, both of which have bitten this project before and are the reason
this is a script rather than a dozen CLI calls:

  * every frame is a FULL-PAGE capture cropped afterwards by the target's own
    absolute page rect, scaled by the capture's ratio to the document size.
    Element-clipped screenshots come back pure white once the page has been
    scrolled — the tool crops by page coordinates and captures by viewport
    coordinates — so "clip to the element" silently writes a blank file that
    looks exactly like a CSS bug.
  * every crop is checked for being non-flat before it is reported (at least 9
    distinct colours). A one-colour crop is a failed capture, not a finding.

The theme is switched by the `X-SF-Preflight: 1` header, so the two runs are two
sessions: `close --all` then a `set headers` carrying BOTH the switch and the
Basic credential (`set credentials` and `set headers` each rebuild the context
and the later one erases the former).

    tools/b2d_h7l_shots.py
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
AUTH = "Basic " + base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()
PF = json.dumps({"X-SF-Preflight": "1", "Authorization": AUTH})
LIVE = json.dumps({"Authorization": AUTH})

OUT = "docs/batchH7l-shots"
TMP = "_backup/_h7l_shots_tmp"

DETAIL = "/formulas/joint-support-soft-chews/"
DETAIL_ZH = "/zh/formulas/joint-support-soft-chews/"
HOME = "/"
HOME_ZH = "/zh/"

# The box whose position is the whole of 待办25.
SIDE = "div.sf-fdetail2__side"
LADDER = '[data-sf-config-group="pricing"]'
CTA = "a.sf-fdetail2__cta"
BAND = ".sf-certstrip"
CARD = ".sf-certstrip__badge"


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


def session(live):
    ab("close", "--all")
    time.sleep(1.0)
    ab("open", BASE + "/")
    time.sleep(2.2)
    ab("set", "headers", LIVE if live else PF)
    time.sleep(0.6)
    ab("reload")
    time.sleep(2.5)


def prescroll(step=700, pause=0.45, settle=1.3):
    """Walk the page down and back so every section is revealed.

    Sections below the fold get `.sf-pending` and are painted `opacity: 0` until
    an IntersectionObserver clears them, so a full-page capture of a page that
    was never scrolled paints those sections as flat background. The reveal is
    one-way, so scrolling back up keeps it. The leftover count is RETURNED, not
    assumed: a frame shot while any section is pending is blank, and the
    difference between "the CSS is broken" and "the capture is blank" is the
    entire reason this is checked.
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
    """Which artifact answered — asserted before anything is shot.

    Printed, not asserted: the E2E is where the artifact is a hard gate. Here it
    is the caption for the frame, so a mis-routed capture is at least visible in
    the log next to the file it wrote.
    """
    return ev("""(() => {
      const l = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(x => x.href);
      const theme = l.find(h => h.includes('sinofresh-theme')) || '';
      return { path: location.pathname, theme,
               pre: theme.includes('-preflight') && !/themes\\/sinofresh-theme\\//.test(theme),
               v: (theme.match(/ver=([0-9.]+)/) || [])[1] || null }; })()""")


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
        print("FAIL %-46s no element %s" % (name, sel))
        return False
    pt = pad if pad_top is None else pad_top
    full = os.path.join(TMP, name + "-full.png")
    ab("screenshot", "--full", full)
    if not os.path.exists(full):
        print("FAIL %-46s no capture" % name)
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
    why = ""
    if not ok:
        pend = (ev("JSON.stringify({n: document.querySelectorAll('.sf-pending').length,"
                   " y: window.scrollY})") or {})
        why = "  <-- .sf-pending=%s scrollY=%s" % (pend.get("n"), pend.get("y"))
    print("%s %-48s %4dx%-5d colours=%-6d dpr=%.0f%s"
          % ("OK  " if ok else "FLAT", name, crop.width, crop.height, names,
             r["dpr"] or 1, why))
    return ok


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)

    # ---------------------------------------------------------- BEFORE pair
    # dev's own 2.10.72, no header: the address and the shape the user is
    # complaining about, as the box actually serves them today.
    session(live=True)
    at(DETAIL, 1440)
    print("  serving:", json.dumps(whose()))
    shoot("h7l-00-before-ladder-at-foot-live-1440", SIDE, pad=6)
    at(HOME, 1440)
    print("  serving:", json.dumps(whose()))
    shoot("h7l-00b-before-certstrip-flat-live-1440", BAND, pad=10,
          mincolours=6)

    # ----------------------------------------------------------- AFTER pair
    session(live=False)
    at(DETAIL, 1440)
    print("  serving:", json.dumps(whose()))
    shoot("h7l-01-ladder-heads-column-1440", SIDE, pad=6, pad_top=6)
    shoot("h7l-02-ladder-closeup-1440", LADDER, pad=4)
    shoot("h7l-03-cta-send-inquiry-1440", CTA, pad=10)
    at(DETAIL, 375)
    print("  serving:", json.dumps(whose()))
    shoot("h7l-04-ladder-heads-column-375", SIDE, pad=6, pad_top=6)

    for i, w in ((5, 1440), (6, 768), (7, 375)):
        at(HOME, w)
        print("  serving:", json.dumps(whose()))
        shoot("h7l-%02d-cert-cards-%d" % (i, w), BAND, pad=10, mincolours=6)
    at(HOME, 1440)
    print("  serving:", json.dumps(whose()))
    shoot("h7l-08-one-card-closeup-1440", CARD, pad=4)

    at(HOME_ZH, 1440)
    print("  serving:", json.dumps(whose()))
    shoot("h7l-09-zh-cert-cards-1440", BAND, pad=10, mincolours=6)
    at(DETAIL_ZH, 1440)
    print("  serving:", json.dumps(whose()))
    shoot("h7l-10-zh-ladder-heads-column", SIDE, pad=6, pad_top=6)

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
