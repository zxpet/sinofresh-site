#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Batch H7l post-deploy acceptance — run against dev AFTER the pull.

Same claims as `tools/b2d_h7l_e2e.py`, driven at the live route (no
`X-SF-Preflight` header) instead of the preflight copy, plus a breadth pass over
all 75 paths. With `--frames` it also writes `docs/batchH7l-live-shots/`.

The one thing that makes this a different script from the E2E
-------------------------------------------------------------
**The `served()` gate is inverted.** The E2E proves "the preflight copy answered"
(`.../sinofresh-theme-preflight/style.css?ver=2.10.73`, and NOT the live dir).
Here the gate must prove the opposite: the theme directory that answers is
`themes/sinofresh-theme/`, its `ver=` is `2.10.73`, and it is NOT the preflight
copy. Before the pull that same URL answers `themes/sinofresh-theme/style.css?ver=2.10.72`
with the ladder at the foot — so this gate is the single assertion separating
"the pull took effect" from "the box is still reading the old bytes". Every other
check hangs off it, and its failure ABORTS rather than being recorded: a report
about the wrong artifact is worse than no report.

The pre-launch twin of this run is `_backup/b2d-h7l-e2e-live.log` (2.10.72,
46/60, the 14 reds being exactly the two items this batch implements).

    tools/b2d_h7l_live_accept.py [--frames]

