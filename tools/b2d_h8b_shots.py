#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H8b evidence frames — docs/batchH8b-shots/.

Fourteen frames: seven of them the AFTER half and seven the BEFORE. The pair is
the whole point of this batch, because its claim is not "the group changed" but
"the group now belongs to the page" — and that is only legible by seeing TWO
DIFFERENT dosage forms side by side, twice each.

    live 2.10.73       every detail page draws the same eight soft-chew shapes,
                       under the word "Shape": a powder offers Bone and Paw, a
                       drops page offers Star. Container Type exists on one page
                       in twenty-one.
    preflight 2.10.75  a powder's picker says "Appearance" and offers Fine
                       Powder / Granules / Microencapsulated; a drops page says
                       "Appearance" and offers Clear / Light Yellow / Amber; a
                       pastes page says "Texture"; fish oil says "Form". Four
                       different sentences in the same slot. Container Type is
                       on every detail page and its options are the dosage
                       form's packaging pool.

Three mechanics, each of which has bitten this project before and is the reason
this is a script rather than a dozen CLI calls:

  * full-page frames are cropped by the target's own ABSOLUTE page rect scaled
    by the capture's ratio to the document. Element-clipped screenshots come
    back pure white once the page has been scrolled — the tool crops by page
    coordinates and captures by viewport coordinates — so "clip to the element"
    silently writes a blank file that looks exactly like a CSS bug.
  * the BEFORE and AFTER halves are two sessions, because the theme is switched
    by the `X-SF-Preflight: 1` header: `close --all`, then a `set headers`
    carrying BOTH the switch and the Basic credential. `set credentials` and
    `set headers` each rebuild the context and the later one erases the former.
  * every crop is checked for being non-flat before it is reported (at least 9
    distinct colours). A one-colour crop is a failed capture, not a finding.

    ~/.workbuddy/binaries/python/envs/default/bin/python tools/b2d_h8b_shots.py
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

OUT = "docs/batchH8b-shots"
TMP = "_backup/_h8b_shots_tmp"

SHAPE = '[data-sf-config-group="shape"]'
CONT = '[data-sf-config-group="container"]'
CONFIG = ".sf-fdetail-config"

POWDER = "/formulas/pumpkin-digestive-powder/"
DROPS = "/formulas/urinary-care-drops/"
PASTES = "/formulas/nutrition-paste/"
FISH = "/formulas/wild-alaskan-salmon-oil/"
CHEWS = "/formulas/skin-coat-soft-chews/"
RECORD = "/formulas/joint-support-soft-chews/"

# (name, live?, path, width, selector, pad_top, pad)
#
# Grouped by session rather than by pair: the theme is switched by a request
# header, so each change of side costs a whole new browser context. The names
# carry the pair, and the record reads them side by side.
FRAMES = [
    # ---- live 2.10.73: one vocabulary, on every page -----------------------
    ("before-powder-shape", True, POWDER, 1440, SHAPE, 8, 8),
    ("before-drops-shape", True, DROPS, 1440, SHAPE, 8, 8),
    ("before-pastes-shape", True, PASTES, 1440, SHAPE, 8, 8),
    ("before-fishoil-shape", True, FISH, 1440, SHAPE, 8, 8),
    ("before-powder-group", True, POWDER, 1440, CONFIG, 8, 8),
    ("before-record-container", True, RECORD, 1440, CONT, 8, 8),
    ("before-chews-group", True, CHEWS, 1440, CONFIG, 8, 8),
    # ---- preflight 2.10.75: four vocabularies, and a group on every page ---
    ("after-powder-shape", False, POWDER, 1440, SHAPE, 8, 8),
    ("after-drops-shape", False, DROPS, 1440, SHAPE, 8, 8),
    ("after-pastes-shape", False, PASTES, 1440, SHAPE, 8, 8),
    ("after-fishoil-shape", False, FISH, 1440, SHAPE, 8, 8),
    ("after-powder-group", False, POWDER, 1440, CONFIG, 8, 8),
    ("after-record-container", False, RECORD, 1440, CONT, 8, 8),
    ("after-chews-group", False, CHEWS, 1440, CONFIG, 8, 8),
    # ---- and the phone, where the fold cuts at the fifth group ------------
    ("after-chews-config-375", False, CHEWS, 375, CONFIG, 8, 8),
]

RESULTS = []


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


