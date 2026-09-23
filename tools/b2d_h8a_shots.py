#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H8a evidence frames — docs/batchH8a-shots/.

Fourteen frames, and seven of them are the BEFORE half. That half is not
decoration: every item of this batch is "the control says the wrong thing" or
"the row is the wrong shape", and the fastest way to read whether it landed is
to see the same box twice — once from the artifact dev serves today (2.10.73)
and once from the one it will serve after the pull (2.10.74).

    live 2.10.73       the parameter list still files a Packaging row and prints
                       "18 months shelf life"; Flavor and Pack Size are
                       multi-selects; Shape wraps three to a line; the gallery
                       scrolls away; the phone fold keeps three groups.
    preflight 2.10.74  the row is gone and the value reads "24 months"; every
                       group is one pick ending in Custom; Shape is one sliding
                       row with arrows; the gallery sticks at 100px; the phone
                       fold keeps four.

Three mechanics, each of which has bitten this project before and is the reason
this is a script rather than a dozen CLI calls:

  * full-page frames are cropped by the target's own ABSOLUTE page rect scaled
    by the capture's ratio to the document. Element-clipped screenshots come back
    pure white once the page has been scrolled — the tool crops by page
    coordinates and captures by viewport coordinates — so "clip to the element"
    silently writes a blank file that looks exactly like a CSS bug.
  * the sticky pair CANNOT be shot that way: a full-page capture paints a
    `position: sticky` element at its unstuck position, so the pair is taken as
    VIEWPORT frames at the same scroll offset, which is what the visitor sees.
  * every crop is checked for being non-flat before it is reported (at least 9
    distinct colours). A one-colour crop is a failed capture, not a finding.

The theme is switched by the `X-SF-Preflight: 1` header, so the two runs are two
sessions: `close --all` then a `set headers` carrying BOTH the switch and the
Basic credential (`set credentials` and `set headers` each rebuild the context
and the later one erases the former).

    tools/b2d_h8a_shots.py
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

OUT = "docs/batchH8a-shots"
TMP = "_backup/_h8a_shots_tmp"

DETAIL = "/formulas/joint-support-soft-chews/"
FORM = "/products/soft-chews/"

SIDE = "div.sf-fdetail2__side"
CONFIG = ".sf-fdetail-config"
SHAPE = '[data-sf-config-group="shape"]'
PARAMS = ".sf-fdetail2__params"
MEDIA = ".sf-fdetail2__media"
FOLD = ".sf-fdetail-config__fold"
CELL = ".sf-facts-mini"

FRAMES = []


def ab(*a, timeout=300):
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
    """Walk the page down and back so every section is revealed, and RETURN the
    number of sections still pending: a frame shot while any section is pending
    is blank, and "the CSS is broken" and "the capture is blank" must not look
    the same."""
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


def at(path, w, h=900, settle=2.2, clear_fold=False):
    ab("open", BASE + path)
    time.sleep(settle)
    for _ in range(4):
        ab("set", "viewport", str(w), str(h))
        time.sleep(0.8)
        got = ev("JSON.stringify({w: innerWidth, p: location.pathname})")
        if isinstance(got, dict) and got.get("w") == w and got.get("p") == path:
            if clear_fold:
                ev("(() => { try { sessionStorage.removeItem('sf-config-fold'); } "
                   "catch (e) {} return 1; })()")
                ab("reload")
                time.sleep(2.2)
                ab("set", "viewport", str(w), str(h))
                time.sleep(0.8)
            pending = prescroll()
            if pending:
                print("    !! %d sections still unrevealed on %s" % (pending, path))
            hid = ev("(() => { let n = 0; document.querySelectorAll('.sf-cookie-banner')"
                     ".forEach(e => { e.style.display = 'none'; n++; }); return n; })()")
            if hid:
                print("    (hid %s cookie banner(s) for the capture)" % hid)
            return got
        time.sleep(0.5)
    raise SystemExit("viewport %d did not take on %s" % (w, path))