Needs the interpreter that has Pillow only when `--frames` is passed.
"""
import base64
import json
import os
import re
import subprocess
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import b2d_h7l_e2e as E                                    # noqa: E402  (probes)

USER, PASS = "sfdev", "VkEws18Kl5V1qp3TpZ6s"
BASE = "https://dev.zxpet.com"
AUTH = "Basic " + base64.b64encode(("%s:%s" % (USER, PASS)).encode()).decode()
LIVE = json.dumps({"Authorization": AUTH})

VER = "2.10.73"
DETAIL = "/formulas/joint-support-soft-chews/"
DETAIL_ZH = "/zh/formulas/joint-support-soft-chews/"
HOME = "/"
HOME_ZH = "/zh/"
MANIFEST = "_backup/b2d-h7l-candidates/MANIFEST.tsv"
OUT = "docs/batchH7l-live-shots"
TMP = "_backup/_h7l_live_tmp"

RANGES = E.RANGES
PRICES = E.PRICES
CHIP_NAMES = E.CHIP_NAMES
CARD_BG = E.CARD_BG
CARD_LINE = E.CARD_LINE
CARD_RADIUS = E.CARD_RADIUS
CARD_PAD = E.CARD_PAD
CARD_GAP = E.CARD_GAP

RESULTS = []
FRAMES = []
FRAMES_ON = False


def ab(*a, timeout=240):
    return E.ab(*a, timeout=timeout)


def ev(js):
    return E.ev(js)


def check(name, ok, detail=""):
    RESULTS.append((name, bool(ok), str(detail)))
    print(("PASS " if ok else "FAIL ") + name
          + ("  | " + str(detail)[:300] if detail else ""))


def session():
    ab("close", "--all")
    time.sleep(1.0)
    ab("open", BASE + "/")
    time.sleep(2.2)
    ab("set", "headers", LIVE)
    time.sleep(0.6)
    ab("reload")
    time.sleep(2.5)


def served(path, why):
    """THE gate. Aborts the run; it is not merely a recorded check."""
    s = ev("""(() => {
      const l = Array.from(document.querySelectorAll('link[rel=stylesheet]')).map(x => x.href);
      const theme = l.find(h => h.includes('sinofresh-theme')) || '';
      return { path: location.pathname, title: document.title, theme,
               pre: theme.includes('-preflight') && !/themes\\/sinofresh-theme\\//.test(theme),
               ver: (theme.match(/ver=([0-9.]+)/) || [])[1] || null,
               h1: document.querySelectorAll('h1').length }; })()""")
    ok = (isinstance(s, dict)
          and re.search(r"themes/sinofresh-theme/style\.css\?ver=", s.get("theme") or "")
          and s.get("ver") == VER and s.get("pre") is False
          and s.get("h1") == 1)
    print("     gate: %s %s" % ("OK " if ok else "BAD", json.dumps(s)))
    if not ok:
        raise SystemExit(
            "\nABORT: the live theme did not answer %s on %s (%s) -- everything "
            "below would be a claim about the wrong bytes.\n%s"
            % (VER, path, why, json.dumps(s)))
    check("live %s served from themes/sinofresh-theme/  [%s]" % (VER, path), True,
          {"ver": s.get("ver"), "pre": s.get("pre")})


def open_at(path, w, h=900):
    E.open_at(path, w, h)


# ------------------------------------------------------------------- frames
def prescroll():
    """Reveal everything below the fold (`.sf-pending` / opacity 0) and hide the
    fixed cookie banner, which otherwise lands across whatever is being shown."""
    if not FRAMES_ON:
        return
    total = (ev("JSON.stringify({h: document.documentElement.scrollHeight})")
             or {}).get("h") or 0
    y = 0
    while y < total:
        ab("eval", "window.scrollTo(0, %d)" % y)
        time.sleep(0.4)
        y += 700
    left = (ev("JSON.stringify({n: document.querySelectorAll('.sf-pending').length})")
            or {}).get("n") or 0
    ev("(() => { document.querySelectorAll('.sf-cookie-banner').forEach(e =>"
       "e.style.display = 'none'); return 'hidden'; })()")
    ab("eval", "window.scrollTo(0, 0)")
    time.sleep(1.2)
    if left:
        print("     !! %d sections still unrevealed" % left)


def shoot(name, sel, pad=8, mincolours=6):
    from PIL import Image
    r = ev("""(() => {
      const e = document.querySelector(%s);
      if (!e) return null;
      const b = e.getBoundingClientRect();
      return { x: b.left + scrollX, y: b.top + scrollY, w: b.width, h: b.height,
               docW: document.documentElement.scrollWidth,
               docH: document.documentElement.scrollHeight }; })()""" % json.dumps(sel))
    if not r:
        print("     FAIL %-44s no element %s" % (name, sel))
        return
    full = os.path.join(TMP, name + "-full.png")
    ab("screenshot", "--full", full)
    im = Image.open(full)
    sx, sy = im.width / float(r["docW"]), im.height / float(r["docH"])
    crop = im.crop((max(0, int((r["x"] - pad) * sx)), max(0, int((r["y"] - pad) * sy)),
                    min(im.width, int((r["x"] + r["w"] + pad) * sx)),
                    min(im.height, int((r["y"] + r["h"] + pad) * sy)))).convert("RGB")
    names = len(crop.getcolors(maxcolors=1 << 20) or [])
    ok = names >= mincolours
    crop.save(os.path.join(OUT, name + ".png"))
    FRAMES.append((name, crop.width, crop.height, names, ok))
    print("     %s %-42s %4dx%-5d colours=%d"
          % ("OK  " if ok else "FLAT", name, crop.width, crop.height, names))


# -------------------------------------------------------------- claim sets
def strip_checks(tag, s, icon="40px", pad=CARD_PAD, gap=CARD_GAP):
    """The 待办4 claim set, checked against the live artifact.

    `icon`/`pad`/`gap` are parameters and not constants because the brief
    declares a phone step: the desktop tokens (40px icon, 16px padding, 16px
    gutter) are NOT the 375 values. The first version of this function hardcoded
    them and went red on the three phone checks against a correct product — the
    E2E had it right by calling its claim set only for 1440 and 768, and copying
    that set into this script lost the per-width scoping. Naming the expected
    values per width is also the stronger form: it demands the step be the
    specific one, not merely "not the desktop value".
    """
    check("待办4 six cards, not twelve chips  [%s]" % tag,
          s.get("count") == 6 and s.get("iconCount") == 6, s.get("count"))
    check("待办4 the names survive verbatim  [%s]" % tag,
          s.get("names") == CHIP_NAMES, s.get("names"))
    check("待办4 the card surface is Mist, hairline, 8px, %s  [%s]" % (pad, tag),
          s.get("cardBg") == CARD_BG and s.get("cardBorderW") == "1px"
          and s.get("cardBorderC") == CARD_LINE and s.get("cardRadius") == CARD_RADIUS
          and s.get("cardPad") == pad,
          {k: s.get(k) for k in ("cardBg", "cardBorderW", "cardBorderC",
                                 "cardRadius", "cardPad")})
    check("待办4 the icon is %s and left of the text  [%s]" % (icon, tag),
          s.get("iconW") == icon and s.get("iconH") == icon
          and s.get("iconLeftOfName") is True
          and abs(s["iconBox"]["h"] - float(icon[:-2])) < 0.6,
          {k: s.get(k) for k in ("iconW", "iconH", "iconLeftOfName")})
    check("待办4 the text runs to at most two lines  [%s]" % tag,
          s.get("nameIsTwoLines") is True, {"lines": s.get("nameLines")})
    check("待办4 the chips sit on a %s gutter  [%s]" % (gap, tag),
          s.get("rowGap") == gap, s.get("rowGap"))
    check("待办4 the lede and the link are still there  [%s]" % tag,
          bool(s.get("lede")) and "Certified to the standards" in (s["lede"]["text"] or "")
          and bool(s.get("more")) and "View all certifications" in (s["more"]["text"] or ""),
          {"lede": (s.get("lede") or {}).get("text"),
           "more": (s.get("more") or {}).get("text")})
    check("待办4 the band stays in its 32px section  [%s]" % tag,
          s.get("sectionPad") == "32px", s.get("sectionPad"))


def curl(path):
    """One path, live route, no preflight header. The caller owns the pacing."""
    return subprocess.run(
        ["curl", "-s", "-u", "%s:%s" % (USER, PASS), BASE + path],
        capture_output=True, text=True, timeout=60).stdout


def main():
    global FRAMES_ON
    FRAMES_ON = "--frames" in sys.argv
    os.makedirs(OUT, exist_ok=True)
    os.makedirs(TMP, exist_ok=True)

    session()

    # ------------------------------------------------- 待办25 / 待办1 / 待办2
    open_at(DETAIL, 1440)
    served(DETAIL, "items 25/1/2")
    prescroll()
    if FRAMES_ON:
        shoot("h7l-live-01-ladder-heads-column-1440", "div.sf-fdetail2__side", pad=6)
        shoot("h7l-live-02-ladder-closeup-1440",
              '[data-sf-config-group="pricing"]', pad=4)
    d = ev(E.DETAIL_PROBE)

    check("待办1 the ladder holds exactly three breaks",
          d.get("tierCount") == 3, d.get("tierCount"))
    check("待办1 the three ranges read as the brief writes them",
          d.get("ranges") == RANGES, d.get("ranges"))
    check("待办1 the three prices ride with them",
          d.get("prices") == PRICES, d.get("prices"))
    check("待办1 no row falls back to the placeholder",
          d.get("customQty") is False, d.get("customQty"))
    check("待办1 the echo line spells all three out",
          all(r in (d.get("metaLine") or "") for r in RANGES), d.get("metaLine"))

    check("待办25 the ladder follows the intro in document order",
          0 <= d.get("domIntro") < d.get("domPricing"),
          {"intro": d.get("domIntro"), "pricing": d.get("domPricing")})
    check("待办25 ...and precedes Flavor",
          d.get("domPricing") < d.get("domFlavor"),
          {"pricing": d.get("domPricing"), "flavor": d.get("domFlavor")})
    check("待办25 ...and it is above it on screen, under the intro",
          d.get("topIntro") < d.get("topPricing") < d.get("topFlavor"),
          {"intro": d.get("topIntro"), "pricing": d.get("topPricing"),
           "flavor": d.get("topFlavor")})
    check("待办25 the ladder keeps its three-column card row",
          d.get("cols") == 3, {"cols": d.get("cols"), "css": d.get("rowCols")})
    check("待办25 the column's 32px bold title survives the move",
          d.get("titleSize") == "32px" and d.get("titleWeight") in ("700", "bold"),
          {"size": d.get("titleSize"), "text": d.get("titleText")})
    check("待办25 ...and the ladder's own price keeps the voice H7i gave it",
          d.get("priceSize") == "17px" and d.get("priceWeight") in ("700", "bold"),
          {"size": d.get("priceSize"), "weight": d.get("priceWeight")})

    check("待办2 the column's foot is a Send Inquiry link",
          d.get("ctaTag") == "a" and d.get("ctaText") == "Send Inquiry"
          and d.get("ctaOpen") is True,
          {"tag": d.get("ctaTag"), "text": d.get("ctaText"), "open": d.get("ctaOpen")})
    check("待办2 ...whose no-script destination is the quote anchor",
          (d.get("ctaHref") or "").endswith("/contact/#quote"), d.get("ctaHref"))
    check("待办2 ...and no Request Sample text is served anywhere",
          d.get("requestSample") is False, d.get("requestSample"))

    ev("document.querySelector('a.sf-fdetail2__cta').click(); 'clicked'")
    now = ev(E.MODAL_NOW)
    time.sleep(0.8)
    then = ev(E.MODAL_NOW)
    check("待办2 the click opens the inquiry dialog",
          then.get("exists") is True and then.get("hidden") is False
          and then.get("isOpen") is True, {"same_tick": now, "after": then})
    check("待办2 ...and the dialog reprints the three breaks",
          all(r in (then.get("qty") or "") for r in RANGES), then.get("qty"))
    ev("(() => { const b = document.querySelector('.sf-inquiry-modal__close');"
       "if (b) b.click(); return 'closed'; })()")
    time.sleep(0.4)

    # ----------------------------------------------------- the phone, folded
    open_at(DETAIL, 375)
    ev("(() => { try { sessionStorage.removeItem('sf-config-fold'); } catch (e) {}"
       "return 'cleared'; })()")
    ab("reload")
    time.sleep(2.5)
    served(DETAIL, "the fold at 375")
    prescroll()
    if FRAMES_ON:
        shoot("h7l-live-03-ladder-heads-column-375", "div.sf-fdetail2__side", pad=6)
    f = ev(E.DETAIL_PROBE)
    want = dict(zip(f.get("groupNames") or [], f.get("groupDisplays") or []))
    check("待办25 the collapsed phone summary now shows the ladder",
          f.get("folded") is True and want.get("pricing") != "none",
          {"folded": f.get("folded"), "displays": want})
    check("待办25 ...because the fold is positional: groups 4+ are the ones hidden",
          all(want.get(g) != "none" for g in ("flavor", "weight"))
          and all(want.get(g) == "none" for g in ("pack", "shape", "container")),
          want)
    check("待办1 the three breaks are painted at 375 too",
          f.get("ranges") == RANGES
          and all(r["display"] != "none" and r["w"] > 20
                  for r in f.get("rangePaint") or []), f.get("rangePaint"))

    # -------------------------------------------------------- the cert band
    heights = {}
    # width, columns, rows, and the tokens THIS width is declared to use.
    BANDS = ((1440, 3, 2, "40px", CARD_PAD, CARD_GAP),
             (768, 2, 3, "40px", CARD_PAD, CARD_GAP),
             (375, 2, 3, "32px", "12px", "12px"))
    for i, (w, cols, rows, icon, pad, gap) in enumerate(BANDS):
        open_at(HOME, w)
        served(HOME, "待办4 at %d" % w)
        prescroll()
        if FRAMES_ON:
            shoot("h7l-live-%02d-cert-cards-%d" % (4 + i, w), ".sf-certstrip",
                  pad=10, mincolours=6)
        s = ev(E.STRIP_PROBE)
        strip_checks("%d" % w, s, icon, pad, gap)
        check("待办4 %d columns at %d" % (cols, w),
              len(s.get("lefts") or []) == cols and len(s.get("tops") or []) == rows,
              {"lefts": len(s.get("lefts") or []), "tops": len(s.get("tops") or [])})
        check("待办4 the icon is on the card's centre line  [%d]" % w,
              abs((s["iconBox"]["t"] + s["iconBox"]["h"] / 2)
                  - (s["cardBox"]["t"] + s["cardBox"]["h"] / 2)) <= 1.0,
              {"icon_cy": s["iconBox"]["t"] + s["iconBox"]["h"] / 2,
               "card_cy": s["cardBox"]["t"] + s["cardBox"]["h"] / 2})
        heights[w] = s["stripBox"]["h"]
        print("       band @%d : %.1f px" % (w, heights[w]))
    check("待办4 the band kept the pre-launch 245.4px it was accepted at  [1440]",
          240 <= heights[1440] <= 250, heights)

    # ------------------------------------------------------------ zh twins
    open_at(HOME_ZH, 1440)
    served(HOME_ZH, "the zh band")
    prescroll()
    if FRAMES_ON:
        shoot("h7l-live-07-zh-cert-cards-1440", ".sf-certstrip", pad=10, mincolours=6)
    zs = ev(E.STRIP_PROBE)
    check("待办4 the zh band is the same six cards",
          zs.get("count") == 6 and zs.get("cardBg") == CARD_BG
          and zs.get("cardRadius") == CARD_RADIUS, zs.get("count"))

    open_at(DETAIL_ZH, 1440)
    served(DETAIL_ZH, "the zh twin")
    prescroll()
    if FRAMES_ON:
        shoot("h7l-live-08-zh-ladder-heads-column", "div.sf-fdetail2__side", pad=6)
    z = ev(E.DETAIL_PROBE)
    check("待办25 the zh twin puts the ladder first as well",
          0 <= z.get("domIntro") < z.get("domPricing") < z.get("domFlavor"),
          {"intro": z.get("domIntro"), "pricing": z.get("domPricing"),
           "flavor": z.get("domFlavor")})
    check("待办1 the zh twin prints the same three breaks",
          z.get("ranges") == RANGES and z.get("customQty") is False, z.get("ranges"))
    check("待办2 the zh twin's button is the same button",
          z.get("ctaText") == "Send Inquiry" and z.get("ctaOpen") is True
          and (z.get("ctaHref") or "").endswith("/zh/contact/#quote"),
          {"text": z.get("ctaText"), "href": z.get("ctaHref")})

    # ------------------------------------------------------------- breadth
    paths = []
    for ln in open(MANIFEST).read().splitlines():
        if ln.startswith("#") or ln.startswith("path\t"):
            continue
        p = ln.split("\t")[0].strip()
        if p:
            paths.append(p)
    bad_code, bad_anchor, bad_old, tried = [], [], [], 0
    for p in paths:
        time.sleep(1.2)                    # CF 403s a persistent UA near ~85 hits
        b = curl(p)
        tried += 1
        if not b:
            bad_code.append((p, "empty body"))
            continue
        m = re.search(r"themes/(sinofresh-theme[a-z-]*)/style\.css\?ver=([0-9.]+)", b)
        if not m:
            bad_anchor.append((p, "no theme anchor"))
        elif m.group(1) != "sinofresh-theme" or m.group(2) != VER:
            bad_anchor.append((p, "%s?ver=%s" % (m.group(1), m.group(2))))
        if "sf-certgrid" in b or 'article class="sf-certcard' in b:
            bad_old.append(p)
    check("breadth: all %d paths answered" % len(paths),
          tried == len(paths) and not bad_code,
          {"tried": tried, "bad": bad_code[:6]})
    check("breadth: every path anchored on themes/sinofresh-theme/ at %s" % VER,
          not bad_anchor, bad_anchor[:6])
    check("breadth: no page still carries the pre-H7k cert markup",
          not bad_old, bad_old[:6])

    # ------------------------------------------------------------- summary
    bad = [r for r in RESULTS if not r[1]]
    print("\n%s  batch H7l live acceptance  (%d checks, %d failed)  [LIVE %s]"
          % ("PASS" if not bad else "FAIL", len(RESULTS), len(bad), VER))
    for n, _, det in bad:
        print("   FAIL %s  | %s" % (n, det[:200]))
    if FRAMES_ON:
        print("  frames: %d/%d non-flat -> %s/"
              % (sum(1 for x in FRAMES if x[4]), len(FRAMES), OUT))
    out = {"live": True, "ver": VER, "band_heights": heights,
           "frames": [{"name": n, "w": w, "h": h, "colours": c, "ok": o}
                      for n, w, h, c, o in FRAMES],
           "checks": [{"name": n, "ok": o, "detail": d} for n, o, d in RESULTS],
           "ok": not bad, "total": len(RESULTS), "failed": len(bad)}
    json.dump(out, open("_backup/b2d-h7l-live-accept.json", "w"), indent=1)
    print("  json -> _backup/b2d-h7l-live-accept.json")
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