def wait_ready(tries=25):
    """A page that has navigated is not a page that has loaded — and a frame
    captured too early is a blank file that looks exactly like a CSS bug."""
    for _ in range(tries):
        st = ev("JSON.stringify({rs: document.readyState, t: document.title,"
                " n: document.querySelectorAll('link[rel=stylesheet]').length})")
        if (isinstance(st, dict) and st.get("rs") == "complete"
                and st.get("n", 0) > 0 and st.get("t")):
            return True
        time.sleep(0.8)
    return False


def prescroll(step=700, pause=0.35, settle=1.2):
    """Walk the page down and back so every section is revealed, and RETURN the
    number of sections still pending: a frame shot while a section is pending is
    blank, and "the CSS is broken" and "the capture is blank" must not look the
    same."""
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


def at(path, w, h=1000, settle=2.0, clear_fold=False):
    ab("open", BASE + path)
    time.sleep(settle)
    ab("set", "headers", PF if CURRENT["live"] is False else LIVE)
    time.sleep(0.4)
    ab("reload")
    wait_ready()
    for _ in range(4):
        ab("set", "viewport", str(w), str(h))
        time.sleep(0.8)
        got = ev("JSON.stringify({w: innerWidth, p: location.pathname})")
        if isinstance(got, dict) and got.get("w") == w:
            if clear_fold and w <= 480:
                ev("(() => { try { sessionStorage.removeItem('sf-config-fold'); } "
                   "catch (e) {} return 1; })()")
                ab("reload")
                wait_ready()
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


CURRENT = {"live": False}


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


def _save(name, crop):
    cols = crop.getcolors(maxcolors=1 << 20) or []
    n = len(cols)
    ok = n >= 9
    crop.save(os.path.join(OUT, name + ".png"))
    RESULTS.append((name, crop.width, crop.height, n, ok))
    print("%s %-32s %4dx%-4d colours=%-6d" % ("ok  " if ok else "FLAT", name,
                                              crop.width, crop.height, n))
    return ok


def shoot(name, sel, pad=8, pad_top=8):
    """Full-page capture, cropped by the target's absolute page rect."""
    r = rect(sel)
    if not r:
        print("FAIL %-32s no element %s" % (name, sel))
        RESULTS.append((name, 0, 0, 0, False))
        return False
    full = os.path.join(TMP, name + "-full.png")
    ab("screenshot", "--full", full)
    if not os.path.exists(full):
        print("FAIL %-32s the capture wrote nothing" % name)
        RESULTS.append((name, 0, 0, 0, False))
        return False
    img = Image.open(full)
    sx = img.width / float(r["docW"]) if r["docW"] else 1.0
    sy = img.height / float(r["docH"]) if r["docH"] else 1.0
    box = (max(0, int((r["x"] - pad) * sx)),
           max(0, int((r["y"] - pad_top) * sy)),
           min(img.width, int((r["x"] + r["w"] + pad) * sx)),
           min(img.height, int((r["y"] + r["h"] + pad) * sy)))
    crop = img.crop(box)
    return _save(name, crop)


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    last = None
    for name, live, path, w, sel, ptop, pad in FRAMES:
        if live != last:
            session(live)
            last = live
            CURRENT["live"] = live
            w0 = whose()
            print("\n== session: %s ==" % ("live 2.10.73" if live else "preflight 2.10.75"))
            print("   serving %s" % w0)
        print("%s  %s  w=%d" % (name, path, w))
        at(path, w, clear_fold=(w <= 480))
        got = whose()
        if (got or {}).get("pre") is not (not live):
            raise SystemExit("wrong route for %s: %s (wanted live=%s)" % (name, got, live))
        shoot(name, sel, pad=pad, pad_top=ptop)
    ab("close", "--all")

    flat = [r for r in RESULTS if not r[4]]
    print("\n%s  batch H8b frames  (%d frames, %d flat)"
          % ("PASS" if not flat else "FAIL", len(RESULTS), len(flat)))
    for n, _, _, c, _ in flat:
        print("   FLAT %s  colours=%d" % (n, c))
    json.dump([{"name": n, "w": w, "h": h, "colours": c, "ok": o}
               for n, w, h, c, o in RESULTS],
              open("/tmp/h8b-frames.json", "w"), indent=1)
    return 0 if not flat else 1


if __name__ == "__main__":
    sys.exit(main())
