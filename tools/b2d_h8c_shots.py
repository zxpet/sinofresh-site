#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H8c evidence frames — docs/batchH8c-shots/.

Fifteen frames, in the pairs that make this batch legible:

    live 2.10.73       the four models are four cards of TEXT on /services/,
                       and the four routes they name do not exist — the theme
                       answers them with its generic page, which is why the
                       BEFORE frames of `/services/oem/` and `/services/odm/`
                       are the SAME page under two different titles.
    preflight 2.10.76  each model has a page of its own (four different h1s,
                       four different bands), the four cards are links, and the
                       whole card — not just its title — is the hit area.

The frame that carries the batch's real claim is `after-card1-focus`: it is
taken after TABBING to the card's link, so the theme's
`.sf-card__title-link:focus-visible::after{outline}` draws its ring around the
entire card. A screenshot cannot show a pseudo-element's hit area, and a
before/after pair of the resting state would show no difference at all (the
anchor inherits the card's colour) — so the ring is the only honest picture of
"the whole card is the link". It is also the picture of "one tab stop per card":
the ring arrives on the first Tab that reaches the card.

Three mechanics, each of which has bitten this project before:

  * full-page frames are cropped by the target's own ABSOLUTE page rect scaled
    by the capture's ratio to the document. Element-clipped screenshots come back
    pure white once the page has been scrolled — the tool crops by page
    coordinates and captures by viewport coordinates — so "clip to the element"
    silently writes a blank file that looks exactly like a CSS bug.
  * the BEFORE and AFTER halves are two sessions, because the theme is switched
    by the `X-SF-Preflight: 1` header: `close --all`, then a `set headers`
    carrying BOTH the switch and the Basic credential. `set credentials` and
    `set headers` each rebuild the context and the later one erases the former.
  * every crop is checked for being non-flat before it is reported (at least 9
    distinct colours). A one-colour crop is a failed capture, not a finding.

The three top-of-page frames are cut by PIXEL BAND, not by selector: the rail
(`nav.sf-toc`) is `position: fixed`, so its page rect is not where it is painted
and a selector crop of it would come back with the wrong region.

    ~/.workbuddy/binaries/python/envs/default/bin/python tools/b2d_h8c_shots.py
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

OUT = "docs/batchH8c-shots"
TMP = "_backup/_h8c_shots_tmp"

OVERVIEW = "/services/"
OEM = "/services/oem/"
ODM = "/services/odm/"
CON = "/services/contract-manufacturing/"
PRI = "/services/private-label/"

CARD = ".sf-card--roomy"
TERMS = "table.sf-keyfacts"
FAQ = "details.sf-faq__item"

# (name, live?, path, width, kind, arg)
#   kind 'sel'  -> arg is a CSS selector; cropped by its absolute page rect
#   kind 'band' -> arg is (y0, y1) in CSS px from the top of the document
#   kind 'focus-card' -> the card, after tabbing to its link
FRAMES = [
    # ---- live 2.10.73: text cards, and no pages behind them ----------------
    ("before-card1", True, OVERVIEW, 1440, "sel", CARD),
    ("before-oem-top", True, OEM, 1440, "band", (0, 1150)),
    ("before-odm-top", True, ODM, 1440, "band", (0, 1150)),
    # ---- preflight 2.10.76: the same card, now a link ---------------------
    ("after-card1", False, OVERVIEW, 1440, "sel", CARD),
    ("after-card1-focus", False, OVERVIEW, 1440, "focus-card", CARD),
    ("after-overview-terms", False, OVERVIEW, 1440, "sel", TERMS),
    # ---- and four pages of their own -------------------------------------
    ("after-oem-top", False, OEM, 1440, "band", (0, 1150)),
    ("after-oem-terms", False, OEM, 1440, "sel", TERMS),
    ("after-oem-faq", False, OEM, 1440, "sel", FAQ),
    ("after-odm-top", False, ODM, 1440, "band", (0, 1150)),
    ("after-contract-top", False, CON, 1440, "band", (0, 1150)),
    ("after-private-top", False, PRI, 1440, "band", (0, 1150)),
    # ---- the phone, where the cards stack and the hero has to hold --------
    ("after-oem-top-375", False, OEM, 375, "band", (0, 900)),
    ("after-private-terms-375", False, PRI, 375, "sel", TERMS),
    ("after-private-faq-375", False, PRI, 375, "sel", FAQ),
]

RESULTS = []
CURRENT = {"live": False}


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
    """Walk the page down and back so every section is revealed. A frame shot
    while content is still pending is blank, and "the CSS is broken" and "the
    capture is blank" must not look the same."""
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


def at(path, w, h=1000, settle=2.0):
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
            pending = prescroll()
            if pending:
                print("    !! %d sections still unrevealed on %s" % (pending, path))
            hid = ev("(() => { let n = 0;"
                     " document.querySelectorAll('.sf-cookie-banner')"
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


def tab_to_card(limit=70):
    """Tab until focus lands on the card's stretched link.

    Tab and not `focus <sel>`: Chrome only matches `:focus-visible` for a
    programmatic focus on some element kinds, and a link is not one of them, so
    a `focus` call would produce a frame with no ring at all. This also means
    the frame doubles as the tab-order reading: the number of Tabs needed is
    printed, and the ring arriving on the first Tab that reaches the card is the
    "one tab stop per card" claim in pixels.
    """
    ev("document.body.setAttribute('tabindex', '-1'); document.body.focus();")
    for i in range(limit):
        ab("press", "Tab")
        got = ev("JSON.stringify({c: String((document.activeElement||{}).className||''),"
                 " t: String((document.activeElement||{}).textContent||'')"
                 ".replace(/\\s+/g,' ').trim().slice(0,40),"
                 " fv: !!(document.activeElement && document.activeElement.matches"
                 " && document.activeElement.matches(':focus-visible'))})")
        if isinstance(got, dict) and "sf-card__title-link" in (got.get("c") or ""):
            return i + 1, got
    return None, None


def _save(name, crop):
    cols = crop.getcolors(maxcolors=1 << 20) or []
    n = len(cols)
    ok = n >= 9
    crop.save(os.path.join(OUT, name + ".png"))
    RESULTS.append((name, crop.width, crop.height, n, ok))
    print("%s %-32s %4dx%-4d colours=%-6d" % ("ok  " if ok else "FLAT", name,
                                              crop.width, crop.height, n))
    return ok


def fullshot(name):
    full = os.path.join(TMP, name + "-full.png")
    ab("screenshot", "--full", full)
    if not os.path.exists(full):
        print("FAIL %-32s the capture wrote nothing" % name)
        RESULTS.append((name, 0, 0, 0, False))
        return None
    return Image.open(full)


def shoot_sel(name, sel, pad=8, pad_top=8):
    r = rect(sel)
    if not r:
        print("FAIL %-32s no element %s" % (name, sel))
        RESULTS.append((name, 0, 0, 0, False))
        return False
    img = fullshot(name)
    if img is None:
        return False
    sx = img.width / float(r["docW"]) if r["docW"] else 1.0
    sy = img.height / float(r["docH"]) if r["docH"] else 1.0
    box = (max(0, int((r["x"] - pad) * sx)),
           max(0, int((r["y"] - pad_top) * sy)),
           min(img.width, int((r["x"] + r["w"] + pad) * sx)),
           min(img.height, int((r["y"] + r["h"] + pad) * sy)))
    return _save(name, img.crop(box))


def shoot_band(name, band):
    y0, y1 = band
    img = fullshot(name)
    if img is None:
        return False
    doc = ev("JSON.stringify({w: document.documentElement.scrollWidth,"
             " h: document.documentElement.scrollHeight})") or {}
    sy = img.height / float(doc.get("h") or 1)
    # Clamped to the image: a band that runs past the end of a SHORT page would
    # otherwise be padded with black by the crop, and a frame with a black band
    # across its bottom reads as a rendering fault. The live half of this batch
    # has exactly such a page — the generic fallback is shorter than the
    # preflight detail page it is being compared with.
    top = max(0, min(img.height, int(y0 * sy)))
    bot = max(top, min(img.height, int(y1 * sy)))
    if bot - top < 40:
        print("    !! %s: the band %s is past the end of a %dpx document"
              % (name, band, doc.get("h") or 0))
    return _save(name, img.crop((0, top, img.width, bot)))


def main():
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)
    last = None
    for name, live, path, w, kind, arg in FRAMES:
        if live != last:
            session(live)
            last = live
            CURRENT["live"] = live
            print("\n== session: %s ==" % ("live 2.10.73" if live else "preflight 2.10.76"))
            print("   serving %s" % whose())
        print("%s  %s  w=%d" % (name, path, w))
        at(path, w)
        got = whose()
        if (got or {}).get("pre") is not (not live):
            raise SystemExit("wrong route for %s: %s (wanted live=%s)"
                             % (name, got, live))
        if kind == "focus-card":
            n, st = tab_to_card()
            if n is None:
                print("FAIL %-32s Tab never reached the card's link" % name)
                RESULTS.append((name, 0, 0, 0, False))
                continue
            print("    focus reached the card link after %d Tab(s): %s"
                  % (n, (st or {}).get("t")))
            if not (st or {}).get("fv"):
                print("    !! focused, but the browser says :focus-visible is false"
                      " — the ring may not be drawn")
            shoot_sel(name, arg)
        elif kind == "sel":
            shoot_sel(name, arg)
        else:
            shoot_band(name, arg)
    ab("close", "--all")

    flat = [r for r in RESULTS if not r[4]]
    print("\n%s  batch H8c frames  (%d frames, %d flat)"
          % ("PASS" if not flat else "FAIL", len(RESULTS), len(flat)))
    for n, _, _, c, _ in flat:
        print("   FLAT %s  colours=%d" % (n, c))
    json.dump([{"name": n, "w": w, "h": h, "colours": c, "ok": o}
               for n, w, h, c, o in RESULTS],
              open("/tmp/h8c-frames.json", "w"), indent=1)
    return 0 if not flat else 1


if __name__ == "__main__":
    sys.exit(main())