def whose():
    return ev("""(() => {
      const l = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(x => x.href);
      const theme = l.find(h => h.includes('sinofresh-theme')) || '';
      return { pre: theme.includes('-preflight'),
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


def rect_v(sel):
    return ev("""(() => {
      const e = document.querySelector(%s);
      if (!e) return null;
      const r = e.getBoundingClientRect();
      return { x: r.left, y: r.top, w: r.width, h: r.height, dpr: devicePixelRatio,
               vw: innerWidth, vh: innerHeight }; })()""" % json.dumps(sel))


def _save(name, crop):
    cols = crop.getcolors(maxcolors=1 << 20) or []
    n = len(cols)
    ok = n >= 9
    crop.save(os.path.join(OUT, name + ".png"))
    FRAMES.append((name, crop.width, crop.height, n, ok))
    print("%s %-34s %4dx%-4d colours=%-6d" % ("ok  " if ok else "FLAT", name,
                                              crop.width, crop.height, n))
    return ok


def shoot(name, sel, pad=0, pad_top=None):
    """Full-page capture, cropped by the target's absolute page rect."""
    r = rect(sel)
    if not r:
        print("FAIL %-34s no element %s" % (name, sel))
        FRAMES.append((name, 0, 0, 0, False))
        return False
    pt = pad if pad_top is None else pad_top
    full = os.path.join(TMP, name + "-full.png")
    ab("screenshot", "--full", full)
    if not os.path.exists(full):
        print("FAIL %-34s no capture" % name)
        FRAMES.append((name, 0, 0, 0, False))
        return False
    im = Image.open(full)
    sx, sy = im.width / float(r["docW"]), im.height / float(r["docH"])
    box = (max(0, int((r["x"] - pad) * sx)), max(0, int((r["y"] - pt) * sy)),
           min(im.width, int((r["x"] + r["w"] + pad) * sx)),
           min(im.height, int((r["y"] + r["h"] + pad) * sy)))
    return _save(name, im.crop(box).convert("RGB"))


def shoot_view(name, sel, pad=16, scroll_to=None):
    """Viewport capture — the only way to shoot a stuck element the way the
    visitor sees it, because a full-page capture unsticks it."""
    if scroll_to is not None:
        ab("eval", "window.scrollTo(0, %d)" % scroll_to)
        time.sleep(1.2)
    r = rect_v(sel)
    if not r:
        print("FAIL %-34s no element %s" % (name, sel))
        FRAMES.append((name, 0, 0, 0, False))
        return False
    p = os.path.join(TMP, name + ".png")
    ab("screenshot", p)
    if not os.path.exists(p):
        print("FAIL %-34s no capture" % name)
        FRAMES.append((name, 0, 0, 0, False))
        return False
    im = Image.open(p)
    d = r["dpr"]
    box = (max(0, int((r["x"] - pad) * d)), max(0, int((r["y"] - pad) * d)),
           min(im.width, int((r["x"] + r["w"] + pad) * d)),
           min(im.height, int((r["y"] + r["h"] + pad) * d)))
    print("       (viewport frame; media top = %.1f px)" % r["y"])
    return _save(name, im.crop(box).convert("RGB"))


def unfold():
    ab("scrollintoview", FOLD)
    time.sleep(0.6)
    ab("click", FOLD)
    time.sleep(1.0)


def mid_sticky():
    """The scroll offset half-way into the range where the gallery CAN stick:
    derived, not guessed, so a frame that shows it unstuck is a finding rather
    than a badly chosen offset."""
    s = ev("""(() => {
      const m = document.querySelector('.sf-fdetail2__media');
      const inner = document.querySelector('.sf-fdetail2__inner');
      const pageTop = m.getBoundingClientRect().top + scrollY;
      const innerBottom = inner.getBoundingClientRect().bottom + scrollY;
      const lo = pageTop - 60, hi = innerBottom - m.getBoundingClientRect().height - 140;
      const max = document.documentElement.scrollHeight - innerHeight;
      return {y: Math.round(Math.min(Math.max((lo + hi) / 2, 60), max - 10))}; })()""")
    return int((s or {}).get("y") or 400)


def run():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)

    for live, tag in ((True, "before"), (False, "after")):
        print("\n===== %s  (%s) =====" % (tag, "live 2.10.73" if live else "preflight 2.10.74"))
        session(live)

        # ---- the right column, whole: the Packaging row, the controls, the value
        at(DETAIL, 1440)
        print("   served:", whose())
        shoot("%02d-%s-column-1440" % (1 if live else 2, tag), SIDE, pad=8)

        # ---- the parameter list alone: 待办26 and 待办29 in one box
        shoot("%02d-%s-params-1440" % (13 if live else 12, tag), PARAMS, pad=6)

        # ---- the shape row: wrapped three-to-a-line vs one sliding line
        ab("scrollintoview", SHAPE)
        time.sleep(0.8)
        shoot("%02d-%s-shape-1440" % (3 if live else 4, tag), SHAPE, pad=26)

        # ---- the sticky gallery, as a VIEWPORT frame at the same offset
        ab("scrollintoview", ".sf-fdetail2__inner")
        time.sleep(0.8)
        y = mid_sticky()
        shoot_view("%02d-%s-sticky-1440" % (10 if live else 11, tag), MEDIA, pad=10,
                   scroll_to=y)

        # ---- the phone: the fold, and the row inside it
        at(DETAIL, 375, 812, clear_fold=True)
        print("   served:", whose())
        ab("scrollintoview", CONFIG)
        time.sleep(0.8)
        shoot("%02d-%s-fold-375" % (5 if live else 6, tag), CONFIG, pad=6)

        unfold()
        ab("scrollintoview", SHAPE)
        time.sleep(0.8)
        shoot("%02d-%s-shape-375" % (7 if live else 8, tag), SHAPE, pad=6)

        # ---- the Custom answer, typed in: 待办27's payload, after only
        if not live:
            at(DETAIL, 1440)
            ab("scrollintoview", '[data-sf-config-group="weight"]')
            time.sleep(0.6)
            ab("click", '[data-sf-config-group="weight"] '
                        '.sf-fdetail-config__opt[data-sf-config-custom] '
                        '.sf-fdetail-config__input')
            time.sleep(0.6)
            ab("fill", '[data-sf-config-custom-input="weight"]', "5 g chew")
            time.sleep(0.4)
            ab("press", "Tab")
            time.sleep(0.8)
            ab("scrollintoview", '[data-sf-config-group="weight"]')
            time.sleep(0.6)
            shoot("09-after-custom-typed-1440", '[data-sf-config-group="weight"]', pad=8)

        # ---- where the retired row's value still lives
        if not live:
            at(FORM, 1440)
            print("   served:", whose())
            ab("scrollintoview", CELL)
            time.sleep(0.8)
            shoot("14-after-formcell-1440", CELL, pad=6)

    print("\n===== frames =====")
    bad = [f for f in FRAMES if not f[4]]
    for name, w, h, n, ok in FRAMES:
        print("  %-4s %-34s %4dx%-4d colours=%d" % ("ok" if ok else "FLAT", name, w, h, n))
    print("\n%s  %d frames written to %s  (%d flat)"
          % ("PASS" if not bad else "FAIL", len(FRAMES), OUT, len(bad)))
    json.dump([{"name": n, "w": w, "h": h, "colours": c, "ok": o}
               for n, w, h, c, o in FRAMES],
              open("/tmp/h8a-shots.json", "w"), indent=1)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(run())
